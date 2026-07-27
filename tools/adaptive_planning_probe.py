"""Profondeur de planning ADAPTATIVE : un agent qui MESURE la fidélité de son modèle et choisit sa
profondeur en conséquence bat-il toute profondeur FIXE en succès-par-calcul ? (G4, PLAN-004 — capstone
de la trilogie PLAN-001/002/003)

PLAN-003 : la profondeur aide proportionnellement à la fidélité ; planifier profond sur un mauvais modèle
GASPILLE du calcul (K^k séquences) pour ~aucun gain. Idée : l'agent observe en ligne la fidélité de son
propre modèle (MSE de prédiction 1-pas — signal gratuit, il voit s' après avoir agi) et règle sa profondeur.
Prédiction : la profondeur adaptative ≈ le succès de la meilleure profondeur fixe, à une FRACTION du calcul
(profond seulement quand le modèle le mérite), et bat la profondeur fixe faible en succès.

Usage : python tools/adaptive_planning_probe.py   (env: APP_SEEDS, APP_DIM, APP_ACTIONS, APP_EXEC, APP_DMAX)
"""
import os
import sys
import numpy as np
from itertools import product

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.anticipation_planning_probe import _true_dynamics, _step, _fit_models, _predict


# --- modèles de fidélité variable : bilinéaire ajusté + bruit de prédiction croissant, plus linéaire (mauvais)
def _model_predict(kind, W_list, models, noise, rng, s, a, d, K):
    if kind == "perfect":
        return _step(W_list, s, a)
    p = _predict(models, "bilinear" if kind.startswith("bilinear") else "linear", s, a, d, K)
    if kind == "bilinear_noisy":
        p = p + noise * rng.randn(d)
    return p


def _measure_fidelity(kind, W_list, models, noise, rng, d, K, n=400):
    """Signal que l'agent observe en ligne : MSE de prédiction 1-pas de SON modèle vs l'état vrai suivant."""
    errs = []
    for _ in range(n):
        s = np.tanh(rng.randn(d))
        a = rng.randint(K)
        pred = _model_predict(kind, W_list, models, noise, rng, s, a, d, K)
        errs.append(np.mean((pred - _step(W_list, s, a)) ** 2))
    return float(np.mean(errs))


def _seq_score(kind, W_list, models, noise, rng, s, seq, goal, d, K):
    """Coût d'une séquence = distance MIN au but sur le rollout PRÉDIT (matche l'objectif « se rapprocher »)."""
    best = np.linalg.norm(s - goal)
    cur = s
    for a in seq:
        cur = _model_predict(kind, W_list, models, noise, rng, cur, a, d, K)
        best = min(best, np.linalg.norm(cur - goal))
    return best


def _plan_success(kind, W_list, models, noise, rng, depth, d, K, exec_steps, n_test):
    """Succès du planning MPC depth-k (buts jamais vus). Renvoie (succès, calcul=rollouts modèle évalués)."""
    seqs = list(product(range(K), repeat=depth))
    succ = []
    for _ in range(n_test):
        s = np.tanh(rng.randn(d))
        goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))
        d0 = np.linalg.norm(s - goal) + 1e-9
        best = d0
        for _e in range(exec_steps):
            seq = min(seqs, key=lambda sq: _seq_score(kind, W_list, models, noise, rng, s, sq, goal, d, K))
            s = _step(W_list, s, seq[0])
            best = min(best, np.linalg.norm(s - goal))
        succ.append(1.0 if best < 0.5 * d0 else 0.0)
    # calcul par décision = |séquences| × longueur ; total = × exec_steps × n_test
    compute = len(seqs) * depth * exec_steps * n_test
    return float(np.mean(succ)), compute


# =====================================================================================================
# DÉCISION SCIENTIFIQUE (contribution utilisateur) : la POLITIQUE fidélité -> profondeur.
# L'agent observe recent_mse (MSE de prédiction 1-pas de son modèle) et doit renvoyer une profondeur de
# planning dans [1, depth_max]. C'est le cœur de PLAN-004 : comment traduire « à quel point je fais
# confiance à mon modèle » en « à quel point je planifie loin ».
# Repères empiriques (PLAN-001/003) : bilinéaire fidèle MSE~0.012 ; bruité ~0.03-0.10 ; linéaire ~0.16.
# Compromis : seuils (où placer la barre pour « mériter » la profondeur) ; granularité (binaire vs graduée) ;
# robustesse au bruit du signal. Sera renseignée après le choix de politique.
# =====================================================================================================
def depth_from_fidelity(recent_mse, depth_max):
    # politique par SEUILS GRADUÉS : la profondeur suit la fidélité par paliers. Exploite le régime
    # intermédiaire (modèle bruité -> depth-2/3, garde le gain de PLAN-003 à calcul modéré) et coupe la
    # profondeur quand le modèle est douteux (calcul non gaspillé).
    if recent_mse < 0.02:   return depth_max               # fidèle -> profond
    if recent_mse < 0.06:   return max(2, depth_max // 2)   # léger bruit -> mi-profond
    if recent_mse < 0.12:   return 2                        # bruité -> peu profond
    return 1                                                # douteux -> greedy


def run_adaptive(d=8, K=4, exec_steps=5, n_test=120, depth_max=4, seed=0, n_fit=3000):
    """Compare, sur une gamme de qualités de modèle : profondeur ADAPTATIVE (choisie via la fidélité mesurée)
    vs FIXE-1 vs FIXE-max, en succès ET en calcul."""
    W_list = _true_dynamics(d, K, seed)
    models = _fit_models(W_list, d, K, n_fit, seed)
    rng = np.random.RandomState(seed + 7)
    # gamme de fidélités : parfait, bilinéaire, bilinéaire + bruit croissant, linéaire (structurellement mauvais)
    regimes = [("perfect", 0.0), ("bilinear", 0.0), ("bilinear_noisy", 0.1),
               ("bilinear_noisy", 0.25), ("linear", 0.0)]
    rows = []
    for kind, noise in regimes:
        mse = _measure_fidelity(kind, W_list, models, noise, rng, d, K)
        d_ada = int(np.clip(depth_from_fidelity(mse, depth_max), 1, depth_max))
        s_ada, c_ada = _plan_success(kind, W_list, models, noise, rng, d_ada, d, K, exec_steps, n_test)
        s_lo, c_lo = _plan_success(kind, W_list, models, noise, rng, 1, d, K, exec_steps, n_test)
        s_hi, c_hi = _plan_success(kind, W_list, models, noise, rng, depth_max, d, K, exec_steps, n_test)
        rows.append({"kind": kind, "noise": noise, "mse": mse, "depth_ada": d_ada,
                     "adaptive": (s_ada, c_ada), "fixed1": (s_lo, c_lo), "fixedmax": (s_hi, c_hi)})
    return {"seed": int(seed), "depth_max": depth_max, "rows": rows}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("APP_SEEDS", "3"))))
    d = int(os.environ.get("APP_DIM", "8"))
    K = int(os.environ.get("APP_ACTIONS", "4"))
    exec_steps = int(os.environ.get("APP_EXEC", "5"))
    depth_max = int(os.environ.get("APP_DMAX", "4"))
    runs = [run_adaptive(d=d, K=K, exec_steps=exec_steps, depth_max=depth_max, seed=s) for s in seeds]

    regimes = [r["kind"] + (f"+{r['noise']}" if r["noise"] else "") for r in runs[0]["rows"]]
    print(f"d={d} K={K} exec={exec_steps} depth_max={depth_max} seeds={len(seeds)}")
    print(f"{'régime':18s} {'MSE':>6s} {'k_ada':>5s} | {'succ_ada':>8s} {'succ_1':>6s} {'succ_max':>8s} | "
          f"{'calc_ada':>9s} {'calc_max':>9s}")
    agg = {"ada_s": [], "lo_s": [], "hi_s": [], "ada_c": [], "hi_c": []}
    for i, name in enumerate(regimes):
        mse = statistics.median(r["rows"][i]["mse"] for r in runs)
        kada = statistics.median(r["rows"][i]["depth_ada"] for r in runs)
        sa = statistics.median(r["rows"][i]["adaptive"][0] for r in runs)
        s1 = statistics.median(r["rows"][i]["fixed1"][0] for r in runs)
        sm = statistics.median(r["rows"][i]["fixedmax"][0] for r in runs)
        ca = statistics.median(r["rows"][i]["adaptive"][1] for r in runs)
        cm = statistics.median(r["rows"][i]["fixedmax"][1] for r in runs)
        print(f"{name:18s} {mse:6.3f} {kada:5.0f} | {sa:8.3f} {s1:6.3f} {sm:8.3f} | {ca:9.0f} {cm:9.0f}")
        agg["ada_s"].append(sa); agg["lo_s"].append(s1); agg["hi_s"].append(sm)
        agg["ada_c"].append(ca); agg["hi_c"].append(cm)

    ada_s, lo_s, hi_s = np.mean(agg["ada_s"]), np.mean(agg["lo_s"]), np.mean(agg["hi_s"])
    ada_c, hi_c = np.sum(agg["ada_c"]), np.sum(agg["hi_c"])
    save = 1 - ada_c / hi_c
    # adaptatif réussit comme fixe-max (à ε près) MAIS moins cher, ET bat fixe-1
    verdict = ("ADAPTIVE_DEPTH_MATCHES_BEST_SUCCESS_AT_LOWER_COMPUTE"
               if ada_s >= hi_s - 0.03 and ada_s > lo_s + 0.03 and save > 0.15 else "ADAPTIVE_NEUTRAL")
    print(f"VERDICT={verdict} : succès adaptatif={ada_s:.3f} vs fixe-max={hi_s:.3f} vs fixe-1={lo_s:.3f} ; "
          f"calcul adaptatif={ada_c:.0f} vs fixe-max={hi_c:.0f} (économie {save*100:.0f}%)")


if __name__ == "__main__":
    main()
