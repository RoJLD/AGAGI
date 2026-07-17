"""Tests des fonctions pures de tools/nav_localization_probe (decodeur + verdict), sans le sim."""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.nav_localization_probe import linear_probe_accuracy, nav_verdict


def _separable(n=400, d=6, k=4, noise=0.2, seed=0):
    """Features lineairement separables : bloc-signal par classe + bruit."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, k, n)
    X = noise * rng.standard_normal((n, d))
    for i, c in enumerate(y):
        X[i, c % d] += 3.0            # signal fort sur une dim dependant de la classe
    return X, y


def test_probe_recovers_separable_signal():
    X, y = _separable()
    acc, chance = linear_probe_accuracy(X, y, seed=1)
    assert acc > 0.9                  # signal lineaire fort -> quasi parfait
    assert chance < 0.5               # 4 classes ~equilibrees


def test_probe_at_chance_on_noise():
    rng = np.random.default_rng(2)
    X = rng.standard_normal((300, 8))
    y = rng.integers(0, 4, 300)       # cible independante des features
    acc, chance = linear_probe_accuracy(X, y, seed=3)
    assert acc < chance + 0.15        # proche du hasard (pas de signal a decoder)


def test_probe_nan_when_too_few_samples():
    acc, chance = linear_probe_accuracy(np.zeros((5, 3)), np.array([0, 1, 0, 1, 0]))
    assert np.isnan(acc)


def test_verdict_invalid_when_obs_at_chance():
    # l'obs elle-meme ne decode pas la cible -> cible mal definie
    assert nav_verdict(acc_obs=0.28, acc_H=0.27, match_emit=0.1, chance=0.25) == "INVALID_TARGET"


def test_verdict_encoder_gap_when_H_loses_signal():
    # obs decode tres bien, mais H proche du hasard -> la dynamique detruit le signal
    assert nav_verdict(acc_obs=0.95, acc_H=0.30, match_emit=0.1, chance=0.25) == "ENCODER_GAP"


def test_verdict_readout_gap_when_H_preserves_but_action_wrong():
    # H preserve la direction (haut) mais l'agent ne fait pas le bon pas -> readout jette l'info
    assert nav_verdict(acc_obs=0.95, acc_H=0.85, match_emit=0.2, chance=0.25) == "READOUT_GAP"


def test_verdict_mixed_when_H_preserves_and_behavior_ok():
    # H preserve ET l'agent reussit deja -> pas de gap a localiser
    assert nav_verdict(acc_obs=0.95, acc_H=0.85, match_emit=0.8, chance=0.25) == "MIXED"
