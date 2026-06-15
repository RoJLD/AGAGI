# tests/sandbox/test_async_logger.py
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
