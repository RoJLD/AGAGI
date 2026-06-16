# tests/test_strategy.py
import gc

from fastapi.testclient import TestClient


def _empty_schema_db(tmp_path):
    """KuzuDB temp avec le schéma (Article/WorldVersion/...) mais AUCUNE donnée de stratégie."""
    from src.graph_rag.experiment_tracker import ExperimentGraph
    db_path = str(tmp_path / "strat.db")
    g = ExperimentGraph(db_path, read_only=False)   # bootstrap schema, pas de WorldVersion
    del g.conn
    del g.db
    gc.collect()
    return db_path


def test_strategy_tree_is_honest_when_empty(tmp_path, monkeypatch):
    db_path = _empty_schema_db(tmp_path)
    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", db_path)
    from backend.app.main import app
    client = TestClient(app)
    body = client.get("/api/strategy/strategy_tree").json()
    # plus AUCUN mock fantôme
    assert "StoneAge (Mock)" not in str(body)
    assert "Tabula_Rasa" not in str(body)
    # flag de source explicite
    assert body["source"] in ("empty", "error")
    assert body["tree"] == {} and body["sankey"]["nodes"] == []
