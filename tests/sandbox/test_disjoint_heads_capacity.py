import pytest

from tools.disjoint_heads_ab import torch, D, K_A, P_PRED, _make_teachers, _make_data
from tools.disjoint_heads_capacity import _verdict_capacity


def test_verdict_induced_credit_robust():
    assert _verdict_capacity([-0.1, -0.1, -0.2, 0.0, -0.3], [0.8, 0.7, 0.9, 0.6, 0.85]) == "INDUCED+CREDIT_ROBUST"


def test_verdict_induced_arch_matters():
    assert _verdict_capacity([-0.2, -0.15, -0.3, -0.1, -0.25], [0.1, 0.15, 0.05, 0.2, 0.1]) == "INDUCED+ARCH_MATTERS"


def test_verdict_not_induced():
    assert _verdict_capacity([0.0, 0.01, -0.02, 0.03, 0.0], [0.9, 0.8, 0.85, 0.7, 0.9]) == "NOT_INDUCED+CREDIT_ROBUST"


def test_verdict_induced_partial():
    assert _verdict_capacity([-0.2, -0.15, -0.3, -0.1, -0.25], [0.35, 0.4, 0.3, 0.45, 0.38]) == "INDUCED+CREDIT_PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_trunk_parity_at_h6():
    from tools.disjoint_heads_capacity import FlatModelH, DisjointModelH
    flat = FlatModelH(6)
    disj = DisjointModelH(6)
    flat_trunk = sum(p.numel() for p in flat.trunk.parameters())
    disj_trunk = sum(p.numel() for t in (disj.trunk_action, disj.trunk_value, disj.trunk_pred) for p in t.parameters())
    assert flat_trunk == disj_trunk  # D*H+H == 3*(D*(H/3)+H/3)


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flatmodelh48_reproduces_flatmodel_init():
    from tools.disjoint_heads_ab import FlatModel
    from tools.disjoint_heads_capacity import FlatModelH
    torch.manual_seed(0)
    ref = FlatModel()
    torch.manual_seed(0)
    got = FlatModelH(48)
    assert torch.allclose(ref.trunk.weight, got.trunk.weight)
    assert torch.allclose(ref.head_action.weight, got.head_action.weight)
    assert torch.allclose(ref.head_value.weight, got.head_value.weight)
    assert torch.allclose(ref.head_pred.weight, got.head_pred.weight)


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_interference_cosine_h_runs():
    from tools.disjoint_heads_capacity import FlatModelH, _interference_cosine_h
    teachers = _make_teachers()
    batch = _make_data(16, 123, teachers)
    c = _interference_cosine_h(FlatModelH(6), batch)
    assert isinstance(c, float) and c == c  # not NaN


def test_smoke_capacity_returns_verdict():
    from tools.disjoint_heads_capacity import main_capacity_check

    res = main_capacity_check(K=1, base=99000, Hs=(48, 3), steps=25, _return=True)
    assert res["verdict"] == "SKIPPED_NO_TORCH" or "+" in res["verdict"]
    assert "per_H" in res
