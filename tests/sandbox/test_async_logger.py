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
