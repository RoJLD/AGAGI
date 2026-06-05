"""
Tests for Phase 3: Macro-NAS Supervisor and Evaluator.
Commandement 7: Validation Rigoureuse.
"""
import sys
import os
import json
import pytest
import numpy as np

# Adjust PYTHONPATH to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from graph_rag.supervisor import build_supervisor_graph, MacroNASState
from graph_rag.evaluator import FitnessEvaluator, EvaluatorConfig

def test_evaluator_numerical_stability():
    """Test Commandement 9: Stabilité Numérique."""
    evaluator = FitnessEvaluator(EvaluatorConfig(lambda_penalty=0.01))
    
    # Normal case
    score = evaluator.evaluate(accuracy=0.9, size_params=1000)
    assert score > 0.0
    
    # NaN/Inf handling
    assert evaluator.evaluate(np.nan, 1000) == -np.inf
    assert evaluator.evaluate(0.9, np.inf) == -np.inf
    assert evaluator.evaluate(0.9, -500) == evaluator.evaluate(0.9, 0) # Should be handled by max(0, x)

def test_supervisor_workflow():
    """Test LangGraph orchestration and sandboxing."""
    graph = build_supervisor_graph()
    
    initial_state = {"architecture_id": "arch_test_001"}
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    # Assertions
    assert "proposed_code" in result
    assert "compiled_path" in result
    assert "sandbox_result" in result
    assert result["sandbox_result"]["success"] is True
    
    assert "fitness_score" in result
    assert isinstance(result["fitness_score"], float)
    
    assert "decision_log" in result
    log = json.loads(result["decision_log"])
    assert log["architecture_id"] == "arch_test_001"
    assert "decision" in log
    assert log["decision"] in ["ACCEPTED", "REJECTED"]
