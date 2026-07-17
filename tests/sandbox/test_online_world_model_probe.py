"""Tests du modèle du monde appris EN LIGNE (PLAN-002, G4). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.online_world_model_probe import run_online, _OnlineBilinear
from tools.anticipation_planning_probe import run_planning
import numpy as np


def test_run_online_curve_keys():
    curve = run_online(d=6, K=3, horizon=3, steps=500, eps=0.4, seed=0, checkpoints=(100, 500), n_test=80)
    assert set(curve) == {100, 500}
    for v in curve.values():
        assert 0.0 <= v <= 1.0


def test_bilinear_sample_efficient_beats_linear():
    # même à FAIBLE budget (N=100), le bilinéaire (action-conditionné) bat le linéaire au planning.
    r = run_planning(d=8, K=4, n_fit=100, n_test=200, horizon=4, seed=1)
    assert r["models"]["bilinear"]["success"] > r["models"]["linear"]["success"] + 0.1


def test_episodic_resets_help_coverage():
    # la couverture d'états (resets = respawns) referme l'écart vs l'attracteur seul.
    no_reset = run_online(d=8, K=4, horizon=4, steps=2000, eps=0.4, seed=2, reset_period=0,
                          checkpoints=(2000,), n_test=200)[2000]
    reset = run_online(d=8, K=4, horizon=4, steps=2000, eps=0.4, seed=2, reset_period=20,
                       checkpoints=(2000,), n_test=200)[2000]
    assert reset >= no_reset - 0.02          # les resets aident (ou au pire neutres au bruit près)


def test_online_bilinear_accumulates():
    # sanity : le modèle incrémental accumule des stats et produit K matrices après refit.
    g = _OnlineBilinear(d=6, K=3)
    rng = np.random.RandomState(0)
    for _ in range(200):
        s, a, sp = rng.randn(6), rng.randint(3), rng.randn(6)
        g.update(s, a, sp)
    g.refit()
    assert len(g.M) == 3 and g.M[0].shape == (6, 6)
