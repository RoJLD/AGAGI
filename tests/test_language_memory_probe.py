import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_alias_keys_smoke():
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    # smoke minuscule : FORME + présence des clés du garde, pas les valeurs scientifiques
    r = run_language_memory_demand_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, D=1)
    assert set(r) >= {"lang_demand", "functional_aliasing", "alias_verdict", "leakage", "x_response"}
    assert r["functional_aliasing"] in ("pass", "fail")
    assert r["n"] == 2 and len(r["lang_intact"]) == 2 and len(r["control_intact"]) == 2
