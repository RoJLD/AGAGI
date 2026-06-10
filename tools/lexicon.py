"""
tools/lexicon.py — Renforcer le langage : multi-référents + lexique (EDR 048, suite de 047).

EDR 047 : le langage référentiel émerge sous demande (MI 0→0.033, 2 référents, 24 ères). On
renforce : 3 référents (Mammouth=appel, Ours=appel récompensé distinct, Leurre=danger), plus d'ères,
et on mesure le LEXIQUE — pour chaque référent, le token dominant et sa pureté. Un vrai lexique =
des tokens distincts par (affordance de) référent.

Usage : HEADLESS=1 python -m tools.lexicon
"""
import time
from collections import Counter, defaultdict

import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.arc5_alignment import _mutual_info

REFERENTS = ["Mammouth", "Ours", "Leurre"]


def _setup(env):
    env.config.target_prey_count = 4
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    env.config.preys["Ours"] = PreyConfig(hp=60.0, damage=30.0, moves_per_tick=0.3)
    for _ in range(4):
        for ref in REFERENTS:
            env._spawn_prey_instance(ref)


def _adjacent_ref(env, ag, r=1):
    for p in env.preys:
        cfg = env.config.preys.get(p["type"])
        if cfg and cfg.hp >= 50 and abs(ag["x"] - p["x"]) + abs(ag["y"] - p["y"]) <= r:
            return p["type"] if p["type"] in REFERENTS else None
    return None


def _world(config, db, num_agents=30):
    env = Biosphere3D(config)
    _setup(env)
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def evolve(config, db, eras, max_ticks=200):
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


def measure(config, db, eras=6, max_ticks=200):
    pairs = []   # (token, referent)
    for _ in range(eras):
        env = _world(config, db)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                ref = _adjacent_ref(env, ag)
                if ref is None:
                    continue
                ls = ag.get("last_spoken", [0.0] * 4)
                tok = int(np.argmax(ls)) if any(abs(v) > 0.01 for v in ls) else 4
                pairs.append((tok, ref))
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    return pairs


def report(pairs, label):
    if not pairs:
        print(f"  [{label}] aucune donnee")
        return
    toks = [p[0] for p in pairs]
    refs = [REFERENTS.index(p[1]) for p in pairs]
    mi = _mutual_info(toks, refs)
    base = float(np.mean([_mutual_info(toks, np.random.permutation(refs).tolist()) for _ in range(5)]))
    print(f"  [{label}] MI(token;referent /3)={mi:.4f} | baseline={base:.4f} | n={len(pairs)}")
    # Lexique : token dominant par referent + purete.
    by_ref = defaultdict(list)
    for tok, ref in pairs:
        by_ref[ref].append(tok)
    for ref in REFERENTS:
        c = Counter(by_ref[ref])
        if not c:
            continue
        top, cnt = c.most_common(1)[0]
        tot = sum(c.values())
        name = {4: "silence"}.get(top, f"tok{top}")
        print(f"    {ref:9s} -> {name:8s} ({100*cnt/tot:.0f}% sur {tot})")


def main(evolve_eras=36):
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
    print(f"LEXIQUE : 3 referents, evolue {evolve_eras} eres, mesure le lexique emergent.")
    report(measure(config, db), "AVANT")
    evolve(config, db, evolve_eras)
    report(measure(config, db), "APRES")
    print("\n  -> tokens DISTINCTS par referent = lexique ; MI/3 en hausse = langage plus riche.")
    async_logger.stop()


if __name__ == "__main__":
    main()
