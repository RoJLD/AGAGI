"""Tests du backend torch — substrat LTC différentiable (ADR-003, Axe 1).

MVP : même équation LTC que le legacy, mais W entraînable par autograd. On teste le
contrat PopulationModel + que le GRADIENT apprend réellement (REINFORCE sur `move`).
Skip propre si torch absent.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
import pytest

pytest.importorskip("torch")
import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population, PopulationModel
from src.agents.backend_torch import TorchPopulationModel


def _agents(n=2, seed=0):
    np.random.seed(seed)
    return [MambaAgent() for _ in range(n)]


def test_make_population_torch_returns_torch_model():
    pop = make_population(_agents(2), backend="torch")
    assert isinstance(pop, PopulationModel)
    assert isinstance(pop, TorchPopulationModel)
    assert pop.B == 2


def test_torch_forward_shape_and_finite():
    pop = make_population(_agents(2), backend="torch")
    preds, _ = pop.forward(np.zeros((2, 59), dtype=np.float32))
    assert preds.shape == (2, pop.O)
    assert np.all(np.isfinite(preds))


def test_torch_forward_deterministic():
    obs = np.zeros((2, 59), dtype=np.float32)
    torch.manual_seed(0)
    p1, _ = make_population(_agents(2, seed=3), backend="torch").forward(obs)
    torch.manual_seed(0)
    p2, _ = make_population(_agents(2, seed=3), backend="torch").forward(obs)
    assert np.allclose(p1, p2)


def test_torch_learn_reduces_reinforce_loss():
    """Le gradient apprend : récompenser `move=0` fait baisser la perte REINFORCE."""
    pop = make_population(_agents(2), backend="torch")
    np.random.seed(1)
    pop.forward(np.random.randn(2, 59).astype(np.float32))
    rewards = np.array([1.0, 1.0], dtype=np.float32)
    acts = [{"move": 0}, {"move": 0}]
    losses = [pop.learn(rewards, acts) for _ in range(8)]
    assert losses[-1] < losses[0]


def test_torch_learn_writes_genome_back():
    agents = _agents(2)
    pop = make_population(agents, backend="torch")
    before = agents[0].genome.W.copy()
    np.random.seed(1)
    pop.forward(np.random.randn(2, 59).astype(np.float32))
    pop.learn(np.array([1.0, 1.0], dtype=np.float32), [{"move": 0}, {"move": 0}])
    assert not np.allclose(before, agents[0].genome.W)


def test_torch_heterogeneous_dims_rejected_in_mvp():
    np.random.seed(0)
    mixed = [MambaAgent(num_nodes=172), MambaAgent(num_nodes=180)]
    with pytest.raises(NotImplementedError):
        make_population(mixed, backend="torch")
