import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_na_aliasing_smoke():
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    # smoke minuscule : on vérifie la FORME + que functional_aliasing='n/a', pas les valeurs scientifiques
    r = run_perception_coordination_demand_probe(seeds=[0, 1], episodes=30, n_agents=8, K=4, V=6)
    assert r["functional_aliasing"] == "n/a"
    assert r["n"] == 2 and len(r["coord_intact"]) == 2 and len(r["nocoord_intact"]) == 2
    assert set(r) >= {"coord", "nocoord", "specificity_control", "nocoord_alive"}
