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

from graph_rag.supervisor import build_supervisor_graph, SupervisorState
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
    """Test LangGraph orchestration."""
    graph = build_supervisor_graph()
    
    initial_state = {
        "db_path": "data/test_dummy_db.db",
        "latest_metrics": {
            "energy_stability": 0.7,
            "genome_diversity": 0.6,
            "social_density": 0.4,
            "avg_energy": 60.0
        }
    }
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    # Assertions
    assert "analysis_insight" in result
    assert "tweaked_parameters" in result
    assert "robustness_score" in result
    assert "emergence_score" in result
    assert isinstance(result["robustness_score"], float)
    assert isinstance(result["emergence_score"], float)

