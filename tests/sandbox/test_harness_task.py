# tests/sandbox/test_harness_task.py
"""Contrat Task du harnais (spec 2026-09-16 §2.1) : la garde refuse en tête, en < 50 ms, sans entraînement,
tout ce qui rendrait le marqueur de demande incapable de produire LES DEUX issues (question A du pré-vol)."""
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode, assert_task_contract  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402


class ToyParity:
    """Tâche jouet : obs (n, 4) one-hot de a dans [0,2) sur [0:2) et b sur [2:4) ; cible (a + b) % 2 ; T == 1."""
    name, version, K, obs_dim, T = "toy_parity", "1", 2, 4, 1

    def __init__(self, bite_key=True, with_nobite=True, ceiling=(0.75, "plafond jouet declare pour le test, minorant", False)):
        abls = [Ablation("permute_a", "input", bite_key, apply=self._permute_a, bayes_floor=0.5)]
        if with_nobite:
            abls.append(Ablation("permute_nothing", "input", False, apply=self._permute_nothing))
        self.demand = DemandDeclaration("parity", tuple(abls), incapable_ceiling=ceiling)

    def episodes(self, rng, n, split="train"):
        a = rng.randint(0, 2, size=n)
        b = rng.randint(0, 2, size=n)
        obs = np.zeros((n, 4), dtype=np.float32)
        obs[np.arange(n), a] = 1.0
        obs[np.arange(n), 2 + b] = 1.0
        return Episode((obs,), ((a + b) % 2).astype(np.int64), None, {"a": a, "b": b})

    def _permute_a(self, ep, rng):
        a2 = ep.meta["a"][rng.permutation(ep.n)]
        obs = np.zeros_like(ep.obs_seq[0])
        obs[np.arange(ep.n), a2] = 1.0
        obs[np.arange(ep.n), 2 + ep.meta["b"]] = 1.0
        return Episode((obs,), ep.target.copy(), None, {"a": a2, "b": ep.meta["b"]})

    def _permute_nothing(self, ep, rng):
        return Episode((ep.obs_seq[0].copy(),), ep.target.copy(), None, dict(ep.meta))

    def score(self, actions, ep):
        if ep.n == 0:
            raise ValueError("score : episode vide")
        return (np.asarray(actions) == ep.target).astype(np.float32)

    def oracle(self, ep):
        return (ep.meta["a"] + ep.meta["b"]) % 2

    def enumerate_states(self):
        return 4

    def regime(self):
        return {"K": 2, "T": 1}


def test_toy_task_passes_the_contract_and_reports_bayes_floors():
    out = assert_task_contract(ToyParity(), seed=0, n=64)
    assert out["certified"] is True
    assert out["bayes_floors"] == {"permute_a": 0.5}
    assert out["elapsed_ms"] < 50.0


def test_contract_refuses_a_task_without_a_non_biting_ablation():
    with pytest.raises(PreflightError, match="must_bite=False"):
        assert_task_contract(ToyParity(with_nobite=False))


def test_contract_refuses_a_biting_ablation_that_does_not_bite():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (Ablation("permute_nothing", "input", True, apply=task._permute_nothing),
                                               Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="permute_nothing"):
        assert_task_contract(task)


def test_contract_refuses_a_verifier_that_is_the_oracle():
    task = ToyParity()
    task.score = lambda actions, ep: np.ones(ep.n, dtype=np.float32)   # note 1.0 quoi qu'on reponde
    with pytest.raises(PreflightError, match="oracle décalé"):
        assert_task_contract(task)


def test_contract_refuses_an_aliased_ablation():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (
        Ablation("alias", "input", True, apply=lambda ep, rng: Episode(ep.obs_seq, ep.target, None, dict(ep.meta)), bayes_floor=0.5),
        Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="shares_memory|VUE"):
        assert_task_contract(task)


def test_contract_refuses_chance_as_representational_ceiling():
    with pytest.raises(PreflightError, match="1/K"):
        assert_task_contract(ToyParity(ceiling=(0.5, "chance deguisee en plafond, vingt caracteres", False)))


def test_contract_refuses_a_short_provenance():
    with pytest.raises(PreflightError, match="provenance"):
        assert_task_contract(ToyParity(ceiling=(0.75, "court", False)))


def test_contract_refuses_non_reproducible_episodes():
    task = ToyParity()
    task.episodes = lambda rng, n, split="train": ToyParity.episodes(task, np.random.RandomState(), n, split)
    with pytest.raises(PreflightError, match="bit-identique"):
        assert_task_contract(task)


def test_state_ablation_requires_a_control_split():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (Ablation("state_reset", "state", True, bayes_floor=0.5),
                                               Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="control"):
        assert_task_contract(task)
