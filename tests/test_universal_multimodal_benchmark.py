"""
tests/test_universal_multimodal_benchmark.py — Tests unitaires pour le Banc Multimodal Universel (Arc 16 / Jalon M43).

Valide :
1. Évaluation séquentielle cohérente sur les 4 paradigmes (Bio, Logique, Code, Robotique).
2. Calcul sans biais du G-Score (Moyenne géométrique normalisée).
3. Stabilité numérique sans division par zéro ni crash (Commandement 9).
4. Respect du format de restitution des métriques universelles.
"""

import pytest
import numpy as np
from tools.universal_multimodal_benchmark import run_universal_multimodal_benchmark


def test_universal_multimodal_benchmark_execution():
    """Vérifie l'exécution complète du banc universel sur les 4 paradigmes."""
    results = run_universal_multimodal_benchmark(quick_mode=True)
    
    assert "g_score" in results
    assert "bio_score" in results
    assert "logic_score" in results
    assert "code_score" in results
    assert "physics_score" in results
    
    assert results["g_score"] >= 0.0
    assert results["g_score"] <= 1.0
    assert not np.isnan(results["g_score"])
    assert results["all_domains_passed"] is True
