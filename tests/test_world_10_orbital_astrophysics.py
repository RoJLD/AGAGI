"""
tests/test_world_10_orbital_astrophysics.py — Validation du Monde 10 (Astro-Physique).
Vérifie la conservation de la dynamique orbitale de Kepler, le calcul du Delta-V et le rendez-vous.
"""
import pytest
import numpy as np
from src.worlds.world_10_orbital_astrophysics import OrbitalAstrophysicsWorld, OrbitalConfig


def test_orbital_world_initialization():
    cfg = OrbitalConfig(mu_gravity=50.0, target_orbit_radius=8.0)
    world = OrbitalAstrophysicsWorld(cfg)
    assert world.config.mu_gravity == 50.0
    t_pos = world.get_target_pos()
    assert abs(np.linalg.norm(t_pos) - 8.0) < 1e-4


def test_orbital_step_and_conservation():
    world = OrbitalAstrophysicsWorld()

    # Vaisseau sans poussée (orbite libre keplerienne)
    class PassiveShip:
        def forward(self, obs):
            return np.zeros(2)

    ag = world.add_agent(PassiveShip(), initial_radius=5.0)
    r_initial = float(np.linalg.norm(ag["pos"]))

    for _ in range(20):
        world.step()

    r_final = float(np.linalg.norm(ag["pos"]))
    # En orbite circulaire libre, le rayon reste quasi-constant
    assert abs(r_final - r_initial) < 0.5


def test_orbital_metrics():
    world = OrbitalAstrophysicsWorld()
    metrics = world.get_orbital_metrics()
    assert "successful_rendezvous" in metrics
    assert "total_delta_v_spent" in metrics
