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


from tools.s2_demand import load_champion_genome, CONDITIONS


def test_conditions_cover_the_ladder():
    keys = set(CONDITIONS)
    assert {"champion", "random_action", "random_genome", "reflex_naive", "reflex_prudent"} <= keys


def test_load_champion_raises_on_empty_hof(monkeypatch):
    import tools.s2_demand as s2
    monkeypatch.setattr(s2, "load_hall_of_fame", lambda: (2, []))
    try:
        load_champion_genome()
        assert False, "doit lever si HoF vide"
    except RuntimeError:
        pass


from tools.s2_demand import required_k


def test_required_k_floor_is_12():
    # effet énorme, variance faible -> K calculé petit, mais plancher = 12 (réf EDR 087)
    assert required_k(mean_diff=100.0, std_diff=5.0) == 12


def test_required_k_grows_with_noise():
    k_low = required_k(mean_diff=10.0, std_diff=5.0)
    k_high = required_k(mean_diff=10.0, std_diff=40.0)
    assert k_high > k_low >= 12
