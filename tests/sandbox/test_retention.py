"""Tests de la carte de rétention — oubli catastrophique (EDR 009 §2)."""
import numpy as np
import pytest

from src.curriculum.runner import EraResult
from src.curriculum.retention import (
    retention_probe,
    build_retention_map,
    forgetting_from_matrix,
    summarize_retention,
    matrix_to_json,
)

LADDER = ["w0", "w1", "w2"]
CHAMPIONS = ["c0", "c1", "c2"]  # cK = champion du stade K


def _deterministic_fn(mastery=0.8, decay=0.1):
    """Faux run_era_fn : compétence = mastery - decay * (stade - index_du_monde).

    Un cerveau au stade j re-testé sur le monde i (i<=j) a oublié `decay` par
    cran de distance (j - i). Déterministe -> matrice prévisible.
    """
    calls = []

    def run_era_fn(world_type, import_id, keep_mem):
        calls.append((world_type, import_id, keep_mem))
        stage = int(import_id[1:])             # "c2" -> 2
        world_idx = LADDER.index(world_type)
        comp = max(0.0, mastery - decay * (stage - world_idx))
        return EraResult(competence=comp, champion_agent_id="probe_champ")

    return run_era_fn, calls


# --- Probe ---

def test_probe_returns_competence_and_ignores_promotion():
    run_era_fn, calls = _deterministic_fn()
    comp = retention_probe(run_era_fn, "w0", "c0", keep_memory=False)
    assert comp == pytest.approx(0.8)
    assert calls == [("w0", "c0", 0)]


def test_probe_passes_keep_memory_flag():
    run_era_fn, calls = _deterministic_fn()
    retention_probe(run_era_fn, "w1", "c1", keep_memory=True)
    assert calls[0][2] == 1


# --- Matrice ---

def test_matrix_is_lower_triangular():
    run_era_fn, _ = _deterministic_fn()
    R = build_retention_map(run_era_fn, LADDER, CHAMPIONS)
    # Au-dessus de la diagonale -> NaN (un cerveau au stade j ne teste pas j+1)
    assert np.isnan(R[1, 0])
    assert np.isnan(R[2, 0])
    assert np.isnan(R[2, 1])
    # Diagonale = maîtrise pleine
    assert R[0, 0] == pytest.approx(0.8)
    assert R[1, 1] == pytest.approx(0.8)
    assert R[2, 2] == pytest.approx(0.8)


def test_matrix_captures_forgetting_below_diagonal():
    run_era_fn, _ = _deterministic_fn(mastery=0.8, decay=0.1)
    R = build_retention_map(run_era_fn, LADDER, CHAMPIONS)
    # monde w0 re-testé aux stades 0,1,2 -> 0.8, 0.7, 0.6
    assert R[0, 0] == pytest.approx(0.8)
    assert R[0, 1] == pytest.approx(0.7)
    assert R[0, 2] == pytest.approx(0.6)


def test_build_map_rejects_mismatched_lengths():
    run_era_fn, _ = _deterministic_fn()
    with pytest.raises(ValueError):
        build_retention_map(run_era_fn, LADDER, ["c0", "c1"])  # 2 != 3


def test_build_map_skips_none_champion():
    run_era_fn, _ = _deterministic_fn()
    R = build_retention_map(run_era_fn, LADDER, ["c0", None, "c2"])
    assert np.isnan(R[0, 1]) and np.isnan(R[1, 1])  # stade 1 sauté
    assert R[0, 0] == pytest.approx(0.8)
    assert R[0, 2] == pytest.approx(0.6)


# --- Oubli ---

def test_forgetting_scores():
    run_era_fn, _ = _deterministic_fn(mastery=0.8, decay=0.1)
    R = build_retention_map(run_era_fn, LADDER, CHAMPIONS)
    f = forgetting_from_matrix(R, LADDER)
    assert f["w0"]["forgetting"] == pytest.approx(0.2)   # 0.8 -> 0.6
    assert f["w1"]["forgetting"] == pytest.approx(0.1)   # 0.8 -> 0.7
    assert f["w2"]["forgetting"] == pytest.approx(0.0)   # rien après
    assert f["w0"]["retention_ratio"] == pytest.approx(0.75)


def test_backward_transfer_is_negative_forgetting():
    # decay négatif => pousser plus loin AMÉLIORE les mondes antérieurs.
    run_era_fn, _ = _deterministic_fn(mastery=0.6, decay=-0.1)
    R = build_retention_map(run_era_fn, LADDER, CHAMPIONS)
    f = forgetting_from_matrix(R, LADDER)
    assert f["w0"]["forgetting"] < 0           # transfert rétrograde
    assert f["w0"]["retention_ratio"] > 1.0


# --- Résumé JSON ---

def test_summarize_is_json_serializable():
    import json
    run_era_fn, _ = _deterministic_fn()
    summary = summarize_retention(run_era_fn, LADDER, CHAMPIONS)
    json.dumps(summary)  # ne doit pas lever
    assert summary["mean_forgetting"] == pytest.approx((0.2 + 0.1 + 0.0) / 3)
    # NaN au-dessus de la diagonale -> None dans le JSON
    assert summary["matrix"][1][0] is None
