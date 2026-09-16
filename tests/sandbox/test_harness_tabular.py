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


def _accuracy_input_ablated(inst, task, rng, ablation, batches=40, n=16):
    """Comme `_accuracy`, mais applique une ablation D'ENTRÉE (site="input", ex. `inject_distractor_slot`,
    `permute_key`) à chaque lot AVANT run_episode -- distincte de `ablate=` de `_accuracy`, qui vise
    `inst.ablate_state` (site="state"). `rng` tire les épisodes en CONTINUATION (jamais réinitialisé
    entre appels) ; l'ablation elle-même consomme un flux SÉPARÉ (`RandomState(31)`, dédié)."""
    abl_rng = np.random.RandomState(31)
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n)
        ep_a = ablation.apply(ep, abl_rng)
        hits.append(run_episode(inst, ep_a, task)[1])
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


def test_specificity_control_spares_the_reader_but_permute_key_bites():
    """Revue (fix round 1) : `_keys` hachait TOUTE la ligne d'observation -- sous `inject_distractor_slot`
    (contrôle de spécificité must_bite=False, l'oracle reste à 1.0), le bit du slot distracteur, jamais
    actif à l'entraînement, faisait diverger la clé vers une entrée jamais peuplée : chute à la chance,
    un artefact de HACHAGE plein-ligne, pas une lecture du canal decoy -- le runner aurait lu X_DECOY
    comme INCONCLUSIVE_SPECIFICITY sur le learner de vérité-terrain lui-même. Après le fix (`seen_cols`
    filtre `act` aux colonnes VUES à l'entraînement), le contrôle ne mord plus ; `permute_key`
    (must_bite=True, change une colonne DÉJÀ vue) continue de mordre."""
    task = CompositionTask(K=6, same_tick=True)
    lrn = TabularLearner(honest=True)
    inst = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0})
    rng = _train(inst, task, 0, 300)
    acc_intact = _accuracy(inst, task, rng)
    inject = next(a for a in task.demand.ablations if a.name == "inject_distractor_slot")
    permute = next(a for a in task.demand.ablations if a.name == "permute_key")
    assert inject.must_bite is False and permute.must_bite is True
    acc_decoy = _accuracy_input_ablated(inst, task, rng, inject)
    acc_bite = _accuracy_input_ablated(inst, task, rng, permute)
    assert acc_intact > 0.95
    assert acc_decoy > 0.95, f"le controle de specificite MORD ({acc_decoy:.3f}) : artefact de hachage"
    assert acc_bite < 0.30, f"l'ablation must_bite ne mord plus ({acc_bite:.3f})"
