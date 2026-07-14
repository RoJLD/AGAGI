"""Le « transfert » est-il une vraie GÉNÉRALISATION ou juste le noyau de survie PARTAGÉ ? (porte G1, G1-001)

Le fil directeur trouve : transfert cross-world POSITIF mais = noyau de survie partagé, PAS de compétence
world-spécifique (« généralisation parfaite ⟺ absence de spécialisation »). On TESTE causalement cette
affirmation avec l'instrument within-subject ([[within-subject-demand-marker]]).

Agent à DEUX têtes (décision noyau + décision spécifique) sur les mêmes entrées (contexte c, paramètre-monde
θ) :
- NOYAU : a_core* = c (θ-INDÉPENDANT, identique dans tout monde) -> transfère trivialement.
- SPÉCIFIQUE : a_spec* = θ (dépend du monde) -> ne transfère que si l'agent LIT θ.

Régimes d'entraînement :
- MONO-monde (θ fixé θ_A) : la tête spécifique peut MÉMORISER a=θ_A (ignore θ).
- MULTI-mondes (θ varie) : la tête spécifique DOIT lire θ -> apprend l'ALGORITHME a=θ.

Transfert zéro-shot vers un monde θ_B ≠ θ_A. Marqueur causal = ablation de l'entrée θ (randomisée) : si le
spécifique s'effondre -> le skill est causalement réutilisé = GÉNÉRALISATION vraie ; s'il est inerte -> le
transfert ne tient qu'au noyau. Corroborant : poids de la tête spécifique sur l'entrée θ.

Usage : python tools/generalization_transfer_probe.py   (env: GT_SEEDS, GT_K)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# entrée = one-hot(contexte) ⊕ one-hot(θ) ⊕ BIAIS. Le biais permet une sortie CONSTANTE sans lire θ (crucial :
# en mono-monde, la tête spécifique doit produire θ_A via le biais, pas via la colonne-θ, sinon l'ablation de θ
# ne serait pas vraiment inerte et le corroborant poids_θ serait faussé).
def _feat(c, theta, K):
    f = np.zeros(2 * K + 1)
    f[c] = 1.0
    f[K + theta] = 1.0
    f[2 * K] = 1.0
    return f


def _fit_head(F, targets, K, lr=0.5, epochs=500, decay=1e-3):
    """Classifieur linéaire softmax (descente de gradient, fiable) ajusté sur les cas énumérés. Weight-decay =
    les poids inutiles retombent à 0 (choisit la sortie constante via le BIAIS plutôt que la colonne-θ)."""
    n, dim = F.shape
    W = np.zeros((K, dim))
    onehot = np.zeros((n, K))
    onehot[np.arange(n), targets] = 1.0
    for _ in range(epochs):
        Z = F @ W.T
        Z -= Z.max(axis=1, keepdims=True)
        P = np.exp(Z)
        P /= P.sum(axis=1, keepdims=True)
        grad = (P - onehot).T @ F / n
        W -= lr * (grad + decay * W)
    return W


def fit_policy(multi, theta_A, K, seed):
    """Ajuste deux têtes softmax (noyau : cible c ; spécifique : cible θ) sur l'énumération complète des cas.
    MONO : seul θ=θ_A vu. MULTI : tous les θ vus."""
    thetas = list(range(K)) if multi else [theta_A]
    feats, core_t, spec_t = [], [], []
    for th in thetas:
        for c in range(K):
            feats.append(_feat(c, th, K))
            core_t.append(c)
            spec_t.append(th)
    F = np.array(feats)
    Wc = _fit_head(F, np.array(core_t), K)
    Ws = _fit_head(F, np.array(spec_t), K)
    return Wc, Ws


def evaluate(Wc, Ws, theta_B, theta_obs_mode, K, seed, n=2000):
    """Précision noyau & spécifique dans le monde θ_B. theta_obs_mode : 'true' (θ vu) / 'random' (ablation :
    l'agent voit un θ bidon, mais a* reste calculé sur le VRAI θ_B)."""
    rng = np.random.RandomState(seed + 700)
    core, spec = [], []
    for _ in range(n):
        c = rng.randint(K)
        theta_obs = theta_B if theta_obs_mode == "true" else rng.randint(K)
        f = _feat(c, theta_obs, K)
        core.append(1.0 if int(np.argmax(Wc @ f)) == c else 0.0)
        spec.append(1.0 if int(np.argmax(Ws @ f)) == theta_B else 0.0)
    return float(np.mean(core)), float(np.mean(spec))


def run(K, seed, theta_A=0, theta_B=None):
    theta_B = (K // 2) if theta_B is None else theta_B
    out = {}
    for regime, multi in (("MONO", False), ("MULTI", True)):
        Wc, Ws = fit_policy(multi, theta_A, K, seed)
        core_t, spec_t = evaluate(Wc, Ws, theta_B, "true", K, seed)
        _, spec_a = evaluate(Wc, Ws, theta_B, "random", K, seed)
        theta_w = float(np.mean(np.abs(Ws[:, K:2 * K])))   # poids de la tête spécifique sur l'entrée θ (hors biais)
        out[regime] = {"core": core_t, "spec_true": spec_t, "spec_ablated": spec_a, "theta_w": theta_w}
    return out


def main():
    import statistics
    seeds = list(range(int(os.environ.get("GT_SEEDS", "8"))))
    K = int(os.environ.get("GT_K", "6"))
    chance = 1.0 / K
    runs = [run(K, s) for s in seeds]

    print(f"K={K} chance={chance:.2f} seeds={len(seeds)} (transfert zéro-shot vers monde θ_B ≠ θ_A)")
    print(f"{'régime':7s} {'noyau':>6s} {'spéc.θvrai':>11s} {'spéc.θablé':>11s} {'poids_θ':>8s} | "
          f"{'ablation Δspéc':>14s}")
    summ = {}
    for regime in ("MONO", "MULTI"):
        core = statistics.median(r[regime]["core"] for r in runs)
        st = statistics.median(r[regime]["spec_true"] for r in runs)
        sa = statistics.median(r[regime]["spec_ablated"] for r in runs)
        tw = statistics.median(r[regime]["theta_w"] for r in runs)
        summ[regime] = (core, st, sa, tw)
        print(f"{regime:7s} {core:6.2f} {st:11.2f} {sa:11.2f} {tw:8.3f} | {st - sa:13.2f}")

    core_mono, st_mono, sa_mono, tw_mono = summ["MONO"]
    core_multi, st_multi, sa_multi, tw_multi = summ["MULTI"]
    # généralisation vraie = MULTI réussit le spécifique ET l'ablation θ l'effondre ; MONO échoue le spécifique
    # (transfert = noyau seul, qui lui transfère) ET l'ablation ne change rien (θ jamais utilisé)
    genuine = (st_multi > 0.6 and (st_multi - sa_multi) > 0.3
               and st_mono < 0.4 and abs(st_mono - sa_mono) < 0.15
               and core_mono > 0.8 and core_multi > 0.8)
    verdict = ("GENERALIZATION_IS_CAUSAL_SKILL_ONLY_UNDER_VARIED_TRAINING" if genuine else "TRANSFER_UNCLEAR")
    print(f"VERDICT={verdict} : le NOYAU transfère dans les 2 régimes (MONO {core_mono:.2f} / MULTI "
          f"{core_multi:.2f}) ; MULTI transfère AUSSI le spécifique ({st_multi:.2f}) et l'ablation θ l'effondre "
          f"(Δ{st_multi - sa_multi:+.2f}, poids_θ {tw_multi:.2f}) = généralisation CAUSALE ; MONO spécifique "
          f"{st_mono:.2f}≈hasard, ablation INERTE (Δ{st_mono - sa_mono:+.2f}, poids_θ {tw_mono:.2f}) → son "
          f"transfert n'est QUE le noyau partagé → le fil directeur « transfert = noyau » est un ARTEFACT de "
          f"l'entraînement mono-monde, PAS une limite de généralisation")


if __name__ == "__main__":
    main()
