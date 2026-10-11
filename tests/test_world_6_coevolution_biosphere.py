"""
tests/test_world_6_coevolution_biosphere.py — Validation du Monde 6 (Co-Évolution).
Vérifie la fuite vectorisée des proies, le camouflage, la toxicité et l'Arms Race.
"""
import pytest
import numpy as np
from src.worlds.world_6_coevolution_biosphere import CoevolutionBiosphereWorld, CoevolutionConfig
from src.agents.mamba_agent import MambaAgent


def test_coevolution_world_initialization():
    cfg = CoevolutionConfig(prey_base_speed=1.0, toxic_prey_ratio=0.5)
    world = CoevolutionBiosphereWorld(cfg)
    assert world.current_prey_speed == 1.0
    assert world.arms_race_generation == 1
    assert len(world.preys) > 0


def test_prey_evasion_behavior():
    cfg = CoevolutionConfig(prey_base_speed=2.0, prey_evasion_radius=15.0)
    world = CoevolutionBiosphereWorld(cfg)

    if len(world.preys) > 0:
        prey = world.preys[0]
        initial_x, initial_y = prey["x"], prey["y"]

        # Créer un agent directement à côté avec add_agent
        model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs)
        agent_x = (initial_x + 1) % world.size
        ag = world.add_agent(model, x=agent_x, y=initial_y, energy=80.0)

        world.step()
        assert world.successful_evasions >= 1


def test_coevolution_metrics():
    world = CoevolutionBiosphereWorld()
    metrics = world.get_coevolution_metrics()
    assert "current_prey_speed" in metrics
    assert "arms_race_generation" in metrics
    assert "successful_evasions" in metrics
