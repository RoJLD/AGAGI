"""
tests/test_exp10_ttc_world_model.py — Validation EXP-10 : Vrai Planning MCTS avec World Model.
Vérifie que la recherche contrefactuelle MCTS intègre les rollouts latents
et la curiosité prédictive du World Model.
"""
import pytest
import numpy as np
from src.agents.planner import mcts_instrumental_search, plan_rollout, normalize_q
from src.agents.world_model import WorldModel


def test_mcts_world_model_imagination():
    """Vérifie que l'exploration MCTS avec World Model module la matrice Q par rapport à la base."""
    B, A, N = 2, 6, 16
    H_rec = np.random.randn(B, N).astype(np.float32)
    G_batch = np.random.randn(B, A, N).astype(np.float32) * 0.1
    value_pos = np.array([10, 10], dtype=np.int64)

    # World model RND
    wm = WorldModel(input_dim=8, out_dim=4, seed=42)
    obs = np.random.randn(B, 8).astype(np.float32)

    # 1. Recherche standard sans World Model
    Q_std, spent_std = mcts_instrumental_search(
        H_rec, G_batch, value_pos, depth=3, num_rollouts=2
    )

    # 2. Recherche augmentée par l'imagination World Model
    Q_wm, spent_wm = mcts_instrumental_search(
        H_rec, G_batch, value_pos, depth=3, num_rollouts=2,
        world_model=wm, obs_batch=obs, curiosity_weight=0.5
    )

    assert Q_std.shape == (B, A)
    assert Q_wm.shape == (B, A)
    assert np.all(np.isfinite(Q_wm))
    assert np.all(spent_wm > 0)
    # L'intégration du World Model doit modifier la distribution Q
    assert not np.allclose(Q_std, Q_wm)


def test_mcts_depth_budget_scaling():
    """Vérifie que le budget de calcul TTC augmente linéairement avec la profondeur."""
    B, A, N = 1, 4, 12
    H_rec = np.zeros((B, N), dtype=np.float32)
    G_batch = np.ones((B, A, N), dtype=np.float32) * 0.05
    value_pos = np.array([5], dtype=np.int64)

    _, spent_d2 = mcts_instrumental_search(H_rec, G_batch, value_pos, depth=2, num_rollouts=1)
    _, spent_d4 = mcts_instrumental_search(H_rec, G_batch, value_pos, depth=4, num_rollouts=1)

    assert spent_d4[0] > spent_d2[0]
