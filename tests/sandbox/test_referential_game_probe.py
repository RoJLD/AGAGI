"""Tests du jeu référentiel de Lewis (Arc 4 langage, roadmap #1). Pur. Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.referential_game_probe import run_lewis
from src.agents.backend_torch import TorchPopulationModel


def test_run_lewis_smoke_keys():
    r = run_lewis(episodes=20, n_agents=16, K=4, V=6, seed=0)
    assert set(r) >= {"acc_late", "acc_fiable", "acc_brouille", "chance", "K", "V"}
    assert r["chance"] == pytest.approx(0.25)
    for k in ("acc_late", "acc_fiable", "acc_brouille"):
        assert 0.0 <= r[k] <= 1.0
    # flags de classe restaurés (pas de gate ici).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_brouille_is_near_chance():
    # signal aléatoire (décorrélé) -> accuracy ~ chance, quel que soit l'apprentissage du sender.
    r = run_lewis(episodes=30, n_agents=32, K=4, V=6, seed=1)
    assert r["acc_brouille"] <= r["chance"] + 0.20   # borne large (bruit d'échantillon)
