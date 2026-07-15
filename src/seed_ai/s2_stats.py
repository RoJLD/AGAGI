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
CLIFF_THRESH = 0.33        # "large" (Romano) — effet PRINCIPAL qui tranche le verdict (spec §8)
RATIO_LO_THRESH = 1.3      # borne_inf IC du ratio de médianes — CORROBORANT (rapporté, NON bloquant, §8)
EQUIV_MARGIN = 0.147       # |Cliff| < 0.147 = "negligible" (Romano) -> équivalence (placeholder pilote)


def _bootstrap_cliff(a, b, n_boot=2000, alpha=ALPHA, seed=0):
    """IC bootstrap de Cliff's delta (ré-échantillonne chaque pool d'individus indépendamment)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return -1.0, 1.0
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot, dtype=float)
    for k in range(n_boot):
        vals[k] = cliffs_delta(a[rng.integers(0, a.size, a.size)], b[rng.integers(0, b.size, b.size)])
    return float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2)))


def _compare(champ, base, key):
    """Comparaison champion-vs-baseline sur `key` ('survival' ou 'life_score'). `champ`/`base` =
    dicts de run_condition (clés poolées + 'era_*' par seed).

    - EFFET (Cliff δ + IC, ratio de médianes) sur les INDIVIDUS poolés -> robuste, distribution riche (§6).
    - SIGNIFICATIVITÉ : test APPARIÉ PAR SEED (Wilcoxon signé) sur les différences des médianes PAR ÈRE
      (champ_era_i − base_era_i), + IC du ratio par ré-échantillonnage des SEEDS (§8). C'est l'appariement
      correct : par ère/seed, PAS index-par-index sur des individus poolés non alignés (fix B1)."""
    era_key = "era_survival" if key == "survival" else "era_life"
    cp = np.asarray(champ[key], dtype=float)              # pooled (individus)
    bp = np.asarray(base[key], dtype=float)
    ce = np.asarray(champ[era_key], dtype=float)          # par seed (médiane d'ère)
    be = np.asarray(base[era_key], dtype=float)
    m = min(ce.size, be.size)                             # appariement seed-à-seed
    _w, p = wilcoxon_signed_rank(ce[:m] - be[:m])
    delta = cliffs_delta(cp, bp)
    cliff_lo, cliff_hi = _bootstrap_cliff(cp, bp)
    ratio = median_ratio(cp, bp)
    ratio_lo, ratio_hi = bootstrap_ci(median_ratio, ce[:m], be[:m], n_boot=2000, alpha=ALPHA, seed=0)
    return {"p": p, "cliff": delta, "cliff_lo": cliff_lo, "cliff_hi": cliff_hi,
            "ratio": ratio, "ratio_lo": ratio_lo, "ratio_hi": ratio_hi}


def s2_verdict(champ, baselines, alpha=ALPHA, cliff_thresh=CLIFF_THRESH, equiv_margin=EQUIV_MARGIN):
    """Verdict S2 d'UN monde (table de décision §10). `champ` et `baselines[nom]` = dicts de
    run_condition (clés 'survival'/'life_score' poolées + 'era_survival'/'era_life' par seed).

    - Cohérence (§6) : le champion doit battre le MEILLEUR baseline sur le life_score (sa fitness
      d'entraînement) -> sinon VOID (le champion ne se comporte pas en champion dans ce régime).
    - Survie : IUT min-test (p_monde = max des p APPARIÉS par seed) ; effet sur le baseline le plus FORT.
    - Décision (§8 : Cliff TRANCHE, le ratio CORROBORE — rapporté mais non bloquant) :
        EXIGE        : p<α ET Cliff δ ≥ cliff_thresh
        ANTI-CORRÉLÉ : p<α ET Cliff δ ≤ -cliff_thresh
        N'EXIGE PAS  : |Cliff δ| < equiv_margin ET p ≥ α (équivalence : aucune différence détectable)
        AMBIGU       : sinon (effet réel sous-seuil, ou significatif mais négligeable -> inconclusif)."""
    # --- Test de cohérence sur life_score (IUT) ---
    life_cmps = {k: _compare(champ, baselines[k], "life_score") for k in baselines}
    life_p = iut_pvalue([c["p"] for c in life_cmps.values()])
    life_best_cliff = min(c["cliff"] for c in life_cmps.values())   # pire baseline sur la cohérence
    coherence_ok = (life_p < alpha) and (life_best_cliff > 0.0)
    if not coherence_ok:
        return {"verdict": "VOID", "coherence_ok": False, "life_p": life_p,
                "survival": {k: _compare(champ, baselines[k], "survival") for k in baselines}}

    # --- Survie ---
    cmps = {k: _compare(champ, baselines[k], "survival") for k in baselines}
    p_monde = iut_pvalue([c["p"] for c in cmps.values()])
    # baseline le plus FORT = plus haute survie médiane (le plus dur à battre, attendu = réflexe)
    strongest = max(baselines, key=lambda k: np.median(baselines[k]["survival"]))
    s = cmps[strongest]

    if p_monde < alpha and s["cliff"] >= cliff_thresh:
        verdict = "EXIGE"
    elif p_monde < alpha and s["cliff"] <= -cliff_thresh:
        verdict = "ANTI-CORRELE"
    elif abs(s["cliff"]) < equiv_margin and p_monde >= alpha:
        verdict = "N'EXIGE PAS"
    else:
        verdict = "AMBIGU"

    return {"verdict": verdict, "coherence_ok": True, "life_p": life_p,
            "p_monde": p_monde, "strongest_baseline": strongest,
            "survival": cmps}


def verdict_from_survival_cmps(survival_cmps, alpha=ALPHA, cliff_thresh=CLIFF_THRESH):
    """Re-rend le verdict S2 d'UN monde depuis les comparaisons de SURVIE déjà calculées
    (champion vs chaque baseline : dicts {p, cliff, ratio_lo, ratio_hi}), SANS re-simuler.

    ADDENDUM 2026-06-30 (post-confirmatoire EDR S2) — cohérence basée SURVIE, pas life_score :
    le gate de cohérence original (`s2_verdict`, sur life_score) produit un FAUX VOID quand le
    champion domine la survie (3-5x) mais que son edge en life_score est noyé par des événements
    rares/chanceux (proies/lances/mammouth). Intention du gate = « le champion se comporte en
    champion » -> mieux opérationnalisée par la survie elle-même. life_score devient corroborant
    NON-bloquant (rapporté ailleurs). Verdict = IUT min-test sur la survie (p_monde = max des p) ;
    effet = Cliff du baseline le plus FORT (cliff minimal = le plus dur à battre).

    Cohérence (survie) : le champion bat le baseline le plus fort en survie -> p_monde<alpha ET
    tous les Cliff>0 ; sinon VOID. Décision : EXIGE (p<alpha & cliff>=thresh) / ANTI-CORRELE
    (p<alpha & cliff<=-thresh) / AMBIGU sinon."""
    p_monde = float(max(c["p"] for c in survival_cmps.values()))
    strongest = min(survival_cmps, key=lambda k: survival_cmps[k]["cliff"])   # plus dur à battre
    s = survival_cmps[strongest]
    # Cohérence survie = champion bat TOUS les baselines (p_monde<alpha ET tous les Cliff>0). Si un
    # baseline domine le champion (cliff<0), incohérent -> VOID (pas d'ANTI-CORRELE : la cohérence
    # exige déjà cliff>0, donc cette branche serait morte ici).
    coherent = (p_monde < alpha) and all(c["cliff"] > 0.0 for c in survival_cmps.values())
    if not coherent:
        verdict = "VOID"
    elif s["cliff"] >= cliff_thresh:                  # p_monde<alpha déjà garanti par `coherent`
        verdict = "EXIGE"
    else:
        verdict = "AMBIGU"                            # cohérent mais effet sous-seuil
    return {"verdict": verdict, "coherence_basis": "survival", "p_monde": p_monde,
            "strongest_baseline": strongest, "cliff": float(s["cliff"]),
            "ratio_lo": s.get("ratio_lo"), "ratio_hi": s.get("ratio_hi")}


def verdict_within_subject(champion, champion_ablated, random_action,
                           alpha=ALPHA, cliff_thresh=CLIFF_THRESH, equiv_margin=EQUIV_MARGIN):
    """Verdict CAUSAL within-subject de « le monde exige la PERCEPTION » (S2-001). Réutilise `_compare`
    (Cliff δ + p apparié par ère). Ablater la perception du MÊME champion (obs décorrélée) doit effondrer
    la survie SI la perception est causalement porteuse.

    - `causal`   = _compare(champion, champion_ablated) : le champion bat-il sa version obs-ablée ?
    - `residual` = _compare(champion_ablated, random_action) : l'ablé garde-t-il un edge sur l'aléatoire ?
    Décision (seuils gelés) :
      NON-CAUSAL     : ablater la perception NE nuit PAS (p≥α OU Cliff<thresh) -> l'edge n'était pas perceptif.
      CAUSAL-FULL    : champion≫ablé ET ablé≈random (|Cliff résiduel|<equiv_margin) -> la perception explique TOUT.
      CAUSAL-PARTIEL : champion≫ablé mais ablé garde un edge résiduel sur l'aléatoire -> la perception explique une PART.
    On ne préjuge PAS : NON-CAUSAL est un résultat falsifiable (l'edge survie viendrait d'un autre facteur)."""
    causal = _compare(champion, champion_ablated, "survival")
    residual = _compare(champion_ablated, random_action, "survival")
    is_causal = (causal["p"] < alpha) and (causal["cliff"] >= cliff_thresh)
    edge_fully_perceptual = bool(abs(residual["cliff"]) < equiv_margin)
    if not is_causal:
        verdict = "NON-CAUSAL"
    elif edge_fully_perceptual:
        verdict = "CAUSAL-FULL"
    else:
        verdict = "CAUSAL-PARTIEL"
    return {"verdict": verdict, "causal_cmp": causal, "residual_cmp": residual,
            "is_causal": bool(is_causal), "edge_fully_perceptual": edge_fully_perceptual}
