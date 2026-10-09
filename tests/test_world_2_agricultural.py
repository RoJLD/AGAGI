"""
Test unitaire pour le Monde 2 (Âge Agricole / Option B).
Valide le cycle saisonnier, la germination, le grenier communautaire et la coordination LU.
"""
import numpy as np
import pytest
from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.agents.mamba_agent import MambaAgent


def test_agricultural_seasons_cycle():
    """Valide la transition séquentielle des 4 saisons."""
    cfg = AgriculturalConfig(season_duration=10, size=10)
    world = AgriculturalWorld(cfg)

    assert world.season == "spring"
    for _ in range(10):
        world.step()
    assert world.season == "summer"
    for _ in range(10):
        world.step()
    assert world.season == "autumn"
    for _ in range(10):
        world.step()
    assert world.season == "winter"


def test_granary_reserves_and_winter_protection():
    """Valide que le grenier protège les agents du gel hivernal et reçoit les dépôts."""
    cfg = AgriculturalConfig(season_duration=5, size=10, enable_granary=True, granary_x=5, granary_y=5)
    world = AgriculturalWorld(cfg)

    # Forcer la saison en hiver
    world.season = "winter"
    world.season_ticks = 0

    # Créer un agent à côté du grenier avec un fruit en inventaire
    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    ag = world.add_agent(model, x=5, y=5, energy=50.0)
    ag["inventory"].append({"type": "Fruit", "weight": 0.5})

    initial_reserves = world.granary["reserves"]
    world.step()

    # Le fruit doit avoir été déposé au grenier ou consommé pour réapprovisionnement
    assert world.granary_deposits >= 1 or world.granary_withdrawals >= 1
    # L'énergie de l'agent ne doit pas s'effondrer grâce au grenier
    assert ag["energy"] > 30.0


def test_plant_growth_and_lu_synergy():
    """Valide la maturation des plantes et l'amplification par coordination LU."""
    cfg = AgriculturalConfig(season_duration=20, size=10, sprout_chance=1.0, growth_rate=1.0, lu_agricultural_synergy=2.0)
    world = AgriculturalWorld(cfg)

    # Installer une plante mature en été
    world.season = "summer"
    world.items.append({"type": "Plant", "x": 3, "y": 3, "growth": 0.9})

    # Placer un agent communiquant en LU à côté (d <= 3)
    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
    ag = world.add_agent(model, x=3, y=4, energy=80.0)
    ag["active_lu_mode"] = True

    initial_harvested = world.harvested_crops
    world.step()

    # La récolte a eu lieu et a profité de la synergie
    assert world.harvested_crops > initial_harvested
    assert world.crops_coordinated_lu >= 1
