"""
tools/lang_speciation.py — Porter la spéciation au LANGAGE : par comportement (EDR 063).

EDR 058/060 : la spéciation PAR TAILLE protège l'innovation architecturale (NAS). On la porte au
langage PAR COMPORTEMENT (niche = token dominant près du Mammouth). Hypothèse à tester — et peut-être
contre-intuitive : le NAS a besoin d'EXPLORER (diversité protégée = bien), le langage a besoin de
CONVERGER (diversité protégée = peut-être MAL). A/B token-spéciation ON vs OFF, multi-seed : le taux
d'émergence (gain MI réel-permuté) monte-t-il, ou la protection de diversité EMPÊCHE-t-elle la
convergence ?

Usage : HEADLESS=1 python -m tools.lang_speciation
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
import src.seed_ai.persistence as persistence
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


def _world(config, db, num_agents=30):
    env = Biosphere3D(config)
    _setup_lewis(env)
    env.track_apex_token = True                     # peuple _apex_token (clé de niche)
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
        env = _world(config, db)
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


def run_seed(config, db, speciate, seed, eras=16, max_ticks=200):
    persistence.SPECIATE = speciate
    persistence.SPECIATE_MODE = "token"
    np.random.seed(seed)
    _restore()
    try:
        for _ in range(eras):
            env = _world(config, db)
            t = 0
            while env.agents and t < max_ticks:
                env.step()
                t += 1
            for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
            if hasattr(env, "memory_retriever"):
                env.memory_retriever.stop()
        g = _gain(config, db)
    finally:
        persistence.SPECIATE = False
        persistence.SPECIATE_MODE = "size"
    return g


def arm(config, db, speciate, seeds, eras, label):
    gains = []
    for s in seeds:
        g = run_seed(config, db, speciate, s, eras)
        gains.append(g)
        print(f"  [{label}] seed {s}: gain={g:+.4f}  {'EMERGE' if g > EMERGE else '.'}")
    rate = sum(1 for g in gains if g > EMERGE) / len(gains)
    return gains, rate


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
    print(f"SPECIATION LANGAGE (par token) : ON vs OFF. {len(seeds)} seeds x {eras} eres.")
    on_g, on_rate = arm(config, db, True, seeds, eras, "TOK")
    off_g, off_rate = arm(config, db, False, seeds, eras, "OFF")

    res = {"token_spec": _stats(on_g), "base": _stats(off_g)}
    v = verdict("token_spec", "base", res, t_thresh=2.0)
    print("\n=== VERDICT ===")
    print(f"  taux d'emergence : OFF={off_rate*100:.0f}%  vs  TOKEN-SPEC={on_rate*100:.0f}%")
    print(f"  {v['summary']}")
    if on_rate > off_rate + 0.25 or (v["significant"] and v["winner"] == "token_spec"):
        print("  -> la speciation par token AIDE la convergence (l'unification tient pour le langage).")
    elif on_rate < off_rate - 0.25 or (v["significant"] and v["winner"] == "base"):
        print("  -> la speciation par token NUIT : proteger la diversite EMPECHE la convergence.")
        print("     => NAS (explorer) et langage (converger) exigent des dynamiques OPPOSEES. Unification raffinee.")
    else:
        print("  -> pas d'effet net (regime faible/bruite, comme tout le langage).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
