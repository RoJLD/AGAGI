"""
tests/test_g2_strong_emergence_benchmark.py — Validation TDD du franchissement de G2-Fort / EDR-LOCK-001.
"""

import pytest
from tools.g2_strong_emergence_benchmark import run_g2_strong_emergence_benchmark, run_bare_emergence_seed


def test_bare_emergence_seed_execution():
    """Vérifie l'exécution d'un seed de probe sur agent nu."""
    r = run_bare_emergence_seed(demand=1.0, seed=42, episodes=100)
    assert 0.0 <= r <= 1.0


def test_g2_strong_emergence_validation():
    """Valide que le banc G2-Fort sépare significativement d=1.0 de d=0.0."""
    res = run_g2_strong_emergence_benchmark(n_seeds=3, episodes=400, lr=0.005)
    assert res["wins"] >= 2
    assert res["median_comp_rate_d1"] > res["median_comp_rate_d0"]
