"""
Unit tests for LU (Langage Ultime) & DSL Optimization Engine.
Validates AST parsing, Gigatoken compilation, linear vector state execution,
and bi-directional translation (Commandments 3, 7, and 9).
"""

import pytest
import numpy as np
from src.metaprog.lu_dsl_engine import (
    LUConfig,
    LUNode,
    LUGraph,
    LUCompiler,
    LUVectorExecutor,
    LUFrontEndBridge,
)


def test_lu_config_defaults():
    config = LUConfig()
    assert config.vector_dim == 64
    assert config.sparsity_lambda == 0.01
    assert config.enable_gigatokens is True


def test_dsl_parser_and_canonicalization():
    compiler = LUCompiler(LUConfig(vector_dim=32, seed=123))
    dsl_input = "@AGENT:Supervisor[n1] ; @DATASET:KuzuDB[n2] EDGES: (n1)-[QUERY]->(n2)"
    
    graph = compiler.parse_dsl(dsl_input)
    assert len(graph.nodes) == 2
    assert "n1" in graph.nodes
    assert "n2" in graph.nodes
    assert graph.nodes["n1"].category == "AGENT"
    assert graph.nodes["n1"].label == "Supervisor"
    assert len(graph.edges) == 1
    assert graph.edges[0] == ("n1", "QUERY", "n2")

    canonical_str = graph.to_dsl_string()
    assert "@AGENT:Supervisor[n1]" in canonical_str
    assert "@DATASET:KuzuDB[n2]" in canonical_str
    assert "(n1)-[QUERY]->(n2)" in canonical_str


def test_gigatoken_compilation_and_numerical_stability():
    config = LUConfig(vector_dim=32, seed=42)
    compiler = LUCompiler(config)
    dsl_input = "@CONCEPT:Intelligence[c1] ; @STATE:Optimal[s1] EDGES: (c1)-[HAS_STATE]->(s1)"
    
    graph = compiler.parse_dsl(dsl_input)
    gigatoken = compiler.compile_to_gigatoken(graph)

    # Check vector dimension
    assert gigatoken.shape == (32,)
    # Check normalization (unit norm)
    norm = np.linalg.norm(gigatoken)
    assert pytest.approx(norm, abs=1e-5) == 1.0
    # Check numerical stability (no NaN or Inf)
    assert not np.isnan(gigatoken).any()
    assert not np.isinf(gigatoken).any()


def test_subquadratic_vector_executor():
    config = LUConfig(vector_dim=16, seed=99)
    compiler = LUCompiler(config)
    executor = LUVectorExecutor(config)

    graph = compiler.parse_dsl("@AGENT:Bot[a1] ; @ACTION:Compute[ac1] EDGES: (a1)-[PERFORMS]->(ac1)")
    gigatoken = compiler.compile_to_gigatoken(graph)

    initial_state = np.zeros(16, dtype=np.float64)
    next_state = executor.execute_step(initial_state, gigatoken)

    assert next_state.shape == (16,)
    assert not np.isnan(next_state).any()
    assert not np.isinf(next_state).any()
    # Check that state changed
    assert not np.allclose(initial_state, next_state)


def test_frontend_bridge_translation():
    bridge = LUFrontEndBridge()
    nl_text = "AGIseed executes SwarmNAS under HighPerformance"
    lu_dsl = bridge.translate_nl_to_lu(nl_text)

    assert "@AGENT:AGIseed[n1]" in lu_dsl
    assert "@TARGET:SwarmNAS[n2]" in lu_dsl
    assert "(n1)-[EXECUTE]->(n2)" in lu_dsl

    # Test reverse summary
    graph = bridge.compiler.parse_dsl(lu_dsl)
    summary = bridge.translate_lu_to_summary(graph)
    assert "AGIseed" in summary
    assert "SwarmNAS" in summary
