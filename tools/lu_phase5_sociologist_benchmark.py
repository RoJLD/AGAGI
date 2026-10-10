"""
tools/lu_phase5_sociologist_benchmark.py — Banc d'évaluation sociologique pour le Langage Ultime (Phase 5).
Conforme au Commandement 15 (Protocole d'Innovation Unitaire / Loi du Sociologue) :
- 30 Ères Baseline : Troc vulnérable aux défecteurs (33% tricheurs, sans gouvernance ni consortiums).
- 30 Ères Intervention : Gouvernance juridique décentralisée, arbitrage d'embargo et consortiums métallurgiques (Phase 5).
- Analyse comparative Before/After et verdict de recevabilité sociologique.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from typing import Dict, Any

from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


def simulate_campaign_phase5(
    enable_phase5: bool,
    eras: int = 30,
    ticks_per_era: int = 30,
    seed: int = 42
) -> Dict[str, Any]:
    """Exécute une campagne de 30 ères sous configuration Baseline (Vulnérable) vs Phase 5 (Gouvernance & Métallurgie)."""
    survivals = []
    total_trades = []
    total_consortiums = []
    total_sanctions = []
    metal_tools_produced = []
    final_energies = []

    for era in range(eras):
        np.random.seed(seed * 1000 + era)
        agri_cfg = AgriculturalConfig(
            size=16,
            season_duration=15,
            winter_energy_penalty=0.20,
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
            # Phase 5 Toggles
            enable_governance=enable_phase5,
            enable_consortium_contracts=enable_phase5,
            consortium_agreement_threshold=0.40,
            embargo_reputation_threshold=0.40,
            embargo_duration_ticks=15,
        )
        adapter = LUInWorldAdapter(world, adapter_cfg)
        world.enable_lu_communication = True
        world.lu_adapter = adapter

        # 6 agents : 4 loyaux (Monde 1 Bûcheron, Monde 2 Fermiers x2, Monde 3 Mineur) et 2 défecteurs (Outlaws)
        for i in range(6):
            is_defector = (i >= 4)
            ag_obj = MambaAgent(isocaloric=True)
            world.add_agent(
                ag_obj,
                x=int(7 + (i % 3)),
                y=int(7 + (i // 3)),
                energy=50.0
            )
            world.agents[-1]["clan"] = "Clan_Outlaw" if is_defector else "Clan_Union"
            world.agents[-1]["is_defector"] = is_defector
            world.agents[-1]["inventory"] = []

        era_trades = 0
        era_consortiums = 0
        era_sanctions = 0
        era_metal_tools = 0
        living_ticks = 0

        for t in range(ticks_per_era):
            # Réapprovisionnement des flux de production biomes tous les 3 ticks
            if t % 3 == 0:
                for i, ag in enumerate(world.agents):
                    if ag.get("is_defector", False):
                        continue
                    inv = ag.setdefault("inventory", [])
                    if len(inv) < 3:
                        if i == 0:
                            inv.append({"type": "WOOD"})
                        elif i in (1, 2):
                            inv.append({"type": "FOOD"})
                        elif i == 3:
                            inv.append({"type": "ORE"})

            prev_trades = adapter.contracts_settled_count
            prev_consortiums = adapter.consortiums_settled_count
            prev_sanctions = adapter.sanctions_count
            prev_tools = adapter.metal_tools_produced_count

            world.step()

            era_trades += (adapter.contracts_settled_count - prev_trades)
            era_consortiums += (adapter.consortiums_settled_count - prev_consortiums)
            era_sanctions += (adapter.sanctions_count - prev_sanctions)
            era_metal_tools += (adapter.metal_tools_produced_count - prev_tools)

            living = [a for a in world.agents if a.get("energy", 0) > 0]
            if len(living) > 0:
                living_ticks += 1
            else:
                break

        survivals.append(living_ticks)
        total_trades.append(era_trades)
        total_consortiums.append(era_consortiums)
        total_sanctions.append(era_sanctions)
        metal_tools_produced.append(era_metal_tools)

        # Mesure d'énergie sur les agents loyaux
        honest_energies = [
            float(a.get("energy", 0.0))
            for a in world.agents
            if not a.get("is_defector", False) and not np.isnan(a.get("energy", 0.0))
        ]
        mean_e = float(np.mean(honest_energies)) if len(honest_energies) > 0 else float('nan')
        final_energies.append(mean_e)

    valid_energies = [e for e in final_energies if not np.isnan(e)]
    mean_final_e = float(np.mean(valid_energies)) if len(valid_energies) > 0 else float('nan')

    return {
        "eras": eras,
        "median_survival_ticks": float(np.median(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_survival_ticks": float(np.mean(survivals)) if len(survivals) > 0 else float('nan'),
        "mean_trades_settled": float(np.mean(total_trades)) if len(total_trades) > 0 else float('nan'),
        "mean_consortiums": float(np.mean(total_consortiums)) if len(total_consortiums) > 0 else float('nan'),
        "mean_sanctions": float(np.mean(total_sanctions)) if len(total_sanctions) > 0 else float('nan'),
        "mean_metal_tools": float(np.mean(metal_tools_produced)) if len(metal_tools_produced) > 0 else float('nan'),
        "mean_final_energy_honest": mean_final_e,
    }


def main():
    print("=" * 80)
    print("🔬 BANC SOCIOLOGIQUE LU PHASE 5 — LOI DU SOCIOLOGUE (COMMANDEMENT 15)")
    print("   Comparaison 30 Ères Baseline (Troc Vulnérable) vs 30 Ères Intervention (Gouvernance & Métallurgie)")
    print("=" * 80)

    print("\n[1/2] Exécution de la Baseline (30 Ères sans gouvernance, prédateurs actifs)...")
    res_base = simulate_campaign_phase5(enable_phase5=False, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne : {res_base['mean_survival_ticks']:.2f} ticks")
    print(f"  -> Énergie finale loyaux : {res_base['mean_final_energy_honest']:.2f} pts")
    print(f"  -> Contrats bilatéraux : {res_base['mean_trades_settled']:.2f} / ère")
    print(f"  -> Consortiums métallurgiques : {res_base['mean_consortiums']:.2f} / ère")
    print(f"  -> Sanctions / Embargos : {res_base['mean_sanctions']:.2f} / ère")

    print("\n[2/2] Exécution de l'Intervention (30 Ères avec gouvernance juridique & consortiums)...")
    res_interv = simulate_campaign_phase5(enable_phase5=True, eras=30, ticks_per_era=30, seed=42)
    print(f"  -> Survie moyenne : {res_interv['mean_survival_ticks']:.2f} ticks")
    print(f"  -> Énergie finale loyaux : {res_interv['mean_final_energy_honest']:.2f} pts")
    print(f"  -> Contrats bilatéraux : {res_interv['mean_trades_settled']:.2f} / ère")
    print(f"  -> Consortiums métallurgiques : {res_interv['mean_consortiums']:.2f} / ère")
    print(f"  -> Outils métalliques forgés : {res_interv['mean_metal_tools']:.2f} / ère")
    print(f"  -> Sanctions / Embargos : {res_interv['mean_sanctions']:.2f} / ère")

    delta_surv = res_interv['mean_survival_ticks'] - res_base['mean_survival_ticks']
    delta_energy = res_interv['mean_final_energy_honest'] - res_base['mean_final_energy_honest']
    delta_consort = res_interv['mean_consortiums'] - res_base['mean_consortiums']

    print("\n" + "=" * 80)
    print("📊 RÉSULTATS COMPARATIFS (PIU / LOI DU SOCIOLOGUE) :")
    print(f"  - Delta Survie : {delta_surv:+.2f} ticks")
    print(f"  - Delta Énergie Moyenne Loyaux : {delta_energy:+.2f} pts")
    print(f"  - Delta Consortiums Métallurgiques : {delta_consort:+.2f} / ère")
    print("=" * 80)

    # Règle d'or du Commandement 15 : Score moyen >= Baseline -> VALIDE.
    is_valid = (delta_surv >= -0.5) and (delta_energy >= 0.0) and (res_interv['mean_consortiums'] > 0.0)
    if is_valid:
        print("\n✅ VERDICT DU SOCIOLOGUE : INNOVATION VALIDÉE ET PÉRENNE.")
        print("   La gouvernance juridique neutralise la prédation et débloque l'industrie métallurgique.")
        return 0
    else:
        print("\n❌ VERDICT DU SOCIOLOGUE : RÉGRESSION DÉTECTÉE — REVERT RECOMMANDÉ.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
