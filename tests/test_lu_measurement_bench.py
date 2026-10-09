"""
Tests unitaires pour la suite métrologique LUMeasurementBench.
Conforme au Commandement 7 (Test-Driven Metaprogramming) et Commandement 15 (Mesures Scientifiques).
"""

import pytest
import numpy as np
from tools.lu_measurement_bench import LUMeasurementBench, LUMetricsReport
from src.metaprog.lu_auto_translator import MutualLatentTranslator, AutoTranslatorConfig


def test_cka_identical_and_orthogonal():
    rng = np.random.RandomState(42)
    x = rng.randn(50, 16)

    # CKA d'une matrice avec elle-même doit valoir 1.0
    cka_self = LUMeasurementBench.compute_linear_cka(x, x)
    assert np.isclose(cka_self, 1.0, atol=1e-5)

    # CKA d'une matrice avec une rotation orthogonale pure doit valoir 1.0
    h = rng.randn(16, 16)
    q, _ = np.linalg.qr(h)
    x_rot = np.dot(x, q)
    cka_rot = LUMeasurementBench.compute_linear_cka(x, x_rot)
    assert np.isclose(cka_rot, 1.0, atol=1e-4)

    # CKA de matrices indépendantes doit être très faible
    y_random = rng.randn(50, 16)
    cka_rand = LUMeasurementBench.compute_linear_cka(x, y_random)
    assert cka_rand < 0.40


def test_mantel_topological_similarity():
    rng = np.random.RandomState(101)
    x = rng.randn(40, 8)

    # Avec elle-même -> corrélation = 1.0
    mantel_self = LUMeasurementBench.compute_mantel_topological_similarity(x, x)
    assert np.isclose(mantel_self, 1.0, atol=1e-4)

    # Sous translation et rotation pure -> les distances relatives sont invariantes
    q, _ = np.linalg.qr(rng.randn(8, 8))
    x_transformed = np.dot(x, q) + 5.0
    mantel_isometry = LUMeasurementBench.compute_mantel_topological_similarity(x, x_transformed)
    assert np.isclose(mantel_isometry, 1.0, atol=1e-4)


def test_full_diagnostic_report():
    rng = np.random.RandomState(77)
    x = rng.randn(30, 12)
    y = x + rng.randn(30, 12) * 0.1

    translator = MutualLatentTranslator(AutoTranslatorConfig(dim_a=12, dim_b=12))
    report = LUMeasurementBench.full_diagnostic_report(x, y, translator=translator)

    assert isinstance(report, LUMetricsReport)
    assert report.is_statistically_sound is True
    assert 0.0 <= report.cka_score <= 1.0
    assert -1.0 <= report.mantel_topological_corr <= 1.0
    assert report.sample_size == 30


def test_compare_discrete_vs_latent_transmission():
    """Vérifie la supériorité informationnelle prouvée du canal latent sur le canal discret."""
    rng = np.random.RandomState(42)
    # 100 concepts complexes en dimension 32
    concepts = rng.randn(100, 32)

    results = LUMeasurementBench.compare_discrete_vs_latent_transmission(
        concepts,
        vocab_size=16,
        noise_level=0.05,
        seed=42
    )

    # Le canal continu LU doit avoir une fidélité cosinus nettement supérieure
    assert results["latent_fidelity"] > 0.95
    assert results["discrete_fidelity"] < 0.85
    assert results["fidelity_ratio_gain"] > 1.15
    assert results["latent_mse"] < results["discrete_mse"]
