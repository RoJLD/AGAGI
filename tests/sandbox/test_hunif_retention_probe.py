"""Tests du probe de rétention H-unif synthétique (EDR-162). Pur. Skip si torch absent.
(Renommé hunif_retention_probe pour éviter la collision avec le banc craft in-world de main.)"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.hunif_retention_probe import run_retention
from src.agents.backend_torch import TorchPopulationModel


def test_run_retention_smoke_on_off():
    on = run_retention(True, 0.3, episodes=20, n_agents=16, seed=0)
    off = run_retention(False, 0.3, episodes=20, n_agents=16, seed=0)
    for r in (on, off):
        assert set(r) >= {"craft_early", "craft_late", "comp_late", "payoff_late", "capability"}
        assert 0.0 <= r["craft_late"] <= 1.0
    # flags de classe restaurés (isolation intra-process).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_capability_off_has_no_gate():
    off = run_retention(False, 0.0, episodes=10, n_agents=8, seed=1)
    assert off["capability"] is False
