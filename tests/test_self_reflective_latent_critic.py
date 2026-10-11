"""
tests/test_self_reflective_latent_critic.py — Validation TDD du Critique Réflexif (Arc 12 : Jalon M26).

Vérifie formellement :
1. L'orthogonalité du gradient riemannien tangent <z, grad_S> = 0.
2. La décroissance monotone de l'énergie de critique sous descente géodésique.
3. L'élimination active des dérives dangereuses ou déviations constitutionnelles.
4. L'unitarité stricte du vecteur corrigé sur S^(D-1).
"""

import pytest
import numpy as np
from src.metaprog.self_reflective_latent_critic import (
    SelfReflectiveLatentCritic,
    SelfReflectiveCriticConfig,
    ReflectionResult,
)


def test_riemannian_gradient_tangency():
    """Vérifie que le gradient projeté est strictement tangent à la sphère unité."""
    critic = SelfReflectiveLatentCritic()
    dim = 64
    rng = np.random.RandomState(42)

    z = critic._normalize(rng.randn(dim))
    c = critic._normalize(rng.randn(dim))
    d = [critic._normalize(rng.randn(dim))]

    energy, grad_tangent, violations = critic.compute_critic_energy_and_gradient(z, c, d)

    # Propriété fondamentale : <z, grad_tangent> == 0
    tangency = float(np.dot(z, grad_tangent))
    assert pytest.approx(tangency, abs=1e-5) == 0.0


def test_self_reflection_energy_reduction():
    """
    Vérifie que la descente de gradient géodésique réduit significativement l'énergie
    de critique et réaligne le vecteur vers la constitution.
    """
    cfg = SelfReflectiveCriticConfig(max_correction_steps=20, learning_rate=0.25)
    critic = SelfReflectiveLatentCritic(cfg)
    dim = 64

    # Vecteur constitutionnel selon l'axe e_0
    const_vec = np.zeros(dim, dtype=np.float32)
    const_vec[0] = 1.0

    # Proposition initiale orthogonale (non alignée : <z, c> = 0.0)
    proposed = np.zeros(dim, dtype=np.float32)
    proposed[1] = 1.0

    result = critic.reflect_and_correct(proposed, const_vec)

    assert isinstance(result, ReflectionResult)
    assert result.energy_reduction > 0.0
    assert result.final_energy < result.initial_energy
    # Le vecteur corrigé doit s'être rapproché du vecteur constitutionnel
    alignment_after = float(np.dot(result.corrected_latent, const_vec))
    assert alignment_after > 0.50, f"Alignement insuffisant après correction : {alignment_after}"
    assert pytest.approx(np.linalg.norm(result.corrected_latent), abs=1e-4) == 1.0


def test_danger_signature_active_avoidance():
    """Vérifie que la réflexion géodésique s'éloigne d'une signature létale."""
    critic = SelfReflectiveLatentCritic(SelfReflectiveCriticConfig(max_correction_steps=15))
    dim = 64

    const_vec = np.zeros(dim, dtype=np.float32)
    const_vec[0] = 1.0

    # Signature de danger selon l'axe e_2
    danger = np.zeros(dim, dtype=np.float32)
    danger[2] = 1.0

    # Proposition initiale dangereusement proche de danger
    proposed = np.zeros(dim, dtype=np.float32)
    proposed[0] = 0.5
    proposed[2] = 0.866  # overlap = 0.866 > margin 0.25
    proposed = proposed / np.linalg.norm(proposed)

    res = critic.reflect_and_correct(proposed, const_vec, danger_signatures=[danger])

    danger_overlap_after = float(np.dot(res.corrected_latent, danger))
    assert danger_overlap_after < 0.866, "La critique réflexive n'a pas repoussé l'état du danger"
