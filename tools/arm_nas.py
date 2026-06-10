"""
tools/arm_nas.py — Arming DIRIGÉ du #8 sur la frontière ARCHITECTURE/NAS (EDR 046).

Constat : tous les champions du HoF font 172 nœuds (figé), alors que `add_node` fonctionne et que
`add_node_rate=0.2`. Hypothèse : la croissance *a lieu* (enfants) mais n'est pas *sélectionnée* — le
monde ne demande pas plus de cerveau. Arming dirigé : forcer la croissance (`add_node_rate` haut) et
mesurer si l'architecture grandit (HoF) ET si la perf s'améliore. A/B même HoF de départ.

Si haut add_node_rate -> HoF plus gros ET meilleure perf : l'architecture aide (NAS fructueux).
Si HoF reste ~172 / perf inchangée : la capacité n'est pas le goulot (le monde ne l'exige pas).

Usage : HEADLESS=1 python -m tools.arm_nas
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score, load_hall_of_fame
from src.graph_rag.async_logger import logger as async_logger
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def evolve(config, db, add_node_rate, eras, num_agents=30, max_ticks=200):
    proies, mammo = [], []
    for _ in range(eras):
        env = Biosphere3D(config)
        env.config.target_prey_count = 12
        env.night_enabled = False
        env.explore_eps = 0.15
        env.craft_level = 0
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
        mammo.append(env.big_kills)
    return proies, mammo


def hof_stats():
    _, hof = load_hall_of_fame()
    sizes = [(e.genome if hasattr(e, "genome") else e[1]).num_nodes for e in hof]
    return (float(np.mean(sizes)), int(max(sizes))) if sizes else (0, 0)


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
    print(f"ARMING NAS (dirige) : {eras} eres/lignee, meme depart.")
    pg, mg = evolve(config, db, 0.6, eras)         # croissance FORCÉE
    sz_g = hof_stats()
    print(f"  add_node_rate=0.6 (croissance) : HoF nodes moy={sz_g[0]:.0f} max={sz_g[1]} | "
          f"proies={np.mean(pg[half:]):.2f} mammouth={np.mean(mg[half:]):.2f}")

    _restore()
    pd, md = evolve(config, db, 0.2, eras)          # défaut
    sz_d = hof_stats()
    print(f"  add_node_rate=0.2 (defaut)     : HoF nodes moy={sz_d[0]:.0f} max={sz_d[1]} | "
          f"proies={np.mean(pd[half:]):.2f} mammouth={np.mean(md[half:]):.2f}")

    print("\n=== VERDICT ===")
    grew = sz_g[1] > sz_d[1] + 2
    better = np.mean(pg[half:]) > np.mean(pd[half:]) + 0.1
    print(f"  architecture a grandi ? {'OUI' if grew else 'NON (figee ~172)'}")
    print(f"  perf amelioree ?        {'OUI' if better else 'NON'}")
    if grew and better:
        print("  -> le NAS aide : la capacite etait un goulot (frontiere fructueuse).")
    else:
        print("  -> la capacite n'est PAS le goulot : le monde n'exige pas plus de cerveau.")

    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
