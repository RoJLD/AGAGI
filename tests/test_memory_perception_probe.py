import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_na_aliasing_smoke():
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    # smoke minuscule : FORME + functional_aliasing='n/a', pas les valeurs scientifiques
    r = run_memory_perception_demand_probe(seeds=[0, 1], episodes=30, n_agents=8, K=4, D=1)
    assert r["functional_aliasing"] == "n/a"
    assert r["n"] == 2 and len(r["delayed_intact"]) == 2 and len(r["present_intact"]) == 2
    assert set(r) >= {"delayed", "present", "specificity_control", "present_alive"}
