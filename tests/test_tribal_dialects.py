"""
tests/test_tribal_dialects.py — Validation Métrologique des Dialectes Tribaux (Arc 5 / Option C).
Vérifie la robustesse numérique et l'identification de la spécialisation lexicale.
"""
import pytest
import numpy as np
from src.evolution.tribal_dialect import TribalDialectAnalyzer, TribalDialectConfig


def test_tribal_dialect_specialization_detection():
    """Vérifie qu'un lexique différencié par rôle produit une divergence mesurée nette."""
    analyzer = TribalDialectAnalyzer(TribalDialectConfig(vector_dim=4, min_samples_per_role=3))

    # SCOUT : communique principalement sur la dimension 0 (positions spatiales)
    for _ in range(5):
        v = np.array([1.0, 0.05, 0.0, 0.02], dtype=np.float32) + np.random.randn(4) * 0.02
        analyzer.record_utterance("SCOUT", v)

    # HUNTER : communique principalement sur la dimension 1 (proies / cibles)
    for _ in range(5):
        v = np.array([0.02, 1.0, 0.01, 0.0], dtype=np.float32) + np.random.randn(4) * 0.02
        analyzer.record_utterance("HUNTER", v)

    # CRAFTER : communique principalement sur la dimension 2 (chaleur / fourneau / craft)
    for _ in range(5):
        v = np.array([0.0, 0.01, 1.0, 0.03], dtype=np.float32) + np.random.randn(4) * 0.02
        analyzer.record_utterance("CRAFTER", v)

    summary = analyzer.summarize()

    assert summary["sample_counts"]["SCOUT"] == 5
    assert summary["sample_counts"]["HUNTER"] == 5
    assert summary["sample_counts"]["CRAFTER"] == 5

    # La cohésion interne doit être proche de 1.0
    assert summary["intra_cohesion"]["SCOUT"] > 0.95
    assert summary["intra_cohesion"]["HUNTER"] > 0.95
    assert summary["intra_cohesion"]["CRAFTER"] > 0.95

    # Les sous-dialectes doivent avoir divergé
    assert summary["is_specialized"] is True
    assert summary["specialization_index"] > 0.3
    assert summary["verdict"] == "DIALECTS_EMERGED"


def test_tribal_dialect_numerical_stability():
    """Vérifie la stabilité face aux vecteurs nuls et rôles sous-représentés."""
    analyzer = TribalDialectAnalyzer(TribalDialectConfig(vector_dim=4, min_samples_per_role=5))

    # Seulement 2 échantillons (sous le seuil de 5)
    analyzer.record_utterance("SCOUT", np.zeros(4))
    analyzer.record_utterance("SCOUT", np.zeros(4))

    summary = analyzer.summarize()
    assert summary["intra_cohesion"]["SCOUT"] == 0.0
    assert summary["is_specialized"] is False
    assert not np.isnan(summary["specialization_index"])
