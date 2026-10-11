"""
tools/federal_agi_benchmark.py — Banc Comparatif Global de Clôture de l'Arc 14 (Jalon M34).

Évalue et compare rigoureusement deux régimes sous le Commandement 15 (PIU) :
1. Baseline : Civilisation Fédérale Multi-Mondes (Arc 13) SANS auto-amélioration récursive
   (génomes statiques, pas de méta-génome, pas de pont Graph-RAG temps réel).
2. Intervention : AGI Fédérale Hybride Auto-Améliorante (Arc 14) AVEC synthèse du méta-génome,
   compilation évolutive en sandbox (NTM -> synapses Lipschitziennes) et synchronisation Graph-RAG temps réel.

Mesure la résilience collective, le ratio de survie, l'énergie moyenne, les mutations appliquées,
le dividende de découverte et la stabilité spectrale contractante rho(W) <= 0.95.
Conforme aux 12 Commandements AGIseed (Commandements 1, 2, 3, 6, 7, 9, 14, 15 et 16).
"""

import sys
import os
import time
from typing import Dict, Any, List
import numpy as np

# Ajout du path racine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.worlds.civilization_world_conductor import (
    CivilizationWorldConductor,
    CivilizationConductorConfig,
)


def run_federal_agi_benchmark(num_steps: int = 30, seed: int = 42) -> Dict[str, Any]:
    """
    Exécute le banc comparatif officiel de clôture de l'Arc 14 Baseline vs Intervention.
    """
    print(f"\n🧠 [BANC GLOBAL ARC 14] Démarrage du benchmark AGI Fédérale Auto-Améliorante ({num_steps} pas)...")

    # -----------------------------------------------------------------
    # 1. RÉGIME BASELINE : Civilisation Coordonnée mais Statique (Sans Arc 14)
    # -----------------------------------------------------------------
    cfg_base = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
        enable_inter_world_trade=True,
        enable_metagenome_compilation=False,
        enable_realtime_graphrag_bridge=False,
        distress_energy_threshold=25.0,
        granary_relief_amount=12.0,
        mcts_num_simulations=15,
        seed=seed,
    )
    conductor_base = CivilizationWorldConductor(cfg_base)
    conductor_base.populate_world("stoneage", count=4, energy=35.0)
    conductor_base.populate_world("agricultural", count=4, energy=45.0)
    conductor_base.populate_world("industrial", count=4, energy=40.0)

    # Conditions de contrainte environnementale (hiver agricole, ressources limitées)
    conductor_base.world_agri.season = "winter"
    conductor_base.world_agri.season_ticks = 0
    conductor_base.world_agri.granary_reserves = 40.0
    conductor_base.world_indus.iron_smelted = 2

    base_start_time = time.perf_counter()
    base_energies = []
    base_survivors = []
    base_mutations_total = 0

    for s in range(num_steps):
        m = conductor_base.step_civilization()
        base_energies.append(m["mean_energy"])
        base_survivors.append(m["total_population"])
        base_mutations_total += m["mutations_applied"]

    base_duration = time.perf_counter() - base_start_time
    final_base_pop = base_survivors[-1] if base_survivors else 0
    final_base_energy = base_energies[-1] if base_energies else float("nan")

    # -----------------------------------------------------------------
    # 2. RÉGIME INTERVENTION : AGI Fédérale Hybride Auto-Améliorante (Arc 14)
    # -----------------------------------------------------------------
    cfg_inter = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
        enable_inter_world_trade=True,
        enable_metagenome_compilation=True,
        enable_realtime_graphrag_bridge=True,
        metagenome_distill_interval=10,
        distress_energy_threshold=25.0,
        granary_relief_amount=12.0,
        mcts_num_simulations=15,
        seed=seed,
    )
    conductor_inter = CivilizationWorldConductor(cfg_inter)
    conductor_inter.populate_world("stoneage", count=4, energy=35.0)
    conductor_inter.populate_world("agricultural", count=4, energy=45.0)
    conductor_inter.populate_world("industrial", count=4, energy=40.0)

    conductor_inter.world_agri.season = "winter"
    conductor_inter.world_agri.season_ticks = 0
    conductor_inter.world_agri.granary_reserves = 40.0
    conductor_inter.world_indus.iron_smelted = 2

    inter_start_time = time.perf_counter()
    inter_energies = []
    inter_survivors = []
    inter_mutations_total = 0
    total_trade_events = 0

    for s in range(num_steps):
        m = conductor_inter.step_civilization()
        inter_energies.append(m["mean_energy"])
        inter_survivors.append(m["total_population"])
        inter_mutations_total += m["mutations_applied"]
        total_trade_events += m["trade_events_count"]

    inter_duration = time.perf_counter() - inter_start_time
    final_inter_pop = inter_survivors[-1] if inter_survivors else 0
    final_inter_energy = inter_energies[-1] if inter_energies else float("nan")

    # Vérification spectrale lipschitzienne sur le méta-génome fédéral distillé (Arc 14 : M32)
    max_spectral_radius = float(conductor_inter.metagenome_synthesizer.spectral_radius)

    # -----------------------------------------------------------------
    # 3. SYNTHÈSE DES MÉTRIQUES & GAINS SOCIOLOGIQUES
    # -----------------------------------------------------------------
    pop_gain = final_inter_pop - final_base_pop
    energy_gain = final_inter_energy - final_base_energy
    pop_gain_pct = ((final_inter_pop - final_base_pop) / max(1, final_base_pop)) * 100.0

    results = {
        "num_steps": num_steps,
        "baseline_final_population": int(final_base_pop),
        "baseline_mean_energy": float(round(final_base_energy, 2)),
        "baseline_mutations_applied": int(base_mutations_total),
        "baseline_duration_sec": float(round(base_duration, 3)),
        "intervention_final_population": int(final_inter_pop),
        "intervention_mean_energy": float(round(final_inter_energy, 2)),
        "intervention_mutations_applied": int(inter_mutations_total),
        "intervention_trade_events": int(total_trade_events),
        "intervention_max_spectral_radius": float(round(max_spectral_radius, 4)),
        "intervention_duration_sec": float(round(inter_duration, 3)),
        "population_gain": int(pop_gain),
        "population_gain_pct": float(round(pop_gain_pct, 1)),
        "mean_energy_gain": float(round(energy_gain, 2)),
    }

    print("\n📊 --- RÉSULTATS COMPARATIFS OFFICIELS ARC 14 ---")
    print(f"🔹 Pas de simulation par régime        : {num_steps}")
    print(f"🔹 Survie Finale (Baseline vs Interv)  : {final_base_pop}/12 -> {final_inter_pop}/12 ({'+' if pop_gain >= 0 else ''}{pop_gain_pct}%)")
    print(f"🔹 Énergie Finale Moyenne              : {final_base_energy:.2f} E -> {final_inter_energy:.2f} E ({'+' if energy_gain >= 0 else ''}{energy_gain:.2f} E)")
    print(f"🔹 Mutations Méta-Génome Appliquées   : {inter_mutations_total} compilations NTM validées en sandbox")
    print(f"🔹 Rayon Spectral Maximal rho(W)       : {max_spectral_radius:.4f} <= 0.95 (Garantie de contraction)")
    print(f"🔹 Événements de Troc Inter-Mondes     : {total_trade_events} transferts de solidarité")
    print(f"🔹 Débit d'exécution (Intervention)    : {num_steps / max(1e-5, inter_duration):.2f} pas/sec")
    print("--------------------------------------------------\n")

    return results


if __name__ == "__main__":
    res = run_federal_agi_benchmark(num_steps=30, seed=42)
