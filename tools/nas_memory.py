"""
tools/nas_memory.py — NAS sous demande de MÉMOIRE (EDR 058).

EDR 046/049 : forcer add_node ne fait pas grandir l'architecture car le monde ne demande pas plus de
cerveau (la perception suffit à 172 nœuds). EDR 058 : on crée une demande de MÉMOIRE (type d'apex
transitoire -> l'agent doit RETENIR pour rester/fuir). Test : la croissance architecturale est-elle
ENFIN sélectionnée ? A/B transient ON vs OFF (add_node=0.6 des deux côtés), multi-seed via le harnais
(EDR 052) : la taille du connectome dans le HoF est-elle plus grande sous demande de mémoire ?

Usage : HEADLESS=1 python -m tools.nas_memory
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.lewis_world import _setup_lewis
from tools.arm_nas import hof_stats
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def _world(config, db, transient, add_node, num_agents=30):
    env = Biosphere3D(config)
    _setup_lewis(env)
    env.transient_apex = transient
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config, add_node_rate=add_node)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def run_seed(config, db, transient, seed, eras=16, add_node=0.6, max_ticks=200):
    np.random.seed(seed)
    _restore()
    mammo = 0
    for _ in range(eras):
        env = _world(config, db, transient, add_node)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
            save_to_hall_of_fame(cand)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
        mammo += env.big_kills
    mean_nodes, max_nodes = hof_stats()
    return mean_nodes, max_nodes, mammo / eras


def arm(config, db, transient, seeds, eras, label):
    nodes, perf = [], []
    for s in seeds:
        mn, mx, pf = run_seed(config, db, transient, s, eras)
        nodes.append(mn)
        perf.append(pf)
        print(f"  [{label}] seed {s}: HoF nodes_moy={mn:.0f} max={mx} | mammouth/ere={pf:.2f}")
    return nodes, perf


def main(seeds=range(6), eras=16):
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
    print(f"NAS-MEMOIRE : transient ON vs OFF (add_node=0.6). {len(seeds)} seeds x {eras} eres.")
    on_n, on_p = arm(config, db, True, seeds, eras, "MEM")
    off_n, off_p = arm(config, db, False, seeds, eras, "OFF")

    res = {"memoire": _stats(on_n), "base": _stats(off_n)}
    v = verdict("memoire", "base", res, t_thresh=2.0)
    print("\n=== VERDICT (taille du connectome HoF) ===")
    print(f"  OFF  : nodes={res['base']['mean']:.1f}+/-{res['base']['std']:.1f} | mammouth/ere={np.mean(off_p):.2f}")
    print(f"  MEM  : nodes={res['memoire']['mean']:.1f}+/-{res['memoire']['std']:.1f} | mammouth/ere={np.mean(on_p):.2f}")
    print(f"  {v['summary']}")
    if v["significant"] and v["winner"] == "memoire":
        print("  -> la demande de MEMOIRE fait grandir l'architecture : recette NAS validee (vs 046/049).")
    elif res["memoire"]["mean"] > res["base"]["mean"] + 1:
        print("  -> tendance a la croissance sous demande de memoire (a confirmer en puissance).")
    else:
        print("  -> pas de croissance : meme 1 bit de memoire ne sature pas 172 noeuds (demande trop petite).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
