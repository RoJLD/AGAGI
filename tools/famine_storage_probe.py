"""Probe d'évolvabilité du stockage dans FamineWorld (spec 2026-06-30-Famine-Storage-Evolvability).

Évolue une population tabula-rasa DANS famine, puis teste causalement si le stockage a émergé :
ablation du cache (ON vs OFF) sur le champion évolué vs le champion stoneage (contrôle). Si la survie
s'effondre cache OFF pour l'évolué mais pas pour le stoneage -> la gratification différée est ÉVOLUÉE.
On évolue pour la SURVIE, jamais en récompensant le stockage (test d'émergence, pas d'enseignement)."""
import os
import sys
import math
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_famine import FamineWorld
from src.environments.config import WorldConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.harness import SeedManager
from main_biosphere import init_primordial_soup
from src.seed_ai.repopulation import build_population
from src.seed_ai.mutation import apply_mutations, MutationConfig


def count_reserves(agent: dict) -> int:
    """Nombre de fruits portés (frais ou masqués en réserve) dans l'inventaire d'un agent-dict."""
    inv = agent.get("inventory", [])
    return sum(1 for it in inv
               if isinstance(it, dict) and it.get("type") in ("Fruit", "_FruitReserve"))


def _genome_to_agent(g) -> MambaAgent:
    a = MambaAgent(g.num_inputs, g.num_outputs, g.num_nodes)
    a.from_genome(g)
    return a


def _new_famine(cache_enabled: bool, cycle_abundance: int, cycle_famine: int) -> FamineWorld:
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()       # repro + anti-contention KuzuDB
        w.memory_retriever.clear()
    w.benchmark_mode = True             # cohorte fixe (pas de repro/mutation pendant la mesure)
    w.night_enabled = False             # régime cohérent EDR-118 (isole la pénurie)
    w.cache_enabled = cache_enabled
    w.cycle_abundance, w.cycle_famine = cycle_abundance, cycle_famine
    return w


def measure_genome(genome, seed, cache_enabled=True, num_agents=10, max_ticks=300,
                   cycle_abundance=60, cycle_famine=40) -> Dict:
    """Survie médiane d'une cohorte de clones du génome, + fruits portés à la 1ʳᵉ transition famine."""
    SeedManager(seed).seed_boundary(0)
    w = _new_famine(cache_enabled, cycle_abundance, cycle_famine)
    for _ in range(num_agents):
        w.add_agent(_genome_to_agent(genome), energy=80.0)
    fruits_at_transition = None
    was_famine = w.is_famine()
    t = 0
    while w.agents and t < max_ticks:
        w.step()
        t += 1
        now_famine = w.is_famine()
        if fruits_at_transition is None and now_famine and not was_famine and w.agents:
            fruits_at_transition = float(np.mean([count_reserves(a) for a in w.agents]))
        was_famine = now_famine
    all_agents = w.agents + getattr(w, "dead_agents", [])
    ages = [int(a["age"]) for a in all_agents]
    return {"median_survival": float(np.median(ages)) if ages else 0.0,
            "fruits_at_transition": fruits_at_transition if fruits_at_transition is not None else 0.0}


def evolve_in_famine(seed, eras=15, num_agents=20, max_ticks=300,
                     cycle_abundance=60, cycle_famine=40):
    """Évolue une population tabula-rasa DANS famine (sélection par survie) -> génome du champion final.
    GA autonome (génome en mémoire, pas de KuzuDB) : population fraîche puis reseed muté du champion."""
    SeedManager(seed).seed_boundary(0)
    genomes, _ = init_primordial_soup(num_agents=num_agents, config=WorldConfig())
    mut_config = MutationConfig(weight_init_std=2.0, add_node_rate=0.0)  # topo fixe (batching stable)
    champion_genome = genomes[0]
    for _era in range(max(1, eras)):
        w = _new_famine(cache_enabled=True, cycle_abundance=cycle_abundance, cycle_famine=cycle_famine)
        for g in genomes:
            w.add_agent(_genome_to_agent(g), energy=50.0)
        t = 0
        while w.agents and t < max_ticks:
            w.step()
            t += 1
        all_agents = w.agents + getattr(w, "dead_agents", [])
        if not all_agents:
            break
        champion_genome = max(all_agents, key=calculate_life_score)["model"].genome
        genomes = build_population([champion_genome], num_agents, mut_config, apply_mutations)
    return champion_genome
