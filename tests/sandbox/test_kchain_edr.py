import numpy as np
import pytest

from tools.kchain_edr import (
    Params, rollout_chain, survival_auc, NOOP, STEP, CONSUME, FORAGE, N_ACTIONS, OBS_DIM,
    oracle_chain_policy, metronome_policy, random_policy, oracle_forage_policy,
)


def test_oracle_chain_survives_with_materials_k2():
    # K=2, materiau TOUJOURS present : l'oracle STEP (prog 0->1) puis CONSUME (+R) -> gain net positif -> survit.
    p = Params(E0=50.0, T=8)
    mat = np.ones((1, 8), dtype=float)
    am = rollout_chain(oracle_chain_policy(2), 'inesc', 2, p, seed=0, M=1, mat_stream=mat)
    assert am.shape == (1, 8)
    assert am.all()   # drift positif -> vivant tout du long


def test_metronome_consume_empty_penalty_k3():
    # K=3, materiau ABSENT : le metronome STEP,STEP,CONSUME open-loop -> STEP gaspilles (pas de mat) -> prog reste 0
    # -> CONSUME a prog<K-1 = consume_empty (cout 6) -> meurt vite. E0 bas.
    p = Params(E0=6.0, T=30)
    mat = np.zeros((1, 30), dtype=float)
    am = rollout_chain(metronome_policy(3), 'inesc', 3, p, seed=0, M=1, mat_stream=mat)
    assert not am[:, -1].any()   # mort


def test_rollout_determinism():
    a = rollout_chain(random_policy(5), 'inesc', 3, Params(T=100), seed=5, M=16)
    b = rollout_chain(random_policy(5), 'inesc', 3, Params(T=100), seed=5, M=16)
    assert np.array_equal(a, b)


def test_survival_auc_range():
    am = rollout_chain(oracle_chain_policy(2), 'inesc', 2, Params(E0=50.0, T=40), seed=1, M=8)
    s = survival_auc(am)
    assert 0.0 <= s <= 1.0
