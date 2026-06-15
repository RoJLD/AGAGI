# tests/sandbox/test_async_logger.py
import pytest

from src.graph_rag.async_logger import AsyncLogger


def test_metrics_has_expected_keys():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    m = lg.metrics()
    for k in ("events_processed", "events_by_type", "error_count",
              "last_latency_ms", "queue_size", "running", "db_connected"):
        assert k in m
    assert m["events_processed"] == 0
    assert m["events_by_type"] == {}
    assert m["queue_size"] == 0
    assert m["running"] is False
    assert m["db_connected"] is False


def test_metrics_queue_size_reflects_pending():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    lg._running = True                 # autorise emit() sans démarrer le worker
    lg.emit("PING", {"x": 1})
    assert lg.metrics()["queue_size"] == 1


def test_run_start_sets_current_run_without_db():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    # _process_event avec conn=None ne doit pas crasher ET doit poser l'état run (en mémoire)
    lg._process_event({"type": "RUN_START", "timestamp": 1,
                       "payload": {"name": "exp", "seed": 7, "commit": "abc", "config_hash": "h"}}, None)
    assert lg._current_run == "run_7_abc"
    lg._process_event({"type": "RUN_END", "timestamp": 2, "payload": {}}, None)
    assert lg._current_run is None


def test_run_start_escapes_single_quotes_creates_node(tmp_path):
    """Non-régression: un name (et un commit) contenant une apostrophe doit
    être échappé pour Cypher; le node Run doit réellement être créé en base,
    et le lien BELONGS_TO_RUN posé par ERA_RESULT doit pointer dessus.
    Avant le fix, l'apostrophe provoquait une Parser exception (KuzuDB 0.11.3),
    le Run n'était jamais créé (ghost data) et le lien de provenance disparaissait.
    """
    kuzu = pytest.importorskip("kuzu")
    db = kuzu.Database(str(tmp_path / "prov.db"))
    conn = kuzu.Connection(db)

    # ERA_RESULT relie un Result à un Experiment préexistant : on pose le schéma.
    conn.execute("CREATE NODE TABLE Experiment(name STRING, description STRING, PRIMARY KEY (name))")
    conn.execute("CREATE NODE TABLE Result (id STRING, max_score DOUBLE, mean_score DOUBLE, ticks INT64, PRIMARY KEY (id))")
    conn.execute("CREATE REL TABLE YIELDED_RESULT (FROM Experiment TO Result)")
    conn.execute("MERGE (e:Experiment {name: 'v1'}) SET e.description = 't'")

    lg = AsyncLogger(db_path=str(tmp_path / "prov.db"))

    # name ET commit contiennent une apostrophe -> rid embarque aussi le commit
    lg._process_event(
        {"type": "RUN_START", "timestamp": 1, "payload": {
            "name": "Robin's exp", "seed": 7, "commit": "a'bc",
            "config_hash": "h'1", "git_dirty": True}},
        conn)

    runs = conn.execute("MATCH (r:Run) RETURN r.id, r.name, r.commit")
    rows = []
    while runs.has_next():
        rows.append(runs.get_next())
    assert len(rows) == 1, f"Run node non créé (ghost data): {rows}"
    rid, name, commit = rows[0]
    assert name == "Robin's exp"
    assert commit == "a'bc"
    assert rid == lg._current_run  # id stocké == id suivi en mémoire

    # ERA_RESULT doit poser BELONGS_TO_RUN vers ce Run (id échappé identiquement)
    lg._process_event(
        {"type": "ERA_RESULT", "timestamp": 2, "payload": {
            "version": "v1", "max_score": 1.0, "mean_score": 0.5,
            "ticks": 10, "best_agent_id": "none"}},
        conn)

    links = conn.execute(
        "MATCH (res:Result)-[:BELONGS_TO_RUN]->(run:Run) RETURN run.id")
    link_rows = []
    while links.has_next():
        link_rows.append(links.get_next())
    assert len(link_rows) == 1, "lien de provenance BELONGS_TO_RUN perdu"
    assert link_rows[0][0] == rid
