"""
tools/aligned_selection.py — Fiabiliser via sélection alignée (EDR 055, suite de 054).

EDR 054 : la convention érode car la sélection (life_score) est aveugle au langage. Remède :
`world.align_selection` prime la DISTINCTION référentielle par agent (tokens distincts près du
Mammouth vs du Leurre ; anti-piège 045 : token constant -> 0). Test : align ON vs OFF, multi-seed,
le TAUX d'émergence bondit-il au-dessus des ~25 % de base (EDR 053) ? Mesure via le harnais (052).

Usage : HEADLESS=1 python -m tools.aligned_selection
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
from tools.lewis_world import _setup_lewis, _apex_ctx
from tools.arc5_alignment import _mutual_info
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR

EMERGE = 0.01


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def _world(config, db, align, num_agents=30):
    env = Biosphere3D(config)
    _setup_lewis(env)
    env.align_selection = align
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def _gain(config, db, max_ticks=200):
    toks, ctxs = [], []
    for _ in range(4):
        env = _world(config, db, 0.0)             # mesure : align off (lecture pure)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                c = _apex_ctx(env, ag)
                if c == 0:
                    continue
                ls = ag.get("last_spoken", [0.0] * 4)
                toks.append(int(np.argmax(ls)) if any(abs(v) > 0.01 for v in ls) else 4)
                ctxs.append(1 if c == 1 else 0)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    if not toks:
        return 0.0
    mi = _mutual_info(toks, ctxs)
    perm = float(np.mean([_mutual_info(toks, np.random.permutation(np.array(ctxs)).tolist()) for _ in range(5)]))
    return mi - perm


def arm(config, db, align, seeds, eras, label, max_ticks=200):
    gains = []
    for s in seeds:
        _restore()
        np.random.seed(s)
        for _ in range(eras):
            env = _world(config, db, align)
            t = 0
            while env.agents and t < max_ticks:
                env.step()
                t += 1
            for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
        g = _gain(config, db)
        gains.append(g)
        print(f"  [{label}] seed {s}: gain={g:+.4f}  {'EMERGE' if g > EMERGE else '.'}")
    rate = sum(1 for g in gains if g > EMERGE) / len(gains)
    return gains, rate


def main(seeds=range(6), eras=16, align=3.0):
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
    print(f"SELECTION ALIGNEE : align ON({align}) vs OFF. {len(seeds)} seeds x {eras} eres.")
    on_g, on_rate = arm(config, db, align, seeds, eras, "ON")
    off_g, off_rate = arm(config, db, 0.0, seeds, eras, "OFF")

    res = {"align": _stats(on_g), "base": _stats(off_g)}
    v = verdict("align", "base", res)
    print("\n=== VERDICT ===")
    print(f"  taux d'emergence : OFF={off_rate*100:.0f}%  vs  ALIGN={on_rate*100:.0f}%")
    print(f"  {v['summary']}")
    if on_rate > off_rate + 0.25 or (v["significant"] and v["winner"] == "align"):
        print("  -> la selection alignee FIABILISE l'emergence (life_score etait aveugle, EDR 054 confirme).")
    else:
        print("  -> pas d'effet net : aligner la selection ne suffit pas (a cette force/puissance).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
