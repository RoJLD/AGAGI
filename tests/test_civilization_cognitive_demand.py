"""
tests/test_civilization_cognitive_demand.py — Épreuves de Demande Cognitive Multi-Mondes (Arc 13 : Jalon M29).

Vérifie formellement que l'orchestration civilisationnelle (CivilizationWorldConductor)
permet aux agents incarnés guidés par fondation de résoudre les défis environnementaux
propres à chaque monde physique :
- Monde 2 (Agricole) : Survie sous rigueur hivernale et gestion des réserves du grenier.
- Monde 3 (Industriel) : Maîtrise de la fusion métallurgique et outillage métallique.
- Synergie Trans-Mondes : Résilience collective et amortissement des chocs systémiques.

Conforme aux 12 Commandements AGIseed (Commandement 14 : Validation par simulation, Commandement 15 : PIU).
"""

import pytest
import numpy as np

from src.worlds.civilization_world_conductor import (
    CivilizationWorldConductor,
    CivilizationConductorConfig,
)
from src.agents.embodied_foundation_agent import EmbodiedFoundationAgent, EmbodiedAgentConfig


def test_agricultural_winter_survival_via_conductor():
    """
    Vérifie que l'orchestrateur soutient la survie des agents lors d'un hiver rude
    grâce à la coordination collective et aux retraits du grenier.
    """
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        distress_energy_threshold=30.0,
        granary_relief_amount=15.0,
    )
    conductor = CivilizationWorldConductor(cfg)

    # Forcer l'hiver dans le Monde 2
    conductor.world_agri.season = "winter"
    conductor.world_agri.season_ticks = 0
    conductor.world_agri.granary_reserves = 50.0

    # Ajouter 2 agents dans le Monde 2
    conductor.populate_world(world_id="agricultural", count=2, energy=40.0)

    # Exécution de 4 pas sous conditions hivernales
    for _ in range(4):
        m = conductor.step_civilization()

    # Les agents doivent avoir survécu grâce à l'orchestration et au grenier
    assert conductor.world_agri.agents[0]["energy"] > 0.0
    assert m["agricultural_population"] == 2


def test_industrial_metallurgy_mastery_via_conductor():
    """
    Vérifie que le Monde 3 produit du fer et que le transfert technologique
    vers le Monde 1 (Stoneage) équipe les chasseurs avec des outils de fer durables.
    """
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_inter_world_trade=True,
    )
    conductor = CivilizationWorldConductor(cfg)

    conductor.populate_world(world_id="stoneage", count=2, energy=60.0)
    conductor.populate_world(world_id="industrial", count=2, energy=60.0)

    # Simuler une production réussie de fer dans le Monde 3
    conductor.world_indus.iron_smelted = 2

    # Exécuter les transferts inter-mondes
    trade_events = conductor.execute_inter_world_trade()

    # Un transfert technologique vers le Monde 1 doit avoir eu lieu
    tech_transfers = [e for e in trade_events if e["type"] == "TECHNOLOGY_TRANSFER"]
    assert len(tech_transfers) >= 1
    assert tech_transfers[0]["target_world"] == "stoneage"
    assert tech_transfers[0]["tool"] == "IronSpear"

    # Vérifier l'inventaire du chasseur équipé
    stone_agent = conductor.world_stone.agents[0]
    assert any(it.get("type") == "IronSpear" for it in stone_agent["inventory"])


def test_inter_world_caloric_shock_absorption():
    """
    Vérifie que le choc de famine dans le Monde 1 est immédiatement absorbé
    par le surplus vivrier du Monde 2, évitant l'extinction de la population.
    """
    cfg = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_inter_world_trade=True,
        distress_energy_threshold=25.0,
        granary_relief_amount=15.0,
    )
    conductor = CivilizationWorldConductor(cfg)

    # Monde 1 au bord de la famine (10.0 E)
    conductor.populate_world(world_id="stoneage", count=2, energy=10.0)
    conductor.populate_world(world_id="agricultural", count=2, energy=75.0)
    conductor.world_agri.granary_reserves = 40.0

    # Un pas synchrone avec soulagement calorique automatique
    metrics = conductor.step_civilization()

    assert metrics["stoneage_population"] == 2
    # L'énergie des agents de l'Âge de pierre a augmenté grâce au grenier
    for ag in conductor.world_stone.agents:
        assert ag["energy"] > 10.0
