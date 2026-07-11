import math
from tools.life_score_contamination_probe import (
    score, kendall_tau, _topk_indices, topk_jaccard, term_mass_share,
)

W = {"age": 0.1, "preys_eaten": 50.0, "altars_solved": 20.0,
     "spears_crafted": 300.0, "mammoth_kills": 400.0, "ref_distinction": 0.0}


def _c(age=0, preys=0, altars=0, spears=0, mammoth=0, ref=0.0):
    return {"age": age, "preys_eaten": preys, "altars_solved": altars,
            "spears_crafted": spears, "mammoth_kills": mammoth, "ref_distinction": ref}


def test_score_weighted_sum():
    assert score(_c(age=10, preys=2), W) == (10 * 0.1 + 2 * 50.0)
    assert score(_c(spears=1), W) == 300.0


def test_kendall_tau_identity():
    assert kendall_tau([3.0, 1.0, 2.0], [3.0, 1.0, 2.0]) == 1.0


def test_kendall_tau_reversed():
    assert kendall_tau([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == -1.0


def test_topk_indices_tie_broken_by_index():
    # scores egaux -> indices croissants
    assert _topk_indices([5.0, 5.0, 5.0], 2) == {0, 1}


def test_topk_jaccard_identical_is_one():
    s = [1.0, 2.0, 3.0, 4.0]
    assert topk_jaccard(s, s, 2) == 1.0


def test_topk_jaccard_disjoint_is_zero():
    # top-1 de full = idx3 ; top-1 de var = idx0 -> disjoint
    assert topk_jaccard([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0], 1) == 0.0


def test_term_mass_share_sums_to_one():
    roster = [_c(preys=2), _c(mammoth=1), _c(spears=1)]
    shares = term_mass_share(roster, W)
    assert abs(sum(shares.values()) - 1.0) < 1e-9
    assert shares["altars_solved"] == 0.0  # aucun autel


def test_term_mass_share_zero_total_safe():
    assert term_mass_share([_c()], W)["preys_eaten"] == 0.0  # pas de division par zero


from tools.life_score_contamination_probe import WEIGHTS_FULL, variants, analyze_roster


def test_variants_structure():
    v = variants()
    assert set(v) == {"full", "drop_altars", "drop_spears", "drop_both"}
    assert v["drop_altars"]["altars_solved"] == 0.0
    assert v["drop_altars"]["spears_crafted"] == 300.0
    assert v["drop_spears"]["spears_crafted"] == 0.0
    assert v["drop_both"]["altars_solved"] == 0.0 and v["drop_both"]["spears_crafted"] == 0.0
    # full ne modifie pas les poids de reference
    assert v["full"]["spears_crafted"] == WEIGHTS_FULL["spears_crafted"]


def test_drop_altars_is_identity_when_altars_dead():
    # altars_solved == 0 partout (dead code EDR 096) -> retirer altars = no-op EXACT
    roster = [_c(age=i, preys=i % 3) for i in range(20)]
    res = analyze_roster(roster)
    assert res["variants"]["drop_altars"]["kendall_tau"] == 1.0
    assert res["variants"]["drop_altars"]["topk_jaccard"] == 1.0
    assert res["n_altar_solvers"] == 0


def test_drop_spears_reorders_when_crafter_present():
    # 19 agents faibles + 1 crafteur qui, GRACE au terme spears.300, entre dans le top-k ;
    # le retirer doit l'en sortir -> jaccard < 1
    roster = [_c(age=1, preys=1) for _ in range(19)] + [_c(age=1, preys=1, spears=1)]
    res = analyze_roster(roster, frac_topk=0.25)
    assert res["n_crafters"] == 1
    assert res["variants"]["drop_spears"]["topk_jaccard"] < 1.0


from tools.life_score_contamination_probe import _components, run_arm


def test_components_extracts_six_terms():
    agent = {"age": 5, "preys_eaten": 3, "altars_solved": 0,
             "spears_crafted": 1, "mammoth_kills": 2, "_ref_distinction": 0.4}
    c = _components(agent)
    assert c == {"age": 5, "preys_eaten": 3, "altars_solved": 0,
                 "spears_crafted": 1, "mammoth_kills": 2, "ref_distinction": 0.4}


def test_components_defaults_missing_keys():
    c = _components({"age": 1, "preys_eaten": 0, "altars_solved": 0})
    assert c["spears_crafted"] == 0 and c["mammoth_kills"] == 0 and c["ref_distinction"] == 0.0


def test_run_arm_smoke_returns_roster():
    # run minuscule : evolue 1 ere de 4 agents 5 ticks, mesure -> liste de dicts a 6 cles
    roster = run_arm(seed=0, eras=1, num_agents=4, max_ticks=5)
    assert isinstance(roster, list) and len(roster) >= 1
    assert set(roster[0]) == {"age", "preys_eaten", "altars_solved",
                              "spears_crafted", "mammoth_kills", "ref_distinction"}
