"""
tests/test_triworld_curriculum.py — Test du Curriculum Évolutif Tri-Mondes.
Vérifie la progression d'une lignée d'agents à travers :
Monde 1 (Pierre) -> Monde 2 (Agricole) -> Monde 3 (Industriel).
"""
import pytest
import numpy as np

from src.evolution.triworld_curriculum import TriWorldCurriculum, TriWorldCurriculumConfig


def test_triworld_curriculum_execution():
    """Valide l'exécution complète du curriculum inter-mondes."""
    cfg = TriWorldCurriculumConfig(
        pop_size=4,
        eras_per_world=1,
        max_ticks_per_era=10,
        mutation_rate=0.02,
        seed=42
    )

    curriculum = TriWorldCurriculum(cfg)
    report = curriculum.run_full_curriculum()

    assert report["status"] == "completed"
    assert len(report["stages"]) == 3
    assert report["stages"][0]["stage_name"] == "StoneAge_World1"
    assert report["stages"][1]["stage_name"] == "Agricultural_World2"
    assert report["stages"][2]["stage_name"] == "Industrial_World3"

    assert "champions" in report
    assert report["champions"]["stoneage"] is not None
    assert report["champions"]["agricultural"] is not None
    assert report["champions"]["industrial"] is not None

    assert len(report["scores_progression"]) == 3
    assert isinstance(report["transfer_ratio"], float)


def test_triworld_curriculum_kuzudb_persistence(tmp_path):
    """Valide l'audit et la persistance KuzuDB d'un run tri-mondes (Commandement 5)."""
    from src.graph_rag.experiment_tracker import ExperimentGraph

    db_file = str(tmp_path / "kuzu_test.db")
    cfg = TriWorldCurriculumConfig(
        pop_size=3,
        eras_per_world=1,
        max_ticks_per_era=5,
        mutation_rate=0.01,
        seed=123
    )
    curriculum = TriWorldCurriculum(cfg)
    report = curriculum.run_full_curriculum()

    run_id = curriculum.persist_to_kuzudb(report, db_path=db_file, run_id="test_run_123")
    assert run_id == "test_run_123"

    graph = ExperimentGraph(db_path=db_file)
    runs = graph.get_phylogenetic_runs()
    assert len(runs) == 1
    assert runs[0]["id"] == "test_run_123"
    assert runs[0]["status"] == "completed"
    assert isinstance(runs[0]["transfer_ratio"], float)

