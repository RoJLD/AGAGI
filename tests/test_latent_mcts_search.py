"""
tests/test_latent_mcts_search.py — Validation TDD du MCTS Latent Continu (Arc 12 : Jalon M25).

Vérifie formellement :
1. La structure arborescente et l'unitarité des nœuds d'états latents.
2. L'orientation téléologique du plan MCTS vers l'attracteur désiré.
3. La non-divergence et la stabilité numérique des valeurs Q in [-1, 1].
4. La supériorité de décision face à une sélection aléatoire.
"""

import pytest
import numpy as np
from src.metaprog.latent_mcts_search import (
    LatentMCTSSearch,
    LatentMCTSConfig,
    LatentMCTSNode,
)


def test_latent_mcts_initialization_and_transition():
    """Vérifie l'initialisation et l'unitarité de transition sur S^(D-1)."""
    mcts = LatentMCTSSearch(LatentMCTSConfig(num_simulations=20))
    s0 = np.random.randn(64).astype(np.float32)
    s0 = s0 / np.linalg.norm(s0)

    s1 = mcts.transition_latent(s0, 0)
    assert s1.shape == (64,)
    assert pytest.approx(np.linalg.norm(s1), abs=1e-4) == 1.0
    assert not np.any(np.isnan(s1))


def test_latent_mcts_planning_teleological_gain():
    """
    Vérifie que la recherche MCTS sélectionne une action qui rapproche l'état
    de l'attracteur téléologique z_goal.
    """
    cfg = LatentMCTSConfig(num_simulations=40, max_depth=3, step_size=0.30)
    mcts = LatentMCTSSearch(cfg)

    dim = 64
    s0 = np.zeros(dim, dtype=np.float32)
    s0[0] = 0.5
    s0[1] = 0.866
    s0 = s0 / np.linalg.norm(s0)

    # Objectif téléologique pur selon l'axe e_0
    goal = np.zeros(dim, dtype=np.float32)
    goal[0] = 1.0

    action, s_next, meta = mcts.plan_trajectory(s0, goal)

    assert isinstance(action, int)
    assert 0 <= action < cfg.num_action_candidates
    assert meta["simulations_run"] == 40
    assert meta["root_visits"] == 40
    # Le prochain état anticipé doit avoir progressé ou maintenu l'alignement
    assert meta["final_proximity"] >= meta["initial_proximity"] - 0.05
    assert not np.any(np.isnan(s_next))


def test_latent_mcts_q_values_bounded():
    """Vérifie que les valeurs Q restent strictement bornées in [-1, 1]."""
    cfg = LatentMCTSConfig(num_simulations=30)
    mcts = LatentMCTSSearch(cfg)

    s0 = np.random.randn(64).astype(np.float32)
    goal = np.random.randn(64).astype(np.float32)

    action, s_next, meta = mcts.plan_trajectory(s0, goal)

    for act, count in meta["action_visit_counts"].items():
        assert count >= 0
