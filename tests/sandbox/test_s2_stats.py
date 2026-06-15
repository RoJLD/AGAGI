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
