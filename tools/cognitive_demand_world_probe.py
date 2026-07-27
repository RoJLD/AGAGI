"""B1 — Recette d'un monde à DEMANDE COGNITIVE survivable (suite CONSTRUCTIVE de S2-003).

S2-003 (négatif) : la survie du champion est perception-NEUTRE — le corps/métabolisme court-circuite la
cognition ; la survie n'a aucun contenu cognitif. Converge avec s2-cognition-body (survie ET fitness = corps).
Conséquence : tout test in-world reste NEUTRE par construction tant que l'objectif = survie/fitness.

Ce probe répond « ALORS QUOI ? » : à quelle CONDITION un objectif de survie in-world récompense-t-il la
cognition (survie perception-SENSIBLE), au lieu d'être court-circuité par le corps ? Mini-sim survie :
- CORPS : action-réflexe fixe (a=0) → +body_gain, indépendante de l'obs (un corps évolué survit par là).
- COGNITION : action nourricière qui VARIE chaque tick, révélée par l'obs → +cog_gain SSI on lit l'obs.
Métabolisme draine `metab` chaque tick. Survie = ticks avant E<=0. On entraîne une politique à MAXIMISER
la survie (hill-climb), puis on lit le témoin demand-marker via l'échelle d'ablation (vrai/permuté/bruit/zéro).

Deux axes :
1. MAGNITUDE (currency='energy') : sweep cog_gain/body_gain → SEUIL où la survie devient SURVIVAL_SENSITIVE.
2. DEVISE (currency='separate') : le gain cognitif ne va PAS dans l'énergie (autre devise, ex. « points »)
   → la survie reste NEUTRE quelle que soit la magnitude (reproduit « la fitness est corps » in-world).

Recette : pour qu'un monde in-world exige la cognition, le succès cognitif doit payer dans la DEVISE
SÉLECTIONNÉE (énergie de survie) ET dépasser l'avantage métabolique du corps. Sinon NEUTRE par construction.

Usage : python tools/cognitive_demand_world_probe.py   (env: CDW_SEEDS, CDW_K, CDW_TICKS)
Réutilise tools/demand_marker.ablation_verdict (témoin partagé). REF-DEMAND-MARKER.
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict


def _obs(cog_action, K, rng, noise=0.35):
    """Indice sensoriel = one-hot bruité de l'action nourricière cognitive de CE tick."""
    o = np.zeros(K)
    o[cog_action] = 1.0
    return o + noise * rng.randn(K)


def _ablate(o_true, mode, K, rng):
    """Échelle d'ablation de l'obs (within-subject) : vrai / permuté(décorrélé in-distrib) / bruit / zéro."""
    if mode == "true":
        return o_true
    if mode == "permuted":
        return _obs(1 + rng.randint(K - 1), K, rng)      # obs réelle mais d'un AUTRE tick (décorrélée)
    if mode == "noise":
        return rng.randn(K) * (o_true.std() + 1e-9) + o_true.mean()
    if mode == "zero":
        return np.zeros(K)
    raise ValueError(mode)


def survive(W, b, obs_mode, body_gain, cog_gain, currency, K, rng, ticks=300, E0=15.0, metab=1.0):
    """Une vie. Corps : a=0 → +body_gain (obs-indépendant). Cognition : a==cog_action(t) → +cog_gain
    en ÉNERGIE si currency='energy' (sinon devise séparée, aucun effet survie). Survie = ticks avant E<=0."""
    E = E0
    for t in range(ticks):
        cog_action = 1 + rng.randint(K - 1)              # jamais 0 (distincte du corps)
        o = _ablate(_obs(cog_action, K, rng), obs_mode, K, rng)
        a = int(np.argmax(W @ o + b))
        gain = body_gain if a == 0 else 0.0
        if a == cog_action and currency == "energy":
            gain += cog_gain                             # le succès cognitif paie EN ÉNERGIE
        E += gain - metab
        if E <= 0:
            return t + 1
    return ticks


def fit_policy(body_gain, cog_gain, currency, K, seed, iters=300, episodes=5, ticks=300):
    """Hill-climb (W,b) pour MAXIMISER la survie (obs vraie). La politique n'apprend à peser l'obs que si
    lire l'obs paie EN SURVIE (currency='energy' ET cog_gain assez grand vs body_gain)."""
    rng = np.random.RandomState(seed)
    W = np.zeros((K, K))
    b = np.zeros(K)

    def score(W, b):
        return np.mean([survive(W, b, "true", body_gain, cog_gain, currency, K,
                                np.random.RandomState(seed + 100 + e), ticks) for e in range(episodes)])

    best, step = score(W, b), 0.5
    for i in range(iters):
        Wc, bc = W + step * rng.randn(K, K), b + step * rng.randn(K)
        sc = score(Wc, bc)
        if sc > best:
            W, b, best = Wc, bc, sc
        elif i % 50 == 49:
            step *= 0.85
    return W, b


def ladder(body_gain, cog_gain, currency, K, seed, n_eval=24, ticks=300):
    """Entraîne une politique puis lit l'échelle d'ablation → verdict SURVIE (via demand_marker).
    Renvoie {ratios par barreau, verdict, obs_weight}."""
    W, b = fit_policy(body_gain, cog_gain, currency, K, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 777)

    def surv(mode):
        return [survive(W, b, mode, body_gain, cog_gain, currency, K,
                        np.random.RandomState(ev.randint(1 << 30)), ticks) for _ in range(n_eval)]

    intact = surv("true")
    rungs = {m: ablation_verdict(intact, surv(m))["ratio"] for m in ("permuted", "noise", "zero")}
    # verdict SURVIE : SENSIBLE si un barreau effondre (>=1.5), NEUTRE si tous plats (<=1.3), sinon MIXTE
    if any(r >= 1.5 for r in rungs.values()):
        verdict = "SURVIVAL_SENSITIVE"
    elif all(r <= 1.3 for r in rungs.values()):
        verdict = "SURVIVAL_NEUTRAL"
    else:
        verdict = "MIXED"
    return {"ratios": rungs, "verdict": verdict, "obs_weight": float(np.mean(np.abs(W)))}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("CDW_SEEDS", "6"))))
    K = int(os.environ.get("CDW_K", "5"))
    ticks = int(os.environ.get("CDW_TICKS", "300"))
    metab = 1.0
    cog_gain = 2.0                                        # cognition > metab (peut sauver la survie)
    SUFF, INSUFF = 1.2, 0.5                               # body_gain : >metab=survit seul / <metab=meurt seul

    # Grille (régime du CORPS × DEVISE de la cognition). SUFFISANT=body_gain>metab (réflexe survit seul) ;
    # INSUFFISANT=body_gain<metab (réflexe seul meurt). cog en 'energy' (devise de survie) vs 'separate'
    # (autre devise, ex. points/fitness — n'aide pas la survie).
    cells = [
        (f"corps SUFFISANT ({SUFF}) + énergie", SUFF, "energy"),        # biosphère : corps survit → NEUTRE
        (f"corps INSUFFISANT ({INSUFF}) + énergie", INSUFF, "energy"),  # la RECETTE → SENSIBLE
        (f"corps INSUFFISANT ({INSUFF}) + devise séparée", INSUFF, "separate"),  # devise → NEUTRE
        (f"corps SUFFISANT ({SUFF}) + devise séparée", SUFF, "separate"),        # biosphère fitness → NEUTRE
    ]
    print(f"K={K} ticks={ticks} seeds={len(seeds)} metab={metab} cog_gain={cog_gain} "
          f"| SUFFISANT=body_gain>{metab} (survit seul), INSUFFISANT<{metab} (réflexe seul meurt)")
    print(f"{'cellule':44s} {'permuted':>9s} {'noise':>7s} {'zero':>7s} {'|W|obs':>7s}  verdict")
    results = {}
    for label, body_gain, currency in cells:
        rows = [ladder(body_gain, cog_gain, currency, K, s, ticks=ticks) for s in seeds]
        med = lambda k: statistics.median(r["ratios"][k] for r in rows)
        ow = statistics.median(r["obs_weight"] for r in rows)
        verdicts = [r["verdict"] for r in rows]
        maj = max(set(verdicts), key=verdicts.count)
        results[label] = maj
        print(f"{label:44s} {med('permuted'):9.2f} {med('noise'):7.2f} {med('zero'):7.2f} "
              f"{ow:7.3f}  {maj}")

    sensitive = [l for l, v in results.items() if v == "SURVIVAL_SENSITIVE"]
    print(f"\nRECETTE (cellules SENSIBLES = {sensitive or 'aucune'}) : un objectif de survie in-world "
          f"n'exige la cognition QUE si DEUX conditions tiennent — (1) le CORPS est INSUFFISANT seul "
          f"(sinon la survie plafonne sur le corps → NEUTRE, cf. S2-003/biosphère) ET (2) le succès "
          f"cognitif paie dans la DEVISE SÉLECTIONNÉE (énergie de survie), pas une devise séparée "
          f"(fitness/points → NEUTRE). C'est la contrepartie constructive du finding négatif in-world.")


if __name__ == "__main__":
    main()
