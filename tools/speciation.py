"""
tools/speciation.py — Protéger l'innovation : spéciation par taille d'archi (EDR 060).

EDR 058 : l'architecture ne grandit jamais (172) car le HoF élitiste strict tue l'innovation immature
(un 173-nœuds quasi-neutre est battu par les 172 rodés avant de mûrir). Remède NEAT : la SPÉCIATION
(`persistence.SPECIATE`) réserve une niche par taille -> le 173 garde un siège et peut optimiser son
nouveau nœud. Test sur la tâche-MÉMOIRE (transient_apex) : A/B spéciation ON vs OFF, multi-seed.

Départage 2 hypothèses :
  - si SPÉCIATION -> perf MONTE (et taille croît utilement) : l'obstacle etait la PROTECTION (058) ;
  - si SPÉCIATION -> grandes archis preservees mais perf inchangee : l'obstacle etait la DEMANDE
    (1 bit de memoire trop bon marche -> il faut une demande plus grosse).

Usage : HEADLESS=1 python -m tools.speciation
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
import src.seed_ai.persistence as persistence
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.nas_memory import _world
from tools.arm_nas import hof_stats
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def run_seed(config, db, speciate, seed, eras=20, transient=True, add_node=0.6, max_ticks=200):
    persistence.SPECIATE = speciate
    np.random.seed(seed)
    _restore()
    mammo = 0
    try:
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
    finally:
        persistence.SPECIATE = False
    return mammo / eras, mean_nodes, max_nodes


def arm(config, db, speciate, seeds, eras, label):
    perf, mean_n, max_n = [], [], []
    for s in seeds:
        pf, mn, mx = run_seed(config, db, speciate, s, eras)
        perf.append(pf)
        mean_n.append(mn)
        max_n.append(mx)
        print(f"  [{label}] seed {s}: mammouth/ere={pf:.2f} | nodes moy={mn:.1f} max={mx}")
    return perf, mean_n, max_n


def main(seeds=range(6), eras=20):
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
    print(f"SPECIATION (tache memoire) : ON vs OFF. {len(seeds)} seeds x {eras} eres.")
    on_p, on_mn, on_mx = arm(config, db, True, seeds, eras, "SPEC")
    off_p, off_mn, off_mx = arm(config, db, False, seeds, eras, "OFF")

    res = {"spec": _stats(on_p), "base": _stats(off_p)}
    v = verdict("spec", "base", res, t_thresh=2.0)
    print("\n=== VERDICT ===")
    print(f"  OFF  : mammouth/ere={res['base']['mean']:.2f}+/-{res['base']['std']:.2f} | nodes moy={np.mean(off_mn):.1f} max={max(off_mx):.0f}")
    print(f"  SPEC : mammouth/ere={res['spec']['mean']:.2f}+/-{res['spec']['std']:.2f} | nodes moy={np.mean(on_mn):.1f} max={max(on_mx):.0f}")
    print(f"  {v['summary']}")
    grew = np.mean(on_mn) > np.mean(off_mn) + 0.5
    helped = v["significant"] and v["winner"] == "spec"
    if helped:
        print("  -> la SPECIATION aide : l'obstacle etait la PROTECTION de l'innovation (EDR 058 confirme).")
    elif grew:
        print("  -> grandes archis PRESERVEES mais perf inchangee : l'obstacle est la DEMANDE (1 bit trop bon marche).")
    else:
        print("  -> ni croissance ni gain : ni protection ni demande ne suffisent a cette echelle.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
