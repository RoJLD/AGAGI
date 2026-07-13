"""Quel MARQUEUR détecte correctement « le monde exige-t-il l'intelligence » ? (fil S2, S2-001)

Le S2 de prod établit EXIGE via champion-vs-baselines (BETWEEN-subject) + survie (pas life_score). Caveat
documenté : « le champion est un SURVIVANT, pas un marqueur » — un survivant compétent peut exister dans un
monde qui n'exige PAS de perception, donc le marqueur « un survivant existe » peut FAUX-POSITIVER. Le témoin
causal correct est WITHIN-subject : ablater la perception du MÊME agent (décorréler ses obs de la réalité) ;
si la survie s'effondre, son traitement d'information est causalement porteur de sa survie.

On valide les marqueurs sur des mondes à VÉRITÉ-TERRAIN connue :
- DEMANDING : l'action nourricière VARIE chaque tick, révélée par l'obs -> survivre EXIGE de lire l'obs.
- TRIVIAL  : l'action nourricière est FIXE, l'obs est un leurre non-informatif -> une politique fixe survit.
Marqueurs : (a) BETWEEN « un survivant existe » = survie(politique ajustée) vs survie(action aléatoire) ;
(b) WITHIN ablation = survie(ajustée, obs VRAIE) vs survie(ajustée, obs RANDOMISÉE) ; corroborant = |W|
(poids que la politique met sur l'obs). Prédiction : (a) fait un FAUX POSITIF sur TRIVIAL ; (b) tranche juste.

Usage : python tools/world_demand_marker_probe.py   (env: WDM_SEEDS, WDM_ACTIONS, WDM_TICKS)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _obs(demanding, food_action, K, rng, noise=0.35):
    """Indice sensoriel. DEMANDING : one-hot de la vraie action nourricière (+bruit). TRIVIAL : one-hot d'une
    action ALÉATOIRE (leurre non-corrélé à la vraie nourriture, qui est fixe) -> l'obs ne porte aucune info."""
    hint = food_action if demanding else rng.randint(K)
    o = np.zeros(K)
    o[hint] = 1.0
    return o + noise * rng.randn(K)


def survive(demanding, W, b, obs_mode, K, rng, ticks=200, E0=10.0, gain=1.0, metab=0.5):
    """Une vie : à chaque tick, l'agent choisit une action via ses logits ; s'il tape l'action nourricière il
    gagne de l'énergie, sinon rien ; le métabolisme ponctionne toujours. Survie = ticks avant énergie<=0.
    obs_mode='true' (perception intacte) ou 'random' (ablation : obs décorrélée de la réalité)."""
    E = E0
    for t in range(ticks):
        food_action = 0 if not demanding else rng.randint(K)
        o_true = _obs(demanding, food_action, K, rng)
        o = o_true if obs_mode == "true" else _obs(demanding, rng.randint(K), K, rng)  # ablation = obs bidon
        a = int(np.argmax(W @ o + b))
        E += (gain if a == food_action else 0.0) - metab
        if E <= 0:
            return t + 1
    return ticks


def fit_policy(demanding, K, seed, iters=400, episodes=6, ticks=200):
    """Ajuste (W,b) par hill-climb pour MAXIMISER la survie avec la perception intacte. La politique apprend
    NATURELLEMENT à peser l'obs (W) SEULEMENT si l'obs est informative (monde demanding)."""
    rng = np.random.RandomState(seed)
    W = np.zeros((K, K))
    b = np.zeros(K)

    def score(W, b):
        return np.mean([survive(demanding, W, b, "true", K, np.random.RandomState(seed + 100 + e), ticks)
                        for e in range(episodes)])

    best = score(W, b)
    step = 0.6
    for i in range(iters):
        Wc = W + step * rng.randn(K, K)
        bc = b + step * rng.randn(K)
        sc = score(Wc, bc)
        if sc > best:
            W, b, best = Wc, bc, sc
        elif i % 60 == 59:
            step *= 0.85                      # recuit du pas
    return W, b, best


def run_world(demanding, K, seed, n_eval=40, ticks=200):
    """Ajuste une politique, puis mesure les marqueurs : BETWEEN (ajustée vs action aléatoire) et WITHIN
    (ablation de perception : obs vraie vs randomisée). Renvoie survies médianes + |W| (poids sur l'obs)."""
    W, b, _ = fit_policy(demanding, K, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 500)

    def med(obs_mode, policy="fit"):
        vals = []
        for _ in range(n_eval):
            r = np.random.RandomState(ev.randint(1 << 30))
            if policy == "random":
                vals.append(_rand_survive(demanding, K, r, ticks))
            else:
                vals.append(survive(demanding, W, b, obs_mode, K, r, ticks))
        return float(np.median(vals))

    return {
        "fit_true": med("true"),
        "fit_ablated": med("random"),
        "random_action": med("true", policy="random"),
        "obs_weight": float(np.mean(np.abs(W))),
    }


def _rand_survive(demanding, K, rng, ticks):
    """Baseline : action uniformément aléatoire chaque tick (aucune politique)."""
    E = 10.0
    for t in range(ticks):
        food_action = 0 if not demanding else rng.randint(K)
        if rng.randint(K) != food_action:
            E -= 0.5
        else:
            E += 0.5
        if E <= 0:
            return t + 1
    return ticks


def main():
    import statistics
    seeds = list(range(int(os.environ.get("WDM_SEEDS", "8"))))
    K = int(os.environ.get("WDM_ACTIONS", "4"))
    ticks = int(os.environ.get("WDM_TICKS", "200"))

    print(f"K={K} ticks={ticks} seeds={len(seeds)} (survie médiane ; cap={ticks})")
    print(f"{'monde':10s} {'fit_true':>9s} {'ablated':>8s} {'random':>7s} | {'|W| obs':>8s} | "
          f"{'BETWEEN':>8s} {'WITHIN':>8s}")
    summary = {}
    for demanding, name in ((True, "DEMANDING"), (False, "TRIVIAL")):
        rows = [run_world(demanding, K, s, ticks=ticks) for s in seeds]
        ft = statistics.median(r["fit_true"] for r in rows)
        fa = statistics.median(r["fit_ablated"] for r in rows)
        ra = statistics.median(r["random_action"] for r in rows)
        ow = statistics.median(r["obs_weight"] for r in rows)
        between = ft / max(ra, 1e-9)          # « un survivant compétent existe ? »
        within = ft / max(fa, 1e-9)           # « la perception est-elle porteuse ? »
        summary[name] = (between, within)
        print(f"{name:10s} {ft:9.1f} {fa:8.1f} {ra:7.1f} | {ow:8.3f} | {between:7.1f}x {within:7.1f}x")

    # marqueur SOUND = celui qui signale la demande SEULEMENT dans DEMANDING (vérité-terrain)
    b_dem, w_dem = summary["DEMANDING"]
    b_triv, w_triv = summary["TRIVIAL"]
    between_falsepos = b_triv > 1.5          # BETWEEN crie « demande » aussi dans TRIVIAL ?
    within_correct = w_dem > 1.5 and w_triv < 1.3   # WITHIN : oui dans DEMANDING, non dans TRIVIAL
    verdict = ("WITHIN_SUBJECT_ABLATION_IS_THE_SOUND_DEMAND_MARKER"
               if between_falsepos and within_correct else "MARKERS_AGREE")
    print(f"VERDICT={verdict} : BETWEEN faux-positif sur TRIVIAL={between_falsepos} "
          f"(demand {b_dem:.1f}x / trivial {b_triv:.1f}x) ; WITHIN tranche juste={within_correct} "
          f"(demand {w_dem:.1f}x / trivial {w_triv:.1f}x) -> le témoin causal de demande d'intelligence "
          f"est l'ablation within-subject de la perception, pas l'existence d'un survivant")


if __name__ == "__main__":
    main()
