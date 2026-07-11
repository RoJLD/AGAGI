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
