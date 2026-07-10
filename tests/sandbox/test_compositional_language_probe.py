"""Tests du jeu référentiel COMPOSITIONNEL (LANG-003, messages 2-symboles, zéro-shot). Pur. Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.compositional_language_probe import run_compositional
from src.agents.backend_torch import TorchPopulationModel


def test_run_compositional_smoke_keys():
    r = run_compositional(episodes=20, n_agents=8, A=3, V=6, seed=0, rotate=True)
    assert set(r) >= {"within", "zeroshot", "gen_gap", "chance", "A", "V", "rotate", "topsim"}
    assert r["chance"] == pytest.approx(1.0 / 3)
    for k in ("within", "zeroshot"):
        assert 0.0 <= r[k] <= 1.0
    assert r["gen_gap"] == pytest.approx(r["zeroshot"] - r["chance"])
    assert -1.0 <= r["topsim"] <= 1.0                              # rho de Spearman borné
    # flags de classe restaurés (pas de gate ici).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_heldout_is_diagonal_untrained():
    # A=4 -> 16 combos, diagonale (4) held-out, 12 combos entraînés ; chaque valeur d'attribut reste vue.
    # Sanity : à peine entraîné, zéro-shot reste dans [0,1] et proche de la chance (pas de fuite/NaN).
    r = run_compositional(episodes=15, n_agents=8, A=4, V=6, seed=1, rotate=False)
    assert r["chance"] == pytest.approx(0.25)
    assert 0.0 <= r["zeroshot"] <= 1.0
