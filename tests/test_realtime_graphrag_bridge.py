"""
tests/test_realtime_graphrag_bridge.py — Tests TDD pour le Pont Graph-RAG Bidirectionnel Temps Réel.
Arc 14 : Jalon M33 (RealtimeGraphRAGBridge).

Vérifie formellement la synchronisation continue entre les consensus de civilisation,
la détection d'effondrement de variance/stagnation et l'injection d'interventions téléologiques.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Transparent & Auditable, Stabilité Numérique).
"""

import pytest
import numpy as np

from src.graph_rag.realtime_graphrag_bridge import (
    RealtimeGraphRAGBridge,
    RealtimeBridgeConfig,
)


def test_bridge_initialization():
    """Vérifie l'instanciation correcte du pont Graph-RAG."""
    cfg = RealtimeBridgeConfig(
        latent_dim=64,
        stagnation_variance_threshold=0.08,
        min_history_steps=4,
    )
    bridge = RealtimeGraphRAGBridge(cfg)

    assert bridge.config.latent_dim == 64
    assert bridge.step_count == 0
    assert len(bridge.history_consensus) == 0
    assert bridge.interventions_count == 0


def test_bridge_variance_monitoring_healthy():
    """Vérifie qu'un essaim exploratoire diversifié ne déclenche pas d'intervention prématurée."""
    cfg = RealtimeBridgeConfig(
        latent_dim=64,
        stagnation_variance_threshold=0.05,
        min_history_steps=3,
    )
    bridge = RealtimeGraphRAGBridge(cfg)

    rng = np.random.RandomState(42)
    # Flux de consensus diversifiés
    for _ in range(5):
        raw = rng.randn(64).astype(np.float32)
        z = raw / np.linalg.norm(raw)
        res = bridge.monitor_and_sync(z, {"mean_energy": 50.0})

    assert res["stagnation_detected"] is False
    assert res["intervention_triggered"] is False
    assert res["variance"] > 0.05
    assert bridge.interventions_count == 0


def test_bridge_stagnation_detection_and_intervention():
    """Vérifie que la perte de variance collective déclenche une intervention d'innovation."""
    cfg = RealtimeBridgeConfig(
        latent_dim=64,
        stagnation_variance_threshold=0.05,
        min_history_steps=4,
    )
    bridge = RealtimeGraphRAGBridge(cfg)

    # Flux de consensus identiques (stagnation artificielle)
    base_z = np.ones(64, dtype=np.float32)
    base_z = base_z / np.linalg.norm(base_z)

    for i in range(5):
        res = bridge.monitor_and_sync(base_z, {"mean_energy": 25.0})

    assert res["stagnation_detected"] is True
    assert res["intervention_triggered"] is True
    assert "refreshed_goal" in res
    refreshed_z = res["refreshed_goal"]
    assert pytest.approx(float(np.linalg.norm(refreshed_z)), abs=1e-4) == 1.0
    # Le but rafraîchi doit diverger du but stagnant
    overlap = float(np.dot(refreshed_z, base_z))
    assert overlap < 0.95
    assert bridge.interventions_count >= 1


def test_bridge_nan_inf_immunity():
    """Vérifie la robustesse numérique absolue face à des entrées corrompues."""
    cfg = RealtimeBridgeConfig(latent_dim=64)
    bridge = RealtimeGraphRAGBridge(cfg)

    corrupt_z = np.array([float("nan")] * 64, dtype=np.float32)
    res = bridge.monitor_and_sync(corrupt_z, {"mean_energy": 30.0})

    assert not np.isnan(res["variance"])
    assert not np.isinf(res["variance"])
    if res["refreshed_goal"] is not None:
        assert not np.any(np.isnan(res["refreshed_goal"]))
