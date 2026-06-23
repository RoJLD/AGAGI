import json
from src.seed_ai.live_progress import emit_progress, ENV_VAR


def test_noop_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    emit_progress({"run": "x", "generation": 1, "fitness": 0.5})
    assert not list(tmp_path.iterdir())  # rien créé, pas d'exception


def test_writes_jsonl_when_env_set(tmp_path, monkeypatch):
    sink = tmp_path / "live.jsonl"
    monkeypatch.setenv(ENV_VAR, str(sink))
    emit_progress({"run": "x", "generation": 1, "fitness": 0.5})
    emit_progress({"run": "x", "generation": 2, "fitness": 0.7})
    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["fitness"] == 0.7
