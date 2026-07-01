"""Tests du port PROD du gate de conditionnement (EDR-148). Pur (pas de biosphère). Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.backend_torch import TorchPopulationModel
from tools.torch_prod_gate_meansends import run_prod


def test_gate_off_by_default_no_params():
    # défaut prod-safe : pas de gate -> pas de params gate, chemin inchangé.
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)])
    assert pop.w_gate is None and pop.b_gate is None


def test_gate_on_creates_params_and_forward_uses_it():
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGET = 4
    try:
        pop = TorchPopulationModel([MambaAgent() for _ in range(4)])
        assert pop.w_gate is not None and pop.b_gate is not None
        # un biais de gate non nul décale le logit cible dans forward.
        import torch
        with torch.no_grad():
            pop.w_gate += 5.0
        obs = (np.random.RandomState(0).randn(4, pop.I) * 0.5).astype(np.float32)
        logits, _ = pop.forward(obs)
        pop.w_gate = None  # neutralise pour comparer la base
        pop.b_gate = None
        base, _ = pop.forward(obs)
        assert not np.allclose(logits[:, 4], base[:, 4])
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def test_run_prod_smoke_both():
    r_none = run_prod(False, episodes=20, n_agents=16, seed=0)
    r_gate = run_prod(True, episodes=20, n_agents=16, seed=0, antisat=6.0)
    for r in (r_none, r_gate):
        assert set(r) >= {"hit_end", "p_x", "binding_gap", "gate"}
    # flags restaurés après run (isolation).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_run_prod_stochastic_smoke():
    # l'échantillonnage stochastique (exploration) est un régime valide du chemin prod.
    r = run_prod(True, episodes=20, n_agents=16, seed=0, antisat=6.0, stochastic=True)
    assert "binding_gap" in r


def test_learn_still_works_gate_off():
    # le chemin learn (Actor-Critic TD) reste fonctionnel sans gate (banc // intact).
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.05)
    obs = (np.random.RandomState(1).randn(4, pop.I) * 0.5).astype(np.float32)
    pop.forward(obs)
    pop.learn(np.zeros(4, np.float32), [{"move": 1, "grab": 0, "rub": 0}] * 4)
    pop.forward(obs)
    loss = pop.learn(np.ones(4, np.float32), [{"move": 2, "grab": 0, "rub": 0}] * 4)
    assert loss is not None
