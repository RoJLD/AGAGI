"""Smoke de FORME de la sonde Lewis DIFFÉRÉE (DELAYED-COORD, Task 2).

Ne teste PAS la science (c'est le crible fail-fast + la calibration de Task 3 qui le font) : seulement
que les deux bras tournent, renvoient des accuracies bornées et exposent `_params`.
"""
import pytest

pytest.importorskip("torch")


def test_probe_returns_both_arms_smoke():
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe
    r = run_delayed_coordination_demand_probe(seeds=[0, 1], D=1, episodes=30, n_agents=4, K=6, V=8)
    for arm in ("RETAIN", "PRESENT"):
        assert len(r[arm + "_intact"]) == 2, r
        assert len(r[arm + "_ablated"]) == 2, r
        for v in r[arm + "_intact"] + r[arm + "_ablated"]:
            assert 0.0 <= v <= 1.0, r
    assert r["n"] == 2
    assert r["_params"]["D"] == 1
