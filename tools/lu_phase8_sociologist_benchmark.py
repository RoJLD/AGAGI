"""
tools/lu_phase8_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 8).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Fédération Phase 7 déclarative avec contrats passifs et vulnérabilité aux déviations adversariales.
- 30 Ères Intervention : Phase 8 complète (Latent Neural VM d'escrow, Découverte causale Do-Calculus et Consensus Byzantin Sphérique).
- Choc expérimental : Pressions climatiques, agents byzantins injectant du bruit adversarial dans les votes et séquestre d'actifs énergétiques.
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


def simulate_campaign_phase8(
    enable_phase8: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Fédération Phase 7 déclarative) 
    vs Intervention Phase 8 (Neural VM, Causalité, BFT).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    smart_contracts_executed_list = []
    causal_discoveries_list = []
    bft_consensus_list = []
    byzantine_filtered_list = []

    for era in range(eras):
        if (era + 1) % 10 == 0 or era == 0:
            print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(seed * 5000 + era)
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
            enable_neural_vm=enable_phase8,
            enable_causal_inference=enable_phase8,
            enable_bft_consensus=enable_phase8,
            causal_ate_threshold=0.35,
            byzantine_tolerance_ratio=0.33,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents de colonie (dont 1 agent byzantin)
        for i in range(6):
            model = MambaAgent(
                num_inputs=agri_cfg.agent.num_inputs,
                num_outputs=agri_cfg.agent.num_outputs,
                isocaloric=True
            )
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

            # Agent byzantin simulé (index 5)
            if i == 5:
                ag["is_byzantine"] = True

        # Enregistrement d'un smart contract d'escrow in-world si Phase 8
        if enable_phase8:
            adapter.register_inworld_smart_contract(
                creator_id="FEDERATION_COUNCIL",
                contract_id=f"ESCROW_ERA_{era}",
                from_state_label="LAW",
                trigger_label="STEEL",
                to_state_label="PEACE",
                escrow_energy=4.0,
                activation_threshold=0.30
            )

        # Feu de camp central pour délibération collective
        world.items.append({"type": "fire", "name": "fire", "x": 8, "y": 8})

        living_ticks = 0
        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0

        for t in range(ticks_per_era):
            if len(world.agents) == 0:
                break
            living_ticks += 1

            # L'agent byzantin injecte un vecteur antipodal adversarial
            for ag in world.agents:
                if ag.get("is_byzantine", False):
                    ag["lu_latent"] = -np.ones(64, dtype=np.float32) / np.sqrt(64)

            # Nouveaux arrivants tous les 10 ticks
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

            # Activité causale de l'Académie scientifique au tick 12
            if enable_phase8 and t == 12 and len(world.agents) >= 2:
                acad_ag = world.agents[0]
                adapter.conduct_causal_experiment(
                    agent=acad_ag,
                    cause_label="FIRE",
                    effect_label="STEEL",
                    n_trials=8
                )

            # L'agent 0 apporte le trigger STEEL au FederalMonument au tick 8
            if enable_phase8 and t == 8 and len(world.agents) > 0:
                agent_trig = world.agents[0]
                v_steel = adapter.grammar.ROLE_FORGE_OUTPUT
                adapter.execute_inworld_smart_contract(agent_trig, v_steel)

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
        smart_contracts_executed_list.append(adapter.smart_contracts_executed_count)
        causal_discoveries_list.append(adapter.causal_hypotheses_validated_count)
        bft_consensus_list.append(adapter.bft_consensus_events_count)
        byzantine_filtered_list.append(adapter.bft_byzantine_mitigated_count)

        # Mesure d'énergie sur les agents citoyens loyaux (non-byzantins)
        era_energies = [
            float(a.get("energy", 0.0))
            for a in world.agents
            if not a.get("is_byzantine", False) and not np.isnan(a.get("energy", 0.0))
        ]
        final_energies.append(float(np.mean(era_energies)) if era_energies else float("nan"))

    return {
        "eras": eras,
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_final_energy": float(np.nanmean(final_energies)),
        "mean_trades_settled": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_smart_contracts_executed": float(np.mean(smart_contracts_executed_list)),
        "mean_causal_discoveries": float(np.mean(causal_discoveries_list)),
        "mean_bft_consensus": float(np.mean(bft_consensus_list)),
        "mean_byzantine_filtered": float(np.mean(byzantine_filtered_list)),
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 8 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Ères Baseline (Phase 7 passif) vs 30 Ères Intervention (Phase 8 VM, Causalité & BFT)")
    print("=" * 80)

    print("\n[1/2] Exécution de la Baseline (30 Ères avec contrats déclaratifs & vulnérabilité byzantine)...")
    base_metrics = simulate_campaign_phase8(enable_phase8=False, eras=30, ticks_per_era=30, seed=42)

    print("\n[2/2] Exécution de l'Intervention (30 Ères avec Latent Neural VM, Do-Calculus & Consensus BFT)...")
    interv_metrics = simulate_campaign_phase8(enable_phase8=True, eras=30, ticks_per_era=30, seed=42)

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
    print(f"{'Smart Contracts exécutés / ère':<38} | {base_metrics['mean_smart_contracts_executed']:<20.2f} | {interv_metrics['mean_smart_contracts_executed']:<22.2f} | {interv_metrics['mean_smart_contracts_executed']:+.2f}")
    print(f"{'Découvertes causales / ère':<38} | {base_metrics['mean_causal_discoveries']:<20.2f} | {interv_metrics['mean_causal_discoveries']:<22.2f} | {interv_metrics['mean_causal_discoveries']:+.2f}")
    print(f"{'Consensus BFT aboutis / ère':<38} | {base_metrics['mean_bft_consensus']:<20.2f} | {interv_metrics['mean_bft_consensus']:<22.2f} | {interv_metrics['mean_bft_consensus']:+.2f}")
    print(f"{'Vecteurs byzantins isolés / ère':<38} | {base_metrics['mean_byzantine_filtered']:<20.2f} | {interv_metrics['mean_byzantine_filtered']:<22.2f} | {interv_metrics['mean_byzantine_filtered']:+.2f}")
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
        print("   Conformément au Commandement 15, la Phase 8 franchit le cap de recevabilité sociologique.")
        return 0
    else:
        print("\n❌ VERDICT : RÉGRESSION SOCIOLOGIQUE. L'intervention doit être rejetée/revertée.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
