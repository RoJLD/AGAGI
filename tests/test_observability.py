# tests/test_observability.py
import json
from pathlib import Path
from backend.app.services.provenance_service import ProvenanceService


def _write_run(results_dir: Path, name: str, seed: int, kpi: float):
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{name}_{seed}.json").write_text(json.dumps(
        {"name": name, "seed": seed, "commit": "abc123", "git_dirty": False,
         "config_hash": "deadbeef", "data": {"kpi": kpi}}), encoding="utf-8")


def test_list_runs_reads_results_json(tmp_path):
    _write_run(tmp_path, "s2_demand", 2026, 0.9)
    svc = ProvenanceService(tmp_path)
    runs = svc.list_runs()
    assert len(runs) == 1
    r = runs[0]
    assert r["name"] == "s2_demand" and r["seed"] == 2026
    assert r["commit"] == "abc123" and r["config_hash"] == "deadbeef" and r["git_dirty"] is False


def test_get_run_returns_detail_and_unknown_is_none(tmp_path):
    _write_run(tmp_path, "exp", 7, 1.5)
    svc = ProvenanceService(tmp_path)
    assert svc.get_run("exp_7")["data"]["kpi"] == 1.5
    assert svc.get_run("does_not_exist") is None


def test_get_run_rejects_path_traversal(tmp_path):
    # un secret hors de results/ ne doit JAMAIS être lisible via file_stem (path traversal).
    (tmp_path.parent / "secret.json").write_text('{"seed": 0, "data": "TOPSECRET"}', encoding="utf-8")
    _write_run(tmp_path, "ok", 1, 0.5)
    svc = ProvenanceService(tmp_path)
    assert svc.get_run("../secret") is None
    assert svc.get_run("..\\secret") is None
    assert svc.get_run("../../etc/passwd") is None
    assert svc.get_run("a/b") is None
    assert svc.get_run("") is None
    assert svc.get_run("ok_1") is not None        # stem légitime toujours servi


def test_list_runs_skips_corrupt_json(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "broken_1.json").write_text("{not json", encoding="utf-8")
    _write_run(tmp_path, "ok", 1, 0.5)
    svc = ProvenanceService(tmp_path)
    names = [r["name"] for r in svc.list_runs()]
    assert "ok" in names and "broken" not in names


def test_kuzu_health_graceful_without_db(tmp_path, monkeypatch):
    import src.graph_rag.async_logger as al
    monkeypatch.setattr(al.logger, "get_db", lambda: None)
    svc = ProvenanceService(tmp_path)
    h = svc.kuzu_health()
    assert h["reachable"] is False        # pas d'exception


def test_logger_metrics_shape(tmp_path):
    svc = ProvenanceService(tmp_path)
    m = svc.logger_metrics()
    assert "queue_size" in m and "events_processed" in m


from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_kuzu_endpoint():
    r = client.get("/api/health/kuzu")
    assert r.status_code == 200
    assert "reachable" in r.json()


def test_observability_logger_endpoint():
    r = client.get("/api/observability/logger")
    assert r.status_code == 200
    assert "queue_size" in r.json()


def test_provenance_list_endpoint():
    r = client.get("/api/provenance")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_provenance_detail_unknown_returns_404():
    r = client.get("/api/provenance/__nope__")
    assert r.status_code == 404
