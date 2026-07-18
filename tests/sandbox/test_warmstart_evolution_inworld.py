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
