import numpy as np

from tools.disjoint_heads_ab import D, K_A, P_PRED
from tools.disjoint_heads_correlated import _make_correlated_teachers, _verdict_correlated


def test_teacher_format():
    t = _make_correlated_teachers(0.5)
    assert set(t.keys()) == {"action", "value", "pred"}
    assert t["action"][0].shape == (D, 16) and t["action"][1].shape == (16, K_A)
    assert t["value"][0].shape == (D, 16) and t["value"][1].shape == (16, 1)
    assert t["pred"][0].shape == (D, 16) and t["pred"][1].shape == (16, P_PRED)


def test_rho_changes_w1():
    # rho=0 (independant) vs rho=0.95 (sous-espace commun signe) -> w1 differe pour value
    t0 = _make_correlated_teachers(0.0)
    t95 = _make_correlated_teachers(0.95)
    assert not np.allclose(t0["value"][0], t95["value"][0])
    # meme seed -> reproductible
    assert np.allclose(t95["value"][0], _make_correlated_teachers(0.95)["value"][0])


def test_verdict_induced_credit_robust():
    assert _verdict_correlated([-0.1, -0.1, -0.2, 0.0, -0.3], [0.8, 0.7, 0.9, 0.6, 0.85]) == "INDUCED+CREDIT_ROBUST"


def test_verdict_not_induced():
    assert _verdict_correlated([0.0, 0.01, -0.02, 0.03, 0.0], [0.9, 0.8, 0.85, 0.7, 0.9]) == "NOT_INDUCED+CREDIT_ROBUST"


def test_verdict_induced_arch_matters():
    assert _verdict_correlated([-0.2, -0.15, -0.3, -0.1, -0.25], [0.1, 0.15, 0.05, 0.2, 0.1]) == "INDUCED+ARCH_MATTERS"


def test_verdict_induced_partial():
    assert _verdict_correlated([-0.2, -0.15, -0.3, -0.1, -0.25], [0.35, 0.4, 0.3, 0.45, 0.38]) == "INDUCED+CREDIT_PARTIAL"


from tools.disjoint_heads_correlated import main_correlated_check


def test_smoke_correlated_returns_verdict():
    res = main_correlated_check(K=1, base=99000, rhos=(0.0, 0.95), steps=25, _return=True)
    assert res["verdict"] == "SKIPPED_NO_TORCH" or "+" in res["verdict"]
    assert "per_rho" in res
