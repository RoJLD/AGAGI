"""Tests de l'abstraction de backend neuronal (ADR-003).

Frontière = population batchée. Le backend `legacy` enveloppe le `MambaBatchModel`
numpy existant et doit être STRICTEMENT non-régressif (preds identiques au modèle
direct). Le seam `make_population(..., backend=...)` accueillera le backend torch (Axe 1).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from src.agents.backend import make_population, LegacyPopulationModel, PopulationModel


def _agents(n=3, seed=0):
    np.random.seed(seed)
    return [MambaAgent() for _ in range(n)]


def test_make_population_legacy_returns_population_model():
    pop = make_population(_agents(3), backend="legacy")
    assert isinstance(pop, PopulationModel)
    assert isinstance(pop, LegacyPopulationModel)
    assert pop.B == 3


def test_unknown_backend_raises():
    with pytest.raises(NotImplementedError):
        make_population(_agents(2), backend="jax")  # non encore implémenté (seam ADR-003)


def test_forward_returns_preds_and_compute_spent():
    pop = make_population(_agents(3), backend="legacy")
    preds, compute_spent = pop.forward(np.zeros((3, 59), dtype=np.float32))
    assert preds.shape[0] == 3


def test_legacy_forward_matches_direct_batch_model():
    """Non-régression : wrapper legacy == MambaBatchModel direct (agents identiques)."""
    obs = np.zeros((3, 59), dtype=np.float32)
    direct = MambaBatchModel(_agents(3, seed=7))
    np.random.seed(123)
    preds_d, _ = direct.forward(obs)
    pop = make_population(_agents(3, seed=7), backend="legacy")
    np.random.seed(123)
    preds_w, _ = pop.forward(obs)
    assert np.allclose(preds_d, preds_w)


def test_learn_updates_genome_in_place():
    agents = _agents(2)
    pop = make_population(agents, backend="legacy")
    np.random.seed(1)
    pop.forward(np.random.randn(2, 59).astype(np.float32))  # obs non-nulle -> état caché non-nul
    before = agents[0].genome.W.copy()
    pop.learn(np.array([5.0, 5.0], dtype=np.float32))  # Hebbien : avantage fort -> maj W in place
    assert not np.allclose(before, agents[0].genome.W)


def test_extract_returns_agents():
    agents = _agents(2)
    pop = make_population(agents, backend="legacy")
    assert pop.extract() is agents
