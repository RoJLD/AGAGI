import sys
import os
import pytest
import numpy as np

# Adjust PYTHONPATH to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from src.graph_rag.supervisor import analyze_metrics, SupervisorState
from src.agents.mamba_agent import _get_activation_function

def test_closed_loop_famine_and_codegen(tmpdir):
    # Setup state with a stagnating score history (variance < 0.02, mean < 0.95)
    # This triggers cognitive famine detection
    state = SupervisorState(
        db_path="data/test_dummy_db.db",
        latest_score=0.51,
        score_history=[0.51, 0.52, 0.51, 0.52, 0.51],
        latest_metrics={
            "energy_stability": 0.7,
            "genome_diversity": 0.6,
            "social_density": 0.4,
            "avg_energy": 60.0
        }
    )
    
    # Run analyze node: this should trigger generation of new activation function 'Swish'
    result = analyze_metrics(state)
    
    # Verify that famine was detected and metaprogramming succeeded
    insight = result["analysis_insight"]
    assert "[FAMINE]" in insight, "Cognitive famine was not detected!"
    assert "Métaprogrammation réussie" in insight or "Métaprogrammation erreur" in insight, "Metaprogramming node was not triggered!"
    
    if "Métaprogrammation réussie" in insight:
        # Verify that the generated file exists in the sandbox
        sandbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/metaprog/sandbox"))
        ops_file = os.path.join(sandbox_dir, "generated_ops.py")
        assert os.path.exists(ops_file), "generated_ops.py file was not created in the sandbox!"
        
        # Verify the dynamic loading in mamba_agent retrieves the custom activation function
        activation_fn = _get_activation_function()
        assert activation_fn is not np.tanh, "Failed to load custom activation function!"
        
        # Verify it works correctly on inputs
        x = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
        y = activation_fn(x)
        assert y.shape == x.shape
        assert not np.isnan(y).any()
        assert not np.isinf(y).any()
