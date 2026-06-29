"""Tests de l'A/B de learnabilité du substrat (ADR-003, barreau-0)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest

from tools.substrate_ab import compute_ab_verdict, run_substrate_ab, compare


def test_verdict_gradient_wins_when_torch_better():
    rows = [{"diff": 0.30}, {"diff": 0.25}, {"diff": 0.40}]
    v = compute_ab_verdict(rows)
    assert v["verdict"] == "GRADIENT_GAGNE"
    assert v["n_gradient_favorable"] == 3 and v["n"] == 3


def test_verdict_hebbien_wins_when_legacy_better():
    rows = [{"diff": -0.30}, {"diff": -0.25}, {"diff": -0.40}]
    assert compute_ab_verdict(rows)["verdict"] == "HEBBIEN_GAGNE"


def test_verdict_neutral_in_band():
    rows = [{"diff": 0.00}, {"diff": 0.01}, {"diff": -0.01}]
    assert compute_ab_verdict(rows)["verdict"] == "NEUTRE"


def test_verdict_empty():
    assert compute_ab_verdict([])["verdict"] == "NEUTRE"


def test_run_legacy_returns_hit_rates_in_range():
    out = run_substrate_ab("legacy", seed=0, ticks=12, n_agents=4)
    assert 0.0 <= out["hit_start"] <= 1.0
    assert 0.0 <= out["hit_end"] <= 1.0
    assert out["backend"] == "legacy"


def test_run_torch_returns_hit_rates_in_range():
    pytest.importorskip("torch")
    out = run_substrate_ab("torch", seed=0, ticks=12, n_agents=4)
    assert 0.0 <= out["hit_end"] <= 1.0
    assert out["backend"] == "torch"


def test_compare_structure():
    pytest.importorskip("torch")
    res = compare(seeds=(0,), ticks=10, n_agents=4)
    assert res["verdict"] in ("GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE")
    assert len(res["per_seed"]) == 1
    assert set(["legacy_delta", "torch_delta", "diff"]).issubset(res["per_seed"][0])
