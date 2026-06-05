import os
import json
import pytest
from src.environments.config import WorldConfig

def test_default_config():
    cfg = WorldConfig()
    assert cfg.size == 10
    assert cfg.agent.num_inputs == 38
    assert cfg.biome.desert_drain == 1.0

def test_load_from_json(tmpdir):
    data = {
        "size": 20,
        "agent": {
            "num_nodes": 128,
            "mutation": {
                "weight_mutate_rate": 0.5
            }
        },
        "biome": {
            "plains_drain": 0.2
        }
    }
    path = os.path.join(tmpdir, "test_cfg.json")
    with open(path, "w") as f:
        json.dump(data, f)
        
    cfg = WorldConfig.load_from_json(path)
    assert cfg.size == 20
    assert cfg.agent.num_nodes == 128
    assert cfg.agent.mutation.weight_mutate_rate == 0.5
    assert cfg.biome.plains_drain == 0.2
    assert cfg.biome.water_drain == 0.5 # Default fallback
