# -*- coding: utf-8 -*-
"""Adaptateur connectome : contrat L0-L7, bit-identité de la cellule A (seed 0 : 0,932812511920929 / 0,27031248807907104,
results bilinear_composition.json), régime de la cellule B (n_classes=6 : retain_compose_lr_replication.json, lr_0.002,
per_seed.learned[0] au seed 0), référence lr=0.

Revue contrôleur, fix round 1 (2026-09-16) : deux nouveaux cas -- CRITICAL 1 (un build qui échoue AVANT
d'avoir rejoint _OPEN ne doit jamais laisser les drapeaux de classe mutés, y compris quand l'échec survient
PENDANT la construction de la population/de l'optimiseur) et IMPORTANT 2 (bilinear_sham=True sans
bilinear=True est refusé, pas silencieusement inerte). Ni l'un ni l'autre n'appelle `learn` (seul `build`
est exercé) -- aucun nouveau libellé de calibration n'est donc nécessaire dans test_instrument_calibration.py."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.agents.backend_torch import TorchPopulationModel  # noqa: E402
from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_learner import assert_learner_contract  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402

HYPER_A = {"lr": 0.02, "rank": 16, "n_classes": None, "credit": "supervised"}
HYPER_B = {"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"}


def _flags():
    return (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
            TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK,
            TorchPopulationModel.BILINEAR_SHAM)


def test_connectome_passes_the_learner_contract():
    out = assert_learner_contract(ConnectomeLearner(), CompositionTask(K=6, same_tick=False), seed=0)
    assert out["n_pieces"] == 3 and out["reference_dparam"] == 0.0


def test_two_open_instances_with_different_flags_are_refused():
    lrn, task = ConnectomeLearner(), CompositionTask(K=6)
    a = lrn.build(0, 4, task.obs_dim, 6, HYPER_A)
    try:
        with pytest.raises(RuntimeError, match="drapeaux"):
            lrn.build(0, 4, task.obs_dim, 6, HYPER_A, without={"bilinear": False})
    finally:
        a.close()


def test_a_failing_build_never_leaks_class_flags():
    """CRITICAL 1 (revue contrôleur, fix round 1) : un build qui échoue AVANT (credit invalide -- pur,
    aucun drapeau touché) ou PENDANT (n=0 -- Adam lève sur une liste de paramètres vide/None APRÈS que
    les drapeaux ont été écrits) la construction ne doit jamais laisser les drapeaux de classe mutés ;
    avant ce fix la fuite était PERMANENTE (le build suivant capturait l'état fuité comme `_ORIGINAL`)."""
    lrn, task = ConnectomeLearner(), CompositionTask(K=6)
    original = _flags()
    with pytest.raises(NotImplementedError):
        lrn.build(0, 4, task.obs_dim, 6, dict(HYPER_A, credit="reinforce"))
    assert _flags() == original
    with pytest.raises(TypeError):
        lrn.build(0, 0, task.obs_dim, 6, HYPER_A)
    assert _flags() == original
    a = lrn.build(0, 4, task.obs_dim, 6, HYPER_A)
    a.close()
    assert _flags() == original


def test_bilinear_sham_without_bilinear_is_refused():
    """IMPORTANT 2 (revue contrôleur, fix round 1) : bilinear_sham=True avec bilinear=False était accepté
    et silencieusement INERTE (la branche sham de _step est sous le garde BILINEAR ; U/V/W_bl restent
    None) -- doit lever AVANT tout drapeau, pas produire un run qui mesure autre chose que ce qu'il
    annonce."""
    lrn, task = ConnectomeLearner(), CompositionTask(K=6)
    original = _flags()
    with pytest.raises(ValueError, match="sham"):
        lrn.build(0, 4, task.obs_dim, 6, dict(HYPER_A, bilinear_sham=True), without={"bilinear": False})
    assert _flags() == original


@pytest.mark.slow
def test_cell_A_seed0_is_bit_identical_to_the_published_json():
    pub = json.load(open(results_file("bilinear_composition.json"), encoding="utf-8"))["decisive_same_tick_supervised"]["per_seed"]
    task, lrn = CompositionTask(K=6, same_tick=True), ConnectomeLearner()
    bil = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, full_eval=True)
    assert bil["last"] == pub["bilinear"][0]                       # 0.932812511920929, EXACT
    plain = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, without={"bilinear": False})
    assert plain["last"] == pub["plain"][0]                        # 0.27031248807907104, EXACT
    ref = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, reference=True)
    assert ref["dose"]["updates"] == 0 and ref["dose"]["calls"] == 300
    assert abs(ref["last"] - 0.16875000298023224) < 1e-9            # mesuré le 2026-09-16 (même nombre d'épisodes)
    assert bil["oracle"] == 1.0 and 0.9 < bil["noop"] < 1.0 and bil["ablated"]["permute_key"] < 0.3


@pytest.mark.slow
def test_cell_B_regime_reproduces_retain_compose_at_seed0():
    known = json.load(open(results_file("retain_compose_lr_replication.json"), encoding="utf-8"))
    known_last = known["lr_0.002"]["per_seed"]["learned"][0]        # même discipline que la cellule A : LU, pas recopié
    task, lrn = CompositionTask(K=6, same_tick=False), ConnectomeLearner()
    res = _run_arm(task, lrn, 0, 16, 6, HYPER_B, 600, 40, full_eval=True)
    assert res["last"] == known_last                                 # 0.932812511920929, EXACT
    assert res["ablated"]["state_reset"] < 0.3
    assert 0.2 < res["control"]["state_reset"]["intact"]              # le split control est PUBLIÉ, pas supposé
