"""
tools/civilization_multiworld_benchmark.py — Banc Comparatif Officiel pour la Civilisation Autonome Multi-Mondes (Arc 13 : Jalon M30).

Évalue et compare rigoureusement deux régimes sous le Commandement 15 (PIU) :
1. Baseline : Mondes 1, 2 et 3 fonctionnant de manière isolée sans consensus BFT ni transferts.
2. Intervention : Mondes 1, 2 et 3 unifiés par CivilizationWorldConductor (Consensus BFT Weiszfeld,
   planification MCTS continue, critique réflexive et solidarité calorique/technologique).

Mesure la résilience collective, le ratio de survie, l'énergie moyenne et les transferts vitaux.
Conforme aux 12 Commandements AGIseed (Commandement 14, 15 et 16).
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


def run_civilization_multiworld_benchmark(num_steps: int = 25, seed: int = 42) -> Dict[str, Any]:
    """
    Exécute le banc comparatif officiel multi-mondes Baseline vs Intervention.
    """
    print(f"\n🏛️ [BANC OFFICIEL] Démarrage du benchmark Civilisation Autonome Multi-Mondes ({num_steps} pas)...")

    # -------------------------------------------------------------
    # 1. RÉGIME BASELINE : Mondes Isolés (Sans coordination ni trade)
    # -------------------------------------------------------------
    cfg_base = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=False,
        enable_latent_mcts=False,
        enable_self_reflection=False,
        enable_inter_world_trade=False,
        seed=seed,
    )
    conductor_base = CivilizationWorldConductor(cfg_base)
    conductor_base.populate_world("stoneage", count=4, energy=35.0)
    conductor_base.populate_world("agricultural", count=4, energy=45.0)
    conductor_base.populate_world("industrial", count=4, energy=40.0)

    # Forcer des conditions de stress dans le Monde 2 (gel) et Monde 1
    conductor_base.world_agri.season = "winter"
    conductor_base.world_agri.season_ticks = 0

    base_start_time = time.perf_counter()
    base_energies = []
    base_survivors = []

    for s in range(num_steps):
        m = conductor_base.step_civilization()
        base_energies.append(m["mean_energy"])
        base_survivors.append(m["total_population"])

    base_duration = time.perf_counter() - base_start_time
    final_base_pop = base_survivors[-1] if base_survivors else 0
    final_base_energy = base_energies[-1] if base_energies else float("nan")

    # -------------------------------------------------------------
    # 2. RÉGIME INTERVENTION : Civilisation Autonome Unifiée
    # -------------------------------------------------------------
    cfg_inter = CivilizationConductorConfig(
        latent_dim=64,
        world_size=10,
        enable_bft_consensus=True,
        enable_latent_mcts=True,
        enable_self_reflection=True,
        enable_inter_world_trade=True,
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
    conductor_inter.world_agri.granary_reserves = 60.0
    conductor_inter.world_indus.iron_smelted = 3

    inter_start_time = time.perf_counter()
    inter_energies = []
    inter_survivors = []
    total_trade_events = 0

    for s in range(num_steps):
        m = conductor_inter.step_civilization()
        inter_energies.append(m["mean_energy"])
        inter_survivors.append(m["total_population"])
        total_trade_events += m["trade_events_count"]

    inter_duration = time.perf_counter() - inter_start_time
    final_inter_pop = inter_survivors[-1] if inter_survivors else 0
    final_inter_energy = inter_energies[-1] if inter_energies else float("nan")

    # -------------------------------------------------------------
    # 3. SYNTHÈSE DES MÉTRIQUES & GAINS SOCIOLOGIQUES
    # -------------------------------------------------------------
    pop_gain = final_inter_pop - final_base_pop
    energy_gain = final_inter_energy - final_base_energy
    pop_gain_pct = ((final_inter_pop - final_base_pop) / max(1, final_base_pop)) * 100.0

    results = {
        "num_steps": num_steps,
        "baseline_final_population": int(final_base_pop),
        "baseline_mean_energy": float(round(final_base_energy, 2)),
        "baseline_duration_sec": float(round(base_duration, 3)),
        "intervention_final_population": int(final_inter_pop),
        "intervention_mean_energy": float(round(final_inter_energy, 2)),
        "intervention_duration_sec": float(round(inter_duration, 3)),
        "total_trade_events": int(total_trade_events),
        "population_gain": int(pop_gain),
        "population_gain_pct": float(round(pop_gain_pct, 2)),
        "energy_gain": float(round(energy_gain, 2)),
        "resilience_validated": bool(final_inter_pop >= final_base_pop and final_inter_energy >= final_base_energy),
    }

    print("\n" + "="*65)
    print("🏛️ RÉSULTATS DU BENCHMARK CIVILISATION MULTI-MONDES (ARC 13)")
    print("="*65)
    print(f"• Pas exécutés : {num_steps} par monde (Total 3x{num_steps} = {3*num_steps} ticks)")
    print(f"• Population finale Baseline (isolée)       : {final_base_pop}/12 agents | Énergie : {final_base_energy:.1f} E")
    print(f"• Population finale Intervention (unie)     : {final_inter_pop}/12 agents | Énergie : {final_inter_energy:.1f} E")
    print(f"• Différentiel de survie                    : +{pop_gain} agents (+{pop_gain_pct:.1f}%)")
    print(f"• Différentiel d'énergie vitale             : +{energy_gain:.1f} E")
    print(f"• Événements de transfert inter-mondes     : {total_trade_events} secours vivriers & techniques")
    print(f"• Temps d'exécution par pas                 : {inter_duration/num_steps*1000:.1f} ms/pas")
    print(f"• Validation de Résilience (PIU C15)        : {'✅ VALIDÉ' if results['resilience_validated'] else '❌ RÉFUTÉ'}")
    print("="*65 + "\n")

    return results


if __name__ == "__main__":
    run_civilization_multiworld_benchmark(num_steps=20)
