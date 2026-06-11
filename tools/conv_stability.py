"""
tools/conv_stability.py — La convention référentielle est-elle STABLE sous sélection ? (EDR 054)

EDR 053 : l'émergence est une loterie (~25 %). Pour la fiabiliser, question préalable : une convention
cristallisée PERSISTE-t-elle, ou s'érode-t-elle ? Le HoF sélectionne par `life_score` (chasse/survie),
AVEUGLE à l'aptitude référentielle. Test propre : une lignée CONTINUE unique sous la demande de Lewis,
MI mesuré tous les `block` ères. Cristallise-t-elle puis tient, ou monte puis redescend ?

(Remplace l'expérience confondue `fiabiliser.py` : seeds identiques entre arms -> effet lavé.)

Usage : HEADLESS=1 python -m tools.conv_stability
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.arm_world_demand import _world
from tools.lewis_world import _apex_ctx
from tools.arc5_alignment import _mutual_info

DEMAND = {"lewis": True}


def _evolve(config, db, eras, max_ticks=200):
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


def _gain(config, db, reps=4, max_ticks=200):
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


def main(blocks=6, block_eras=8, seed=0):
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
    np.random.seed(seed)

    print(f"STABILITE DE LA CONVENTION : lignee continue, {blocks}x{block_eras} eres, MI(gain) par bloc.")
    traj = []
    for b in range(blocks):
        _evolve(config, db, block_eras)
        g = _gain(config, db)
        traj.append(g)
        era = (b + 1) * block_eras
        bar = "#" * max(0, int(g * 400))
        print(f"  ere {era:3d} : gain={g:+.4f}  {bar}")

    peak = max(traj)
    last = traj[-1]
    print("\n=== VERDICT ===")
    print(f"  pic={peak:+.4f} (ere {(traj.index(peak)+1)*block_eras}) ; final={last:+.4f}")
    if peak > 0.015 and last < peak * 0.5:
        print("  -> la convention CRISTALLISE puis S'ERODE : la selection (life_score) ne la preserve pas.")
        print("     => fiabiliser exige de SELECTIONNER POUR la convention (life_score est aveugle au langage).")
    elif peak > 0.015 and last >= peak * 0.5:
        print("  -> la convention cristallise et PERSISTE : stable une fois formee (amorcer 1x suffirait).")
    else:
        print("  -> pas de cristallisation nette sur cette lignee (loterie : ce seed n'a pas tire le bon numero).")
    async_logger.stop()


if __name__ == "__main__":
    main()
