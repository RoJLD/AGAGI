"""Tests du probe monde compositionnel (EDR-161). Pur (pas de biosphère). Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.compositional_world_probe import run_world, _energy, CRAFT, USE, FREE
from src.agents.backend_torch import TorchPopulationModel


def test_energy_rewards_composition():
    # coût de faim -0.3 partout ; composer domine à d=1, FREE domine à d=0 ; USE-sans-craft = faim seule.
    assert _energy(USE, True, 1.0) == pytest.approx(1.2)    # composition réussie, demande max
    assert _energy(USE, False, 1.0) == pytest.approx(-0.3)  # USE sans craft = juste la faim (doux)
    assert _energy(FREE, False, 1.0) == pytest.approx(-0.3) # à d=1 FREE ne vaut plus rien
    assert _energy(FREE, False, 0.0) == pytest.approx(0.7)  # à d=0 FREE couvre la faim + food
    assert _energy(USE, True, 0.0) == pytest.approx(0.2)    # à d=0 composer paie peu
    # à d=1, composer (>0) domine FREE/abstention (<0) ; à d=0, FREE domine composer.
    assert _energy(USE, True, 1.0) > _energy(FREE, False, 1.0)
    assert _energy(FREE, False, 0.0) > _energy(USE, True, 0.0)


def test_run_world_smoke_on_off():
    on = run_world(True, 1.0, episodes=20, n_agents=16, seed=0)
    off = run_world(False, 1.0, episodes=20, n_agents=16, seed=0)
    for r in (on, off):
        assert set(r) >= {"payoff", "comp_rate", "capability", "demand"}
    # flags de classe restaurés (isolation intra-process).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_capability_off_has_no_gate():
    # capacité OFF => pas de params de gate (substrat plain, EDR-148).
    off = run_world(False, 0.5, episodes=10, n_agents=8, seed=1)
    assert off["capability"] is False
