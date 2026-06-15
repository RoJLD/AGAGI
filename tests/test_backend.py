from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_experiments_endpoint_returns_list() -> None:
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["gate"] == "AND" for item in data)


def test_experiments_endpoint_reads_results_csv() -> None:
    response = client.get("/api/experiments/AND/history")
    assert response.status_code == 200
    payload = response.json()
    assert payload["generation"] == [1]
    assert payload["accuracy"][0] == 1.0
    assert payload["fitness"][0] > 0


def test_experiment_graph_endpoint_parses_dot_topology() -> None:
    response = client.get("/api/experiments/AND/graph")
    assert response.status_code == 200
    graph = response.json()
    assert "nodes" in graph
    assert "links" in graph
    assert len(graph["nodes"]) >= 1
    assert len(graph["links"]) >= 1


def test_experiment_summary_includes_emergent_score() -> None:
    response = client.get("/api/experiments")
    assert response.status_code == 200
    experiments = response.json()
    assert isinstance(experiments, list)
    assert any("emergent_score" in item for item in experiments)
    if experiments:
        assert experiments[0]["emergent_score"] is not None


def test_experiment_detail_includes_metrics() -> None:
    response = client.get("/api/experiments/AND")
    assert response.status_code == 200
    details = response.json()
    assert "metrics" in details
    assert details["metrics"] is not None
    assert details["metrics"]["num_nodes"] >= 1
    assert "emergent_score" in details["metrics"]
    assert "robustness_score" in details["metrics"]
    assert "performance_stability" in details["metrics"]
    assert details["metrics"]["performance_stability"] >= 0


def test_experiment_summary_includes_robustness() -> None:
    response = client.get("/api/experiments")
    assert response.status_code == 200
    experiments = response.json()
    assert isinstance(experiments, list)
    assert any("robustness_score" in item for item in experiments)
    if experiments:
        assert experiments[0]["robustness_score"] is not None


def test_academy_endpoint_returns_structure() -> None:
    response = client.get("/api/academy")
    assert response.status_code == 200
    payload = response.json()
    assert "version_history" in payload
    assert "timeline" in payload
    assert "learning_goals" in payload


def test_unknown_gate_returns_404() -> None:
    response = client.get("/api/experiments/UNKNOWN_GATE")
    assert response.status_code == 404


def test_flatland_websocket_streams_frames() -> None:
    with client.websocket_connect("/ws/flatland") as websocket:
        frame = websocket.receive_json()
        assert isinstance(frame, dict)
        assert "ticks" in frame
        assert "size" in frame
        assert "agents" in frame
        assert "preys" in frame
        assert frame["agents"] is not None
        assert frame["preys"] is not None
        assert "summary" in frame
        summary = frame["summary"]
        assert summary["agent_count"] == len(frame["agents"])
        assert summary["prey_count"] == len(frame["preys"])
        assert summary["avg_energy"] >= 0.0
        assert summary["avg_hp"] >= 0.0
        assert "energy_std" in summary
        assert "hp_std" in summary
        assert "social_density" in summary
        assert "genome_diversity" in summary


def test_flatland_runs_crud() -> None:
    r = client.post("/api/flatland/runs", json={"config_overrides": {"size": 16}, "pop_size": 2, "label": "e2e"})
    assert r.status_code == 200
    rid = r.json()["run_id"]
    try:
        lst = client.get("/api/flatland/runs").json()
        assert any(x["run_id"] == rid and x["label"] == "e2e" for x in lst)
    finally:
        d = client.delete(f"/api/flatland/runs/{rid}")
        assert d.status_code == 200 and d.json()["stopped"] is True


def test_flatland_delete_unknown_returns_404() -> None:
    assert client.delete("/api/flatland/runs/__nope__").status_code == 404


def test_flatland_bad_override_returns_400() -> None:
    r = client.post("/api/flatland/runs", json={"config_overrides": {"evil_key": 1}, "pop_size": 2})
    assert r.status_code == 400
