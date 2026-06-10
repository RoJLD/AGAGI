"""
tools/probe_impasse.py — Sondeur d'IMPASSE (EDR 037, Vague 3 / pré-#8).

Méthodologie : au lieu de scripter l'émergence avancée, on lance une évolution LONGUE sur la
chaîne sociale robuste (coopération, EDR 028) à une rareté survivable, on **active le canal de
langage latent** (non-scripté) et on **mesure où ça plafonne**. On réutilise notre propre
`compute_trend` (superviseur réflexif EDR 036) pour détecter le plateau = l'impasse, qui est —
par décision utilisateur — le déclencheur du #8 (vraie RSI).

Sortie : trajectoire (mammouth/proies/crafts par ère) + verdict de tendance sur la 2e moitié.

Usage : HEADLESS=1 python -m tools.probe_impasse
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.reflexive_supervisor import compute_trend
from src.graph_rag.async_logger import logger as async_logger


def run_era(config, db, target_prey=12, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = target_prey
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"   # canal de langage latent ACTIVÉ (non-scripté)
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=energy)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = env.agents + env.dead_agents
    for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
        save_to_hall_of_fame(cand)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    crafts = sum(a.get("spears_crafted", 0) for a in pool)
    # signal : combien d'agents émettent un signal non trivial (proxy d'usage du langage).
    speakers = sum(1 for a in pool if a.get("last_spoken") and any(abs(v) > 0.01 for v in a["last_spoken"]))
    mp = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return crafts, env.big_kills, mp, speakers, len(pool)


def main(eras=40, target_prey=12):
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

    print(f"SONDEUR D'IMPASSE : {eras} eres, rarete {target_prey}, LANGUAGE on.")
    mammo, proies, crafts_s = [], [], []
    for e in range(eras):
        c, b, mp, spk, n = run_era(config, db, target_prey)
        mammo.append(b); proies.append(mp); crafts_s.append(c)
        print(f"  ere {e:2d}: mammouth={b:2d} proies_moy={mp:.2f} crafts={c:3d} parleurs={spk:2d}/{n}")

    # Verdict : tendance sur la 2e moitié (régime « mûr »), via notre propre compute_trend.
    half = eras // 2
    print("\n=== VERDICT D'IMPASSE (tendance 2e moitie, compute_trend EDR 036) ===")
    for name, series in (("mammouth", mammo), ("proies_moy", proies), ("crafts", crafts_s)):
        tr = compute_trend(series[half:])
        print(f"  {name:11s}: direction={tr['direction']:9s} pente={tr['slope']:+.4f} "
              f"moy={tr['mean']:.2f}")
    print("\n  -> plateau partout = IMPASSE (declencheur du #8). Amelioration = continuer.")
    async_logger.stop()


if __name__ == "__main__":
    main()
