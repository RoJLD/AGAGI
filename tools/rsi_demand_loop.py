"""
tools/rsi_demand_loop.py — La boucle #8 COMPLÈTE : propose -> mesure PUISSANTE -> enregistre -> itère.

Réunit tout (EDR 044/051/052/059/061) : un Proposer (catalogue dirigé, ou LLM injecté), une mesure
MULTI-SEED via le harnais (plus de classement-du-bruit, EDR 051), l'enregistrement à l'ontologie, et
un `context` qui ACCUMULE les résultats passés (que le LLM lira pour ne pas se répéter).

ARMER = remplacer `WorldDemandProposer()` par `LLMProposer(llm_fn=<appel LLM en CONTENEUR JETABLE>)`.
Une seule ligne. Tout le reste (mesure puissante incluse) est déjà branché.

Usage : HEADLESS=1 python -m tools.rsi_demand_loop   (long : multi-seed par demande)
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.metaprog.rsi_loop import WorldDemandProposer, make_powered_measure, rsi_demand_step
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from tools.arm_world_demand import _world, _measure_mi
from tools.lewis_world import _apex_ctx
from tools.arc5_alignment import _mutual_info
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def make_run_seed(config, db, eras=16, max_ticks=200):
    """run_seed(params, seed) -> gain MI (réel - permuté) d'UN réplicat, sous la demande `params`."""
    def run_seed(params, seed):
        np.random.seed(seed)
        _restore()                                  # même départ pour chaque (demande, seed)
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
        # mesure : gain référentiel réel vs permuté (null)
        toks, ctxs = [], []
        for _ in range(4):
            env = _world(config, db, {})
            t = 0
            while env.agents and t < max_ticks:
                env.step()
                t += 1
                for ag in env.agents:
                    c = _apex_ctx(env, ag)
                    if c == 0:
                        continue
                    toks.append(int(np.argmax(ag.get("last_spoken", [0.0] * 4)))
                                if any(abs(v) > 0.01 for v in ag.get("last_spoken", [0.0] * 4)) else 4)
                    ctxs.append(1 if c == 1 else 0)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
        if not toks:
            return 0.0
        mi = _mutual_info(toks, ctxs)
        perm = float(np.mean([_mutual_info(toks, np.random.permutation(np.array(ctxs)).tolist()) for _ in range(5)]))
        return mi - perm
    return run_seed


def main(seeds=(0, 1, 2), proposer=None, n_iters=None):
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
    run_seed = make_run_seed(config, db)
    powered = make_powered_measure(run_seed, seeds=seeds)        # <-- mesure PUISSANTE (harnais)
    if proposer is None:
        proposer = WorldDemandProposer()                        # défaut : catalogue dirigé
    if n_iters is None:
        n_iters = len(WorldDemandProposer.CATALOG)
    label = type(proposer).__name__
    context = {"trend": {"direction": "?"}, "recent": []}        # accumulé pour le générateur (LLM)

    print(f"BOUCLE #8 COMPLETE ({label}, mesure puissante, {len(seeds)} seeds/demande, {n_iters} iters).")
    results = []
    for _ in range(n_iters):
        proposal, score, detail = rsi_demand_step(context, powered, proposer=proposer)
        print(f"  '{proposal.name:20s}' -> {detail}")
        context["recent"].append({"name": proposal.name, "params": proposal.params, "score": round(score, 4)})
        results.append((proposal.name, score))

    results.sort(key=lambda r: r[1], reverse=True)
    print("\n=== CLASSEMENT (gain moyen multi-seed) ===")
    for name, score in results:
        print(f"  {name:20s} : {score:+.4f}")
    print(f"\n  -> meilleure demande : '{results[0][0]}'. Mesure PUISSANTE -> plus de classement du bruit (EDR 051).")
    if "LLM" in label:
        print(f"  -> #8 ARME ({label}) : le generateur a propose+mesure+itere. Live.")
    else:
        print("  -> ARMER : passer LLMProposer(llm_fn=local_llm_fn()) en argument. Tout est branche.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
