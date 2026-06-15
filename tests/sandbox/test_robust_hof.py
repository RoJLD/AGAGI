"""Tests du HoF robuste (EDR 078/079/080) — câblage gated + de-bruitage de la sélection."""
import inspect

import numpy as np
import pytest

from src.environments.config import WorldConfig
from src.seed_ai import robust_hof
from src.seed_ai.persistence import save_to_hall_of_fame


def test_robust_hof_K_default_off():
    # Gated : défaut 0 -> comportement historique (non-régression).
    assert WorldConfig().robust_hof_K == 0


def test_save_to_hof_accepts_external_score():
    # save_to_hall_of_fame doit accepter un score robuste fourni (au lieu du life_score d'une ère).
    assert "score" in inspect.signature(save_to_hall_of_fame).parameters


def test_robust_hof_exposes_api():
    assert callable(robust_hof.robust_evaluate)
    assert callable(robust_hof.robust_rank)


def test_robust_rank_skips_genomeless_and_sorts(monkeypatch):
    # robust_rank trie par score robuste décroissant et ignore les candidats sans génome.
    scores = {"A": 5.0, "B": 9.0, "C": 2.0}
    monkeypatch.setattr(robust_hof, "robust_evaluate",
                        lambda cfg, g, K, num_agents=20, seed=None: scores[g])
    cands = [{"genome": "A"}, {"genome": "B"}, {"no_genome": True}, {"genome": "C"}]
    ranked = robust_hof.robust_rank(WorldConfig(), cands, K=3)
    assert [g for _s, c in ranked for g in [c["genome"]]] == ["B", "A", "C"]   # 9 > 5 > 2
    assert len(ranked) == 3                                                    # le candidat sans génome est ignoré


def test_robust_evaluate_returns_zero_without_pool(monkeypatch):
    # Robustesse : si aucune ère n'est scorable (pool vide), renvoie 0.0 (pas d'exception).
    from src.agents.mamba_agent import MambaAgent

    class _Env:
        def __init__(self, cfg):
            self.agents = []
            self.dead_agents = []
        def add_agent(self, a, energy=0.0): pass
        def step(self): pass
    monkeypatch.setattr("src.worlds.world_1_stoneage.Biosphere3D", _Env, raising=False)
    out = robust_hof.robust_evaluate(WorldConfig(), MambaAgent().genome, K=2, num_agents=3, max_ticks=5)
    assert out == 0.0
