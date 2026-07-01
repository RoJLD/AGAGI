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


def _pmove0(preds):
    z = preds[0, :8] - preds[0, :8].max()
    e = np.exp(z)
    return float((e / e.sum())[0])


def test_torch_actor_critic_first_call_is_deferred():
    """Crédit TEMPOREL : le 1er learn n'a pas de V(s') -> différé (None). Le 2e apprend."""
    pop = make_population(_agents(2), backend="torch")
    obs = np.zeros((2, 59), dtype=np.float32)
    pop.forward(obs)
    assert pop.learn(np.array([1.0, 1.0], dtype=np.float32), [{"move": 0}, {"move": 0}]) is None
    pop.forward(obs)
    loss = pop.learn(np.array([1.0, 1.0], dtype=np.float32), [{"move": 0}, {"move": 0}])
    assert loss is not None and np.isfinite(loss)


def test_torch_critic_value_rises_with_reward():
    """Le critic (value head, nœud 28) apprend : récompense forte -> V(s) monte."""
    pop = make_population(_agents(2), backend="torch")
    np.random.seed(1)
    obs = np.random.randn(2, 59).astype(np.float32)
    v0 = float(pop.forward(obs)[0][0, 28])
    for _ in range(60):
        pop.forward(obs)
        pop.learn(np.array([5.0, 5.0], dtype=np.float32), [{"move": 0, "grab": 0, "rub": 0}] * 2)
    vN = float(pop.forward(obs)[0][0, 28])
    assert vN > v0


def test_torch_actor_raises_taken_move_prob():
    """L'acteur apprend : avantage positif sur move=0 -> P(move=0) augmente."""
    pop = make_population(_agents(2), backend="torch")
    np.random.seed(2)
    obs = np.random.randn(2, 59).astype(np.float32)
    before = _pmove0(pop.forward(obs)[0])
    for _ in range(60):
        pop.forward(obs)
        pop.learn(np.array([5.0, 5.0], dtype=np.float32), [{"move": 0, "grab": 0, "rub": 0}] * 2)
    after = _pmove0(pop.forward(obs)[0])
    assert after > before


def test_torch_learn_writes_genome_back():
    agents = _agents(2)
    pop = make_population(agents, backend="torch")
    before = agents[0].genome.W.copy()
    np.random.seed(1)
    obs = np.random.randn(2, 59).astype(np.float32)
    pop.forward(obs)
    pop.learn(np.array([1.0, 1.0], dtype=np.float32), [{"move": 0}, {"move": 0}])  # différé
    pop.forward(obs)
    pop.learn(np.array([1.0, 1.0], dtype=np.float32), [{"move": 0}, {"move": 0}])  # applique + write-back
    assert not np.allclose(before, agents[0].genome.W)


def test_torch_heterogeneous_dims_rejected_in_mvp():
    np.random.seed(0)
    mixed = [MambaAgent(num_nodes=172), MambaAgent(num_nodes=180)]
    with pytest.raises(NotImplementedError):
        make_population(mixed, backend="torch")
