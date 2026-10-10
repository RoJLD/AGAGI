"""
tools/lu_phase7_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 7).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société proto-industrielle Phase 6 cloisonnée sans fédération diplomatique ni métagrammaire.
- 30 Ères Intervention : Fédération constitutionnelle inter-mondes, macro-règles RSI et traité de paix (Phase 7).
- Choc expérimental : Interactions multilatérales continues sous pressions climatiques et économiques.
- Analyse comparative Before/After et verdict de recevabilité sociologique.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
logging.disable(logging.INFO)
logging.getLogger("src.graph_rag.async_logger").setLevel(logging.WARNING)

import numpy as np
from typing import Dict, Any

from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase7(
    enable_diplomacy: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Sans fédération diplomatique) vs Phase 7 (Avec fédération & RSI).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    treaties_ratified_list = []
    meta_rules_list = []
    protections_list = []

    for era in range(eras):
        if (era + 1) % 10 == 0 or era == 0:
            print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(seed * 3000 + era)
        agri_cfg = AgriculturalConfig(
            size=16,
            season_duration=15,
            winter_energy_penalty=0.15,
        )
        world = AgriculturalWorld(agri_cfg)

        adapter_cfg = LUInWorldConfig(
            latent_dim=64,
            hear_radius=4,
            enable_multi_hop=True,
            enable_compositional_grammar=True,
            enable_tom=True,
            enable_deliberation=True,
            enable_dialects=True,
            enable_trade_contracts=True,
            trade_agreement_threshold=0.40,
            market_point=(8, 8),
            market_radius=4,
            enable_governance=True,
            enable_consortium_contracts=True,
            consortium_agreement_threshold=0.40,
            enable_writing=True,
            enable_arithmetic=True,
            read_inscription_radius=4.0,
            epigenetic_prior_boost=5.0,
            # Phase 7 Toggles
            enable_diplomacy=enable_diplomacy,
            enable_meta_grammar=enable_diplomacy,
            federation_monument_x=8.0,
            federation_monument_y=8.0,
            treaty_cooperation_bonus=2.5,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents de colonie (Bûcherons, Fermiers, Mineurs)
        for i in range(6):
            model = MambaAgent(
                num_inputs=agri_cfg.agent.num_inputs,
                num_outputs=agri_cfg.agent.num_outputs,
                isocaloric=True
            )
            # Dispersion autour du marché et du monument central (8, 8)
            ox = int(np.clip(8 + np.random.randint(-2, 3), 1, 14))
            oy = int(np.clip(8 + np.random.randint(-2, 3), 1, 14))
            ag = world.add_agent(model, x=ox, y=oy, energy=45.0)

            # Dotation d'inventaire spécialisé
            if i % 3 == 0:
                ag["inventory"] = [{"type": "WOOD", "weight": 1.0}]
            elif i % 3 == 1:
                ag["inventory"] = [{"type": "FOOD", "weight": 0.5}]
            else:
                ag["inventory"] = [{"type": "ORE", "weight": 2.0}]

        living_ticks = 0
        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0

        # Remplacement démographique (Novices réguliers)
        for t in range(ticks_per_era):
            if len(world.agents) == 0:
                break
            living_ticks += 1

            # Tous les 10 ticks, un nouvel arrivant intègre la biosphère
            if t > 0 and t % 10 == 0 and len(world.agents) < 8:
                novice_model = MambaAgent(
                    num_inputs=agri_cfg.agent.num_inputs,
                    num_outputs=agri_cfg.agent.num_outputs,
                    isocaloric=True
                )
                nx = int(np.clip(8 + np.random.randint(-1, 2), 1, 14))
                ny = int(np.clip(8 + np.random.randint(-1, 2), 1, 14))
                new_ag = world.add_agent(novice_model, x=nx, y=ny, energy=40.0)
                inv_types = ["WOOD", "FOOD", "ORE"]
                new_ag["inventory"] = [{"type": inv_types[t % 3], "weight": 1.0}]

            # Pas de simulation
            step_stats = world.step()
            lu_stats = getattr(world, "last_lu_stats", {})
            era_trades += lu_stats.get("tick_trades", 0)
            era_consortiums += lu_stats.get("tick_consortiums", 0)
            era_metal_tools += lu_stats.get("metal_tools_produced", 0)

            if len(world.agents) == 0:
                break

        survivals.append(living_ticks)
        total_trades.append(era_trades)
        total_consortiums.append(era_consortiums)
        total_metal_tools.append(era_metal_tools)
        treaties_ratified_list.append(adapter.treaties_ratified_count)
        meta_rules_list.append(adapter.meta_rules_compiled_count)
        protections_list.append(adapter.constitutional_protections_count)

        era_energies = [float(a.get("energy", 0.0)) for a in world.agents if not np.isnan(a.get("energy", 0.0))]
        final_energies.append(float(np.mean(era_energies)) if era_energies else float("nan"))

    return {
        "eras": eras,
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_final_energy": float(np.nanmean(final_energies)),
        "mean_trades_settled": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_treaties_ratified": float(np.mean(treaties_ratified_list)),
        "mean_meta_rules": float(np.mean(meta_rules_list)),
        "mean_constitutional_protections": float(np.mean(protections_list)),
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 7 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Ères Baseline (Sans Fédération) vs 30 Ères Intervention (Fédération Diplomatique & RSI)")
    print("=" * 80)

    print("\n[1/2] Exécution de la Baseline (30 Ères sans fédération diplomatique)...")
    base_metrics = simulate_campaign_phase7(enable_diplomacy=False, eras=30, ticks_per_era=30, seed=42)

    print("\n[2/2] Exécution de l'Intervention (30 Ères avec fédération & macro-règles RSI)...")
    interv_metrics = simulate_campaign_phase7(enable_diplomacy=True, eras=30, ticks_per_era=30, seed=42)

    print("\n" + "=" * 80)
    print("📊 RÉSULTATS COMPARATIFS SUR 60 ÈRES DE SIMULATION")
    print("=" * 80)
    print(f"{'Métrique':<38} | {'Baseline (30 ères)':<20} | {'Intervention (30 ères)':<22} | {'Delta':<10}")
    print("-" * 98)

    delta_surv = interv_metrics['mean_survival_ticks'] - base_metrics['mean_survival_ticks']
    delta_energy = interv_metrics['mean_final_energy'] - base_metrics['mean_final_energy']
    delta_trades = interv_metrics['mean_trades_settled'] - base_metrics['mean_trades_settled']
    delta_consort = interv_metrics['mean_consortiums'] - base_metrics['mean_consortiums']
    delta_tools = interv_metrics['mean_metal_tools'] - base_metrics['mean_metal_tools']

    print(f"{'Survie moyenne (ticks)':<38} | {base_metrics['mean_survival_ticks']:<20.2f} | {interv_metrics['mean_survival_ticks']:<22.2f} | {delta_surv:+.2f}")
    print(f"{'Énergie finale moyenne (pts)':<38} | {base_metrics['mean_final_energy']:<20.2f} | {interv_metrics['mean_final_energy']:<22.2f} | {delta_energy:+.2f}")
    print(f"{'Contrats de troc conclus':<38} | {base_metrics['mean_trades_settled']:<20.2f} | {interv_metrics['mean_trades_settled']:<22.2f} | {delta_trades:+.2f}")
    print(f"{'Consortiums tripartites scellés':<38} | {base_metrics['mean_consortiums']:<20.2f} | {interv_metrics['mean_consortiums']:<22.2f} | {delta_consort:+.2f}")
    print(f"{'Outils métalliques forgés':<38} | {base_metrics['mean_metal_tools']:<20.2f} | {interv_metrics['mean_metal_tools']:<22.2f} | {delta_tools:+.2f}")
    print(f"{'Traités fédéraux ratifiés / ère':<38} | {base_metrics['mean_treaties_ratified']:<20.2f} | {interv_metrics['mean_treaties_ratified']:<22.2f} | {interv_metrics['mean_treaties_ratified']:+.2f}")
    print(f"{'Protections constitutionnelles / ère':<38} | {base_metrics['mean_constitutional_protections']:<20.2f} | {interv_metrics['mean_constitutional_protections']:<22.2f} | {interv_metrics['mean_constitutional_protections']:+.2f}")
    print("=" * 80)

    # Règle de décision : Commandement 15 (PIU)
    # Score composite de bien-être sociétal
    score_base = base_metrics['mean_final_energy'] + base_metrics['mean_survival_ticks'] * 0.5 + base_metrics['mean_trades_settled'] * 0.1
    score_interv = interv_metrics['mean_final_energy'] + interv_metrics['mean_survival_ticks'] * 0.5 + interv_metrics['mean_trades_settled'] * 0.1

    print(f"\nScore Sociologique Composite (Énergie + Survie + Échanges) :")
    print(f"  - Baseline     : {score_base:.2f}")
    print(f"  - Intervention : {score_interv:.2f}")
    print(f"  - Différentiel : {score_interv - score_base:+.2f}")

    if score_interv >= score_base:
        print("\n✅ VERDICT : INNOVATION VALIDÉE (Score Intervention >= Score Baseline).")
        print("   Conformément au Commandement 15, la Phase 7 franchit le cap de recevabilité sociologique.")
        return 0
    else:
        print("\n❌ VERDICT : RÉGRESSION SOCIOLOGIQUE. L'intervention doit être rejetée/revertée.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
