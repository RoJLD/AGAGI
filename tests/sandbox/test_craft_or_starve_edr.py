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


def test_dip_then_recover_survives_single_mortality_check():
    # E0=1.0, un seul tick, mat=1, oracle_composer : S1 craft-avec-mat (-c_craft -h) fait plonger E sous 0,
    # mais S2 consume-avec-inv (+R -h) le rachete au-dessus de 0 -> DOIT survivre (mort verifiee 1x en fin de tick).
    # E = 1.0 -0.5 -1.0 -1.0 +8.0 = 6.5 > 0.
    p = Params(E0=1.0, T=1)
    mat = np.array([[1]], dtype=float)
    am = rollout(oracle_composer_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    assert am[0, 0]   # vivant en fin de tick 0 (aurait ete tue par un double-check apres S1)


from tools.craft_or_starve_edr import check_viability_gates, calibrate, PILOT_SEEDS


def test_gates_structure_and_bools():
    res = check_viability_gates(Params(E0=16.0), seeds=(1000, 1001), M=32)
    assert set(res['gates']) >= {'G1_oracle_composer', 'G2_random_inesc', 'G3_forage', 'G5_metronome', 'ALL'}
    assert set(res['aucs']) >= {'oracle_composer', 'random_inesc', 'oracle_forage', 'random_absent', 'metronome'}
    for v in res['gates'].values():
        assert isinstance(v, (bool, np.bool_))


def test_world_discriminates_conditioning():
    # coeur du pilote : a E0 confortable, l'oracle-composeur survit BEAUCOUP mieux que metronome ET random.
    res = check_viability_gates(Params(E0=16.0), seeds=(1000, 1001), M=64)
    a = res['aucs']
    assert a['oracle_composer'] > a['metronome']
    assert a['oracle_composer'] > a['random_inesc']
    assert a['oracle_composer'] >= 0.90        # G1 doit tenir a E0 confortable
    assert a['metronome'] <= 0.40              # G5 : l'horloge ne survit pas


def test_gates_deterministic():
    r1 = check_viability_gates(Params(E0=12.0), seeds=(1000, 1001), M=32)
    r2 = check_viability_gates(Params(E0=12.0), seeds=(1000, 1001), M=32)
    assert r1['aucs'] == r2['aucs']


def test_calibrate_returns_ok_or_report():
    # on ne prejuge PAS du verdict (GATE DUR du controleur) : on verifie le CONTRAT + la fenetre viable.
    res = calibrate(seeds=(1000, 1001), e0_grid=(16.0, 24.0), M=32)
    assert 'ok' in res and 'grid' in res
    assert len(res['grid']) == 2                      # grid balaye TOUT le grille (pas d'early-return)
    for row in res['grid']:
        assert set(row) >= {'E0', 'all', 'composer', 'metronome'}
    if res['ok']:
        assert res['result']['gates']['ALL']
        assert res['E0_min_viable'] in (16.0, 24.0)


# === Phase B1a : apprenant L0 (REINFORCE tronque, pur numpy) ===

from tools.craft_or_starve_edr import (
    N_H, LR, TEMP, _softmax, NpReinforceLearner, rollout_learn,
)


def test_softmax_stable_and_normalized():
    p = _softmax(np.array([[1000.0, 1000.0, 1000.0, 0, 0, 0, 0, 0]]))
    assert np.isfinite(p).all()
    assert abs(p.sum() - 1.0) < 1e-9
    assert p[0, 0] == pytest.approx(p[0, 1])


def test_learner_shapes_and_determinism():
    l1 = NpReinforceLearner(seed=0, arm="inesc")
    l1.reset_state(4)
    obs = np.zeros((4, 6))
    a = l1.act(obs)
    assert a.shape == (4,) and a.dtype.kind in "iu"
    assert (a >= 0).all() and (a < N_ACTIONS).all()
    # deux rollouts d'apprentissage au meme seed -> poids byte-identiques
    a_learner = rollout_learn(NpReinforceLearner(seed=7, arm="inesc"), "inesc", Params(E0=16.0, T=40), seed=7, M=8, n_episodes=3)
    b_learner = rollout_learn(NpReinforceLearner(seed=7, arm="inesc"), "inesc", Params(E0=16.0, T=40), seed=7, M=8, n_episodes=3)
    assert np.array_equal(a_learner.W_out, b_learner.W_out)
    assert np.array_equal(a_learner.W_hh, b_learner.W_hh)


def test_learner_updates_weights():
    # l'apprentissage DOIT bouger les poids (sinon le gradient est nul = bug)
    learner = NpReinforceLearner(seed=1, arm="inesc")
    W0 = learner.W_out.copy()
    rollout_learn(learner, "inesc", Params(E0=16.0, T=60), seed=1, M=16, n_episodes=5)
    assert not np.allclose(learner.W_out, W0)


# === Phase B1a Task 2 : metriques d'evaluation (binding_gap tick-level, null-metronome) ===

from tools.craft_or_starve_edr import evaluate_learner, null_metronome_gap


def test_evaluate_learner_contract():
    learner = rollout_learn(NpReinforceLearner(seed=2, arm="inesc"), "inesc", Params(E0=16.0, T=80), seed=2, M=16, n_episodes=8)
    res = evaluate_learner(learner, "inesc", Params(E0=16.0, T=200), seed=99, M=32)
    assert set(res) >= {"survival", "binding_gap", "p_c_inv1", "p_c_inv0", "craft_rate"}
    assert 0.0 <= res["survival"] <= 1.0
    assert -1.0 <= res["binding_gap"] <= 1.0
    # binding_gap == p_c_inv1 - p_c_inv0
    assert res["binding_gap"] == pytest.approx(res["p_c_inv1"] - res["p_c_inv0"], abs=1e-9)


def test_null_metronome_gap_is_low():
    # l'horloge open-loop ne conditionne pas sur inv -> gap ~0 (borne null). Materiau stochastique p_mat=0.5.
    g = null_metronome_gap(Params(E0=16.0, T=200), seed=5, M=64)
    assert abs(g) < 0.15


# === Phase B1a Task 3 : re-calibration apprenant + GATE DUR ===

from tools.craft_or_starve_edr import recalibrate_learner


def test_recalibrate_learner_contract():
    # on ne prejuge PAS du verdict (GATE DUR du controleur) : on verifie le CONTRAT + la fenetre.
    res = recalibrate_learner(seeds=(1000,), e0_grid=(16.0, 32.0), M=16, n_episodes=10)
    assert "ok" in res and "grid" in res and "gate" in res
    assert len(res["grid"]) == 2
    for row in res["grid"]:
        assert set(row) >= {"E0", "g4_headroom", "binding_adv", "pass"}
    if res["ok"]:
        assert res["E0_learner"] in (16.0, 32.0)
