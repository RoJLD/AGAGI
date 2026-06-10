"""
tools/lewis_world.py — Monde de Lewis : la DEMANDE fait-elle émerger le langage ? (EDR 047)

EDR 046 : on ne fait pas émerger une capacité en l'ajoutant ; il faut que le MONDE l'exige. Test :
un monde où deux gros gibiers sont indistinguables à distance — **Mammouth** (récompense, appeler le
pack) et **Leurre** (piège : dangereux, zéro récompense). Un agent ADJACENT perçoit le type ; les
agents distants ne voient que « gros gibier, direction X » → ils ONT BESOIN du token pour décider
(approcher le Mammouth / éviter le Leurre). Un token constant ne distingue pas -> aucun bénéfice :
SEUL un token référentiel paie. On évolue SOUS cette demande (sans pression scriptée) et on mesure
`I(token ; type_apex)` chez les agents adjacents. MI ≫ baseline -> le langage émerge SOUS DEMANDE.

Usage : HEADLESS=1 python -m tools.lewis_world
"""
import time

import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.arc5_alignment import _mutual_info


def _setup_lewis(env, n_each=5):
    env.config.target_prey_count = 4
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)  # piège
    for _ in range(n_each):
        env._spawn_prey_instance("Mammouth")
        env._spawn_prey_instance("Leurre")


def _apex_ctx(env, ag, r=1):
    for p in env.preys:
        cfg = env.config.preys.get(p["type"])
        if cfg and cfg.hp >= 50 and abs(ag["x"] - p["x"]) + abs(ag["y"] - p["y"]) <= r:
            return 1 if p["type"] == "Mammouth" else (-1 if p["type"] == "Leurre" else 0)
    return 0


def _world(config, db, num_agents=30):
    env = Biosphere3D(config)
    _setup_lewis(env)
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


def measure_mi(config, db, eras=6, max_ticks=200):
    toks, ctxs = [], []
    for _ in range(eras):
        env = _world(config, db)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                c = _apex_ctx(env, ag)
                if c == 0:
                    continue                       # on ne mesure QUE près d'un gros gibier
                ls = ag.get("last_spoken", [0.0] * 4)
                tok = int(np.argmax(ls)) if any(abs(v) > 0.01 for v in ls) else 4
                toks.append(tok)
                ctxs.append(1 if c == 1 else 0)    # 1=Mammouth, 0=Leurre
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    if not toks:
        return 0.0, 0.0, 0
    mi = _mutual_info(toks, ctxs)
    perm = np.array(ctxs)
    base = float(np.mean([_mutual_info(toks, np.random.permutation(perm).tolist()) for _ in range(5)]))
    return mi, base, len(toks)


def main(evolve_eras=24):
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

    print(f"MONDE DE LEWIS : evolue {evolve_eras} eres SOUS DEMANDE, puis mesure MI(token ; Mammouth/Leurre).")
    mi0, base0, n0 = measure_mi(config, db)
    print(f"  AVANT evolution : MI={mi0:.4f} | baseline={base0:.4f} | n={n0}")
    evolve(config, db, evolve_eras)
    mi1, base1, n1 = measure_mi(config, db)
    print(f"  APRES evolution : MI={mi1:.4f} | baseline={base1:.4f} | n={n1}")

    print("\n=== VERDICT ===")
    if mi1 > 0.03 and mi1 > 3 * max(base1, mi0):
        print("  -> le langage REFERENTIEL emerge SOUS DEMANDE : la these EDR 046 est CONFIRMEE.")
    else:
        print("  -> pas d'emergence nette meme sous demande (frontiere plus profonde, ou demande encore insuffisante).")
    async_logger.stop()


if __name__ == "__main__":
    main()
