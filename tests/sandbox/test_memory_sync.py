import pytest
import numpy as np
import os
import shutil
import gc
from src.seed_ai.network import MicroEngine, MicroEngineConfig
from src.graph_rag.database import KuzuDatabase, DatabaseConfig
from src.graph_rag.memory_sync import MemorySyncer

@pytest.fixture
def test_db_path():
    path = "./tests/test_kuzudb"
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception:
            pass
    yield path
    gc.collect() # Force garbage collection of Kuzu handles
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception:
            pass

def test_memory_sync(test_db_path):
    # Initialize DB
    db_config = DatabaseConfig(db_path=test_db_path, buffer_pool_size=1024 * 1024 * 128)
    db = KuzuDatabase(db_config)
    
    # Initialize Engine
    engine_config = MicroEngineConfig(max_nodes=10)
    engine = MicroEngine(engine_config)
    
    # Setup network with Write (3) and Read (4) nodes
    engine.add_node(0, 0, is_input=True) # Input
    engine.add_node(1, 3) # Write (Neurone-Greffier)
    engine.add_node(2, 4) # Read (Neurone-Sonde)
    engine.add_node(3, 0, is_output=True) # Output
    
    # Simple connections: Input -> Write, Read -> Output
    engine.set_weight(0, 1, 1.0)
    engine.set_weight(2, 3, 1.0)
    
    # Initialize Syncer
    syncer = MemorySyncer(db, engine)
    
    # Step 1: Forward pass, should trigger Write node since Input is 1.0 (so state > 0.5)
    outputs = engine.forward([1.0], iterations=2)
    
    # Check that memory_buffer has captured the event
    assert len(engine.memory_buffer) > 0
    node_id, activation, state = engine.memory_buffer[0]
    assert node_id == 1
    assert activation == 1.0
    assert len(state) == 10
    
    # Step 2: Sync to KuzuDB
    syncer.sync()
    
    # Buffer should be empty after sync
    assert len(engine.memory_buffer) == 0
    
    # Step 3: Now let's trick it. We want Read node to pick up the written value.
    import uuid
    test_id = str(uuid.uuid4())
    db.execute_cypher(
        f"CREATE (s:Souvenir {{id: '{test_id}', node_id: 2, activation: 0.88, state: [0.0]}})"
    )
    
    # Sync again to trigger READ PHASE
    syncer.sync()
    
    # Check if memory_cache was populated
    assert np.isclose(engine.memory_cache[2], 0.88, atol=1e-5)
    
    # Step 4: Forward pass again to verify Neurone-Sonde applies cached value
    # Needs at least 2 iterations for Read (node 2) to propagate to Output (node 3)
    outputs = engine.forward([0.0], iterations=2)
    
    # Output node 3 gets value from node 2 (Read node). Node 2 should output 0.88
    assert np.isclose(outputs[0], 0.88, atol=1e-5)
    
    # Free DB handles
    db.conn.close()
    db = None
