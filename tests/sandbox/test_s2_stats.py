# tests/sandbox/test_s2_stats.py
import numpy as np
from src.seed_ai.s2_stats import cliffs_delta, median_ratio


def test_cliffs_delta_full_dominance():
    # tous les a > tous les b -> delta = +1
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0


def test_cliffs_delta_full_dominance_negative():
    assert cliffs_delta([1, 2, 3], [5, 6, 7]) == -1.0


def test_cliffs_delta_no_difference():
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_median_ratio_basic():
    assert median_ratio([20, 40, 60], [10, 20, 30]) == 2.0


def test_median_ratio_zero_denominator_returns_inf():
    assert median_ratio([5, 5, 5], [0, 0, 0]) == float("inf")


from src.seed_ai.s2_stats import wilcoxon_signed_rank


def test_wilcoxon_all_positive_is_significant():
    # 15 différences toutes positives -> p très petit
    d = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    w, p = wilcoxon_signed_rank(d)
    assert p < 0.01


def test_wilcoxon_symmetric_not_significant():
    d = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0]
    w, p = wilcoxon_signed_rank(d)
    assert p > 0.5


def test_wilcoxon_drops_zeros_and_handles_empty():
    assert wilcoxon_signed_rank([0.0, 0.0])[1] == 1.0


from src.seed_ai.s2_stats import bootstrap_ci, median_ratio as _mr


def test_bootstrap_ci_brackets_point_estimate():
    # NB : espacement NON uniforme (et non proportionnel à b) -> le bootstrap apparié a une vraie
    # variance. med(a)=32, med(b)=15.5 -> ratio vrai ~2. (Des données a==2*b donneraient lo==hi.)
    a = [18, 21, 23, 26, 28, 31, 33, 35, 38, 41, 43, 46]
    b = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    lo, hi = bootstrap_ci(_mr, a, b, n_boot=500, alpha=0.05, seed=1)
    assert lo <= 2.0 <= hi          # ratio vrai ~2
    assert lo < hi


def test_bootstrap_ci_is_deterministic_with_seed():
    a, b = [3, 4, 5, 6], [1, 2, 3, 4]
    assert bootstrap_ci(_mr, a, b, n_boot=200, seed=7) == bootstrap_ci(_mr, a, b, n_boot=200, seed=7)
