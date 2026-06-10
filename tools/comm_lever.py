"""
tools/comm_lever.py — Levier structurel de communication (EDR 038, Vague 3 / option B).

L'EDR 037 a montré : activer le canal de langage (signal same-cell) ne crée que du bruit, la
chaîne plafonne (impasse). Hypothèse B : le signal était inutile car **sans portée** — on
n'entend les alliés qu'une fois déjà ensemble. On donne au signal une **portée** (`hear_radius`,
atténuée) -> capacité physique de **recruter** le pack vers l'apex. Le *sens* n'est pas scripté ;
la pression (coopération payante, EDR 028) existe déjà. Test : la portée brise-t-elle l'impasse
(mammouth qui remonte) ou non ?

Compare à l'EDR 037 (radius 0 : mammouth déclin -0.048, plateau). Verdict via `compute_trend`.

Usage : HEADLESS=1 python -m tools.comm_lever
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.reflexive_supervisor import compute_trend
from src.graph_rag.async_logger import logger as async_logger


def run_era(config, db, hear_radius, target_prey=12, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = target_prey
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = hear_radius                 # PORTÉE du signal (le levier B)
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=energy)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = env.agents + env.dead_agents
    for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
        save_to_hall_of_fame(cand)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    crafts = sum(a.get("spears_crafted", 0) for a in pool)
    mp = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return crafts, env.big_kills, mp


def main(eras=30, target_prey=12, hear_radius=3):
    async_logger.start()
    db = None
    for _ in range(50):
        db = async_logger.get_db()
        if db:
            break
        time.sleep(0.1)
    if db is None:
        print("KuzuDB indisponible.")
        return
    config = WorldConfig()

    print(f"LEVIER B : {eras} eres, rarete {target_prey}, LANGUAGE on, hear_radius={hear_radius}.")
    mammo, proies, crafts_s = [], [], []
    for e in range(eras):
        c, b, mp = run_era(config, db, hear_radius, target_prey)
        mammo.append(b); proies.append(mp); crafts_s.append(c)
        print(f"  ere {e:2d}: mammouth={b:2d} proies_moy={mp:.2f} crafts={c:3d}")

    half = eras // 2
    print("\n=== VERDICT (tendance 2e moitie vs EDR 037 radius=0) ===")
    for name, series, ref in (("mammouth", mammo, "-0.048 (declin)"),
                              ("proies_moy", proies, "plateau ~1.0"),
                              ("crafts", crafts_s, "-0.029 (declin)")):
        tr = compute_trend(series[half:])
        print(f"  {name:11s}: direction={tr['direction']:9s} pente={tr['slope']:+.4f} "
              f"moy={tr['mean']:.2f}   (EDR037 radius0: {ref})")
    print("\n  -> mammouth qui REMONTE = la portee a brise l'impasse (recrutement emerge).")
    async_logger.stop()


if __name__ == "__main__":
    main()
