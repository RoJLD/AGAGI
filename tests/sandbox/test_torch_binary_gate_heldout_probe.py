import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_arm_smoke_true_and_shuffle():
    from tools.torch_binary_gate_heldout_probe import run_arm
    r_true = run_arm(shuffle_reward=False, train_ep=80, test_ep=30, n_agents=32, seed=0)
    r_shuf = run_arm(shuffle_reward=True, train_ep=80, test_ep=30, n_agents=32, seed=0)
    for r in (r_true, r_shuf):
        assert set(["shuffle_reward", "binding_gap_heldout", "comp_rate_heldout", "throw_rate_heldout"]).issubset(r)
        assert -1.0 <= r["binding_gap_heldout"] <= 1.0
        assert 0.0 <= r["throw_rate_heldout"] <= 1.0


def test_verdict_pure_true_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": d} for d in (0.60, 0.70, 0.55, 0.62, 0.58, 0.66)]   # gap ON - gap SHUFFLE > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 6
