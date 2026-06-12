"""tools/robust_trajectory.py — Le fix fait-il GRIMPER la compétence au fil des générations ? (EDR 081)

EDR 076 : sous sélection bruitée, la compétence PLAFONNE/dérive sur les générations. EDR 080 : la
sélection robuste donne un meilleur champion FINAL. Question de compoundabilité : la robuste fait-elle
GRIMPER la compétence vraie au fil des générations, là où la bruitée plafonne ? On évolue N générations
et on mesure la compétence VRAIE du champion best-ever à des checkpoints, bruitée (K=1) vs robuste (K=4).
"""
import time
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.robust_eval import run_era, _reproduce, _load_champions, _robust_score, _true_competence
from tools.progress import Progress


def evolve_traj(cfg, K, gens, checkpoints, num_agents, mc, n_eval, prog):
    champions = _load_champions()
    best_ever = [(0.0, g) for g in champions]
    traj = {}
    for gen in range(1, gens + 1):
        genomes = _reproduce([g for _s, g in best_ever], num_agents, mc)
        scored, _ = run_era(cfg, genomes)
        if scored:
            if K > 1:
                top_g = scored[0][1]
                scored[0] = (_robust_score(cfg, top_g, K, num_agents), top_g)
            best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
        if gen in checkpoints:
            traj[gen] = _true_competence(cfg, best_ever[0][1], n_eval, num_agents)
    return traj


def main(gens=24, checkpoints=(6, 12, 18, 24), num_agents=30, n_eval=12):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    print(f"TRAJECTOIRE : competence vraie aux checkpoints {checkpoints}, BRUITEE (K=1) vs ROBUSTE (K=4).")
    tn = evolve_traj(cfg, 1, gens, checkpoints, num_agents, mc, n_eval, Progress(gens, label="BRUITEE (K=1)"))
    tr = evolve_traj(cfg, 4, gens, checkpoints, num_agents, mc, n_eval, Progress(gens, label="ROBUSTE (K=4)"))
    print("\n=== competence vraie (survie ticks) par generation ===")
    print("  gen   :  " + "  ".join(f"{c:>5d}" for c in checkpoints))
    print("  BRUIT :  " + "  ".join(f"{tn[c]:5.1f}" for c in checkpoints))
    print("  ROBUST:  " + "  ".join(f"{tr[c]:5.1f}" for c in checkpoints))
    cn = checkpoints
    slope_n = tn[cn[-1]] - tn[cn[0]]
    slope_r = tr[cn[-1]] - tr[cn[0]]
    print(f"\n  pente BRUITEE  : {slope_n:+.1f}   pente ROBUSTE : {slope_r:+.1f}")
    print("\n=== VERDICT ===")
    if slope_r > 3 and slope_r > slope_n + 3:
        print(f"  -> la ROBUSTE fait GRIMPER la competence ({tr[cn[0]]:.0f}->{tr[cn[-1]]:.0f}) la ou la bruitee")
        print(f"     stagne ({tn[cn[0]]:.0f}->{tn[cn[-1]]:.0f}). Le fix COMPOSE : la competence s'accumule.")
    elif tr[cn[-1]] > tn[cn[-1]] * 1.15:
        print(f"  -> robuste > bruitee a la fin ({tr[cn[-1]]:.0f} vs {tn[cn[-1]]:.0f}) ; avantage confirme, pente bruitee.")
    else:
        print(f"  -> pas de grimpee nette ({tr[cn[0]]:.0f}->{tr[cn[-1]]:.0f}) : compoundabilite limitee a ce N.")
    async_logger.stop()


if __name__ == "__main__":
    main()
