"""
tools/curriculum_world.py — Curriculum développemental sur l'AXE MONDE (EDR 026).

Étape 5 de la Vague 0ter, symétrique de l'axe Craft (EDR 025) : ramper la *difficulté du
monde* par paliers, chacun franchi quand le précédent est MAÎTRISÉ (mastery gate). La
difficulté la plus contraignante (EDR 021) est la **rareté alimentaire** : on rampe la
capacité de charge en proies (abondant → rare). La sélection (HoF) adapte la population à
chaque cran ; on avance quand elle se nourrit (`proies_moy ≥ mastery`).

On NE réinitialise PAS le HoF : on part de chasseurs viables (une population random meurt
en ~2 ticks — logits explosés). Le monde tourne en mode normal (nuit, danger, régén).

Usage : HEADLESS=1 python -m tools.curriculum_world
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger


def run_world_era(config, db, target_prey, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    env.config.target_prey_count = target_prey   # difficulté = rareté alimentaire (capacité de charge)
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
        save_to_hall_of_fame(cand)           # sélection : les meilleurs chasseurs persistent
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    mean_prey = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return mean_prey, t


def main(levels=(30, 20, 12, 6), max_eras=15, mastery=1.0, patience=2):
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
        print(f"\n=== AXE MONDE — DIFFICULTE (capacite proies = {tp}) ===")
        consec = 0
        mastered = False
        for e in range(max_eras):
            mp, t = run_world_era(config, db, tp)
            consec = consec + 1 if mp >= mastery else 0
            tag = " <- MAITRISE" if consec >= patience else ""
            print(f"  proies={tp:2d} ere {e+1:2d}: proies_moy={mp:.2f} duree={t:3d} consec={consec}{tag}")
            if consec >= patience:
                mastered = True
                break
        summary[tp] = "maitrise" if mastered else "NON maitrise (plafond)"
        print(f"  --> capacite {tp} : {summary[tp]}")

    print("\n=== BILAN AXE MONDE ===")
    for tp in levels:
        print(f"  capacite proies={tp:2d} : {summary[tp]}")
    async_logger.stop()


if __name__ == "__main__":
    main()
