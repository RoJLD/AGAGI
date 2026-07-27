"""Qu'est-ce qui BORNE la compositionnalité (within ~0.54) ? Crédit, budget, ou capacité ? (Arc 4, LANG-005)

LANG-003/004 : le code compositionnel émerge mais IMPARFAIT (within ~0.54, ~0.2 au-dessus de la chance).
Trois causes candidates au plafond :
- CRÉDIT : le retour JOINT (fraction d'attributs corrects) crédite symbole_t/guess_t par le succès des DEUX
  attributs -> variance (le succès sur a1 pollue le gradient de symbole_0). Un crédit PAR-ATTRIBUT
  (symbole_t/guess_t <- correction de a_t seule) donne un signal net.
- BUDGET : plus d'épisodes suffiraient (convergence incomplète).
- CAPACITÉ : plafond du substrat (LTC 172 nœuds, crédit tronqué) — si ni crédit ni budget ne montent.

Ablation {joint, per_attr} x {court, long} + un bras CAPACITÉ (num_nodes 172->384), FIXED (M=8, A=3, V=6,
2 seeds). Diagnostic sur le plafond de WITHIN (accuracy sur combos entraînés) :
- per_attr >> joint -> VARIANCE DE CRÉDIT.  - long >> court -> BUDGET.  - bigN >> N172 -> CAPACITÉ.
- plateau sur les TROIS -> RÉGIME D'OPTIMISATION (équilibre partiel de la co-adaptation REINFORCE ;
  ni capacité ni budget ni crédit ne lèvent le plafond). Résultat mesuré (LANG-005) : OPTIMIZATION_REGIME —
  within ~0.54 invariant ; MAIS capacité et per_attr améliorent la GÉNÉRALISATION (zeroshot), pas l'accuracy.

Usage : python tools/compositional_ceiling_probe.py  (env: CEP_SHORT, CEP_LONG, CEP_BIGNODES, CEP_SEEDS, CEP_A, CEP_V, CEP_AGENTS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main():
    import statistics
    from tools.compositional_language_probe import run_compositional

    short = int(os.environ.get("CEP_SHORT", "8000"))
    long = int(os.environ.get("CEP_LONG", "16000"))
    seeds = list(range(int(os.environ.get("CEP_SEEDS", "2"))))
    A = int(os.environ.get("CEP_A", "3"))
    V = int(os.environ.get("CEP_V", "6"))
    M = int(os.environ.get("CEP_AGENTS", "8"))
    chance = 1.0 / A

    big_nodes = int(os.environ.get("CEP_BIGNODES", "384"))       # arm CAPACITÉ (défaut 172 -> 384)

    def cell(credit, episodes, num_nodes=172):
        rows = [run_compositional(episodes=episodes, n_agents=M, A=A, V=V, seed=s, rotate=False,
                                  credit=credit, num_nodes=num_nodes) for s in seeds]
        return {k: statistics.median(r[k] for r in rows) for k in ("within", "zeroshot", "topsim")}

    grid = {}
    print(f"A={A} V={V} chance={chance:.2f} M={M} short={short} long={long} bigN={big_nodes} "
          f"seeds={len(seeds)} (FIXED)")
    for credit in ("joint", "per_attr"):
        for ep in (short, long):
            c = grid[(credit, ep, 172)] = cell(credit, ep)
            print(f"{credit:8s} ep={ep:6d} N=172 within={c['within']:.3f} zeroshot={c['zeroshot']:.3f} "
                  f"topsim={c['topsim']:+.3f}")
    cap = grid[("joint", short, big_nodes)] = cell("joint", short, num_nodes=big_nodes)   # arm capacité
    print(f"{'joint':8s} ep={short:6d} N={big_nodes} within={cap['within']:.3f} "
          f"zeroshot={cap['zeroshot']:.3f} topsim={cap['topsim']:+.3f}")

    # diagnostic : chaque levier lève-t-il le PLAFOND DE within ? (>0.08 = significatif)
    d_credit = grid[("per_attr", long, 172)]["within"] - grid[("joint", long, 172)]["within"]
    d_budget = grid[("joint", long, 172)]["within"] - grid[("joint", short, 172)]["within"]
    d_capacity = cap["within"] - grid[("joint", short, 172)]["within"]
    d_gen_cap = cap["zeroshot"] - grid[("joint", short, 172)]["zeroshot"]                  # levier généralisation
    best = max(c["within"] for c in grid.values())
    if max(d_credit, d_budget, d_capacity) < 0.08:
        cause = "OPTIMIZATION_REGIME"        # plafond invariant à crédit/budget/capacité = régime d'optim
    else:
        cause = ("CREDIT_VARIANCE" if d_credit >= max(d_budget, d_capacity) else
                 "BUDGET" if d_budget >= d_capacity else "SUBSTRATE_CAPACITY")
    print(f"VERDICT within_ceiling={best:.3f} cause={cause} : d_credit={d_credit:+.3f} "
          f"d_budget={d_budget:+.3f} d_capacity={d_capacity:+.3f} | levier GÉNÉRALISATION "
          f"d_zeroshot(capacité)={d_gen_cap:+.3f}")


if __name__ == "__main__":
    main()
