import numpy as np
import pytest

from tools.craft_or_starve_edr import (
    Params, rollout, survival_auc, NOOP, CRAFT, CONSUME, FORAGE, N_ACTIONS, OBS_DIM,
    oracle_composer_policy, metronome_policy, oracle_forage_policy, random_policy,
)


def test_composer_accounting_alternating_stream():
    # stream mat = [1,0,1,0] : composeur => cycle mat=1 : +5.5 ; cycle mat=0 : -2.0. E0 haut => reste vivant.
    p = Params(E0=100.0, T=4)
    mat = np.array([[1, 0, 1, 0]], dtype=float)
    am = rollout(oracle_composer_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    assert am.shape == (1, 4)
    assert am.all()  # E0=100, drift positif => vivant tout du long


def test_metronome_dies_faster_than_composer_same_stream():
    # meme stream : metronome cycle mat=1 : +5.5 ; cycle mat=0 : -11.0 (craft-sans-mat -3 + consume-vide -6 + 2h)
    p = Params(E0=6.0, T=8)
    mat = np.array([[0, 0, 0, 0, 0, 0, 0, 0]], dtype=float)  # que du mat=0 : pire cas
    am_metro = rollout(metronome_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    am_comp = rollout(oracle_composer_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    # metronome : -11/cycle => mort au 1er cycle (E0=6) ; composeur : -2/cycle => survit plus longtemps
    assert not am_metro[0, 0]                 # metronome mort des le 1er tick
    assert am_comp[:, :2].all()               # composeur encore vivant a t=0 et t=1


def test_absorbing_death():
    p = Params(E0=1.5, T=5)
    mat = np.zeros((1, 5), dtype=float)
    am = rollout(metronome_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    # une fois mort, reste mort (monotone decroissant de alive)
    a = am[0]
    assert not a[-1]
    for i in range(1, len(a)):
        assert not (a[i] and not a[i - 1])   # jamais de resurrection


def test_absent_arm_forage_delivers_unconditionally():
    # bras absent : FORAGE en S1 => +f_forage a S2 sans condition. oracle_forage survit (net +2/cycle).
    p = Params(E0=6.0, T=50, f_forage=4.0)
    am_forage = rollout(oracle_forage_policy(), 'absent', p, seed=1, M=1)
    am_noop = rollout(metronome_policy(), 'absent', p, seed=1, M=1)  # ne forage jamais (CRAFT/CONSUME inertes en absent)
    assert am_forage.all()          # forage net positif => vivant
    assert not am_noop[0, -1]       # jamais de nourriture => meurt


def test_determinism_two_rollouts_identical():
    p = Params(E0=10.0, T=100)
    a = rollout(random_policy(7), 'inesc', p, seed=7, M=32)
    b = rollout(random_policy(7), 'inesc', p, seed=7, M=32)
    assert np.array_equal(a, b)


def test_survival_auc_range_and_median():
    # alive_matrix synthetique : 3 agents, T=8, dernier quart = 2 derniers ticks
    am = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1],   # vivant : dernier quart = 1.0
        [1, 1, 1, 1, 1, 1, 0, 0],   # mort avant dernier quart : 0.0
        [1, 1, 1, 1, 1, 1, 1, 0],   # dernier quart = [1,0] => 0.5
    ], dtype=bool)
    # medianes-par-agent = median(1.0, 0.0, 0.5) = 0.5
    assert survival_auc(am) == pytest.approx(0.5)


def test_obs_shape_and_action_space():
    p = Params(E0=100.0, T=1)
    seen = {}

    def probe(obs, mem, phase):
        seen['obs_dim'] = obs.shape[1]
        return np.full(obs.shape[0], NOOP, dtype=int), mem

    rollout(probe, 'inesc', p, seed=0, M=3)
    assert seen['obs_dim'] == OBS_DIM
    assert N_ACTIONS == 8
