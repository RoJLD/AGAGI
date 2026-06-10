"""
tools/curriculum_developmental.py — Curriculum développemental 2D de RÉFÉRENCE (EDR 030).

Unifie le programme de la Vague 0 : à mesure que la population mûrit (ère globale), le monde
**durcit** (rareté ↓, axe Monde) ET les **scaffolds se sèvrent** ensemble (coup critique →0,
prime de groupe pleine→partagée). Tooling disponible (auto-craft L0 + matériaux). On vérifie que
la chaîne moyens→fins (collecter → crafter → chasse coopérative de l'apex) reste **dominante et
robuste** une fois les béquilles retirées.

Remplace les drivers expérimentaux (grab/craft/world/2d/persistence) par un programme unique,
piloté par l'ère globale (corrige le bug « chaque ère = ère 1 » → les scaffolds s'annèlent vraiment).

Usage : HEADLESS=1 python -m tools.curriculum_developmental
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.environments.stone_economy import crit_chance, anneal
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger


def run_era(config, db, global_era, rarity, crit_eras, group_eras, crit_base=0.6,
            eps=0.2, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = rarity     # axe Monde (durcit avec l'ère)
    env.night_enabled = False
    env.explore_eps = eps
    env.craft_level = 0                        # axe Craft : outils dispo (auto-craft)
    env.crit_base = crit_base
    env.crit_eras = crit_eras                  # sevrage du crit
    env.group_reward_eras = group_eras         # sevrage de la prime de groupe
    env.current_era = global_era               # pilote TOUS les sevrages/scaffolds
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=energy)
    env.current_era = global_era
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
    mean_prey = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return crafts, env.big_kills, mean_prey, t


def main(eras=30, wean_eras=20):
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

    print("CURRICULUM DEVELOPPEMENTAL : le monde durcit ET les scaffolds se sevrent ensemble.")
    weaned = []
    for e in range(eras):
        rarity = max(10, 16 - e // 4)                  # 16 -> 10 (durcit avec la maturité)
        crit = crit_chance(0.6, e, wean_eras)
        grp = anneal(e, wean_eras)
        crafts, big, mp, t = run_era(config, db, e, rarity, wean_eras, wean_eras)
        phase = "scaffold" if (crit > 0 or grp > 0) else "SEVRE"
        print(f"  ere {e:2d} [{phase:8s} rarete={rarity:2d} crit={crit:.2f} prime={grp:.2f}]: "
              f"crafts={crafts:3d} mammouth={big:2d} proies_moy={mp:.2f} duree={t:3d}")
        if crit == 0 and grp == 0:
            weaned.append((big, mp))

    print("\n=== BILAN — la chaîne tient-elle SANS béquille (crit=0, prime partagée) ? ===")
    if weaned:
        mb = np.mean([w[0] for w in weaned])
        mp = np.mean([w[1] for w in weaned])
        print(f"  phase SEVRÉE : mammouth/ère={mb:.2f}  proies_moy={mp:.2f}  "
              f"-> {'DOMINANTE & ROBUSTE' if mp >= 1.0 and mb >= 0.5 else 'robuste mais bornée'}")
    async_logger.stop()


if __name__ == "__main__":
    main()
