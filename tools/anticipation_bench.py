"""Banc d'anticipation (NAS Axe 3) : danger télégraphié 1-pas. Le planificateur (PLAN_BIAS>0)
doit battre le réactif (0.0) sur un env CONÇU pour récompenser l'anticipation -> découple
'le plan marche' de 'le monde le récompense'. Déterministe, sans graph_rag (reproductible).
Usage : AB_SEEDS=0,1,2 python tools/anticipation_bench.py"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel

L = 7                     # longueur de la grille
T_WARN_PERIOD = 6         # un danger est télégraphié tous les N ticks


def _obs(pos: int, danger_cell: int) -> np.ndarray:
    """Obs = one-hot position (L) ++ one-hot danger télégraphié (L), paddé à num_inputs au forward."""
    o = np.zeros(2 * L, dtype=np.float32)
    o[pos] = 1.0
    if danger_cell is not None:
        o[L + danger_cell] = 1.0
    return o


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def run_bench(plan_bias: float, seeds, steps: int = 60) -> dict:
    per_seed = []
    for seed in seeds:
        np.random.seed(seed)
        a = MambaAgent()
        a.genome.organ_genes = np.array([True, False])      # organe planificateur actif
        prev_bias = MambaBatchModel.PLAN_BIAS
        MambaBatchModel.PLAN_BIAS = plan_bias
        try:
            m = MambaBatchModel([a])
            pos = L // 2
            danger_cell = None          # case mortelle au PROCHAIN tick
            alive_ticks = 0
            for t in range(steps):
                # résoudre le danger télégraphié au tick précédent
                if danger_cell is not None and pos == danger_cell:
                    break               # mort
                danger_cell = None
                warn = (t % T_WARN_PERIOD == 0)
                telegraph = pos if warn else None   # danger annoncé SUR la case courante
                obs = _obs(pos, telegraph)[None, :]
                preds, _ = m.forward(obs)
                move = int(np.argmax(preds[0, :8])) % 3     # 0=gauche,1=rester,2=droite
                new_pos = min(L - 1, max(0, pos + (move - 1)))
                # récompense : -1 si on reste sur une case télégraphiée, +0.1 sinon (s'éloigner paie)
                reward = -1.0 if (warn and new_pos == pos) else 0.1
                m.compute_policy_gradient(np.array([reward], dtype=np.float32),
                                          [{"move": move, "grab": 0, "rub": 0}])
                if warn:
                    danger_cell = telegraph             # frappe au tick suivant
                pos = new_pos
                alive_ticks += 1
            per_seed.append(alive_ticks / float(steps))
        finally:
            MambaBatchModel.PLAN_BIAS = prev_bias
    return {"survival_mean": float(st.mean(per_seed)) if per_seed else 0.0,
            "per_seed": [{"seed": int(s), "survival": v} for s, v in zip(seeds, per_seed)]}


def compare(seeds, steps: int = 60) -> dict:
    ratios = []
    for seed in seeds:
        plan = run_bench(0.5, [seed], steps)["survival_mean"]
        react = run_bench(0.0, [seed], steps)["survival_mean"]
        ratios.append(plan / max(react, 1e-6))
    eff = [r for r in ratios if r != 1.0]
    n_fav = sum(1 for r in ratios if r > 1.0)
    p = _sign_p(sum(1 for r in eff if r > 1.0), len(eff))
    med = st.median(ratios) if ratios else 1.0
    verdict = "PLAN_GAGNE" if (med > 1.05 and 2 * n_fav > len(ratios)) else \
              ("PLAN_PERD" if med < 0.95 else "NEUTRE")
    return {"verdict": verdict, "median_ratio": float(med), "sign_p": float(p),
            "n_favorable": int(n_fav), "n": len(ratios), "ratios": ratios}


def main():
    seeds = [int(s) for s in os.environ.get("AB_SEEDS", "0,1,2,3,4,5,6,7").split(",") if s.strip()]
    steps = int(os.environ.get("AB_STEPS", "60"))
    out = compare(seeds, steps)
    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    return out


if __name__ == "__main__":
    main()
