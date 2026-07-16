import pytest

from tools.disjoint_heads_ab import torch, _make_teachers
from tools.disjoint_heads_v3 import _train_flat_perhead, _verdict_v3


def test_verdict_optimizer_confirmed():
    # 3/5 seeds >= 0.90 -> CONFIRMED (majorite = 3)
    assert _verdict_v3([0.95, 0.92, 0.91, 0.5, 0.4]) == "OPTIMIZER_CONFIRMED"


def test_verdict_refuted():
    # 3/5 seeds <= 0.79 -> REFUTED
    assert _verdict_v3([0.70, 0.60, 0.75, 0.95, 0.92]) == "REFUTED"


def test_verdict_partial():
    # ni majorite >=0.90 ni majorite <=0.79
    assert _verdict_v3([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_perhead_runs_and_returns_dict():
    # Critique : ce test attrape une eventuelle erreur autograd in-place
    # (forward unique + retain_graph + 3 step sequentiels sur trunc partage).
    teachers = _make_teachers()
    out = _train_flat_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert out[k] == out[k]  # not NaN
        assert out[k] >= 0.0


from tools.disjoint_heads_v3 import main_v3_check


def test_smoke_v3_returns_verdict():
    res = main_v3_check(K=1, base=99000, steps=30, _return=True)
    assert res["verdict"] in {"OPTIMIZER_CONFIRMED", "REFUTED", "PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res
