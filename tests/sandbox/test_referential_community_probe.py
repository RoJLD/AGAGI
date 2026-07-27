"""Tests du jeu référentiel COMMUNAUTAIRE (LANG-002, rotation de partenaires). Pur. Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.referential_community_probe import run_community
from src.agents.backend_torch import TorchPopulationModel


def test_run_community_smoke_keys():
    r = run_community(episodes=20, n_agents=16, K=4, V=6, seed=0, rotate=True, eval_shifts=3)
    assert set(r) >= {"within", "cross", "mi", "chance", "K", "V", "rotate", "learned"}
    assert r["chance"] == pytest.approx(0.25)
    assert r["rotate"] is True
    for k in ("within", "cross"):
        assert 0.0 <= r[k] <= 1.0
    # flags de classe restaurés (pas de gate ici).
    assert TorchPopulationModel.CONDITION_GATE is False
    assert TorchPopulationModel.GATE_TARGET is None


def test_fixed_reduces_to_paired_game():
    # rotate=False => décalage s=0 => appariement d'origine (sender_i<->receiver_i) : within est la
    # diagonale, cross échantillonne des partenaires jamais co-appariés (décalés).
    r = run_community(episodes=30, n_agents=32, K=4, V=6, seed=1, rotate=False, eval_shifts=3)
    assert r["rotate"] is False
    # within >= cross attendu sous paires figées (code potentiellement privé) — borne large (bruit).
    assert r["within"] >= r["cross"] - 0.20


def test_mi_is_nan_when_unlearned():
    # 5 épisodes -> régime non-appris (within ~ chance) -> MI marqué NaN (dénominateur ininterprétable).
    r = run_community(episodes=5, n_agents=16, K=6, V=8, seed=2, rotate=True, eval_shifts=2)
    if not r["learned"]:
        assert r["mi"] != r["mi"]   # NaN
