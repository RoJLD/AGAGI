# tests/sandbox/test_s2_demand.py
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.baseline_models import RandomActionBatchModel
from tools.s2_demand import run_condition


def test_run_condition_returns_individual_survival():
    cfg = WorldConfig()
    out = run_condition(Biosphere3D, RandomActionBatchModel, genome=None,
                        seed=2026, num_agents=4, max_ticks=8, n_eras=2)
    assert "survival" in out and "life_score" in out
    assert len(out["survival"]) >= 4 * 2          # un âge PAR agent PAR ère (pas l'extinction-cohorte)
    assert all(s >= 0 for s in out["survival"])
    assert "censored_frac" in out


def test_run_condition_is_reproducible():
    cfg = WorldConfig()
    a = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    b = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    assert a["survival"] == b["survival"]
