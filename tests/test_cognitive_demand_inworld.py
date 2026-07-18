import os
import numpy as np
import pytest
from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, CognitiveOracleAblated


class _Ag:
    def __init__(self, O=120):
        self.genome = type("G", (), {"num_outputs": O})()
        self.surprise = 0.0; self.surprise_momentum = 0.0


def test_oracle_picks_signal_direction():
    agents = [_Ag(), _Ag()]
    m = CognitiveOracleBatchModel(agents)
    obs = np.zeros((2, 20), dtype=np.float32)
    obs[0, 12] = 1.0;  obs[0, 13] = 1.0     # dir = 3
    obs[1, 12] = -1.0; obs[1, 13] = 1.0     # dir = 1
    logits, _ = m.forward(obs)
    assert int(np.argmax(logits[0, :8])) == 3
    assert int(np.argmax(logits[1, :8])) == 1


def test_oracle_ablated_decorrelates():
    np.random.seed(0)
    agents = [_Ag() for _ in range(4)]
    obs = np.zeros((4, 20), dtype=np.float32)
    combos = [(-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)]   # dirs 0,1,2,3 (distincts)
    for i, (a, b) in enumerate(combos):
        obs[i, 12] = a; obs[i, 13] = b
    intact, _ = CognitiveOracleBatchModel(agents).forward(obs)
    ablated, _ = CognitiveOracleAblated(agents).forward(obs)
    intact_dirs = np.argmax(intact[:, :8], 1)
    ablated_dirs = np.argmax(ablated[:, :8], 1)
    # tous distincts intact (0,1,2,3) ; un dérangement (aucun point fixe) change CHAQUE direction
    assert sorted(intact_dirs.tolist()) == [0, 1, 2, 3]
    assert not np.any(intact_dirs == ablated_dirs)   # aucun agent ne garde sa direction


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="run in-world lourd")
def test_cog_demand_map_smoke():
    from tools.cognitive_demand_inworld import run_cog_demand_map
    m = run_cog_demand_map(seed=2026, K=2, num_agents=6, max_ticks=60, base_metabolism=4.0, cog_gain=6.0)
    assert set(m) == {"on", "off"}
    for mode in ("on", "off"):
        assert set(m[mode]) == {"ratio", "verdict", "n"}
        assert m[mode]["ratio"] > 0.0
