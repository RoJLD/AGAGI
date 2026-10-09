"""
tests/test_world_lu_integration.py — Validation de l'intégration in-world de la branche LU (Langage Ultime).

Commandements AGIseed :
7. Validation Rigoureuse (Test-Driven) : Couverture 100% des cas d'activation et de non-régression.
9. Stabilité Numérique : Pas de NaN, pas d'Inf, préservation des normes unitaires.
15. Non-Régression Bit-Exacte : Si enable_lu_communication=False, comportement legacy intact.
"""

import pytest
import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _create_agent(world, x=5, y=5, energy=50.0):
    agent_model = MambaAgent(
        num_inputs=world.config.agent.num_inputs,
        num_outputs=world.config.agent.num_outputs,
        num_nodes=world.config.agent.num_nodes,
    )
    world.add_agent(agent_model, x=x, y=y, energy=energy)
    return world.agents[-1]


def test_lu_inworld_disabled_by_default():
    """Vérifie la non-régression stricte : LU est désactivé par défaut."""
    cfg = WorldConfig()
    assert cfg.enable_lu_communication is False

    world = Biosphere3D(cfg)
    assert world.enable_lu_communication is False
    assert world.lu_adapter is None

    _create_agent(world, 5, 5)
    _create_agent(world, 6, 5)
    
    # Doit s'exécuter sans erreur
    world.step()
    assert world.ticks == 1
    assert "lu_latent" not in world.agents[0]


def test_lu_inworld_enabled_lifecycle():
    """Vérifie le cycle de vie complet de la communication continue LU in-world."""
    cfg = WorldConfig(
        enable_lu_communication=True,
        lu_latent_dim=16,
        lu_hear_radius=4,
        lu_noise_level=0.02,
        lu_alignment_reward=1.0,
        lu_referential_bonus=2.0
    )
    world = Biosphere3D(cfg)
    assert world.enable_lu_communication is True
    assert world.lu_adapter is not None

    # Créer deux agents voisins
    a1 = _create_agent(world, x=4, y=4, energy=50.0)
    a2 = _create_agent(world, x=5, y=4, energy=50.0)

    # Créer une proie proche pour induire de la sémantique
    world.preys = [{"x": 6, "y": 4, "type": "Mammouth", "stunned": 0, "hp": 100.0}]

    world.step()

    # Vérification des Gigatokens générés
    assert "lu_latent" in a1
    assert "lu_latent" in a2
    z1 = a1["lu_latent"]
    z2 = a2["lu_latent"]
    assert z1.shape == (16,)
    assert z2.shape == (16,)
    assert np.all(np.isfinite(z1))
    assert np.all(np.isfinite(z2))
    assert abs(np.linalg.norm(z1) - 1.0) < 1e-4

    # Vérification des métriques de l'adaptateur
    metrics = world.lu_adapter.step()
    assert metrics["transmissions"] >= 1
    assert world.lu_adapter.total_transmissions >= 1


def test_lu_inworld_steer_action():
    """Vérifie que le biais de steering latent guide l'orientation de mouvement."""
    cfg = WorldConfig(enable_lu_communication=True, lu_latent_dim=16)
    world = Biosphere3D(cfg)

    agent = {"id": "test_agent", "x": 5, "y": 5}
    
    # Biais vers l'Est (dx > 0) -> action 2
    agent["lu_steer_bias"] = (0.8, 0.0)
    action = world._lu_steer_action(agent, 0)
    assert action == 2

    # Biais vers le Sud (dy > 0) -> action 1
    agent["lu_steer_bias"] = (0.0, 0.9)
    action = world._lu_steer_action(agent, 0)
    assert action == 1


def test_lu_inworld_explainer():
    """Vérifie l'explicabilité en langage naturel des Gigatokens d'agents vivants."""
    cfg = WorldConfig(enable_lu_communication=True, lu_latent_dim=16)
    world = Biosphere3D(cfg)
    a = _create_agent(world, x=3, y=3)
    
    world.step()
    explanation_fr = world.lu_adapter.explain_agent_thought(a, lang="fr")
    assert isinstance(explanation_fr, str)
    assert len(explanation_fr) > 0
    assert "Concept Latent" in explanation_fr or "Vecteur" in explanation_fr or "Énergie" in explanation_fr or "Gigatoken" in explanation_fr or "Dim" in explanation_fr


def test_lu_inworld_hgt_transmission():
    """Vérifie l'héritage horizontal et vertical des matrices de projection latente."""
    cfg = WorldConfig(enable_lu_communication=True, lu_latent_dim=16)
    world = Biosphere3D(cfg)

    p1 = _create_agent(world, x=5, y=5, energy=70.0)
    p2 = _create_agent(world, x=5, y=5, energy=70.0)

    # Forcer la création de leurs projections
    proj_p1 = world.lu_adapter._get_agent_projection(p1["id"], 8)
    proj_p2 = world.lu_adapter._get_agent_projection(p2["id"], 8)

    # Simuler la transmission HGT vers un enfant
    child_id = "child_123"
    child_proj = world.lu_adapter.inherit_latent_traits(child_id, p1["id"], p2["id"], input_dim=8)

    assert child_proj.shape == (8, 16)
    assert np.all(np.isfinite(child_proj))
    assert child_id in world.lu_adapter.agent_projections

    # Vérification de la transmission par surprise HGT
    world.lu_adapter.absorb_latent_knowledge(p1["id"], p2["id"], alpha=0.3, input_dim=8)
    updated_p1 = world.lu_adapter._get_agent_projection(p1["id"], 8)
    assert updated_p1.shape == (8, 16)
    assert np.all(np.isfinite(updated_p1))

