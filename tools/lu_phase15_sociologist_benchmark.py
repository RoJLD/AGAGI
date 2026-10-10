"""
tools/lu_phase15_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 15).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société Phase 14 (Singularité Autopoïétique, Méta-Langage Holographique Universel,
                     sans Intrication Sémantique Non-Locale ni Démiurgie Multivers).
- 30 Ères Intervention : Phase 15 complète (Intrication Non-Locale de Bell, Rétrocausalité de Wheeler-Feynman,
                         Collapse Démiurgique et Grand Dividende Démiurgique +25.0 E).
- Choc expérimental : Rareté énergétique agricole (Monde 2), hivers rudes et exigence d'alignement civilisationnel démiurgique.
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

from src.metaprog.lu_symbolic_bridge import FederalDiplomaticBridge
_orig_fdb_init = FederalDiplomaticBridge.__init__
def _safe_fdb_init(self, seed=42, db=None, grammar=None):
    _orig_fdb_init(self, seed=seed, db=None, grammar=grammar)
FederalDiplomaticBridge.__init__ = _safe_fdb_init

import numpy as np

from typing import Dict, Any

from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase15(
    enable_phase15: bool,
    eras: int = 30,
    ticks_per_era: int = 15,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Phase 14 sans intrication démiurgique)
    vs Intervention Phase 15 (Intrication Sémantique Non-Locale, Rétrocausalité Téléologique & Démiurgie Multivers).
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
    autopoietic_steps_list = []
    holographic_projections_list = []
    teleological_convergences_list = []
    singularity_dividends_list = []
    demiurgic_steps_list = []
    entangled_pairs_list = []
    demiurgic_dividends_list = []

    for era in range(eras):
        print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(int((seed * 9500 + era) % (2**31 - 1)))
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
            dream_rollout_horizon=4,
            dream_predictive_bonus=6.0,
            dream_min_gain_threshold=0.00,

            # Phase 12 Toggles
            enable_noosphere_grid=True,
            resonance_decay=0.10,
            epistemic_confidence_threshold=0.45,
            sinkhorn_regularization=0.05,
            noosphere_dividend=8.0,
            # Phase 13 Toggles
            enable_reaction_diffusion_pde=True,
            pde_diffusion_coef=0.15,
            pde_reaction_rate=0.25,
            enable_hyperconnectome_distillation=True,
            hyperconnectome_learning_rate=0.10,
            noogenetic_rebirth_bonus=12.0,
            # Phase 14 Toggles
            enable_autopoietic_singularity=True,
            holographic_projection_ratio=0.40,
            teleological_attractor_force=0.25,
            autopoietic_entropy_threshold=0.65,
            singularity_dividend_bonus=20.0,
            # Phase 15 Toggles (Variable Unitaire PIU)
            enable_demiurgic_multiverse=enable_phase15,
            entanglement_coupling_strength=0.35,
            retrocausal_influence_rate=0.20,
            bell_violation_threshold=2.05,
            demiurgic_dividend_bonus=25.0,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # Ajout d'un feu de camp en (8, 8)
        world.items.append({"type": "fire", "x": 8, "y": 8})

        # 4 agents de colonie au départ
        for i in range(4):
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

        # Ajout d'une stèle
        rng_st = np.random.default_rng(42)
        v_st = rng_st.normal(size=64).astype(np.float32)
        v_st /= np.linalg.norm(v_st)
        adapter.engrave_stele(
            world.agents[0],
            topic="AUTOPOIESIS_BEACON",
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
        autopoietic_steps_list.append(adapter.autopoietic_steps_count)
        holographic_projections_list.append(adapter.holographic_projections_count)
        teleological_convergences_list.append(adapter.teleological_convergences_count)
        singularity_dividends_list.append(adapter.singularity_dividends_count)
        demiurgic_steps_list.append(adapter.demiurgic_steps_count)
        entangled_pairs_list.append(adapter.entangled_pairs_count)
        demiurgic_dividends_list.append(adapter.demiurgic_dividends_count)

        living_agents = [a for a in world.agents if a.get("alive", True) and a.get("energy", 0.0) > 0.0]
        if living_agents:
            final_energies.append(float(np.mean([a["energy"] for a in living_agents])))
        else:
            final_energies.append(float('nan'))

    return {
        "mean_survival": float(np.mean(survivals)) if survivals else float('nan'),
        "mean_energy": float(np.nanmean(final_energies)) if final_energies else float('nan'),
        "mean_trades": float(np.mean(total_trades)) if total_trades else float('nan'),
        "mean_consortiums": float(np.mean(total_consortiums)) if total_consortiums else float('nan'),
        "mean_metal_tools": float(np.mean(total_metal_tools)) if total_metal_tools else float('nan'),
        "mean_programs_exec": float(np.mean(programs_executed_list)) if programs_executed_list else float('nan'),
        "mean_self_compilations": float(np.mean(self_compilations_list)) if self_compilations_list else float('nan'),
        "mean_shared_dreams": float(np.mean(shared_dreams_list)) if shared_dreams_list else float('nan'),
        "mean_noosphere_broadcasts": float(np.mean(noosphere_broadcasts_list)) if noosphere_broadcasts_list else float('nan'),
        "mean_synarchic_ratifications": float(np.mean(synarchic_ratifications_list)) if synarchic_ratifications_list else float('nan'),
        "mean_pde_steps": float(np.mean(pde_steps_list)) if pde_steps_list else float('nan'),
        "mean_hyperconnectome_updates": float(np.mean(hyperconnectome_updates_list)) if hyperconnectome_updates_list else float('nan'),
        "mean_noogenetic_distillations": float(np.mean(noogenetic_distillations_list)) if noogenetic_distillations_list else float('nan'),
        "mean_autopoietic_steps": float(np.mean(autopoietic_steps_list)) if autopoietic_steps_list else float('nan'),
        "mean_holographic_projections": float(np.mean(holographic_projections_list)) if holographic_projections_list else float('nan'),
        "mean_teleological_convergences": float(np.mean(teleological_convergences_list)) if teleological_convergences_list else float('nan'),
        "mean_singularity_dividends": float(np.mean(singularity_dividends_list)) if singularity_dividends_list else float('nan'),
        "mean_demiurgic_steps": float(np.mean(demiurgic_steps_list)) if demiurgic_steps_list else float('nan'),
        "mean_entangled_pairs": float(np.mean(entangled_pairs_list)) if entangled_pairs_list else float('nan'),
        "mean_demiurgic_dividends": float(np.mean(demiurgic_dividends_list)) if demiurgic_dividends_list else float('nan'),
    }


def compute_sociological_score_phase15(metrics: Dict[str, Any]) -> float:
    """
    Score sociologique composite sous Commandement 15 pour la Phase 15 :
    Équilibre Survie (x20), Énergie vitale (x3), Vitalité Synarchique (x5),
    Distillations Noogénétiques (x2), Clôture Autopoïétique (x1) et Démiurgie Multivers (x2).
    """
    survival_pts = metrics["mean_survival"] * 20.0
    energy_pts = metrics["mean_energy"] * 3.0
    synarchy_pts = metrics["mean_synarchic_ratifications"] * 5.0
    distill_pts = metrics["mean_noogenetic_distillations"] * 2.0
    auto_pts = metrics["mean_autopoietic_steps"] * 1.0
    demiurge_pts = metrics["mean_demiurgic_steps"] * 2.0
    return round(float(survival_pts + energy_pts + synarchy_pts + distill_pts + auto_pts + demiurge_pts), 2)


def main():
    print("=" * 80)
    print("BANC SOCIOLOGIQUE COMPARATIF — LANGAGE ULTIME PHASE 15 (ARC 9 : G15)")
    print("Commandement 15 (Protocole d'Innovation Unitaire) : Baseline vs Intervention (30 Ères)")
    print("=" * 80)

    # 1. Baseline : Phase 14 sans Intrication Démiurgique (30 ères)
    print("\n[1/2] Lancement de la Campagne Baseline (30 Ères — Phase 14 sans Intrication Démiurgique)...", flush=True)
    baseline_res = simulate_campaign_phase15(enable_phase15=False, eras=30, ticks_per_era=15, seed=42)
    baseline_score = compute_sociological_score_phase15(baseline_res)
    print(f"    => Survie Baseline: {baseline_res['mean_survival']*100:.2f}% | Énergie: {baseline_res['mean_energy']:.2f}")
    print(f"    => Score Sociologique Baseline: {baseline_score:.2f} / 100")

    # 2. Intervention : Phase 15 complète (30 ères)
    print("\n[2/2] Lancement de la Campagne Intervention (30 Ères — Phase 15 complète avec Démiurgie & Intrication)...", flush=True)
    intervention_res = simulate_campaign_phase15(enable_phase15=True, eras=30, ticks_per_era=15, seed=42)
    intervention_score = compute_sociological_score_phase15(intervention_res)
    print(f"    => Survie Intervention: {intervention_res['mean_survival']*100:.2f}% | Énergie: {intervention_res['mean_energy']:.2f}")
    print(f"    => Score Sociologique Intervention: {intervention_score:.2f} / 100")

    # 3. Rapport d'Analyse Comparative
    print("\n" + "=" * 80)
    print("ANALYSE COMPARATIVE FORMELLE (PIU)")
    print("=" * 80)
    print(f"{'Métrique':<32} {'Baseline (Ph14)':<18} {'Intervention (Ph15)':<22} {'Delta':<10}")
    print("-" * 80)
    print(f"{'Taux de survie moyen':<30}: {baseline_res['mean_survival']*100:>6.2f}%         {intervention_res['mean_survival']*100:>6.2f}%            {'+' if intervention_res['mean_survival']>=baseline_res['mean_survival'] else ''}{intervention_res['mean_survival']*100 - baseline_res['mean_survival']*100:>5.2f}%")
    print(f"{'Énergie finale moyenne':<30}: {baseline_res['mean_energy']:>7.2f}            {intervention_res['mean_energy']:>7.2f}              {'+' if intervention_res['mean_energy']>=baseline_res['mean_energy'] else ''}{intervention_res['mean_energy'] - baseline_res['mean_energy']:>5.2f}")
    print(f"{'Conseils synarchiques ratifiés':<30}: {baseline_res['mean_synarchic_ratifications']:>7.2f}            {intervention_res['mean_synarchic_ratifications']:>7.2f}              {'+' if intervention_res['mean_synarchic_ratifications']>=baseline_res['mean_synarchic_ratifications'] else ''}{intervention_res['mean_synarchic_ratifications'] - baseline_res['mean_synarchic_ratifications']:>5.2f}")
    print(f"{'Distillations Noogénétiques':<30}: {baseline_res['mean_noogenetic_distillations']:>7.2f}            {intervention_res['mean_noogenetic_distillations']:>7.2f}              {'+' if intervention_res['mean_noogenetic_distillations']>=baseline_res['mean_noogenetic_distillations'] else ''}{intervention_res['mean_noogenetic_distillations'] - baseline_res['mean_noogenetic_distillations']:>5.2f}")
    print(f"{'Étapes Autopoïétiques':<30}: {baseline_res['mean_autopoietic_steps']:>7.2f}            {intervention_res['mean_autopoietic_steps']:>7.2f}              {'+' if intervention_res['mean_autopoietic_steps']>=baseline_res['mean_autopoietic_steps'] else ''}{intervention_res['mean_autopoietic_steps'] - baseline_res['mean_autopoietic_steps']:>5.2f}")
    print(f"{'Étapes Démiurgiques':<30}: {baseline_res['mean_demiurgic_steps']:>7.2f}            {intervention_res['mean_demiurgic_steps']:>7.2f}              {'+' if intervention_res['mean_demiurgic_steps']>=baseline_res['mean_demiurgic_steps'] else ''}{intervention_res['mean_demiurgic_steps'] - baseline_res['mean_demiurgic_steps']:>5.2f}")
    print(f"{'Paires Intriquées':<30}: {baseline_res['mean_entangled_pairs']:>7.2f}            {intervention_res['mean_entangled_pairs']:>7.2f}              {'+' if intervention_res['mean_entangled_pairs']>=baseline_res['mean_entangled_pairs'] else ''}{intervention_res['mean_entangled_pairs'] - baseline_res['mean_entangled_pairs']:>5.2f}")
    print(f"{'Dividendes Démiurgiques':<30}: {baseline_res['mean_demiurgic_dividends']:>7.2f}            {intervention_res['mean_demiurgic_dividends']:>7.2f}              {'+' if intervention_res['mean_demiurgic_dividends']>=baseline_res['mean_demiurgic_dividends'] else ''}{intervention_res['mean_demiurgic_dividends'] - baseline_res['mean_demiurgic_dividends']:>5.2f}")
    print("-" * 80)
    score_delta = intervention_score - baseline_score
    score_pct = (score_delta / baseline_score) * 100 if baseline_score > 0 else 0.0
    print(f"{'Score Sociologique Global':<30}: {baseline_score:>7.2f}           {intervention_score:>7.2f}              {'+' if score_delta>=0 else ''}{score_delta:>5.2f} ({'+' if score_pct>=0 else ''}{score_pct:.2f}%)")
    print("=" * 80)

    # 4. Décision Formelle sous Commandement 15
    if intervention_score >= baseline_score:
        print("\n[VERDICT PIU : SUCCÈS] Score Intervention (%.2f) >= Baseline (%.2f)." % (intervention_score, baseline_score))
        print("L'intervention Phase 15 (Intrication Sémantique & Démiurgie Multivers) est formellement VALIDÉE.\n")
    else:
        print("\n[VERDICT PIU : REVERT REQUIS] Score Intervention (%.2f) < Baseline (%.2f)." % (intervention_score, baseline_score))
        print("L'intervention a provoqué une régression sociologique. Conformément au Commandement 15 : REVERT.\n")


if __name__ == "__main__":
    main()
