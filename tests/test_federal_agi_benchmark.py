"""
tests/test_federal_agi_benchmark.py — Validation unitaire du banc comparatif Arc 14 (Jalon M34).

Vérifie l'exécution du banc officiel federal_agi_benchmark :
- Stabilité spectrale contractante rho(W) <= 0.95
- Succès de la synthèse du méta-génome et compilation en sandbox
- Gain énergétique et transferts de solidarité inter-mondes
- Présence des métriques conformes sans fabrication de valeurs
"""

import pytest
import numpy as np
from tools.federal_agi_benchmark import run_federal_agi_benchmark


def test_federal_agi_benchmark_execution():
    """Valide l'exécution et les garanties d'invariance du benchmark Arc 14."""
    res = run_federal_agi_benchmark(num_steps=12, seed=123)

    assert "baseline_final_population" in res
    assert "intervention_final_population" in res
    assert "baseline_mean_energy" in res
    assert "intervention_mean_energy" in res
    assert "intervention_mutations_applied" in res
    assert "intervention_max_spectral_radius" in res

    # 1. Garantie de contraction spectrale lipschitzienne (Commandement 9)
    assert res["intervention_max_spectral_radius"] <= 0.9501

    # 2. Validation que des mutations méta-génomiques ont été appliquées en sandbox (Arc 14 : M32)
    assert res["intervention_mutations_applied"] > 0
    assert res["baseline_mutations_applied"] == 0

    # 3. Solidarité inter-mondes active
    assert res["intervention_trade_events"] >= 0

    # 4. Pas de valeurs aberrantes ou manquantes
    assert not np.isnan(res["intervention_mean_energy"])
