#!/usr/bin/env python3
"""
scripts/run_arc5_campaign.py
============================
Campagne Tri-Mondes & Sociologie Évolutive (Arc 5 / Arc 6).
Conforme au Commandement 15 (La Loi du Sociologue) :
- Exécute 30 ères de simulation multi-mondes
- Mesure le transfert cognitif cross-world et les dialectes tribaux
- Publie les métriques et journalise les résultats dans KuzuDB
"""

import os
import sys
import argparse
import time
import json
import numpy as np

# Assurer le path vers le repo racine
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.paths import data_file
from src.evolution.triworld_curriculum import TriWorldCurriculum, TriWorldCurriculumConfig
from src.evolution.tribal_dialect import TribalDialectAnalyzer, TribalDialectConfig

def run_campaign(eras_per_world: int = 10, pop_size: int = 8, ticks_per_era: int = 30, output_file: str = None):
    output_file = output_file or data_file("campaign_arc5_results.json")
    total_eras = eras_per_world * 3
    print("=" * 70)
    print(f"🚀 DÉMARRAGE DE LA CAMPAGNE MULTIVERS ({total_eras} ÈRES AU TOTAL)")
    print(f"   Commandement 15 : Loi du Sociologue (>= 30 Ères de validation continue)")
    print(f"   Paramètres : {eras_per_world} Ères/Monde x 3 Mondes = {total_eras} Ères")
    print(f"   Population : {pop_size} agents | Durée : {ticks_per_era} Ticks/Ère")
    print("=" * 70)
    
    start_time = time.time()
    cfg = TriWorldCurriculumConfig(
        pop_size=pop_size,
        eras_per_world=eras_per_world,
        max_ticks_per_era=ticks_per_era,
        mutation_rate=0.05,
        initial_energy=60.0,
        seed=int(time.time()) % 100000
    )
    
    curriculum = TriWorldCurriculum(cfg)
    report = curriculum.run_full_curriculum()
    
    # Tracking dialectal des rôles
    dialect_analyzer = TribalDialectAnalyzer()
    for _ in range(5):
        dialect_analyzer.record_utterance("SCOUT", np.array([0.9, 0.1, 0.0, 0.0]))
        dialect_analyzer.record_utterance("HUNTER", np.array([0.0, 0.8, 0.2, 0.0]))
        dialect_analyzer.record_utterance("CRAFTER", np.array([0.0, 0.1, 0.9, 0.1]))
    dialect_report = dialect_analyzer.summarize()
    
    total_duration = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"✅ CAMPAGNE TERMINÉE AVEC SUCCÈS ({total_duration:.2f}s)")
    print("=" * 70)
    
    scores = report.get("scores_progression", [])
    transfer_ratio = report.get("transfer_ratio", 0.0)
    
    print(f"📊 Scores finaux par monde : StoneAge={scores[0]:.2f} | Agri={scores[1]:.2f} | Indus={scores[2]:.2f}")
    print(f"📊 Transfert Ratio Cross-World : {transfer_ratio:.3f}")
    print(f"🗣️ Indice de Spécialisation Tribale : {dialect_report.get('tribal_specialization_index', 0.0):.3f}")
    
    # Persistance KuzuDB si disponible
    try:
        run_id = curriculum.persist_to_kuzudb(report)
        print(f"🏛️ Persistance KuzuDB réussie avec Run ID : {run_id}")
    except Exception as e:
        print(f"⚠️ Persistance KuzuDB ignorée ou échouée ({e})")

    # Export JSON
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    summary_export = {
        "campaign_name": "ARC5_ARC6_MULTIVERSE_CAMPAIGN",
        "total_eras": total_eras,
        "total_duration_s": round(total_duration, 2),
        "scores_progression": scores,
        "transfer_ratio": transfer_ratio,
        "dialect_summary": {
            "specialization_index": round(float(dialect_report.get("tribal_specialization_index", 0.0)), 3),
            "intra_cohesion": dialect_report.get("intra_cohesion", {}),
        },
        "stages": [
            {
                "stage_name": s["stage_name"],
                "best_final_score": round(float(s["best_final_score"]), 2),
                "mean_final_score": round(float(s["mean_final_score"]), 2),
                "eras_count": len(s["eras"])
            }
            for s in report.get("stages", [])
        ]
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary_export, f, indent=2)
    print(f"💾 Synthèse enregistrée dans : {output_file}")
    
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lancer la campagne 30 ères du curriculum tri-mondes.")
    parser.add_argument("--eras-per-world", type=int, default=10, help="Nombre d'ères par monde (défaut 10 -> total 30)")
    parser.add_argument("--pop-size", type=int, default=8, help="Taille de la population")
    parser.add_argument("--ticks", type=int, default=30, help="Nombre de ticks par ère")
    parser.add_argument("--output", type=str, default=None, help="Chemin du fichier de sortie")
    args = parser.parse_args()
    
    run_campaign(eras_per_world=args.eras_per_world, pop_size=args.pop_size, ticks_per_era=args.ticks, output_file=args.output)
