"""C1 — Demand-marker par ablation de MODULE : l'anticipation (G4). Extension de l'arc S2-004/005/006
aux capacités-CALCUL (que l'ablation d'INPUT ne couvre pas — cf. la frontière d'EDR-S2-006).

Anticipation = utiliser un MODÈLE de transition pour agir sur une conséquence FUTURE. Mini-sim survie :
- CORPS : réflexe a=0 → +body_gain, sans modèle.
- ANTICIPATION : la nourriture VISÉE paie au tick suivant = shift(état courant s_t). L'agent OBSERVE s_t
  (donc PAS de demande perceptive ni mémoire) mais doit APPLIQUER un forward-model M (la dynamique connue
  s→shift(s)) pour viser shift(s_t). Module INTACT : pred = M·obs ≈ one-hot(shift(s_t)). Module ABLATÉ :
  pred = obs (identité, réactif) → vise s_t ≠ shift(s_t) → rate.
Contrôle « anticipation NON demandée » : shift=0 (nourriture statique) → correct = s_t = obs → le réactif
suffit → ablation inerte. Politique entraînée (hill-climb) à maximiser la survie ; témoin = ablation du
MODULE (M→identité, within-subject, demand_marker). Recette (cadre S2-006) : la survie exige l'anticipation
SSI corps INSUFFISANT + dynamique NON-triviale (shift≠0) + devise de survie (énergie).

Usage : python tools/anticipation_demand_world_probe.py   (env: ADW_SEEDS, ADW_K, ADW_TICKS)
Réutilise tools/demand_marker.ablation_verdict. REF-DEMAND-MARKER. Ouvre l'arc ablation-MODULE (G4/G2).
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict


def _shifted(s, shift, K):
    """Dynamique : état cognitif s∈[1,K) → s décalé de `shift` dans le cycle [1,K). shift=0 → identité."""
    return 1 + ((s - 1 + shift) % (K - 1))


def _model_matrix(shift, K):
    """Forward-model M (K,K) = la dynamique connue. M·one-hot(s) = one-hot(shifted(s)) ; identité sur 0."""
    M = np.zeros((K, K))
    M[0, 0] = 1.0
    for s in range(1, K):
        M[_shifted(s, shift, K), s] = 1.0
    return M


def _onehot(i, K, noise, rng):
    o = np.zeros(K)
    o[i] = 1.0
    return o + noise * rng.randn(K)


def survive(W, b, module_mode, body_gain, cog_gain, currency, shift, K, rng,
            ticks=300, E0=15.0, metab=1.0, noise=0.25):
    """Une vie. correct_t = shifted(s_t). Module INTACT : pred=M·obs (anticipe) ; ABLATÉ : pred=obs (réactif)."""
    M = _model_matrix(shift, K)
    E = E0
    for t in range(ticks):
        s = 1 + rng.randint(K - 1)                       # état observé de CE tick (∈ [1,K))
        correct = _shifted(s, shift, K)                  # nourriture visée = état décalé (futur)
        obs = _onehot(s, K, noise, rng)
        pred = (M @ obs) if module_mode == "intact" else obs   # ablation module = identité (réactif)
        a = int(np.argmax(W @ pred + b))
        gain = body_gain if a == 0 else 0.0
        if a == correct and currency == "energy":
            gain += cog_gain
        E += gain - metab
        if E <= 0:
            return t + 1
    return ticks


def fit_policy(body_gain, cog_gain, currency, shift, K, seed, iters=300, episodes=5, ticks=300):
    """Hill-climb (W,b) pour MAXIMISER la survie, module INTACT (l'agent DISPOSE du modèle)."""
    rng = np.random.RandomState(seed)
    W = np.zeros((K, K))
    b = np.zeros(K)

    def score(W, b):
        return np.mean([survive(W, b, "intact", body_gain, cog_gain, currency, shift, K,
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


def probe(body_gain, cog_gain, currency, shift, K, seed, n_eval=24, ticks=300):
    """Entraîne (module intact) puis ablate le MODULE (M→identité) → verdict SURVIE."""
    W, b = fit_policy(body_gain, cog_gain, currency, shift, K, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 777)

    def surv(mode):
        return [survive(W, b, mode, body_gain, cog_gain, currency, shift, K,
                        np.random.RandomState(ev.randint(1 << 30)), ticks) for _ in range(n_eval)]

    v = ablation_verdict(surv("intact"), surv("ablated"))
    verdict = ("SURVIVAL_ANTICIPATION_SENSITIVE" if v["collapse"] and v["n"] >= 12
               else "SURVIVAL_NEUTRAL" if v["decoy"] else "MIXED")
    return {"ratio": v["ratio"], "verdict": verdict}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("ADW_SEEDS", "8"))))
    K = int(os.environ.get("ADW_K", "5"))
    ticks = int(os.environ.get("ADW_TICKS", "300"))
    cog_gain = 2.0
    SUFF, INSUFF = 1.2, 0.5

    cells = [
        (f"corps SUFFISANT ({SUFF}) + dynamique (shift1) + énergie", SUFF, "energy", 1),
        (f"corps INSUFFISANT ({INSUFF}) + dynamique (shift1) + énergie", INSUFF, "energy", 1),
        (f"corps INSUFFISANT ({INSUFF}) + STATIQUE (shift0) + énergie", INSUFF, "energy", 0),
        (f"corps INSUFFISANT ({INSUFF}) + dynamique (shift1) + devise sép.", INSUFF, "separate", 1),
    ]
    print(f"K={K} ticks={ticks} seeds={len(seeds)} metab=1.0 cog_gain={cog_gain} | ablation = MODULE (M→identité)")
    print(f"{'cellule':56s} {'ratio':>6s}  verdict")
    results = {}
    for label, body_gain, currency, shift in cells:
        rows = [probe(body_gain, cog_gain, currency, shift, K, s, ticks=ticks) for s in seeds]
        ratio = statistics.median(r["ratio"] for r in rows)
        verdicts = [r["verdict"] for r in rows]
        maj = max(set(verdicts), key=verdicts.count)
        results[label] = maj
        print(f"{label:56s} {ratio:6.2f}  {maj}")

    sensitive = [l for l, v in results.items() if v == "SURVIVAL_ANTICIPATION_SENSITIVE"]
    print(f"\nRECETTE (cellules anticipation-SENSIBLES = {sensitive or 'aucune'}) : la survie in-world exige "
          f"l'ANTICIPATION (application d'un forward-model) SSI (1) corps INSUFFISANT, (2) dynamique "
          f"NON-triviale (la conséquence survie est dans le FUTUR, shift≠0), (3) devise de survie. Étend "
          f"la recette S2-006 aux capacités-CALCUL via ablation de MODULE (1er jalon de l'arc G4/G2).")


if __name__ == "__main__":
    main()
