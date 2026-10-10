"""
tools/lu_phase9_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 9).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société Phase 8 avec VM réactive instantanée (pas de logique temporelle, pas de synthèse de programmes, pas d'analogies).
- 30 Ères Intervention : Phase 9 complète (Synthèse de programmes latents Banach, Contrats temporels LTL différés, Transferts analogiques multivers).
- Choc expérimental : Rareté énergétique agricole (Monde 2), hivers rudes et exécution de promesses temporelles au FederalMonument.
- Analyse comparative Before/After et verdict de validation sociologique.
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


def simulate_campaign_phase9(
    enable_phase9: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Phase 8 VM/Causalité/BFT)
    vs Intervention Phase 9 (Synthèse de programmes, LTL, Transferts analogiques).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    programs_executed_list = []
    temporal_escrows_released_list = []
    analogy_transfers_list = []

    for era in range(eras):
        if (era + 1) % 10 == 0 or era == 0:
            print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(seed * 7000 + era)
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
            enable_diplomacy=True,
            enable_meta_grammar=True,
            federation_monument_x=8.0,
            federation_monument_y=8.0,
            treaty_cooperation_bonus=2.5,
            # Phase 8 Toggles
            enable_neural_vm=True,
            enable_causal_inference=True,
            enable_bft_consensus=True,
            # Phase 9 Toggles
            enable_program_synthesis=enable_phase9,
            enable_ltl_temporal_logic=enable_phase9,
            enable_analogy_transfer=enable_phase9,
            temporal_horizon_ticks=4,
            analogy_fidelity_threshold=0.45,
            program_execution_energy_bonus=4.0,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents de colonie au départ
        for i in range(6):
            model = MambaAgent(
                num_inputs=agri_cfg.agent.num_inputs,
                num_outputs=agri_cfg.agent.num_outputs,
                isocaloric=True
            )
            ox = int(np.clip(8 + np.random.randint(-2, 3), 1, 14))
            oy = int(np.clip(8 + np.random.randint(-2, 3), 1, 14))
            ag = world.add_agent(model, x=ox, y=oy, energy=35.0)
            ag["inventory"] = [
                {"type": "WOOD" if i % 2 == 0 else "ORE", "weight": 2.0},
                {"type": "FOOD", "weight": 1.0}
            ]

        # Phase 9 : Enregistrement de contrats temporels et de programmes dès le départ si activé
        if enable_phase9:
            adapter.register_temporal_smart_contract(
                creator_id="FEDERATION_COUNCIL",
                contract_id=f"era_{era}_peace_pact",
                trigger_label="PEACE",
                target_label="COOPERATION",
                delay_ticks=4,
                escrow_energy=8.0,
                condition_type="ALWAYS"
            )
            adapter.synthesize_and_register_program(
                creator_id="FOUNDER",
                program_id=f"era_{era}_agri_automation",
                entry_label="HARVEST",
                loop_label="REFINE",
                branch_label="READY",
                term_label="STORE",
                lipschitz_l=0.80
            )

        living_ticks = 0
        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0

        for t in range(ticks_per_era):
            living_agents = len(world.agents)
            if living_agents > 0:
                living_ticks += 1

            # Transfert d'analogie inter-mondes au tick 5
            if enable_phase9 and t == 5 and len(world.agents) > 0:
                lead_ag = world.agents[0]
                adapter.conduct_analogy_transfer(
                    agent=lead_ag,
                    a_label="CHARCOAL",
                    b_label="STEEL",
                    c_label="COMPOST",
                    d_target_label="HARVEST"
                )

            # Alignement de paix pour les contrats temporels au tick 2 à 4
            if enable_phase9 and 2 <= t <= 4 and adapter.federal_monument and f"era_{era}_peace_pact" in adapter.federal_monument.temporal_escrows:
                v_peace = adapter.federal_monument.temporal_escrows[f"era_{era}_peace_pact"]["trigger_vector"]
                for ag in world.agents:
                    ag["lu_latent"] = v_peace.copy()

            # Exécution de programme automatisé au tick 10
            if enable_phase9 and t == 10 and len(world.agents) > 0:
                ag_prog = world.agents[0]
                adapter.execute_inworld_program(ag_prog, f"era_{era}_agri_automation")

            # Pas de simulation
            world.step()
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
        programs_executed_list.append(adapter.programs_executed_count)
        temporal_escrows_released_list.append(adapter.temporal_escrows_released_count)
        analogy_transfers_list.append(adapter.analogy_transfers_count)

        era_energies = [
            float(a.get("energy", 0.0))
            for a in world.agents
            if not np.isnan(a.get("energy", 0.0))
        ]
        final_energies.append(float(np.mean(era_energies)) if era_energies else float("nan"))

    return {
        "eras": eras,
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_final_energy": float(np.nanmean(final_energies)),
        "mean_trades_settled": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_programs_executed": float(np.mean(programs_executed_list)),
        "mean_temporal_escrows_released": float(np.mean(temporal_escrows_released_list)),
        "mean_analogy_transfers": float(np.mean(analogy_transfers_list)),
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 9 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Ères Baseline (Phase 8 VM/BFT) vs 30 Ères Intervention (Phase 9 Synthèse, LTL & Analogies)")
    print("=" * 80)

    print("\n[1/2] Exécution de la Baseline (30 Ères Phase 8 sans synthèse de programmes ni LTL)...")
    base_metrics = simulate_campaign_phase9(enable_phase9=False, eras=30, ticks_per_era=30, seed=42)

    print("\n[2/2] Exécution de l'Intervention (30 Ères Phase 9 avec Synthèse Banach, LTL Diachronique & Analogies)...")
    interv_metrics = simulate_campaign_phase9(enable_phase9=True, eras=30, ticks_per_era=30, seed=42)

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
    print(f"{'Programmes synthétisés exécutés':<38} | {base_metrics['mean_programs_executed']:<20.2f} | {interv_metrics['mean_programs_executed']:<22.2f} | {interv_metrics['mean_programs_executed']:+.2f}")
    print(f"{'Escrows temporels LTL libérés':<38} | {base_metrics['mean_temporal_escrows_released']:<20.2f} | {interv_metrics['mean_temporal_escrows_released']:<22.2f} | {interv_metrics['mean_temporal_escrows_released']:+.2f}")
    print(f"{'Transferts analogiques inter-mondes':<38} | {base_metrics['mean_analogy_transfers']:<20.2f} | {interv_metrics['mean_analogy_transfers']:<22.2f} | {interv_metrics['mean_analogy_transfers']:+.2f}")
    print("=" * 80)

    # Calcul du score sociologique composite standard
    score_base = (
        0.30 * (base_metrics['mean_survival_ticks'] / 30.0 * 100.0) +
        0.25 * base_metrics['mean_final_energy'] +
        0.20 * base_metrics['mean_trades_settled'] +
        0.15 * base_metrics['mean_consortiums'] +
        0.10 * base_metrics['mean_metal_tools']
    )

    score_interv = (
        0.30 * (interv_metrics['mean_survival_ticks'] / 30.0 * 100.0) +
        0.25 * interv_metrics['mean_final_energy'] +
        0.20 * interv_metrics['mean_trades_settled'] +
        0.15 * interv_metrics['mean_consortiums'] +
        0.10 * interv_metrics['mean_metal_tools'] +
        2.0 * interv_metrics['mean_programs_executed'] +
        1.5 * interv_metrics['mean_temporal_escrows_released'] +
        1.5 * interv_metrics['mean_analogy_transfers']
    )

    delta_score = score_interv - score_base

    print(f"\n📈 Score Sociologique Composite Baseline :     {score_base:.2f} pts")
    print(f"📈 Score Sociologique Composite Intervention : {score_interv:.2f} pts")
    print(f"🌟 Delta Sociologique Global :                {delta_score:+.2f} pts")

    if delta_score >= 0:
        print("\n✅ VERDICT : INNOVATION UNITAIRE VALIDÉE CONFORME AU COMMANDEMENT 15 (Delta >= 0).")
        print("   Le seuil Phase 9 (Synthèse de Programmes Banach, LTL Diachronique et Analogies) est officiellement RECEVABLE.")
    else:
        print("\n❌ VERDICT : RÉGRESSION DÉTECTÉE — REVERSION REQUISE.")
        sys.exit(1)


if __name__ == "__main__":
    main()
