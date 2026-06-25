"""Sonde du plafond apex sous croissance topologique ACCUMULÉE (multi-ères évolutif).

Question : quand l'archi grossie PERSISTE entre générations (preserve_dims=True), les réseaux
grossissent-ils ET l'apex monte-t-il au-delà de ~0.21 — ou plafonne-t-il (verrou = répertoire-monde) ?

Harnais évolutif PROPRE (≠ main_biosphere lourd/non-repro) : carry des top-3 champions EN MÉMOIRE
(pas de HoF global → reproductible, isolé des sessions //), preserve_dims appliqué au ré-import
inter-ère (seul endroit où l'aplatissement mord). Déterministe (memory_retriever neutralisé, seedé).

Usage :
    AGISEED_QUIET_LOG=1 EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 \\
      EVP_MAX_TICKS=300 EVP_NODE_CAP=512 CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=0 \\
      python -u tools/evolve_ceiling_probe.py
"""
import os
import sys
import copy
import logging
import statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.curriculum.competence import competence_for, _frac_reaching
from src.seed_ai.harness import SeedManager, Harness
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.mutation import MutationConfig, apply_mutations
from src.seed_ai.repopulation import build_population
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.EvolveCeiling")


def _median(xs):
    return float(statistics.median(xs)) if xs else 0.0


def _agent_stats(all_agents):
    """Mêmes champs que target_competence_probe (signaux vivants EDR 096)."""
    return [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
             "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
             "total_dreams": a.get("total_dreams", 0),
             "mammoth_kills": a.get("mammoth_kills", 0),
             "spears_crafted": a.get("spears_crafted", 0)} for a in all_agents]


def run_evolution(target, k_eras, num_agents, max_ticks, shared_db,
                  preserve_dims, node_cap, experiment_seed=0):
    """K ères en `target`, carry des top-3 champions EN MÉMOIRE entre ères. preserve_dims appliqué
    au ré-import inter-ère. Retourne la trajectoire par ère (apex + taille réseau)."""
    comp_fn = competence_for(target)
    config = WorldConfig()
    config.base_metabolism = float(os.environ.get("CT_METAB", "0.25"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "3.0"))

    mut_config = MutationConfig(weight_init_std=2.0)
    heavy = copy.deepcopy(mut_config)            # fraction exploratrice (comme init_primordial_soup)
    heavy.weight_mutate_rate = min(1.0, mut_config.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mut_config.weight_mutate_power * 1.5

    carried = None        # liste de génomes champions portés en mémoire (None = ère 0)
    per_era = []

    for era in range(k_eras):
        SeedManager(experiment_seed + era * 1_000_000).seed_boundary(0)   # apparié (graine, ère)
        env = _prepare_world(target, config, deterministic=True)

        if carried is None:
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
        else:
            genomes = build_population(carried, num_agents, mut_config, apply_mutations,
                                       heavy_config=heavy, heavy_frac=0.3)

        cap_hits = 0
        for g in genomes:
            if g.num_nodes > node_cap:     # garde-fou compute NON silencieux
                cap_hits += 1
            a = MambaAgent()
            a.from_genome(g, preserve_dims=preserve_dims)
            env.add_agent(a, energy=50.0)

        env.current_era = era + 1
        t = 0
        while len(env.agents) > 0 and t < max_ticks:
            env.step()
            t += 1

        all_agents = env.agents + env.dead_agents
        stats = _agent_stats(all_agents)
        nodes = [a["model"].genome.num_nodes for a in all_agents if a.get("model") is not None]
        row = {
            "era": era,
            "frac_apex": round(_frac_reaching(stats, "mammoth_kills"), 4),
            "frac_tool": round(_frac_reaching(stats, "spears_crafted"), 4),
            "median_competence": round(comp_fn(stats), 4),
            "mean_nodes": round(statistics.mean(nodes), 2) if nodes else 0.0,
            "max_nodes": max(nodes) if nodes else 0,
            "n": len(all_agents),
            "ticks": t,
            "cap_hits": cap_hits,
        }
        per_era.append(row)
        log.info("  era=%d apex=%.3f C=%.3f mean_nodes=%.1f max_nodes=%d n=%d t=%d cap_hits=%d",
                 era, row["frac_apex"], row["median_competence"], row["mean_nodes"],
                 row["max_nodes"], row["n"], t, cap_hits)

        # Sélection -> carry (proxy fidèle de la sélection générationnelle, top-3 par life_score).
        top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]
        carried = [copy.deepcopy(a["model"].genome) for a in top if a.get("model") is not None]

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    return {"target": target, "preserve_dims": preserve_dims, "k_eras": k_eras,
            "node_cap": node_cap, "per_era": per_era}


def main():
    target = os.environ.get("EVP_TARGET", "stoneage")
    k = int(os.environ.get("EVP_K", "12"))
    num_agents = int(os.environ.get("EVP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("EVP_MAX_TICKS", "300"))
    node_cap = int(os.environ.get("EVP_NODE_CAP", "512"))
    preserve_dims = os.environ.get("EVP_PRESERVE_DIMS", "") == "1"
    experiment_seed = int(os.environ.get("EXPERIMENT_SEED", "0"))

    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Evolve ceiling : cible=%s preserve=%s K=%d agents=%d ticks=%d cap=%d seed=%d "
                 "metab=%s payoff=%s ===", target, preserve_dims, k, num_agents, max_ticks, node_cap,
                 experiment_seed, os.environ.get("CT_METAB", "0.25"), os.environ.get("CT_PAYOFF", "3.0"))
        result = run_evolution(target, k, num_agents, max_ticks, shared_db,
                               preserve_dims=preserve_dims, node_cap=node_cap,
                               experiment_seed=experiment_seed)
    finally:
        async_logger.stop()

    h = Harness(seed=0, name="evolve_ceiling_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    apex_traj = [r["frac_apex"] for r in result["per_era"]]
    nodes_traj = [r["mean_nodes"] for r in result["per_era"]]
    log.info("TRAJ apex=%s | mean_nodes=%s -> %s", apex_traj, nodes_traj, path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
