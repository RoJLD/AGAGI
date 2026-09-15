"""E28 (2026-09-15) — le World Model par agent ne laisse plus sortir un NON-FINI.

Mesuré : 669/669 morts d'une cohorte immortelle (legacy, lr 0,04, 200 ticks, seed 2026) avaient un `Wp` non fini,
dès le tick 51 — le SGD brut sur l'observation (énergie jusqu'à 100, lr 0,01) diverge ; le NaN devient `surprise`
NaN, `brain_cost` NaN, puis `energy = max(0.0, nan)` = 0.0 : une mort par tick. Garde : Wp remis à zéro, err = 1.0
(surprise maximale, bornée), événement COMPTÉ. Trois cas : no-op EXACT sur des valeurs finies ; NaN injecté ->
reset compté, err 1.0, Wp fini ; un agent sain dans le même batch n'est PAS touché. Aucun monde."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agents.world_model import WorldModel  # noqa: E402


def _wm(dim=6, out=4):
    wm = WorldModel(dim, out_dim=out, lr=0.01, seed=1)
    rng = np.random.RandomState(3)
    Wp = rng.uniform(-0.1, 0.1, (3, dim, out)).astype(np.float32)
    prev = rng.uniform(-1, 1, (3, dim)).astype(np.float32)
    nxt = rng.uniform(-1, 1, (3, dim)).astype(np.float32)
    return wm, Wp, prev, nxt


def test_finite_batch_is_a_bit_identical_noop_of_the_historical_update():
    wm, Wp, prev, nxt = _wm()
    pred = np.einsum('bi,bio->bo', prev, Wp); tgt = nxt @ wm.P; diff = pred - tgt
    err_attendu = np.mean(diff ** 2, axis=1)
    Wp_attendu = Wp - wm.lr * np.einsum('bi,bo->bio', prev, diff)
    n0 = WorldModel.nonfinite_resets
    err, Wp2 = wm.observe_batch(Wp.copy(), prev, nxt, train=True)
    assert np.array_equal(err, err_attendu) and np.array_equal(Wp2, Wp_attendu)
    assert WorldModel.nonfinite_resets == n0


def test_a_diverged_agent_is_reset_counted_and_bounded_while_its_neighbours_are_untouched():
    wm, Wp, prev, nxt = _wm()
    Wp[1] = np.inf                                          # l'agent 1 a divergé
    n0 = WorldModel.nonfinite_resets
    err, Wp2 = wm.observe_batch(Wp.copy(), prev, nxt, train=True)
    assert WorldModel.nonfinite_resets == n0 + 1
    assert np.isfinite(err).all() and np.isfinite(Wp2).all()
    assert err[1] == 1.0 and np.all(Wp2[1] == 0.0)
    # les voisins : exactement la mise à jour historique
    pred = np.einsum('bi,bio->bo', prev, Wp); tgt = nxt @ wm.P; diff = pred - tgt
    for b in (0, 2):
        assert np.array_equal(Wp2[b], Wp[b] - wm.lr * np.einsum('i,o->io', prev[b], diff[b]))
        assert err[b] == np.mean(diff[b] ** 2)


def test_the_guard_CAN_FAIL_a_nan_error_alone_is_also_caught():
    wm, Wp, prev, nxt = _wm()
    prev[2] = np.nan                                        # observation corrompue -> err NaN, Wp fini
    err, Wp2 = wm.observe_batch(Wp.copy(), prev, nxt, train=True)
    assert err[2] == 1.0 and np.isfinite(Wp2).all()
