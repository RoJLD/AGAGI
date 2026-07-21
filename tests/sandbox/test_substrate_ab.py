"""Tests de l'A/B de learnabilité du substrat (ADR-003, barreau-0)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest

from tools.substrate_ab import compute_ab_verdict, run_substrate_ab, compare


def test_verdict_gradient_wins_when_torch_better():
    # n=6 : depuis P2.5 le verdict exige la bande ET `sign_p<0.1`. A n=3, sign_p vaut 0.25 meme en
    # separation parfaite -> aucun verdict possible. Ce test verifiait le CABLAGE a une taille qui ne
    # peut rien porter ; les 7 tests de cablage du depot faisaient tous la meme chose.
    rows = [{"diff": d} for d in (0.30, 0.25, 0.40, 0.32, 0.28, 0.35)]
    v = compute_ab_verdict(rows)
    assert v["verdict"] == "GRADIENT_GAGNE"
    assert v["n_gradient_favorable"] == 6 and v["n"] == 6


def test_verdict_hebbien_wins_when_legacy_better():
    rows = [{"diff": d} for d in (-0.30, -0.25, -0.40, -0.32, -0.28, -0.35)]
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
