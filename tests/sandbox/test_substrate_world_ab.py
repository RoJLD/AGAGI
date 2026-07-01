"""Tests de l'A/B de learnabilité IN-WORLD (ADR-003, Axe 1, aligné EDR-129).

Parties PURES uniquement (verdict depuis médianes de survie + signatures). Le smoke
biosphère réel (measure_survival qui tourne env.step) est différé à la fenêtre de run
KuzuDB calme — non committé ici (anti-contention machine multi-sessions).
"""
import sys, os, inspect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.substrate_world_ab import _ab_from_meds, measure_survival, compare_backends, compare_arms


def test_ab_from_meds_gradient_wins():
    r = _ab_from_meds([10, 12, 11], [30, 28, 33])  # torch >> legacy
    assert r["verdict"] == "GRADIENT_GAGNE"
    assert len(r["per_seed"]) == 3
    assert r["per_seed"][0]["diff"] == 20.0


def test_ab_from_meds_hebbien_wins():
    assert _ab_from_meds([30, 28, 32], [10, 12, 11])["verdict"] == "HEBBIEN_GAGNE"


def test_ab_from_meds_neutral_within_band():
    # diffs [0, +1, -1] : médiane 0 dans la bande (2 ticks) -> NEUTRE
    assert _ab_from_meds([20, 20, 20], [20, 21, 19])["verdict"] == "NEUTRE"


def test_ab_from_meds_truncates_to_common_length():
    assert len(_ab_from_meds([1, 2, 3, 4], [5, 6])["per_seed"]) == 2


def test_measure_survival_accepts_backend_cls_and_genome():
    p = inspect.signature(measure_survival).parameters
    assert "backend_cls" in p and "genome" in p and "world_key" in p


def test_compare_backends_signature():
    p = inspect.signature(compare_backends).parameters
    assert "world_key" in p and "genome" in p and "band" in p


def test_compare_arms_signature():
    # bras à 3 (EDR-134 suite) : legacy-full / legacy-core / torch-core.
    p = inspect.signature(compare_arms).parameters
    assert "world_key" in p and "genome" in p and "band" in p
