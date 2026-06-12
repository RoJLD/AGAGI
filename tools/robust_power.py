"""tools/robust_power.py — Amplification AVEC PUISSANCE : K x R repetitions, moyenne +/- ecart (EDR 080).

EDR 079/080 : la validation a 1 run/regime est bruitee (le K=4 a chute). On AJOUTE de la puissance :
R runs independants par K -> moyenne +/- ecart. Repond a "puissance statistique". Usage : HEADLESS=1
python -m tools.robust_power
"""
import time
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.robust_eval import evolve, _true_competence
from tools.progress import Progress


def main(Ks=(1, 4, 8), R=4, eras=12, num_agents=30, n_final=15):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    total = len(Ks) * R
    print(f"PUISSANCE : K in {Ks}, R={R} runs/K, {eras} eres. {total} evolutions.")
    prog = Progress(total, label="runs")
    res = {K: [] for K in Ks}
    for K in Ks:
        for r in range(R):
            champ = evolve(cfg, K, eras, num_agents, mc, Progress(eras, label=f"K={K} run {r+1}/{R}"))
            res[K].append(_true_competence(cfg, champ, n_final, num_agents))
            prog.update()
    print("\n=== competence vraie (moyenne +/- ecart, R runs) vs K ===")
    rows = [(K, float(np.mean(res[K])), float(np.std(res[K]))) for K in Ks]
    for K, m, s in rows:
        print(f"  K={K:2d} : {m:5.1f} +/- {s:4.1f} ticks   {'#'*int(m)}")
    base = rows[0][1]
    print("\n=== VERDICT ===")
    hi = rows[-1]
    # test grossier : K eleve depasse-t-il K=1 d'au moins 1 ecart combine ?
    sep = (hi[1] - base) > (rows[0][2] + hi[2]) * 0.5
    if hi[1] > base * 1.15 and sep:
        print(f"  -> de-bruiter forge PLUS de competence, signal ROBUSTE : K=1 {base:.0f} -> K={hi[0]} {hi[1]:.0f} ticks (+{(hi[1]/base-1)*100:.0f}%).")
        print(f"     EDR 078/079 confirme avec puissance ; remede en production justifie.")
    elif hi[1] > base * 1.15:
        print(f"  -> tendance positive ({base:.0f} -> {hi[1]:.0f}) mais ecarts larges : effet reel, bruite (R plus grand).")
    else:
        print(f"  -> pas de separation nette sous puissance ({base:.0f} -> {hi[1]:.0f}) : le bruit social domine.")
    async_logger.stop()


if __name__ == "__main__":
    main()
