"""P4.8 — `S2-REWARD-ABLATION` : le crédit in-world publié EFFACE le bassin DAgger
([[EDR-S2-CREDIT-RETENTION]] : ERODE, 36,0 -> 8,0, 12/12 seeds). Poursuit-il les termes INTRINSÈQUES de
`world_1_stoneage.py:1713` (curiosité, nouveauté) plutôt que l'ÉNERGIE ?

Ce fichier calibre TROIS choses, dans l'ordre du pré-vol :
  1. le SEAM de récompense (question 2 du pré-vol : « le chemin qu'on croit couper est-il le seul ? ») —
     réponse CONNUE : à échelles nulles, la récompense passée au learner est EXACTEMENT Δénergie, et le
     terme de nouveauté se décompose additivement (scale/√count) ; ET le terme de curiosité est
     STRUCTURELLEMENT NUL sous le backend torch (trouvé au smoke du 2026-09-14 : `b_energy` et
     `b_energy_curiosity` bit-identiques sur 200 ticks) — un bras qui ne peut rien changer (E2) est retiré
     du design, et le pré-vol REFUSE si la surprise se réveille ;
  2. le VERDICT (pur, lignes synthétiques, branches de la règle scellée dans l'ORDRE imposé) ;
  3. les gardes du runner (refus AVANT tout monde ; import des lignes P4.4 SEULEMENT sur réplication
     bit-identique constatée).
Les tests 1 simulent un monde (1 à 50 ticks, 1 à 4 agents) : sautés par conftest quand un run tient `kuzu`.
"""
import copy
import json
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import s2_reward_ablation as R  # noqa: E402

# --------------------------------------------------------------------------------------------------
# 0. La table des bras : ce que chaque bras COUPE, déclaré une fois, lu par le runner et par la règle.
# --------------------------------------------------------------------------------------------------


def test_arm_table_declares_the_frozen_control_the_full_reward_and_delta_energy_alone():
    assert R.ARMS == ("a_frozen", "b_full", "b_energy")
    # None = échelle du MONDE (publiée par `reward_defaults`, jamais recopiée) ; 0.0 = terme COUPÉ.
    assert R.ARM_REWARD["b_full"] == (None, None)
    assert R.ARM_REWARD["b_energy"] == (0.0, 0.0)
    assert "a_frozen" not in R.ARM_REWARD          # le bras gelé n'apprend pas : aucune récompense à décliner
    assert R.LEARNING_ARMS == ("b_full", "b_energy")


# --------------------------------------------------------------------------------------------------
# 1. Le seam de récompense — réponse connue.
# --------------------------------------------------------------------------------------------------


def test_reward_defaults_are_read_from_a_world_instance():
    """Une prémisse est une MESURE (E8 occ. 4) : les échelles par défaut sont lues sur un monde
    construit, pas recopiées de `world_1_stoneage.py:164/168`."""
    d = R.reward_defaults()
    assert set(d) == {"curiosity_scale", "novelty_scale"}
    assert d["curiosity_scale"] == pytest.approx(2.0) and d["novelty_scale"] == pytest.approx(3.0)
    e = R._world(2026, 0, curiosity_scale=0.0, novelty_scale=None)
    assert e.curiosity_scale == 0.0 and e.novelty_scale == pytest.approx(d["novelty_scale"])
    if hasattr(e, "memory_retriever"):
        e.memory_retriever.stop()


def test_first_tick_reward_decomposes_exactly_into_delta_energy_plus_novelty_and_a_dead_curiosity():
    """UN agent du bassin, UN tick, quatre mondes au même seed (identiques jusqu'à la récompense) :
    r_energy == Δénergie EXACT ; r_nov − r_energy == 3/√count ; r_cur − r_energy == 2·surprise == 0 (la
    surprise n'est JAMAIS écrite par le forward torch) ; r_full == r_energy + les deux. C'est la preuve que
    couper les échelles coupe LE chemin, tout le chemin, et rien d'autre."""
    from src.environments.stone_economy import novelty_bonus
    full = R.first_tick_reward(2026, None, None, num_agents=1)
    energy = R.first_tick_reward(2026, 0.0, 0.0, num_agents=1)
    cur = R.first_tick_reward(2026, None, 0.0, num_agents=1)
    nov = R.first_tick_reward(2026, 0.0, None, num_agents=1)
    for d in (full, energy, cur, nov):
        assert d["rewards"].shape == (1,) and d["delta_energy"].shape == (1,)
        assert np.all(np.isfinite(d["rewards"]))
    # les quatre mondes sont identiques jusqu'à la récompense
    for d in (energy, cur, nov):
        assert d["delta_energy"] == pytest.approx(full["delta_energy"], abs=1e-6)
        assert d["surprise"] == pytest.approx(full["surprise"], abs=1e-6)
        assert d["novelty_count"] == full["novelty_count"]
    s, c = float(full["surprise"][0]), int(full["novelty_count"][0])
    assert s == 0.0                                  # curiosité MORTE sous torch (mamba_agent.py:824 est legacy)
    assert c >= 1 and novelty_bonus(c, 3.0) > 0.0    # la nouveauté, elle, est VIVANTE au tick 1
    assert float(energy["rewards"][0]) == pytest.approx(float(energy["delta_energy"][0]), abs=1e-5)
    assert float(cur["rewards"][0] - energy["rewards"][0]) == pytest.approx(2.0 * s, abs=1e-5)
    assert float(nov["rewards"][0] - energy["rewards"][0]) == pytest.approx(novelty_bonus(c, 3.0), abs=1e-5)
    assert float(full["rewards"][0]) == pytest.approx(float(energy["rewards"][0]) + 2.0 * s + novelty_bonus(c, 3.0), abs=1e-5)
    # l'ablation CHANGE quelque chose (E2) : le terme de nouveauté est non nul au tick 1
    assert float(full["rewards"][0]) != pytest.approx(float(energy["rewards"][0]), abs=1e-6)


def test_preflight_reward_seam_publishes_the_decomposition_on_a_cohort():
    out = R.preflight_reward_seam(2026, num_agents=4)
    for k in ("seed", "num_agents", "max_abs_residual", "intrinsic_share_full", "reward_defaults",
              "r_full", "r_energy", "delta_energy"):
        assert k in out, k
    assert out["num_agents"] == 4 and out["max_abs_residual"] < 1e-4
    assert 0.0 < out["intrinsic_share_full"] <= 1.0
    assert out["reward_defaults"]["curiosity_scale"] == pytest.approx(2.0)


def test_curiosity_term_is_structurally_zero_under_the_torch_backend():
    """Trouvé au SMOKE du 2026-09-14 (E2 attrapée avant 10 h de calcul) : sous `use_torch_inworld`, le
    forward torch n'écrit JAMAIS `model.surprise` (seul le forward legacy numpy le pose,
    `mamba_agent.py:824`), donc le terme `curiosity_scale·surprise` de `world_1_stoneage.py:1713` vaut 0
    à chaque tick : `b_energy` et `b_energy_curiosity` étaient BIT-IDENTIQUES sur 200 ticks (dW 1442,82).
    Le pré-vol le MESURE (50 ticks, 4 agents) et le runner refuse tout design à trois bras si la
    surprise se réveille un jour."""
    out = R.preflight_curiosity_dead(2026, num_agents=4, ticks=50)
    assert out["ticks"] == 50 and out["num_agents"] == 4
    assert out["max_abs_surprise"] == 0.0 and out["learn_calls"] >= 50
    assert out["rewards_identical_curiosity_0_vs_default"] is True
    assert out["curiosity_scale_default"] == pytest.approx(2.0)


def test_preflight_curiosity_dead_refuses_a_live_surprise(monkeypatch):
    """Contre-exemple : si la surprise est NON nulle, le pré-vol doit LEVER (le design à 3 bras suppose
    la curiosité morte ; le design à 5 bras du sceau original serait alors requis)."""
    from tools.experiment_preflight import PreflightError
    real = R._ticks_reward_trace

    def fake(seed, curiosity_scale, novelty_scale, num_agents, ticks):
        d = real(seed, curiosity_scale, novelty_scale, num_agents, ticks)
        d["max_abs_surprise"] = 0.37
        d["rewards"] = [r + (0.0 if curiosity_scale == 0.0 else 0.74) for r in d["rewards"]]
        return d
    monkeypatch.setattr(R, "_ticks_reward_trace", fake)
    with pytest.raises(PreflightError):
        R.preflight_curiosity_dead(2026, num_agents=2, ticks=5)


# --------------------------------------------------------------------------------------------------
# 2. Le verdict — branches scellées, dans l'ordre imposé, sur lignes synthétiques.
# --------------------------------------------------------------------------------------------------


def _col(v, i, default):
    if v is None:
        return default
    return v[i] if isinstance(v, (list, tuple)) else v


def _rows(n=12, S_a=36.0, S_full=8.0, S_energy=8.0, dose_full=1999, dose_energy=1999):
    rows = []
    for i in range(n):
        rows.append({"seed": 2026 + i, "S_a": float(_col(S_a, i, 36.0)), "S_full": float(_col(S_full, i, 8.0)),
                     "S_energy": float(_col(S_energy, i, 8.0)),
                     "dose_full": int(dose_full), "dose_energy": int(dose_energy)})
    return rows


def test_verdict_refuses_missing_or_non_finite_inputs():
    rows = _rows()
    rows[3]["S_energy"] = float("nan")
    with pytest.raises(ValueError):
        R.reward_ablation_verdict(rows)
    rows = _rows()
    del rows[5]["S_full"]
    with pytest.raises(ValueError):
        R.reward_ablation_verdict(rows)
    with pytest.raises(ValueError):
        R.reward_ablation_verdict([])


def test_verdict_branch_1_INCOMPLET_wins_over_everything():
    v = R.reward_ablation_verdict(_rows(n=7, S_a=2.0, S_full=40.0))
    assert v["verdict"] == "INCOMPLET" and v["n"] == 7


def test_verdict_branch_2_INDETERMINE_HARNAIS_when_the_bassin_does_not_transfer():
    v = R.reward_ablation_verdict(_rows(S_a=15.0, S_full=8.0, S_energy=30.0))
    assert v["verdict"] == "INDETERMINE_HARNAIS" and "S_a" in v["why"]


def test_verdict_branch_3_INDETERMINE_DOSE_when_any_learning_arm_did_not_fire():
    v = R.reward_ablation_verdict(_rows(dose_energy=40))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_energy" in v["why"]
    v = R.reward_ablation_verdict(_rows(dose_full=40))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_full" in v["why"]


def test_verdict_branch_4_INDETERMINE_REPLICATION_when_the_full_reward_no_longer_erodes():
    """La prémisse (P4.4 : ERODE 12/12, −28) doit se REPRODUIRE dans ce run ; sinon il n'y a rien à
    ablater et aucune branche 6 n'est lue."""
    v = R.reward_ablation_verdict(_rows(S_full=34.0, S_energy=35.0))          # d_full = −2 : pas ERODE
    assert v["verdict"] == "INDETERMINE_REPLICATION" and "d_full" in v["why"]
    v = R.reward_ablation_verdict(_rows(S_full=[8.0] * 9 + [36.0] * 3))       # −28 mais 9/12
    assert v["verdict"] == "INDETERMINE_REPLICATION"


def test_verdict_RECOMPENSE_MAL_ALIGNEE_when_delta_energy_alone_does_not_erode():
    """Δénergie seule NEUTRE (35 vs 36) et complète ERODE : l'érosion EXIGE le terme de nouveauté — le
    seul terme intrinsèque VIVANT sous torch, donc nommé par construction."""
    v = R.reward_ablation_verdict(_rows(S_energy=35.0))
    assert v["verdict"] == "RECOMPENSE_MAL_ALIGNEE" and v["terme"] == "NOUVEAUTE"
    assert v["arm_energy"] == "NEUTRE" and v["arm_full"] == "ERODE" and v["attenuation"] is None


def test_verdict_RECOMPENSE_MAL_ALIGNEE_also_when_energy_alone_EXTENDS_the_bassin():
    v = R.reward_ablation_verdict(_rows(S_energy=[46.0] * 11 + [30.0]))
    assert v["verdict"] == "RECOMPENSE_MAL_ALIGNEE" and v["arm_energy"] == "ETENDU"


def test_verdict_CREDIT_ERODE_SEUL_PLEIN_when_delta_energy_alone_erodes_as_much_as_the_full_reward():
    v = R.reward_ablation_verdict(_rows(S_energy=8.0))
    assert v["verdict"] == "CREDIT_ERODE_SEUL" and v["attenuation"] == "PLEIN" and v["terme"] is None
    assert v["arm_energy"] == "ERODE" and v["d_energy_median"] == pytest.approx(-28.0)


def test_verdict_CREDIT_ERODE_SEUL_ATTENUE_when_the_novelty_term_adds_erosion():
    """Δénergie seule ÉRODE (20 vs 36 : −16, 12/12) mais MOINS que la récompense complète (20 vs 8 :
    +12 sur 12/12) : la nouveauté n'est pas nécessaire, elle aggrave."""
    v = R.reward_ablation_verdict(_rows(S_energy=20.0))
    assert v["verdict"] == "CREDIT_ERODE_SEUL" and v["attenuation"] == "ATTENUE"
    assert v["d_energy_vs_full_median"] == pytest.approx(12.0) and v["d_energy_vs_full_positive"] == "12/12"
    v = R.reward_ablation_verdict(_rows(S_energy=[20.0] * 9 + [8.0] * 3))   # 9/12
    assert v["verdict"] == "CREDIT_ERODE_SEUL" and v["attenuation"] == "PLEIN"


def test_verdict_arm_classification_needs_sign_10_of_12_AND_median_5_ticks():
    v = R.reward_ablation_verdict(_rows(S_energy=[8.0] * 9 + [40.0] * 3))     # médiane −28 mais 9/12
    assert v["arm_energy"] == "NEUTRE" and v["verdict"] == "RECOMPENSE_MAL_ALIGNEE"
    v = R.reward_ablation_verdict(_rows(S_energy=[33.0] * 12))                # 12/12 mais −3 > −5
    assert v["arm_energy"] == "NEUTRE"


def test_verdict_publishes_the_full_reading_and_the_thresholds():
    v = R.reward_ablation_verdict(_rows())
    for k in ("verdict", "n", "S_a_median", "S_full_median", "S_energy_median", "d_full_median", "d_energy_median",
              "d_energy_negative", "d_energy_positive", "d_full_negative", "arm_full", "arm_energy",
              "d_energy_vs_full_median", "d_energy_vs_full_positive", "dose_energy_median", "dose_full_median",
              "thresholds", "why", "terme", "attenuation"):
        assert k in v, k
    assert v["thresholds"] == {"harness_min": 20.0, "dose_min": 1000, "sign_min": 10, "delta_min": 5.0, "n_min": 12}


# --------------------------------------------------------------------------------------------------
# 3. Les gardes du runner.
# --------------------------------------------------------------------------------------------------


def test_run_arm_refuses_degenerate_args_before_any_world():
    import time
    t0 = time.time()
    for bad in (dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0), dict(arm="zzz"),
                dict(arm="b_warm_credit"), dict(arm="b_energy_curiosity")):
        kw = dict(seed=2026, arm="b_energy", num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.run_arm(**kw)
    assert time.time() - t0 < 0.5


def _p44():
    return json.load(open(os.path.join(R._ROOT, R.P44_RESULTS), encoding="utf-8"))


def test_replication_check_compares_the_measured_ages_with_the_P44_row_of_the_same_seed():
    p44 = _p44()
    row = copy.deepcopy(p44["arms"]["b_warm_credit"]["2026"])
    chk = R.replication_check(row, seed=2026)
    assert chk["identical"] is True and chk["p44_ages"] == row["survival"]["ages"]
    row["survival"]["ages"][0] += 1
    chk = R.replication_check(row, seed=2026)
    assert chk["identical"] is False
    with pytest.raises(KeyError):
        R.replication_check(row, seed=1999)                      # seed jamais mesuré par P4.4 : pas d'import


def test_p44_full_rows_are_importable_only_after_a_bit_identical_replication():
    with pytest.raises(ValueError):
        R.p44_full_rows(replication_identical=False)
    rows = R.p44_full_rows(replication_identical=True)
    assert sorted(rows) == [str(s) for s in R.SEEDS_DEFAULT]
    r = rows["2030"]
    assert r["arm"] == "b_full" and r["imported_from"] == R.P44_RESULTS
    assert math.isfinite(r["survival"]["survival_median"]) and r["learning"]["td_updates"] >= 1000
    assert r["reward"] == {"curiosity_scale": None, "novelty_scale": None}
