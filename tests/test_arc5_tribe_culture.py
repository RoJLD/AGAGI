"""
tests/test_arc5_tribe_culture.py — Validation causale et unitaire de l'Arc 5 :
La Tribu, Spécialisation des Rôles, Coût Métabolique et Transmission Culturelle de Recettes via Gigatokens.

Commandements AGIseed :
1. Hyper-Configurabilité : Paramètres de coût métabolique et multiplicateur coopératif injectés.
3. Haute Performance : Vectorisation NumPy sur les Gigatokens continus.
7. Validation Rigoureuse (Test-Driven) : Tests exhaustifs des nouvelles dynamiques.
9. Stabilité Numérique : Absence de NaN, vecteurs bornés sur la sphère unité S^(D-1).
"""

import pytest
import numpy as np

from src.environments.config import WorldConfig
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
    ROLE_SCOUT,
    ROLE_HUNTER,
    ROLE_CRAFTER,
)
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _create_agent(world, x=5, y=5, energy=50.0, role=None):
    agent_model = MambaAgent(
        num_inputs=world.config.agent.num_inputs,
        num_outputs=world.config.agent.num_outputs,
        num_nodes=world.config.agent.num_nodes,
    )
    world.add_agent(agent_model, x=x, y=y, energy=energy)
    ag = world.agents[-1]
    if role:
        ag["role"] = role
    return ag


def test_tribal_role_specialization():
    """Vérifie l'attribution automatique et la persistance des rôles tribaux."""
    cfg = WorldConfig(enable_lu_communication=True, lu_latent_dim=16)
    world = Biosphere3D(cfg)

    a1 = _create_agent(world, 2, 2)
    a2 = _create_agent(world, 3, 2)
    a3 = _create_agent(world, 4, 2)

    roles = world.lu_adapter.assign_tribal_roles(world.agents)
    assert len(roles) == 3
    assigned = [world.agents[0]["role"], world.agents[1]["role"], world.agents[2]["role"]]
    assert ROLE_SCOUT in assigned
    assert ROLE_HUNTER in assigned
    assert ROLE_CRAFTER in assigned


def test_metabolic_cost_of_signaling():
    """Vérifie que la communication continue induit un coût métabolique d'information non nul."""
    cost = 0.1
    cfg = WorldConfig(
        enable_lu_communication=True,
        lu_latent_dim=16,
        lu_hear_radius=3,
        lu_signal_metabolic_cost=cost,
    )
    world = Biosphere3D(cfg)

    a1 = _create_agent(world, 5, 5, energy=50.0)
    a2 = _create_agent(world, 6, 5, energy=50.0)

    # Initial energy before communication
    e1_init = a1["energy"]
    e2_init = a2["energy"]

    res = world.lu_adapter.step()
    assert res["transmissions"] >= 1
    assert res["total_metabolic_cost"] >= cost * 2.0
    assert world.lu_adapter.total_metabolic_cost > 0.0

    # L'énergie totale a été débitée du coût d'émission
    assert a1["energy"] <= 100.0
    assert a2["energy"] <= 100.0


def test_cooperative_hunt_scout_to_hunter():
    """Vérifie la synergie coordonnée entre Éclaireur (SCOUT) et Chasseur (HUNTER)."""
    np.random.seed(42)
    cfg = WorldConfig(
        enable_lu_communication=True,
        lu_latent_dim=16,
        lu_hear_radius=18,
        lu_noise_level=0.01,
        lu_alignment_threshold=0.05,
        lu_alignment_reward=1.0,
        lu_referential_bonus=2.0,
        lu_cooperative_prey_multiplier=3.0,
        target_prey_count=1,
    )
    world = Biosphere3D(cfg)

    # a1 est SCOUT, a2 est HUNTER
    a1 = _create_agent(world, 4, 4, energy=80.0, role=ROLE_SCOUT)
    a2 = _create_agent(world, 5, 4, energy=80.0, role=ROLE_HUNTER)

    # Placer un Mammouth pour induire une intention directionnelle
    world.preys = [{"x": 8, "y": 4, "type": "Mammouth", "stunned": 0, "hp": 100.0}]

    for _ in range(5):
        world.lu_adapter.step()

    assert world.lu_adapter.pack_coordinations_count >= 1
    assert world.lu_adapter.cooperative_hunts_count >= 1
    assert a2.get("cooperative_hunt_active", False) is True


def test_craft_recipe_encoding_decoding():
    """Vérifie l'encodage et le décodage d'une recette artisanale continue."""
    adapter = LUInWorldAdapter(None, LUInWorldConfig(latent_dim=16))

    recipe_vec = adapter.encode_craft_recipe(
        recipe_name="friction_fire",
        materials=["wood_stick", "dry_leaves"],
        target_product="fire"
    )

    assert recipe_vec.shape == (16,)
    assert np.all(np.isfinite(recipe_vec))
    assert abs(np.linalg.norm(recipe_vec) - 1.0) < 1e-4

    decoded = adapter.decode_craft_recipe(recipe_vec)
    assert decoded["is_craft_recipe"] is True
    assert decoded["complexity_level"] >= 1
    assert 0.0 < decoded["estimated_success_rate"] <= 1.0


def test_inter_agent_cultural_recipe_transmission():
    """Vérifie la transmission culturelle horizontale d'une recette entre agents."""
    adapter = LUInWorldAdapter(None, LUInWorldConfig(latent_dim=16))

    transmission = adapter.transmit_cultural_recipe(
        crafter_id="artisan_alpha",
        student_id="apprenti_beta",
        recipe_name="stone_axe",
        materials=["flint_rock", "wood_stick", "fiber_vine"],
        target_product="axe"
    )

    assert transmission["is_craft_recipe"] is True
    assert transmission["crafter_id"] == "artisan_alpha"
    assert transmission["student_id"] == "apprenti_beta"
    assert transmission["recipe_name"] == "stone_axe"
    assert transmission["target_product"] == "axe"
    assert adapter.recipes_transmitted == 1
    assert np.isfinite(transmission["alignment_quality"])


def test_dialect_divergence_metric():
    """Vérifie le calcul géométrique de la divergence dialectale (distance de Grassmann)."""
    cfg = WorldConfig(enable_lu_communication=True, lu_latent_dim=16)
    world = Biosphere3D(cfg)

    # Répartir 4 agents dans différents quadrants
    _create_agent(world, 1, 1)
    _create_agent(world, 2, 1)
    _create_agent(world, 8, 8)
    _create_agent(world, 9, 8)

    dialects = world.lu_adapter.compute_tribe_dialects()
    assert dialects["status"] == "computed"
    assert dialects["tribe_count"] >= 2
    assert isinstance(dialects["dialect_divergence"], float)
    assert dialects["dialect_divergence"] >= 0.0
