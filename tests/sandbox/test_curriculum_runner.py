"""Tests du CurriculumRunner — axe ontogénétique (EDR 008)."""
import pytest

from src.curriculum.runner import (
    EraResult,
    WorldStage,
    GraduationConfig,
    CurriculumRunner,
    has_graduated,
    plateau_slope,
)


# --- Prédicats purs : plateau & graduation ---

def test_plateau_slope_flat_is_near_zero():
    assert abs(plateau_slope([0.8] * 5, 5)) < 1e-9


def test_plateau_slope_rising_is_positive():
    assert plateau_slope([0.1, 0.2, 0.3, 0.4, 0.5], 5) > 0.05


def test_not_graduated_when_history_too_short():
    cfg = GraduationConfig(window=5)
    assert not has_graduated([0.9, 0.9], cfg)


def test_not_graduated_when_still_rising():
    cfg = GraduationConfig(window=5, eps_plateau=0.01, c_floor=0.6, patience=2)
    # pente forte -> pas de plateau, même si haut
    assert not has_graduated([0.1, 0.3, 0.5, 0.7, 0.9], cfg)


def test_graduated_when_flat_and_high():
    cfg = GraduationConfig(window=5, eps_plateau=0.02, c_floor=0.6, patience=2)
    assert has_graduated([0.70, 0.71, 0.70, 0.72, 0.71], cfg)


def test_not_graduated_when_flat_but_low():
    cfg = GraduationConfig(window=5, eps_plateau=0.02, c_floor=0.6, patience=2)
    # plateau, mais sous le plancher C_floor -> on ne promeut pas la médiocrité
    assert not has_graduated([0.30, 0.31, 0.30, 0.29, 0.30], cfg)


# --- Orchestration : traversée des mondes ---

def _ramping_world_fn():
    """Fabrique un run_era_fn qui monte puis plafonne, par monde, avec un champion."""
    calls = {}
    ramp = [0.2, 0.4, 0.6, 0.75, 0.80, 0.80, 0.81, 0.80, 0.80, 0.80]

    def run_era_fn(world_type, import_id, keep_mem):
        n = calls.get(world_type, 0)
        calls[world_type] = n + 1
        comp = ramp[min(n, len(ramp) - 1)]
        return EraResult(
            competence=comp,
            champion_agent_id=f"{world_type[:4]}_champ",
            raw_stats={"import": import_id, "keep_mem": keep_mem},
        )

    return run_era_fn, calls


def test_runner_graduates_and_promotes_champion():
    stages = [WorldStage("soup"), WorldStage("stoneage")]
    cfg = GraduationConfig(window=5, eps_plateau=0.02, c_floor=0.6, patience=2, max_eras=30)
    run_era_fn, _ = _ramping_world_fn()

    transcript = CurriculumRunner(stages, run_era_fn, cfg).run()

    assert len(transcript) == 2
    # soup a bien diplômé sur plateau haut
    assert transcript[0]["graduated"] is True
    assert transcript[0]["champion_promoted"] == "soup_champ"
    assert transcript[0]["inherited_from"] is None
    # le relicat de soup est hérité par stoneage
    assert transcript[1]["inherited_from"] == "soup_champ"


def test_runner_threads_import_id_into_next_world():
    stages = [WorldStage("soup"), WorldStage("stoneage")]
    cfg = GraduationConfig(window=5, eps_plateau=0.02, c_floor=0.6, patience=2, max_eras=30)

    seen_imports = []

    def run_era_fn(world_type, import_id, keep_mem):
        seen_imports.append((world_type, import_id))
        # soup plafonne vite ; stoneage aussi
        return EraResult(competence=0.8, champion_agent_id=f"{world_type[:4]}_champ")

    CurriculumRunner(stages, run_era_fn, cfg, keep_memory=True).run()

    # Le 1er appel sur stoneage doit recevoir l'import du champion de soup
    stoneage_imports = [imp for (w, imp) in seen_imports if w == "stoneage"]
    assert stoneage_imports[0] == "soup_champ"


def test_runner_guard_time_forces_progression():
    # Compétence plate mais SOUS le plancher : ne diplôme jamais -> garde-temps.
    stages = [WorldStage("soup")]
    cfg = GraduationConfig(window=5, eps_plateau=0.02, c_floor=0.6, patience=2, max_eras=4)

    def run_era_fn(world_type, import_id, keep_mem):
        return EraResult(competence=0.4, champion_agent_id="c")

    transcript = CurriculumRunner(stages, run_era_fn, cfg).run()

    assert transcript[0]["graduated"] is False
    assert transcript[0]["eras"] == 4
    assert transcript[0]["champion_promoted"] == "c"


def test_runner_rejects_empty_curriculum():
    with pytest.raises(ValueError):
        CurriculumRunner([], lambda *a: EraResult(0.0))
