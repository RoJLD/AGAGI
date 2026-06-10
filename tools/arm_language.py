"""
tools/arm_language.py — Arming DIRIGÉ du #8 sur la frontière LANGAGE (EDR 045).

EDR 042/043 : le langage référentiel n'émerge pas seul (MI≈0 ; seule la présence compte).
Le #8, armé en mode DIRIGÉ (l'intervention que le LLM proposerait, sans appel LLM externe), teste
si une **pression référentielle** (récompenser la convergence sur un token partagé près de l'apex)
fait émerger le sens. A/B : on fait ÉVOLUER la population sous la pression (puis sans), même HoF de
départ, et on mesure `I(token ; near_Mammouth)`. MI(pression) >> MI(sans) ≈ baseline -> frontière
franchissable par une intervention dirigée (et donc, demain, par le LLM au même seam).

Usage : HEADLESS=1 python -m tools.arm_language
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from src.graph_rag.reflexive_supervisor import compute_trend  # (dispo si besoin)
from tools.arc5_alignment import _mutual_info, _near_mammoth
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR
import os
import shutil


def _world(config, db, ref_scale, num_agents=30):
    env = Biosphere3D(config)
    env.config.target_prey_count = 12
    env.night_enabled = False
    env.explore_eps = 0.15
    env.craft_level = 0
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.referential_scale = ref_scale
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    return env


def evolve(config, db, ref_scale, eras, max_ticks=200):
    for _ in range(eras):
        env = _world(config, db, ref_scale)
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
        env = _world(config, db, 0.0)        # mesure pure : pression off, on lit les politiques évoluées
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                ls = ag.get("last_spoken", [0.0] * 4)
                tok = int(np.argmax(ls)) if any(abs(v) > 0.01 for v in ls) else 4
                toks.append(tok)
                ctxs.append(1 if _near_mammoth(env, ag) else 0)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    mi = _mutual_info(toks, ctxs)
    perm = np.array(ctxs)
    base = np.mean([_mutual_info(toks, np.random.permutation(perm).tolist()) for _ in range(5)])
    return mi, float(base)


def main(evolve_eras=20, ref_scale=0.5):
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
    print(f"ARMING LANGAGE (dirige) : evolue {evolve_eras} eres puis mesure MI(token; Mammouth).")

    evolve(config, db, ref_scale, evolve_eras)
    mi_ref, base_ref = measure_mi(config, db)
    print(f"  AVEC pression referentielle (scale={ref_scale}) : MI={mi_ref:.4f} | baseline={base_ref:.4f} | ratio={mi_ref/(base_ref+1e-6):.1f}x")

    _restore()
    evolve(config, db, 0.0, evolve_eras)
    mi_no, base_no = measure_mi(config, db)
    print(f"  SANS pression (controle)            : MI={mi_no:.4f} | baseline={base_no:.4f} | ratio={mi_no/(base_no+1e-6):.1f}x")

    print("\n=== VERDICT ===")
    print(f"  MI avec pression = {mi_ref:.4f} ; sans = {mi_no:.4f}")
    if mi_ref > 3 * max(mi_no, base_ref) and mi_ref > 0.01:
        print("  -> le langage REFERENTIEL emerge sous pression dirigee : frontiere FRANCHISSABLE.")
    else:
        print("  -> pas d'emergence nette : la pression dirigee ne suffit pas (frontiere tenace).")

    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
