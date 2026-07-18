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
from src.seed_ai.evolution import tournament_selection
from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.EvolveCeiling")


def _agent_stats(all_agents):
    """Mêmes champs que target_competence_probe (signaux vivants EDR 096)."""
    return [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
             "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
             "total_dreams": a.get("total_dreams", 0),
             "mammoth_kills": a.get("mammoth_kills", 0),
             "spears_crafted": a.get("spears_crafted", 0)} for a in all_agents]


def run_evolution(target, k_eras, num_agents, max_ticks, shared_db,
                  preserve_dims, node_cap, experiment_seed=0,
                  select="elitist", n_carry=12, tournament_size=3, pop_cap=None):
    """K ères en `target`, carry des champions EN MÉMOIRE entre ères. preserve_dims appliqué au
    ré-import inter-ère. select='elitist' (top-3) | 'diverse' (tournoi sur toute la population, EDR 105
    corollaire). pop_cap borne la repro intra-ère (config.max_population). Retourne la trajectoire."""
    comp_fn = competence_for(target)
    config = WorldConfig()
    config.base_metabolism = float(os.environ.get("CT_METAB", "0.25"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "3.0"))
    config.mammoth_hp = float(os.environ.get("EVP_MAMMOTH_HP", "100"))   # tool-gate EDR 111 (100 = contrôle)
    MambaBatchModel.TD_GAMMA = float(os.environ.get("EVP_GAMMA", "0.9"))   # EDR 112/113 horizon crédit (0.9 = contrôle)
    config.max_population = pop_cap     # None = pas de cap (historique) ; sinon borne le runaway (EDR 105)

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
        w_means = [a["model"].genome.W.mean() for a in all_agents if a.get("model") is not None]
        genome_diversity = round(float(statistics.pstdev(w_means)), 4) if len(w_means) > 1 else 0.0
        # Diversité COMPORTEMENTALE (EDR 109) : std inter-agents de descripteurs NORMALISÉS par dimension
        # (sinon age ~0-300 domine mammoth ~0-2). Décompo -> stratégie (preys/mammoth/spears) vs survie (age).
        DESCRIPTORS = ("preys_eaten", "mammoth_kills", "spears_crafted", "age")
        bdiv = {}
        for d in DESCRIPTORS:
            vals = [s[d] for s in stats]
            vmax = max(vals) if vals else 0
            norm = [v / vmax for v in vals] if vmax > 0 else [0.0 for _ in vals]
            bdiv[d] = statistics.pstdev(norm) if len(norm) > 1 else 0.0
        behavioral_diversity = round(statistics.mean(bdiv.values()), 4) if bdiv else 0.0
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
            "genome_diversity": genome_diversity,
            "behavioral_diversity": behavioral_diversity,
            "bdiv_preys": round(bdiv["preys_eaten"], 4),
            "bdiv_mammoth": round(bdiv["mammoth_kills"], 4),
            "bdiv_spears": round(bdiv["spears_crafted"], 4),
            "bdiv_age": round(bdiv["age"], 4),
        }
        per_era.append(row)
        log.info("  era=%d apex=%.3f C=%.3f mean_nodes=%.1f n=%d t=%d gdiv=%.4f bdiv=%.4f",
                 era, row["frac_apex"], row["median_competence"], row["mean_nodes"],
                 row["n"], t, row["genome_diversity"], row["behavioral_diversity"])

        # Sélection -> carry. elitist=top-3 (EDR 105 baseline) ; diverse=tournoi sur TOUTE la pop.
        pool = [a for a in all_agents if a.get("model") is not None]
        if select == "diverse" and pool:
            fits = [calculate_life_score(a) for a in pool]
            genomes_pool = [a["model"].genome for a in pool]
            ts = min(tournament_size, len(genomes_pool))
            idxs = [tournament_selection(genomes_pool, fits, ts) for _ in range(n_carry)]
            carried = [copy.deepcopy(genomes_pool[i]) for i in idxs]
        else:
            top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]
            carried = [copy.deepcopy(a["model"].genome) for a in top if a.get("model") is not None]

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    return {"target": target, "preserve_dims": preserve_dims, "k_eras": k_eras,
            "node_cap": node_cap, "select": select, "n_carry": n_carry, "pop_cap": pop_cap,
            "per_era": per_era}


def main():
    target = os.environ.get("EVP_TARGET", "stoneage")
    k = int(os.environ.get("EVP_K", "12"))
    num_agents = int(os.environ.get("EVP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("EVP_MAX_TICKS", "300"))
    node_cap = int(os.environ.get("EVP_NODE_CAP", "512"))
    preserve_dims = os.environ.get("EVP_PRESERVE_DIMS", "") == "1"
    experiment_seed = int(os.environ.get("EXPERIMENT_SEED", "0"))
    select = os.environ.get("EVP_SELECT", "elitist")
    n_carry = int(os.environ.get("EVP_N_CARRY", "12"))
    tournament_size = int(os.environ.get("EVP_TOURNAMENT", "3"))
    _cap_env = os.environ.get("EVP_POP_CAP", "")
    pop_cap = int(_cap_env) if _cap_env else None

    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Evolve ceiling : cible=%s preserve=%s K=%d agents=%d ticks=%d cap=%d seed=%d "
                 "select=%s n_carry=%d pop_cap=%s metab=%s payoff=%s ===", target, preserve_dims, k,
                 num_agents, max_ticks, node_cap, experiment_seed, select, n_carry, pop_cap,
                 os.environ.get("CT_METAB", "0.25"), os.environ.get("CT_PAYOFF", "3.0"))
        result = run_evolution(target, k, num_agents, max_ticks, shared_db,
                               preserve_dims=preserve_dims, node_cap=node_cap,
                               experiment_seed=experiment_seed, select=select,
                               n_carry=n_carry, tournament_size=tournament_size, pop_cap=pop_cap)
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
