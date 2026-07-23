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


def main():
    """Go/no-go CALIB-ALIAS. GO ssi : disjoint -> SURGICAL (no-op exact) ET le garde comportemental passe ;
    partagé -> FUNCTIONAL_LEAK ET le garde comportemental TIRE. Renvoie 0 (GO) ou 1 (NO-GO)."""
    from tools.experiment_preflight import (declare_design, assert_no_functional_aliasing, PreflightError)
    from tools.ground_truth_worlds import make_aliasing_genome

    design = declare_design(
        question="L'ablation within-subject d'un canal reste-t-elle chirurgicale (pas de fuite vers une "
                 "capacité de contrôle) sur le vrai substrat récurrent ?",
        replication_unit="génome-étalon (déterministe)", n_independent=1,
        links={"cablage_impose->reponse": "measured", "ablation->fuite": "measured"},
        cost_estimate="pur numpy, < 1 s")
    print(f"DESIGN: {design['replication_unit']}")

    disjoint = run_functional_aliasing_probe(make_aliasing_genome(0.0))
    shared = run_functional_aliasing_probe(make_aliasing_genome(1.0))

    # disjoint : le garde comportemental DOIT passer (contrôle inchangé)
    guard_ok_on_disjoint = True
    try:
        assert_no_functional_aliasing(disjoint["control_intact"], disjoint["control_ablated"])
    except PreflightError:
        guard_ok_on_disjoint = False
    # partagé : le garde comportemental DOIT tirer (contrôle a bougé)
    guard_fires_on_shared = False
    try:
        assert_no_functional_aliasing(shared["control_intact"], shared["control_ablated"])
    except PreflightError:
        guard_fires_on_shared = True

    passed = (disjoint["verdict"] == "SURGICAL" and disjoint["leakage"] == 0.0 and guard_ok_on_disjoint
              and shared["verdict"] == "FUNCTIONAL_LEAK" and guard_fires_on_shared)
    verdict = "GO (ablation isolable + garde opposable)" if passed else "NO-GO"
    print(f"VERDICT CALIB-ALIAS = {verdict} | disjoint leakage={disjoint['leakage']:.4f} ({disjoint['verdict']}) "
          f"garde_passe={guard_ok_on_disjoint} | partagé leakage={shared['leakage']:.4f} "
          f"({shared['verdict']}) garde_tire={guard_fires_on_shared}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
