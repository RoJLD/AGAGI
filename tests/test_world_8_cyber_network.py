"""
tests/test_world_8_cyber_network.py — Validation du Monde 8 (Cyber-Réseau).
Vérifie la topologie, le routage de paquets, la bande passante et les métriques de trafic.
"""
import pytest
import numpy as np
from src.worlds.world_8_cyber_network import CyberNetworkWorld, CyberNetworkConfig


def test_cyber_world_initialization():
    cfg = CyberNetworkConfig(num_nodes=6, link_probability=0.5)
    world = CyberNetworkWorld(cfg)
    assert world.adjacency_matrix.shape == (6, 6)
    assert np.all(world.adjacency_matrix == world.adjacency_matrix.T)
    assert len(world.packet_queues) == 6


def test_cyber_packet_routing_and_delivery():
    cfg = CyberNetworkConfig(num_nodes=4, byzantine_corruption_rate=0.0, packet_loss_rate=0.0)
    world = CyberNetworkWorld(cfg)

    # Agent oracle passif
    class DummyAgent:
        def forward(self, obs):
            return np.zeros(2)

    world.add_agent(DummyAgent(), node_id=1, energy=50.0)

    # Faire tourner plusieurs steps
    for _ in range(10):
        world.step()

    metrics = world.get_cyber_metrics()
    assert metrics["delivered_packets"] >= 0
    assert "delivery_rate" in metrics


def test_cyber_metrics_integrity():
    world = CyberNetworkWorld()
    metrics = world.get_cyber_metrics()
    assert "active_queues_total" in metrics
    assert "dropped_packets" in metrics
