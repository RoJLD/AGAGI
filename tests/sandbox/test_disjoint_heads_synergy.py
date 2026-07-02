import pytest

from tools.disjoint_heads_ab import torch, _make_teachers
from tools.disjoint_heads_synergy import _train_flat_norm_perhead, _verdict_v4


def test_verdict_synergy_closes():
    # 3/5 seeds >= 0.90 -> SYNERGY_CLOSES
    assert _verdict_v4([0.95, 0.92, 0.91, 0.5, 0.4]) == "SYNERGY_CLOSES"


def test_verdict_no_synergy():
    # 3/5 seeds <= 0.79 -> NO_SYNERGY
    assert _verdict_v4([0.70, 0.60, 0.75, 0.95, 0.92]) == "NO_SYNERGY"


def test_verdict_partial():
    assert _verdict_v4([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_norm_perhead_runs_and_returns_dict():
    # Attrape une eventuelle RuntimeError autograd in-place (forward unique + retain_graph + 3 step sequentiels).
    teachers = _make_teachers()
    out = _train_flat_norm_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert out[k] == out[k]  # not NaN
        assert out[k] >= 0.0
