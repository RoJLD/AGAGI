"""
tools/ablation_multi.py — Ablation MULTI-POINTS × MULTI-MÉTRIQUES (EDR 041, corrige EDR 039).

EDR 039 a montré que l'ablation à *un seul point* (crit plein) et *une seule métrique* (proies)
ment : la coopération sortait « neutre » car le crit la masquait (substituabilité). Ici on ablate
chaque mécanisme à DEUX points de fonctionnement (crit **plein** vs **sevré**) et on rapporte DEUX
métriques (proies_moy, mammouth). Un mécanisme dont le verdict **change** selon le point est
substituable/contextuel — l'outil le rend désormais VISIBLE au lieu de le cacher.

Usage : HEADLESS=1 python -m tools.ablation_multi
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger


def run_condition(config, db, apply_fn, crit_base, n_eras=4, num_agents=30, max_ticks=200):
    proies, mammo = [], []
    for _ in range(n_eras):
        env = Biosphere3D(config)
        env.config.target_prey_count = 12
        env.night_enabled = False
        env.explore_eps = 0.2
        env.craft_level = 0
        env.current_era = 1
        env.crit_base = crit_base               # POINT de fonctionnement : crit plein (0.6) ou sevré (0.0)
        apply_fn(env)
        genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = env.agents + env.dead_agents
        proies.append(np.mean([a.get("preys_eaten", 0) for a in pool]) if pool else 0.0)
        mammo.append(env.big_kills)
    return float(np.mean(proies)), float(np.mean(mammo))


MECHANISMS = {
    "cooperation":    lambda e: setattr(e, "coop_reward", False),     # la vedette (EDR 039)
    "nouveaute":      lambda e: setattr(e, "novelty_scale", 0.0),
    "curiosite":      lambda e: setattr(e, "curiosity_scale", 0.0),
    "scaffold_craft": lambda e: setattr(e, "scaffold_craft", 0.0),
    "seuils":         "MODULE_THRESHOLDS",
}
POINTS = [("crit_plein", 0.6), ("crit_sevre", 0.0)]


def main(n_eras=4):
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

    print("ABLATION MULTI-POINTS x MULTI-METRIQUES (delta proies / delta mammouth)")
    results = {}
    for pt_name, cb in POINTS:
        base_p, base_m = run_condition(config, db, lambda e: None, cb, n_eras)
        print(f"\n[{pt_name}] BASELINE: proies={base_p:.2f} mammouth={base_m:.2f}")
        for mech, fn in MECHANISMS.items():
            if fn == "MODULE_THRESHOLDS":
                MambaBatchModel.ABLATE_THRESHOLDS = True
                p, m = run_condition(config, db, lambda e: None, cb, n_eras)
                MambaBatchModel.ABLATE_THRESHOLDS = False
            else:
                p, m = run_condition(config, db, fn, cb, n_eras)
            results[(mech, pt_name)] = (p - base_p, m - base_m)
            print(f"  sans {mech:15s}: dproies={p-base_p:+.2f} dmammouth={m-base_m:+.2f}")

    print("\n=== VERDICT qui CHANGE selon le point (= mecanisme substituable/contextuel) ===")
    for mech in MECHANISMS:
        dp_plein = results[(mech, "crit_plein")][0]
        dp_sevre = results[(mech, "crit_sevre")][0]
        flip = (dp_plein < -0.10) != (dp_sevre < -0.10)
        tag = "  <-- CHANGE de verdict (contextuel !)" if flip else ""
        print(f"  {mech:15s}: dproies crit_plein={dp_plein:+.2f} | crit_sevre={dp_sevre:+.2f}{tag}")
    async_logger.stop()


if __name__ == "__main__":
    main()
