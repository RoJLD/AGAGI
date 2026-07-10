import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_arm_smoke_keys_and_bounds():
    from tools.torch_throw_gate_inworld_ab import run_arm
    r = run_arm(shuffle=False, seed=0, ticks=40, warmup=20, n_agents=8)
    for k in ("shuffle", "seed", "binding_gap_inworld", "kills_with_tool",
              "spear_n", "nospear_n", "throw_rate"):
        assert k in r
    assert -1.0 <= r["binding_gap_inworld"] <= 1.0
    assert 0.0 <= r["throw_rate"] <= 1.0
    assert r["kills_with_tool"] >= 0


def test_verdict_pure_true_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.30}, {"diff": 0.25}, {"diff": 0.40}]   # gap ON - gap SHUFFLE > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
