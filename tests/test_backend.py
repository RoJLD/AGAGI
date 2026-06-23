from fastapi.testclient import TestClient

from backend.app.main import app, _resolve_cors_origins
from backend.app.services.sandbox_service import sandbox_service
from backend.app.services.runs_service import runs_service

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


# --- F3.12 sécurité (opt-in / env-gated / non-breaking par défaut) ---
def test_cors_origins_default_wildcard() -> None:
    """Sans AGAGI_CORS_ORIGINS : on garde ['*'] (comportement historique préservé)."""
    assert _resolve_cors_origins(None) == ["*"]
    assert _resolve_cors_origins("") == ["*"]
    assert _resolve_cors_origins("   ") == ["*"]


def test_cors_origins_csv_parsed() -> None:
    """Env défini : CSV -> liste d'origines (trim, vides ignorés)."""
    assert _resolve_cors_origins("https://a.test, https://b.test ,") == ["https://a.test", "https://b.test"]


def test_sandbox_rejects_non_allowlisted_script() -> None:
    """Bornage sandbox : script hors liste blanche rejeté sans lancement de process."""
    result = sandbox_service.start({"script_name": "__definitely_not_a_real_script__.py"})
    assert result["status"] == "error"
    assert "autoris" in result["message"].lower()


def test_sandbox_rejects_path_traversal() -> None:
    """Bornage sandbox : path-traversal (../) bloqué avant tout Popen."""
    result = sandbox_service.start({"script_name": "../secret.py"})
    assert result["status"] == "error"
    assert "autoris" in result["message"].lower()


def test_api_token_disabled_by_default_allows_mutation() -> None:
    """Sans AGAGI_API_TOKEN : aucune auth (la mutation n'est pas un 401 ; rejet en aval si script invalide)."""
    response = client.post("/api/sandbox/start", json={"script_name": "__no_such_script__.py"})
    assert response.status_code != 401


def test_api_token_blocks_mutation_without_header(monkeypatch) -> None:
    """Token posé + mutation sans Bearer -> 401."""
    monkeypatch.setenv("AGAGI_API_TOKEN", "secret-test-token")
    response = client.post("/api/sandbox/start", json={"script_name": "__no_such_script__.py"})
    assert response.status_code == 401


def test_api_token_allows_mutation_with_valid_header(monkeypatch) -> None:
    """Token posé + Bearer valide -> passe l'auth (pas de 401 ; rejet en aval, pas de process)."""
    monkeypatch.setenv("AGAGI_API_TOKEN", "secret-test-token")
    response = client.post(
        "/api/sandbox/start",
        json={"script_name": "__no_such_script__.py"},
        headers={"Authorization": "Bearer secret-test-token"},
    )
    assert response.status_code != 401


def test_api_token_leaves_get_free(monkeypatch) -> None:
    """Token posé : les lectures (GET) restent libres."""
    monkeypatch.setenv("AGAGI_API_TOKEN", "secret-test-token")
    response = client.get("/api/sandbox/status")
    assert response.status_code == 200


# --- Articles Sociologue <-> runs (lien par condition, store sidecar) ---
def test_article_link_roundtrip(tmp_path, monkeypatch) -> None:
    """set_article_link trie + filtre les vides ; _articles_for_condition lit l'inverse."""
    store = tmp_path / "article_links.json"
    monkeypatch.setattr(runs_service, "_article_links_path", lambda: store)
    out = runs_service.set_article_link("art_1", ["condB", "condA", ""])
    assert out == {"article_id": "art_1", "conditions": ["condA", "condB"]}
    assert runs_service._articles_for_condition("condA") == ["art_1"]
    assert runs_service._articles_for_condition("condX") == []


def test_article_links_endpoint_returns_mapping() -> None:
    response = client.get("/api/runs/article-links")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_ws_evolution_streams_appended_events(tmp_path, monkeypatch) -> None:
    sink = tmp_path / "live_progress.jsonl"
    import backend.app.main as main_mod
    monkeypatch.setattr(main_mod, "LIVE_PROGRESS_PATH", sink)
    sink.write_text('{"run":"demo","generation":1,"fitness":0.4}\n', encoding="utf-8")
    with client.websocket_connect("/ws/evolution") as ws:
        event = ws.receive_json()
        assert event["generation"] == 1
        assert event["run"] == "demo"


def test_arm_live_progress_sets_env_and_clears_file() -> None:
    import os as _os
    env: dict = {}
    path = sandbox_service._arm_live_progress(env)
    assert env["AGISEED_LIVE_PROGRESS"] == path
    assert _os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        assert f.read() == ""  # vidé au démarrage


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
