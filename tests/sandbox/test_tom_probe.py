import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.tom_probe import (
    _make_cfg_tom,
    _head_accuracy,
    _shuffle_accuracy,
    _latent_probe,
    _verdict_tom_emergence,
)


def test_make_cfg_tom_sets_flag_and_keeps_sweet():
    cfg = _make_cfg_tom("TOM")
    assert cfg.active_exp_variable == "TOM"
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0
    assert _make_cfg_tom("NONE").active_exp_variable == "NONE"


def _rec(pred, act, latent=None):
    return {"pred": pred, "act": act, "latent": np.zeros(68) if latent is None else latent}


def test_head_accuracy_exact_fraction():
    recs = [_rec(3, 3), _rec(3, 3), _rec(3, 3), _rec(0, 1)]
    assert _head_accuracy(recs) == 0.75
    assert _head_accuracy([]) == 0.0


def test_shuffle_accuracy_deterministic_edges():
    assert _shuffle_accuracy([_rec(3, 3), _rec(3, 3)]) == 1.0
    assert _shuffle_accuracy([_rec(0, 1), _rec(0, 1)]) == 0.0
    assert _shuffle_accuracy([]) == 0.0


def test_latent_probe_separable_beats_shuffle():
    np.random.seed(0)
    recs = []
    for c in range(4):
        base = np.zeros(68)
        base[c] = 5.0
        for _ in range(30):
            lat = base + np.random.randn(68) * 0.1
            recs.append(_rec(c, c, lat))
    acc_true, acc_shuffle = _latent_probe(recs)
    assert acc_true > 0.8
    assert acc_true > acc_shuffle


def test_latent_probe_too_few_records():
    assert _latent_probe([_rec(0, 0)]) == (0.0, 0.0)


def test_verdict_tom_emergence_two_branches():
    assert _verdict_tom_emergence(0.45, 0.20, 0.22) == "TOM_EMERGES"
    assert _verdict_tom_emergence(0.22, 0.20, 0.21) == "TOM_INERT"
    assert _verdict_tom_emergence(0.40, 0.35, 0.20) == "TOM_INERT"
