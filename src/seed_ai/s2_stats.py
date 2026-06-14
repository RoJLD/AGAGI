# src/seed_ai/s2_stats.py
"""
src/seed_ai/s2_stats.py — Stats PRÉ-ENREGISTRÉES du benchmark S2 (le monde exige-t-il l'intelligence ?).

Survie = distribution asymétrique/censurée -> effets NON-paramétriques (Cliff's delta, ratio de
médianes) + test APPARIÉ sur les différences (Wilcoxon signed-rank, approx. normale valide à K>=12).
Pas de scipy (hors dépendances) : tout en numpy + math.erf. Aucune hypothèse de normalité.
Détail : docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md (§8).
"""
import math
import numpy as np


def cliffs_delta(a, b):
    """Dominance stochastique de a sur b dans [-1, 1] : P(a>b) - P(a<b). Robuste, sans échelle."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return 0.0
    diff = a[:, None] - b[None, :]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / (a.size * b.size))


def median_ratio(a, b):
    """Ratio des médianes med(a)/med(b). inf si med(b)=0 et med(a)>0 ; 1.0 si les deux sont 0."""
    ma, mb = float(np.median(a)), float(np.median(b))
    if mb == 0.0:
        return float("inf") if ma > 0.0 else 1.0
    return ma / mb
