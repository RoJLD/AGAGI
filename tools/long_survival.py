"""tools/long_survival.py — La SURVIE LONGUE émerge-t-elle ? (EDR 084)

EDR 082/083 : le langage ne paye pas car les agents MEURENT avant que la coordination paye (survivants=0).
Dernier verrou = la survie soutenue. Question : sous évolution robuste (K=4) dans le monde de base
(avec nourriture), la survie GRIMPE-t-elle vers l'indéfini (le cap d'ère) ou plafonne-t-elle ? On trace
la survie vraie (extinction moyenne) sur 40 générations + on lit le plafond.

Usage : HEADLESS=1 python -m tools.long_survival
"""
import time
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.robust_eval import run_era, _reproduce, _load_champions, _robust_score, _true_competence
from tools.progress import Progress

CAP = 400   # max_ticks d'une ère (run_era) : la survie ne peut pas le dépasser


def main(gens=40, K=4, checkpoints=(5, 10, 20, 30, 40), num_agents=30, n_eval=12):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    print(f"SURVIE LONGUE : evolution robuste (K={K}), {gens} gens, monde de base. Cap d'ere = {CAP} ticks.")
    best = [(0.0, g) for g in _load_champions()]
    traj = {}
    prog = Progress(gens, label="evolution robuste")
    for gen in range(1, gens + 1):
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        scored, _ = run_era(cfg, genomes)
        if scored and K > 1:
            g0 = scored[0][1]
            scored[0] = (_robust_score(cfg, g0, K, num_agents), g0)
        best = sorted(best + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
        if gen in checkpoints:
            traj[gen] = _true_competence(cfg, best[0][1], n_eval, num_agents)   # survie vraie (ticks)
    print("\n=== SURVIE VRAIE (ticks avant extinction) par generation ===")
    print("  gen    :  " + "  ".join(f"{c:>5d}" for c in checkpoints))
    print("  survie :  " + "  ".join(f"{traj[c]:5.1f}" for c in checkpoints))
    s0, sN = traj[checkpoints[0]], traj[checkpoints[-1]]
    pente = (sN - s0) / (checkpoints[-1] - checkpoints[0])
    extrap = (CAP - sN) / pente if pente > 0.05 else float("inf")
    print(f"\n  pente ~ {pente:+.2f} ticks/gen ; plafond atteint = {sN:.0f}/{CAP}")
    print("\n=== VERDICT ===")
    if sN >= CAP * 0.8:
        print(f"  -> SURVIE LONGUE ATTEINTE ({sN:.0f}/{CAP}) : les agents survivent quasi-indefiniment.")
        print("     Le dernier verrou cede -> re-tester le benefice du langage sur ce substrat.")
    elif pente > 0.5:
        print(f"  -> la survie GRIMPE ({s0:.0f}->{sN:.0f}, {pente:+.1f}/gen) mais lentement : ~{extrap:.0f} gens")
        print(f"     de plus pour atteindre l'indefini. Levier d'appoint utile (monde plus nourricier ?).")
    else:
        print(f"  -> la survie PLAFONNE ({s0:.0f}->{sN:.0f}) bien sous le cap : verrou structurel (metabolisme/")
        print(f"     mort par combat ?) -> l'evolution seule ne suffit pas, il faut un levier de monde.")
    async_logger.stop()


if __name__ == "__main__":
    main()
