"""
Test unitaire pour le Monde 3 (Âge Industriel & Métallurgie).
Valide la fusion au haut fourneau, le forgeage d'outils métalliques et la dynamique de pollution.
"""
import pytest
import numpy as np
from src.worlds.world_3_industrial import IndustrialWorld, IndustrialConfig
from src.agents.mamba_agent import MambaAgent


def test_blast_furnace_smelting_and_pollution():
    """Vérifie la fusion IronOre + Coal -> IronIngot et l'émission de pollution."""
    cfg = IndustrialConfig(size=12, furnace_x=6, furnace_y=6, pollution_per_smelt=0.05)
    world = IndustrialWorld(cfg)

    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    ag = world.add_agent(model, x=6, y=6, energy=60.0)

    # Donner du minerai de fer et du charbon à l'agent
    ag["inventory"].append({"type": "IronOre", "weight": 2.0})
    ag["inventory"].append({"type": "Coal", "weight": 1.0})

    initial_pollution = world.pollution
    world.step()

    # Le lingot de fer et la lance doivent avoir été forgés
    has_ingot_or_tool = any(it.get("type") in ["IronIngot", "IronSpear"] for it in ag["inventory"] + world.items)
    assert has_ingot_or_tool is True
    assert world.iron_smelted >= 1
    assert world.pollution > initial_pollution


def test_metal_tool_crafting():
    """Vérifie la transformation IronIngot -> IronSpear."""
    cfg = IndustrialConfig(size=12, furnace_x=5, furnace_y=5)
    world = IndustrialWorld(cfg)

    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    ag = world.add_agent(model, x=5, y=5, energy=70.0)

    # Donner un lingot de fer à l'agent
    ag["inventory"].append({"type": "IronIngot", "weight": 1.5, "tier": "METAL"})

    world.step()

    # L'outil métallique doit avoir été forgé (en inventaire ou lâché/lancé dans le monde)
    has_spear = any(it.get("type") == "IronSpear" for it in ag["inventory"] + world.items)
    assert has_spear is True
    assert world.metal_tools_crafted >= 1


def test_vegetation_depollution():
    """Vérifie que la présence de plantes réduit le niveau de pollution."""
    cfg = IndustrialConfig(size=10, plant_depollution_rate=0.02)
    world = IndustrialWorld(cfg)

    # Injecter de la pollution artificielle
    world.pollution = 0.5
    # Ajouter des plantes dans l'environnement
    world.items.append({"type": "Plant", "x": 2, "y": 2})
    world.items.append({"type": "Plant", "x": 3, "y": 3})

    initial_pol = world.pollution
    world.step()

    assert world.pollution < initial_pol
    assert world.pollution_absorbed > 0.0
