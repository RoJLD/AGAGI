import numpy as np
import pytest
from src.seed_ai import exp_stats as st


def test_wilcoxon_all_positive_is_significant():
    r = st.wilcoxon_signed_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert r["n"] == 10
    assert r["p"] < 0.01
    assert r["stat"] == 0.0  # W = min(W+, W-) = W- = 0


def test_wilcoxon_symmetric_is_not_significant():
    r = st.wilcoxon_signed_rank([1, -1, 2, -2, 3, -3, 4, -4])
    assert r["p"] > 0.5


def test_wilcoxon_drops_zeros():
    r = st.wilcoxon_signed_rank([0, 0, 1, 2, 3])
    assert r["n"] == 3


def test_wilcoxon_matches_scipy():
    scipy_stats = pytest.importorskip("scipy.stats")
    d = [0.5, -1.2, 2.3, 1.1, -0.4, 3.0, 0.9, -0.2, 1.5, 2.2, -1.0, 0.7]
    mine = st.wilcoxon_signed_rank(d)
    ref = scipy_stats.wilcoxon(d, correction=True, mode="approx")
    assert abs(mine["stat"] - float(ref.statistic)) < 1e-9
    assert abs(mine["p"] - float(ref.pvalue)) < 0.02


def test_paired_summary_fields():
    s = st.paired_summary([1.0, 2.0, -0.5, 3.0])
    assert set(s) >= {"mean", "se", "win_rate", "wilcoxon_p", "n"}
    assert s["n"] == 4
    assert 0.0 <= s["win_rate"] <= 1.0
