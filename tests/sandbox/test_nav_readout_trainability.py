"""Tests du banc T1/M1 (readout RL-recuperable ?) : verdict pur + smoke torch sur donnees synthetiques."""
import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.nav_readout_trainability import readout_verdict, analyze
from tools.nav_localization_probe import capture  # noqa: F401 (garde l'import stable)
from tools.lewis_survival_sweep import _cfg  # noqa: F401

try:
    import torch
except Exception:
    torch = None


def test_verdict_invalid_when_supervised_cannot_learn():
    # le supervise lui-meme reste au hasard -> cible mal posee
    assert readout_verdict(acc_sup=0.55, acc_rl=0.52, chance=0.5) == "INVALID_TARGET"


def test_verdict_rl_recovers_when_rl_reaches_ceiling():
    # sup 0.80, chance 0.5 ; rl 0.75 -> recovery (0.25/0.30)=0.83 >= 0.70
    assert readout_verdict(acc_sup=0.80, acc_rl=0.75, chance=0.5) == "RL_RECOVERS"


def test_verdict_credit_gated_when_rl_fails():
    # sup 0.80, rl 0.56 -> recovery (0.06/0.30)=0.20 <= 0.30
    assert readout_verdict(acc_sup=0.80, acc_rl=0.56, chance=0.5) == "CREDIT_GATED"


def test_verdict_partial_between():
    # recovery ~0.5
    assert readout_verdict(acc_sup=0.80, acc_rl=0.65, chance=0.5) == "PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_smoke_supervised_beats_rl_floor_on_separable_synthetic():
    # 3 classes lineairement separables : le SUPERVISE doit largement battre le hasard (sanity du harnais
    # d'entrainement, sans faire tourner le monde). On ne teste PAS le verdict RL ici (c'est la question).
    rng = np.random.default_rng(0)
    n, d = 600, 12
    y = rng.integers(0, 3, size=n)
    centers = rng.standard_normal((3, d)) * 3.0
    H = (centers[y] + rng.standard_normal((n, d))).astype(np.float32)
    cap = {"H": H, "correct": y}
    res = analyze(cap, seeds=(0, 1), steps=300)
    assert res["acc_sup"] > res["chance"] + 0.15      # le supervise apprend nettement
    assert res["verdict"] in {"RL_RECOVERS", "CREDIT_GATED", "PARTIAL", "INVALID_TARGET"}
