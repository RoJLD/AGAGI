"""tools/robust_amplify.py — Amplification d'EDR 079 : le lift monte-t-il avec K ? (EDR 080)"""
import time
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.robust_eval import evolve, _true_competence
from tools.progress import Progress


def main(Ks=(1, 4, 8), eras=18, num_agents=30, n_final=18):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    print(f"AMPLIFICATION : le lift monte-t-il avec K ? K in {Ks}, {eras} eres, n_final={n_final}.")
    rows = []
    for K in Ks:
        p = Progress(eras, label=f"K={K}")
        champ = evolve(cfg, K, eras, num_agents, mc, p)
        tc = _true_competence(cfg, champ, n_final, num_agents)
        rows.append((K, tc))
        print(f"  K={K}: competence vraie = {tc:.1f} ticks")
    print("\n=== competence vraie vs K (de-bruitage) ===")
    base = rows[0][1]
    for K, tc in rows:
        print(f"  K={K:2d} : {tc:5.1f} ticks  (+{(tc/base-1)*100:+.0f}%)  {'#'*int(tc)}")
    print("\n=== VERDICT ===")
    if rows[-1][1] > rows[0][1] * 1.2:
        print(f"  -> le lift S'AMPLIFIE avec K ({rows[0][1]:.0f} -> {rows[-1][1]:.0f} ticks) : de-bruiter PLUS forge PLUS.")
    else:
        print(f"  -> lift sature/instable ({rows[0][1]:.0f} -> {rows[-1][1]:.0f}) ; K=4 suffit peut-etre.")
    async_logger.stop()


if __name__ == "__main__":
    main()
