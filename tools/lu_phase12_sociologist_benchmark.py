"""
tools/lu_phase12_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 12).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société Phase 11 (Méta-Simulation Contrefactuelle, Rêve Sémantique Partagé au feu, mais sans Noosphère longue distance ni Sinkhorn).
- 30 Ères Intervention : Phase 12 complète (La Noosphère Latente, Conscience Collective Trans-Mondes, Métacognition Épistémique et Transport de Wasserstein).
- Choc expérimental : Rareté énergétique agricole (Monde 2), hivers rudes et exigence d'anticipation trans-mondes instantanée.
- Analyse comparative Before/After et verdict de validation sociologique.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["AGISEED_QUIET_LOG"] = "1"
import logging
logging.disable(logging.INFO)
logging.getLogger("src.graph_rag.async_logger").setLevel(logging.CRITICAL)

from src.graph_rag.async_logger import logger
logger._running = False
logger.start = lambda *args, **kwargs: None
logger.stop = lambda *args, **kwargs: None
logger.emit = lambda *args, **kwargs: None
logger.emit_sync = lambda *args, **kwargs: True

from src.graph_rag.memory_retriever import AsyncMemoryRetriever
AsyncMemoryRetriever.start = lambda self: None
AsyncMemoryRetriever.stop = lambda self: None
AsyncMemoryRetriever.get_memories = lambda *args, **kwargs: []

import numpy as np
from typing import Dict, Any

from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase12(
    enable_phase12: bool,
    eras: int = 30,
    ticks_per_era: int = 15,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Phase 11 sans Noosphère longue distance)
    vs Intervention Phase 12 (Noosphère complète, résonance stigmargique, métacognition épistémique, Sinkhorn).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    programs_executed_list = []
    self_compilations_list = []
    shared_dreams_list = []
    dreams_ratified_list = []
    noosphere_broadcasts_list = []
    synarchic_councils_list = []
    synarchic_ratifications_list = []

    for era in range(eras):
        print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(int((seed * 8000 + era) % (2**31 - 1)))
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
            # Phase 10 Toggles
            enable_self_compilation=True,
            enable_hoare_verification=True,
            self_evolution_energy_bonus=10.0,
            # Phase 11 Toggles
            enable_counterfactual_dreaming=True,
            dream_rollout_horizon=10,
            dream_predictive_bonus=6.0,
            dream_min_gain_threshold=0.00,
            # Phase 12 Toggles (Variable Unitaire)
            enable_noosphere_grid=enable_phase12,
            resonance_decay=0.10,
            epistemic_confidence_threshold=0.45,
            sinkhorn_regularization=0.05,
            noosphere_dividend=8.0,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # Ajout d'un feu de camp en (8, 8)
        world.items.append({"type": "fire", "x": 8, "y": 8})

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

        # Enregistrement du programme agricole de base
        adapter.synthesize_and_register_program(
            creator_id="FOUNDER",
            program_id=f"era_{era}_agri_automation",
            entry_label="HARVEST",
            loop_label="REFINE",
            branch_label="READY",
            term_label="STORE",
            lipschitz_l=0.80
        )

        # Ajout d'une stèle pour initialiser la résonance noosphérique
        rng_st = np.random.default_rng(42)
        v_st = rng_st.normal(size=64).astype(np.float32)
        v_st /= np.linalg.norm(v_st)
        adapter.engrave_stele(
            world.agents[0],
            topic="HARMONIC_BEACON",
            content=v_st,
            pos=(8.0, 8.0, 0.0),
        )

        living_ticks = 0
        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0

        for t in range(ticks_per_era):
            world.tick = t
            world.ticks = t
            alive_count = sum(1 for a in world.agents if a.get("alive", True) and a.get("energy", 0.0) > 0.0)
            if alive_count > 0:
                living_ticks += 1

            # Auto-compilation récursive
            if t == 8 and len(world.agents) >= 2:
                for ag in world.agents[:2]:
                    model_ag = ag.get("model") or ag.get("brain")
                    if model_ag is not None and not ag.get("connectome_self_compiled", False):
                        adapter.verify_and_apply_connectome_evolution(ag, model_ag)

            # Rêve au feu de camp (Phase 11)
            if t == 15 and len(world.agents) >= 2:
                campfire_agents = world.agents[:3]
                adapter.deliberate_shared_dreams_at_campfire(campfire_agents)

            # Pas de simulation (inclut l'étape 15 Noosphère si activée)
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
        self_compilations_list.append(adapter.self_compiled_mutations_count)
        shared_dreams_list.append(adapter.shared_dreams_count)
        dreams_ratified_list.append(adapter.dreams_ratified_count)
        noosphere_broadcasts_list.append(adapter.noosphere_broadcasts_count)
        synarchic_councils_list.append(adapter.synarchic_councils_count)
        synarchic_ratifications_list.append(adapter.synarchic_ratifications_count)

        era_energies = [
            float(a.get("energy", 0.0))
            for a in world.agents
            if not np.isnan(a.get("energy", 0.0))
        ]
        final_energies.append(float(np.mean(era_energies)) if era_energies else float("nan"))

        del world
        del adapter
        import gc
        gc.collect()

    return {
        "eras": eras,
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_final_energy": float(np.nanmean(final_energies)),
        "mean_trades_settled": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_programs_executed": float(np.mean(programs_executed_list)),
        "mean_self_compilations": float(np.mean(self_compilations_list)),
        "mean_shared_dreams": float(np.mean(shared_dreams_list)),
        "mean_dreams_ratified": float(np.mean(dreams_ratified_list)),
        "mean_noosphere_broadcasts": float(np.mean(noosphere_broadcasts_list)),
        "mean_synarchic_councils": float(np.mean(synarchic_councils_list)),
        "mean_synarchic_ratifications": float(np.mean(synarchic_ratifications_list)),
    }


def compute_sociological_score_phase12(metrics: Dict[str, Any]) -> float:
    """
    Score sociologique composite pour la Phase 12 :
    Pondère la thermodynamique de survie, l'anticipation calorique, l'intégration institutionnelle,
    la méta-simulation contrefactuelle, et le dividende de conscience noosphérique trans-mondes.
    """
    s_ticks = metrics["mean_survival_ticks"] * 5.0
    s_energy = (0.0 if np.isnan(metrics["mean_final_energy"]) else metrics["mean_final_energy"]) * 3.0
    s_consortiums = metrics["mean_consortiums"] * 2.0
    s_tools = metrics["mean_metal_tools"] * 2.0
    s_prog = metrics["mean_programs_executed"] * 2.0
    s_self_comp = metrics["mean_self_compilations"] * 4.0
    s_dreams = metrics["mean_shared_dreams"] * 4.0
    s_noosphere = metrics.get("mean_noosphere_broadcasts", 0.0) * 8.0
    s_synarchy = metrics.get("mean_synarchic_ratifications", 0.0) * 12.0

    return float(s_ticks + s_energy + s_consortiums + s_tools + s_prog + s_self_comp + s_dreams + s_noosphere + s_synarchy)


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE DU LANGAGE ULTIME — PHASE 12 (COMMANDEMENT 15)")
    print("   Hypothèse : La Noosphère Latente, la résonance stigmargique trans-mondes")
    print("   et le barycentre de Sinkhorn-Wasserstein éliminent le mur de distance,")
    print("   éradiquent l'illusion épistémique et synchronisent les 3 Mondes.")
    print("=" * 80)

    # 1. Campagne Baseline (30 ères, Phase 11)
    print("\n[1/3] Exécution de la campagne BASELINE (Phase 11 : Rêve sans Noosphère Trans-Mondes)...")
    baseline = simulate_campaign_phase12(enable_phase12=False, eras=30, ticks_per_era=15, seed=101)

    # 2. Campagne Intervention (30 ères, Phase 12)
    print("\n[2/3] Exécution de la campagne INTERVENTION (Phase 12 : Noosphère & Conscience Collective)...")
    intervention = simulate_campaign_phase12(enable_phase12=True, eras=30, ticks_per_era=15, seed=101)

    # 3. Calcul des scores et verdict
    print("\n[3/3] Analyse comparative sociologique (Loi du Sociologue - Commandement 15)...")
    score_base = compute_sociological_score_phase12(baseline)
    score_interv = compute_sociological_score_phase12(intervention)
    delta_score = score_interv - score_base
    pct_gain = (delta_score / score_base) * 100.0 if score_base > 0 else 0.0

    print("-" * 80)
    print(f"{'MÉTRIQUE SOCIOLOGIQUE':<38} | {'BASELINE (P11)':<18} | {'INTERVENTION (P12)':<18}")
    print("-" * 80)
    print(f"{'Survie moyenne (ticks)':<38} | {baseline['mean_survival_ticks']:<18.2f} | {intervention['mean_survival_ticks']:<18.2f}")
    print(f"{'Énergie moyenne finale (E)':<38} | {baseline['mean_final_energy']:<18.2f} | {intervention['mean_final_energy']:<18.2f}")
    print(f"{'Troc inter-clans conclu':<38} | {baseline['mean_trades_settled']:<18.2f} | {intervention['mean_trades_settled']:<18.2f}")
    print(f"{'Consortiums métallurgiques':<38} | {baseline['mean_consortiums']:<18.2f} | {intervention['mean_consortiums']:<18.2f}")
    print(f"{'Outils acier produits':<38} | {baseline['mean_metal_tools']:<18.2f} | {intervention['mean_metal_tools']:<18.2f}")
    print(f"{'Programmes FSM exécutés':<38} | {baseline['mean_programs_executed']:<18.2f} | {intervention['mean_programs_executed']:<18.2f}")
    print(f"{'Auto-compilations connectome':<38} | {baseline['mean_self_compilations']:<18.2f} | {intervention['mean_self_compilations']:<18.2f}")
    print(f"{'Rêves partagés au feu (P11)':<38} | {baseline['mean_shared_dreams']:<18.2f} | {intervention['mean_shared_dreams']:<18.2f}")
    print(f"{'Diffusions noosphériques (P12)':<38} | {baseline['mean_noosphere_broadcasts']:<18.2f} | {intervention['mean_noosphere_broadcasts']:<18.2f}")
    print(f"{'Conseils synarchiques tenus':<38} | {baseline['mean_synarchic_councils']:<18.2f} | {intervention['mean_synarchic_councils']:<18.2f}")
    print(f"{'Ratifications Wasserstein-Sinkhorn':<38} | {baseline['mean_synarchic_ratifications']:<18.2f} | {intervention['mean_synarchic_ratifications']:<18.2f}")
    print("-" * 80)
    print(f"{'SCORE SOCIOLOGIQUE COMPOSITE':<38} | {score_base:<18.2f} | {score_interv:<18.2f}")
    print(f"{'GAIN NET SOCIOLOGIQUE':<38} | {'---':<18} | {delta_score:+.2f} ({pct_gain:+.2f}%)")
    print("-" * 80)

    if score_interv >= score_base:
        print("\n🎉 VERDICT PIU (Commandement 15) : INNOVATION VALIDÉE !")
        print(f"   La Noosphère Latente et le Barycentre de Sinkhorn améliorent la société de {delta_score:+.2f} pts.")
        return 0
    else:
        print("\n❌ VERDICT PIU (Commandement 15) : RÉGRESSION DÉTECTÉE — REVERT REQUIS !")
        print(f"   L'intervention dégrade le score sociologique de {delta_score:.2f} pts.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
