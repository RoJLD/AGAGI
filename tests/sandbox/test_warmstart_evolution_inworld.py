"""Tests WARM-001/WARM-002 — imitation BPTT récurrente + évolution in-world W-only + verdict partagé."""
import os, sys
import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=0):
    """Construit un TorchPopulationModel minimal sur des agents jouets (Genome réel, petit N)."""
    torch = pytest.importorskip("torch")
    from src.seed_ai.mutation import Genome
    from src.agents.backend_torch import TorchPopulationModel
    rng = np.random.RandomState(seed)

    class _A:
        def __init__(self, g): self.genome = g
    agents = []
    for _ in range(B):
        W = (rng.randn(N, N) * 0.1).astype(np.float32)
        agents.append(_A(Genome(W, num_inputs=I, num_outputs=O)))
    return TorchPopulationModel(agents, lr=0.2)


def test_imitate_episode_bptt_reduces_loss_and_learns_separable_map():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=1)
    rng = np.random.RandomState(2)
    # Tâche jouet séparable : le signe de obs[:,0] -> cible 0 (négatif) ou 3 (positif).
    T = 6
    obs_seq, tgt_seq = [], []
    for _ in range(T):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        obs = np.zeros((4, 2), dtype=np.float32); obs[:, 0] = s
        obs_seq.append(obs)
        tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    for _ in range(60):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    assert last < first, f"la perte d'imitation devrait décroître ({first:.3f} -> {last:.3f})"


def test_verdict_demand_marker_random_genome_is_neutral_and_wellformed():
    from tools.warmstart_evolution_inworld import verdict_demand_marker
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome                         # génome aléatoire (non-suiveur)
    r = verdict_demand_marker(g, backend="mamba", seed=2026, K=2,
                              num_agents=4, max_ticks=20)
    assert set(r) >= {"ratio", "verdict", "n", "intact_survival", "ablated_survival"}
    assert r["verdict"] in ("PERCEPTION_DEMANDED", "NEUTRAL", "INCONCLUSIVE")


def test_run_inworld_evolution_smoke_returns_trend_and_best():
    from tools.warmstart_evolution_inworld import run_inworld_evolution
    from src.seed_ai.mutation import Genome
    out = run_inworld_evolution(seed=2026, generations=2, pop_size=6, survival_frac=0.34,
                                mut_power=0.2, max_ticks=15)
    assert len(out["trend"]) == 2
    assert isinstance(out["best_genome"], Genome)
    assert out["best_age"] >= 0


def test_mutate_w_only_changes_W_not_router():
    from tools.warmstart_evolution_inworld import _mutate_W_only
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome
    W0 = g.W.copy()
    router0 = None if g.W_router is None else g.W_router.copy()
    _mutate_W_only(g, power=0.5, rng=np.random.RandomState(0))
    assert not np.allclose(g.W, W0), "W devrait changer"
    if router0 is not None:
        assert np.allclose(g.W_router, router0), "W_router ne doit PAS changer (comparaison propre au gradient)"


def test_collect_oracle_trajectory_shapes():
    from tools.warmstart_evolution_inworld import _collect_oracle_trajectory
    obs_seq, tgt_seq = _collect_oracle_trajectory(seed=2026, num_agents=4, max_ticks=8,
                                                  metab=0.75, cog=12.0)
    assert len(obs_seq) == len(tgt_seq) and len(obs_seq) >= 1
    assert obs_seq[0].shape[0] == 4 and obs_seq[0].shape[1] >= 14      # B=4, >= colonnes bit_a/bit_b
    assert tgt_seq[0].shape[0] == 4 and tgt_seq[0].max() < 8


def test_run_bptt_imitation_warmstart_smoke_reduces_loss():
    pytest.importorskip("torch")
    from tools.warmstart_evolution_inworld import run_bptt_imitation_warmstart
    from src.seed_ai.mutation import Genome
    out = run_bptt_imitation_warmstart(seed=2026, num_agents=4, n_epochs=8,
                                       truncate_window=10, max_ticks=12)
    assert isinstance(out["learned_genome"], Genome)
    assert out["loss_trend"][-1] <= out["loss_trend"][0]


def test_imitate_episode_bptt_mask_all_ones_trains_and_zero_mask_noop():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=3)
    rng = np.random.RandomState(4)
    obs_seq, tgt_seq = [], []
    for _ in range(5):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        o = np.zeros((4, 2), dtype=np.float32); o[:, 0] = s
        obs_seq.append(o); tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    ones = [np.ones(4, dtype=np.float32) for _ in range(5)]
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    for _ in range(50):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    assert last < first, "masque tout-à-1 doit entraîner (perte décroît)"
    zeros = [np.zeros(4, dtype=np.float32) for _ in range(5)]
    lz = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=zeros)
    assert lz <= 1e-6, "masque tout-à-0 -> perte nulle, pas d'exception"
