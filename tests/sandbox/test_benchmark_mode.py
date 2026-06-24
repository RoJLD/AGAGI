# tests/sandbox/test_benchmark_mode.py
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaBatchModel


def test_default_batch_model_cls_is_mamba():
    env = Biosphere3D(WorldConfig())
    assert env.batch_model_cls is MambaBatchModel


import numpy as np
from src.agents.mamba_agent import MambaAgent


def test_benchmark_mode_freezes_cohort_size():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000              # scaffolds OFF
    for _ in range(8):
        a = MambaAgent()
        env.add_agent(a, energy=99.0)     # quasi reproduction -> doit être bloquée
    n0 = len(env.agents)
    for _ in range(15):
        env.step()
    # cohorte fixe : la population ne CROÎT jamais (peut décroître par mort)
    assert len(env.agents) + len(getattr(env, "dead_agents", [])) <= n0


def test_default_mode_allows_reproduction_attr():
    env = Biosphere3D(WorldConfig())
    assert env.benchmark_mode is False
