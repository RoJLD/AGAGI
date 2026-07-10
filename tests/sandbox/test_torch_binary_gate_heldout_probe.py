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
