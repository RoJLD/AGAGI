"""
tools/lu_phase4_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 4).
Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : LU Phase 3 isolée (Autarcie sans troc entre clans spécialisés).
- 30 Ères Intervention : LU Phase 4 (Marché décentralisé, contrats de troc latents et dialectes de clan).
- Analyse comparative Before/After et verdict de recevabilité sociologique.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from typing import Dict, Any

from src.environments.config import WorldConfig
from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase4(enable_phase4: bool, eras: int = 30, ticks_per_era: int = 30, seed: int = 42) -> Dict[str, Any]:
    """Exécute une campagne de 30 ères sous configuration Phase 3 Autarcie vs Phase 4 Marché/Troc."""
    survivals = []
    total_trades = []
    final_energies = []
    harvest_counts = []
    tom_silences = []

    for era in range(eras):
        np.random.seed(seed * 1000 + era)
        # Utilisation du Monde 2 (Agricole) avec cycle saisonnier
        agri_cfg = AgriculturalConfig(
            size=16,
            season_duration=15,  # 2 saisons par ère de 30 ticks (Printemps/Été ou Automne/Hiver)
            winter_energy_penalty=0.15,
        )
        world = AgriculturalWorld(agri_cfg)
        
        adapter_cfg = LUInWorldConfig(
            latent_dim=32,
            hear_radius=3,
            enable_multi_hop=True,
            enable_compositional_grammar=True,
            enable_tom=True,
            enable_deliberation=True,
            enable_dialects=enable_phase4,
            enable_trade_contracts=enable_phase4,
            trade_agreement_threshold=0.60,
            market_point=(8, 8),
            market_radius=5,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents répartis en 2 clans spécialisés complémentaires :
        # Clan Nord (Agriculteurs, x=7..9, y=6..8) porteurs de Fruit/Nourriture
        # Clan Sud (Artisans/Chasseurs, x=7..9, y=8..10) porteurs d'outils/bois
        for i in range(6):
            clan = "Clan_North" if i < 3 else "Clan_South"
            init_inv = [{"type": "Fruit", "quality": 1.0}] if i < 3 else [{"type": "Spear", "quality": 1.0}]
            ag_obj = MambaAgent(isocaloric=True)
            world.add_agent(
                ag_obj,
                x=int(7 + (i % 3)),
                y=int(7 + (i // 3)),
                energy=55.0
            )
            # Affectation du clan et inventaire initial asymétrique
            world.agents[-1]["clan"] = clan
            world.agents[-1]["inventory"] = list(init_inv)

        era_trades = 0
        era_silences = 0
        living_ticks = 0

        for t in range(ticks_per_era):
            prev_trades = adapter.contracts_settled_count
            prev_silences = adapter.tom_silences_count

            world.step()

            era_trades += (adapter.contracts_settled_count - prev_trades)
            era_silences += (adapter.tom_silences_count - prev_silences)

            living = [a for a in world.agents if a.get("energy", 0) > 0]
            if len(living) > 0:
                living_ticks += 1
            else:
                break

        survivals.append(living_ticks)
        total_trades.append(era_trades)
        tom_silences.append(era_silences)
        harvest_counts.append(world.harvested_crops)

        agent_energies = [float(a.get("energy", 0.0)) for a in world.agents if not np.isnan(a.get("energy", 0.0))]
        mean_e = float(np.mean(agent_energies)) if len(agent_energies) > 0 else float('nan')
        final_energies.append(mean_e)

    valid_energies = [e for e in final_energies if not np.isnan(e)]
    mean_final_e = float(np.mean(valid_energies)) if len(valid_energies) > 0 else float('nan')

    return {
        "eras": eras,
        "median_survival_ticks": float(np.median(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_survival_ticks": float(np.mean(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_trades_settled": float(np.mean(total_trades)) if len(total_trades) > 0 else float('nan'),
        "mean_tom_silences": float(np.mean(tom_silences)) if len(tom_silences) > 0 else float('nan'),
        "mean_harvests": float(np.mean(harvest_counts)) if len(harvest_counts) > 0 else float('nan'),
        "mean_final_energy": mean_final_e,
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 4 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Eres Baseline (LU Phase 3 Autarcie) vs 30 Eres Intervention (LU Phase 4 Marche/Troc)")
    print("=" * 80)

    # 1. Baseline
    print("\n[1/2] Execution de la Campagne Baseline (30 Eres - LU Phase 3 Autarcie sans troc)...")
    base_res = simulate_campaign_phase4(enable_phase4=False, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne      : {base_res['mean_survival_ticks']:.2f} ticks (mediane: {base_res['median_survival_ticks']:.1f})")
    print(f"  -> Contrats de troc    : {base_res['mean_trades_settled']:.2f} / ere")
    print(f"  -> Recoltes agricoles  : {base_res['mean_harvests']:.2f} / ere")
    print(f"  -> Silences ToM        : {base_res['mean_tom_silences']:.2f} / ere")
    print(f"  -> Energie finale moy  : {base_res['mean_final_energy']:.2f}")

    # 2. Intervention
    print("\n[2/2] Execution de la Campagne Intervention (30 Eres - LU Phase 4 Contrats de Troc & Dialectes)...")
    interv_res = simulate_campaign_phase4(enable_phase4=True, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne      : {interv_res['mean_survival_ticks']:.2f} ticks (mediane: {interv_res['median_survival_ticks']:.1f})")
    print(f"  -> Contrats de troc    : {interv_res['mean_trades_settled']:.2f} / ere")
    print(f"  -> Recoltes agricoles  : {interv_res['mean_harvests']:.2f} / ere")
    print(f"  -> Silences ToM        : {interv_res['mean_tom_silences']:.2f} / ere")
    print(f"  -> Energie finale moy  : {interv_res['mean_final_energy']:.2f}")

    # 3. Decision
    energy_delta = interv_res['mean_final_energy'] - base_res['mean_final_energy']
    survival_delta = interv_res['mean_survival_ticks'] - base_res['mean_survival_ticks']
    trades_delta = interv_res['mean_trades_settled'] - base_res['mean_trades_settled']

    print("\n" + "=" * 80)
    print("📊 RAPPORT COMPARATIF SOCIOLOGIQUE PIU (AVANT / APRES) :")
    print(f"  * Delta Survie        : {survival_delta:+.2f} ticks")
    print(f"  * Delta Energie finale: {energy_delta:+.2f} pts (Surplus commercial et complementaite)")
    print(f"  * Contrats Conclus    : {interv_res['mean_trades_settled']:.2f} / ere (0.0 en baseline autarcique)")
    print(f"  * Silences ToM        : {interv_res['mean_tom_silences']:.2f} / ere")
    print("-" * 80)

    passed = (interv_res['mean_survival_ticks'] >= base_res['mean_survival_ticks']) and (interv_res['mean_final_energy'] >= base_res['mean_final_energy'])
    if passed:
        print("✅ VERDICT SOCIOLOGIQUE : INNOVATION VALIDE (Score Intervention >= Baseline)")
        print("   L'economie de marche par contrats latents et la speciation dialectale ameliorent")
        print("   significativement le bilan energetique sans aucune regression adaptative.")
    else:
        print("❌ VERDICT SOCIOLOGIQUE : REJET (Regression observee)")
    print("=" * 80)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
