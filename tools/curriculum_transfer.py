"""Harnais Ratio de Transfert (Dev #3, mesure). Le curriculum développemental transfère-t-il mieux
que tabula-rasa ? Expérience appariée multi-seed à BUDGET COMPUTE ÉGAL, verdict + provenance ledger.
Spec : docs/superpowers/specs/2026-06-23-Curriculum-Transfer-design.md"""
import os
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

log = logging.getLogger("AGIseed.CurriculumTransfer")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe). Sans dépendance (math.comb)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_transfer_verdict(ratios: List[float], neutral_band: float = 0.05) -> Dict:
    """ratio par seed -> {n, median_ratio, n_favorable, sign_p, verdict}. PUR (testable sans biosphère)."""
    n = len(ratios)
    if n == 0:
        return {"n": 0, "median_ratio": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(ratios))
    n_fav = sum(1 for r in ratios if r > 1.0)
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    if med > 1.0 + neutral_band and 2 * n_fav > n:
        verdict = "TRANSFERE"
    elif med < 1.0 - neutral_band and 2 * n_fav < n:
        verdict = "NUIT"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_ratio": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}
