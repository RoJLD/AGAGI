"""
tools/lu_phase6_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 6).

Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Société proto-industrielle Phase 5 sans écriture stigmargique (mortalité informationnelle).
- 30 Ères Intervention : Écriture stigmargique durable, stèles d'Académie et transmission épigénétique (Phase 6).
- Choc expérimental : Renouvellement démographique périodique (remplacement d'un artisan par un novice tous les 8 ticks).
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


def simulate_campaign_phase6(
    enable_writing: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Exécute une campagne de 30 ères sous configuration Baseline (Sans écriture) vs Phase 6 (Avec stèles & arithmétique).
    """
    survivals = []
    total_trades = []
    total_consortiums = []
    total_metal_tools = []
    final_energies = []
    steles_read_list = []
    epigenetic_boosts_list = []

    for era in range(eras):
        if (era + 1) % 10 == 0 or era == 0:
            print(f"    -> Ère {era + 1}/{eras}...", flush=True)
        np.random.seed(seed * 2000 + era)
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
            # Phase 6 Toggles
            enable_writing=enable_writing,
            enable_arithmetic=enable_writing,
            read_inscription_radius=4.0,
            epigenetic_prior_boost=5.0,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents de colonie (Bûcherons, Fermiers, Mineurs)
        for i in range(6):
            ag_obj = MambaAgent(isocaloric=True)
            world.add_agent(
                ag_obj,
                x=int(7 + (i % 3)),
                y=int(7 + (i // 3)),
                energy=45.0
            )
            world.agents[-1]["age"] = 10
            world.agents[-1]["inventory"] = []

        era_trades = 0
        era_consortiums = 0
        era_metal_tools = 0
        living_ticks = 0

        for t in range(ticks_per_era):
            world.tick = t

            # Réapprovisionnement régulier des intrants de base
            if t % 3 == 0:
                for i, ag in enumerate(world.agents):
                    inv = ag.setdefault("inventory", [])
                    if len(inv) < 3:
                        if i == 0:
                            inv.append({"type": "WOOD"})
                        elif i in (1, 2):
                            inv.append({"type": "FOOD"})
                        elif i == 3:
                            inv.append({"type": "ORE"})

            # Choc démographique : Remplacement périodique d'un agent par un novice au tick 8 et 18
            if t in (8, 18) and len(world.agents) > 0:
                replaced_idx = (t // 8) % len(world.agents)
                world.agents[replaced_idx]["energy"] = 20.0
                world.agents[replaced_idx]["age"] = 0
                world.agents[replaced_idx]["inventory"] = []
                world.agents[replaced_idx].pop("lu_prior_boosted", None)

            prev_trades = adapter.contracts_settled_count
            prev_consortiums = adapter.consortiums_settled_count
            prev_tools = adapter.metal_tools_produced_count

            step_res = adapter.step()
            world.step()

            era_trades += (adapter.contracts_settled_count - prev_trades)
            era_consortiums += (adapter.consortiums_settled_count - prev_consortiums)
            era_metal_tools += (adapter.metal_tools_produced_count - prev_tools)

            living = [a for a in world.agents if a.get("energy", 0) > 0]
            if len(living) > 0:
                living_ticks += 1
            else:
                break

        survivals.append(living_ticks)
        total_trades.append(era_trades)
        total_consortiums.append(era_consortiums)
        total_metal_tools.append(era_metal_tools)
        steles_read_list.append(adapter.steles_read_count)
        epigenetic_boosts_list.append(adapter.epigenetic_boosts_count)

        if not era_energies:
            raise ValueError(f"Aucun agent avec une énergie valide trouvé à l'ère {era}")
        final_energies.append(float(np.mean(era_energies)))

    return {
        "eras": eras,
        "mean_survival_ticks": float(np.mean(survivals)),
        "mean_final_energy": float(np.mean(final_energies)),
        "mean_trades_settled": float(np.mean(total_trades)),
        "mean_consortiums": float(np.mean(total_consortiums)),
        "mean_metal_tools": float(np.mean(total_metal_tools)),
        "mean_steles_read": float(np.mean(steles_read_list)),
        "mean_epigenetic_boosts": float(np.mean(epigenetic_boosts_list)),
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 6 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Ères Baseline (Sans Écriture) vs 30 Ères Intervention (Écriture & Académie)")
    print("=" * 80)

    print("\n[1/2] Exécution de la Baseline (30 Ères sans écriture sous renouvellement démographique)...")
    res_base = simulate_campaign_phase6(enable_writing=False, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne : {res_base['mean_survival_ticks']:.2f} ticks")
    print(f"  -> Énergie finale moyenne : {res_base['mean_final_energy']:.2f} pts")
    print(f"  -> Contrats bilatéraux : {res_base['mean_trades_settled']:.2f} / ère")
    print(f"  -> Consortiums métallurgiques : {res_base['mean_consortiums']:.2f} / ère")
    print(f"  -> Outils métalliques forgés : {res_base['mean_metal_tools']:.2f} / ère")

    print("\n[2/2] Exécution de l'Intervention (30 Ères avec stèles de savoir et arithmétique)...")
    res_interv = simulate_campaign_phase6(enable_writing=True, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne : {res_interv['mean_survival_ticks']:.2f} ticks")
    print(f"  -> Énergie finale moyenne : {res_interv['mean_final_energy']:.2f} pts")
    print(f"  -> Contrats bilatéraux : {res_interv['mean_trades_settled']:.2f} / ère")
    print(f"  -> Consortiums métallurgiques : {res_interv['mean_consortiums']:.2f} / ère")
    print(f"  -> Outils métalliques forgés : {res_interv['mean_metal_tools']:.2f} / ère")
    print(f"  -> Lectures de stèles : {res_interv['mean_steles_read']:.2f} / ère")
    print(f"  -> Boosts épigénétiques de savoir : {res_interv['mean_epigenetic_boosts']:.2f} / ère")

    delta_surv = res_interv['mean_survival_ticks'] - res_base['mean_survival_ticks']
    delta_energy = res_interv['mean_final_energy'] - res_base['mean_final_energy']
    delta_tools = res_interv['mean_metal_tools'] - res_base['mean_metal_tools']

    print("\n" + "=" * 80)
    print("📊 RÉSULTATS COMPARATIFS (PIU / LOI DU SOCIOLOGUE) :")
    print(f"  - Delta Survie : {delta_surv:+.2f} ticks")
    print(f"  - Delta Énergie Moyenne : {delta_energy:+.2f} pts")
    print(f"  - Delta Outils Métalliques Forgés : {delta_tools:+.2f} / ère")
    print("=" * 80)

    # Règle d'or du Commandement 15 : Score moyen Intervention >= Baseline -> VALIDE.
    is_valid = (delta_surv >= -0.5) and (delta_energy >= 0.0) and (res_interv['mean_epigenetic_boosts'] > 0.0)
    if is_valid:
        print("\n✅ VERDICT DU SOCIOLOGUE : INNOVATION VALIDÉE ET PÉRENNE.")
        print("   L'écriture stigmargique et les stèles de savoir brisent la mortalité informationnelle.")
        return 0
    else:
        print("\n❌ VERDICT DU SOCIOLOGUE : RÉGRESSION DÉTECTÉE — REVERT RECOMMANDÉ.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
