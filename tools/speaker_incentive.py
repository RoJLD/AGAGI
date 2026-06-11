"""
tools/speaker_incentive.py — Vaincre le silence : incitation du locuteur (EDR 050).

EDR 048 : le langage référentiel émerge (047) mais reste FAIBLE car le SILENCE domine — parler ne
profite qu'à l'auditeur (altruisme du signal). Remède classique : la RÉCIPROCITÉ. `world.speaker_reward`
prime un agent qui a annoncé (signalé adjacent) un Mammouth EFFECTIVEMENT tué par le pack -> annoncer
une vraie opportunité paie pour le PARLEUR. A/B (ON vs OFF, même départ, monde de Lewis 2 référents) :
le silence près de l'apex baisse-t-il ? MI(token;Mammouth/Leurre) monte-t-il ?

Usage : HEADLESS=1 python -m tools.speaker_incentive
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
from tools.lewis_world import _setup_lewis, _apex_ctx
from tools.arc5_alignment import _mutual_info
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _world(config, db, speaker_reward, num_agents=30):
    env = Biosphere3D(config)
    _setup_lewis(env)
    env.speaker_reward = speaker_reward
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def evolve(config, db, speaker_reward, eras, max_ticks=200):
    for _ in range(eras):
        env = _world(config, db, speaker_reward)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
            save_to_hall_of_fame(cand)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()


def measure(config, db, eras=6, max_ticks=200):
    toks, ctxs, silent, total = [], [], 0, 0
    for _ in range(eras):
        env = _world(config, db, 0.0)        # mesure : prime off, on lit les politiques évoluées
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                c = _apex_ctx(env, ag)
                if c == 0:
                    continue
                ls = ag.get("last_spoken", [0.0] * 4)
                spoke = any(abs(v) > 0.01 for v in ls)
                total += 1
                if not spoke:
                    silent += 1
                toks.append(int(np.argmax(ls)) if spoke else 4)
                ctxs.append(1 if c == 1 else 0)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    if total == 0:
        return 0.0, 0.0, 1.0
    mi = _mutual_info(toks, ctxs)
    base = float(np.mean([_mutual_info(toks, np.random.permutation(np.array(ctxs)).tolist()) for _ in range(5)]))
    return mi, base, silent / total


def main(evolve_eras=24, reward=5.0):
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
    print(f"INCITATION LOCUTEUR : {evolve_eras} eres, A/B reciprocite ON({reward}) vs OFF.")
    evolve(config, db, reward, evolve_eras)
    mi_on, base_on, sil_on = measure(config, db)
    print(f"  ON  : silence(pres apex)={sil_on*100:.0f}% | MI={mi_on:.4f} | baseline={base_on:.4f}")

    _restore()
    evolve(config, db, 0.0, evolve_eras)
    mi_off, base_off, sil_off = measure(config, db)
    print(f"  OFF : silence(pres apex)={sil_off*100:.0f}% | MI={mi_off:.4f} | baseline={base_off:.4f}")

    print("\n=== VERDICT ===")
    less_silent = sil_on < sil_off - 0.05
    more_ref = mi_on > 1.5 * max(mi_off, base_on) and mi_on > 0.02
    print(f"  moins de silence ? {'OUI' if less_silent else 'NON'} ({sil_off*100:.0f}%->{sil_on*100:.0f}%)")
    print(f"  plus referentiel ? {'OUI' if more_ref else 'NON'} (MI {mi_off:.4f}->{mi_on:.4f})")
    if less_silent and more_ref:
        print("  -> la reciprocite vainc le silence ET renforce le langage (EDR 048 resolu).")
    elif less_silent:
        print("  -> moins de silence mais pas plus referentiel (parle, sans encoder le sens).")
    else:
        print("  -> la reciprocite ne suffit pas (silence tenace / autre goulot).")

    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
