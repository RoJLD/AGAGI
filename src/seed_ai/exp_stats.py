"""
src/seed_ai/exp_stats.py — Tests statistiques pré-enregistrés (EDR 088), numpy PUR (pas de scipy).

Appariés (Wilcoxon signed-rank), tendance ordonnée (Jonckheere-Terpstra), bootstrap IC, OLS.
Loi normale via math.erfc (stdlib). Validé contre scipy dans les tests (oracle), mais sans
dépendance scipy à l'exécution.
"""
import math
import numpy as np


def _norm_sf(x):
    """Survie de la loi normale standard : P(Z > x)."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def _average_ranks(a):
    """Rangs 1..n avec moyenne des rangs sur les ex-aequo."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    sa = a[order]
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j < len(a) and sa[j] == sa[i]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0   # moyenne des rangs (1-based) i+1..j
        i = j
    return ranks


def wilcoxon_signed_rank(d):
    """Wilcoxon signed-rank apparié (vs 0), approx normale + correction de continuité.
    Zéros écartés ; ex-aequo en rangs moyens + correction de variance. -> {stat, z, p, n}."""
    d = np.asarray(d, dtype=float)
    d = d[d != 0.0]
    n = len(d)
    if n == 0:
        return {"stat": 0.0, "z": 0.0, "p": 1.0, "n": 0}
    absd = np.abs(d)
    ranks = _average_ranks(absd)
    w_plus = float(ranks[d > 0].sum())
    w_minus = float(ranks[d < 0].sum())
    w = min(w_plus, w_minus)
    mean_w = n * (n + 1) / 4.0
    _, counts = np.unique(absd, return_counts=True)
    tie = float(((counts ** 3) - counts).sum())
    var_w = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    if var_w <= 0:
        return {"stat": w, "z": 0.0, "p": 1.0, "n": n}
    cc = 0.5 * np.sign(mean_w - w)          # continuité vers la moyenne
    z = (w - mean_w + cc) / math.sqrt(var_w)
    p = min(1.0, 2.0 * _norm_sf(abs(z)))    # bilatéral
    return {"stat": w, "z": float(z), "p": float(p), "n": n}


def paired_summary(d):
    """Résumé d'une diff appariée : moyenne, SE, win-rate (P(d>0)), p de Wilcoxon."""
    a = np.asarray(d, dtype=float)
    se = a.std(ddof=1) / math.sqrt(len(a)) if len(a) > 1 else float("inf")
    return {
        "mean": float(a.mean()),
        "se": float(se),
        "win_rate": float(np.mean(a > 0)),
        "wilcoxon_p": wilcoxon_signed_rank(a)["p"],
        "n": int(len(a)),
    }
