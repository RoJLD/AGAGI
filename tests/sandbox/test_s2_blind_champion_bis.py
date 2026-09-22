"""S2-BLIND-CHAMPION-bis (P2.42) — les deux politiques du `-bis` confrontées à des réponses CONNUES, 0 monde :
l'aveugle à l'entrée IGNORE l'observation (forward bit-identique sur deux obs différentes, là où la politique de
base les distingue) ; le crédit gelé ne touche pas W (là où le crédit de base le touche) ; le runner refuse les
arguments dégénérés avant tout monde ; injection d'un `map_fn` factice : les classes, la bande appariée et le
no-op sont demandés, et le verdict calibré est appliqué.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

from src.agents.mamba_agent import MambaAgent, MambaBatchModel  # noqa: E402
from tools.evo_runs.s2_blind_champion_bis import (BlindExceptIdentityFrozenMamba, FrozenCreditMamba,  # noqa: E402
                                                  IdentityZeroedFrozenMamba, InputBlindFrozenMamba,
                                                  blind_champion_verdict_ter, decomp_verdict, run_blind_champion_bis,
                                                  run_decomp)


def _pop(cls, seed=0, n=3):
    np.random.seed(seed)
    return cls([MambaAgent() for _ in range(n)])


def _two_obs(pop, seed=1):
    r = np.random.RandomState(seed)
    return (r.uniform(-1, 1, (pop.B, pop.max_I)).astype(np.float32),
            r.uniform(-1, 1, (pop.B, pop.max_I)).astype(np.float32))


def test_input_blind_policy_IGNORES_the_observation_where_the_base_policy_reads_it():
    a, b = _two_obs(_pop(InputBlindFrozenMamba))
    blind = _pop(InputBlindFrozenMamba)
    la = np.array(blind.forward(a)[0], copy=True)
    blind2 = _pop(InputBlindFrozenMamba)
    lb = np.array(blind2.forward(b)[0], copy=True)
    assert np.array_equal(la, lb), "l'aveugle à l'entrée doit rendre les MÊMES logits quelle que soit l'obs"
    base = _pop(FrozenCreditMamba)
    ka = np.array(base.forward(a)[0], copy=True)
    base2 = _pop(FrozenCreditMamba)
    kb = np.array(base2.forward(b)[0], copy=True)
    assert not np.array_equal(ka, kb), "contrôle positif : la politique de base LIT l'observation"


def test_frozen_credit_leaves_W_untouched_where_the_base_credit_moves_it():
    frozen = _pop(FrozenCreditMamba, seed=3)
    a, _ = _two_obs(frozen)
    frozen.forward(a)
    W0 = [g.genome.W.copy() for g in frozen.agents]
    assert frozen.compute_policy_gradient(np.ones(frozen.B, np.float32), [{"move": 1, "grab": 0, "rub": 0}] * frozen.B) is None
    assert all(np.array_equal(w, g.genome.W) for w, g in zip(W0, frozen.agents))
    base = _pop(MambaBatchModel, seed=3)
    base.forward(a)
    base.forward(a)                                     # le crédit legacy est différé d'un tick
    W1 = [g.genome.W.copy() for g in base.agents]
    base.compute_policy_gradient(np.ones(base.B, np.float32), [{"move": 1, "grab": 0, "rub": 0}] * base.B)
    base.forward(a)
    base.compute_policy_gradient(np.ones(base.B, np.float32), [{"move": 1, "grab": 0, "rub": 0}] * base.B)
    assert any(not np.array_equal(w, g.genome.W) for w, g in zip(W1, base.agents)), "contrôle positif : le crédit de base bouge W"


def test_runner_refuses_degenerate_arguments_before_any_world():
    with pytest.raises(ValueError):
        run_blind_champion_bis(seeds=[], map_fn=lambda **k: (_ for _ in ()).throw(AssertionError("monde lancé")))
    with pytest.raises(ValueError):
        run_blind_champion_bis(seeds=[1], k=0, map_fn=lambda **k: (_ for _ in ()).throw(AssertionError("monde lancé")))


def test_runner_requests_paired_band_and_noop_for_both_arms_and_applies_the_calibrated_verdict():
    seen = []

    def _map(worlds, seed, K, subject, batch_model_cls, paired_band, noop_control, **regime):
        seen.append((batch_model_cls.__name__, paired_band, noop_control))
        blind = batch_model_cls is InputBlindFrozenMamba
        return {"stoneage": {"intact_median": 40.0 if blind else 30.0, "within_ratio": 1.0 if blind else 0.94,
                             "verdict": "PERCEPTION_DECOY", "n": K, "policy": batch_model_cls.__name__,
                             "reference": "paired_band" if paired_band else "bare",
                             "noop": {"ratio": 1.0, "verdict": "PERCEPTION_DECOY", "median": 30.0}}}

    class G:
        W = np.zeros((4, 4))
    rows, verdict = run_blind_champion_bis(seeds=[1, 2, 3, 4, 5, 6, 7], map_fn=_map, champion_fn=lambda: G(), verbose=False)
    assert seen[:2] == [("FrozenCreditMamba", True, True), ("InputBlindFrozenMamba", True, True)] and len(seen) == 14
    assert all(r["blind"]["w_ok"] for r in rows)
    assert verdict["verdict"] == "AVEUGLE_SURVIT_MIEUX" and verdict["r_blind"] == pytest.approx(4 / 3)


def test_control_ii_failing_on_one_seed_gives_INDETERMINE_HARNAIS_never_a_verdict():
    def _map(worlds, seed, K, subject, batch_model_cls, paired_band, noop_control, **regime):
        blind = batch_model_cls is InputBlindFrozenMamba
        return {"stoneage": {"intact_median": 40.0 if blind else 30.0,
                             "within_ratio": (0.90 if seed == 3 else 1.0) if blind else 0.94,
                             "verdict": "PERCEPTION_DECOY", "n": K, "policy": batch_model_cls.__name__,
                             "reference": "paired_band", "noop": {"ratio": 1.0, "verdict": "PERCEPTION_DECOY", "median": 30.0}}}

    class G:
        W = np.zeros((4, 4))
    _, verdict = run_blind_champion_bis(seeds=[1, 2, 3], map_fn=_map, champion_fn=lambda: G(), verbose=False)
    assert verdict["verdict"] == "INDETERMINE-HARNAIS" and any("seed 3" in e for e in verdict["echecs"])


def _row(seed, intact, blind, within_blind=1.0):
    return {"seed": seed, "intact": {"intact_median": intact, "within_ratio": 0.99, "verdict": "PERCEPTION_DECOY"},
            "blind": {"intact_median": blind, "within_ratio": within_blind, "verdict": "PERCEPTION_DECOY", "w_ok": True}}


def test_ter_clause_iii_keeps_a_seed_whose_INTACT_arm_is_under_the_floor_and_names_it():
    # le cas du -bis : intact 20,5 < 24,0, aveugle 35 > 24,0 -> gardé, nommé, verdict lu
    rows = [_row(s, 20.5, 35.0) for s in range(7)]
    v = blind_champion_verdict_ter(rows, floor=24.0)
    assert v["verdict"] == "AVEUGLE_SURVIT_MIEUX" and v["intact_sous_plancher"] == list(range(7)) and v["ecartes"] == []
    assert v["n"] == 7 and v["r_blind"] == pytest.approx(35.0 / 20.5)


def test_ter_clause_iii_discards_ONLY_when_both_arms_are_pinned_at_or_under_the_floor():
    rows = [_row(0, 20.0, 22.0), _row(1, 20.0, 24.0)] + [_row(s, 20.5, 35.0) for s in range(2, 7)]
    v = blind_champion_verdict_ter(rows, floor=24.0)
    # 5 seeds unanimes : p = 2 x 0,5^5 = 0,0625 >= 0,05 -> INDETERMINE (la puissance manque, l'instrument le dit)
    assert v["ecartes"] == [0, 1] and v["n"] == 5 and v["verdict"] == "INDETERMINE" and v["sign_p"] == pytest.approx(0.0625)
    rows.append(_row(7, 20.5, 35.0))                    # 6 gardés : p = 0,031 -> lisible
    assert blind_champion_verdict_ter(rows, floor=24.0)["verdict"] == "AVEUGLE_SURVIT_MIEUX"
    v2 = blind_champion_verdict_ter([_row(0, 20.0, 22.0), _row(1, 20.0, 23.0)], floor=24.0)
    assert v2["verdict"] == "INDETERMINE-DEGENERE" and v2["ecartes"] == [0, 1]


def test_ter_controls_still_come_first_and_no_cost_is_still_readable():
    rows = [_row(s, 30.0, 30.0) for s in range(7)]
    assert blind_champion_verdict_ter(rows, floor=24.0)["verdict"] == "PAS_DE_COUT"
    rows[3]["blind"]["within_ratio"] = 0.90
    assert blind_champion_verdict_ter(rows, floor=24.0)["verdict"] == "INDETERMINE-HARNAIS"
    assert blind_champion_verdict_ter([], floor=24.0)["verdict"] == "INDETERMINE-SANS-MESURE"


# ---- DECOMP-R1 : les deux masques partiels, et le verdict de décomposition ----------------------------------
def _champion_like_pop(cls, n=3):
    """Une population dont la géométrie est celle du champion HoF (64 entrées, 126 sorties, 172 nœuds -> 18 identités)."""
    np.random.seed(0)
    return cls([MambaAgent(num_inputs=64, num_outputs=126, num_nodes=172) for _ in range(n)])


def test_partial_masks_zero_EXACTLY_the_announced_slice_and_nothing_else(monkeypatch):
    recu = {}

    def _spy(self, batch_obs, env_surprise_batch=None):
        recu["x"] = np.array(batch_obs, copy=True)
        return np.zeros((self.B, self.max_O), np.float32), np.zeros(self.B)
    monkeypatch.setattr(FrozenCreditMamba, "forward", _spy)
    for cls, lo, hi in ((BlindExceptIdentityFrozenMamba, 0, 46), (IdentityZeroedFrozenMamba, 46, 64)):
        pop = _champion_like_pop(cls)
        assert pop._zero_slice() == (lo, hi)
        obs = np.random.RandomState(2).uniform(0.5, 1.0, (pop.B, pop.max_I)).astype(np.float32)   # jamais 0 par hasard
        pop.forward(obs)
        x = recu["x"]
        assert np.all(x[:, lo:hi] == 0.0), cls.__name__
        garde = np.ones(pop.max_I, bool)
        garde[lo:hi] = False
        assert np.array_equal(x[:, garde], obs[:, garde]), cls.__name__
        assert np.array_equal(obs, obs)                     # l'entrée n'est pas mutée (copie)


def test_the_two_partial_masks_are_complementary_and_together_make_the_full_blind():
    pop_a, pop_b = _champion_like_pop(BlindExceptIdentityFrozenMamba), _champion_like_pop(IdentityZeroedFrozenMamba)
    (lo_a, hi_a), (lo_b, hi_b) = pop_a._zero_slice(), pop_b._zero_slice()
    assert hi_a == lo_b and lo_a == 0 and hi_b == pop_b.max_I, "les deux tranches se recollent en [0, max_I)"


def _drow(seed, ref_i, ex, idz, noop_ex=1.0, noop_id=1.0, w_ok=True):
    return {"seed": seed, "intact_median_ref": ref_i, "blind_median_ref": ref_i * 1.6,
            "except_identity": {"intact_median": ex, "noop": {"ratio": noop_ex}, "w_ok": w_ok, "within_ratio": 1.0},
            "identity_zeroed": {"intact_median": idz, "noop": {"ratio": noop_id}, "w_ok": w_ok, "within_ratio": 1.0}}


def test_decomp_branches_in_the_imposed_order():
    assert decomp_verdict([_drow(s, 22.0, 35.0, 22.5) for s in range(7)])["verdict"] == "EXCITATION"
    assert decomp_verdict([_drow(s, 22.0, 22.5, 35.0) for s in range(7)])["verdict"] == "IDENTITE"
    assert decomp_verdict([_drow(s, 22.0, 35.0, 35.0) for s in range(7)])["verdict"] == "LES_DEUX"
    assert decomp_verdict([_drow(s, 22.0, 22.5, 22.5) for s in range(7)])["verdict"] == "NI_L_UN_NI_L_AUTRE"
    assert decomp_verdict([_drow(s, 22.0, 25.0, 25.0) for s in range(7)])["verdict"] == "MIXTE"        # 1,14 : entre les barres
    assert decomp_verdict([])["verdict"] == "INDETERMINE-SANS-MESURE"


def test_decomp_controls_come_first_noop_must_be_EXACTLY_one():
    rows = [_drow(s, 22.0, 35.0, 22.5) for s in range(7)]
    rows[2]["except_identity"]["noop"]["ratio"] = 1.02
    v = decomp_verdict(rows)
    assert v["verdict"] == "INDETERMINE-HARNAIS" and any("seed 2" in e for e in v["echecs"])
    rows = [_drow(s, 22.0, 35.0, 22.5, w_ok=(s != 4)) for s in range(7)]
    assert decomp_verdict(rows)["verdict"] == "INDETERMINE-HARNAIS"


def test_decomp_six_of_seven_convention_and_mixed():
    rows = [_drow(s, 22.0, 35.0 if s < 5 else 23.0, 22.5) for s in range(7)]     # 5/7 hauts seulement
    assert decomp_verdict(rows)["verdict"] == "MIXTE"


def test_run_decomp_imports_the_reference_by_seed_and_requests_both_partial_arms(monkeypatch):
    seen = []

    def _map(worlds, seed, K, subject, batch_model_cls, paired_band, noop_control, **regime):
        seen.append((seed, batch_model_cls.__name__, paired_band, noop_control))
        return {"stoneage": {"intact_median": 30.0, "within_ratio": 1.0, "verdict": "PERCEPTION_DECOY", "n": K,
                             "policy": batch_model_cls.__name__, "reference": "paired_band",
                             "noop": {"ratio": 1.0, "verdict": "PERCEPTION_DECOY", "median": 30.0}}}

    class G:
        W = np.zeros((4, 4))
    refs = {s: {"intact": {"intact_median": 20.0}, "blind": {"intact_median": 32.0}} for s in (1, 2)}
    rows, v = run_decomp(seeds=[1, 2], map_fn=_map, champion_fn=lambda: G(), ref_rows=refs, verbose=False)
    assert [x[1] for x in seen] == ["BlindExceptIdentityFrozenMamba", "IdentityZeroedFrozenMamba"] * 2
    assert all(x[2] and x[3] for x in seen) and rows[0]["intact_median_ref"] == 20.0 and rows[0]["except_identity"]["w_ok"]
    assert v["r_ex"] == [1.5, 1.5]
    with pytest.raises(ValueError):
        run_decomp(seeds=[], map_fn=_map, champion_fn=lambda: G(), ref_rows=refs)
