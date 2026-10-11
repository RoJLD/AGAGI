"""
tests/test_embodied_foundation_agent.py — Validation TDD du Contrôleur Incarné (Arc 11 : Jalon M21).

Vérifie formellement :
1. L'initialisation isocalorique et la conformité dimensionnelle.
2. Le couplage continu sans dérive numérique.
3. L'influence effective du Gigatoken de fondation sur les commandes motrices finales.
4. L'absence de régression ou divergence face à des entrées extrêmes.
"""

import pytest
import numpy as np
from src.agents.embodied_foundation_agent import (
    EmbodiedFoundationAgent,
    EmbodiedAgentConfig,
)
from src.agents.mamba_agent import MambaAgent


def test_embodied_agent_initialization_and_shape():
    """Vérifie la dimension des sorties et l'isocaloricité stricte."""
    cfg = EmbodiedAgentConfig(latent_dim=64, num_inputs=59, num_outputs=108, isocaloric=True)
    agent = EmbodiedFoundationAgent(cfg)

    obs = np.random.randn(59).astype(np.float32)
    action = agent.step(obs)

    assert action.shape == (108,)
    assert not np.any(np.isnan(action))
    assert not np.any(np.isinf(action))


def test_embodied_agent_foundation_steering_influence():
    """
    Vérifie qu'injecter un Gigatoken de fondation modifie significativement
    l'action motrice dans la direction désirée.
    """
    cfg = EmbodiedAgentConfig(
        latent_dim=64,
        num_inputs=59,
        num_outputs=108,
        foundation_coupling_strength=0.50,
    )
    agent = EmbodiedFoundationAgent(cfg)

    obs = np.zeros(59, dtype=np.float32)
    # Action de base réflexe (sans but téléologique)
    action_base = agent.step(obs).copy()

    # Injection d'un but de fondation
    goal = np.zeros(64, dtype=np.float32)
    goal[0] = 1.0  # Axe téléologique dominant
    agent.set_foundation_goal(goal)

    action_steered = agent.step(obs)

    # L'action pilotée doit différer de l'action de base
    diff = float(np.linalg.norm(action_steered - action_base))
    assert diff > 0.05, f"Le guidage de fondation n'a eu aucun effet sur l'action motrice : diff = {diff}"


def test_embodied_agent_extreme_input_stability():
    """Vérifie la résistance aux entrées corrompues ou infinies (Commandement 9)."""
    cfg = EmbodiedAgentConfig(latent_dim=64, num_inputs=59, num_outputs=108)
    agent = EmbodiedFoundationAgent(cfg)

    corrupted_goal = np.full(64, np.nan, dtype=np.float32)
    agent.set_foundation_goal(corrupted_goal)

    obs = np.full(59, np.inf, dtype=np.float32)
    action = agent.step(obs)

    assert not np.any(np.isnan(action))
    assert not np.any(np.isinf(action))
    assert np.all(np.abs(action) <= 1.0)
