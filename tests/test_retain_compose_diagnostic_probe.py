import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4)
    assert set(r) >= {"same_tick_median", "oracle_median", "learned_median", "gap_verdict"}
    assert r["n"] == 2 and len(r["per_seed"]["oracle"]) == 2
    assert r["gap_verdict"] in ("RETENTION", "REPRESENTATION", "INCONCLUSIVE")
