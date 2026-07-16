from tools.memory_credit_horizon import (train_arm, _verdict_horizon, main_credit_horizon)


def test_train_arm_dispatch_deterministic():
    a = train_arm("mutation", N=10, K=1, D=0, epochs=30, seed=5)
    b = train_arm("mutation", N=10, K=1, D=0, epochs=30, seed=5)
    assert a == b
    c = train_arm("bptt", N=12, K=1, D=0, epochs=30, seed=5)
    assert 0.0 <= c <= 1.0


def test_train_arm_rejects_unknown():
    import pytest
    with pytest.raises(ValueError):
        train_arm("nope", N=10, K=1, D=0, epochs=1, seed=0)


def test_verdict_horizon_branches():
    confirme = ({1: 0.95, 24: 0.95}, {1: 0.90, 24: 0.65})   # gap 0.05 -> 0.30 (delta 0.25) ; D=24 separe
    assert _verdict_horizon(*confirme) == "HORIZON CONFIRME"
    refute = ({1: 0.95, 24: 0.95}, {1: 0.90, 24: 0.85})      # gap 0.05 -> 0.10 (delta 0.05)
    assert _verdict_horizon(*refute) == "HORIZON REFUTE"
    assert _verdict_horizon({1: 0.9}, {}) == "INDETERMINE"


def test_main_credit_horizon_smoke():
    r = main_credit_horizon(K=1, Ds=(1, 6), R=1, epochs=20, seed=99167, _return=True)
    assert r["verdict"] in ("HORIZON CONFIRME", "HORIZON REFUTE", "INDETERMINE")
    assert len(r["table"]) == 2   # 2 valeurs de D
