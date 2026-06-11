"""
tools/reconfirm_047.py — Re-confirmer l'émergence du langage (047) SOUS PUISSANCE (EDR 053).

EDR 052 : nos verdicts à 1 run étaient non fiables ; 047 (lewis_2ref) variait 0.019/0.002/0.017 selon
le seed. Avant d'en faire une fondation, on le re-teste proprement : 8 seeds × 24 ères, et pour
CHAQUE seed on compare le MI réel (token↔Mammouth/Leurre, évolué sous la demande de Lewis) à sa
PERMUTATION (le null « aucune information »). Test apparié via le harnais (Welch + Cohen).

Verdict honnête : si `reel` bat `permute` de façon SIGNIFICATIVE sur 8 seeds -> le langage référentiel
émerge VRAIMENT sous demande (047 confirmé). Sinon -> 047 était du bruit, à ne pas survendre.

Usage : HEADLESS=1 python -m tools.reconfirm_047
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

DEMAND = {"lewis": True}            # demande référentielle réelle (047)


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def run_seed(config, db, seed, eras=24, max_ticks=200):
    np.random.seed(seed)
    _restore()                                          # même HoF de départ pour chaque seed
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
    # Mesure : collecte token/contexte chez les agents adjacents à un gros gibier.
    toks, ctxs = [], []
    for _ in range(4):
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
        return 0.0, 0.0
    mi_real = _mutual_info(toks, ctxs)
    mi_perm = float(np.mean([_mutual_info(toks, np.random.permutation(np.array(ctxs)).tolist())
                             for _ in range(5)]))
    return mi_real, mi_perm


def main(seeds=range(8)):
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

    _backup()
    reals, perms = [], []
    print(f"RE-CONFIRMATION 047 (langage sous demande), {len(list(seeds))} seeds x 24 eres.")
    for s in seeds:
        mi_r, mi_p = run_seed(config, db, s)
        reals.append(mi_r)
        perms.append(mi_p)
        print(f"  seed {s}: MI_reel={mi_r:.4f}  MI_perm={mi_p:.4f}  gain={mi_r-mi_p:+.4f}")

    results = {"reel": _stats(reals), "permute": _stats(perms)}
    v = verdict("reel", "permute", results)
    gains = np.array(reals) - np.array(perms)
    print("\n=== VERDICT (8 seeds) ===")
    print(f"  {v['summary']}")
    print(f"  gain moyen (reel - perm) = {gains.mean():+.4f} +/- {gains.std(ddof=1):.4f}")
    if v["significant"] and v["winner"] == "reel":
        print("  -> 047 CONFIRME sous puissance : le langage referentiel emerge vraiment sous demande.")
    else:
        print("  -> 047 NON confirme : l'effet ne se distingue pas du null a cette puissance (ne pas survendre).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
