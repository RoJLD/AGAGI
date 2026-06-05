import os
import json
import pytest
from src.graph_rag.supervisor import read_kuzu_db, analyze, tweak_environment, build_supervisor_graph, SupervisorState

def test_analyze_node():
    state = SupervisorState(latest_score=0.5)
    result = analyze(state)
    assert result["analysis_insight"] == "Score is 0.5. Score stagne, augmentation du taux de mutation nécessaire."
    assert result["tweaked_parameters"]["mutation_rate"] == 0.05

def test_tweak_environment_node(tmpdir):
    # Change working directory to tmpdir so config.json is created there
    import os
    original_cwd = os.getcwd()
    os.chdir(tmpdir)
    
    try:
        state = SupervisorState(tweaked_parameters={"mutation_rate": 0.05})
        result = tweak_environment(state)
        
        assert os.path.exists("config.json")
        with open("config.json", "r") as f:
            data = json.load(f)
            assert data["mutation_rate"] == 0.05
    finally:
        os.chdir(original_cwd)

def test_graph_build():
    app = build_supervisor_graph()
    assert app is not None
