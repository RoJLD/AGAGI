"""Probe d'évolvabilité du stockage dans FamineWorld (spec 2026-06-30-Famine-Storage-Evolvability).

Évolue une population tabula-rasa DANS famine, puis teste causalement si le stockage a émergé :
ablation du cache (ON vs OFF) sur le champion évolué vs le champion stoneage (contrôle). Si la survie
s'effondre cache OFF pour l'évolué mais pas pour le stoneage -> la gratification différée est ÉVOLUÉE.
On évolue pour la SURVIE, jamais en récompensant le stockage (test d'émergence, pas d'enseignement)."""
import os
import sys
import math
import statistics
import json
from typing import List, Dict

from tools.curriculum_transfer import _sign_test_p
from tools.s2_demand import load_champion_genome

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


def compute_emergence_verdict(deltas_famine: List[float], deltas_stoneage: List[float],
                              min_effect: float = 5.0) -> Dict:
    """PUR. Delta d'ablation apparié (famine - stoneage) par seed -> verdict d'émergence du stockage."""
    n = min(len(deltas_famine), len(deltas_stoneage))
    if n == 0:
        return {"n": 0, "median_delta_famine": 0.0, "median_delta_stoneage": 0.0,
                "median_paired": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "N_EMERGE_PAS"}
    paired = [deltas_famine[i] - deltas_stoneage[i] for i in range(n)]
    med_pair = float(statistics.median(paired))
    n_fav = sum(1 for p in paired if p > 0.0)
    effective = [p for p in paired if p != 0.0]
    sign_p = _sign_test_p(sum(1 for p in effective if p > 0.0), len(effective))
    emerge = (med_pair > min_effect) and (2 * n_fav > n) and (sign_p < 0.05)
    return {"n": n,
            "median_delta_famine": float(statistics.median(deltas_famine[:n])),
            "median_delta_stoneage": float(statistics.median(deltas_stoneage[:n])),
            "median_paired": med_pair, "n_favorable": n_fav, "sign_p": sign_p,
            "verdict": "EMERGE" if emerge else "N_EMERGE_PAS"}


def run_storage_probe(seeds, eras=15, num_agents=20, max_ticks=300,
                      cycle_abundance=60, cycle_famine=40) -> Dict:
    """Orchestration : par seed, évolue en famine + ablation A/B (évolué) + contrôle stoneage."""
    stoneage_genome = load_champion_genome()
    per_seed, df, ds = [], [], []
    for seed in seeds:
        champ = evolve_in_famine(seed, eras, num_agents, max_ticks, cycle_abundance, cycle_famine)
        f_on = measure_genome(champ, seed, True, num_agents, max_ticks, cycle_abundance, cycle_famine)
        f_off = measure_genome(champ, seed, False, num_agents, max_ticks, cycle_abundance, cycle_famine)
        s_on = measure_genome(stoneage_genome, seed, True, num_agents, max_ticks, cycle_abundance, cycle_famine)
        s_off = measure_genome(stoneage_genome, seed, False, num_agents, max_ticks, cycle_abundance, cycle_famine)
        d_f = f_on["median_survival"] - f_off["median_survival"]
        d_s = s_on["median_survival"] - s_off["median_survival"]
        df.append(d_f); ds.append(d_s)
        per_seed.append({"seed": int(seed), "delta_famine": d_f, "delta_stoneage": d_s,
                         "fruits_famine": f_on["fruits_at_transition"],
                         "fruits_stoneage": s_on["fruits_at_transition"],
                         "f_on": f_on["median_survival"], "f_off": f_off["median_survival"],
                         "s_on": s_on["median_survival"], "s_off": s_off["median_survival"]})
    verdict = compute_emergence_verdict(df, ds)
    return {**verdict, "per_seed": per_seed,
            "config": {"seeds": [int(s) for s in seeds], "eras": eras, "num_agents": num_agents,
                       "max_ticks": max_ticks, "cycle_abundance": cycle_abundance,
                       "cycle_famine": cycle_famine}}


def main():
    seeds = [int(s) for s in os.environ.get("FSP_SEEDS", "0,1").split(",") if s.strip()]
    eras = int(os.environ.get("FSP_ERAS", "15"))
    num_agents = int(os.environ.get("FSP_NUM_AGENTS", "20"))
    max_ticks = int(os.environ.get("FSP_MAX_TICKS", "300"))
    r = run_storage_probe(seeds, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    print("FSP_RESULT", json.dumps(r))
    return r


if __name__ == "__main__":
    main()
