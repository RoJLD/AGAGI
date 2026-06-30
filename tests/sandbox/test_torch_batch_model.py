"""Test TorchBatchModel — forward conforme (B×O) avec padding hétérogène.

Task 1 (TDD) : test d'échec AVANT l'implémentation, puis PASS après.
Skip propre si torch absent.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np, pytest
pytest.importorskip("torch")
from src.agents.mamba_agent import MambaAgent
from src.agents.torch_batch_model import TorchBatchModel

def test_forward_shape_heterogeneous():
    np.random.seed(0)
    models = [MambaAgent(), MambaAgent()]  # même dim ici ; padding teste l'élastique
    bm = TorchBatchModel(models)
    O = max(m.genome.num_outputs for m in models)
    logits, spent = bm.forward(np.zeros((2, models[0].genome.num_inputs), dtype=np.float32))
    assert logits.shape == (2, O)
    assert spent.shape == (2,)
    assert np.all(np.isfinite(logits))


def test_forward_syncs_agent_state():
    np.random.seed(0)
    m = MambaAgent()
    bm = TorchBatchModel([m])
    bm.forward(np.zeros((1, m.genome.num_inputs), dtype=np.float32))
    assert isinstance(m.surprise_momentum, float)
    assert m.attention_mask is not None and m.ntm_memory is not None


def test_cpg_actor_critic_learns():
    np.random.seed(0)
    m = MambaAgent()
    bm = TorchBatchModel([m])
    rng = np.random.RandomState(1)
    obs = (rng.randn(1, m.genome.num_inputs) * 0.5).astype(np.float32)
    v0 = float(bm.forward(obs)[0][0, 28])
    W0 = m.genome.W.copy()
    for _ in range(40):
        bm.forward(obs)
        bm.compute_policy_gradient(
            np.array([5.0], np.float32),
            [{"move": 0, "grab": 0, "rub": 0}],
        )
    vN = float(bm.forward(obs)[0][0, 28])
    assert vN > v0 and not np.allclose(W0, m.genome.W)
