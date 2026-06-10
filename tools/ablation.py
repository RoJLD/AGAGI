"""
tools/ablation.py — Ablation systématique + ontologie scientifique (EDR 032, Vague 1).

Commandement 15 retourné sur le projet lui-même : on désactive UN mécanisme à la fois et on
mesure le delta de survie (proies_moy) vs baseline -> quels leviers comptent VRAIMENT, maintenant
que la chaîne s'exprime. Chaque mécanisme = une `Hypothesis` (« X contribue »), chaque run = un
`Fact` (SUPPORTS si l'ablation fait mal, REFUTES sinon) écrit dans KuzuDB (ontologie branchée).

Monde fixe & survivable (rareté 12, ère 1 = scaffolds pleins) ; HoF non muté (mesure pure, même
population de départ pour toutes les conditions). MambaBatchModel.ABLATE_* pour les gènes câblés.

Usage : HEADLESS=1 python -m tools.ablation
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger
from src.graph_rag.experiment_tracker import ExperimentGraph


def _setup(env):
    env.config.target_prey_count = 12
    env.night_enabled = False
    env.explore_eps = 0.2
    env.craft_level = 0
    env.current_era = 1            # scaffolds + crit à plein régime (pour mesurer leur ablation)


def run_condition(config, db, apply_fn, n_eras=5, num_agents=30, max_ticks=200):
    proies, mammo = [], []
    for _ in range(n_eras):
        env = Biosphere3D(config)
        _setup(env)
        apply_fn(env)
        env.current_era = 1
        genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = env.agents + env.dead_agents          # PAS de save HoF : mesure pure, pop fixe
        proies.append(np.mean([a.get("preys_eaten", 0) for a in pool]) if pool else 0.0)
        mammo.append(env.big_kills)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    return float(np.mean(proies)), float(np.mean(mammo))


# Mécanismes ablables (réglés à 0 / neutralisés). MODULE = flag de classe (gène câblé).
WORLD_ABLATIONS = {
    "curiosite":       lambda e: setattr(e, "curiosity_scale", 0.0),
    "nouveaute":       lambda e: setattr(e, "novelty_scale", 0.0),
    "scaffold_grab":   lambda e: setattr(e, "scaffold_grab", 0.0),
    "scaffold_craft":  lambda e: setattr(e, "scaffold_craft", 0.0),
    "scaffold_bighit": lambda e: setattr(e, "scaffold_bighit", 0.0),
    "scaffold_approche": lambda e: setattr(e, "scaffold_eps", 0.0),   # ajout EDR 039
    "crit":            lambda e: setattr(e, "crit_base", 0.0),
    "cooperation":     lambda e: setattr(e, "coop_reward", False),    # ajout EDR 039 (clé !)
    "world_model":     lambda e: setattr(e, "world_model", None),     # ajout EDR 039
}
MODULE_ABLATIONS = ["seuils", "router"]   # gènes câblés (EDR 031)


def main(n_eras=5):
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
    eg = ExperimentGraph(db=db)

    print("ABLATION (rareté 12, %d ères/condition) — quels mécanismes comptent ?" % n_eras)
    base_p, base_m = run_condition(config, db, lambda e: None, n_eras)
    print(f"  BASELINE          : proies_moy={base_p:.2f} mammouth={base_m:.1f}")

    results = {}
    for name, fn in WORLD_ABLATIONS.items():
        p, m = run_condition(config, db, fn, n_eras)
        results[name] = (p, m)
        print(f"  sans {name:16s}: proies_moy={p:.2f} mammouth={m:.1f}  (d={p-base_p:+.2f})")
    for name in MODULE_ABLATIONS:
        setattr(MambaBatchModel, "ABLATE_THRESHOLDS", name == "seuils")
        setattr(MambaBatchModel, "ABLATE_ROUTER", name == "router")
        p, m = run_condition(config, db, lambda e: None, n_eras)
        results[name] = (p, m)
        print(f"  sans {name:16s}: proies_moy={p:.2f} mammouth={m:.1f}  (d={p-base_p:+.2f})")
        MambaBatchModel.ABLATE_THRESHOLDS = False
        MambaBatchModel.ABLATE_ROUTER = False

    # --- Écriture dans l'ontologie (Hypothesis / Fact) ---
    print("\n=== ONTOLOGIE (KuzuDB) : qui SUPPORTE/RÉFUTE « X contribue » ? ===")
    for name, (p, m) in sorted(results.items(), key=lambda kv: kv[1][0] - base_p):
        delta = p - base_p
        helps = delta < -0.10          # l'ablation fait mal -> le mécanisme contribue
        hid = f"mech_{name}"
        eg.log_hypothesis(hid, f"Le mecanisme {name} contribue a la survie (proies_moy)",
                          status="supported" if helps else "refuted")
        rel = "SUPPORTS" if helps else "REFUTES"
        eg.log_fact(f"ablation_{name}",
                    f"ablation {name}: proies_moy {p:.2f} vs baseline {base_p:.2f} (delta {delta:+.2f})",
                    hid, relation=rel)
        verdict = "COMPTE   " if helps else "négligeable/nul"
        print(f"  {name:16s} d={delta:+.2f} -> {rel:8s} ({verdict})")

    async_logger.stop()


if __name__ == "__main__":
    main()
