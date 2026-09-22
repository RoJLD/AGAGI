"""
tests/sandbox/test_harness_seal_r1.py — tests de la fonction PURE `build_rule_r1` (tâche 10).

Cinq tests : les trois du brief (second lr de B choisi parmi les alternatives mesurées au smoke ;
refus si aucune alternative ne franchit la barre ; discrimination exhaustive + DV backtickée +
prédictions chiffrées) et deux ajoutés par les décisions contrôleur (1) `matched_sham` est LU du
registre `PIECES`, jamais typé en dur ; (2) chaque sous-règle de cellule passe `validate_rule` seule,
sans lever -- c'est ce que `run_harness_cell` appellera EN TÊTE avant tout build.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_pieces import PIECES  # noqa: E402
from src.seed_ai.harness_verdict import BRANCHES, validate_rule  # noqa: E402
from tools.harness.seal_r1 import build_rule_r1  # noqa: E402


def _smoke(b_med=None):
    b_med = b_med or {"0.002": 0.92, "0.001": 0.88, "0.0005": 0.70}
    return {"A": {"0.02": {"0": 0.93, "1": 0.92, "2": 0.94}}, "A_ref": {"0": 0.17, "1": 0.20, "2": 0.18},
            "B": {lr: {"0": m, "1": m, "2": m} for lr, m in b_med.items()}, "B_ref": {"0": 0.17, "1": 0.19, "2": 0.18},
            "unit_s": {"A": 3.5, "Aprime": 1.8, "B": 7.0}}


def test_second_lr_of_B_is_the_best_measured_alternative_above_the_bar():
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["B"]["sweep"] == [{"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"},
                                              {"lr": 0.001, "rank": 16, "n_classes": 6, "credit": "supervised"}]


def test_seal_refuses_when_no_alternative_lr_clears_the_bar():
    with pytest.raises(ValueError, match="aucun second pas"):
        build_rule_r1(_smoke({"0.002": 0.92, "0.001": 0.20, "0.0005": 0.19}))


def test_rule_has_exhaustive_discrimination_backticked_dv_and_predictions():
    rule = build_rule_r1(_smoke())
    assert set(rule["discrimination"]) == set(BRANCHES) and "AUTRE" in rule["discrimination"]
    assert "`hits`" in rule["dv_primaire"] and "`dose.updates`" in rule["dv_primaire"]
    assert rule["predictions_chiffrees_AVANT_le_run"]["A"].startswith("PIECE_PARTIAL")
    assert rule["predictions_chiffrees_AVANT_le_run"]["B"].startswith("DEMANDED_ACQUIRED_NECESSARY")
    assert rule["budget_s"] == pytest.approx(3.0 * (3.5 + 1.8 + 7.0) * 12 * 5, rel=0.01)


def test_matched_sham_is_read_from_the_pieces_registry_never_typed():
    """Décision contrôleur (1) : `matched_sham` de chaque cellule vient de `PIECES[piece].matched_sham`,
    jamais d'une valeur écrite en dur dans `seal_r1.py` -- c'est ce que lit `_necessity` (rule.get
    ("matched_sham")) pour publier `sham: DECLARED`/`PARAMS_NON_APPARIES`."""
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["A"]["matched_sham"] == PIECES["bilinear"].matched_sham
    assert rule["cellules"]["Aprime"]["matched_sham"] == PIECES["bilinear"].matched_sham
    assert rule["cellules"]["B"]["matched_sham"] == PIECES["recurrent_state"].matched_sham


def test_each_cell_sub_rule_passes_validate_rule_alone():
    """Décision contrôleur (2) : chaque sous-règle de cellule (`rule["cellules"][c]`) doit passer
    `validate_rule` seule -- c'est exactement ce que `run_harness_cell` appelle EN TÊTE, avant tout
    build, une fois `rule_path=["cellules", c]` descendu dans la règle scellée entière."""
    rule = build_rule_r1(_smoke())
    for c in ("A", "Aprime", "B"):
        validate_rule(rule["cellules"][c])          # ne doit PAS lever
