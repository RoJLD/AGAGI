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
