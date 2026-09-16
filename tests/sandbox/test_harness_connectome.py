# -*- coding: utf-8 -*-
"""Adaptateur connectome : contrat L0-L7, bit-identité de la cellule A (seed 0 : 0,932812511920929 / 0,27031248807907104,
results bilinear_composition.json), régime de la cellule B (n_classes=6 : 0,932812511920929 au seed 0), référence lr=0."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_learner import assert_learner_contract  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402

HYPER_A = {"lr": 0.02, "rank": 16, "n_classes": None, "credit": "supervised"}
HYPER_B = {"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"}


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
    task, lrn = CompositionTask(K=6, same_tick=False), ConnectomeLearner()
    res = _run_arm(task, lrn, 0, 16, 6, HYPER_B, 600, 40, full_eval=True)
    assert res["last"] == 0.932812511920929                          # retain_compose_lr_replication lr_0.002 learned[0]
    assert res["ablated"]["state_reset"] < 0.3
    assert 0.2 < res["control"]["state_reset"]["intact"]              # le split control est PUBLIÉ, pas supposé
