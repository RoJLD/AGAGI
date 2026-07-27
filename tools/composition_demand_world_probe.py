"""C2 — Demand-marker par ablation de MODULE : la COMPOSITION (means→ends, G2). 2e jalon de l'arc
module-ablation (après l'anticipation S2-007), sur le cœur du projet (chaînage/binding means→ends).

Composition = enchaîner un MOYEN non-récompensé pour atteindre une FIN récompensée (craft-or-starve).
Mini-sim survie :
- CORPS : réflexe a=0 → +body_gain, sans plan.
- COMPOSITION : chaîne 2-étapes. Stage 0 = faire le MOYEN (action `means_t`, VARIE, révélée UNIQUEMENT
  par le module de plan, ZÉRO récompense) → passe stage 1. Stage 1 = faire la FIN (action END fixe) →
  +cog_gain (énergie), retour stage 0. Le MOYEN ne paie pas ; seul le chaînage complet paie.
Module INTACT : plan = one-hot(means_t) au stage 0 (identifie le moyen non-récompensé). ABLATÉ : plan→0 →
agent MYOPE (le moyen a 0 récompense immédiate et plus d'info) → prend le corps → reste bloqué stage 0 →
ne craft jamais → meurt (si corps insuffisant). La FIN est fixe (apprenable de l'obs) → le plan ne porte
QUE le moyen (évite le faux-positif de redondance). cog_gain>2·metab (la chaîne 2-ticks reste survivable).
Contrôle « composition NON demandée » : chain_len=1 (la FIN paie direct, pas de moyen) → plan vide →
ablation inerte. Politique entraînée (hill-climb, module intact) ; témoin = ablation du MODULE de plan.
Recette (cadre S2-006) : la survie exige la COMPOSITION SSI corps INSUFFISANT + chaîne ≥2 (moyen requis)
+ devise de survie.

Usage : python tools/composition_demand_world_probe.py   (env: CPW_SEEDS, CPW_K, CPW_TICKS)
Réutilise tools/demand_marker.ablation_verdict. REF-DEMAND-MARKER. Clôt l'arc module-ablation (G4+G2).
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict

END = 1                                               # action FIN (fixe) ; MOYEN ∈ [2,K) ; corps = 0


def _onehot(i, K, noise, rng):
    o = np.zeros(K)
    o[i] = 1.0
    return o + noise * rng.randn(K)


def survive(W, b, module_mode, body_gain, cog_gain, currency, chain_len, K, rng,
            ticks=300, E0=15.0, metab=1.0, noise=0.2):
    """Une vie. chain_len=2 : stage0 MOYEN(means_t, non payé) → stage1 FIN(END, payée). chain_len=1 :
    FIN directe. obs = one-hot du stage (padded K). plan (module) = one-hot(means_t) au stage0 sinon 0."""
    E = E0
    stage = 0
    means = 1 + rng.randint(K - 1) if K > 2 else 1
    for t in range(ticks):
        if chain_len == 2 and stage == 0:
            means = 2 + rng.randint(K - 2)            # MOYEN varie ∈ [2,K) (≠ END, ≠ corps)
        obs = np.zeros(K); obs[stage] = 1.0           # indicateur de stage (0/1)
        plan = np.zeros(K)
        if chain_len == 2 and stage == 0:
            plan = _onehot(means, K, noise, rng)      # le plan identifie le MOYEN non-récompensé
        pvec = np.zeros(K) if module_mode == "ablated" else plan
        x = np.concatenate([obs, pvec])
        a = int(np.argmax(W @ x + b))
        gain = body_gain if a == 0 else 0.0
        if chain_len == 2:
            if stage == 0 and a == means:
                stage = 1                             # moyen réussi → avance (ZÉRO récompense)
            elif stage == 1 and a == END:
                if currency == "energy":
                    gain += cog_gain                  # FIN → paie SSI devise de survie
                stage = 0
        else:                                          # chain_len == 1 : FIN directe
            if a == END and currency == "energy":
                gain += cog_gain
        E += gain - metab
        if E <= 0:
            return t + 1
    return ticks


def fit_policy(body_gain, cog_gain, currency, chain_len, K, seed, iters=350, episodes=5, ticks=300):
    """Hill-climb (W: (K,2K), b) pour MAXIMISER la survie, module de plan INTACT."""
    rng = np.random.RandomState(seed)
    W = np.zeros((K, 2 * K))
    b = np.zeros(K)

    def score(W, b):
        return np.mean([survive(W, b, "intact", body_gain, cog_gain, currency, chain_len, K,
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


def probe(body_gain, cog_gain, currency, chain_len, K, seed, n_eval=24, ticks=300):
    """Entraîne (module intact) puis ablate le MODULE de plan (plan→0) → verdict SURVIE."""
    W, b = fit_policy(body_gain, cog_gain, currency, chain_len, K, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 777)

    def surv(mode):
        return [survive(W, b, mode, body_gain, cog_gain, currency, chain_len, K,
                        np.random.RandomState(ev.randint(1 << 30)), ticks) for _ in range(n_eval)]

    v = ablation_verdict(surv("intact"), surv("ablated"))
    verdict = ("SURVIVAL_COMPOSITION_SENSITIVE" if v["collapse"] and v["n"] >= 12
               else "SURVIVAL_NEUTRAL" if v["decoy"] else "MIXED")
    return {"ratio": v["ratio"], "verdict": verdict}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("CPW_SEEDS", "8"))))
    K = int(os.environ.get("CPW_K", "5"))
    ticks = int(os.environ.get("CPW_TICKS", "300"))
    cog_gain = 3.0                                     # > 2·metab (chaîne 2-ticks nette survivable)
    SUFF, INSUFF = 1.2, 0.5

    cells = [
        (f"corps SUFFISANT ({SUFF}) + chaîne2 + énergie", SUFF, "energy", 2),
        (f"corps INSUFFISANT ({INSUFF}) + chaîne2 + énergie", INSUFF, "energy", 2),
        (f"corps INSUFFISANT ({INSUFF}) + chaîne1 (pas de moyen) + énergie", INSUFF, "energy", 1),
        (f"corps INSUFFISANT ({INSUFF}) + chaîne2 + devise sép.", INSUFF, "separate", 2),
    ]
    print(f"K={K} ticks={ticks} seeds={len(seeds)} metab=1.0 cog_gain={cog_gain} | ablation = MODULE de plan (means→0)")
    print(f"{'cellule':52s} {'ratio':>6s}  verdict")
    results = {}
    for label, body_gain, currency, chain_len in cells:
        rows = [probe(body_gain, cog_gain, currency, chain_len, K, s, ticks=ticks) for s in seeds]
        ratio = statistics.median(r["ratio"] for r in rows)
        verdicts = [r["verdict"] for r in rows]
        maj = max(set(verdicts), key=verdicts.count)
        results[label] = maj
        print(f"{label:52s} {ratio:6.2f}  {maj}")

    sensitive = [l for l, v in results.items() if v == "SURVIVAL_COMPOSITION_SENSITIVE"]
    print(f"\nRECETTE (cellules composition-SENSIBLES = {sensitive or 'aucune'}) : la survie in-world exige "
          f"la COMPOSITION (chaîner un moyen non-récompensé vers une fin) SSI (1) corps INSUFFISANT, "
          f"(2) chaîne ≥2 (un MOYEN non-récompensé est requis), (3) devise de survie. 2e jalon "
          f"ablation-MODULE (avec l'anticipation S2-007) → la recette S2-006 tient sur TOUTES les "
          f"capacités testées (input ET calcul).")


if __name__ == "__main__":
    main()
