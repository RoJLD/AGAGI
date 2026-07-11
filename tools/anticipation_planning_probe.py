"""La FIDÉLITÉ d'un modèle de transition se traduit-elle en COMPORTEMENT ? (G4 anticipation, PLAN-001)

EDR-193 (`g_bilinear_probe.py`, session //) : un modèle bilinéaire g(H,a)->H' prédit le latent caché ~17×
mieux que le linéaire (action-conditionné) -> « la FORME de g est un levier ». Caveat explicite :
fidélité≠comportement. Et le planning depth-1 à g LINÉAIRE avait été RÉFUTÉ (PLAN_PERD, nuit comme dreaming).
Question ouverte : un g BILINÉAIRE rend-il le planning UTILE là où le linéaire échoue ?

Proxy standalone (pur numpy, non-collidant). Le vrai avantage d'un modèle du monde = **zéro-shot à un
NOUVEAU but** sans réentraînement (north-star transfert). Un planificateur choisit
`a* = argmax_a v_but(g(s,a))` -> s'adapte à n'importe quel but SI g est fidèle.

- Dynamique VRAIE ACTION-CONDITIONNÉE : s' = tanh(W_a @ s), une matrice W_a par action (= la structure que
  193 a trouvée dans le latent réel). Un g LINÉAIRE partagé (s' ≈ A@s + B[:,a]) ne peut PAS la capturer (il
  translate, ne tourne pas) ; un g BILINÉAIRE (matrice par action) oui.
- g ajusté hors-ligne sur des transitions aléatoires (goal-AGNOSTIQUE) ; planning zéro-shot vers des buts
  aléatoires JAMAIS vus. Modèles comparés : `bilinear`, `linear`, `none` (action aléatoire).

Prédiction : bilinear >> linear ≈ none -> la FORME de g détermine le comportement (clôt le caveat de 193).

Usage : python tools/anticipation_planning_probe.py   (env: PLP_SEEDS, PLP_DIM, PLP_ACTIONS, PLP_HORIZON)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _true_dynamics(d, K, seed):
    """K matrices (d,d) distinctes -> transition action-conditionnée s' = tanh(W_a @ s)."""
    rng = np.random.RandomState(seed)
    # spectre ~0.9 pour rester contractant/stable (états bornés par tanh) mais bien action-dépendant.
    return [rng.randn(d, d).astype(np.float64) * (0.9 / np.sqrt(d)) for _ in range(K)]


def _step(W_list, s, a):
    return np.tanh(W_list[a] @ s)


def _fit_models(W_list, d, K, n_fit, seed):
    """Ajuste g LINÉAIRE (A@s + B[:,a], partagé) et BILINÉAIRE (M_a par action) par moindres carrés
    sur des transitions aléatoires (goal-agnostique)."""
    rng = np.random.RandomState(seed + 1)
    S = rng.randn(n_fit, d)
    A_idx = rng.randint(0, K, size=n_fit)
    Sp = np.stack([_step(W_list, S[i], A_idx[i]) for i in range(n_fit)])

    # BILINÉAIRE : une matrice M_a par action (capte l'action-conditionnement) -> M_a = Sp_a^T pinv(S_a^T)
    M = []
    for a in range(K):
        mask = A_idx == a
        Sa, Spa = S[mask], Sp[mask]                       # (n_a, d)
        M.append(np.linalg.lstsq(Sa, Spa, rcond=None)[0].T)   # (d,d) : s' ≈ M_a @ s

    # LINÉAIRE partagé : s' ≈ A@s + B@onehot(a) -> features [s ; onehot(a)] (d+K)
    feat = np.concatenate([S, np.eye(K)[A_idx]], axis=1)  # (n_fit, d+K)
    coef = np.linalg.lstsq(feat, Sp, rcond=None)[0]       # (d+K, d)
    A_lin, B_lin = coef[:d].T, coef[d:].T                 # (d,d), (d,K)
    return {"bilinear": M, "linear": (A_lin, B_lin)}


def _predict(models, model, s, a, d, K):
    if model == "bilinear":
        return models["bilinear"][a] @ s
    A_lin, B_lin = models["linear"]
    return A_lin @ s + B_lin[:, a]


def run_planning(d=8, K=4, n_fit=3000, n_test=500, horizon=4, seed=0):
    """Ajuste g une fois, puis planifie (depth-1 model-predictive) vers des buts aléatoires JAMAIS vus.
    Renvoie, par modèle, la distance normalisée au but atteinte (min sur le rollout) et le taux de succès."""
    W_list = _true_dynamics(d, K, seed)
    models = _fit_models(W_list, d, K, n_fit, seed)
    rng = np.random.RandomState(seed + 7)

    # fidélité 1-pas (MSE sur transitions held-out) -> relie le COMPORTEMENT à la FIDÉLITÉ (caveat 193).
    fs = np.tanh(rng.randn(400, d))
    fa = rng.randint(0, K, size=400)
    ftrue = np.stack([_step(W_list, fs[i], fa[i]) for i in range(400)])
    fidelity = {}
    for m in ("bilinear", "linear"):
        pred = np.stack([_predict(models, m, fs[i], int(fa[i]), d, K) for i in range(400)])
        fidelity[m] = float(np.mean((pred - ftrue) ** 2))

    out = {}
    for model in ("bilinear", "linear", "none"):
        norm_best, succ = [], []
        for _ in range(n_test):
            s = np.tanh(rng.randn(d))                         # état initial (dans le manifold)
            goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))   # but atteignable, JAMAIS vu
            d0 = np.linalg.norm(s - goal) + 1e-9
            best = d0
            for _t in range(horizon):
                if model == "none":
                    a = rng.randint(K)                        # pas de modèle : action aléatoire
                else:
                    # depth-1 model-predictive : choisit l'action dont la CONSÉQUENCE prédite est la + proche du but
                    preds = [_predict(models, model, s, a, d, K) for a in range(K)]
                    a = int(np.argmin([np.linalg.norm(p - goal) for p in preds]))
                s = _step(W_list, s, a)                       # exécute dans la VRAIE dynamique
                best = min(best, np.linalg.norm(s - goal))
            norm_best.append(best / d0)                       # <1 = s'est rapproché ; 1 = pas mieux qu'au départ
            succ.append(1.0 if best < 0.5 * d0 else 0.0)      # a réduit la distance de moitié
        out[model] = {"norm_dist": float(np.mean(norm_best)), "success": float(np.mean(succ))}
    return {"seed": int(seed), "d": d, "K": K, "horizon": horizon, "models": out, "fidelity": fidelity}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("PLP_SEEDS", "5"))))
    d = int(os.environ.get("PLP_DIM", "8"))
    K = int(os.environ.get("PLP_ACTIONS", "4"))
    horizon = int(os.environ.get("PLP_HORIZON", "4"))
    rows = [run_planning(d=d, K=K, horizon=horizon, seed=s) for s in seeds]

    def med(model, key):
        return statistics.median(r["models"][model][key] for r in rows)

    fid_bi = statistics.median(r["fidelity"]["bilinear"] for r in rows)
    fid_li = statistics.median(r["fidelity"]["linear"] for r in rows)
    print(f"d={d} K={K} horizon={horizon} seeds={len(seeds)} (zéro-shot vers buts jamais vus)")
    print(f"fidélité 1-pas (MSE, +bas=+fidèle) : bilinéaire={fid_bi:.4f}  linéaire={fid_li:.4f}  "
          f"(ratio {fid_li/max(fid_bi,1e-9):.1f}×)")
    for model in ("bilinear", "linear", "none"):
        print(f"{model:9s} norm_dist={med(model,'norm_dist'):.3f} (<1=rapproche) "
              f"success={med(model,'success'):.3f}")
    bi, li, no = med("bilinear", "norm_dist"), med("linear", "norm_dist"), med("none", "norm_dist")
    # la FORME compte pour le comportement si bilinéaire aide ET linéaire n'aide pas plus que le hasard
    form_matters = bi < no - 0.08 and bi < li - 0.08 and li > no - 0.06
    verdict = ("BILINEAR_MODEL_ENABLES_PLANNING" if form_matters else
               "BOTH_MODELS_PLAN" if bi < no - 0.08 and li < no - 0.08 else
               "NO_PLANNING_BENEFIT")
    print(f"VERDICT={verdict} : bilinéaire={bi:.3f} vs linéaire={li:.3f} vs hasard={no:.3f} "
          f"(la FORME de g {'DÉTERMINE' if form_matters else 'ne détermine pas seule'} le comportement)")


if __name__ == "__main__":
    main()
