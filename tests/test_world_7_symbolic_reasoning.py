"""
tests/test_world_7_symbolic_reasoning.py — Validation du Monde 7 (Raisonnement Symbolique).
Vérifie la génération de tâches algébriques, la résolution par Modus Ponens et la distribution des récompenses.
"""
import pytest
import numpy as np
from src.worlds.world_7_symbolic_reasoning import SymbolicReasoningWorld, SymbolicConfig


def test_symbolic_world_initialization():
    cfg = SymbolicConfig(reward_correct_proof=15.0)
    world = SymbolicReasoningWorld(cfg)
    assert world.config.reward_correct_proof == 15.0
    assert world.current_task is not None
    assert "target" in world.current_task


def test_symbolic_world_correct_solving():
    world = SymbolicReasoningWorld()

    # Agent oracle qui renvoie directement la cible exacte
    class ExactOracleModel:
        def __init__(self, w):
            self.w = w
        def forward(self, obs):
            return np.array([self.w.current_task["target"]])

    model = ExactOracleModel(world)
    ag = world.add_agent(model, energy=50.0)

    # Step de résolution
    world.step()
    assert world.solved_tasks == 1
    assert world.failed_tasks == 0
    assert ag["energy"] > 50.0


def test_symbolic_metrics():
    world = SymbolicReasoningWorld()
    metrics = world.get_symbolic_metrics()
    assert "accuracy" in metrics
    assert "solved_tasks" in metrics
