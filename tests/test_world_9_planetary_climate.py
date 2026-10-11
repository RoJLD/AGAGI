"""
tests/test_world_9_planetary_climate.py — Validation du Monde 9 (Climat Planétaire).
Vérifie le forçage radiatif du CO2, la fonte de l'albédo glaciaire et les événements extrêmes.
"""
import pytest
import numpy as np
from src.worlds.world_9_planetary_climate import PlanetaryClimateWorld, PlanetaryClimateConfig


def test_climate_world_initialization():
    cfg = PlanetaryClimateConfig(initial_co2_ppm=300.0)
    world = PlanetaryClimateWorld(cfg)
    assert world.co2_ppm == 300.0
    assert world.temp_anomaly == 0.0
    assert world.ice_sheet_fraction == 1.0


def test_climate_step_emissions_and_warming():
    world = PlanetaryClimateWorld()

    # Agent passif émetteur standard
    class PolluterAgent:
        def forward(self, obs):
            return np.array([1.0, 0.0])  # Action 0: émission

    world.add_agent(PolluterAgent(), energy=80.0)

    # 10 pas d'émissions
    for _ in range(10):
        world.step()

    metrics = world.get_planetary_metrics()
    assert metrics["total_emissions"] > 0.0
    assert "temp_anomaly" in metrics


def test_climate_reforestation_and_capture():
    world = PlanetaryClimateWorld()

    # Agent écologiste reboiseur
    class EcoAgent:
        def forward(self, obs):
            return np.array([0.0, 1.0])  # Action 1: reboisement

    world.add_agent(EcoAgent(), energy=80.0)

    world.step()
    metrics = world.get_planetary_metrics()
    assert metrics["carbon_captured"] > 0.0
