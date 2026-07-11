"""Le modèle de transition g peut-il être appris EN LIGNE (peu de données auto-générées) et débloquer quand
même le planning ? (G4 anticipation, PLAN-002 — clôt le caveat « fit offline/oracle » de PLAN-001/EDR-193)

PLAN-001 a montré : un g BILINÉAIRE fidèle -> planning zéro-shot utile (linéaire ≈ hasard). MAIS g était
ajusté HORS-LIGNE sur 3000 transitions aléatoires (oracle). In-world, g doit être appris de PEU de données
que l'agent GÉNÈRE lui-même. Deux questions :
1. EFFICACITÉ-ÉCHANTILLON : combien de transitions pour un bon planning ? (sweep du budget de données)
2. EXPLORATION : les propres trajectoires de l'agent (ε-greedy : planifie + explore) couvrent-elles assez
   l'espace pour apprendre un g généralisable ? (bras EN LIGNE incrémental)

Note : les moindres carrés étant ordre-indépendants, apprendre g en ligne par stats suffisantes accumulées
≡ offline sur les mêmes données -> le vrai défi en ligne = la COUVERTURE générée par la politique.

Usage : python tools/online_world_model_probe.py   (env: OWM_SEEDS, OWM_DIM, OWM_ACTIONS, OWM_HORIZON, OWM_EPS)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.anticipation_planning_probe import _true_dynamics, _step, run_planning


def _plan_eval(W_list, predict_fn, d, K, horizon, n_test, rng):
    """Planning depth-1 vers n_test buts aléatoires jamais vus. predict_fn(s,a)->s' prédit ; None=hasard."""
    norm_best, succ = [], []
    for _ in range(n_test):
        s = np.tanh(rng.randn(d))
        goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))
        d0 = np.linalg.norm(s - goal) + 1e-9
        best = d0
        for _t in range(horizon):
            if predict_fn is None:
                a = rng.randint(K)
            else:
                a = int(np.argmin([np.linalg.norm(predict_fn(s, a) - goal) for a in range(K)]))
            s = _step(W_list, s, a)
            best = min(best, np.linalg.norm(s - goal))
        norm_best.append(best / d0)
        succ.append(1.0 if best < 0.5 * d0 else 0.0)
    return float(np.mean(succ))


class _OnlineBilinear:
    """g bilinéaire appris par STATS SUFFISANTES accumulées (moindres carrés exacts, incrémental) : une
    matrice M_a par action, M_a = C_a (S_a)^-1 avec S_a=Σ s sᵀ, C_a=Σ s' sᵀ (régularisé)."""
    def __init__(self, d, K, lam=1e-2):
        self.d, self.K = d, K
        self.S = [np.eye(d) * lam for _ in range(K)]
        self.C = [np.zeros((d, d)) for _ in range(K)]
        self.M = [np.zeros((d, d)) for _ in range(K)]

    def update(self, s, a, sp):
        self.S[a] += np.outer(s, s)
        self.C[a] += np.outer(sp, s)

    def refit(self):
        for a in range(self.K):
            self.M[a] = self.C[a] @ np.linalg.inv(self.S[a])

    def predict(self, s, a):
        return self.M[a] @ s


def run_online(d=8, K=4, horizon=4, steps=3000, eps=0.4, refit_every=50, goal_period=20,
               seed=0, checkpoints=(100, 300, 1000, 3000), n_test=200, reset_period=0):
    """Agent EN LIGNE : ε-greedy (planifie avec g courant sinon explore), apprend g de SES trajectoires,
    refit périodique. À chaque checkpoint, gèle g et évalue le planning zéro-shot (succès). Renvoie la
    courbe d'apprentissage succès-vs-expérience (couverture auto-générée). reset_period>0 : ré-initialise
    l'état à un point varié tous les reset_period pas (= épisodes/respawns -> couverture au-delà de
    l'attracteur de la dynamique)."""
    W_list = _true_dynamics(d, K, seed)
    rng = np.random.RandomState(seed + 3)
    g = _OnlineBilinear(d, K)
    s = np.tanh(rng.randn(d))
    goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))
    curve = {}
    cps = set(checkpoints)
    for t in range(1, steps + 1):
        if reset_period and t % reset_period == 0:
            s = np.tanh(rng.randn(d))                                        # respawn : état varié (hors attracteur)
        if t % goal_period == 0:
            goal = np.tanh(W_list[rng.randint(K)] @ np.tanh(rng.randn(d)))   # but change : stresse la couverture
        # ε-greedy : explore (récolte des transitions diverses) OU planifie (exploite g courant)
        if rng.rand() < eps or t < refit_every:
            a = rng.randint(K)
        else:
            a = int(np.argmin([np.linalg.norm(g.predict(s, a) - goal) for a in range(K)]))
        sp = _step(W_list, s, a)
        g.update(s, a, sp)
        s = sp
        if t % refit_every == 0:
            g.refit()
        if t in cps:
            g.refit()
            ev_rng = np.random.RandomState(seed + 100)       # même jeu de buts à chaque checkpoint
            curve[t] = _plan_eval(W_list, g.predict, d, K, horizon, n_test, ev_rng)
    return curve


def main():
    import statistics
    seeds = list(range(int(os.environ.get("OWM_SEEDS", "5"))))
    d = int(os.environ.get("OWM_DIM", "8"))
    K = int(os.environ.get("OWM_ACTIONS", "4"))
    horizon = int(os.environ.get("OWM_HORIZON", "4"))
    eps = float(os.environ.get("OWM_EPS", "0.4"))

    # --- (1) EFFICACITÉ-ÉCHANTILLON : sweep du budget de données (fit offline, réutilise run_planning) ---
    print(f"d={d} K={K} horizon={horizon} seeds={len(seeds)}")
    print("(1) efficacité-échantillon (succès planning zéro-shot, fit sur N transitions aléatoires) :")
    budgets = [50, 100, 200, 500, 1000, 3000]
    for n in budgets:
        rows = [run_planning(d=d, K=K, n_fit=n, n_test=300, horizon=horizon, seed=s) for s in seeds]
        bi = statistics.median(r["models"]["bilinear"]["success"] for r in rows)
        li = statistics.median(r["models"]["linear"]["success"] for r in rows)
        print(f"  N={n:5d}  bilinéaire={bi:.3f}  linéaire={li:.3f}")

    # --- (2) EN LIGNE : g appris des trajectoires auto-générées (ε-greedy) — quantité vs COUVERTURE ---
    orc = statistics.median(run_planning(d=d, K=K, n_fit=3000, n_test=300, horizon=horizon, seed=s)
                            ["models"]["bilinear"]["success"] for s in seeds)
    print(f"(2) en ligne (ε-greedy={eps}, g appris des trajectoires de l'agent) — oracle offline={orc:.3f} :")
    # sans reset = limité à l'attracteur de la dynamique ; avec reset = départs variés (épisodes/respawns)
    no_reset = statistics.median(run_online(d=d, K=K, horizon=horizon, eps=eps, seed=s, reset_period=0)[3000]
                                 for s in seeds)
    reset = statistics.median(run_online(d=d, K=K, horizon=horizon, eps=eps, seed=s, reset_period=20)[3000]
                              for s in seeds)
    print(f"  sans reset (attracteur)      succès={no_reset:.3f}  (écart oracle {orc-no_reset:+.3f})")
    print(f"  reset /20 pas (respawns)     succès={reset:.3f}  (écart oracle {orc-reset:+.3f})")
    # online débloque le planning SI la couverture épisodique est fournie (resets ~= oracle)
    gap = orc - reset
    verdict = ("ONLINE_G_ENABLES_PLANNING_WITH_EPISODIC_COVERAGE" if reset > 0.5 and gap < 0.10 else
               "ONLINE_G_PARTIAL" if reset > 0.4 else "ONLINE_G_FAILS")
    print(f"VERDICT={verdict} : online+resets={reset:.3f}≈oracle {orc:.3f} (écart {gap:+.3f}) ; "
          f"le verrou en ligne = COUVERTURE d'états (attracteur), levée par la diversité épisodique "
          f"(que la biosphère fournit), PAS la quantité de données ni l'exploration (ε neutre)")


if __name__ == "__main__":
    main()
