import copy
import json
import os
import subprocess
import sys
import time

import pytest
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


def test_P2_81_le_puits_de_progression_du_backend_est_celui_que_le_lanceur_arme() -> None:
    """P2.81 : `main.py:68` résolvait la racine par `parents[3]`, forme copiée des routes qui vivent un
    niveau PLUS PROFOND — pour `main.py` c'est le dossier PARENT du dépôt. Mesuré le 2026-09-22 :
    `C:/Users/robla/VScode_Project/results`, qui n'existe pas. Le WS `/ws/evolution` taillait donc un
    fichier que le lanceur n'écrit jamais, depuis le commit initial.

    ⚠️ Ce test NE DOIT PAS appeler `_arm_live_progress` : elle fait `os.makedirs` puis `open(path, "w")`
    sur le VRAI `<dépôt>/results/live_progress.jsonl` — elle TRONQUERAIT la progression d'un run en vol,
    et un test deviendrait writer d'un fichier partagé. On compare au helper PUR.
    """
    from pathlib import Path
    from backend.app import main as main_mod
    from backend.app.services import sandbox_service as sb

    assert Path(main_mod.LIVE_PROGRESS_PATH) == Path(sb.default_live_progress_path())
    assert Path(main_mod.RESULTS_DIR).name == "results"
    assert (Path(main_mod.RESULTS_DIR).parent / "tools" / "hooks" / "pre-commit").exists(), (
        "la racine du backend doit être le DÉPÔT : son parent doit porter tools/hooks/pre-commit")


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


def test_flatland_runs_crud(sans_bail_etranger) -> None:
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


def test_ws_flatland_run_id_streams_frames(sans_bail_etranger) -> None:
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


def test_list_forage_funnels_extracts_levels(tmp_path, monkeypatch) -> None:
    """Un run d'entonnoir (data.table par niveau) -> 1 ForageFunnel ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    agg0 = {"p_reach": 0.18, "p_cap": 1.0, "income_t": 0.5, "drain_t": 0.2,
            "mean_captures": 1.2, "mean_contacts": 6.5, "mean_min_dist": 3.1, "n_agents": 40}
    agg25 = {"p_reach": 0.12, "p_cap": 1.0, "income_t": 0.3, "drain_t": 0.4,
             "mean_captures": 0.8, "mean_contacts": 5.0, "mean_min_dist": 3.6, "n_agents": 38}
    (tmp_path / "lewis_forage_funnel_7.json").write_text(json.dumps({
        "name": "lewis_forage_funnel", "seed": 7, "commit": "abc1234",
        "data": {"knob": "base_metab", "metab_levels": [0.0, 0.25], "verdict": "APPROCHE casse",
                 "R": 4, "n_eval": 8, "table": {"0.0": agg0, "0.25": agg25}},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    funnels = rs_mod.runs_service.list_forage_funnels()
    assert len(funnels) == 1
    f = funnels[0]
    assert f["run_id"] == "lewis_forage_funnel_7"
    assert [lv["metab"] for lv in f["levels"]] == [0.0, 0.25]
    assert f["levels"][0]["p_reach"] == 0.18
    assert f["verdict"] == "APPROCHE casse"

    resp = client.get("/api/runs/forage-funnels")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "lewis_forage_funnel"


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


def test_flatland_server_does_not_reuse_a_CLOSED_event_loop() -> None:
    """Flake d'ordre de la suite complète (2026-09-16) : un test précédent laisse une boucle FERMÉE comme boucle
    courante ; `asyncio.get_event_loop()` la rend, et le serveur mourait sur « Event loop is closed ». Gelé :
    boucle courante fermée -> le serveur en crée une neuve ; boucle ouverte -> il la garde (no-op apparié).
    Le thread de simulation n'est PAS lancé (patch de `threading.Thread.start`) : on teste le CHOIX de boucle."""
    import asyncio
    import threading
    from backend.app.flatland_server import FlatlandServer
    orig_start = threading.Thread.start
    threading.Thread.start = lambda self: None            # pas de simulation : seul le choix de boucle compte
    try:
        fermee = asyncio.new_event_loop()
        fermee.close()
        asyncio.set_event_loop(fermee)
        srv = FlatlandServer(pop_size=1, config_overrides={"size": 16})
        srv.start()
        assert srv.loop is not fermee and not srv.loop.is_closed()
        srv.stop()
        ouverte = asyncio.new_event_loop()
        asyncio.set_event_loop(ouverte)
        srv2 = FlatlandServer(pop_size=1, config_overrides={"size": 16})
        srv2.start()
        assert srv2.loop is ouverte
        srv2.stop()
        ouverte.close()
    finally:
        threading.Thread.start = orig_start
        asyncio.set_event_loop(asyncio.new_event_loop())


def _sources_du_pilotage() -> tuple[str, dict[str, str]]:
    """Chemins des cinq sources du pilotage, construits SANS les lecteurs de `tools/pm/pilotage.py` (F2).

    La racine vient de CE fichier de test, le dépôt commun d'un appel `git rev-parse --git-common-dir`
    fait ICI, et les chemins relatifs de l'accesseur `src.paths` (ou d'`AGAGI_DATA_ROOT` si elle est
    posée) — jamais de `read_board` / `read_roles_counts` / `read_records_graph`, qui sont l'instrument
    sous test : un lecteur qui rend faussement `None` ferait juger la source absente et SAUTER
    l'assertion (oracle circulaire, prouvé par la re-revue sous la reversion de C1)."""
    from src import paths

    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
    commun = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=racine, capture_output=True,
                            encoding="utf-8", check=True).stdout.strip()
    if not os.path.isabs(commun):
        commun = os.path.join(racine, commun)
    racine_commune = os.path.dirname(os.path.realpath(commun))
    base_pm = racine if os.environ.get("AGAGI_DATA_ROOT") else racine_commune

    def _ancre(base: str, rel: str) -> str:
        return rel if os.path.isabs(rel) else os.path.join(base, rel)

    return racine, {
        "PRIORITES_ET_DETTES.md": os.path.join(racine, "docs", "roadmap", "PRIORITES_ET_DETTES.md"),
        "records_graph.json": _ancre(racine, paths.results_file("records_graph.json")),
        "ROLES_COUNTS.json": _ancre(base_pm, paths.pm_dir("ROLES_COUNTS.json")),
        "BOARD.json": _ancre(base_pm, paths.pm_dir("BOARD.json")),
        "pre-commit": os.path.join(racine, "tools", "hooks", "pre-commit"),
    }


def test_pilotage_endpoint_rend_le_schema() -> None:
    """Bout-en-bout sur la vraie app et les vraies sources. Les quatre assertions d'origine (200, schéma,
    `generated_at` numérique, `aveugle` liste) sont satisfaites par le dict de MODE DÉGRADÉ du service
    lui-même ; `_vider_cache()` en entrée (le cache est un état de PROCESSUS), la roadmap NON `null` (elle
    est TOUJOURS calculable dans ce dépôt) et aucune ligne `aveugle` ne doit nommer une source dont le
    fichier EXISTE.

    Ce que ce test vérifie, et rien de plus : la PRÉSENCE est jugée par `os.path.isfile` sur des chemins
    construits hors de `pilotage.py` (`_sources_du_pilotage`). Sur une machine où `BOARD.json` et
    `ROLES_COUNTS.json` existent (dépôt commun), il rougit si le service les déclare absents — prouvé sous
    la mutation « ancrer sur `repo_root` » (F2). Là où ils n'existent pas (CI), la branche jugeait RIEN, sans
    aucun signal (G6) : elle juge désormais le sens réciproque — une source ABSENTE selon l'oracle doit être
    NOMMÉE par une ligne `aveugle` (prouvé sous un mutant qui supprime la ligne « introuvable » du board, avec
    `AGAGI_DATA_ROOT` pointée vers un répertoire vide). L'ancrage lui-même reste tenu, en CI, par les tests
    hermétiques de `tests/sandbox/test_pm_pilotage.py`."""
    from backend.app.services import pilotage_service as ps

    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "pilotage_v1"
    assert isinstance(d["generated_at"], (int, float))
    assert isinstance(d["aveugle"], list)
    assert d["roadmap"] is not None, f"la roadmap est TOUJOURS calculable dans ce dépôt : {d['aveugle']}"

    racine, chemins = _sources_du_pilotage()
    assert d["repo_root"] == racine, (d["repo_root"], racine)
    for nom, chemin in chemins.items():
        if os.path.isfile(chemin):
            assert not any(nom in a for a in d["aveugle"]), (
                f"ligne aveugle nommant {nom!r} alors que {chemin} EXISTE sur le disque : {d['aveugle']}")
        else:
            # G6 : le sens RÉCIPROQUE. Sans lui, là où la source manque (CI : pas de data/pm/), la boucle ne
            # jugeait RIEN et l'exécution n'en montrait aucun signal ; désormais elle juge partout.
            assert any(nom in a for a in d["aveugle"]), (
                f"{nom!r} est ABSENT du disque ({chemin}) et AUCUNE ligne aveugle ne le nomme : {d['aveugle']}")


def test_pilotage_n_ecrit_JAMAIS_AGAGI_DATA_ROOT_dans_l_environnement(monkeypatch) -> None:
    """F1, contre-exemple GELÉ : `read_board` et `read_roles_counts` appelaient `ancrer_data_root`, qui
    ÉCRIT `os.environ["AGAGI_DATA_ROOT"]`. Dans un CLI court c'est un choix ; dans le processus uvicorn,
    mesuré par la re-revue, UN poll faisait basculer `paths.data_root()` / `paths.db_root()` (KuzuDB,
    génomes, HoF) vers le `data/` COMMUN pour TOUT le processus, et tout enfant lancé avec
    `os.environ.copy()` en héritait. L'ancrage doit être une résolution PURE.

    Isolation : sentinelle setenv PUIS delenv, pour qu'une écriture éventuelle soit défaite en fin de test
    et ne fuie pas vers la suite de la session."""
    from backend.app.services import pilotage_service as ps
    from tools.pm import pilotage as P

    monkeypatch.setenv("AGAGI_DATA_ROOT", "sentinelle-a-effacer")
    monkeypatch.delenv("AGAGI_DATA_ROOT", raising=False)
    racine = P.racine_depot()
    P.read_board(racine)
    assert "AGAGI_DATA_ROOT" not in os.environ, f"read_board a ÉCRIT l'environnement : {os.environ['AGAGI_DATA_ROOT']}"
    P.read_roles_counts(racine)
    assert "AGAGI_DATA_ROOT" not in os.environ, (
        f"read_roles_counts a ÉCRIT l'environnement : {os.environ['AGAGI_DATA_ROOT']}")
    ps._vider_cache()
    ps.get_pilotage()
    assert "AGAGI_DATA_ROOT" not in os.environ, (
        f"get_pilotage a ÉCRIT l'environnement : {os.environ['AGAGI_DATA_ROOT']}")


def test_pilotage_le_POLL_ne_recalcule_JAMAIS_le_snapshot(monkeypatch) -> None:
    """La mesure qui a changé le design : `snapshot()` coûte 15,6-18,1 s (charge notée : 40 % CPU,
    9 processus python) alors qu'`apiFetch` coupe à 10 s et que toute la roadmap coûte 0,70 s. Le poll ne
    doit donc jamais l'appeler — seul `?frais=1` le fait.

    ⚠️ Le compteur est indispensable, et l'assertion porte sur LUI : le filet d'exception du service
    (toute exception -> une ligne `aveugle`, jamais un 500) attrape l'AssertionError du monkeypatch, donc
    un test qui n'assert que le statut 200 passerait même si la régression était réintroduite — vérifié
    par la revue en simulant l'appel inconditionnel. Le `raise` reste pour documenter l'intention ; c'est
    `appels["n"] == 0` qui garde la propriété."""
    from backend.app.services import pilotage_service as ps

    appels = {"n": 0}

    def _interdit(*a, **k):
        appels["n"] += 1
        raise AssertionError("snapshot() appelé sur le chemin du poll : 18 s par requête")

    monkeypatch.setattr(ps, "snapshot", _interdit)
    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200
    assert appels["n"] == 0, "snapshot() a été appelé sur le chemin du poll (18 s par requête)"


def test_pilotage_un_lecteur_qui_leve_devient_une_ligne_aveugle_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import pilotage_service as ps

    def _boum(*a, **k):
        raise RuntimeError("lecteur casse")

    monkeypatch.setattr(ps.pilotage, "compute_pilotage", _boum)
    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200, "une exception ne doit jamais devenir un 500"
    d = r.json()
    assert d["aveugle"] and d["aveugle"][0].startswith("pilotage:")
    assert d["flotte"] is None and d["roadmap"] is None and d["portes"] is None and d["charge"] is None


def test_pilotage_frais_est_REFUSE_quand_une_simulation_est_en_vol(monkeypatch) -> None:
    """IMPORTANT 6 (spec §5) : `?frais=1` pendant qu'une simulation tourne doit être REFUSÉ et DIT, jamais
    silencieux -- et le refus se juge sur le DERNIER tableau CONNU (`BOARD.json`), jamais sur un nouveau
    `snapshot()` (18 s, exactement le coût que le refus évite d'engager).

    F4 : le `raise` seul ne verrouillait rien. Mesuré par la re-revue : un mutant qui ajoute la ligne de
    refus mais OUBLIE `effectif = False` appelle `snapshot()`, dont l'exception est avalée par le filet du
    service (200) — le test restait VERT. C'est le piège déjà payé sur ce lot (31785f77) : « faire lever »
    s'inverse en aval d'un filet d'exception ; seul un compteur incrémenté AVANT le `raise` survit. D'où
    `appels == 0` et aucune ligne `pilotage:` (la trace du filet)."""
    from backend.app.services import pilotage_service as ps

    appels = {"n": 0}

    def _interdit(*a, **k):
        appels["n"] += 1
        raise AssertionError("snapshot() a été appelé alors que sims_en_vol > 0 -- le refus doit l'éviter")

    monkeypatch.setattr(ps, "snapshot", _interdit)
    monkeypatch.setattr(ps.pilotage, "read_board", lambda racine: {
        "generated_at": time.time(), "sessions": [],
        "charge_connue": {"sims_en_vol": 2, "cpu_pct": 50.0, "bails_vivants": []}})
    ps._vider_cache()
    r = client.get("/api/pm/pilotage?frais=1")
    assert r.status_code == 200
    d = r.json()
    assert any("frais" in a and "refus" in a.lower() for a in d["aveugle"]), d["aveugle"]
    assert appels["n"] == 0, "snapshot() a été APPELÉ malgré le refus -- le filet du service l'a masqué"
    assert not any(a.startswith("pilotage:") for a in d["aveugle"]), d["aveugle"]


def test_pilotage_frais_PROCEDE_quand_aucune_simulation_n_est_en_vol(monkeypatch) -> None:
    """Contrôle positif du refus précédent : `sims_en_vol == 0` ne bloque rien, `frais=1` appelle bien
    `snapshot()` (`snapshot` est monkeypatché en version RAPIDE : le vrai coûte 15-18 s, hors de propos
    ici -- seul le fait qu'il soit APPELÉ, donc pas refusé, est sous test)."""
    from backend.app.services import pilotage_service as ps

    appels = {"n": 0}

    def _faux_snapshot(racine):
        appels["n"] += 1
        return {"now": time.time(), "repo_root": racine, "psutil": False, "registry": None,
                "bulletins": None, "worktrees": None, "commits": None, "leases": None,
                "processes": None, "cpu_pct": None, "backlog_paths": None, "hook_errors": None}

    monkeypatch.setattr(ps, "snapshot", _faux_snapshot)
    monkeypatch.setattr(ps.pilotage, "read_board", lambda racine: {
        "generated_at": time.time(), "sessions": [],
        "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []}})
    ps._vider_cache()
    r = client.get("/api/pm/pilotage?frais=1")
    assert r.status_code == 200
    d = r.json()
    assert appels["n"] == 1, "frais=1 sans simulation en vol doit appeler snapshot() (pas de refus)"
    assert not any("refus" in a.lower() for a in d["aveugle"]), d["aveugle"]
    assert not any("SANS mesure de charge" in a for a in d["aveugle"]), "la charge a été MESURÉE (0 sim)"


def _faux_snapshot_rapide(appels):
    def _snap(racine):
        appels["n"] += 1
        return {"now": time.time(), "repo_root": racine, "psutil": False, "registry": None,
                "bulletins": None, "worktrees": None, "commits": None, "leases": None,
                "processes": None, "cpu_pct": None, "backlog_paths": None, "hook_errors": None}
    return _snap


@pytest.mark.parametrize("dernier", [
    None,                                                                          # BOARD.json absent
    [1, 2],                                                                        # illisible
    {"generated_at": 1.0, "sessions": [], "charge_connue": {"sims_en_vol": None}},  # charge non mesurée
    {"generated_at": 1.0, "sessions": [], "charge_connue": {"sims_en_vol": True}},  # un booléen n'est pas un compte
    # G8 : un entier JSON de plus de 309 chiffres fait lever OverflowError à math.isfinite — l'exception
    # aveuglait TOUT le pilotage au lieu d'être une non-mesure.
    json.loads('{"generated_at": 1.0, "sessions": [], "charge_connue": {"sims_en_vol": 1' + "0" * 400 + "}}"),
])
def test_pilotage_frais_SANS_mesure_de_charge_est_ACCEPTE_mais_DIT(monkeypatch, dernier) -> None:
    """F6 : sans dernier tableau lisible, `frais=1` lançait le recalcul de 15-18 s sans dire que la charge
    était INCONNUE — un refus se prononce sur une mesure, donc l'absence de mesure n'est pas un refus, mais
    elle ne passe pas pour un « 0 simulation en vol » : elle se dit."""
    from backend.app.services import pilotage_service as ps

    appels = {"n": 0}
    monkeypatch.setattr(ps, "snapshot", _faux_snapshot_rapide(appels))
    monkeypatch.setattr(ps.pilotage, "read_board", lambda racine: copy.deepcopy(dernier))
    ps._vider_cache()
    r = client.get("/api/pm/pilotage?frais=1")
    assert r.status_code == 200
    d = r.json()
    assert appels["n"] == 1, "sans mesure, frais=1 n'est pas refusé"
    assert any("SANS mesure de charge" in a and "aveugle" in a for a in d["aveugle"]), d["aveugle"]
    assert not any(a.startswith("pilotage:") for a in d["aveugle"]), d["aveugle"]


def test_pilotage_racine_depot_qui_LEVE_devient_une_ligne_aveugle_jamais_un_500(monkeypatch) -> None:
    """F7 : `racine_depot()` était appelé HORS du filet d'exception — monkeypatché pour lever, il donnait
    un 500. En mode dégradé, `repo_root` porte la racine si elle a été résolue, `None` sinon (ici)."""
    from backend.app.services import pilotage_service as ps

    def _boum():
        raise RuntimeError("racine casse")

    monkeypatch.setattr(ps.pilotage, "racine_depot", _boum)
    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200, "une exception ne doit jamais devenir un 500"
    d = r.json()
    assert d["aveugle"] and d["aveugle"][0].startswith("pilotage:") and "racine casse" in d["aveugle"][0]
    assert d["repo_root"] is None
    assert d["flotte"] is None and d["roadmap"] is None and d["portes"] is None and d["charge"] is None


def test_pilotage_lecture_de_charge_qui_LEVE_sous_frais_jamais_un_500(monkeypatch) -> None:
    """F7 : `_sims_en_vol_dernier_tableau` était lui aussi hors du filet. La racine, résolue AVANT
    l'exception, est portée par le mode dégradé ; `snapshot()` n'est pas atteint."""
    from backend.app.services import pilotage_service as ps
    from tools.pm import pilotage as P

    appels = {"n": 0}

    def _boum(racine):
        raise RuntimeError("tableau casse")

    monkeypatch.setattr(ps, "_sims_en_vol_dernier_tableau", _boum)
    monkeypatch.setattr(ps, "snapshot", _faux_snapshot_rapide(appels))
    ps._vider_cache()
    r = client.get("/api/pm/pilotage?frais=1")
    assert r.status_code == 200, "une exception ne doit jamais devenir un 500"
    d = r.json()
    assert d["aveugle"][0].startswith("pilotage:") and "tableau casse" in d["aveugle"][0], d["aveugle"]
    assert d["repo_root"] == P.racine_depot()
    assert appels["n"] == 0


def _json_ou_none(chemin):
    try:
        with open(chemin, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _donnees_de_base():
    """Copie des données RÉELLES (lues par `_sources_du_pilotage`, jamais par les lecteurs sous test) ; en
    CI, où `data/pm/` n'existe pas, un tableau et des compteurs SYNTHÉTIQUES de même forme que ceux du
    tick PM (`board.compute`, `roles_counts.compute_counts`), pour que le test tourne partout."""
    _racine, chemins = _sources_du_pilotage()
    board = _json_ou_none(chemins["BOARD.json"])
    if not (isinstance(board, dict) and isinstance(board.get("charge_connue"), dict)):
        board = {"generated_at": time.time(), "repo_root": _racine, "aveugle": [], "sessions": [],
                 "sessions_mortes": [], "alertes": [],
                 "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": ["pm"]},
                 "worktrees": [], "bails": None}
    roles = _json_ou_none(chemins["ROLES_COUNTS.json"])
    if not isinstance(roles, dict):
        roles = {"generated_at": time.time(), "depuis": "2026-09-16",
                 "fenetre": {"depuis": "2026-08-25", "jours": 30}, "alertes": {"emises": 0},
                 "fichiers": {"science": 2, "methodo": 2, "autre": 1}, "ratio_science_methodo": 1.0,
                 "fichiers_disponibles": True}
    graphe = _json_ou_none(chemins["records_graph.json"])
    if not (isinstance(graphe, dict) and isinstance(graphe.get("roadmap"), dict)):
        graphe = {"roadmap": {"G0": {"status": "validated"}}}
    return board, roles, graphe


def _servir(monkeypatch, board, roles, graphe, cl=None):
    from backend.app.services import pilotage_service as ps

    monkeypatch.setattr(ps.pilotage, "read_board", lambda racine: board)
    monkeypatch.setattr(ps.pilotage, "read_roles_counts", lambda racine: roles)
    monkeypatch.setattr(ps.pilotage, "read_records_graph", lambda racine: graphe)
    ps._vider_cache()
    return (cl or client).get("/api/pm/pilotage")


# Un client qui REND le 500 au lieu de relever l'exception serveur dans le test : c'est le statut que le
# navigateur verrait, et le seul moyen de constater qu'un défaut de rendu en est un (G2, G4).
client_500 = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("source,champ,valeur", [
    ("board", "cpu_pct", "n/a"),
    ("board", "bails_vivants", [{"x": 1}]),
    ("board", "sims_en_vol", 1.5),
    ("roles", "ratio_science_methodo", "inf"),
    ("roles", "fenetre", 30),
    ("roles", "fichiers", {"science": None, "methodo": 1, "autre": 2}),
])
def test_pilotage_un_champ_de_TYPE_inattendu_n_aveugle_que_charge_jamais_un_500(monkeypatch, source, champ,
                                                                              valeur) -> None:
    """F3 : `Charge` recopie des champs de `BOARD.json` et de `ROLES_COUNTS.json`, sources qui
    n'appartiennent pas à `pilotage.py`. Mesuré par la re-revue : UN champ de type inattendu donnait un 500
    à la sérialisation de la réponse, APRÈS le filet du service, sans ligne d'aveuglement. Chaque cas part
    d'une copie des données réelles avec UN SEUL champ changé : 200, `charge` à `null`, une ligne qui NOMME
    le bloc, les autres blocs servis."""
    board, roles, graphe = _donnees_de_base()
    if source == "board":
        board["charge_connue"][champ] = valeur
    else:
        roles[champ] = valeur
    r = _servir(monkeypatch, board, roles, graphe)
    assert r.status_code == 200, "un refus du modèle de la route ne doit jamais devenir un 500"
    d = r.json()
    assert d["charge"] is None, d["charge"]
    assert any(a.startswith("charge") and "refus" in a for a in d["aveugle"]), d["aveugle"]
    assert d["flotte"] is not None and d["roadmap"] is not None and d["portes"] is not None


def test_pilotage_portes_agi_de_FORME_inattendue_n_aveugle_que_portes_agi(monkeypatch) -> None:
    """F3 : `Roadmap.portes_agi` recopie `records_graph["roadmap"]` — source étrangère. Une liste à la place
    du dict donnait un 500. `portes_agi` seul tombe à `null`, NOMMÉ ; la roadmap du backlog reste servie."""
    board, roles, graphe = _donnees_de_base()
    graphe["roadmap"] = []
    r = _servir(monkeypatch, board, roles, graphe)
    assert r.status_code == 200, "un refus du modèle de la route ne doit jamais devenir un 500"
    d = r.json()
    assert d["roadmap"] is not None and d["roadmap"]["portes_agi"] is None
    assert any("portes_agi" in a for a in d["aveugle"]), d["aveugle"]
    assert d["flotte"] is not None and d["portes"] is not None and d["charge"] is not None


def test_pilotage_controle_la_copie_INTACTE_des_donnees_est_servie_sans_refus(monkeypatch) -> None:
    """Contrôle des deux tests précédents : la MÊME copie, sans champ changé, est servie en entier — sinon
    un refus serait l'effet du dispositif, pas du champ modifié."""
    board, roles, graphe = _donnees_de_base()
    r = _servir(monkeypatch, board, roles, graphe)
    assert r.status_code == 200
    d = r.json()
    assert not any("refus" in a for a in d["aveugle"]), d["aveugle"]
    assert all(d[k] is not None for k in ("flotte", "roadmap", "portes", "charge")), d["aveugle"]
    assert d["roadmap"]["portes_agi"] == graphe["roadmap"]


@pytest.mark.parametrize("source,champ,valeur,blocs", [
    # `charge_connue` est RECOPIÉE dans les deux blocs (`flotte` = le board, `charge` = ses trois champs) :
    # la valeur fautive est servie deux fois, les deux blocs tombent, et eux seuls.
    ("board_cc", "bails_vivants", ["\ud800"], ("flotte", "charge")),
    ("roles", "fenetre", {"x": "\ud800"}, ("charge",)),
    ("board", "zz", "a\ud800b", ("flotte",)),
    ("board", "aveugle", ["x\udc80"], ("flotte",)),
    ("graphe", "G0", "\udfff", ("portes_agi",)),
])
def test_pilotage_un_SURROGATE_isole_n_aveugle_que_son_bloc_jamais_un_500(monkeypatch, source, champ, valeur,
                                                                          blocs) -> None:
    """G2 : `_servable` rejouait validation, dump et `json.dumps(allow_nan=False)`, mais pas le
    `.encode("utf-8")` de `JSONResponse.render`. Mesuré : une chaîne portant un surrogate isolé (ce que
    `json.load` rend pour `"\\ud800"`) passait le filet par bloc ET celui d'enveloppe, puis donnait un 500 —
    les cinq cas ci-dessous. Chacun : 200, le ou les blocs qui PORTENT la valeur à `null`, une ligne qui
    NOMME chacun, les autres servis. `portes_agi` est un sous-bloc (source étrangère : `records_graph.json`) :
    seul lui tombe, jamais toute la roadmap (même règle que la couche 2 de F3)."""
    board, roles, graphe = _donnees_de_base()
    if source == "board_cc":
        board["charge_connue"][champ] = valeur
    elif source == "board":
        board[champ] = valeur
    elif source == "roles":
        roles[champ] = valeur
    else:
        graphe["roadmap"][champ] = valeur
    r = _servir(monkeypatch, board, roles, graphe, cl=client_500)
    assert r.status_code == 200, f"un surrogate isolé a donné {r.status_code}"
    d = r.json()
    for bloc in blocs:
        if bloc == "portes_agi":
            assert d["roadmap"] is not None and d["roadmap"]["portes_agi"] is None, d["aveugle"]
        else:
            assert d[bloc] is None, d[bloc]
        assert any(a.startswith(bloc) and "refus" in a for a in d["aveugle"]), (bloc, d["aveugle"])
    autres = tuple(k for k in ("flotte", "roadmap", "portes", "charge") if k not in blocs)
    assert all(d[k] is not None for k in autres), d["aveugle"]
    assert not any(a.startswith("pilotage:") for a in d["aveugle"]), d["aveugle"]


@pytest.mark.parametrize("cas", ["message_a_surrogate", "racine_Path"])
def test_pilotage_le_MODE_DEGRADE_est_lui_meme_servable_jamais_un_500(monkeypatch, cas) -> None:
    """G2 : le dict du mode dégradé n'était validé par rien. Une exception dont le message porte un surrogate
    isolé, ou un `racine_depot` qui rend un `Path` (sa `.replace` n'est pas celle d'une chaîne : TypeError,
    puis `repo_root` non-chaîne dans le dict dégradé), donnaient un 500. La ligne est rendue ENCODABLE
    (échappement visible `\\ud800`, jamais une suppression) et `repo_root` est une chaîne POSIX."""
    from backend.app.services import pilotage_service as ps
    from tools.pm import pilotage as P
    import pathlib

    vraie = P.racine_depot()
    if cas == "message_a_surrogate":
        def _racine():
            raise RuntimeError("racine casse \ud800 ici")
    else:
        def _racine():
            return pathlib.Path(vraie)
    monkeypatch.setattr(ps.pilotage, "racine_depot", _racine)
    ps._vider_cache()
    r = client_500.get("/api/pm/pilotage")
    assert r.status_code == 200, f"le mode dégradé a donné {r.status_code}"
    d = r.json()
    assert d["aveugle"] and d["aveugle"][0].startswith("pilotage:"), d["aveugle"]
    assert d["flotte"] is None and d["roadmap"] is None and d["portes"] is None and d["charge"] is None
    if cas == "message_a_surrogate":
        assert "racine casse \\ud800 ici" in d["aveugle"][0], d["aveugle"]
        assert d["repo_root"] is None
    else:
        assert d["repo_root"] == vraie, d["repo_root"]


@pytest.mark.parametrize("source,modif,bloc,chemin", [
    ("board", lambda b, r, g: b.__setitem__("sessions", [{"x": [1.0, float("nan")]}]), "flotte",
     "flotte.sessions[0].x[1]"),
    ("graphe", lambda b, r, g: g["roadmap"].__setitem__("G0", {"score": float("inf")}), "portes_agi",
     "roadmap.portes_agi.G0.score"),
    ("roles", lambda b, r, g: r.__setitem__("fenetre", {"depuis": "2026-08-25", "jours": float("nan")}),
     "charge", "charge.fenetre.jours"),
])
def test_pilotage_un_float_NON_FINI_imbrique_est_REFUSE_et_NOMME_jamais_un_null_muet(monkeypatch, source, modif,
                                                                                     bloc, chemin) -> None:
    """G3 : pydantic, en mode json, sert à `null` SANS ligne un `nan` ou un `inf` placé dans un champ `Any`
    (`flotte`, `portes_agi`, `fenetre`) — alors qu'un `inf` dans un champ `float` déclaré
    (`ratio_science_methodo`) est, lui, refusé et nommé. Une pré-passe sur le bloc BRUT refuse le bloc et
    NOMME le chemin du premier non-fini. Mesuré sur HEAD : 200, `null`, aucune ligne."""
    board, roles, graphe = _donnees_de_base()
    modif(board, roles, graphe)
    r = _servir(monkeypatch, board, roles, graphe, cl=client_500)
    assert r.status_code == 200
    d = r.json()
    if bloc == "portes_agi":
        assert d["roadmap"] is not None and d["roadmap"]["portes_agi"] is None, d["roadmap"] and d["roadmap"]["portes_agi"]
        autres = ("flotte", "portes", "charge")
    else:
        assert d[bloc] is None, d[bloc]
        autres = tuple(k for k in ("flotte", "roadmap", "portes", "charge") if k != bloc)
    lignes = [a for a in d["aveugle"] if a.startswith(bloc) and "non fini" in a]
    assert len(lignes) == 1 and chemin in lignes[0], (chemin, d["aveugle"])
    assert all(d[k] is not None for k in autres), d["aveugle"]


def test_la_pre_passe_NON_FINI_voit_cles_tuples_et_profondeur_et_se_tait_sur_le_fini() -> None:
    """G3, unitaire : la pré-passe parcourt dict (CLÉS comprises), liste et tuple à toute profondeur ; elle rend
    le chemin du PREMIER non-fini, `None` sur une structure finie (contrôle), et refuse une structure
    cyclique au lieu de boucler."""
    from backend.app.services import pilotage_service as ps

    assert ps._premier_non_fini({"a": [1, 2.5, {"b": (0, "inf")}]}, "x") is None
    assert ps._premier_non_fini({"a": ({"b": [0, float("inf")]},)}, "x") == "x.a[0].b[1]"
    assert ps._premier_non_fini({"a": {float("nan"): 1}}, "x") == "x.a[clé nan]"
    assert ps._premier_non_fini({(1.0, float("-inf")): 1}, "x") == "x[clé (1.0, -inf)][1]"
    assert ps._premier_non_fini(float("nan"), "x") == "x"
    cyclique = {"a": []}
    cyclique["a"].append(cyclique)
    with pytest.raises(ValueError, match="cyclique"):
        ps._premier_non_fini(cyclique, "x")


@pytest.mark.parametrize("champ,valeur", [("aveugle", [1]), ("repo_root", "Path")])
def test_pilotage_le_FILET_D_ENVELOPPE_nomme_l_enveloppe_jamais_un_500(monkeypatch, champ, valeur) -> None:
    """G4 : le filet final `_servable(_ENVELOPPE, out)` était PORTEUR sans aucun témoin — la re-revue l'a
    montré : un `compute_pilotage` qui rend `aveugle=[1]` ou `repo_root=Path(...)` donne 200 dégradé grâce à
    lui, 500 sans lui, et le mutant qui le retire laissait les 21 tests pilotage verts. La ligne NOMME
    l'enveloppe et RÉSUME le refus (une ligne, jamais l'erreur pydantic vidée sur plusieurs lignes)."""
    from backend.app.services import pilotage_service as ps
    import pathlib

    vrai = ps.pilotage.compute_pilotage

    def _enveloppe_malformee(*a, **k):
        out = vrai(*a, **k)
        out[champ] = pathlib.Path(out["repo_root"]) if valeur == "Path" else valeur
        return out

    monkeypatch.setattr(ps.pilotage, "compute_pilotage", _enveloppe_malformee)
    ps._vider_cache()
    r = client_500.get("/api/pm/pilotage")
    assert r.status_code == 200, f"une enveloppe malformée a donné {r.status_code}"
    d = r.json()
    assert len(d["aveugle"]) == 1 and d["aveugle"][0].startswith("pilotage:"), d["aveugle"]
    assert "enveloppe" in d["aveugle"][0] and champ in d["aveugle"][0], d["aveugle"]
    assert "\n" not in d["aveugle"][0], "le refus est RÉSUMÉ, jamais l'erreur pydantic vidée en entier"
    assert d["flotte"] is None and d["roadmap"] is None and d["portes"] is None and d["charge"] is None


@pytest.mark.parametrize("cache", ["froid", "chaud"])
@pytest.mark.parametrize("dernier,ligne", [
    (None, "SANS mesure de charge"),                                                         # accepté, dit
    ({"generated_at": 1.0, "sessions": [], "charge_connue": {"sims_en_vol": 2}}, "refusé"),  # refusé, dit
])
def test_pilotage_une_ligne_de_FRAIS_n_entre_JAMAIS_dans_le_cache(monkeypatch, cache, dernier, ligne) -> None:
    """G5 : la non-pollution du cache n'était verrouillée par rien — le mutant qui met en cache la ligne de
    refus et la ligne « SANS mesure de charge » laissait les 21 tests verts. Or ces lignes décrivent UNE
    requête `frais=1` : servies ensuite à chaque poll normal pendant 30 s, elles affirmeraient un refus ou
    un recalcul qui n'a pas eu lieu. Cache froid ET cache chaud ; la présence de la ligne sur la requête
    `frais=1` elle-même est le contrôle du dispositif."""
    from backend.app.services import pilotage_service as ps

    appels = {"n": 0}
    monkeypatch.setattr(ps, "snapshot", _faux_snapshot_rapide(appels))
    monkeypatch.setattr(ps.pilotage, "read_board", lambda racine: copy.deepcopy(dernier))
    ps._vider_cache()
    if cache == "chaud":
        avant = client.get("/api/pm/pilotage").json()
        assert not any("frais=1" in a for a in avant["aveugle"]), avant["aveugle"]
    d1 = client.get("/api/pm/pilotage?frais=1").json()
    assert any(a.startswith("frais=1") and ligne in a for a in d1["aveugle"]), ("contrôle", d1["aveugle"])
    d2 = client.get("/api/pm/pilotage").json()
    assert not any("frais=1" in a for a in d2["aveugle"]), (
        f"une ligne de la requête frais=1 a été SERVIE au poll suivant (cache {cache}) : {d2['aveugle']}")


def test_pilotage_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import pilotage_service as ps
    appels = {"n": 0}
    vrai = ps.pilotage.compute_pilotage

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)

    monkeypatch.setattr(ps.pilotage, "compute_pilotage", _compte)
    ps._vider_cache()
    client.get("/api/pm/pilotage")
    client.get("/api/pm/pilotage")
    assert appels["n"] == 1, f"le cache 30 s n'a pas tenu : {appels['n']} calculs"


# --- 2026-09-26 : le smoke docker rougissait — le backend mourait à l'import de tools.pm -------------------
_SONDE_SANS_TOOLS_PM = '''
import json, sys
from importlib.abc import MetaPathFinder


class _BloqueToolsPm(MetaPathFinder):
    """Reproduit l'image backend sans le volume ./tools : tout import de tools.pm échoue."""
    def find_spec(self, nom, chemin=None, cible=None):
        if nom == "tools.pm" or nom.startswith("tools.pm."):
            raise ModuleNotFoundError("No module named " + repr(nom), name=nom)
        return None


sys.meta_path.insert(0, _BloqueToolsPm())
sys.path.insert(0, sys.argv[1])
from backend.app.main import app
from fastapi.testclient import TestClient

with TestClient(app, raise_server_exceptions=False) as c:
    h = c.get("/health")
    p = c.get("/api/pm/pilotage")
    s = c.get("/api/pm/science")
print("RESULTAT " + json.dumps({"health": h.status_code, "pilotage": p.status_code,
                                "corps": p.json() if p.status_code == 200 else None,
                                "science": s.status_code, "corps_science": s.json() if s.status_code == 200 else None}))
'''


def _sonder_sans_tools_pm(tmp_path) -> dict:
    """Lance `_SONDE_SANS_TOOLS_PM` dans un processus NEUF et rend son résultat (santé, pilotage, science)."""
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sonde = tmp_path / "sonde_sans_tools_pm.py"
    sonde.write_text(_SONDE_SANS_TOOLS_PM, encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH", None)
    r = subprocess.run([os.sys.executable, str(sonde), racine], cwd=racine, capture_output=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    lignes = [ligne for ligne in r.stdout.splitlines() if ligne.startswith("RESULTAT ")]
    assert r.returncode == 0 and lignes, f"le backend ne démarre pas sans tools.pm :\n{r.stderr[-3000:]}"
    return json.loads(lignes[-1][len("RESULTAT "):])


def test_le_backend_DEMARRE_sans_tools_pm_et_le_pilotage_NOMME_l_absence(tmp_path) -> None:
    """Régression du 2026-09-26 (run CI 36210667429) : `pilotage_service` importait `tools.pm` au niveau du
    module, or `tools/` n'est pas dans l'image backend. Le processus uvicorn mourait AU DÉMARRAGE, /health
    avec lui, et le smoke ne montrait que « Failed to connect ». L'import est désormais GARDÉ : le backend
    démarre, et l'absence n'est pas tue — la route rend le mode dégradé, dont la ligne `pilotage:` NOMME
    ImportError et tools.pm (c'est ce marqueur que le smoke de la CI fait rougir).

    Sous-processus obligatoire : l'import de `backend.app.main` est un état de processus, déjà fait ici par le
    module de test. Un chercheur de `sys.meta_path` y bloque `tools.pm`, sans toucher au disque."""
    res = _sonder_sans_tools_pm(tmp_path)
    assert res["health"] == 200, res
    assert res["pilotage"] == 200, res
    d = res["corps"]
    assert d["schema"] == "pilotage_v1"
    assert all(d[b] is None for b in ("flotte", "roadmap", "portes", "charge")), d
    degrade = [a for a in d["aveugle"] if a.startswith("pilotage:")]
    assert len(degrade) == 1, d["aveugle"]
    assert "ImportError" in degrade[0] and "tools.pm" in degrade[0], degrade


def test_le_SCHEMA_recopie_par_le_service_suit_celui_de_tools_pm() -> None:
    """Le mode dégradé doit rendre le schéma SANS tools.pm, donc le service le recopie : cette recopie ne
    peut pas dériver en silence de `tools.pm.pilotage.SCHEMA`."""
    from backend.app.services import pilotage_service as ps
    from tools.pm import pilotage as P
    assert ps._SCHEMA == P.SCHEMA


def test_index_repond_200_schema_index_v1_et_familles_servies() -> None:
    from backend.app.services import index_service as ix
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "index_v1" and isinstance(d["generated_at"], (int, float))
    assert d["familles"] is not None and d["artefacts"] is not None, d["aveugle"]
    assert not any(a.startswith("index:") for a in d["aveugle"]), d["aveugle"]
    rec = next(f for f in d["familles"] if f["nom"] == "record")
    assert rec["indexes"] > 300


@pytest.fixture(autouse=True)
def _cache_de_l_index_vide_apres_chaque_test():
    """Revue du pas 2 (M3) : le cache de l'index est un état de PROCESSUS ; un test qui y laissait un mode dégradé
    le servait au test suivant pendant 60 s."""
    yield
    from backend.app.services import index_service
    index_service._vider_cache()
    science_service = sys.modules.get("backend.app.services.science_service")    # P2.84 : même état de processus
    if science_service is not None:
        science_service._vider_cache()


def test_index_ne_DATE_jamais_par_git_seule_la_racine_commune(monkeypatch) -> None:
    """D1 : git DATE dans l'écrivain de DATES_GIT.json, jamais sur le chemin de la requête. Revue du pas 2 (I4) : le
    témoin d'avant ne patchait que `_git` et `calculer_dates_git`, alors que la requête lance bien UNE commande git —
    `rev-parse --git-common-dir`, pour trouver le data/ du dépôt COMMUN (P2.114) — et un `git log` ajouté au service
    SURVIVAIT. Espion sur `subprocess.Popen` : seule cette commande est admise (le filet avalerait une AssertionError :
    on compte, on n'assert pas dedans)."""
    from backend.app.services import index_service as ix
    vrai, git = subprocess.Popen, []

    class _Espion(vrai):
        def __init__(self, args, *a, **k):
            if isinstance(args, (list, tuple)) and args and os.path.basename(str(args[0])).startswith("git"):
                git.append(list(args))
            super().__init__(args, *a, **k)
    monkeypatch.setattr(subprocess, "Popen", _Espion)
    ix._vider_cache()
    assert client.get("/api/pm/index").status_code == 200
    assert all(c == ["git", "rev-parse", "--git-common-dir"] for c in git), git


def test_index_surrogate_dans_UN_artefact_echappe_jamais_le_bloc_entier(monkeypatch) -> None:
    """Revue du pas 2 (I2) : un titre porteur d'un surrogate isolé (PyYAML le lit tel quel) faisait refuser les 780
    artefacts d'un bloc ; il est servi ÉCHAPPÉ, visible (G2), et la ligne le compte."""
    from backend.app.services import index_service as ix
    vrai = ix.index_artefacts.indexer

    def _surrogate(*a, **k):
        out = vrai(*a, **k)
        out["artefacts"][0]["titre"] = "\ud800x"
        return out
    monkeypatch.setattr(ix.index_artefacts, "indexer", _surrogate)
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["artefacts"] is not None and d["artefacts"][0]["titre"] == "\\ud800x"
    assert any(a.startswith("artefacts : 1 chaîne") for a in d["aveugle"]), d["aveugle"]


def test_index_DATES_GIT_hostile_n_aveugle_pas_l_index(monkeypatch) -> None:
    """Revue du pas 2 (I3) : `read_dates` était appelé dans le filet GLOBAL — un DATES_GIT.json hostile mettait les
    quatre blocs à null. Refus LOCAL : dates null avec sa ligne, familles et artefacts servis."""
    from backend.app.services import index_service as ix

    def _profond(*a, **k):
        raise RecursionError("maximum recursion depth exceeded while decoding a JSON array")
    monkeypatch.setattr(ix.index_artefacts, "read_dates", _profond)
    ix._vider_cache()
    d = client.get("/api/pm/index").json()
    assert d["familles"] is not None and d["artefacts"] is not None and d["dates"] is None
    assert not any(a.startswith("index:") for a in d["aveugle"]), d["aveugle"]
    assert any(a.startswith("dates : ") and "RecursionError" in a for a in d["aveugle"]), d["aveugle"]


def test_index_enveloppe_refusee_est_NOMMEE(monkeypatch) -> None:
    """Revue du pas 2 (M4) : le filet d'enveloppe n'avait AUCUN témoin (ses deux mutants survivaient)."""
    from backend.app.services import index_service as ix
    vrai = ix.index_artefacts.indexer

    def _ligne_non_chaine(*a, **k):
        out = vrai(*a, **k)
        out["aveugle"] = out["aveugle"] + [None]
        return out
    monkeypatch.setattr(ix.index_artefacts, "indexer", _ligne_non_chaine)
    ix._vider_cache()
    d = client.get("/api/pm/index").json()
    assert d["aveugle"][0].startswith("index: enveloppe refusée"), d["aveugle"]
    assert d["familles"] is None and d["artefacts"] is None


def test_blocs_servables_sans_adaptateur_LEVE_jamais_deguise_en_refus() -> None:
    """Revue du pas 2 (M5) : un bloc sans adaptateur (erreur de programmation) sortait « bloc refusé par le modèle de
    la route (KeyError) » ; il lève, et le filet global le NOMME pour ce qu'il est."""
    from backend.app.services import index_service as ix
    with pytest.raises(KeyError):
        ix._blocs_servables({"aveugle": [], "pipeline": {"x": 1}}, ("pipeline",))


def test_index_indexer_qui_leve_devient_une_ligne_index_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import index_service as ix

    def _boum(*a, **k):
        raise RuntimeError("indexeur cassé")
    monkeypatch.setattr(ix.index_artefacts, "indexer", _boum)
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["aveugle"][0].startswith("index: RuntimeError") and d["familles"] is None and d["artefacts"] is None


def test_index_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    vrai, appels = ix.index_artefacts.indexer, {"n": 0}

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(ix.index_artefacts, "indexer", _compte)
    ix._vider_cache()
    client.get("/api/pm/index")
    client.get("/api/pm/index")
    assert appels["n"] == 1


def test_index_bloc_de_type_etranger_devient_null_sans_500(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    vrai = ix.index_artefacts.indexer

    def _etranger(*a, **k):
        out = vrai(*a, **k)
        out["hors_familles"] = {"n": "beaucoup", "repertoires": {}}
        return out
    monkeypatch.setattr(ix.index_artefacts, "indexer", _etranger)
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["hors_familles"] is None and d["familles"] is not None
    assert any(a.startswith("hors_familles : bloc refusé") for a in d["aveugle"]), d["aveugle"]


def test_index_import_refuse_est_NOMME(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    monkeypatch.setattr(ix, "_IMPORT_REFUSE", ImportError("No module named 'yaml'"))
    ix._vider_cache()
    d = client.get("/api/pm/index").json()
    assert d["aveugle"][0].startswith("index: ImportError") and "yaml" in d["aveugle"][0]


# --- P2.84, lot 2 « Science » : GET /api/pm/science (plan 2, Task 2, amendement A1) ---------------------------------

def test_science_repond_200_schema_science_v1_blocs_servis() -> None:
    """Revue de la tâche 2 (I5, classe E25) : les comptes ne sont plus GELÉS (3 établies, 2 réfutées, plus de 100
    verdicts) — ajouter une arête, un progrès, faisait rougir un test BACKEND. Ils sont RECALCULÉS depuis leurs
    sources : les deux JSON de la taxonomie, et l'index servi par la route voisine (même processus, même cache)."""
    from backend.app.services import index_service as ix, science_service as sc
    from src import paths
    from tools.pm.pilotage import racine_depot
    ix._vider_cache()
    sc._vider_cache()
    r = client.get("/api/pm/science")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "science_v1" and not any(a.startswith("science:") for a in d["aveugle"]), d["aveugle"]
    assert d["pipeline"]["couverture"]["total"] > 0
    rep = os.path.join(racine_depot(), paths.data_file("agi_taxonomy"))
    attendu = {n: len(json.load(open(os.path.join(rep, f"{f}.json"), encoding="utf-8")))
               for n, f in (("etablie", "demands"), ("refutee", "refuted"))}
    natures = [a["nature"] for a in d["taxonomie"]["aretes"]]
    assert attendu["etablie"] > 0 and {n: natures.count(n) for n in attendu} == attendu
    assert all(a["preuves"]["specificity_control"] == "pass" for a in d["taxonomie"]["aretes"]
               if a["nature"] == "etablie")                                   # A1 (I5)
    index = client.get("/api/pm/index").json()
    lus = [a for a in index["artefacts"] if a["famille"] == "record" and a["etat_source"] == "verdict"]
    assert lus and len(d["trouvailles"]["verdicts"]) == len(lus)
    assert all(set(e) == {"date", "semaines", "sans_date", "semaine_partielle", "raison"}
               for e in d["trouvailles"]["par_semaine"].values())              # A1 (I2) : jamais null


def test_science_route_sert_EXACTEMENT_la_sortie_du_module(monkeypatch) -> None:
    """Revue de la tâche 2 (I1) : pydantic RETIRE en silence une clé que le modèle ne déclare pas. Un champ servi par
    `compute_science` et absent du modèle — `depassee_par`, `compte_graphe`… — disparaissait de la route sans un rouge,
    et `make api-types` régénérait un contrat cohérent avec la perte. Chaque bloc servi est ÉGAL à la sortie du module
    (contrôle positif : chaque bloc non null)."""
    from backend.app.services import index_service as ix, science_service as sc
    vrai, sortie = sc.science.compute_science, {}

    def _capture(*a, **k):
        out = vrai(*a, **k)
        sortie["out"] = json.loads(json.dumps(out))
        return out
    monkeypatch.setattr(sc.science, "compute_science", _capture)
    ix._vider_cache()
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    for bloc in ("pipeline", "taxonomie", "trouvailles"):
        assert d[bloc] is not None, (bloc, d["aveugle"])
        assert d[bloc] == sortie["out"][bloc], bloc
    assert d["aveugle"] == sortie["out"]["aveugle"]


def test_science_lit_l_index_dans_le_MEME_cache(monkeypatch) -> None:
    """M6 : /science n'appelle pas indexer quand le cache de l'index est chaud. Revue de la tâche 2 (mineur 1) :
    contrôle POSITIF — l'index reçu par `compute_science` est l'objet même du cache, et les trouvailles sont servies
    (un science en mode dégradé avant toute lecture rendait ce compte à 0 trivialement)."""
    from backend.app.services import index_service as ix, science_service as sc
    ix._vider_cache()
    ix.get_index()
    appels, recu = {"n": 0}, {}
    vrai_ix, vrai_sc = ix.index_artefacts.indexer, sc.science.compute_science

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai_ix(*a, **k)

    def _recoit(index, *a, **k):
        recu["index"] = index
        return vrai_sc(index, *a, **k)
    monkeypatch.setattr(ix.index_artefacts, "indexer", _compte)
    monkeypatch.setattr(sc.science, "compute_science", _recoit)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert appels["n"] == 0
    assert recu["index"] is ix._cache["valeur"] and d["trouvailles"] is not None, d["aveugle"]


def test_science_compute_qui_leve_devient_une_ligne_science_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import science_service as sc

    def _boum(*a, **k):
        raise RuntimeError("science cassée")
    monkeypatch.setattr(sc.science, "compute_science", _boum)
    sc._vider_cache()
    r = client.get("/api/pm/science")
    assert r.status_code == 200
    d = r.json()
    assert d["aveugle"][0].startswith("science: RuntimeError")
    assert (d["pipeline"], d["taxonomie"], d["trouvailles"]) == (None, None, None)


def test_science_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import science_service as sc
    vrai, appels = sc.science.compute_science, {"n": 0}

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(sc.science, "compute_science", _compte)
    sc._vider_cache()
    client.get("/api/pm/science")
    client.get("/api/pm/science")
    assert appels["n"] == 1


def test_science_cache_EXPIRE_au_dela_du_TTL(monkeypatch) -> None:
    """Revue de la tâche 2 (mineur 8) : le témoin du TTL était à sens unique — un cache qui n'expire jamais passait."""
    from backend.app.services import science_service as sc
    vrai, appels = sc.science.compute_science, {"n": 0}

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(sc.science, "compute_science", _compte)
    sc._vider_cache()
    sc.get_science(ttl_s=0)
    sc.get_science(ttl_s=0)
    assert appels["n"] == 2


def test_science_bloc_de_type_etranger_devient_null_sans_500(monkeypatch) -> None:
    from backend.app.services import science_service as sc
    vrai = sc.science.compute_science

    def _etranger(*a, **k):
        out = vrai(*a, **k)
        out["taxonomie"] = {"capacites": "beaucoup", "aretes": []}
        return out
    monkeypatch.setattr(sc.science, "compute_science", _etranger)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["taxonomie"] is None and d["pipeline"] is not None
    assert any(a.startswith("taxonomie : bloc refusé") for a in d["aveugle"]), d["aveugle"]


def test_science_raison_HORS_VOCABULAIRE_refuse_le_bloc_trouvailles_seul(monkeypatch) -> None:
    """A1 (I2) : la cause d'un `semaines` null est un vocabulaire FERMÉ côté route aussi (Literal) — une cause
    inventée ne passe pas pour une cause publiée ; le bloc est refusé avec sa ligne, les deux autres restent servis."""
    from backend.app.services import science_service as sc
    vrai = sc.science.compute_science

    def _cause_inventee(*a, **k):
        out = vrai(*a, **k)
        next(iter(out["trouvailles"]["par_semaine"].values()))["raison"] = "git_en_panne"
        return out
    monkeypatch.setattr(sc.science, "compute_science", _cause_inventee)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["trouvailles"] is None and d["taxonomie"] is not None and d["pipeline"] is not None
    assert any(a.startswith("trouvailles : bloc refusé") for a in d["aveugle"]), d["aveugle"]


def test_science_import_refuse_est_NOMME(monkeypatch) -> None:
    """Revue de la tâche 2 (I2) : « tools.pm.science » est DÉJÀ dans le texte fixe du service — le témoin ne pouvait
    pas voir la perte de la CAUSE. La cause injectée (« yaml ») n'apparaît nulle part ailleurs."""
    from backend.app.services import science_service as sc
    monkeypatch.setattr(sc, "_IMPORT_REFUSE", ImportError("No module named 'yaml'"))
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["aveugle"][0].startswith("science: ImportError") and "yaml" in d["aveugle"][0], d["aveugle"]


def test_le_backend_DEMARRE_sans_tools_pm_et_science_NOMME_l_absence(tmp_path) -> None:
    """Revue de la tâche 2 (I2) : le blocage RÉEL, pas un monkeypatch — l'image sans le volume ./tools. La route
    science répond 200 en mode dégradé, et sa ligne `science:` nomme ImportError ET la cause d'origine."""
    res = _sonder_sans_tools_pm(tmp_path)
    assert res["science"] == 200, res
    d = res["corps_science"]
    assert d["schema"] == "science_v1" and (d["pipeline"], d["taxonomie"], d["trouvailles"]) == (None, None, None)
    degrade = [a for a in d["aveugle"] if a.startswith("science:")]
    assert len(degrade) == 1 and "ImportError" in degrade[0] and "ModuleNotFoundError" in degrade[0], degrade


def test_science_pipeline_sans_racine_null_et_ligne(monkeypatch, tmp_path) -> None:
    """B2 par la route : le module sans ses répertoires lève (P2.135), la pipeline est null, jamais (0, 0, 0, 0)."""
    from backend.app.services import science_service as sc
    from tools import check_preregistration_applied as cpa
    monkeypatch.setattr(cpa, "_PREREG", str(tmp_path / "absent"))
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["pipeline"] is None and any(a.startswith("pipeline : ") for a in d["aveugle"]), d["aveugle"]


def test_science_index_DEGRADE_trouvailles_null_jamais_science_degrade(monkeypatch) -> None:
    """Review Focus 1 du plan 2, par la route : l'index en mode dégradé (`index: …`) ne met pas science en mode
    dégradé — trouvailles null avec SA ligne, pré-inscriptions null, taxonomie servie ; jamais une liste vide."""
    from backend.app.services import index_service as ix, science_service as sc

    def _boum(*a, **k):
        raise RuntimeError("indexeur cassé")
    monkeypatch.setattr(ix.index_artefacts, "indexer", _boum)
    ix._vider_cache()
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert not any(a.startswith("science:") for a in d["aveugle"]), d["aveugle"]
    assert d["trouvailles"] is None and d["taxonomie"] is not None and d["pipeline"]["preinscriptions"] is None
    assert any(a.startswith("pipeline : famille preinscription") for a in d["aveugle"]), d["aveugle"]
    # revue de la tâche 2 (mineur 5) : la CAUSE du mode dégradé de l'index est relayée, la vue Science la montre
    assert any(a.startswith("trouvailles : (index) index: RuntimeError") and "indexeur cassé" in a
               for a in d["aveugle"]), d["aveugle"]


def test_science_age_NEGATIF_de_l_instantane_DIT_dans_science(monkeypatch) -> None:
    """Revue de la tâche 2 (mineur 4, regradé : spec §9 « âge négatif ET une ligne ») : `trouvailles.dates` recopie
    l'âge de l'index, mais la ligne « FUTUR » restait dans /api/pm/index, que la vue Science n'affiche pas."""
    from backend.app.services import index_service as ix, science_service as sc
    futur = {"schema": "dates_git_v1", "generated_at": time.time() + 3600, "head": "abc", "historique": "tronque",
             "dates": None, "suivis": None, "raison": "clone superficiel"}
    monkeypatch.setattr(ix.index_artefacts, "read_dates", lambda racine: {"doc": futur, "chemin": "x", "raison": None})
    ix._vider_cache()
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["trouvailles"]["dates"]["age_s"] < 0, d["trouvailles"]["dates"]
    assert any(a.startswith("trouvailles : (index) dates : instantané daté dans le FUTUR") for a in d["aveugle"]), \
        d["aveugle"]


def test_science_ne_DATE_jamais_par_git(monkeypatch) -> None:
    """Leçon du pas 2 du plan 1 (I4), appliquée d'emblée : la requête /science ne lance que la commande git de l'index
    (`rev-parse --git-common-dir`, racine commune) — jamais une commande qui DATE (espion sur `subprocess.Popen`)."""
    from backend.app.services import index_service as ix, science_service as sc
    vrai, git = subprocess.Popen, []

    class _Espion(vrai):
        def __init__(self, args, *a, **k):
            if isinstance(args, (list, tuple)) and args and os.path.basename(str(args[0])).startswith("git"):
                git.append(list(args))
            super().__init__(args, *a, **k)
    monkeypatch.setattr(subprocess, "Popen", _Espion)
    ix._vider_cache()
    sc._vider_cache()
    r = client.get("/api/pm/science")
    assert r.status_code == 200 and r.json()["trouvailles"] is not None
    # revue de la tâche 2 (mineur 2) : `all([])` est vrai — l'espion doit avoir VU la commande de l'index
    assert git and all(c == ["git", "rev-parse", "--git-common-dir"] for c in git), git


def test_science_surrogate_dans_UNE_arete_echappe_jamais_le_bloc_entier(monkeypatch) -> None:
    """Leçon du pas 2 du plan 1 (I2), appliquée d'emblée : `_blocs_servables` est partagé — une chaîne non encodable
    est servie ÉCHAPPÉE et comptée, le bloc reste servi."""
    from backend.app.services import science_service as sc
    vrai = sc.science.compute_science

    def _surrogate(*a, **k):
        out = vrai(*a, **k)
        out["taxonomie"]["aretes"][0]["raison"] = "\ud800x"
        return out
    monkeypatch.setattr(sc.science, "compute_science", _surrogate)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["taxonomie"] is not None and d["taxonomie"]["aretes"][0]["raison"] == "\\ud800x"
    assert any(a.startswith("taxonomie : 1 chaîne") for a in d["aveugle"]), d["aveugle"]


def test_science_enveloppe_refusee_est_NOMMEE(monkeypatch) -> None:
    """Leçon du pas 2 du plan 1 (M4), appliquée d'emblée : le filet d'enveloppe a son témoin."""
    from backend.app.services import science_service as sc
    vrai = sc.science.compute_science

    def _ligne_non_chaine(*a, **k):
        out = vrai(*a, **k)
        out["aveugle"] = out["aveugle"] + [None]
        return out
    monkeypatch.setattr(sc.science, "compute_science", _ligne_non_chaine)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["aveugle"][0].startswith("science: enveloppe refusée"), d["aveugle"]
    assert (d["pipeline"], d["taxonomie"], d["trouvailles"]) == (None, None, None)


def test_science_SCHEMA_du_service_egal_a_celui_du_module() -> None:
    """Même garde que pour le pilotage : la constante du service ne dérive pas en silence de `science.SCHEMA`."""
    from backend.app.services import science_service as sc
    from tools.pm import science as S
    assert sc._SCHEMA == S.SCHEMA


def test_science_VOCABULAIRES_de_la_route_identiques_au_module() -> None:
    """A1 : la route FERME deux vocabulaires que le module définit (causes d'un `semaines` null, champs de `preuves`).
    Une cause ajoutée au module sans la route ferait refuser TOUT le bloc trouvailles ; un champ de preuve ajouté
    serait retiré en silence par le modèle. Parité exacte, dans les deux sens."""
    import typing
    from backend.app.schemas import SemainesFamille, TaxonomiePreuves
    from tools.pm import science as S
    raison = SemainesFamille.model_fields["raison"].annotation
    assert {v for arg in typing.get_args(raison) for v in typing.get_args(arg)} == set(S.RAISONS_SEMAINES)
    assert list(TaxonomiePreuves.model_fields) == list(S.PREUVES)
