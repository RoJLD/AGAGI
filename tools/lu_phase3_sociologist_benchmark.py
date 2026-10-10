"""
tools/lu_phase3_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 3).
Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : LU Phase 2 (Compositionnalité VSA + Relais multi-hop, sans ToM ni délibération).
- 30 Ères Intervention : LU Phase 3 (Récursion sémantique, Théorie de l'Esprit Latente et Délibération au coin du feu).
- Analyse comparative Before/After et verdict de recevabilité sociologique.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from typing import Dict, Any

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase3(enable_phase3: bool, eras: int = 30, ticks_per_era: int = 25, seed: int = 42) -> Dict[str, Any]:
    """Exécute une campagne de 30 ères sous configuration Phase 2 vs Phase 3."""
    survivals = []
    cooperative_hunts = []
    total_relays = []
    tom_silences = []
    deliberations_count = []
    final_energies = []

    for era in range(eras):
        np.random.seed(seed * 1000 + era)
        world_cfg = WorldConfig(size=16)
        world = Biosphere3D(world_cfg)
        
        adapter_cfg = LUInWorldConfig(
            latent_dim=16,
            hear_radius=3,
            enable_multi_hop=True,
            enable_compositional_grammar=True,
            enable_tom=enable_phase3,
            enable_deliberation=enable_phase3,
            pack_coordination=True,
            deliberation_rounds=3,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter
        
        # 6 agents avec connectomes Mamba isocaloriques
        for i in range(6):
            world.add_agent(
                MambaAgent(isocaloric=True),
                x=int(7 + (i % 3)),
                y=int(7 + (i // 3)),
                energy=60.0
            )

        # Proies
        for p_idx in range(4):
            world.preys.append({
                "x": int(1 + p_idx * 3),
                "y": int(2 + p_idx * 2),
                "hp": 1.0,
                "type": "Mammouth"
            })

        # Si Phase 3, placer un feu de camp au centre pour tester les rituels délibératifs
        if enable_phase3:
            world.items = [{"x": 8, "y": 8, "type": "fire"}]

        era_hunts = 0
        era_relays = 0
        era_tom_silences = 0
        era_deliberations = 0
        living_ticks = 0

        for t in range(ticks_per_era):
            # Alternance jour/nuit pour déclencher le feu de camp si Phase 3
            if enable_phase3 and t % 10 == 0:
                world.is_night = True
            else:
                world.is_night = False

            prev_hunts = adapter.cooperative_hunts_count
            prev_relays = adapter.multi_hop_relays_count
            prev_silences = adapter.tom_silences_count
            prev_delib = adapter.deliberation_events_count

            world.step()

            era_hunts += (adapter.cooperative_hunts_count - prev_hunts)
            era_relays += (adapter.multi_hop_relays_count - prev_relays)
            era_tom_silences += (adapter.tom_silences_count - prev_silences)
            era_deliberations += (adapter.deliberation_events_count - prev_delib)
            
            living = [a for a in world.agents if a.get("energy", 0) > 0]
            if len(living) > 0:
                living_ticks += 1
            else:
                break

        survivals.append(living_ticks)
        cooperative_hunts.append(era_hunts)
        total_relays.append(era_relays)
        tom_silences.append(era_tom_silences)
        deliberations_count.append(era_deliberations)

        agent_energies = [float(a.get("energy", 0.0)) for a in world.agents if not np.isnan(a.get("energy", 0.0))]
        mean_e = float(np.mean(agent_energies)) if len(agent_energies) > 0 else float('nan')
        final_energies.append(mean_e)

    valid_energies = [e for e in final_energies if not np.isnan(e)]
    mean_final_e = float(np.mean(valid_energies)) if len(valid_energies) > 0 else float('nan')

    return {
        "eras": eras,
        "median_survival_ticks": float(np.median(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_survival_ticks": float(np.mean(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_cooperative_hunts": float(np.mean(cooperative_hunts)) if len(cooperative_hunts) > 0 else float('nan'),
        "mean_relays_per_era": float(np.mean(total_relays)) if len(total_relays) > 0 else float('nan'),
        "mean_tom_silences": float(np.mean(tom_silences)) if len(tom_silences) > 0 else float('nan'),
        "mean_deliberations": float(np.mean(deliberations_count)) if len(deliberations_count) > 0 else float('nan'),
        "mean_final_energy": mean_final_e,
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 3 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Eres Baseline (LU Phase 2) vs 30 Eres Intervention (LU Phase 3 ToM + Deliberation)")
    print("=" * 80)

    # 1. Baseline
    print("\n[1/2] Execution de la Campagne Baseline (30 Eres - LU Phase 2 Relais Seul)...")
    base_res = simulate_campaign_phase3(enable_phase3=False, eras=30, ticks_per_era=25, seed=42)
    print(f"  -> Survie moyenne      : {base_res['mean_survival_ticks']:.2f} ticks (mediane: {base_res['median_survival_ticks']:.1f})")
    print(f"  -> Chasses coordonnees : {base_res['mean_cooperative_hunts']:.2f} / ere")
    print(f"  -> Relais multi-hop    : {base_res['mean_relays_per_era']:.2f} / ere")
    print(f"  -> Silences ToM        : {base_res['mean_tom_silences']:.2f} / ere")
    print(f"  -> Deliberations feu   : {base_res['mean_deliberations']:.2f} / ere")
    print(f"  -> Energie finale moy  : {base_res['mean_final_energy']:.2f}")

    # 2. Intervention
    print("\n[2/2] Execution de la Campagne Intervention (30 Eres - LU Phase 3 ToM + Deliberation)...")
    interv_res = simulate_campaign_phase3(enable_phase3=True, eras=30, ticks_per_era=25, seed=42)
    print(f"  -> Survie moyenne      : {interv_res['mean_survival_ticks']:.2f} ticks (mediane: {interv_res['median_survival_ticks']:.1f})")
    print(f"  -> Chasses coordonnees : {interv_res['mean_cooperative_hunts']:.2f} / ere")
    print(f"  -> Relais multi-hop    : {interv_res['mean_relays_per_era']:.2f} / ere")
    print(f"  -> Silences ToM        : {interv_res['mean_tom_silences']:.2f} / ere")
    print(f"  -> Deliberations feu   : {interv_res['mean_deliberations']:.2f} / ere")
    print(f"  -> Energie finale moy  : {interv_res['mean_final_energy']:.2f}")

    # 3. Decision
    energy_delta = interv_res['mean_final_energy'] - base_res['mean_final_energy']
    survival_delta = interv_res['mean_survival_ticks'] - base_res['mean_survival_ticks']
    hunts_delta = interv_res['mean_cooperative_hunts'] - base_res['mean_cooperative_hunts']

    print("\n" + "=" * 80)
    print("📊 RAPPORT COMPARATIF SOCIOLOGIQUE PIU (AVANT / APRES) :")
    print(f"  * Delta Survie        : {survival_delta:+.2f} ticks")
    print(f"  * Delta Energie finale: {energy_delta:+.2f} pts (Gain d'efficience metabolique et epargne ToM)")
    print(f"  * Delta Chasses       : {hunts_delta:+.2f} / ere")
    print(f"  * Silences Pragmatiques ToM : {interv_res['mean_tom_silences']:.2f} / ere (0.0 en baseline)")
    print(f"  * Rituels de Deliberation  : {interv_res['mean_deliberations']:.2f} / ere (0.0 en baseline)")

    passed = (interv_res['mean_survival_ticks'] >= base_res['mean_survival_ticks']) and (interv_res['mean_final_energy'] >= base_res['mean_final_energy'])
    print("-" * 80)
    if passed:
        print("✅ VERDICT SOCIOLOGIQUE : INNOVATION VALIDE (Score Intervention >= Baseline)")
        print("   La Theorie de l'Esprit Latente et les Rituels Deliberatifs ameliorent la conservation d'energie")
        print("   et la cohesion de meute sans regression adaptative.")
    else:
        print("❌ VERDICT SOCIOLOGIQUE : REJET (Regression observee)")
    print("=" * 80)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
