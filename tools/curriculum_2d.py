"""
tools/curriculum_2d.py — Intégration 2D (Monde × Craft) — EDR 027, Vague 0quater.

Découverte EDR 026 : la chasse simple PLAFONNE à la rareté extrême (6 proies). Thèse du
projet : avec les OUTILS (craft + crit), la population doit franchir ce mur en basculant
vers le **gros gibier** (Mammouth = 105 d'énergie). Ici on rampe la rareté alimentaire *en
laissant le tooling disponible* (auto-craft L0 + coup critique + matériaux régénérés), et on
mesure si la chaîne moyens→fins émerge : crafts + tués de **gros gibier** + survie.

Monde hybride (découplage EDR 027) : proies & matériaux régénérés, MAIS nuit off (survivable)
et ε-greedy on (explorer le grab). On NE réinitialise PAS le HoF (chasseurs viables).

Usage : HEADLESS=1 python -m tools.curriculum_2d
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger


def run_2d_era(config, db, target_prey, craft_level=0, eps=0.2, crit_base=0.6,
               num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = target_prey   # axe Monde : rareté alimentaire
    env.night_enabled = False                    # survivable (jour permanent)
    env.explore_eps = eps                        # explorer grab/rub (ε découplé)
    env.craft_level = craft_level                # axe Craft : outils disponibles
    env.crit_base = crit_base                    # gros gibier survivable (scaffold annealé)
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
    mean_prey = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return crafts, env.big_kills, mean_prey, t


def main(levels=(20, 12, 6), max_eras=15, mastery=1.0, patience=2):
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

    summary = {}
    for tp in levels:
        print(f"\n=== 2D (Monde×Craft) — rareté proies = {tp} (outils dispo) ===")
        consec = 0
        mastered = False
        for e in range(max_eras):
            crafts, big, mp, t = run_2d_era(config, db, tp)
            consec = consec + 1 if mp >= mastery else 0
            tag = " <- MAITRISE" if consec >= patience else ""
            print(f"  proies={tp:2d} ere {e+1:2d}: proies_moy={mp:.2f} crafts={crafts:3d} "
                  f"mammouth={big:2d} duree={t:3d}{tag}")
            if consec >= patience:
                mastered = True
                break
        summary[tp] = "maitrise" if mastered else "NON (plafond)"
        print(f"  --> rareté {tp} : {summary[tp]}")

    print("\n=== BILAN 2D — la rareté force-t-elle l'outillage du gros gibier ? ===")
    for tp in levels:
        print(f"  rareté proies={tp:2d} : {summary[tp]}")
    async_logger.stop()


if __name__ == "__main__":
    main()
