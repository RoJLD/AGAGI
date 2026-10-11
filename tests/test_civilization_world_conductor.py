"""
tests/test_civilization_world_conductor.py — Tests TDD pour l'Orchestrateur Civilisationnel Multi-Mondes.
Arc 13 : Jalon M28 (CivilizationWorldConductor).

Vérifie l'intégration synchrone des 3 mondes physiques (Stoneage, Agricole, Industriel)
avec les agents incarnés pilotés par fondation, consensus BFT Weiszfeld et recherche MCTS continue.
Conforme aux 12 Commandements AGIseed (Modulaire, Haute Performance, Stabilité Numérique).
"""

import pytest
import numpy as np

from src.worlds.civilization_world_conductor import (
    CivilizationWorldConductor,
    CivilizationConductorConfig,
)
from src.agents.embodied_foundation_agent import EmbodiedFoundationAgent, EmbodiedAgentConfig


def test_conductor_initialization():
    """Vérifie l'instanciation correcte des 3 mondes et des sous-systèmes cognitifs."""
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
    )
    conductor = CivilizationWorldConductor(cfg)

    assert conductor.world_stone is not None
    assert conductor.world_agri is not None
    assert conductor.world_indus is not None
    assert conductor.encoder is not None
    assert conductor.consensus_module is not None
    assert conductor.mcts_searcher is not None
    assert conductor.critic is not None
    assert conductor.step_count == 0


def test_conductor_agent_population():
    """Vérifie le peuplement d'agents incarnés dans les 3 mondes."""
    cfg = CivilizationConductorConfig(latent_dim=64, world_size=10)
    conductor = CivilizationWorldConductor(cfg)

    # Peupler chaque monde avec des agents incarnés
    conductor.populate_world(world_id="stoneage", count=3, energy=60.0)
    conductor.populate_world(world_id="agricultural", count=3, energy=60.0)
    conductor.populate_world(world_id="industrial", count=3, energy=60.0)

    assert len(conductor.world_stone.agents) == 3
    assert len(conductor.world_agri.agents) == 3
    assert len(conductor.world_indus.agents) == 3

    # Vérifier que les contrôleurs sont bien des EmbodiedFoundationAgent
    for ag in conductor.world_stone.agents:
        assert isinstance(ag["model"], EmbodiedFoundationAgent)


def test_conductor_synchronous_step():
    """Vérifie l'exécution d'un pas complet de synchronisation civilisationnelle."""
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
    )
    conductor = CivilizationWorldConductor(cfg)
    conductor.populate_world(world_id="stoneage", count=2, energy=50.0)
    conductor.populate_world(world_id="agricultural", count=2, energy=50.0)
    conductor.populate_world(world_id="industrial", count=2, energy=50.0)

    metrics = conductor.step_civilization()

    assert conductor.step_count == 1
    assert "civilization_consensus_norm" in metrics
    assert pytest.approx(metrics["civilization_consensus_norm"], abs=1e-3) == 1.0
    assert "stoneage_population" in metrics
    assert "agricultural_population" in metrics
    assert "industrial_population" in metrics
    assert "critic_energy" in metrics
    assert metrics["critic_energy"] <= 0.20


def test_conductor_inter_world_trade_transfers():
    """Vérifie le mécanisme de transfert de ressources et de surplus inter-mondes."""
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_inter_world_trade=True,
    )
    conductor = CivilizationWorldConductor(cfg)
    conductor.populate_world(world_id="stoneage", count=2, energy=15.0)  # En détresse
    conductor.populate_world(world_id="agricultural", count=2, energy=80.0) # Abondance
    conductor.populate_world(world_id="industrial", count=2, energy=50.0)

    # Assurer que le grenier agricole possède des réserves
    conductor.world_agri.granary_reserves = 50.0

    trade_events = conductor.execute_inter_world_trade()

    assert len(trade_events) > 0
    # Le monde en détresse a dû recevoir de l'aide calorique
    stone_agent = conductor.world_stone.agents[0]
    assert stone_agent["energy"] > 15.0


def test_conductor_multi_step_stability():
    """Vérifie la stabilité numérique sur 5 pas successifs sans NaN/Inf."""
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
    )
    conductor = CivilizationWorldConductor(cfg)
    conductor.populate_world("stoneage", 2, 50.0)
    conductor.populate_world("agricultural", 2, 50.0)
    conductor.populate_world("industrial", 2, 50.0)

    for _ in range(5):
        m = conductor.step_civilization()
        assert not np.isnan(m["mean_energy"])
        assert not np.isinf(m["mean_energy"])

    assert conductor.step_count == 5
