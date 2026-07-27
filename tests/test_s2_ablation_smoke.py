import os
import pytest


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1",
                    reason="run in-world lourd : activer avec RUN_SLOW=1")
def test_ablation_map_smoke():
    from tools.s2_demand_ablation import run_ablation_map
    m = run_ablation_map(worlds=["stoneage"], seed=2026, K=2, num_agents=6, max_ticks=60)
    assert "stoneage" in m
    r = m["stoneage"]
    assert set(r) == {"within_ratio", "between_ratio", "verdict", "n"}
    assert r["within_ratio"] > 0.0
    assert r["verdict"] in {"PERCEPTION_DEMANDED", "PERCEPTION_DECOY", "INCONCLUSIVE"}
    assert r["n"] == 2
