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


def jonckheere_terpstra(groups):
    """Test de tendance ordonnée de Jonckheere-Terpstra (groupes pré-ordonnés).
    H1 (one-sided) : les médianes croissent avec l'ordre des groupes.
    Stat J = somme sur i<j de #{(x in g_i, y in g_j) : y>x} (+0.5 par ex-aequo).
    Approx normale (sans correction d'ex-aequo — noté). -> {stat, z, p_one_sided, p_two_sided}."""
    gs = [np.asarray(g, dtype=float) for g in groups]
    k = len(gs)
    J = 0.0
    for i in range(k):
        for j in range(i + 1, k):
            for x in gs[i]:
                J += float(np.sum(gs[j] > x) + 0.5 * np.sum(gs[j] == x))
    N = sum(len(g) for g in gs)
    sum_ni2 = sum(len(g) ** 2 for g in gs)
    mean_J = (N ** 2 - sum_ni2) / 4.0
    var_J = (N ** 2 * (2 * N + 3) - sum(len(g) ** 2 * (2 * len(g) + 3) for g in gs)) / 72.0
    z = (J - mean_J) / math.sqrt(var_J) if var_J > 0 else 0.0
    return {
        "stat": float(J),
        "z": float(z),
        "p_one_sided": float(_norm_sf(z)),
        "p_two_sided": float(min(1.0, 2.0 * _norm_sf(abs(z)))),
    }


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


def bootstrap_ci(data, statistic_fn, n_boot=2000, alpha=0.05, seed=0):
    """IC percentile bootstrap (ré-échantillonnage avec remise). Seedé -> reproductible."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    rng = np.random.default_rng(int(seed))
    stats = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        stats[b] = statistic_fn(data[rng.integers(0, n, n)])
    lo = float(np.percentile(stats, 100 * alpha / 2.0))
    hi = float(np.percentile(stats, 100 * (1.0 - alpha / 2.0)))
    return lo, hi


def ols_slope(x, y):
    """Pente OLS (moindres carrés) de y sur x."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.polyfit(x, y, 1)[0])
