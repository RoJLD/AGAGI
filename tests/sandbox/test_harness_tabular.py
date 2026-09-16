"""Learner de vérité-terrain : une table de comptes apprend (q+key)%K par construction (T=1 : 36 clés),
la pièce `table` est nécessaire par construction, la pièce `decoy` est REFUSÉE par L4 (jamais « dispensable »)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import assert_learner_contract, run_episode  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tools.harness.learners.tabular import TabularLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402


def _train(inst, task, seed, episodes, n=16):
    rng = np.random.RandomState(seed + 1)
    for _ in range(episodes):
        ep = task.episodes(rng, n)
        actions, hits = run_episode(inst, ep, task)
        inst.learn(ep, actions, hits)
    return rng


def _accuracy(inst, task, rng, batches=40, n=16, ablate=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n)
        hits.append(run_episode(inst, ep, task, ablate=ablate)[1])
    return float(np.mean(np.concatenate(hits)))


def test_honest_tabular_passes_the_contract_on_both_regimes():
    for same_tick in (True, False):
        assert_learner_contract(TabularLearner(honest=True), CompositionTask(K=6, same_tick=same_tick), seed=0)


def test_decoy_piece_is_refused_by_L4_not_judged_dispensable():
    with pytest.raises(PreflightError, match="VACUOUS_PIECE.*decoy"):
        assert_learner_contract(TabularLearner(), CompositionTask(K=6), seed=0)


def test_table_learns_composition_and_reference_stays_at_chance():
    task = CompositionTask(K=6, same_tick=True)
    lrn = TabularLearner(honest=True)
    inst = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0})
    rng = _train(inst, task, 0, 300)
    assert _accuracy(inst, task, rng) > 0.95
    assert inst.dose().updates == 300 and inst.dose().calls == 300
    ref = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0}, reference=True)
    rng_r = _train(ref, task, 0, 300)
    assert ref.dose().updates == 0 and ref.dose().dparam_abs_sum == 0.0
    assert abs(_accuracy(ref, task, rng_r) - 1 / 6) < 0.1


def test_without_table_falls_to_chance_and_state_reset_kills_two_step():
    task = CompositionTask(K=6, same_tick=False)
    lrn = TabularLearner(honest=True)
    inst = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0})
    rng = _train(inst, task, 0, 600)
    state = rng.get_state()
    acc = _accuracy(inst, task, rng)
    rng.set_state(state)
    acc_reset = _accuracy(inst, task, rng, ablate="state_reset")
    assert acc > 0.95 and abs(acc_reset - 1 / 6) < 0.1
    off = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0}, without={"table": True})
    rng_o = _train(off, task, 0, 600)
    assert abs(_accuracy(off, task, rng_o) - 1 / 6) < 0.1
