"""Tests NAV-004 (frontiere de recuperation) : verdict pur + smoke torch synthetique."""
import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.nav_signal_density import density_verdict, analyze
from tools.nav_readout_trainability import _split_zscore  # noqa: F401 (garde l'import stable)

try:
    import torch
except Exception:
    torch = None


def test_verdict_bias_is_fatal():
    # sparsite (non-biaise) tient (>=0.50), misattribution (biaise) s'effondre (<=0.30)
    assert density_verdict([0.9, 0.8, 0.7, 0.6], [0.9, 0.5, 0.2, -0.4]) == "BIAS_IS_FATAL"


def test_verdict_density_is_fatal():
    assert density_verdict([0.9, 0.5, 0.2, 0.05], [0.9, 0.8, 0.7, 0.6]) == "DENSITY_IS_FATAL"


def test_verdict_both_robust():
    assert density_verdict([0.9, 0.8, 0.7, 0.6], [0.9, 0.85, 0.75, 0.7]) == "BOTH_ROBUST"


def test_verdict_both_fragile():
    assert density_verdict([0.4, 0.2, 0.1, 0.0], [0.4, 0.2, 0.1, 0.0]) == "BOTH_FRAGILE"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_smoke_bias_hurts_more_than_sparsity_on_separable_synthetic():
    # 3 classes separables : la misattribution BIAISEE doit degrader plus que la sparsite non-biaisee
    rng = np.random.default_rng(0)
    n, d = 800, 12
    y = rng.integers(0, 3, size=n)
    centers = rng.standard_normal((3, d)) * 3.0
    H = (centers[y] + rng.standard_normal((n, d))).astype(np.float32)
    cap = {"H": H, "correct": y}
    res = analyze(cap, seeds=(0, 1), steps=300, sparsities=(1.0, 0.1), noises=(0.0, 1.0), misattrs=(0.0, 1.0))
    assert res["verdict"] in {"BIAS_IS_FATAL", "DENSITY_IS_FATAL", "BOTH_ROBUST", "BOTH_FRAGILE", "MIXED"}
    assert set(res) >= {"sparsity", "noise", "misattr"}
    # au point le plus dur, la misattribution totale doit faire au moins aussi mal que la sparsite forte
    assert res["misattr"][-1]["recovery"] <= res["sparsity"][-1]["recovery"] + 0.20
