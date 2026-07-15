import numpy as np

from src.seed_ai.s2_stats import verdict_cognition_body


def _cond(center, n=12, spread=4.0):
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era}


def test_verdict_cognition():
    # C(45) >> B(12) ; B(12) ~ R(12) -> la POLITIQUE porte la survie -> COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12))
    assert r["verdict"] == "COGNITION"
    assert r["policy_sig"] and not r["body_sig"]


def test_verdict_body():
    # C(45) ~ B(44) ; B(44) >> R(12) -> le CORPS/genome porte la survie -> BODY
    r = verdict_cognition_body(_cond(45), _cond(44), _cond(20), _cond(12))
    assert r["verdict"] == "BODY"
    assert r["body_sig"] and not r["policy_sig"]


def test_verdict_both():
    # C(45) >> B(28) >> R(12) -> corps ET politique -> BOTH
    r = verdict_cognition_body(_cond(45), _cond(28), _cond(20), _cond(12))
    assert r["verdict"] == "BOTH"
    assert r["policy_sig"] and r["body_sig"]


def test_verdict_neither():
    # C(20) ~ B(20) ~ R(20) -> aucun -> NEITHER
    r = verdict_cognition_body(_cond(20), _cond(20), _cond(20), _cond(20))
    assert r["verdict"] == "NEITHER"
