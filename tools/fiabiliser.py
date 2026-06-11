"""
tools/fiabiliser.py — Fiabiliser l'émergence du langage : la convention est-elle héritable ? (EDR 054)

EDR 053 : l'émergence est une loterie (~25 %, brisure de symétrie). Lever le plus direct : PROPAGER
une lignée chanceuse. Test : on cristallise une convention (un seed connu, 24 ères sous demande de
Lewis), puis on compare le TAUX d'émergence des descendants partant de ce FONDATEUR cristallisé vs
d'un départ de BASE (contrôle). Si propager fait bondir le taux -> la convention est héritable et
s'auto-renforce (effet fondateur) ; fiabiliser = amorcer une fois. Sinon -> elle n'est pas stable.

Mesure par le harnais (EDR 052) : par seed, MI réel vs permutation (null), gain. « Émergé » = gain
> 0.01. Verdict = taux fondateur vs taux base + Welch sur les gains.

Usage : HEADLESS=1 python -m tools.fiabiliser
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.arm_world_demand import _world
from tools.lewis_world import _apex_ctx
from tools.arc5_alignment import _mutual_info
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR

DEMAND = {"lewis": True}
EMERGE_THRESHOLD = 0.01


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def _evolve(config, db, eras, seed=None, max_ticks=200):
    if seed is not None:
        np.random.seed(seed)
    for _ in range(eras):
        env = _world(config, db, DEMAND)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
            save_to_hall_of_fame(cand)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()


def _measure_gain(config, db, reps=4, max_ticks=200):
    toks, ctxs = [], []
    for _ in range(reps):
        env = _world(config, db, DEMAND)
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


def _arm(config, db, seeds, cont_eras, label):
    gains = []
    for s in seeds:
        _restore()                                  # repart du backup courant (base ou fondateur)
        np.random.seed(s)
        _evolve(config, db, cont_eras)
        g = _measure_gain(config, db)
        gains.append(g)
        print(f"  [{label}] seed {s}: gain={g:+.4f}  {'EMERGE' if g > EMERGE_THRESHOLD else '.'}")
    rate = sum(1 for g in gains if g > EMERGE_THRESHOLD) / len(gains)
    return gains, rate


def main(seeds=range(6), cont_eras=12, founder_seed=0, founder_eras=24):
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

    _backup()                                       # BASE (départ commun, contrôle)
    print(f"FIABILISER : contrôle (base) vs fondateur cristallise. {len(seeds)} seeds x {cont_eras} eres.")
    base_gains, base_rate = _arm(config, db, seeds, cont_eras, "BASE")

    print(f"\n  cristallisation du fondateur (seed {founder_seed}, {founder_eras} eres)...")
    _restore()
    _evolve(config, db, founder_eras, seed=founder_seed)
    founder_mi = _measure_gain(config, db)
    print(f"  fondateur : gain={founder_mi:+.4f}  {'(cristallise)' if founder_mi > EMERGE_THRESHOLD else '(PAS cristallise !)'}")
    _backup()                                       # le HoF courant = FONDATEUR

    founder_gains, founder_rate = _arm(config, db, seeds, cont_eras, "FOND")

    res = {"fondateur": _stats(founder_gains), "base": _stats(base_gains)}
    v = verdict("fondateur", "base", res)
    print("\n=== VERDICT ===")
    print(f"  taux d'emergence : BASE={base_rate*100:.0f}%  vs  FONDATEUR={founder_rate*100:.0f}%")
    print(f"  {v['summary']}")
    if founder_rate > base_rate + 0.25 or (v['significant'] and v['winner'] == 'fondateur'):
        print("  -> PROPAGER fiabilise : la convention est heritable (effet fondateur). Amorcer 1x suffit.")
    else:
        print("  -> propager ne suffit pas : la convention n'est pas stable / regression vers la loterie.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
