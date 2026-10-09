"""
tests/test_arc5_multiverse_roles.py — Validation causale de l'Arc 5 dans les Mondes Agricole et Industriel.
Vérifie la synergie des rôles tribaux (CRAFTER, HUNTER, SCOUT) :
1. En Monde 2 : Le Crafter/Hunter apporte du grain au grenier avec bonus de rendement (+50%).
2. En Monde 3 : Le Crafter maîtrise la forge, réduisant la pollution (-30%) et bonifiant les outils (+20%).
"""
import pytest
import numpy as np

from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.worlds.world_3_industrial import IndustrialWorld, IndustrialConfig
from src.agents.mamba_agent import MambaAgent


def test_agricultural_role_synergy():
    """Vérifie le bonus coopératif tribal de stockage au grenier pour les rôles CRAFTER/HUNTER."""
    cfg = AgriculturalConfig(size=10, enable_granary=True, granary_x=5, granary_y=5)
    world = AgriculturalWorld(cfg)

    model1 = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    model2 = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)

    # Agent spécialisé CRAFTER
    ag_crafter = world.add_agent(model1, x=5, y=5, energy=50.0)
    ag_crafter["role"] = "CRAFTER"
    ag_crafter["inventory"].append({"type": "Fruit", "weight": 0.5})

    # Agent non spécialisé (sans rôle)
    ag_standard = world.add_agent(model2, x=5, y=5, energy=50.0)
    ag_standard["inventory"].append({"type": "Fruit", "weight": 0.5})

    reserves_init = world.granary["reserves"]
    world.step()

    # Le Crafter a déclenché le bonus tribal (x1.5 sur les réserves déposées)
    assert ag_crafter.get("tribal_synergy_active", False) is True
    assert world.granary_deposits >= 2
    # Le delta apporté doit inclure le bonus de spécialisation
    assert world.granary["reserves"] > reserves_init + 4.0


def test_industrial_crafter_metallurgy_mastery():
    """Vérifie que le CRAFTER produit moins de suie et fabrique des armes renforcées au fourneau."""
    cfg = IndustrialConfig(size=10, furnace_x=5, furnace_y=5, pollution_per_smelt=0.10)
    world = IndustrialWorld(cfg)

    # Crafter spécialisé
    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    ag_master = world.add_agent(model, x=5, y=5, energy=50.0)
    ag_master["role"] = "CRAFTER"
    ag_master["inventory"].extend([
        {"type": "IronOre", "weight": 2.0},
        {"type": "Coal", "weight": 1.0}
    ])

    world.step()

    # 1. Vérification du bonus d'énergie et tag tribal
    assert ag_master.get("tribal_craft_bonus", False) is True
    # 2. La pollution émise doit être atténuée (0.10 * 0.7 = 0.07)
    assert world.pollution < 0.09
    # 3. L'arme forgée bénéficie du bonus de dégâts renforcé (x1.2)
    crafted_spear = next((it for it in ag_master["inventory"] if it.get("type") == "IronSpear"), None)
    if crafted_spear:
        expected_mult = cfg.metal_efficiency_boost * 1.2
        assert abs(crafted_spear["damage_mult"] - expected_mult) < 1e-4
