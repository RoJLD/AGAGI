"""Tests du probe de spécialisation multi-chaînes (EDR-165). Pur. Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

import numpy as np
from tools.craft_specialization_probe import run_spec, USE_A, USE_B
from src.agents.mamba_agent import MambaAgent
from src.agents.backend_torch import TorchPopulationModel


def test_multi_target_gate_creates_matrix_params():
    # gate MULTI-CIBLE (EDR-165) : w_gate (N,K), b_gate (K,) ; single-target inchangé.
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGETS)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGETS = [USE_A, USE_B]
    try:
        pop = TorchPopulationModel([MambaAgent() for _ in range(4)])
        assert pop.w_gate is not None and tuple(pop.w_gate.shape) == (pop.N, 2)
        assert tuple(pop.b_gate.shape) == (2,)
        import torch
        gb = pop._gate_value(torch.zeros(4, pop.N))
        assert tuple(gb.shape) == (4, 2)                 # un biais par cible
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGETS) = saved


def test_run_spec_smoke_on_off():
    on = run_spec(True, episodes=20, n_agents=16, seed=0)
    off = run_spec(False, episodes=20, n_agents=16, seed=0)
    for r in (on, off):
        assert set(r) >= {"spec_depth", "comp_total", "frac_specialists", "frac_A"}
    # flags de classe restaurés (isolation intra-process) — critique : GATE_TARGETS ne doit pas fuiter.
    assert TorchPopulationModel.GATE_TARGETS is None
    assert TorchPopulationModel.CONDITION_GATE is False


def test_single_target_gate_unchanged():
    # non-régression : GATE_TARGETS None => w_gate reste vecteur (N,), comportement single inchangé.
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGET = 4
    try:
        pop = TorchPopulationModel([MambaAgent() for _ in range(4)])
        assert pop.w_gate.dim() == 1 and pop.w_gate.shape[0] == pop.N
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved
