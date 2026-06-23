import json
from src.curriculum.runner import CurriculumRunner, WorldStage, GraduationConfig, EraResult
from src.seed_ai.live_progress import ENV_VAR


def test_curriculum_runner_emits_progress_per_era(tmp_path, monkeypatch):
    sink = tmp_path / "live.jsonl"
    monkeypatch.setenv(ENV_VAR, str(sink))

    def fake_era(world_type, carried, keep):
        return EraResult(competence=0.5)  # < c_floor (0.6) -> jamais diplômé

    runner = CurriculumRunner(
        stages=[WorldStage("soup")],
        run_era_fn=fake_era,
        grad_cfg=GraduationConfig(max_eras=3),
    )
    runner.run()

    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # 3 ères
    assert json.loads(lines[0]) == {
        "run": "soup", "generation": 1, "fitness": 0.5, "accuracy": None, "size": None,
    }
