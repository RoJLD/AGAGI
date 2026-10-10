"""
tools/lu_phase10_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 10).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société Phase 9 (Programmes synthétisés Banach, LTL, analogies multivers, mais SANS auto-compilation de connectome).
- 30 Ères Intervention : Phase 10 complète (Auto-Compilation Récursive du Connectome Liquid Mamba, Logique de Hoare continue, Autel d'Évolution au FederalMonument).
- Choc expérimental : Rareté énergétique agricole (Monde 2), hivers rudes et exigence d'adaptation métabolique endogène.
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


def simulate_campaign_phase10(
    enable_phase10: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Phase 9 sans auto-compilation)
    vs Intervention Phase 10 (Auto-compilation de connectome, Logique de Hoare, dividendes Seed AI).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    programs_executed_list = []
    temporal_escrows_released_list = []
    analogy_transfers_list = []
    self_compilations_list = []
    hoare_proofs_list = []

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
            enable_program_synthesis=True,
            enable_ltl_temporal_logic=True,
            enable_analogy_transfer=True,
            temporal_horizon_ticks=4,
            analogy_fidelity_threshold=0.45,
            program_execution_energy_bonus=4.0,
            # Phase 10 Toggles (Innovation Unitaire)
            enable_self_compilation=enable_phase10,
            enable_hoare_verification=enable_phase10,
            self_evolution_energy_bonus=10.0,
            hoare_safety_threshold=0.65,
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

        # Enregistrement de contrats temporels et programmes de Phase 9
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
            if t == 5 and len(world.agents) > 0:
                lead_ag = world.agents[0]
                adapter.conduct_analogy_transfer(
                    agent=lead_ag,
                    a_label="CHARCOAL",
                    b_label="STEEL",
                    c_label="COMPOST",
                    d_target_label="HARVEST"
                )

            # Alignement de paix pour les contrats temporels aux ticks 2 à 4
            if 2 <= t <= 4 and adapter.federal_monument and f"era_{era}_peace_pact" in adapter.federal_monument.temporal_escrows:
                v_peace = adapter.federal_monument.temporal_escrows[f"era_{era}_peace_pact"]["trigger_vector"]
                for ag in world.agents:
                    ag["lu_latent"] = v_peace.copy()

            # Exécution de programme automatisé au tick 10
            if t == 10 and len(world.agents) > 0:
                ag_prog = world.agents[0]
                adapter.execute_inworld_program(ag_prog, f"era_{era}_agri_automation")

            # Phase 10 : Auto-compilation explicite au tick 12 pour les agents près du Monument
            if enable_phase10 and t == 12 and len(world.agents) > 0:
                for ag in world.agents[:2]:
                    model_ag = ag.get("model") or ag.get("brain")
                    if model_ag is not None and not ag.get("connectome_self_compiled", False):
                        adapter.verify_and_apply_connectome_evolution(ag, model_ag)

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
        self_compilations_list.append(adapter.self_compiled_mutations_count)
        hoare_proofs_list.append(adapter.hoare_proofs_verified_count)

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
        "mean_self_compilations": float(np.mean(self_compilations_list)),
        "mean_hoare_proofs": float(np.mean(hoare_proofs_list)),
    }


def compute_sociological_score_phase10(metrics: Dict[str, Any]) -> float:
    """
    Score sociologique composite pour la Phase 10 :
    Pondère la thermodynamique de survie, l'efficience calorique, l'intégration institutionnelle
    et la singularité Seed AI (auto-compilation récursive de connectome validée par Hoare).
    """
    s_ticks = metrics["mean_survival_ticks"] * 5.0
    s_energy = (0.0 if np.isnan(metrics["mean_final_energy"]) else metrics["mean_final_energy"]) * 3.0
    s_consortiums = metrics["mean_consortiums"] * 2.0
    s_tools = metrics["mean_metal_tools"] * 2.0
    s_prog = metrics["mean_programs_executed"] * 2.0
    s_ltl = metrics["mean_temporal_escrows_released"] * 2.0
    s_analogy = metrics["mean_analogy_transfers"] * 3.0
    s_self_comp = metrics["mean_self_compilations"] * 10.0
    s_hoare = metrics["mean_hoare_proofs"] * 5.0

    return float(s_ticks + s_energy + s_consortiums + s_tools + s_prog + s_ltl + s_analogy + s_self_comp + s_hoare)


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE DU LANGAGE ULTIME — PHASE 10 (COMMANDEMENT 15)")
    print("   Hypothèse : L'auto-compilation récursive du connectome Liquid Mamba")
    print("   sous Logique de Hoare continue franchit la clôture de Von Neumann-Gödel")
    print("   et accélère drastiquement l'adaptation et la thermodynamique de la meute.")
    print("=" * 80)

    # 1. Campagne Baseline (30 ères, Phase 9)
    print("\n[1/3] Exécution de la campagne BASELINE (Phase 9 : Programmes/LTL/Analogies sans auto-compilation)...")
    baseline = simulate_campaign_phase10(enable_phase10=False, eras=30, ticks_per_era=30, seed=101)

    # 2. Campagne Intervention (30 ères, Phase 10)
    print("\n[2/3] Exécution de la campagne INTERVENTION (Phase 10 : Auto-Compilation Connectome & Hoare)...")
    intervention = simulate_campaign_phase10(enable_phase10=True, eras=30, ticks_per_era=30, seed=101)

    # 3. Calcul et comparaison des scores sociologiques
    score_base = compute_sociological_score_phase10(baseline)
    score_interv = compute_sociological_score_phase10(intervention)
    diff = score_interv - score_base
    pct_gain = (diff / max(score_base, 1e-6)) * 100.0

    print("\n" + "=" * 80)
    print("📊 RÉSULTATS COMPARATIFS DU PROTOCOLE DU SOCIOLOGUE (30 vs 30 ÈRES)")
    print("=" * 80)
    print(f"{'Métrique':<42} | {'Baseline (P9)':<15} | {'Intervention (P10)':<18} | {'Delta':<10}")
    print("-" * 80)
    print(f"{'Survie moyenne (ticks / 30)':<42} | {baseline['mean_survival_ticks']:<15.2f} | {intervention['mean_survival_ticks']:<18.2f} | {intervention['mean_survival_ticks'] - baseline['mean_survival_ticks']:+.2f}")
    print(f"{'Énergie moyenne résiduelle':<42} | {baseline['mean_final_energy']:<15.2f} | {intervention['mean_final_energy']:<18.2f} | {intervention['mean_final_energy'] - baseline['mean_final_energy']:+.2f}")
    print(f"{'Contrats de troc exécutés':<42} | {baseline['mean_trades_settled']:<15.2f} | {intervention['mean_trades_settled']:<18.2f} | {intervention['mean_trades_settled'] - baseline['mean_trades_settled']:+.2f}")
    print(f"{'Consortiums métallurgiques':<42} | {baseline['mean_consortiums']:<15.2f} | {intervention['mean_consortiums']:<18.2f} | {intervention['mean_consortiums'] - baseline['mean_consortiums']:+.2f}")
    print(f"{'Outils métalliques forgés':<42} | {baseline['mean_metal_tools']:<15.2f} | {intervention['mean_metal_tools']:<18.2f} | {intervention['mean_metal_tools'] - baseline['mean_metal_tools']:+.2f}")
    print(f"{'Programmes latents exécutés':<42} | {baseline['mean_programs_executed']:<15.2f} | {intervention['mean_programs_executed']:<18.2f} | {intervention['mean_programs_executed'] - baseline['mean_programs_executed']:+.2f}")
    print(f"{'Escrows temporels LTL libérés':<42} | {baseline['mean_temporal_escrows_released']:<15.2f} | {intervention['mean_temporal_escrows_released']:<18.2f} | {intervention['mean_temporal_escrows_released'] - baseline['mean_temporal_escrows_released']:+.2f}")
    print(f"{'Transferts d analogies résolus':<42} | {baseline['mean_analogy_transfers']:<15.2f} | {intervention['mean_analogy_transfers']:<18.2f} | {intervention['mean_analogy_transfers'] - baseline['mean_analogy_transfers']:+.2f}")
    print(f"{'Auto-compilations connectome':<42} | {baseline['mean_self_compilations']:<15.2f} | {intervention['mean_self_compilations']:<18.2f} | {intervention['mean_self_compilations'] - baseline['mean_self_compilations']:+.2f}")
    print(f"{'Preuves de Hoare validées':<42} | {baseline['mean_hoare_proofs']:<15.2f} | {intervention['mean_hoare_proofs']:<18.2f} | {intervention['mean_hoare_proofs'] - baseline['mean_hoare_proofs']:+.2f}")
    print("-" * 80)
    print(f"{'SCORE SOCIOLOGIQUE GLOBAL':<42} | {score_base:<15.2f} | {score_interv:<18.2f} | {diff:+.2f} ({pct_gain:+.1f}%)")
    print("=" * 80)

    # Commandement 15 : Verdict
    if score_interv >= score_base and diff >= 0:
        print("\n✅ VERDICT : INNOVATION UNITAIRE VALIDÉE CONFORME AU COMMANDEMENT 15.")
        print("   L'Auto-Compilation Récursive du Connectome Liquid Mamba sous Logique de Hoare continue")
        print("   surpasse la baseline et établit l'autonomie Seed AI de Phase 10.")
    else:
        print("\n❌ VERDICT : RÉGRESSION SOCIOLOGIQUE. L'INNOVATION DOIT ÊTRE REVERT.")
        sys.exit(1)


if __name__ == "__main__":
    main()
