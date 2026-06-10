"""
tools/persistence_test.py — Sevrage du crit : la chasse à l'apex persiste-t-elle ? (EDR 028)

Question de la persistance (réflexion Vague 0quater) : le coup critique (EDR 022) est une
béquille *chanceuse*. Si on le **sèvre** (anneal → 0), la chasse au Mammouth s'effondre-t-elle
(dépendance au crit) ou tient-elle via une stratégie *robuste* (coopération : 2 lances
one-shotent l'apex, la riposte ne frappe qu'un agent) ?

Protocole : difficulté FIXE à la rareté extrême (6 proies — là où l'outil est requis, EDR 026),
crit annelé 0.6 → 0 sur les ères via l'ère GLOBALE (corrige le bug « chaque ère = ère 1 »).
On mesure crafts + Mammouths tués + survie à mesure que le crit s'efface.

Usage : HEADLESS=1 python -m tools.persistence_test
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.environments.stone_economy import anneal, crit_chance
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger


def run_era(config, db, global_era, target_prey=6, crit_base=0.6, crit_eras=20,
            eps=0.2, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = target_prey
    env.night_enabled = False
    env.explore_eps = eps
    env.craft_level = 0
    env.crit_base = crit_base
    env.crit_eras = crit_eras
    env.current_era = global_era      # cadence le crit (et les scaffolds) sur l'ère GLOBALE
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=energy)
    env.current_era = global_era
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
    mean_prey = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return crafts, env.big_kills, mean_prey, t


def main(eras=35, crit_base=0.6, crit_eras=20):
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

    print("SEVRAGE DU CRIT (rareté 6 fixe) — la chasse au Mammouth persiste-t-elle ?")
    pre, post = [], []
    for e in range(eras):
        crit = crit_chance(crit_base, e, crit_eras)
        crafts, big, mp, t = run_era(config, db, e, crit_base=crit_base, crit_eras=crit_eras)
        phase = "CRIT" if crit > 0 else "SEVRE"
        print(f"  ere {e:2d} [{phase:5s} crit={crit:.2f}]: crafts={crafts:3d} mammouth={big:2d} "
              f"proies_moy={mp:.2f} duree={t:3d}")
        (pre if crit > 0 else post).append(big)

    print("\n=== BILAN SEVRAGE ===")
    if pre:
        print(f"  Mammouths/ère AVEC crit  : {np.mean(pre):.2f}")
    if post:
        print(f"  Mammouths/ère SEVRE (crit=0) : {np.mean(post):.2f}  "
              f"-> {'PERSISTE (robuste)' if np.mean(post) >= 0.5 * (np.mean(pre) if pre else 1) else 'S EFFONDRE (crit-dependant)'}")
    async_logger.stop()


if __name__ == "__main__":
    main()
