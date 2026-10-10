"""
tools/lu_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 2).
Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : LU continu holistique sans relais multi-hop.
- 30 Ères Intervention : LU compositionnel avec propagation acoustique multi-hop.
- Analyse comparative Before/After et verdict de recevabilité.
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


def run_campaign(enable_multihop: bool, eras: int = 30, ticks_per_era: int = 25, seed: int = 42) -> Dict[str, Any]:
    """Exécute une campagne de 30 ères sous configuration fixée."""
    np.random.seed(seed)
    
    survivals = []
    cooperative_hunts = []
    total_relays = []
    final_energies = []

    for era in range(eras):
        np.random.seed(seed * 1000 + era)
        world_cfg = WorldConfig(size=16)
        world = Biosphere3D(world_cfg)
        
        adapter_cfg = LUInWorldConfig(
            latent_dim=16,
            hear_radius=3,
            enable_multi_hop=enable_multihop,
            enable_compositional_grammar=enable_multihop,
            pack_coordination=True,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter
        
        # 6 agents avec connectomes Mamba isocaloriques
        for i in range(6):
            world.add_agent(
                MambaAgent(isocaloric=True),
                x=int(2 + (i * 2) % 12),
                y=int(2 + (i * 3) % 12),
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

        era_hunts = 0
        era_relays = 0
        living_ticks = 0

        for t in range(ticks_per_era):
            prev_hunts = adapter.cooperative_hunts_count
            prev_relays = adapter.multi_hop_relays_count
            world.step()
            era_hunts += (adapter.cooperative_hunts_count - prev_hunts)
            era_relays += (adapter.multi_hop_relays_count - prev_relays)
            
            living = [a for a in world.agents if a.get("energy", 0) > 0]
            if len(living) > 0:
                living_ticks += 1
            else:
                break

        survivals.append(living_ticks)
        cooperative_hunts.append(era_hunts)
        total_relays.append(era_relays)
        mean_e = float(np.mean([a.get("energy", 0) for a in world.agents])) if len(world.agents) > 0 else float('nan')
        final_energies.append(mean_e)

    return {
        "eras": eras,
        "median_survival_ticks": float(np.median(survivals)),
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_cooperative_hunts": float(np.mean(cooperative_hunts)),
        "mean_relays_per_era": float(np.mean(total_relays)),
        "mean_final_energy": float(np.mean(final_energies)),
    }


def main():
    print("🔬 Démarrage du Banc Sociologique LU Phase 2 (Loi du Sociologue - Commandement 15)...")
    
    # 1. Baseline : 30 Ères sans Multi-Hop
    print("\n--- 1. ÉVALUATION BASELINE (30 Ères - Sans Multi-Hop) ---")
    baseline = run_campaign(enable_multihop=False, eras=30)
    print(f"  Survie médiane : {baseline['median_survival_ticks']:.1f} ticks")
    print(f"  Chasses coopératives moyennes : {baseline['mean_cooperative_hunts']:.2f}")
    print(f"  Énergie finale moyenne : {baseline['mean_final_energy']:.2f}")

    # 2. Intervention : 30 Ères avec Multi-Hop
    print("\n--- 2. ÉVALUATION INTERVENTION (30 Ères - Avec Multi-Hop & Compositionnalité) ---")
    intervention = run_campaign(enable_multihop=True, eras=30)
    print(f"  Survie médiane : {intervention['median_survival_ticks']:.1f} ticks")
    print(f"  Chasses coopératives moyennes : {intervention['mean_cooperative_hunts']:.2f}")
    print(f"  Relais multi-hop moyens / ère : {intervention['mean_relays_per_era']:.2f}")
    print(f"  Énergie finale moyenne : {intervention['mean_final_energy']:.2f}")

    # 3. Analyse & Décision (Commandement 15)
    delta_energy = intervention['mean_final_energy'] - baseline['mean_final_energy']
    ratio_hunts = (intervention['mean_cooperative_hunts'] + 1e-6) / (baseline['mean_cooperative_hunts'] + 1e-6)

    print("\n--- 3. VERDICT DU SOCIOLOGUE ---")
    print(f"  Delta Énergie : {delta_energy:+.2f}")
    print(f"  Ratio Chasses Coopératives : x{ratio_hunts:.2f}")

    if delta_energy >= -1.0 and ratio_hunts >= 1.0:
        verdict = "VALIDÉ"
        print(f"✅ INNOVATION VALIDÉE SELON LA LOI DU SOCIOLOGUE (Score Intervention >= Baseline)")
    else:
        verdict = "REJET"
        print(f"❌ INNOVATION REJETÉE")

    return {
        "baseline": baseline,
        "intervention": intervention,
        "verdict": verdict
    }


if __name__ == "__main__":
    main()
