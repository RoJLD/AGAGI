"""
Tests unitaires pour MutualLatentTranslator (Co-apprentissage de traducteurs latents).
Conforme au Commandement 7 (Test-Driven Metaprogramming) et Commandement 9 (Stabilité Numérique).
"""

import pytest
import numpy as np
from src.metaprog.lu_auto_translator import (
    MutualLatentTranslator,
    AutoTranslatorConfig,
)


def test_auto_translator_initialization():
    cfg = AutoTranslatorConfig(dim_a=32, dim_b=32)
    translator = MutualLatentTranslator(cfg)
    v = np.random.randn(32)
    out_b = translator.translate_a_to_b(v)
    out_a = translator.translate_b_to_a(out_b)

    assert out_b.shape == (32,)
    assert out_a.shape == (32,)
    assert not np.any(np.isnan(out_b))
    assert not np.any(np.isnan(out_a))


def test_mutual_co_training_convergence():
    """Vérifie que l'apprentissage conjoint converge et augmente la fidélité mutuelle."""
    rng = np.random.RandomState(42)
    dim = 16
    n_samples = 120

    # Génération d'un ensemble de vecteurs A et d'une transformation cible vers B
    z_a = rng.randn(n_samples, dim)
    true_w = rng.randn(dim, dim) / np.sqrt(dim)
    z_b = np.dot(z_a, true_w) + rng.randn(n_samples, dim) * 0.02

    cfg = AutoTranslatorConfig(
        dim_a=dim,
        dim_b=dim,
        learning_rate=0.05,
        momentum=0.85,
        cycle_lambda=0.5,
        align_lambda=1.0,
    )
    translator = MutualLatentTranslator(cfg)

    initial_fidelity = translator.compute_mutual_fidelity(z_a, z_b)

    # Entraînement sur plusieurs époques / pas
    for _ in range(80):
        metrics = translator.train_step(z_a, z_b)
        assert not np.isnan(metrics["total_loss"])

    final_fidelity = translator.compute_mutual_fidelity(z_a, z_b)
    assert final_fidelity > initial_fidelity, "La fidélité doit augmenter après co-apprentissage."
    assert final_fidelity > 0.80, f"Fidélité attendue > 0.80, obtenu {final_fidelity}"


def test_cycle_consistency_unsupervised_step():
    """Vérifie la diminution de l'erreur de cycle en mode auto-supervisé pur."""
    rng = np.random.RandomState(123)
    dim = 24
    z_a = rng.randn(50, dim)

    cfg = AutoTranslatorConfig(dim_a=dim, dim_b=dim, learning_rate=0.03, cycle_lambda=1.0)
    translator = MutualLatentTranslator(cfg)

    # Introduit une perturbation initiale sur W_ba pour simuler un traducteur non calibré
    translator.W_ba += rng.randn(*translator.W_ba.shape) * 0.15

    # Avant entraînement
    cycle_before = translator.translate_b_to_a(translator.translate_a_to_b(z_a))
    err_before = np.mean(np.linalg.norm(cycle_before - z_a, axis=1))

    # Entraînement cycle-only
    for _ in range(80):
        translator.train_step(z_a, batch_z_b=None)

    cycle_after = translator.translate_b_to_a(translator.translate_a_to_b(z_a))
    err_after = np.mean(np.linalg.norm(cycle_after - z_a, axis=1))

    assert err_after < err_before, f"L'erreur de cycle doit diminuer: avant {err_before:.4f}, après {err_after:.4f}"



def test_asymmetric_dimensions_co_training():
    """Vérifie le co-apprentissage pour dimensions asymétriques (dim_a=48, dim_b=24)."""
    rng = np.random.RandomState(999)
    da, db = 48, 24
    n_samples = 100

    z_a = rng.randn(n_samples, da)
    w_proj = rng.randn(da, db) / np.sqrt(da)
    z_b = np.dot(z_a, w_proj)

    cfg = AutoTranslatorConfig(dim_a=da, dim_b=db, learning_rate=0.04)
    translator = MutualLatentTranslator(cfg)

    for _ in range(70):
        translator.train_step(z_a, z_b)

    pred_b = translator.translate_a_to_b(z_a)
    assert pred_b.shape == (n_samples, db)
    assert not np.any(np.isnan(pred_b))

    fid = translator.compute_mutual_fidelity(z_a, z_b)
    assert fid > 0.75
