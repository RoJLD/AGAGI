import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def _gated_pop(n=4, seed=0):
    np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGET = 4        # USE
    try:
        pop = make_population([MambaAgent() for _ in range(n)], backend="torch")
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved
    return pop


def test_inherit_gate_copies_values():
    import torch
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    with torch.no_grad():
        old.w_gate += 3.0                        # rend le gate distinct de l'init
        old.b_gate -= 1.5
    new = _gated_pop(seed=1)
    ok = inherit_gate(new, old)
    assert ok is True
    assert torch.allclose(new.w_gate.data, old.w_gate.data)
    assert torch.allclose(new.b_gate.data, old.b_gate.data)


def test_inherit_gate_noop_when_gate_absent():
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    plain = make_population([MambaAgent() for _ in range(4)], backend="torch")  # gate OFF -> w_gate None
    assert inherit_gate(plain, old) is False     # cible sans gate -> no-op
    assert inherit_gate(old, plain) is False      # source sans gate -> no-op
