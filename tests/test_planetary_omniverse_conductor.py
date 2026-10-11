"""
tests/test_planetary_omniverse_conductor.py — Validation du Conductor Planétaire Omniversel.
Vérifie la progression conjointe des mondes cyber, climatique et orbital ainsi que l'indice Kardashev.
"""
import pytest
import numpy as np
from src.worlds.planetary_omniverse_conductor import PlanetaryOmniverseConductor, OmniverseConfig


def test_omniverse_conductor_initialization():
    conductor = PlanetaryOmniverseConductor()
    assert conductor.cyber_world is not None
    assert conductor.climate_world is not None
    assert conductor.orbital_world is not None


def test_omniverse_conductor_step_and_kardashev():
    conductor = PlanetaryOmniverseConductor()

    class DummyAgent:
        def forward(self, obs):
            return np.zeros(2)

    conductor.cyber_world.add_agent(DummyAgent(), node_id=0)
    conductor.climate_world.add_agent(DummyAgent())
    conductor.orbital_world.add_agent(DummyAgent(), initial_radius=5.0)

    # Avancer de 10 pas
    for _ in range(10):
        res = conductor.step()

    report = conductor.get_omniverse_report()
    assert report["kardashev_index"] > 0.0
    assert "cyber" in report
    assert "climate" in report
    assert "orbital" in report
