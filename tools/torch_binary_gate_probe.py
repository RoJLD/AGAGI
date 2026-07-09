"""Gate de conditionnement sur action BINAIRE (cran 2, Brique A). Le gate livre (EDR-159/165) biaise une
politique CATEGORIELLE (8 moves) ; l'action "ends" biosphere = throw (logit 8, BINAIRE). Ce harnais teste
en ISOLATION si un readout de H apprend a conditionner throw sur did_craft sous credit episodique, avant
tout cablage biosphere. Monde 2-pas binaire ; ne touche NI backend_torch NI la biosphere.

Usage : python tools/torch_binary_gate_probe.py   (env: TBG_SEEDS, TBG_EPISODES, TBG_AGENTS)
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
from tools.compositional_world_probe import _softmax_np, CRAFT, _MOVE
from tools.substrate_ab import compute_ab_verdict


def _energy_binary(throw, did_craft, hunger=-0.3):
    """Energie/episode du monde 2-pas binaire. +1 SSI composition (throw ET craft) ; faim sinon
    (throw-sans-craft, craft-sans-throw, abstention) -> l'abstention COUTE, force l'engagement."""
    return 1.0 if (throw and did_craft) else hunger


def _binding_gap(throws, did_crafts):
    """Instrument de binding direct (EDR-126) : P(throw|did_craft) - P(throw|¬did_craft). >0 = throw
    conditionne sur le craft ; ~0 = throw independant du craft (pas de binding)."""
    throws = np.asarray(throws, dtype=np.float32)
    dc = np.asarray(did_crafts, dtype=bool)
    p_given = float(throws[dc].mean()) if dc.any() else 0.0
    p_notgiven = float(throws[~dc].mean()) if (~dc).any() else 0.0
    return p_given - p_notgiven
