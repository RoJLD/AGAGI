"""
tools/arm_world_demand.py — La boucle #8 sur les DEMANDES de monde (EDR 051).

EDR 050 : 4 designs manuels, 3+ échecs — concevoir la bonne demande est une RECHERCHE. Le #8, étendu
au périmètre `world_demand` (rsi_loop.WorldDemandProposer), itère et CLASSE les demandes par la
mesure. Ici, en mode DIRIGÉ (catalogue des demandes 047/045/050, pas de LLM live), on démontre que la
boucle **re-découvre** le bon levier : `lewis_2ref` (demande référentielle réelle) bat la pression
scriptée (045) et la réciprocité (050). Le LLMProposer s'y substituerait pour en INVENTER de nouvelles.

Usage : HEADLESS=1 python -m tools.arm_world_demand
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from src.metaprog.rsi_loop import WorldDemandProposer, rsi_demand_step
from tools.lewis_world import _setup_lewis, _apex_ctx
from tools.arc5_alignment import _mutual_info
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _apply_demand(env, params):
    _setup_lewis(env)                                   # toutes les demandes partent du monde de Lewis
    # Jeu complet de params SÛRS (allow-list rsi_loop.ALLOWED_DEMAND_PARAMS, déjà sanitisés).
    for attr in ("referential_scale", "speaker_reward", "align_selection"):
        if attr in params:
            setattr(env, attr, float(params[attr]))
    if "transient_apex" in params:
        env.transient_apex = bool(params["transient_apex"])


def _world(config, db, params):
    env = Biosphere3D(config)
    _apply_demand(env, params)
    genomes, _ = init_primordial_soup(num_agents=30, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def _measure_mi(config, db, params, eras=4, max_ticks=200):
    toks, ctxs = [], []
    for _ in range(eras):
        env = _world(config, db, {})        # mesure pure (demande off pendant la mesure)
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
    return _mutual_info(toks, ctxs)


def make_measure_fn(config, db, eras=12):
    """Le SEAM de mesure injecté dans rsi_demand_step : restaure le départ commun, évolue SOUS la
    demande, mesure MI. Score = MI - baseline (>0 si la demande crée du référentiel)."""
    def measure(proposal):
        _restore()                                      # même HoF de départ pour chaque demande
        for _ in range(eras):
            env = _world(config, db, proposal.params)
            t = 0
            while env.agents and t < 200:
                env.step()
                t += 1
            for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
        mi = _measure_mi(config, db, proposal.params)
        return float(mi), f"MI={mi:.4f}"
    return measure


def main():
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

    _backup()                                           # départ commun (sauvegardé une fois)
    measure_fn = make_measure_fn(config, db)
    proposer = WorldDemandProposer()
    print("BOUCLE #8 / world_demand (dirige) : propose + mesure + classe les demandes.")
    results = []
    for _ in range(len(WorldDemandProposer.CATALOG)):
        proposal, score, detail = rsi_demand_step({}, measure_fn, proposer=proposer)
        print(f"  demande '{proposal.name:20s}' -> {detail}   ({proposal.rationale})")
        results.append((proposal.name, score))

    results.sort(key=lambda r: r[1], reverse=True)
    best = results[0]
    print("\n=== CLASSEMENT (par MI mesuré) ===")
    for name, score in results:
        print(f"  {name:20s} : {score:.4f}")
    print(f"\n  -> la boucle retient '{best[0]}' (MI={best[1]:.4f}).")
    if best[0] == "lewis_2ref":
        print("  -> elle RE-DECOUVRE le bon levier (EDR 047) en mesurant, pas en supposant. #8 valide.")
    else:
        print("  -> classement different (bruit/derive) ; la METHODE (mesurer+classer) tient.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
