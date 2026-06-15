# tests/sandbox/test_benchmark_mode.py
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaBatchModel


def test_default_batch_model_cls_is_mamba():
    env = Biosphere3D(WorldConfig())
    assert env.batch_model_cls is MambaBatchModel
