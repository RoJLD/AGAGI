import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _cfg, _measure_forage, _verdict_forage


def _agg(p_reach, p_cap, income_t, drain_t):
    return {"p_reach": p_reach, "p_cap": p_cap, "income_t": income_t, "drain_t": drain_t}


def test_verdict_forage_approche():
    assert _verdict_forage(_agg(0.3, 1.0, 5.0, 1.0)) == "GOULOT=APPROCHE"


def test_verdict_forage_capture():
    assert _verdict_forage(_agg(0.9, 0.3, 5.0, 1.0)) == "GOULOT=CAPTURE"


def test_verdict_forage_revenu():
    assert _verdict_forage(_agg(0.9, 0.9, 0.5, 1.0)) == "GOULOT=REVENU"


def test_verdict_forage_suffisant():
    assert _verdict_forage(_agg(0.9, 0.9, 2.0, 1.0)) == "FORAGE SUFFISANT"


def _mk_env(trace_forage):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_forage = trace_forage
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(4):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def test_config_default_trace_forage_off():
    assert WorldConfig().trace_forage is False


def test_trace_forage_off_is_inert():
    env = _mk_env(trace_forage=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool, "des agents doivent exister"
    for ag in pool:
        assert "_forage_min_dist" not in ag
        assert "_forage_contacts" not in ag
        assert "_forage_income" not in ag


def test_trace_forage_on_records_min_dist():
    env = _mk_env(trace_forage=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_forage_min_dist" in ag]
    assert traced, "des agents doivent porter _forage_min_dist (proies presentes)"
    for ag in traced:
        assert np.isfinite(ag["_forage_min_dist"])
        assert ag["_forage_min_dist"] >= 0


def test_cfg_trace_forage_param():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    assert cfg.trace_forage is True
    assert cfg.trace_energy_sinks is True
    assert cfg.base_metabolism == 0.0


def test_measure_forage_smoke():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    agg = _measure_forage(cfg, [105, 106], n_apex=0, max_ticks=20)
    assert agg["n_agents"] > 0
    assert 0.0 <= agg["p_reach"] <= 1.0
    assert 0.0 <= agg["p_cap"] <= 1.0
    assert agg["income_t"] >= 0.0
    assert agg["drain_t"] >= 0.0
    assert np.isfinite(agg["mean_min_dist"])
