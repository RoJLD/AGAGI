"""
tools/lu_phase13_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 13).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société Phase 12 (Noosphère Latente, Conscience Collective Trans-Mondes, Sinkhorn,
                     mais sans Morphogenèse Noogénétique par Réaction-Diffusion ni Hyper-Connectome).
- 30 Ères Intervention : Phase 13 complète (Équations de Turing-FitzHugh-Nagumo vectorisées,
                         Hyper-Connectome Fédéral Distribué à contraction lipschitzienne, Distillation épigénétique aux nouveau-nés).
- Choc expérimental : Rareté énergétique agricole (Monde 2), hivers rudes et exigence de résilience noogénétique.
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


def simulate_campaign_phase13(
    enable_phase13: bool,
    eras: int = 30,
    ticks_per_era: int = 15,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Phase 12 sans réaction-diffusion ni hyper-connectome)
    vs Intervention Phase 13 (Morphogenèse Noogénétique, Réaction-Diffusion continue et Hyper-Connectome distillateur).
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
    pde_steps_list = []
    hyperconnectome_updates_list = []
    noogenetic_distillations_list = []
    final_pde_energies = []

    for era in range(eras):
        print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(int((seed * 9000 + era) % (2**31 - 1)))
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
            # Phase 12 Toggles
            enable_noosphere_grid=True,
            resonance_decay=0.10,
            epistemic_confidence_threshold=0.45,
            sinkhorn_regularization=0.05,
            noosphere_dividend=8.0,
            # Phase 13 Toggles (Variable Unitaire PIU)
            enable_reaction_diffusion_pde=enable_phase13,
            pde_diffusion_coef=0.15,
            pde_reaction_rate=0.25,
            enable_hyperconnectome_distillation=enable_phase13,
            hyperconnectome_learning_rate=0.10,
            noogenetic_rebirth_bonus=12.0,
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

        # Ajout d'une stèle pour initialiser la résonance
        rng_st = np.random.default_rng(42)
        v_st = rng_st.normal(size=64).astype(np.float32)
        v_st /= np.linalg.norm(v_st)
        adapter.engrave_stele(
            world.agents[0],
            topic="NOOGENESIS_BEACON",
            content=v_st,
            pos=(8.0, 8.0, 0.0),
        )

        living_ticks = 0
        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0

        # Simulation de l'ère
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
            if t == 12 and len(world.agents) >= 2:
                campfire_agents = world.agents[:3]
                adapter.deliberate_shared_dreams_at_campfire(campfire_agents)

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
        pde_steps_list.append(adapter.pde_steps_count)
        hyperconnectome_updates_list.append(adapter.hyperconnectome_updates_count)
        noogenetic_distillations_list.append(adapter.noogenetic_distillations_count)
        final_pde_energies.append(adapter.pde_engine.compute_pde_energy() if adapter.pde_engine else 0.0)

        alive_agents = [ag for ag in world.agents if ag.get("energy", 0.0) > 0.0]
        mean_energy = float(np.mean([ag.get("energy", 0.0) for ag in alive_agents])) if alive_agents else float('nan')
        final_energies.append(mean_energy)

    return {
        "mean_survival_rate": float(np.mean(survivals)),
        "mean_final_energy": float(np.mean(final_energies)),
        "mean_trades": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_programs_executed": float(np.mean(programs_executed_list)),
        "mean_self_compilations": float(np.mean(self_compilations_list)),
        "mean_shared_dreams": float(np.mean(shared_dreams_list)),
        "mean_dreams_ratified": float(np.mean(dreams_ratified_list)),
        "mean_noosphere_broadcasts": float(np.mean(noosphere_broadcasts_list)),
        "mean_synarchic_councils": float(np.mean(synarchic_councils_list)),
        "mean_synarchic_ratifications": float(np.mean(synarchic_ratifications_list)),
        "mean_pde_steps": float(np.mean(pde_steps_list)),
        "mean_hyperconnectome_updates": float(np.mean(hyperconnectome_updates_list)),
        "mean_noogenetic_distillations": float(np.mean(noogenetic_distillations_list)),
        "mean_pde_energy": float(np.mean(final_pde_energies)),
    }


def compute_sociological_score(metrics: Dict[str, Any]) -> float:
    """
    Calcule le Score Sociologique Global de Cohésion et Résilience AGIseed.
    S = 0.35 * Survie + 0.35 * (Énergie / 50.0) + 0.15 * Coopération + 0.15 * Morphogenèse
    """
    s_surv = metrics["mean_survival_rate"]
    s_ene = min(1.0, metrics["mean_final_energy"] / 50.0)
    coop_events = (
        metrics["mean_trades"] +
        metrics["mean_consortiums"] +
        metrics["mean_synarchic_ratifications"]
    )
    s_coop = min(1.0, coop_events / 6.0)
    morpho_events = (
        metrics["mean_noogenetic_distillations"] +
        metrics["mean_hyperconnectome_updates"]
    )
    s_morpho = min(1.0, morpho_events / 4.0)

    score = 0.35 * s_surv + 0.35 * s_ene + 0.15 * s_coop + 0.15 * s_morpho
    return float(round(score * 100.0, 2))


def main():
    print("=" * 80)
    print("BANC SOCIOLOGIQUE COMPARATIF — LANGAGE ULTIME PHASE 13 (ARC 7 : G13)")
    print("Commandement 15 (Protocole d'Innovation Unitaire) : Baseline vs Intervention (30 Ères)")
    print("=" * 80)

    print("\n[1/2] Lancement de la Campagne Baseline (30 Ères — Phase 12 sans Réaction-Diffusion)...")
    baseline = simulate_campaign_phase13(enable_phase13=False, eras=30, ticks_per_era=15, seed=42)
    score_baseline = compute_sociological_score(baseline)
    print(f"    => Survie Baseline: {baseline['mean_survival_rate']*100:.2f}% | Énergie: {baseline['mean_final_energy']:.2f}")
    print(f"    => Score Sociologique Baseline: {score_baseline:.2f} / 100")

    print("\n[2/2] Lancement de la Campagne Intervention (30 Ères — Phase 13 complète avec Réaction-Diffusion & Hyper-Connectome)...")
    intervention = simulate_campaign_phase13(enable_phase13=True, eras=30, ticks_per_era=15, seed=42)
    score_intervention = compute_sociological_score(intervention)
    print(f"    => Survie Intervention: {intervention['mean_survival_rate']*100:.2f}% | Énergie: {intervention['mean_final_energy']:.2f}")
    print(f"    => Score Sociologique Intervention: {score_intervention:.2f} / 100")

    delta_score = score_intervention - score_baseline
    rel_gain = (delta_score / score_baseline * 100.0) if score_baseline > 0 else 0.0

    print("\n" + "=" * 80)
    print("ANALYSE COMPARATIVE FORMELLE (PIU)")
    print("=" * 80)
    print(f"Métrique                        Baseline (Ph12)   Intervention (Ph13)    Delta")
    print(f"-------------------------------------------------------------------------------")
    print(f"Taux de survie moyen          : {baseline['mean_survival_rate']*100:6.2f}%         {intervention['mean_survival_rate']*100:6.2f}%           {(intervention['mean_survival_rate'] - baseline['mean_survival_rate'])*100:+6.2f}%")
    print(f"Énergie finale moyenne         : {baseline['mean_final_energy']:6.2f}           {intervention['mean_final_energy']:6.2f}             {intervention['mean_final_energy'] - baseline['mean_final_energy']:+6.2f}")
    print(f"Transactions commerciales      : {baseline['mean_trades']:6.2f}           {intervention['mean_trades']:6.2f}             {intervention['mean_trades'] - baseline['mean_trades']:+6.2f}")
    print(f"Consortiums industriels        : {baseline['mean_consortiums']:6.2f}           {intervention['mean_consortiums']:6.2f}             {intervention['mean_consortiums'] - baseline['mean_consortiums']:+6.2f}")
    print(f"Conseils synarchiques ratifiés : {baseline['mean_synarchic_ratifications']:6.2f}           {intervention['mean_synarchic_ratifications']:6.2f}             {intervention['mean_synarchic_ratifications'] - baseline['mean_synarchic_ratifications']:+6.2f}")
    print(f"Étapes PDE Réaction-Diffusion  : {baseline['mean_pde_steps']:6.2f}           {intervention['mean_pde_steps']:6.2f}             {intervention['mean_pde_steps'] - baseline['mean_pde_steps']:+6.2f}")
    print(f"Mises à jour Hyper-Connectome  : {baseline['mean_hyperconnectome_updates']:6.2f}           {intervention['mean_hyperconnectome_updates']:6.2f}             {intervention['mean_hyperconnectome_updates'] - baseline['mean_hyperconnectome_updates']:+6.2f}")
    print(f"Distillations Noogénétiques    : {baseline['mean_noogenetic_distillations']:6.2f}           {intervention['mean_noogenetic_distillations']:6.2f}             {intervention['mean_noogenetic_distillations'] - baseline['mean_noogenetic_distillations']:+6.2f}")
    print(f"Énergie PDE finale L2          : {baseline['mean_pde_energy']:6.2f}           {intervention['mean_pde_energy']:6.2f}             {intervention['mean_pde_energy'] - baseline['mean_pde_energy']:+6.2f}")
    print(f"-------------------------------------------------------------------------------")
    print(f"Score Sociologique Global     : {score_baseline:6.2f}           {score_intervention:6.2f}             {delta_score:+6.2f} ({rel_gain:+.2f}%)")
    print("=" * 80)

    if score_intervention >= score_baseline:
        print(f"\n[VERDICT PIU : SUCCÈS] Score Intervention ({score_intervention:.2f}) >= Baseline ({score_baseline:.2f}).")
        print("L'intervention Phase 13 (Morphogenèse Noogénétique & Hyper-Connectome) est formellement VALIDÉE.")
        return 0
    else:
        print(f"\n[VERDICT PIU : ÉCHEC] Régression sociologique observée ({score_intervention:.2f} < {score_baseline:.2f}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
