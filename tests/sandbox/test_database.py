import os
import sys
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.graph_rag.database import KuzuDatabase, DatabaseConfig

def test_kuzu_database_bootstrap():
    """
    Validates that KuzuDB can spin up locally, create the schema,
    and survive multiple idempotent bootstrap calls without crashing.
    """
    test_db_dir = "./data/test_kuzudb_dir"
    test_db_path = f"{test_db_dir}/test.db"
    
    # Clean up before
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    config = DatabaseConfig(db_path=test_db_path, buffer_pool_size=1024 * 1024 * 100) # 100MB
    db = KuzuDatabase(config)
    
    # First bootstrap
    db.bootstrap_schema()
    assert os.path.exists(test_db_dir), "bootstrap_schema n'a rien cree sur disque"

    # Second bootstrap to test idempotency (2026-09-02 : la docstring promettait « survive multiple
    # idempotent bootstrap calls » sans rien asserter -- un echec silencieux ressemblait a un succes)
    db.bootstrap_schema()
    assert os.path.exists(test_db_dir), "le second bootstrap a detruit la base"
    
    # Clean up after
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
