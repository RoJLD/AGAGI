"""Tests du World Model — tête prédictive RND (EDR 010 / roadmap Vague 0)."""
import numpy as np
import pytest

from src.agents.world_model import WorldModel


def test_projection_is_deterministic():
    a = WorldModel(10, seed=7)
    b = WorldModel(10, seed=7)
    assert np.allclose(a.P, b.P)
    # ... et le seed change la projection
    c = WorldModel(10, seed=8)
    assert not np.allclose(a.P, c.P)


def test_error_shape_and_nonnegative():
    wm = WorldModel(6)
    rng = np.random.default_rng(0)
    err = wm.observe(rng.random((4, 6)), rng.random((4, 6)), train=False)
    assert err.shape == (4,)
    assert (err >= 0).all()


def test_no_train_does_not_change_Wp():
    wm = WorldModel(6)
    before = wm.Wp.copy()
    rng = np.random.default_rng(1)
    wm.observe(rng.random((3, 6)), rng.random((3, 6)), train=False)
    assert np.array_equal(wm.Wp, before)


def test_initial_prediction_is_zero():
    # Wp init à zéro -> prédiction nulle, erreur = mean(target²) > 0.
    wm = WorldModel(8, seed=3)
    assert np.allclose(wm.predict(np.ones((1, 8))), 0.0)


def test_learns_a_fixed_transition():
    # Répéter une transition fixe -> l'erreur doit s'effondrer (le modèle apprend).
    wm = WorldModel(8, lr=0.05, seed=1)
    prev = np.ones((1, 8), dtype=np.float32)
    nxt = np.arange(8, dtype=np.float32).reshape(1, 8)
    e0 = float(wm.observe(prev, nxt, train=False)[0])
    for _ in range(500):
        wm.observe(prev, nxt, train=True)
    e1 = float(wm.observe(prev, nxt, train=False)[0])
    assert e1 < e0 * 0.1   # chute > 90 %


def test_learns_a_linear_world():
    # Monde linéaire next = prev @ Mᵀ : le modèle doit converger, l'erreur chuter.
    rng = np.random.default_rng(0)
    M = rng.standard_normal((8, 8)).astype(np.float32)
    wm = WorldModel(8, lr=0.02, seed=2)

    def batch(n=16):
        prev = rng.standard_normal((n, 8)).astype(np.float32)
        return prev, prev @ M.T

    p, n = batch()
    e0 = float(np.mean(wm.observe(p, n, train=False)))
    for _ in range(3000):
        p, n = batch()
        wm.observe(p, n, train=True)
    p, n = batch()
    e1 = float(np.mean(wm.observe(p, n, train=False)))
    assert e1 < e0 * 0.5   # le world model a appris la dynamique


def test_fit_width_pads_and_truncates_without_crash():
    wm = WorldModel(5)
    # plus large -> tronqué ; plus court -> padé ; ne doit pas lever
    err = wm.observe(np.ones((2, 8)), np.ones((2, 3)), train=True)
    assert err.shape == (2,)


def test_surprise_drops_on_familiar_rises_on_novel():
    # Après apprentissage d'une transition A, une transition B inédite surprend plus.
    wm = WorldModel(8, lr=0.05, seed=5)
    a_prev = np.ones((1, 8), dtype=np.float32)
    a_next = np.full((1, 8), 2.0, dtype=np.float32)
    for _ in range(300):
        wm.observe(a_prev, a_next, train=True)
    familiar = float(wm.observe(a_prev, a_next, train=False)[0])
    b_prev = np.full((1, 8), -1.0, dtype=np.float32)
    b_next = np.full((1, 8), 5.0, dtype=np.float32)
    novel = float(wm.observe(b_prev, b_next, train=False)[0])
    assert novel > familiar
