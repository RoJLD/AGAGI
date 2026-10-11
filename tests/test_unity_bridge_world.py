"""
tests/test_unity_bridge_world.py — Validation de la passerelle UnityBridgeWorld.
Vérifie la robustesse de l'initialisation, le mode Fallback/Mock, l'envoi d'actions,
la génération d'observations 3D LiDAR et la télémétrie de la passerelle.
"""
import pytest
import numpy as np
from src.worlds.unity_bridge_world import UnityBridgeWorld, UnityBridgeConfig


def test_unity_bridge_initialization():
    cfg = UnityBridgeConfig(mock_if_disconnected=True)
    world = UnityBridgeWorld(cfg)
    assert not world.connected_to_unity
    obs = world.reset()
    assert obs.shape == (cfg.observation_dim,)
    assert isinstance(obs, np.ndarray)


def test_unity_bridge_mock_step_physics():
    world = UnityBridgeWorld(UnityBridgeConfig(mock_if_disconnected=True))

    class MotorAgent:
        def forward(self, obs):
            # Commande motrice 3D [Fx, Fy, Fz]
            return np.array([2.0, 0.0, 1.0] + [0.0] * 22, dtype=np.float32)

    agent = world.add_agent(MotorAgent(), energy=100.0)

    # 10 étapes de simulation physique locale
    for _ in range(10):
        world.step()

    metrics = world.get_unity_metrics()
    assert metrics["tick_count"] == 10
    assert metrics["avatar_health"] > 0.0
    # La vitesse ou position doit avoir évolué suite à la poussée motrice
    assert np.linalg.norm(metrics["mock_position"]) > 0.0 or np.linalg.norm(metrics["mock_velocity"]) > 0.0


def test_unity_bridge_observation_format():
    world = UnityBridgeWorld()
    obs = world.reset()
    # Le vecteur d'observation doit être borné et sans NaN/Inf
    assert not np.isnan(obs).any()
    assert not np.isinf(obs).any()
    metrics = world.get_unity_metrics()
    assert "mock_position" in metrics
    world.close()
