import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, rank=8)
    assert set(r) >= {"plain_median", "bilinear_median", "unlocked", "per_seed"}
    assert r["n"] == 2 and len(r["per_seed"]["plain"]) == 2 and len(r["per_seed"]["bilinear"]) == 2
    assert isinstance(r["unlocked"], bool)
