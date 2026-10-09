"""
Tests unitaires pour le parser sémantique LU, la validation ontologique et l'émetteur Cypher.
Conformité stricte au Commandement 7 (Test-Driven Metaprogramming) et Commandement 9 (Stabilité).
"""

import pytest
import numpy as np
from src.metaprog.lu_dsl_semantic import (
    LUSemanticParser,
    LUSemanticValidator,
    LUCypherEmitter,
    LUAlgebra,
    LUSyntaxError,
    LUSemanticError,
    OntologyConfig,
)
from src.metaprog.lu_dsl_engine import LUGraph, LUNode, LUCompiler


def test_semantic_parser_valid_statements():
    parser = LUSemanticParser()
    stmt = (
        "(Hunter:AGENT {name: 'Predator_01'})-[TARGETS {prio: 0.95}]->(Prey:CONCEPT {speed: 1.2}) ; "
        "(Prey:CONCEPT)-[IS_A]->(Animal:CONCEPT)"
    )
    graph = parser.parse_statement(stmt)

    assert len(graph.nodes) == 3
    assert "Hunter" in graph.nodes
    assert graph.nodes["Hunter"].category == "AGENT"
    assert graph.nodes["Hunter"].attributes["name"] == "Predator_01"
    assert graph.nodes["Prey"].attributes["speed"] == 1.2

    assert len(graph.edges) == 2
    assert ("Hunter", "TARGETS", "Prey") in graph.edges
    assert ("Prey", "IS_A", "Animal") in graph.edges


def test_semantic_parser_isolated_nodes():
    parser = LUSemanticParser()
    stmt = "(Night:STATE {darkness: 0.8}) ; (Feu:TOOL {heat: 50})"
    graph = parser.parse_statement(stmt)

    assert len(graph.nodes) == 2
    assert graph.nodes["Night"].category == "STATE"
    assert graph.nodes["Feu"].category == "TOOL"
    assert len(graph.edges) == 0


def test_syntax_error_invalid_clause():
    parser = LUSemanticParser()
    with pytest.raises(LUSyntaxError):
        parser.parse_statement("THIS IS NOT A VALID LU DSL STATEMENT")


def test_semantic_error_invalid_category():
    parser = LUSemanticParser()
    # 'ALIEN' n'est pas une catégorie autorisée
    with pytest.raises(LUSemanticError) as exc_info:
        parser.parse_statement("(X:ALIEN)-[TARGETS]->(Y:CONCEPT)")
    assert "Catégorie inconnue 'ALIEN'" in str(exc_info.value)


def test_semantic_error_type_mismatch():
    parser = LUSemanticParser()
    # 'DESIRES' exige source AGENT et cible STATE ou CONCEPT.
    # Ici source = TOOL, doit lever LUSemanticError
    with pytest.raises(LUSemanticError) as exc_info:
        parser.parse_statement("(Hammer:TOOL)-[DESIRES]->(Energy:STATE)")
    assert "Relation 'DESIRES'" in str(exc_info.value)


def test_kuzu_cypher_emitter():
    parser = LUSemanticParser()
    stmt = (
        "(Ag01:AGENT)-[TARGETS]->(Meat:CONCEPT) ; "
        "(Meat:CONCEPT)-[IS_A]->(Food:CONCEPT)"
    )
    graph = parser.parse_statement(stmt)
    queries = LUCypherEmitter.emit_kuzu_cypher(graph)

    assert len(queries) >= 5  # 3 MERGE Concept + 2 relations (INFLUENCES / IS_A)
    assert any("MERGE (c:Concept {id: 'Ag01'})" in q for q in queries)
    assert any("-[:IS_A]->" in q for q in queries)
    assert any("-[:INFLUENCES" in q for q in queries)


def test_lu_algebra_union_and_composition():
    parser = LUSemanticParser()
    g1 = parser.parse_statement("(A:AGENT)-[TARGETS]->(B:CONCEPT)")
    g2 = parser.parse_statement("(C:STATE)-[TRIGGERS]->(D:ACTION)")

    # Test Union
    union_graph = LUAlgebra.union(g1, g2)
    assert len(union_graph.nodes) == 4
    assert len(union_graph.edges) == 2

    # Test Composition Séquentielle
    composed = LUAlgebra.compose_sequential(g1, g2, bridge_rel="LEADS_TO")
    assert len(composed.nodes) == 4
    # Doit avoir relié les nœuds terminaux de g1 (B) aux initiaux de g2 (C)
    assert ("B", "LEADS_TO", "C") in composed.edges


def test_gigatoken_end_to_end_from_parsed_dsl():
    """Vérifie que le graphe parsé produit un Gigatoken dense de dimension D normalisé."""
    parser = LUSemanticParser()
    compiler = LUCompiler()
    stmt = (
        "(AgentX:AGENT)-[DESIRES]->(Safety:STATE) ; "
        "(Safety:STATE)-[TRIGGERS]->(BuildShelter:ACTION)"
    )
    graph = parser.parse_statement(stmt)
    gigatoken = compiler.compile_to_gigatoken(graph)

    assert gigatoken.shape == (compiler.config.vector_dim,)
    assert not np.any(np.isnan(gigatoken))
    assert not np.any(np.isinf(gigatoken))
    assert np.isclose(np.linalg.norm(gigatoken), 1.0, atol=1e-5)
