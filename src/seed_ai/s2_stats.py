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


def bootstrap_ci(stat_fn, *arrays, n_boot=2000, alpha=0.05, seed=0):
    """IC percentile bootstrap d'une statistique. APPARIÉ : tous les arrays sont rééchantillonnés
    avec les MÊMES indices (préserve l'appariement seed-à-seed champion/baseline). stat_fn reçoit
    les arrays rééchantillonnés. Déterministe au seed."""
    arrays = [np.asarray(x, dtype=float) for x in arrays]
    n = len(arrays[0])
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot, dtype=float)
    for k in range(n_boot):
        idx = rng.integers(0, n, n)
        stats[k] = stat_fn(*[x[idx] for x in arrays])
    finite = stats[np.isfinite(stats)]
    if finite.size == 0:
        return float("nan"), float("nan")
    lo = float(np.percentile(finite, 100.0 * alpha / 2.0))
    hi = float(np.percentile(finite, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def holm(pvals):
    """Correction Holm-Bonferroni (step-down) du FWER. Renvoie les p-values ajustées (monotones,
    bornées à 1). Famille S2 = les 4 verdicts-monde (m=4), PAS les 12 comparaisons baseline."""
    pvals = np.asarray(pvals, dtype=float)
    m = pvals.size
    order = np.argsort(pvals)
    adj = np.empty(m, dtype=float)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])   # monotonie step-down
        adj[i] = min(1.0, running)
    return adj


def iut_pvalue(pvals):
    """Intersection-Union Test : pour conclure que le champion bat les 3 baselines (critère
    CONJONCTIF), la p-value du monde = MAX des p-values. Contrôle déjà le type-I à alpha, SANS
    correction (propriété IUT). C'est le bon outil pour un min-test, pas Holm."""
    return float(np.max(np.asarray(pvals, dtype=float)))


# Seuils PRÉ-ENREGISTRÉS (spec §8). Modifiables UNIQUEMENT via l'addendum post-pilote daté.
ALPHA = 0.05
CLIFF_THRESH = 0.33        # "large" (Romano) — effet principal
RATIO_LO_THRESH = 1.3      # borne_inf de l'IC bootstrap du ratio de médianes (corroborant)
EQUIV_MARGIN = 0.21        # |Cliff| < 0.21 = effet "negligible/petit" (Vargha-Delaney) -> équivalence (placeholder pilote)


def _compare(champ, base):
    """Une comparaison appariée champion-vs-baseline -> dict de stats."""
    champ = np.asarray(champ, dtype=float)
    base = np.asarray(base, dtype=float)
    d = champ - base
    _w, p = wilcoxon_signed_rank(d)
    delta = cliffs_delta(champ, base)
    ratio = median_ratio(champ, base)
    ratio_lo, ratio_hi = bootstrap_ci(median_ratio, champ, base, n_boot=2000, alpha=ALPHA, seed=0)
    return {"p": p, "cliff": delta, "ratio": ratio, "ratio_lo": ratio_lo, "ratio_hi": ratio_hi}


def s2_verdict(surv_champ, surv_baselines, life_champ, life_baselines,
               alpha=ALPHA, cliff_thresh=CLIFF_THRESH, ratio_lo_thresh=RATIO_LO_THRESH,
               equiv_margin=EQUIV_MARGIN):
    """Verdict S2 d'UN monde (table de décision §10). surv_baselines / life_baselines : dict
    {nom: liste de survies/life appariées par seed}. Renvoie un dict complet (verdict + stats).

    - Cohérence (§6) : le champion doit battre le MEILLEUR baseline sur le life_score (sa fitness
      d'entraînement) -> sinon VOID (le champion ne se comporte pas en champion dans ce régime).
    - Survie : IUT min-test (p_monde = max des p) ; effet sur le baseline le plus FORT (réflexe).
    - Issues : EXIGE / N'EXIGE PAS (équivalence) / ANTI-CORRÉLÉ / AMBIGU."""
    # --- Test de cohérence sur life_score (IUT) ---
    life_cmps = {k: _compare(life_champ, life_baselines[k]) for k in life_baselines}
    life_p = iut_pvalue([c["p"] for c in life_cmps.values()])
    life_best_cliff = min(c["cliff"] for c in life_cmps.values())   # pire baseline sur la cohérence
    coherence_ok = (life_p < alpha) and (life_best_cliff > 0.0)
    if not coherence_ok:
        return {"verdict": "VOID", "coherence_ok": False, "life_p": life_p,
                "survival": {k: _compare(surv_champ, surv_baselines[k]) for k in surv_baselines}}

    # --- Survie ---
    cmps = {k: _compare(surv_champ, surv_baselines[k]) for k in surv_baselines}
    p_monde = iut_pvalue([c["p"] for c in cmps.values()])
    # baseline le plus FORT = plus haute survie médiane (le plus dur à battre, attendu = réflexe)
    strongest = max(surv_baselines, key=lambda k: np.median(surv_baselines[k]))
    s = cmps[strongest]

    if p_monde < alpha and s["cliff"] >= cliff_thresh and s["ratio_lo"] >= ratio_lo_thresh:
        verdict = "EXIGE"
    elif s["cliff"] < -cliff_thresh and p_monde < alpha:
        verdict = "ANTI-CORRELE"
    elif abs(s["cliff"]) < equiv_margin:
        verdict = "N'EXIGE PAS"
    else:
        verdict = "AMBIGU"

    return {"verdict": verdict, "coherence_ok": True, "life_p": life_p,
            "p_monde": p_monde, "strongest_baseline": strongest,
            "survival": cmps}
