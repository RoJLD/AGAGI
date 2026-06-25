"""tools/g_fidelity_probe.py — Sonde de fidélité de g (NAS Axe 3, spec dream-offline, composant A).
go/no-go : g(H,a)→H' prédit-il les transitions latentes mieux que la baseline « pas de changement » ?
Si NON -> escalader vers g bilinéaire avant de bâtir Dyna. AUCUN changement du code cœur.
Usage : GFP_SEEDS=0,1,2 python tools/g_fidelity_probe.py"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def transition_error(H_prev, g_delta, H_next):
    """(g_err, base_err) pour une transition latente. g_err = prédiction de g ; base_err = baseline."""
    H_prev = np.asarray(H_prev, dtype=np.float32)
    g_delta = np.asarray(g_delta, dtype=np.float32)
    H_next = np.asarray(H_next, dtype=np.float32)
    g_err = float(np.mean((H_prev + g_delta - H_next) ** 2))
    base_err = float(np.mean((H_prev - H_next) ** 2))
    return g_err, base_err


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def fidelity_verdict(ratios) -> dict:
    """ratios[i] = g_err/base_err par transition. g UTILE = ratio < 1 (g bat la baseline)."""
    ratios = [float(r) for r in ratios]
    n = len(ratios)
    if n == 0:
        return {"median_ratio": 1.0, "n_favorable": 0, "n": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = st.median(ratios)
    n_fav = sum(1 for r in ratios if r < 1.0)            # favorable = g meilleur
    eff = [r for r in ratios if r != 1.0]
    sign_p = _sign_p(sum(1 for r in eff if r < 1.0), len(eff))
    if med < 0.95 and 2 * n_fav > n:
        verdict = "G_FIDELE"
    elif med > 1.05:
        verdict = "G_INUTILE"
    else:
        verdict = "NEUTRE"
    return {"median_ratio": float(med), "n_favorable": int(n_fav), "n": int(n),
            "sign_p": float(sign_p), "verdict": verdict}
