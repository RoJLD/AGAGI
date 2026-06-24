import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _mk_env(trace):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_energy_sinks = trace
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(4):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def test_trace_off_is_inert():
    env = _mk_env(trace=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool, "des agents doivent exister"
    assert all("_e_phases" not in ag for ag in pool)   # trace OFF -> aucun _e_phases


def test_trace_on_records_four_phases():
    env = _mk_env(trace=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_e_phases" in ag]
    assert traced, "des agents doivent porter _e_phases"
    for ag in traced:
        ph = ag["_e_phases"]
        assert set(ph) == {"brain", "action", "biologie", "mouvement"}
        assert all(np.isfinite(v) for v in ph.values())


def test_config_default_trace_off():
    assert WorldConfig().trace_energy_sinks is False


def test_trace_off_is_inert_bio():
    env = _mk_env(trace=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool
    assert all("_e_bio" not in ag for ag in pool)            # trace OFF -> aucun _e_bio


def test_trace_on_records_bio_subphases_and_coheres():
    env = _mk_env(trace=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_e_bio" in ag]
    assert traced, "des agents doivent porter _e_bio"
    for ag in traced:
        bio = ag["_e_bio"]
        assert set(bio) == {"metab", "terrain", "carry", "autres"}
        # coherence : somme des sous-postes = phase biologie d'EDR 099 (telescopage s0-s5)
        if "_e_phases" in ag:
            assert abs(sum(bio.values()) - ag["_e_phases"]["biologie"]) < 1e-6
