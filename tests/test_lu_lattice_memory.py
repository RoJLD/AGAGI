"""
Tests unitaires pour LULatticeMemory (KuzuDB + Gigatokens LU).
Conformité au Commandement 7 (Test-Driven Metaprogramming) et Commandement 9 (Stabilité Numérique).
"""

import pytest
import numpy as np
import gc

from src.graph_rag.database import KuzuDatabase, DatabaseConfig
from src.graph_rag.lu_lattice_memory import LULatticeMemory, LULatticeConfig
from src.metaprog.lu_dsl_semantic import LUSemanticParser


@pytest.fixture
def temp_kuzu_db(tmp_path):
    """Fixture créant une base KuzuDB temporaire et isolée."""
    db_path = str(tmp_path / "test_lu_kuzu.db")
    config = DatabaseConfig(db_path=db_path)
    db = KuzuDatabase(config)
    db.bootstrap_schema()
    yield db
    # Nettoyage mémoire
    del db.conn
    del db.db
    gc.collect()


def test_store_and_recall_thought(temp_kuzu_db):
    parser = LUSemanticParser()
    lattice_cfg = LULatticeConfig(vector_dim=64, similarity_threshold=0.60)
    memory = LULatticeMemory(temp_kuzu_db, lattice_cfg)

    # 1. Enregistre une pensée sur la recherche de nourriture
    stmt1 = (
        "(Hunter:AGENT {name: 'Agent_01'})-[TARGETS]->(Prey:CONCEPT) ; "
        "(Prey:CONCEPT)-[IS_A]->(Food:CONCEPT)"
    )
    g1 = parser.parse_statement(stmt1)
    tid1 = memory.store_thought("Agent_01", g1, stmt1, timestamp=100)
    assert tid1.startswith("lu_")

    # 2. Enregistre une pensée distincte sur le sommeil / nuit
    stmt2 = (
        "(Sleeper:AGENT {name: 'Agent_02'})-[DESIRES]->(Rest:STATE) ; "
        "(Night:STATE)-[TRIGGERS]->(Rest:STATE)"
    )
    g2 = parser.parse_statement(stmt2)
    tid2 = memory.store_thought("Agent_02", g2, stmt2, timestamp=105)

    # 3. Requête avec un Gigatoken proche de g1
    query_gigatoken = memory.compiler.compile_to_gigatoken(g1)
    recalled = memory.recall_nearest_thoughts(query_gigatoken, top_k=2)

    assert len(recalled) >= 1
    # Le premier résultat doit être g1 avec une similarité cosinus proche de 1.0
    best_id, best_dsl, best_score = recalled[0]
    assert best_id == tid1
    assert best_score > 0.95


def test_recall_empty_or_low_similarity(temp_kuzu_db):
    lattice_cfg = LULatticeConfig(vector_dim=64, similarity_threshold=0.99)
    memory = LULatticeMemory(temp_kuzu_db, lattice_cfg)

    # Vecteur aléatoire
    rng = np.random.RandomState(42)
    random_vec = rng.randn(64)
    # Rien en base
    results = memory.recall_nearest_thoughts(random_vec)
    assert results == []

    # Vecteur nul (doit être protégé par eps)
    zero_vec = np.zeros(64)
    results_zero = memory.recall_nearest_thoughts(zero_vec)
    assert results_zero == []
