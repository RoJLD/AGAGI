import json

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
def test_cors_origins_default_locked() -> None:
    """Sans AGAGI_CORS_ORIGINS : allowlist dev locale (jamais '*' — cf. test_security)."""
    expected = ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert _resolve_cors_origins(None) == expected
    assert _resolve_cors_origins("") == expected
    assert _resolve_cors_origins("   ") == expected


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


def test_arm_live_progress_sets_env_and_clears_file(tmp_path) -> None:
    import os as _os
    sink = tmp_path / "live_progress.jsonl"
    env: dict = {}
    path = sandbox_service._arm_live_progress(env, str(sink))
    assert env["AGISEED_LIVE_PROGRESS"] == str(sink)
    assert _os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        assert f.read() == ""


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


def test_ws_flatland_run_id_streams_frames() -> None:
    rid = client.post("/api/flatland/runs", json={"pop_size": 2, "label": "wt"}).json()["run_id"]
    try:
        with client.websocket_connect(f"/ws/flatland/{rid}") as ws:
            frame = ws.receive_json()
            assert "agents" in frame and "summary" in frame
    finally:
        client.delete(f"/api/flatland/runs/{rid}")


def test_ws_flatland_unknown_run_closes() -> None:
    from starlette.websockets import WebSocketDisconnect
    import pytest
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/flatland/__nope__") as ws:
            ws.receive_json()


def test_list_distributions_returns_per_seed_vals(tmp_path, monkeypatch) -> None:
    """Distributions : vals par seed pour chaque condition portant la métrique ; autres exclues."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "A_0.json").write_text(json.dumps({"name": "A", "seed": 0, "data": {"fitness": 0.2}}), encoding="utf-8")
    (tmp_path / "A_1.json").write_text(json.dumps({"name": "A", "seed": 1, "data": {"fitness": 0.4}}), encoding="utf-8")
    (tmp_path / "B_0.json").write_text(json.dumps({"name": "B", "seed": 0, "data": {"autre": 9.0}}), encoding="utf-8")
    dists = rs_mod.runs_service.list_distributions("fitness")
    assert len(dists) == 1
    assert dists[0]["name"] == "A"
    assert sorted(dists[0]["vals"]) == [0.2, 0.4]
    assert dists[0]["n"] == 2

    resp = client.get("/api/runs/distributions", params={"metric": "fitness"})
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "A"


def test_run_notes_roundtrip_and_feed(tmp_path, monkeypatch) -> None:
    """Carnet : add -> list -> feed agrégé (run_name) -> delete ; texte vide rejeté ; delete absent 404."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "lewis_42.json").write_text(
        json.dumps({"name": "lewis", "seed": 42, "data": {"x": 1.0}}), encoding="utf-8"
    )

    r = client.post("/api/runs/lewis_42/notes", json={"text": "  seed 3 diverge  "})
    assert r.status_code == 200
    note = r.json()
    assert note["text"] == "seed 3 diverge"
    assert note["id"] and note["ts"]

    assert client.post("/api/runs/lewis_42/notes", json={"text": "   "}).status_code == 400

    lst = client.get("/api/runs/lewis_42/notes").json()
    assert len(lst) == 1 and lst[0]["text"] == "seed 3 diverge"

    feed = client.get("/api/notes").json()
    assert feed[0]["run_id"] == "lewis_42" and feed[0]["run_name"] == "lewis"

    assert client.delete(f"/api/runs/lewis_42/notes/{note['id']}").status_code == 200
    assert client.get("/api/runs/lewis_42/notes").json() == []
    assert client.delete("/api/runs/lewis_42/notes/nope").status_code == 404


def test_list_sweeps_extracts_knob_levels_series(tmp_path, monkeypatch) -> None:
    """Un run sweep (knob+levels+series) -> 1 SweepResult ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "lewis_survival_sweep_42.json").write_text(json.dumps({
        "name": "lewis_survival_sweep", "seed": 42, "commit": "abc1234",
        "data": {"knob": "forage_payoff", "levels": [0.1, 0.2, 0.3],
                 "median_survival": [0.2, 0.5, 0.8], "median_survival_std": [0.05, 0.05, 0.05],
                 "R": 4, "n_eval": 8},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    sweeps = rs_mod.runs_service.list_sweeps()
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s["knob"] == "forage_payoff"
    assert s["x"] == [0.1, 0.2, 0.3]
    assert s["series"]["median_survival"] == [0.2, 0.5, 0.8]
    assert s["y_std"]["median_survival"] == [0.05, 0.05, 0.05]


def test_list_decompositions_extracts_phases(tmp_path, monkeypatch) -> None:
    """Un run avec data.phases -> 1 Decomposition ; un run scalaire -> ignore."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    phases = {
        "brain": 1.0, "action": 2.0, "biologie": 9.0, "mouvement": 0.0,
        "net": 12.0, "n_agents": 40.0,
        "bio_metab": 13.47, "bio_terrain": 0.27, "bio_carry": 0.13, "bio_autres": 0.13,
    }
    (tmp_path / "lewis_drain_decompose_7.json").write_text(json.dumps({
        "name": "lewis_drain_decompose", "seed": 7, "commit": "abc1234",
        "data": {"phases": phases, "verdict": "biologie domine", "bio_verdict": "metab domine",
                 "R": 4, "n_eval": 8},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    decomps = rs_mod.runs_service.list_decompositions()
    assert len(decomps) == 1
    d = decomps[0]
    assert d["run_id"] == "lewis_drain_decompose_7"
    assert d["phases"]["bio_metab"] == 13.47
    assert d["verdict"] == "biologie domine"

    resp = client.get("/api/runs/decompositions")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "lewis_drain_decompose"
