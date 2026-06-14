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
