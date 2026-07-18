import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.tom_probe import (
    _make_cfg_tom,
    _head_accuracy,
    _shuffle_accuracy,
    _latent_probe,
    _verdict_tom_emergence,
    _collect_pairs_from_agents,
    _agent_latent,
    main_tom_probe,
)


def test_make_cfg_tom_sets_flag_and_keeps_sweet():
    cfg = _make_cfg_tom("TOM")
    assert cfg.active_exp_variable == "TOM"
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0
    assert _make_cfg_tom("NONE").active_exp_variable == "NONE"


def _rec(pred, act, latent=None):
    return {"pred": pred, "act": act, "latent": np.zeros(68) if latent is None else latent}


def test_head_accuracy_exact_fraction():
    recs = [_rec(3, 3), _rec(3, 3), _rec(3, 3), _rec(0, 1)]
    assert _head_accuracy(recs) == 0.75
    assert _head_accuracy([]) == 0.0


def test_shuffle_accuracy_deterministic_edges():
    assert _shuffle_accuracy([_rec(3, 3), _rec(3, 3)]) == 1.0
    assert _shuffle_accuracy([_rec(0, 1), _rec(0, 1)]) == 0.0
    assert _shuffle_accuracy([]) == 0.0


def test_latent_probe_separable_beats_shuffle():
    np.random.seed(0)
    recs = []
    for c in range(4):
        base = np.zeros(68)
        base[c] = 5.0
        for _ in range(30):
            lat = base + np.random.randn(68) * 0.1
            recs.append(_rec(c, c, lat))
    acc_true, acc_shuffle = _latent_probe(recs)
    assert acc_true > 0.8
    assert acc_true > acc_shuffle


def test_latent_probe_too_few_records():
    assert _latent_probe([_rec(0, 0)]) == (0.0, 0.0)


def test_verdict_tom_emergence_two_branches():
    assert _verdict_tom_emergence(0.45, 0.20, 0.22) == "TOM_EMERGES"
    assert _verdict_tom_emergence(0.22, 0.20, 0.21) == "TOM_INERT"
    assert _verdict_tom_emergence(0.40, 0.35, 0.20) == "TOM_INERT"


def _fake_model(pred_argmax):
    ph = np.zeros(8)
    ph[pred_argmax] = 1.0
    return types.SimpleNamespace(
        predictor_head=ph,
        goal_vector=np.zeros(5),
        explicit_memory=np.zeros(5),
        ntm_memory=np.zeros((10, 5)),
    )


def _fake_agent(x, y, pred_argmax, last_action):
    return {"x": x, "y": y, "z": 0, "last_action": last_action, "model": _fake_model(pred_argmax)}


def test_collect_pairs_same_cell_both_directions():
    a = _fake_agent(0, 0, pred_argmax=3, last_action=2)
    b = _fake_agent(0, 0, pred_argmax=5, last_action=3)
    far = _fake_agent(9, 9, pred_argmax=1, last_action=1)
    records = []
    _collect_pairs_from_agents([a, b, far], records)
    assert len(records) == 2
    preds_acts = sorted((r["pred"], r["act"]) for r in records)
    assert (3, 3) in preds_acts and (5, 2) in preds_acts
    assert all(r["latent"].shape == (68,) for r in records)


def test_agent_latent_shape_and_none_guard():
    assert _agent_latent(_fake_model(0)).shape == (68,)
    empty = types.SimpleNamespace(predictor_head=None, goal_vector=None, explicit_memory=None, ntm_memory=None)
    assert _agent_latent(empty).shape == (68,)


def test_smoke_main_tom_probe_returns_verdict():
    res = main_tom_probe(R=1, eras=2, num_agents=12, max_ticks=80, seed=99280, _return=True)
    assert res["verdict"] in {"TOM_EMERGES", "TOM_INERT"}
    assert len(res["per_seed"]) == 1
    assert set(res["per_seed"][0].keys()) >= {"seed", "ctrl", "tom"}


def test_shuffle_accuracy_idempotent():
    recs = [_rec(i % 8, (i * 3) % 8) for i in range(50)]
    assert _shuffle_accuracy(recs) == _shuffle_accuracy(recs)
