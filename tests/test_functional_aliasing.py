import numpy as np


def _settle(genome, x, y, ticks=4):
    """Fait tourner recurrent_forward `ticks` fois en rebouclant H ; renvoie preds (O,) = [out_X, out_Y]."""
    from src.seed_ai.rl_evolution import recurrent_forward
    N = genome.num_nodes
    H = np.zeros((1, N), dtype=np.float32)
    Hh = np.zeros((1, 1, N), dtype=np.float32)
    Hp = np.zeros((1, N), dtype=np.float32)
    obs = np.array([[x, y]], dtype=np.float32)
    preds = None
    for _ in range(ticks):
        preds, H, Hh, Hp, _ = recurrent_forward(genome, obs, H, Hh, Hp, 0.0)
    return preds[0].copy()


def test_genome_layout_and_capabilities_respond():
    from tools.ground_truth_worlds import make_aliasing_genome
    g = make_aliasing_genome(0.0)
    assert g.num_nodes == 7 and g.num_inputs == 2 and g.num_outputs == 2
    on = _settle(g, 1.0, 1.0)
    x_off = _settle(g, 0.0, 1.0)
    y_off = _settle(g, 1.0, 0.0)
    assert abs(on[0] - x_off[0]) > 0.1, "out_X doit répondre à X (métrique vivante)"
    assert abs(on[1] - y_off[1]) > 0.1, "out_Y doit répondre à Y (métrique vivante)"


def test_disjoint_is_exact_noop_on_control_output():
    from tools.ground_truth_worlds import make_aliasing_genome
    g = make_aliasing_genome(0.0)
    intact = _settle(g, 1.0, 1.0)
    ablated = _settle(g, 0.0, 1.0)          # X ablaté (entrée 0 = 0)
    assert intact[1] == ablated[1], "α=0 : out_Y doit être BIT-IDENTIQUE (no-op exact)"
    assert abs(intact[0] - ablated[0]) > 0.1, "…mais out_X (capacité propre de X) DOIT chuter"


def test_shared_leaks_and_is_monotone_in_alpha():
    from tools.ground_truth_worlds import make_aliasing_genome
    leaks = []
    for alpha in (0.0, 0.3, 0.6, 1.0):
        g = make_aliasing_genome(alpha)
        leaks.append(abs(_settle(g, 1.0, 1.0)[1] - _settle(g, 0.0, 1.0)[1]))
    assert leaks[0] == 0.0, f"α=0 doit être un no-op exact : {leaks}"
    assert leaks == sorted(leaks) and leaks[-1] > leaks[0], f"fuite non monotone : {leaks}"
    assert leaks[-1] > 0.1, f"α=1 doit fuir nettement : {leaks[-1]}"
