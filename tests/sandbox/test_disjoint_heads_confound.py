import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

torch = pytest.importorskip("torch")

from tools.disjoint_heads_ab import _make_teachers
from tools.disjoint_heads_confound import _train_flat_norm, _recovery, _verdict_confound, main_confound_check


def test_verdict_confound_three_branches():
    assert _verdict_confound([0.6, 0.7, 0.8, 0.1, 0.0]) == "CONFOUND_CONFIRMED"
    assert _verdict_confound([0.1, 0.0, 0.15, 0.6, 0.7]) == "CONFOUND_REFUTED"
    assert _verdict_confound([0.3, 0.4, 0.35, 0.6, 0.0]) == "CONFOUND_PARTIAL"


def test_recovery_math():
    flat = {"action": 0.25, "value": 0.030, "pred": 0.030}
    disj = {"action": 0.25, "value": 0.010, "pred": 0.010}
    flatnorm = {"action": 0.25, "value": 0.020, "pred": 0.020}
    assert abs(_recovery(flat, flatnorm, disj) - 0.5) < 1e-9


def test_train_flat_norm_finite():
    te = _make_teachers()
    d = _train_flat_norm(2200, te, steps=40)
    assert set(d.keys()) == {"action", "value", "pred"}
    assert all(v == v and v < 1e6 for v in d.values())


def test_smoke_confound_returns_verdict():
    res = main_confound_check(K=1, base=99000, steps=30, _return=True)
    assert res["verdict"] in {"CONFOUND_CONFIRMED", "CONFOUND_REFUTED", "CONFOUND_PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res
