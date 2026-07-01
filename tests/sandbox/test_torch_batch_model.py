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
    import torch; torch.manual_seed(0)
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


def test_activation_swish_changes_dynamics():
    """EDR-139 : activation configurable. swish (x*sigmoid(x)) != tanh -> H diffère."""
    import torch
    np.random.seed(0)
    agents = [MambaAgent() for _ in range(2)]
    obs = (np.random.RandomState(2).randn(2, agents[0].genome.num_inputs) * 2.0).astype(np.float32)
    Tanh = type("TorchTanh", (TorchBatchModel,), {"ACTIVATION": "tanh"})
    Swish = type("TorchSwish", (TorchBatchModel,), {"ACTIVATION": "swish"})
    bt, bs = Tanh(agents), Swish(agents)
    lt = bt.forward(obs)[0]
    ls = bs.forward(obs)[0]
    assert not np.allclose(lt, ls)             # l'activation change bien la dynamique
    assert bt._act_kind == "tanh" and bs._act_kind == "swish"


def test_activation_auto_matches_world():
    """EDR-140 (reco migration) : défaut "auto" détecte l'activation LIVE du monde et la matche."""
    from src.agents.torch_batch_model import _detect_world_activation
    np.random.seed(0)
    agents = [MambaAgent() for _ in range(2)]
    assert TorchBatchModel.ACTIVATION == "auto"          # défaut = adaptateur fidèle
    detected = _detect_world_activation()
    assert detected in ("swish", "tanh")
    bm = TorchBatchModel(agents)                          # auto
    assert bm._act_kind == detected                      # résout vers l'activation du monde


def test_learns_and_carries_H_across_per_tick_rebuild():
    """BUGFIX EDR-137 : le monde reconstruit le batch model CHAQUE tick (world:992).
    Sans round-trip via l'agent, torch n'apprendrait jamais (self._prev jeté) et H repartirait
    à zéro. Ce test simule le pattern monde (nouvelle instance chaque tick, mêmes agents)."""
    import torch; torch.manual_seed(0)
    np.random.seed(0)
    agents = [MambaAgent() for _ in range(3)]
    W0 = agents[0].genome.W.copy()
    h_carried = False
    for t in range(6):
        bm = TorchBatchModel(agents)                     # <-- rebuild par-tick
        if t >= 2 and float(torch.max(torch.abs(bm.H))) > 0.0:
            h_carried = True                             # H restaurée depuis l'agent
        obs = (np.random.randn(3, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
        bm.forward(obs)
        bm.compute_policy_gradient(np.array([1.0, -1.0, 0.5], np.float32),
                                   [{"move": 1, "grab": 1, "rub": 0}] * 3)
    assert not np.allclose(W0, agents[0].genome.W)        # a APPRIS malgré le rebuild
    assert h_carried                                     # récurrence portée entre ticks
