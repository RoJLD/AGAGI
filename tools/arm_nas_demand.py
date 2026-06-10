"""
tools/arm_nas_demand.py — La recette du langage appliquée au NAS (EDR 049).

EDR 046 : dans le monde de base, forcer la croissance (add_node_rate haut) ne fait PAS grandir
l'architecture (HoF figé à 172) — le monde ne demande pas plus de cerveau. EDR 047/048 : la
*demande* fait émerger le langage. On applique la même recette au NAS : re-faire l'A/B add_node_rate
mais dans le **monde exigeant** (Lewis 3 référents : distinguer/signaler/décoder/naviguer). Si la
tâche plus riche fait grandir l'architecture sélectionnée (HoF > 172), la recette « la demande crée
la capacité » vaut aussi pour l'architecture.

Usage : HEADLESS=1 python -m tools.arm_nas_demand
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.lexicon import _setup            # monde exigeant (3 référents)
from tools.arm_nas import hof_stats
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def evolve(config, db, add_node_rate, eras, num_agents=30, max_ticks=200):
    proies = []
    for _ in range(eras):
        env = Biosphere3D(config)
        _setup(env)                          # tâche exigeante (Lewis 3 référents)
        genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config,
                                          add_node_rate=add_node_rate)
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
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
        proies.append(np.mean([a.get("preys_eaten", 0) for a in pool]) if pool else 0.0)
    return proies


def main(eras=18):
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
    half = eras // 2

    _backup()
    print(f"NAS SOUS DEMANDE (monde exigeant Lewis-3) : {eras} eres/lignee, meme depart.")
    pg = evolve(config, db, 0.6, eras)
    sz_g = hof_stats()
    print(f"  add_node_rate=0.6 : HoF nodes moy={sz_g[0]:.0f} max={sz_g[1]} | proies={np.mean(pg[half:]):.2f}")

    _restore()
    pd = evolve(config, db, 0.2, eras)
    sz_d = hof_stats()
    print(f"  add_node_rate=0.2 : HoF nodes moy={sz_d[0]:.0f} max={sz_d[1]} | proies={np.mean(pd[half:]):.2f}")

    print("\n=== VERDICT (vs EDR 046 : monde de base -> fige a 172) ===")
    grew = sz_g[1] > 174
    print(f"  architecture a grandi sous demande ? {'OUI (> 172)' if grew else 'NON (encore ~172)'}")
    if grew:
        print("  -> la recette vaut pour le NAS : la DEMANDE fait grandir l'architecture.")
    else:
        print("  -> meme la tache Lewis-3 ne sature pas 172 noeuds (demande encore insuffisante / autre goulot).")

    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
