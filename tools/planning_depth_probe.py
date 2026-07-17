"""Profondeur de planning × fidélité du modèle : y a-t-il une profondeur OPTIMALE ? (G4, PLAN-003)

PLAN-001/002 : un g bilinéaire fidèle débloque le planning depth-1, apprenable en ligne. Question naturelle :
planifier PLUS profond (depth-k, séquence d'actions anticipée) aide-t-il ? Résultat classique du model-based
RL : avec un modèle IMPARFAIT, chaque pas de rollout COMPOSE l'erreur -> il existe une profondeur optimale,
au-delà planifier profond EMPIRE. On teste l'interaction profondeur × fidélité.

Planner depth-k par MPC (receding horizon) : à chaque pas réel, énumère les séquences d'actions de longueur
k, roule le MODÈLE k pas, score l'état final prédit par distance au but, exécute la 1ʳᵉ action dans la VRAIE
dynamique, re-planifie. Modèles de fidélité décroissante : `perfect` (dynamique vraie), `bilinear` (ajusté),
`bilinear_noisy` (ajusté + bruit de prédiction), `linear` (ajusté, inadéquat car dynamique action-conditionnée).

Prédiction : perfect -> monotone (plus profond = mieux) ; bilinear -> aide (petite erreur) ; bilinear_noisy ->
optimum puis dégradation (erreur composée) ; linear -> plat/inutile à toute profondeur.

Usage : python tools/planning_depth_probe.py   (env: PDP_SEEDS, PDP_DIM, PDP_ACTIONS, PDP_EXEC, PDP_NOISE)
"""
import os
import sys
import numpy as np
from itertools import product

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.anticipation_planning_probe import _true_dynamics, _step, _fit_models, _predict


def _model_predict(kind, W_list, models, noise, rng, s, a, d, K):
    if kind == "perfect":
        return _step(W_list, s, a)                       # modèle = dynamique vraie (fidélité parfaite)
    p = _predict(models, "bilinear" if kind.startswith("bilinear") else "linear", s, a, d, K)
    if kind == "bilinear_noisy":
        p = p + noise * rng.randn(d)                     # bruit de prédiction -> compose sur le rollout
    return p


def _seq_score(kind, W_list, models, noise, rng, s, seq, goal, d, K):
    """Coût d'une séquence = distance MIN au but sur le rollout PRÉDIT (pas seulement l'état final) —
    matche l'objectif « se rapprocher à un moment » ; un coût terminal seul biaiserait contre la profondeur."""
    best = np.linalg.norm(s - goal)
    cur = s
    for a in seq:
        cur = _model_predict(kind, W_list, models, noise, rng, cur, a, d, K)
        best = min(best, np.linalg.norm(cur - goal))
    return best


def run_depth(d=8, K=4, exec_steps=5, n_test=120, depths=(1, 2, 3, 4), noise=0.15, seed=0, n_fit=3000):
    """Pour chaque modèle et chaque profondeur k, succès du planning MPC depth-k vers des buts jamais vus."""
    W_list = _true_dynamics(d, K, seed)
    models = _fit_models(W_list, d, K, n_fit, seed)
    rng = np.random.RandomState(seed + 5)
    seqs = {k: list(product(range(K), repeat=k)) for k in depths}

    out = {}
    for kind in ("perfect", "bilinear", "bilinear_noisy", "linear"):
        out[kind] = {}
        for k in depths:
            succ = []
            for _ in range(n_test):
                s = np.tanh(rng.randn(d))
                goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))
                d0 = np.linalg.norm(s - goal) + 1e-9
                best = d0
                for _e in range(exec_steps):
                    seq = min(seqs[k], key=lambda sq: _seq_score(
                        kind, W_list, models, noise, rng, s, sq, goal, d, K))
                    s = _step(W_list, s, seq[0])         # exécute la 1ʳᵉ action dans la VRAIE dynamique (MPC)
                    best = min(best, np.linalg.norm(s - goal))
                succ.append(1.0 if best < 0.5 * d0 else 0.0)
            out[kind][k] = float(np.mean(succ))
    return {"seed": int(seed), "depths": list(depths), "models": out}


def main():
    import statistics
    seeds = list(range(int(os.environ.get("PDP_SEEDS", "3"))))
    d = int(os.environ.get("PDP_DIM", "8"))
    K = int(os.environ.get("PDP_ACTIONS", "4"))
    exec_steps = int(os.environ.get("PDP_EXEC", "5"))
    noise = float(os.environ.get("PDP_NOISE", "0.15"))
    depths = (1, 2, 3, 4)
    rows = [run_depth(d=d, K=K, exec_steps=exec_steps, depths=depths, noise=noise, seed=s) for s in seeds]

    def m(kind, k):
        return statistics.median(r["models"][kind][k] for r in rows)

    print(f"d={d} K={K} exec={exec_steps} noise={noise} seeds={len(seeds)} (succès planning MPC par profondeur)")
    print("modèle           " + "  ".join(f"k={k}" for k in depths))
    for kind in ("perfect", "bilinear", "bilinear_noisy", "linear"):
        print(f"{kind:16s} " + "  ".join(f"{m(kind,k):.3f}" for k in depths))

    # gain de profondeur par modèle = succès au meilleur k − succès à k=1 ; la FIDÉLITÉ plafonne ce gain.
    def gain(kind):
        return max(m(kind, k) for k in depths) - m(kind, depths[0])
    g_bi, g_noisy, g_lin = gain("bilinear"), gain("bilinear_noisy"), gain("linear")
    ceil_bi, ceil_lin = max(m("bilinear", k) for k in depths), max(m("linear", k) for k in depths)
    # profondeur utile SI le modèle fidèle en tire un gain net, le bruité MOINS, le mauvais RIEN (coincé)
    gated = g_bi > 0.12 and g_bi > g_noisy + 0.05 and ceil_lin < 0.5
    verdict = ("PLANNING_DEPTH_HELPS_GATED_BY_MODEL_FIDELITY" if gated else "DEPTH_NEUTRAL")
    print(f"VERDICT={verdict} : gain(profondeur) bilinéaire={g_bi:+.2f} > bruité={g_noisy:+.2f} > "
          f"linéaire={g_lin:+.2f} ; plafond bilinéaire={ceil_bi:.2f} vs linéaire={ceil_lin:.2f} (coincé au hasard) "
          f"-> la fidélité PLAFONNE la valeur de la profondeur")


if __name__ == "__main__":
    main()
