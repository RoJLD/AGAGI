import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


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
