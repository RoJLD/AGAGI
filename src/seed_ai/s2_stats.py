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


def _phi(z):
    """CDF de la loi normale centrée réduite (sans scipy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _average_ranks(values):
    """Rangs moyens (gère les ex aequo) — valeurs >= 0 (abs des différences)."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # rangs 1-indexés, moyenne sur les ex aequo
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon_signed_rank(d):
    """Test de Wilcoxon signé sur les différences appariées d (champion - baseline).
    Approximation normale avec correction de continuité (valide à n>=12, plancher S2).
    Renvoie (W_plus, p_bilatéral). Les zéros sont retirés (convention). p=1.0 si n=0."""
    d = np.asarray(d, dtype=float)
    d = d[d != 0.0]
    n = d.size
    if n == 0:
        return 0.0, 1.0
    ranks = _average_ranks(np.abs(d))
    w_plus = float(np.sum(ranks[d > 0]))
    mean = n * (n + 1) / 4.0
    var = n * (n + 1) * (2 * n + 1) / 24.0
    if var == 0.0:
        return w_plus, 1.0
    cc = 0.5 * np.sign(w_plus - mean)            # correction de continuité
    z = (w_plus - mean - cc) / math.sqrt(var)
    p = 2.0 * (1.0 - _phi(abs(z)))
    return w_plus, float(min(1.0, max(0.0, p)))
