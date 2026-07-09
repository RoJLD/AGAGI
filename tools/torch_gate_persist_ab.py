"""A/B PERSIST vs RESET du gate au rebuild du pop (cran 2, prerequis EDR-163). Le gate porte le binding
means->ends (EDR-158/159) mais est population-partage, PAS dans le genome -> perdu au rebuild sur
mortalite. Ce banc teste si le porter (inherit_gate) maintient le CAPABILITY_PAYS d'EDR-161 a travers
les rebuilds. Reutilise le monde 2-pas craft->USE de compositional_world_probe (EDR-161).

Usage : python tools/torch_gate_persist_ab.py   (env: TGP_SEEDS, TGP_EPISODES, TGP_REBUILD_EVERY, TGP_DEMAND)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel
from tools.compositional_world_probe import _energy, _softmax_np, CRAFT, USE, _MOVE
from tools.substrate_ab import compute_ab_verdict


def inherit_gate(new_pop, old_pop) -> bool:
    """Porte le gate appris (w_gate/b_gate) de old_pop vers new_pop a travers un rebuild. Le gate est
    population-partage, hors genome -> perdu au rebuild sauf carry-over explicite. No-op (False) si un
    gate est absent ou si les dimensions different. N'affecte PAS W (survit via genome)."""
    if getattr(new_pop, "w_gate", None) is None or getattr(old_pop, "w_gate", None) is None:
        return False
    if new_pop.w_gate.shape != old_pop.w_gate.shape or new_pop.b_gate.shape != old_pop.b_gate.shape:
        return False
    with torch.no_grad():
        new_pop.w_gate.data.copy_(old_pop.w_gate.data)
        new_pop.b_gate.data.copy_(old_pop.b_gate.data)
    return True
