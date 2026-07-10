import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent


class _FakePop:
    """Stub minimal du pop torch : expose seulement .N (dim cachee)."""
    def __init__(self, n):
        self.N = n
        self.B = 0


def _fresh_world():
    w = Biosphere3D(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    return w


def test_throw_gate_defaults_off():
    w = _fresh_world()
    assert w.torch_throw_gate is False
    assert w._throw_w is None and w._throw_opt is None
    assert w._throw_kills_tool == 0


def test_ensure_throw_gate_noop_when_off():
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = False        # gate OFF -> no-op meme si pop present
    w._torch_pop = _FakePop(8)
    w._ensure_throw_gate()
    assert w._throw_w is None


def test_ensure_throw_gate_builds_head():
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(8)
    w._ensure_throw_gate()
    assert tuple(w._throw_w.shape) == (8,)
    assert tuple(w._throw_b.shape) == (1,)
    assert w._throw_opt is not None and w._throw_shuf_rng is not None
    prev = w._throw_w
    w._ensure_throw_gate()            # idempotent : ne recree pas
    assert w._throw_w is prev


def _torch_world(n_agents=4, seed=0):
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    w = _fresh_world()
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    w.current_era = 1
    w.benchmark_mode = True
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    for a in w.agents:                       # semer un spear (contexte present)
        a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})
    return w


def test_gate_on_step_records_and_H_shape():
    w = _torch_world()
    w.step()
    # pop.H aligne sur les agents (assomption porteuse)
    assert w._torch_pop.H.shape[0] == len(w.agents)
    assert w._torch_pop.H.shape[1] == w._torch_pop.N
    for a in w.agents:
        assert "_throw_did" in a and isinstance(a["_throw_did"], bool)
        assert "_throw_ctx" in a and isinstance(a["_throw_ctx"], bool)
        assert "_throw_kill_tool" in a and isinstance(a["_throw_kill_tool"], bool)
        assert "throw" in a["_pg"]


def test_gate_off_is_nonregressive():
    np.random.seed(1)
    w = _fresh_world()
    for _ in range(4):
        w.add_agent(MambaAgent(), energy=80.0)
    w.current_era = 1
    w.benchmark_mode = True
    # use_torch_inworld reste False, torch_throw_gate reste False : legacy pur
    w.step()                                  # ne doit pas crasher
    for a in w.agents:
        assert "_throw_did" not in a          # aucun record B2 en legacy
        assert "_throw_kill_tool" not in a    # garde de flag : le bloc kill-outil ne fuit pas en legacy


def test_learn_throw_gate_steps_optimizer():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    # H fixe (3 agents x 6) ; agent 0 kill-outil, agent 1 throw-rate, agent 2 pas de throw
    w._torch_pop.H = torch.randn(3, 6)
    w.agents = [{"_throw_did": True, "_throw_kill_tool": True},
                {"_throw_did": True, "_throw_kill_tool": False},
                {"_throw_did": False, "_throw_kill_tool": False}]
    w0 = w._throw_w.detach().clone()
    loss = w._learn_throw_gate()
    assert loss is not None
    assert not torch.equal(w._throw_w.detach(), w0)   # l'optimiseur a bouge les poids
    assert w._throw_kills_tool == 1                    # 1 kill-outil credite


def test_learn_throw_gate_shuffle_runs():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w.torch_throw_shuffle = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    w._torch_pop.H = torch.randn(4, 6)
    w.agents = [{"_throw_did": bool(i % 2), "_throw_kill_tool": False} for i in range(4)]
    assert w._learn_throw_gate() is not None            # bras shuffle ne crashe pas


def test_learn_throw_gate_skips_on_desync():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    w._torch_pop.H = torch.randn(3, 6)
    w.agents = [{"_throw_did": False, "_throw_kill_tool": False}]   # B(3) != agents(1)
    assert w._learn_throw_gate() is None
