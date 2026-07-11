"""Tests du proxy de planning anticipatif (PLAN-001, G4). Pur numpy (pas de torch)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest

from tools.anticipation_planning_probe import run_planning, _fit_models, _true_dynamics, _predict


def test_run_planning_smoke_keys():
    r = run_planning(d=6, K=3, n_fit=800, n_test=100, horizon=3, seed=0)
    assert set(r["models"]) == {"bilinear", "linear", "none"}
    for m in ("bilinear", "linear", "none"):
        assert 0.0 <= r["models"][m]["norm_dist"]      # borne physique (distance normalisée >= 0)
        assert 0.0 <= r["models"][m]["success"] <= 1.0
    assert {"bilinear", "linear"} <= set(r["fidelity"])


def test_bilinear_more_faithful_than_linear():
    # la dynamique est action-conditionnée -> le bilinéaire (matrice par action) DOIT mieux prédire.
    r = run_planning(d=8, K=4, n_fit=3000, n_test=200, horizon=3, seed=1)
    assert r["fidelity"]["bilinear"] < r["fidelity"]["linear"]


def test_bilinear_planning_beats_random():
    # fidélité -> comportement : le planning bilinéaire se rapproche PLUS du but que le hasard.
    r = run_planning(d=8, K=4, n_fit=3000, n_test=300, horizon=4, seed=2)
    assert r["models"]["bilinear"]["norm_dist"] < r["models"]["none"]["norm_dist"]


def test_fit_recovers_action_conditioning():
    # sanity : le fit bilinéaire par action récupère ~la vraie matrice (pré-tanh) mieux que le linéaire.
    W = _true_dynamics(d=6, K=3, seed=3)
    models = _fit_models(W, d=6, K=3, n_fit=4000, seed=3)
    assert len(models["bilinear"]) == 3           # une matrice par action
    assert models["bilinear"][0].shape == (6, 6)
