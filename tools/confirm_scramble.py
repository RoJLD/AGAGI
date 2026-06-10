"""
tools/confirm_scramble.py — Test de BROUILLAGE : présence vs contenu (EDR 043, ferme EDR 042).

EDR 042 : la portée aide la chasse, mais le token ne porte pas d'info (MI≈0) -> hypothèse :
le bénéfice vient de la PRÉSENCE (entendre un voisin), pas du SENS du token. Arbitre : on
brouille le contenu du token (token aléatoire) en gardant la présence. Trois lignées, même HoF
de départ :
  - radius 0          : pas de portée (référence).
  - radius 3 réel     : portée + token du connectome.
  - radius 3 brouillé : portée + token ALÉATOIRE (présence préservée, sens détruit).

Si réel ≈ brouillé ≫ radius 0 -> c'est la PRÉSENCE qui porte le bénéfice (EDR 042 confirmé).
Si réel > brouillé -> le contenu du token comptait (référentiel partiel).

Usage : HEADLESS=1 python -m tools.confirm_scramble
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR
import os
import shutil


def run_era(config, db, hear_radius, scramble, num_agents=30, max_ticks=200):
    env = Biosphere3D(config)
    env.config.target_prey_count = 12
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = hear_radius
    env.scramble_signal = scramble
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
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
    mp = float(np.mean([a.get("preys_eaten", 0) for a in pool])) if pool else 0.0
    return env.big_kills, mp


def main(eras=16):
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
    conditions = [("radius0", 0, False), ("radius3_reel", 3, False), ("radius3_brouille", 3, True)]
    half = eras // 2
    print(f"TEST DE BROUILLAGE (meme HoF de depart, {eras} eres/lignee) :")
    res = {}
    for label, r, s in conditions:
        _restore()
        mammo = []
        for _ in range(eras):
            b, _mp = run_era(config, db, r, s)
            mammo.append(b)
        res[label] = float(np.mean(mammo[half:]))
        print(f"  {label:18s}: mammouth_moy(2e moitie)={res[label]:.2f}")

    print("\n=== VERDICT ===")
    gain_reel = res["radius3_reel"] - res["radius0"]
    gain_brou = res["radius3_brouille"] - res["radius0"]
    print(f"  gain portee REEL     = {gain_reel:+.2f}")
    print(f"  gain portee BROUILLE = {gain_brou:+.2f}")
    if gain_brou > 0.5 * max(gain_reel, 1e-6):
        print("  -> brouille garde le gain => c'est la PRESENCE, pas le contenu (EDR 042 confirme).")
    else:
        print("  -> brouille perd le gain => le CONTENU du token comptait (referentiel partiel).")

    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
