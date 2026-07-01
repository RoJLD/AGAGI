import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

torch = pytest.importorskip("torch")

from tools.disjoint_heads_ab import (
    _make_teachers, _make_data, FlatModel, DisjointModel, _trunk_params_count, D, K_A, P_PRED,
)


def test_data_deterministic():
    te = _make_teachers()
    a = _make_data(16, 123, te)
    b = _make_data(16, 123, te)
    assert torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])
    assert torch.equal(a[2], b[2]) and torch.equal(a[3], b[3])


def test_trunk_param_parity():
    assert _trunk_params_count(FlatModel()) == _trunk_params_count(DisjointModel())


def test_forward_shapes():
    te = _make_teachers()
    x = _make_data(7, 1, te)[0]
    for m in (FlatModel(), DisjointModel()):
        la, v, p = m(x)
        assert la.shape == (7, K_A) and v.shape == (7, 1) and p.shape == (7, P_PRED)


from tools.disjoint_heads_ab import _train_arm, _interference_cosine


def test_train_arm_returns_finite_losses():
    te = _make_teachers()
    for arm in ("flat", "disjoint"):
        losses, interf = _train_arm(arm, 2200, te, steps=60)
        assert set(losses.keys()) == {"action", "value", "pred"}
        assert all(v == v and v < 1e6 for v in losses.values())  # finis (pas NaN/inf)
    # interference : float dans [-1, 1] pour FLAT, None pour DISJOINT
    _, interf_flat = _train_arm("flat", 2200, te, steps=10)
    assert -1.0001 <= interf_flat <= 1.0001
    _, interf_disj = _train_arm("disjoint", 2200, te, steps=10)
    assert interf_disj is None


def test_train_arm_deterministic():
    te = _make_teachers()
    a, _ = _train_arm("flat", 2201, te, steps=40)
    b, _ = _train_arm("flat", 2201, te, steps=40)
    assert a == b
