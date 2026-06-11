"""
tools/nas_rich.py — NAS : vraie demande de mémoire (multi-types) + maturation + spéciation (EDR 062).

EDR 060 : la spéciation PROTÈGE l'innovation (archis 173-174 persistent) mais ne suffit pas à 20 ères
sur 1 bit de mémoire. On donne au NAS ce qui manquait : (a) une demande PLUS GROSSE (3 types d'apex à
retenir via l'indice transitoire, vs 2) et (b) plus de MATURATION (36 ères). Spéciation ON des deux
côtés. A/B mémoire (transient) ON vs OFF, multi-seed : les grandes archis PROLIFÈRENT-elles (node
count moyen ↑) et PAIENT-elles (perf ↑) ?

Usage : HEADLESS=1 python -m tools.nas_rich
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
import src.seed_ai.persistence as persistence
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.lexicon import _setup as _setup3        # 3 types : Mammouth, Ours, Leurre
from tools.arm_nas import hof_stats
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def _world(config, db, transient, add_node=0.6, num_agents=30):
    env = Biosphere3D(config)
    _setup3(env)                                    # 3 référents/types
    env.transient_apex = transient                  # mémoire : type révélé au 1er contact puis caché
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config, add_node_rate=add_node)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def run_seed(config, db, transient, seed, eras=36, max_ticks=200):
    persistence.SPECIATE = True                     # protection acquise (EDR 060)
    np.random.seed(seed)
    _restore()
    preys = []
    try:
        for _ in range(eras):
            env = _world(config, db, transient)
            t = 0
            while env.agents and t < max_ticks:
                env.step()
                t += 1
            pool = env.agents + env.dead_agents
            for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
            preys.append(np.mean([a.get("preys_eaten", 0) for a in pool]) if pool else 0.0)
        mean_nodes, max_nodes = hof_stats()
    finally:
        persistence.SPECIATE = False
    half = eras // 2
    return mean_nodes, max_nodes, float(np.mean(preys[half:]))


def arm(config, db, transient, seeds, eras, label):
    mean_n, max_n, perf = [], [], []
    for s in seeds:
        mn, mx, pf = run_seed(config, db, transient, s, eras)
        mean_n.append(mn)
        max_n.append(mx)
        perf.append(pf)
        print(f"  [{label}] seed {s}: nodes moy={mn:.1f} max={mx} | preys={pf:.2f}")
    return mean_n, max_n, perf


def main(seeds=range(5), eras=36):
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
    seeds = list(seeds)

    _backup()
    print(f"NAS-RICHE (3 types + maturation + speciation) : memoire ON vs OFF. {len(seeds)} seeds x {eras} eres.")
    on_mn, on_mx, on_p = arm(config, db, True, seeds, eras, "MEM")
    off_mn, off_mx, off_p = arm(config, db, False, seeds, eras, "OFF")

    res = {"memoire": _stats(on_mn), "base": _stats(off_mn)}
    v = verdict("memoire", "base", res, t_thresh=2.0)
    print("\n=== VERDICT (taille d'archi proliferante) ===")
    print(f"  OFF  : nodes moy={res['base']['mean']:.2f}+/-{res['base']['std']:.2f} max={max(off_mx):.0f} | preys={np.mean(off_p):.2f}")
    print(f"  MEM  : nodes moy={res['memoire']['mean']:.2f}+/-{res['memoire']['std']:.2f} max={max(on_mx):.0f} | preys={np.mean(on_p):.2f}")
    print(f"  {v['summary']}")
    grew = v["significant"] and v["winner"] == "memoire"
    if grew:
        print("  -> la demande de memoire fait PROLIFERER les grandes archis : la croissance PAIE (NAS boucle).")
    elif max(on_mx) > 174:
        print("  -> archis plus grandes preservees (max>174) mais pas dominantes : maturation/demande encore juste.")
    else:
        print("  -> la memoire-foraging ne sature pas : il faut une tache-memoire dediee (hors foraging).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
