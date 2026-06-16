# tests/test_sociologist.py
import gc

from fastapi.testclient import TestClient


def _article_db(tmp_path):
    """KuzuDB temp avec le schéma Article(id,title,content,date) + 1 article."""
    from src.graph_rag.experiment_tracker import ExperimentGraph
    db_path = str(tmp_path / "soc.db")
    g = ExperimentGraph(db_path, read_only=False)
    g.conn.execute(
        "CREATE (a:Article {id: 'a1', title: 'T1', content: 'C1', date: '2026-06-16 10:00:00'})")
    del g.conn
    del g.db
    gc.collect()
    return db_path


def test_sociologist_articles_returns_real_article(tmp_path, monkeypatch):
    db_path = _article_db(tmp_path)
    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", db_path)
    from backend.app.main import app
    client = TestClient(app)
    r = client.get("/api/sociologist/articles")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "a1" and data[0]["date"] == "2026-06-16 10:00:00"
