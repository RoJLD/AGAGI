# tests/sandbox/test_harness_composition.py
"""Port de la tâche (q+key)%K : les épisodes sont BIT-IDENTIQUES à _make_seq au même rng (c'est ce qui rend la
cellule A rejouable), le contrat passe, et chaque ablation rend l'issue attendue sur l'oracle."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import assert_task_contract  # noqa: E402
from tools.bilinear_composition_probe import _make_seq  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402


@pytest.mark.parametrize("same_tick,kind", [(True, "composition"), (False, "composition"), (True, "recall")])
def test_episodes_are_bit_identical_to_make_seq(same_tick, kind):
    task = CompositionTask(K=6, same_tick=same_tick, kind=kind)
    rng = np.random.RandomState(1)
    ep = task.episodes(rng, 16)
    ref = np.random.RandomState(1)
    key = ref.randint(0, 6, size=16)
    q = ref.randint(0, 6, size=16)
    seq, mask = _make_seq(key, q, kind, 6, 59, 16, same_tick)
    assert all(np.array_equal(a, b) for a, b in zip(ep.obs_seq, seq))
    assert (mask is None and ep.mask_seq is None) or all(np.array_equal(a, b) for a, b in zip(ep.mask_seq, mask))
    tgt = (q + key) % 6 if kind == "composition" else key
    assert np.array_equal(ep.target, tgt)
    assert rng.randint(0, 6) == ref.randint(0, 6)     # même position de rng après l'appel


@pytest.mark.parametrize("same_tick", [True, False])
def test_contract_passes_and_names_bayes_floors(same_tick):
    out = assert_task_contract(CompositionTask(K=6, same_tick=same_tick), seed=0, n=256)
    assert out["certified"] is True
    assert out["bayes_floors"]["permute_key"] == pytest.approx(1 / 6)
    assert out["bayes_floors"]["permute_query"] == pytest.approx(1 / 6)
    if not same_tick:
        assert out["bayes_floors"]["state_reset"] == pytest.approx(1 / 6)


def test_recall_declares_query_as_non_biting():
    task = CompositionTask(K=6, same_tick=True, kind="recall")
    names = {a.name: a.must_bite for a in task.demand.ablations}
    assert names["permute_key"] is True and names["permute_query"] is False
    assert_task_contract(task, seed=0, n=256)


def test_control_split_re_presents_key_at_the_answer_step():
    task = CompositionTask(K=6, same_tick=False)
    ep = task.episodes(np.random.RandomState(3), 8, split="control")
    key, q = ep.meta["key"], ep.meta["q"]
    assert ep.T == 2
    assert np.array_equal(ep.obs_seq[1][np.arange(8), key], np.ones(8, dtype=np.float32))
    assert np.array_equal(ep.obs_seq[1][np.arange(8), 6 + q], np.ones(8, dtype=np.float32))
    assert np.array_equal(ep.target, (q + key) % 6)


def test_regime_is_published_and_ceiling_is_the_frozen_minorant():
    task = CompositionTask(K=6, same_tick=True)
    r = task.regime()
    assert r["K"] == 6 and r["T"] == 1 and r["same_tick"] is True and r["kind"] == "composition"
    value, prov, proven = task.demand.incapable_ceiling
    assert value == pytest.approx(34 / 36) and proven is False and len(prov) >= 20
