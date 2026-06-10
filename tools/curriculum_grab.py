"""
tools/curriculum_grab.py — Curriculum de collecte (EDR 017).

Le diagnostic a montré que `rub` est facile une fois rock+stick en main ; le mur
est la COLLECTE (grab rocher + naviguer + grab stick + garder les deux). Ce
curriculum enseigne la collecte en isolation, puis transfère vers le monde dur.

Phase 1 (grab) : monde SÛR (pas de nuit, pas de proie/danger), inondé de rock+stick,
collecte/craft fortement récompensés -> les agents apprennent à collecter et crafter,
les meilleurs (life_score dominé par le craft) sont sauvés au HoF.
Phase 2 (normal) : monde dur, charge le HoF grab-entraîné -> le craft se transfère-t-il ?

Usage : HEADLESS=1 python -m tools.curriculum_grab
"""
import os
import time
import shutil

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger


def _setup_grab_training(env, eps=0.3, n_items=50, keep_prey=False):
    """Monde d'entraînement. n_items décroît au fil du ramp (généralisation à la rareté,
    EDR 021) ; keep_prey rapproche les observations du monde dur en fin de ramp."""
    env.training_mode = "grab"
    env.explore_eps = eps        # ε-greedy annelé : explorer le geste grab (EDR 019)
    env.scaffold_grab = 8.0      # forte prime de collecte d'ingrédient
    env.novelty_scale = 6.0      # forte prime de nouveauté (rock+stick = rare)
    if not keep_prey:
        env.preys = []           # tôt : pas de proie (collecte pure, sûr)
    for _ in range(n_items):
        env._spawn_rocks()       # rochers (tranchant)
    for _ in range(n_items):     # sticks (manche)
        x, y = np.random.randint(0, env.size), np.random.randint(0, env.size)
        env.items.append({"x": int(x), "y": int(y), "z": 0, "type": "stick", "weight": 1.0})


def run_one_era(config, db, training, eps=0.3, n_items=50, keep_prey=False,
                craft_level=0, num_agents=30, max_ticks=200, energy=80.0):
    env = Biosphere3D(config)
    if training:
        _setup_grab_training(env, eps, n_items, keep_prey)
    env.craft_level = craft_level   # axe Craft (EDR 018/025) : L0 auto -> L1 rub -> L2 position
    genomes, ntm = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        if ntm is not None:
            a.ntm_memory = ntm.copy()
        env.add_agent(a, energy=energy)
    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1
    pool = env.agents + env.dead_agents
    # SAUVEGARDE HoF (le fix EDR 016) : les meilleurs persistent -> transfert.
    for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
        save_to_hall_of_fame(cand)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    crafts = sum(a.get("spears_crafted", 0) for a in pool)
    survivors = len(env.agents)
    return crafts, t, survivors


def main(grab_eras=30, normal_eras=12, eps0=0.35):
    # HoF vierge pour un transfert propre (backup).
    if os.path.exists("data/hall_of_fame.pkl"):
        shutil.copy("data/hall_of_fame.pkl", "data/hall_of_fame.pkl.bak_pre_curriculum")
        os.remove("data/hall_of_fame.pkl")
    shutil.rmtree("data/agent_states/hall_of_fame", ignore_errors=True)

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

    print("=== PHASE 1 : GRAB-TRAINING (monde sûr, riche en rock+stick) ===")
    grab_crafts = 0
    for e in range(grab_eras):
        eps = eps0 * (1.0 - e / grab_eras)     # ε annelé : 0.35 -> ~0
        # Entraînement item-riche (encodage fort) ; le monde NORMAL (phase 2) fournit
        # désormais assez de matériaux (régén EDR 021) pour que le geste appris paie.
        c, t, s = run_one_era(config, db, training=True, eps=eps, n_items=50)
        grab_crafts += c
        print(f"  grab ere {e+1:2d}: eps={eps:.2f} crafts={c:3d} ticks={t:3d}")
    print(f"  --> total lances craftees en entrainement : {grab_crafts}")

    print(f"=== PHASE 2 : MONDE NORMAL (HoF grab-entraine) ===")
    normal_crafts = 0
    for e in range(normal_eras):
        c, t, s = run_one_era(config, db, training=False)
        normal_crafts += c
        print(f"  normal ere {e+1:2d}: crafts={c:3d} ticks={t:3d}")
    print(f"  --> total lances craftees en monde normal : {normal_crafts}")
    print(f"\nTRANSFERT : grab={grab_crafts} -> normal={normal_crafts}  "
          f"(le craft se transfere-t-il au monde dur ?)")

    async_logger.stop()


if __name__ == "__main__":
    main()
