import numpy as np
import pytest

from tools.kchain_edr import (
    Params, rollout_chain, survival_auc, NOOP, STEP, CONSUME, FORAGE, N_ACTIONS, OBS_DIM,
    oracle_chain_policy, metronome_policy, random_policy, oracle_forage_policy,
    binding_gap, _run_chain_logged, calibrate_K,
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


def test_binding_gap_oracle_high_random_low():
    # oracle : CONSUME ssi prog==K-1 -> binding_gap ~1. random : actions independantes de prog -> ~0.
    # NB (finding EDR 202) : le metronome N'EST PAS un controle negatif de BINDING : sous p_mat=0.8
    # sa cadence fixe (STEP..STEP,CONSUME) traque INCIDEMMENT prog -> gm ~0.71-0.83 a bas K (0 a K>=4).
    # Il reste le controle negatif de SURVIE (gate G2, il meurt via cons_empty). random est le vrai
    # controle negatif de binding : gr = 0.0 a TOUT K.
    P = Params(E0=50.0, T=200)
    orc = oracle_chain_policy(3)
    rnd = random_policy(7)
    _, so = _run_chain_logged(lambda obs, mem, prog: orc(obs, mem, prog), 'inesc', 3, P, seed=7, M=32)
    _, sr = _run_chain_logged(lambda obs, mem, prog: rnd(obs, mem, prog), 'inesc', 3, P, seed=7, M=32)
    go = binding_gap((*so, 3))
    gr = binding_gap((*sr, 3))
    assert go > 0.6            # l'oracle conditionne fortement (CONSUME ssi prog==K-1)
    assert gr < go - 0.3       # random independant de prog -> binding_gap ~0


def test_calibrate_k_contract():
    # CONTRAT seulement (config reduite) : structure + la fenetre.
    res = calibrate_K(2, seeds=(2000,), r_grid=(8.0, 12.0), e0_grid=(12.0, 24.0), M=16)
    assert set(res) >= {"ok", "R_K", "E0_K", "last"}
    assert isinstance(res["ok"], bool)
    if res["ok"]:
        assert res["R_K"] in (8.0, 12.0) and res["E0_K"] in (12.0, 24.0)
