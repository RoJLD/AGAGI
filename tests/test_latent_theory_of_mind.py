"""
tests/test_latent_theory_of_mind.py — Validation TDD du Moteur de Théorie de l'Esprit Latente (Arc 15 : Jalon M36).
"""

import pytest
import numpy as np
from src.metaprog.latent_theory_of_mind import LatentTheoryOfMindEngine, ToMConfig


def test_tom_initialization_and_unitary_invariance():
    """Vérifie que les croyances et cartes mentales sont rigoureusement unitaires sur S^(D-1)."""
    engine = LatentTheoryOfMindEngine(ToMConfig(latent_dim=64, seed=42))

    z_hat = engine.predict_target_intention(observer_id="agent_1", target_id="agent_2")
    assert z_hat.shape == (64,)
    assert np.isclose(np.linalg.norm(z_hat), 1.0, atol=1e-5)


def test_tom_riemannian_observation_convergence():
    """Vérifie que l'observation répétée rapproche géodésiquement l'intention estimée de l'action réelle."""
    engine = LatentTheoryOfMindEngine(ToMConfig(latent_dim=64, learning_rate=0.30, seed=42))

    # Action cible fixe
    target_action = np.ones(64, dtype=np.float32) / np.sqrt(64)

    initial_z = engine.predict_target_intention("obs_A", "target_B")
    initial_dist = 1.0 - float(np.dot(initial_z, target_action))

    # 15 pas d'observation
    for _ in range(15):
        rep = engine.observe_agent_step("obs_A", "target_B", target_action)
        assert np.isclose(rep["z_posterior_norm"], 1.0, atol=1e-5)

    final_z = engine.predict_target_intention("obs_A", "target_B")
    final_dist = 1.0 - float(np.dot(final_z, target_action))

    # La distance cosinus doit avoir décru de manière significative
    assert final_dist < initial_dist
    assert final_dist < 0.10
    assert rep["confidence"] > 0.80


def test_tom_byzantine_defection_detection():
    """Vérifie que l'agent déviant ou opposé à l'objectif commun est immédiatement détecté comme suspect."""
    engine = LatentTheoryOfMindEngine(
        ToMConfig(latent_dim=64, byzantine_divergence_threshold=0.50, seed=42)
    )

    common_goal = np.zeros(64, dtype=np.float32)
    common_goal[0] = 1.0  # Alignement sur axe 0

    # Agent loyal aligné sur l'axe 0
    loyal_action = np.zeros(64, dtype=np.float32)
    loyal_action[0] = 1.0

    # Agent hostile/byzantin opposé (direction antipodale -1.0)
    hostile_action = np.zeros(64, dtype=np.float32)
    hostile_action[0] = -1.0

    # Observation des deux agents
    for _ in range(5):
        engine.observe_agent_step("chief", "loyal_agent", loyal_action)
        engine.observe_agent_step("chief", "hostile_agent", hostile_action)

    risk_loyal = engine.assess_cooperation_risk("chief", "loyal_agent", common_goal)
    risk_hostile = engine.assess_cooperation_risk("chief", "hostile_agent", common_goal)

    assert not risk_loyal["is_suspicious"]
    assert risk_loyal["defection_probability"] < 0.20

    assert risk_hostile["is_suspicious"]
    assert risk_hostile["defection_probability"] > 0.40
    assert risk_hostile["cosine_distance"] > 1.0


def test_tom_collective_mental_map_synthesis():
    """Vérifie la synthèse du barycentre des intentions perçues."""
    engine = LatentTheoryOfMindEngine(ToMConfig(latent_dim=64, seed=42))

    # Observer 3 cibles distinctes
    for i in range(3):
        v = np.random.randn(64).astype(np.float32)
        v = v / np.linalg.norm(v)
        engine.observe_agent_step("observer", f"target_{i}", v)

    collective_map = engine.synthesize_collective_mental_map("observer")
    assert collective_map.shape == (64,)
    assert np.isclose(np.linalg.norm(collective_map), 1.0, atol=1e-5)


def test_tom_nan_inf_robustness():
    """Vérifie la robustesse aux entrées dégénérées ou corrompues."""
    engine = LatentTheoryOfMindEngine(ToMConfig(latent_dim=64, seed=42))

    corrupt_action = np.array([float("nan"), float("inf"), -float("inf")] + [0.0] * 61, dtype=np.float32)
    rep = engine.observe_agent_step("obs", "corrupt_target", corrupt_action)

    assert not np.isnan(rep["z_posterior_norm"])
    assert np.isclose(rep["z_posterior_norm"], 1.0, atol=1e-5)

    risk = engine.assess_cooperation_risk("obs", "corrupt_target", corrupt_action)
    assert not np.isnan(risk["defection_probability"])
