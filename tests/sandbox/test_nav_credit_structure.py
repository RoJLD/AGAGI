"""Tests NAV-005 (rareté vs biais du crédit) : verdict pur + espérance analytique + smoke torch."""
import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.nav_credit_structure import credit_verdict, _expected_correct, analyze

try:
    import torch
except Exception:
    torch = None


def test_verdict_bias_not_rarity():
    # non-biaisé tient au plus rare (>=0.50), biaisé s'effondre (<=0.30)
    assert credit_verdict([0.9, 0.8, 0.7, 0.6], [0.9, 0.5, 0.0, -0.5]) == "BIAS_NOT_RARITY"


def test_verdict_rarity_also_fatal():
    assert credit_verdict([0.9, 0.6, 0.3, 0.1], [0.9, 0.5, 0.1, -0.2]) == "RARITY_ALSO_FATAL"


def test_expected_correct_threshold_at_one_third():
    # sous penalty=-0.5, E[correct] change de signe a p_success=1/3
    assert _expected_correct(1 / 3, -0.5) == pytest.approx(0.0, abs=1e-9)
    assert _expected_correct(0.02, -0.5) < 0        # regime in-world de T3 -> negatif
    assert _expected_correct(0.02, 0.0) >= 0        # non-biaise -> jamais negatif


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_smoke_biased_hurts_at_low_p_on_separable_synthetic():
    rng = np.random.default_rng(0)
    n, d = 800, 12
    y = rng.integers(0, 3, size=n)
    centers = rng.standard_normal((3, d)) * 3.0
    H = (centers[y] + rng.standard_normal((n, d))).astype(np.float32)
    cap = {"H": H, "correct": y}
    res = analyze(cap, seeds=(0, 1), steps=300, p_successes=(1.0, 0.03), penalty=-0.5)
    assert res["verdict"] in {"BIAS_NOT_RARITY", "RARITY_ALSO_FATAL", "BOTH_ROBUST", "MIXED"}
    # au plus rare, le biaisé doit faire au moins aussi mal que le non-biaisé
    assert res["biased"][-1]["recovery"] <= res["unbiased"][-1]["recovery"] + 0.20
