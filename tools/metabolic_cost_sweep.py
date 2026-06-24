# tools/metabolic_cost_sweep.py
"""tools/metabolic_cost_sweep.py — Mesure X2 de D1 (coût métabolique d'activation, NAS Axe D-1).
Le coût métabolique sélectionne-t-il des connectomes efficients sans effondrer la compétence ?
Trajectoires évolutives appariées multi-seed, banc stoneage survivable (sweet-spot EDR 085).
Spec : docs/superpowers/specs/2026-06-24-NAS-D1-Measurement-design.md
Usage : MCS_SEEDS=0,1,2 MCS_SWEEP=0,0.001,0.01 python tools/metabolic_cost_sweep.py"""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

log = logging.getLogger("AGIseed.MetabolicCostSweep")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_sweep_verdict(per_coef: List[Dict], eff_band: float = 0.05,
                          collapse_frac: float = 0.90) -> Dict:
    """per_coef[i] = {coef, eff_ratios:[par seed], surv_ratios:[par seed]} -> verdict par coef. PUR."""
    out = []
    for entry in per_coef:
        eff = list(entry.get("eff_ratios", []))
        surv = list(entry.get("surv_ratios", []))
        n = len(eff)
        if n == 0:
            out.append({"coef": entry.get("coef"), "median_eff": 0.0, "n": 0,
                        "n_favorable": 0, "sign_p": 1.0, "collapsed": False, "verdict": "NEUTRE"})
            continue
        median_eff = float(statistics.median(eff))
        n_fav = sum(1 for r in eff if r > 1.0)
        effective = [r for r in eff if r != 1.0]
        sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
        collapsed = bool(surv) and statistics.median(surv) < collapse_frac
        if collapsed:
            verdict = "NUIT"
        elif median_eff > 1.0 + eff_band and 2 * n_fav > n:
            verdict = "EFFICACE"
        else:
            verdict = "NEUTRE"
        out.append({"coef": entry.get("coef"), "median_eff": median_eff, "n": n,
                    "n_favorable": n_fav, "sign_p": sign_p, "collapsed": collapsed, "verdict": verdict})
    return {"per_coef": out}
