#!/usr/bin/env python3
"""
tools/register_phylogenetic_run.py — CLI pour exécuter et enregistrer un Curriculum Tri-Mondes dans KuzuDB.
Respecte les Commandements AGIseed :
- Commandement 1 : Flexible (arguments en ligne de commande)
- Commandement 5 : Transparent & Auditable (enregistrement dans la Lattice Memory)
"""
import argparse
import sys
import os

# Assurer l'accès au path racine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.paths import kuzu_graph
from src.evolution.triworld_curriculum import TriWorldCurriculum, TriWorldCurriculumConfig
from src.graph_rag.experiment_tracker import ExperimentGraph


def main():
    parser = argparse.ArgumentParser(description="Exécuter et enregistrer un run Tri-Mondes dans KuzuDB")
    parser.add_argument("--pop-size", type=int, default=6, help="Taille de la population")
    parser.add_argument("--eras", type=int, default=2, help="Nombre d'ères par monde")
    parser.add_argument("--ticks", type=int, default=20, help="Ticks max par ère")
    parser.add_argument("--mutation-rate", type=float, default=0.03, help="Taux de mutation")
    parser.add_argument("--db-path", type=str, default=None, help="Chemin vers la base KuzuDB")
    parser.add_argument("--run-id", type=str, default=None, help="ID optionnel du run")
    args = parser.parse_args()

    print(f"[Curriculum CLI] Démarrage du Curriculum Tri-Mondes (pop={args.pop_size}, ères={args.eras}, ticks={args.ticks})...")
    cfg = TriWorldCurriculumConfig(
        pop_size=args.pop_size,
        eras_per_world=args.eras,
        max_ticks_per_era=args.ticks,
        mutation_rate=args.mutation_rate
    )
    curriculum = TriWorldCurriculum(cfg)
    report = curriculum.run_full_curriculum()

    print(f"[Curriculum CLI] Exécution achevée ! Ratio de transfert: {report['transfer_ratio']:.3f}")
    print(f"[Curriculum CLI] Scores par monde: {report['scores_progression']}")

    run_id = curriculum.persist_to_kuzudb(report, db_path=args.db_path, run_id=args.run_id)
    print(f"[Curriculum CLI] Persisté avec succès dans KuzuDB ({args.db_path}) sous l'ID: {run_id}")

    # Vérification lecture
    from src.graph_rag.async_logger import logger as async_logger
    shared_db = async_logger.get_db()
    if shared_db is not None:
        graph = ExperimentGraph(db=shared_db)
    else:
        graph = ExperimentGraph(db_path=args.db_path or kuzu_graph())
    runs = graph.get_phylogenetic_runs()
    print(f"[Curriculum CLI] Nombre total de runs phylogénétiques dans KuzuDB: {len(runs)}")


if __name__ == "__main__":
    main()
