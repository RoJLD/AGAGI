"""CALIB-ALIAS — l'ablation within-subject d'un canal d'entrée reste-t-elle CHIRURGICALE sur le vrai
substrat récurrent, ou fuit-elle vers une capacité de contrôle par la représentation partagée ?

On fait tourner un génome-étalon dans le VRAI recurrent_forward, entrée intacte vs colonne `x_input`=0,
et on lit la variation d'une sortie de CONTRÔLE. Fuite -> l'ablation n'est pas chirurgicale. Le nom
`run_*probe` / `*verdict*` trippe volontairement le cliquet. Usage : python tools/functional_aliasing_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.seed_ai.rl_evolution import recurrent_forward


def _settle(genome, obs_vec, settle_ticks):
    """recurrent_forward `settle_ticks` fois (H rebouclé) ; renvoie preds (O,) copié."""
    N = genome.num_nodes
    H = np.zeros((1, N), dtype=np.float32)
    Hh = np.zeros((1, 1, N), dtype=np.float32)
    Hp = np.zeros((1, N), dtype=np.float32)
    obs = np.asarray([obs_vec], dtype=np.float32)
    preds = None
    for _ in range(int(settle_ticks)):
        preds, H, Hh, Hp, _ = recurrent_forward(genome, obs, H, Hh, Hp, 0.0)
    return preds[0].copy()


def run_functional_aliasing_probe(genome, x_input=0, x_readout=0, control_readout=1,
                                  settle_ticks=4, test_input=(1.0, 1.0)):
    """Ablate chirurgicalement l'entrée `x_input` (colonne -> 0) et mesure la fuite sur la sortie de
    contrôle `control_readout` vs la réponse de la capacité propre `x_readout`. Voir docstring du module."""
    intact_vec = list(test_input)
    ablated_vec = list(test_input)
    ablated_vec[int(x_input)] = 0.0
    intact = _settle(genome, intact_vec, settle_ticks)
    ablated = _settle(genome, ablated_vec, settle_ticks)
    leakage = float(abs(intact[int(control_readout)] - ablated[int(control_readout)]))
    x_response = float(abs(intact[int(x_readout)] - ablated[int(x_readout)]))
    return {"leakage": leakage, "x_response": x_response,
            "control_intact": float(intact[int(control_readout)]),
            "control_ablated": float(ablated[int(control_readout)]),
            "verdict": functional_aliasing_verdict(leakage, x_response)}


def functional_aliasing_verdict(leakage, x_response, tol=1e-9):
    """VACUOUS_ABLATION si l'ablation ne fait RIEN à la capacité propre (générateur A échoué) ; SURGICAL
    si la fuite sur le contrôle est nulle ; FUNCTIONAL_LEAK sinon."""
    if float(x_response) <= float(tol):
        return "VACUOUS_ABLATION"
    if float(leakage) <= float(tol):
        return "SURGICAL"
    return "FUNCTIONAL_LEAK"
