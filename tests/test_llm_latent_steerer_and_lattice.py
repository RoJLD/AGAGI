"""
tests/test_llm_latent_steerer_and_lattice.py — Suite de validation TDD pour le Steering Téléologique et la Lattice Memory (Arc 10).
"""

import pytest
import numpy as np
from src.metaprog.llm_latent_steerer import (
    SteeringConfig,
    LLMLatentSteerer,
    SteeringMode,
)
from src.metaprog.llm_lattice_bridge import (
    LLMLatticeConfig,
    LLMLatticeBridge,
)


def test_latent_steerer_goal_alignment_gain():
    """Vérifie que l'activation steering augmente significativement l'alignement vers le but."""
    steerer = LLMLatentSteerer(SteeringConfig(steering_strength=0.40))

    rng = np.random.default_rng(42)
    d_model = 384
    d_latent = 64

    # Matrice de projection semi-orthogonale
    q, _ = np.linalg.qr(rng.normal(size=(d_model, d_latent)))
    P = q.astype(np.float32)

    # État initial neutre
    h_init = rng.normal(size=d_model).astype(np.float32)
    h_init /= np.linalg.norm(h_init)

    # But téléologique
    z_goal = rng.normal(size=d_latent).astype(np.float32)
    z_goal /= np.linalg.norm(z_goal)

    h_steered, gain = steerer.steer_hidden_state(h_init, z_goal, P)

    assert gain > 0.15, f"Gain d'alignement attendu > 0.15, obtenu {gain:.4f}"
    # Préservation stricte de la norme d'activation
    assert abs(np.linalg.norm(h_steered) - 1.0) < 1e-4


def test_teleological_rollout_convergence():
    """Vérifie la trajectoire de convergence intérieure vers l'attracteur en K pas."""
    steerer = LLMLatentSteerer(SteeringConfig(steering_strength=0.30, teleological_horizon_steps=4))

    rng = np.random.default_rng(100)
    d_model = 256
    d_latent = 32

    q, _ = np.linalg.qr(rng.normal(size=(d_model, d_latent)))
    P = q.astype(np.float32)

    h_start = rng.normal(size=d_model).astype(np.float32)
    h_start /= np.linalg.norm(h_start)

    z_target = rng.normal(size=d_latent).astype(np.float32)
    z_target /= np.linalg.norm(z_target)

    trajectory = steerer.compute_teleological_rollout(h_start, z_target, P, steps=4)
    assert len(trajectory) == 5

    # La similarité avec la cible doit croître le long de la trajectoire
    sims = [
        float(np.dot(np.dot(h, P), z_target) / (np.linalg.norm(np.dot(h, P)) * np.linalg.norm(z_target)))
        for h in trajectory
    ]
    assert sims[-1] > sims[0] + 0.20, f"Progression insuffisante: {sims[0]:.3f} -> {sims[-1]:.3f}"


def test_hoare_safety_verification_and_adversarial_rejection():
    """Vérifie la preuve de sécurité de Hoare et le rejet des signatures adverses."""
    bridge = LLMLatticeBridge(LLMLatticeConfig(latent_dim=64, adversarial_rejection_threshold=0.45))

    # 1. Vecteur aligné et unitaire -> Doit être validé
    z_safe = bridge.constitution_vector.copy()
    is_safe, score, reason = bridge.verify_hoare_safety(z_safe)
    assert is_safe is True
    assert score > 0.70

    # 2. Vecteur corrompu par une signature adverse -> Doit être rejeté
    z_hostile = bridge.adversarial_signatures[0].copy()
    is_safe_adv, score_adv, reason_adv = bridge.verify_hoare_safety(z_hostile)
    assert is_safe_adv is False
    assert "Détection de signature adverse" in reason_adv


def test_lattice_thought_recording_and_explanation():
    """Vérifie l'enregistrement dans la Lattice Memory et l'explicabilité humaine."""
    bridge = LLMLatticeBridge(LLMLatticeConfig(latent_dim=64))

    z_thought = bridge.constitution_vector.copy()
    record = bridge.record_thought_transfer(
        thought_id="th_test_001",
        source_model="Qwen-1.5B",
        target_model="Mistral-7B",
        prompt_topic="Optimisation de portefeuille énergétique",
        thought_latent=z_thought,
        fidelity=0.92,
    )

    assert record.thought_id == "th_test_001"
    assert record.is_safe is True
    assert record.cosine_fidelity == 0.92

    # Décompilation explicable
    explanation = bridge.explain_thought(z_thought)
    assert explanation["safety_verdict"] == "CERTIFIÉ SÛR"
    assert len(explanation["dominant_latent_axes"]) == 3
    assert len(explanation["dominant_latent_values"]) == 3
