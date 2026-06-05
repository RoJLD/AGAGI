import pytest
from src.graph_rag.visualize_hcm import KuzuHCMVisualizer, HCMConfig
import kuzu
import tempfile
import os
import shutil

@pytest.fixture
def mock_db_path():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_db")
    
    # Initialize a dummy kuzu db with schema
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    conn.execute("CREATE NODE TABLE CognitiveState (state_id STRING, type STRING, cluster_center STRING, PRIMARY KEY (state_id))")
    conn.execute("CREATE REL TABLE TRANSITIONS_TO (FROM CognitiveState TO CognitiveState, prob DOUBLE)")
    
    conn.execute("CREATE (c:CognitiveState {state_id: '0', type: 'UP', cluster_center: '0.0'})")
    conn.execute("CREATE (c:CognitiveState {state_id: '1', type: 'DOWN', cluster_center: '1.0'})")
    
    conn.execute("MATCH (a:CognitiveState {state_id: '0'}), (b:CognitiveState {state_id: '1'}) CREATE (a)-[:TRANSITIONS_TO {prob: 0.8}]->(b)")
    
    conn.close()
    db.close()
    
    yield db_path
    
    shutil.rmtree(temp_dir)

def test_fetch_nodes_and_edges(mock_db_path):
    config = HCMConfig(db_path=mock_db_path)
    visualizer = KuzuHCMVisualizer(config)
    
    nodes = visualizer.fetch_nodes()
    assert len(nodes) == 2
    assert ('0', 'UP') in nodes
    assert ('1', 'DOWN') in nodes
    
    edges = visualizer.fetch_edges()
    assert len(edges) == 1
    assert ('0', '1', 0.8) in edges

def test_generate_mermaid(mock_db_path):
    config = HCMConfig(db_path=mock_db_path)
    visualizer = KuzuHCMVisualizer(config)
    
    mermaid = visualizer.generate_mermaid()
    
    assert "graph TD" in mermaid
    assert '0["0\\nUP"]' in mermaid
    assert '1["1\\nDOWN"]' in mermaid
    assert "0 -->|0.80| 1" in mermaid
