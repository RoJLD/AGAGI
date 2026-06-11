"""
tools/powered_demand.py — Le classement des demandes (EDR 051), mais PUISSANT (EDR 052).

EDR 051 : la boucle #8 a classé 3 demandes par le BRUIT (1 run, 12 ères). On rejoue le classement à
travers le harnais d'évaluation puissant (multi-seeds) -> verdict AVEC confiance : un gagnant
significatif, ou « toujours du bruit » (= il faut encore plus de puissance). Les deux sont honnêtes.

Usage : HEADLESS=1 python -m tools.powered_demand
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import powered_eval, rank, is_robust_winner
from tools.arm_world_demand import _world, _measure_mi
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR

DEMANDS = {
    "lewis_2ref": {"lewis": True},
    "referential_pressure": {"lewis": True, "referential_scale": 0.5},
    "speaker_reciprocity": {"lewis": True, "speaker_reward": 5.0},
}


def make_run_seed_fn(config, db, eras=18, max_ticks=200):
    def run_seed(params, seed):
        np.random.seed(seed)            # réplicat indépendant (denoising)
        _restore()                      # même HoF de départ pour CHAQUE (demande, seed)
        for _ in range(eras):
            env = _world(config, db, params)
            t = 0
            while env.agents and t < max_ticks:
                env.step()
                t += 1
            for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
        return _measure_mi(config, db, params)
    return run_seed


def main(seeds=(0, 1, 2)):
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
    print(f"CLASSEMENT PUISSANT des demandes : {len(seeds)} seeds x 18 eres (harnais EDR 052).")
    run_seed = make_run_seed_fn(config, db)
    results = powered_eval(DEMANDS, run_seed, seeds=seeds)

    print("\n=== RESULTATS (moyenne +/- ecart-type sur seeds) ===")
    for name, mean, std in rank(results):
        print(f"  {name:20s} : MI = {mean:.4f} +/- {std:.4f}  (vals={['%.4f'%v for v in results[name]['vals']]})")

    winner, v = is_robust_winner(results)
    print("\n=== VERDICT ===")
    if v is not None:
        print(f"  {v['summary']}")
    if winner:
        print(f"  -> gagnant ROBUSTE : '{winner}'. La mesure puissante TRANCHE (vs le bruit de l'EDR 051).")
        if winner == "lewis_2ref":
            print("  -> et c'est bien la demande referentielle reelle (EDR 047). Methode validee.")
    else:
        print("  -> AUCUN gagnant robuste : meme a cette puissance, les demandes ne se separent pas")
        print("     (population derivee / besoin de plus de seeds+eres). Verdict honnete : ne pas conclure.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
