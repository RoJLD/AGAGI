# tests/sandbox/test_baseline_models.py
import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.baseline_models import RandomActionBatchModel


def _agents(n=4):
    out = []
    for _ in range(n):
        a = MambaAgent()
        a.surprise = 9.9            # valeur "sale" à écraser
        a.surprise_momentum = 9.9
        out.append(a)
    return out


def test_random_action_forward_shape_matches_outputs():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    O = max(a.genome.num_outputs for a in agents)
    logits, spent = bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert logits.shape == (len(agents), O)
    assert spent.shape == (len(agents),)
    assert np.all(spent == 0.0)         # pas de rêve


def test_random_action_writes_zero_surprise():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert all(a.surprise == 0.0 and a.surprise_momentum == 0.0 for a in agents)


def test_random_action_compute_policy_gradient_is_noop():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.compute_policy_gradient(np.zeros(len(agents)), None)     # ne lève pas


def test_random_action_is_seeded():
    agents = _agents()
    obs = np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32)
    np.random.seed(123); a1, _ = RandomActionBatchModel(agents).forward(obs)
    np.random.seed(123); a2, _ = RandomActionBatchModel(agents).forward(obs)
    assert np.allclose(a1, a2)          # tire du flux global seedé (appariement)
