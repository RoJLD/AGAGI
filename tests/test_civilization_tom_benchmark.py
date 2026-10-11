"""
tests/test_civilization_tom_benchmark.py — Validation unitaire du banc comparatif Arc 15 (Jalon M38).
"""

import pytest
import numpy as np
from tools.civilization_tom_benchmark import run_civilization_tom_benchmark


def test_civilization_tom_benchmark_execution():
    """Valide l'exécution et les garanties d'invariance du benchmark Arc 15."""
    res = run_civilization_tom_benchmark(num_steps=10, seed=123)

    assert "baseline_final_population" in res
    assert "intervention_final_population" in res
    assert "baseline_mean_energy" in res
    assert "intervention_mean_energy" in res
    assert "intervention_tom_map_norm" in res

    # 1. Carte mentale ToM unitaire sur S^(D-1)
    assert np.isclose(res["intervention_tom_map_norm"], 1.0, atol=1e-4)

    # 2. Pas de NaN ou de corruption
    assert not np.isnan(res["intervention_mean_energy"])
    assert res["intervention_final_population"] >= 0
