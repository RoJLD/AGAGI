import numpy as np
import pytest
from tools.s2_demand_ablation import derange_rows, PerceptionAblatedMamba
from src.agents.mamba_agent import MambaBatchModel


def test_derange_no_fixed_point():
    np.random.seed(0)
    obs = np.arange(20 * 4, dtype=np.float32).reshape(20, 4)  # 20 lignes distinctes
    out = derange_rows(obs)
    assert out.shape == obs.shape
    # aucune ligne ne reste à sa place (dérangement)
    assert not np.any(np.all(out == obs, axis=1))
    # c'est bien une PERMUTATION des lignes d'origine (ensemble préservé)
    assert sorted(out[:, 0].tolist()) == sorted(obs[:, 0].tolist())


def test_derange_does_not_mutate_input():
    np.random.seed(1)
    obs = np.arange(12 * 3, dtype=np.float32).reshape(12, 3)
    before = obs.copy()
    _ = derange_rows(obs)
    assert np.array_equal(obs, before)      # entrée intacte


def test_derange_small_batch_is_identity():
    obs1 = np.ones((1, 5), dtype=np.float32)
    assert np.array_equal(derange_rows(obs1), obs1)
    obs0 = np.zeros((0, 5), dtype=np.float32)
    assert derange_rows(obs0).shape == (0, 5)


def test_forward_feeds_deranged_obs(monkeypatch):
    # On capture ce que le parent reçoit, sans instancier le vrai moteur.
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(PerceptionAblatedMamba)      # saute __init__ (pas d'agents)
    np.random.seed(2)
    obs = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)
    inst.forward(obs)
    # le parent a reçu une obs DÉRANGÉE (aucune ligne à sa place), pas l'obs d'origine
    assert not np.any(np.all(captured["obs"] == obs, axis=1))
    assert sorted(captured["obs"][:, 0].tolist()) == sorted(obs[:, 0].tolist())
