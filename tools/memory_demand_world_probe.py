"""B2 — Recette d'un monde in-world à demande de MÉMOIRE (pendant de MEM-001, cadre corps+devise de S2-004).

S2-004 a donné la recette pour la PERCEPTION (corps insuffisant + devise de survie). Ici : à quelle
CONDITION un objectif de survie in-world exige-t-il la MÉMOIRE (rappel différé), au lieu d'être
court-circuité par le corps ? Mini-sim survie :
- CORPS : action-réflexe fixe (a=0) → +body_gain, sans mémoire.
- MÉMOIRE : la bonne action nourricière AU tick t = l'indice vu au tick t-1 (rappel différé). L'agent
  porte une MÉMOIRE = intégrateur à fuite des indices passés (substrat FIXE, contourne BPTT, cf. MEM-001) ;
  hitter la bonne action → +cog_gain SSI on lit la mémoire.
Deux axes clés, en plus du corps (suffisant/insuffisant) et de la devise (énergie/séparée) :
- RAPPEL DIFFÉRÉ (recall='delayed') : l'obs courante ne montre PAS l'action correcte (indice passé) →
  il FAUT la mémoire. Contrôle RAPPEL-NON-DEMANDÉ (recall='present') : l'obs montre l'action correcte
  directement → la mémoire est inutile.
Politique entraînée (hill-climb) à MAXIMISER la survie ; témoin = ablation de la MÉMOIRE (m→0, within-
subject, demand_marker). Recette : la mémoire n'est survival-porteuse QUE si corps INSUFFISANT ET rappel
DIFFÉRÉ ET gain EN ÉNERGIE.

Usage : python tools/memory_demand_world_probe.py   (env: MDW_SEEDS, MDW_K, MDW_TICKS)
Réutilise tools/demand_marker.ablation_verdict. REF-DEMAND-MARKER.
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict


def _onehot(i, K, noise, rng):
    o = np.zeros(K)
    o[i] = 1.0
    return o + noise * rng.randn(K)


def survive(W, b, mem_mode, body_gain, cog_gain, currency, recall, K, rng,
            ticks=300, E0=15.0, metab=1.0, leak=0.55, noise=0.25):
    """Une vie. À chaque tick, la bonne action nourricière = l'indice du tick PRÉCÉDENT (rappel différé).
    Entrée politique = concat(obs_courante, mémoire) (dim 2K). mem_mode='intact' | 'ablated' (m→0).
    recall='delayed' : obs courante = zéros (pas d'indice courant) → il faut la mémoire ;
    recall='present' : obs courante = one-hot de l'action correcte → mémoire inutile."""
    E = E0
    m = np.zeros(K)                                  # mémoire = intégrateur à fuite des indices PASSÉS (c_0..c_{t-1})
    prev_cue = None
    for t in range(ticks):
        cue = 1 + rng.randint(K - 1)                 # indice de CE tick (∈ [1,K), jamais le corps)
        if recall == "delayed":
            correct = prev_cue                       # bonne action = indice PASSÉ (seulement en mémoire)
            obs = np.zeros(K)                         # l'obs courante ne montre PAS l'action correcte
        else:                                        # recall == "present"
            correct = cue                            # bonne action = indice COURANT (pas encore en mémoire)
            obs = _onehot(cue, K, noise, rng)         # montré dans l'obs → mémoire inutile (elle n'a que le passé)
        mvec = np.zeros(K) if mem_mode == "ablated" else m
        x = np.concatenate([obs, mvec])
        a = int(np.argmax(W @ x + b))
        gain = body_gain if a == 0 else 0.0
        if correct is not None and a == correct and currency == "energy":
            gain += cog_gain
        E += gain - metab
        if E <= 0:
            return t + 1
        m = leak * m + _onehot(cue, K, 0.0, rng)     # intègre l'indice de CE tick (dominant = plus récent)
        prev_cue = cue
    return ticks


def fit_policy(body_gain, cog_gain, currency, recall, K, seed, iters=300, episodes=5, ticks=300):
    """Hill-climb (W: (K,2K), b: (K,)) pour MAXIMISER la survie (mémoire intacte)."""
    rng = np.random.RandomState(seed)
    W = np.zeros((K, 2 * K))
    b = np.zeros(K)

    def score(W, b):
        return np.mean([survive(W, b, "intact", body_gain, cog_gain, currency, recall, K,
                                np.random.RandomState(seed + 100 + e), ticks) for e in range(episodes)])

    best, step = score(W, b), 0.5
    for i in range(iters):
        Wc, bc = W + step * rng.randn(K, 2 * K), b + step * rng.randn(K)
        sc = score(Wc, bc)
        if sc > best:
            W, b, best = Wc, bc, sc
        elif i % 50 == 49:
            step *= 0.85
    return W, b


def probe(body_gain, cog_gain, currency, recall, K, seed, n_eval=24, ticks=300):
    """Entraîne, puis ablate la MÉMOIRE (m→0) → verdict SURVIE. mem_weight = poids que la politique met
    sur la moitié mémoire de l'entrée."""
    W, b = fit_policy(body_gain, cog_gain, currency, recall, K, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 777)

    def surv(mem_mode):
        return [survive(W, b, mem_mode, body_gain, cog_gain, currency, recall, K,
                        np.random.RandomState(ev.randint(1 << 30)), ticks) for _ in range(n_eval)]

    v = ablation_verdict(surv("intact"), surv("ablated"))
    verdict = ("SURVIVAL_MEMORY_SENSITIVE" if v["collapse"] and v["n"] >= 12
               else "SURVIVAL_NEUTRAL" if v["decoy"] else "MIXED")
    return {"ratio": v["ratio"], "verdict": verdict, "mem_weight": float(np.mean(np.abs(W[:, K:])))}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("MDW_SEEDS", "8"))))
    K = int(os.environ.get("MDW_K", "5"))
    ticks = int(os.environ.get("MDW_TICKS", "300"))
    cog_gain = 2.0
    SUFF, INSUFF = 1.2, 0.5

    cells = [
        (f"corps SUFFISANT ({SUFF}) + rappel différé + énergie", SUFF, "energy", "delayed"),
        (f"corps INSUFFISANT ({INSUFF}) + rappel différé + énergie", INSUFF, "energy", "delayed"),
        (f"corps INSUFFISANT ({INSUFF}) + rappel PRÉSENT + énergie", INSUFF, "energy", "present"),
        (f"corps INSUFFISANT ({INSUFF}) + rappel différé + devise sép.", INSUFF, "separate", "delayed"),
    ]
    print(f"K={K} ticks={ticks} seeds={len(seeds)} metab=1.0 cog_gain={cog_gain} | ablation = MÉMOIRE (m→0)")
    print(f"{'cellule':52s} {'ratio':>6s} {'|W|mém':>7s}  verdict")
    results = {}
    for label, body_gain, currency, recall in cells:
        rows = [probe(body_gain, cog_gain, currency, recall, K, s, ticks=ticks) for s in seeds]
        ratio = statistics.median(r["ratio"] for r in rows)
        mw = statistics.median(r["mem_weight"] for r in rows)
        verdicts = [r["verdict"] for r in rows]
        maj = max(set(verdicts), key=verdicts.count)
        results[label] = maj
        print(f"{label:52s} {ratio:6.2f} {mw:7.3f}  {maj}")

    sensitive = [l for l, v in results.items() if v == "SURVIVAL_MEMORY_SENSITIVE"]
    print(f"\nRECETTE (cellules mémoire-SENSIBLES = {sensitive or 'aucune'}) : un objectif de survie "
          f"in-world n'exige la MÉMOIRE que si TROIS conditions tiennent — (1) corps INSUFFISANT seul, "
          f"(2) RAPPEL DIFFÉRÉ (l'info survie n'est que dans le passé, pas l'obs courante), (3) le succès "
          f"payé EN ÉNERGIE. Généralise S2-004 (perception) à la mémoire ; converge MEM-001.")


if __name__ == "__main__":
    main()
