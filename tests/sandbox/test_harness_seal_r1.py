"""
tests/sandbox/test_harness_seal_r1.py — tests de la fonction PURE `build_rule_r1` (tâche 10, fix round 1/5).

HARNESS-R1 (sans -bis) n'avait encore lu AUCUNE cellule quand la revue a trouvé 8 défauts Important,
dont 4 touchant le CONTENU scellé (E2/E5/E8/E23) : la voie légitime est un `-bis` scellé AVANT toute
cellule, citant R1 et la raison. `build_rule_r1` scelle donc directement HARNESS-R1-bis (cf.
`tools/harness/seal_r1.py::main`) ; ces tests couvrent les propriétés PURES de la fonction.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_pieces import PIECES  # noqa: E402
from src.seed_ai.harness_verdict import BRANCHES, validate_rule  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.seal_r1 import B_SWEEP0_LR, build_rule_r1  # noqa: E402
from tools.plain_substrate_ceiling import PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE  # noqa: E402


def _smoke(b_med=None):
    b_med = b_med or {"0.002": 0.92, "0.001": 0.88, "0.0005": 0.70}
    return {
        "A": {"0.02": {"0": 0.93, "1": 0.92, "2": 0.94}},
        "A_ref": {"0": 0.17, "1": 0.20, "2": 0.18},
        "Aprime_ref": {"0": 0.20, "1": 0.18, "2": 0.19},
        "B": {lr: {"0": m, "1": m, "2": m} for lr, m in b_med.items()},
        "B_ref": {"0": 0.17, "1": 0.19, "2": 0.18},
        "noise": {"A": {"0": 1.00, "1": 0.99, "2": 1.03},
                  "Aprime": {"0": 1.0, "1": 1.0, "2": 1.0},
                  "B": {"0": 0.99, "1": 0.995, "2": 0.997}},
        "unit_s": {"A": 6.4, "Aprime": 3.3, "B": 17.1},          # bras full_eval (fix 2)
        "unit_s_nude": {"A": 5.1, "Aprime": 2.5, "B": 16.8},
    }


def test_second_lr_of_B_is_the_best_measured_alternative_above_the_bar():
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["B"]["sweep"] == [{"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"},
                                              {"lr": 0.001, "rank": 16, "n_classes": 6, "credit": "supervised"}]


def test_seal_refuses_when_no_alternative_lr_clears_the_bar():
    with pytest.raises(ValueError, match="aucun second pas"):
        build_rule_r1(_smoke({"0.002": 0.92, "0.001": 0.20, "0.0005": 0.19}))


def test_tie_break_picks_the_lr_closest_to_sweep0_lr():
    """Fix (10) : à médiane ÉGALE entre les deux candidats, le bris d'égalité choisit le lr le plus
    proche de `B_SWEEP0_LR` (0.001 est à 0.001 de 0.002 ; 0.0005 est à 0.0015 -- 0.001 gagne)."""
    rule = build_rule_r1(_smoke({"0.002": 0.92, "0.001": 0.80, "0.0005": 0.80}))
    assert rule["cellules"]["B"]["sweep"][1]["lr"] == pytest.approx(0.001)
    assert rule["cellules"]["B"]["sweep"][1]["lr"] != B_SWEEP0_LR


def test_rule_has_exhaustive_DISTINCT_discrimination_backticked_dv_and_predictions():
    rule = build_rule_r1(_smoke())
    disc = rule["discrimination"]
    assert set(disc) == set(BRANCHES) and "AUTRE" in disc
    # une déclaration dont les 15 valeurs sont IDENTIQUES ne discrimine rien (le défaut que la revue a
    # trouvé dans R1) : chaque branche doit porter une phrase propre.
    assert len(set(disc.values())) == len(BRANCHES)
    assert "`hits`" in rule["dv_primaire"] and "`dose.updates`" in rule["dv_primaire"]
    assert rule["predictions_chiffrees_AVANT_le_run"]["A"].startswith("PIECE_PARTIAL")
    assert rule["predictions_chiffrees_AVANT_le_run"]["Aprime"].startswith("PIECE_NOT_NECESSARY")
    assert rule["predictions_chiffrees_AVANT_le_run"]["B"].startswith("DEMANDED_ACQUIRED_NECESSARY")


def test_budget_is_per_cell_and_family_is_their_sum():
    """Fix (1) : chaque cellule porte son propre `budget_s` (3 x unit_s[cellule] x 12 x 5, l'unite
    full_eval) ; `budget_family_s` en est la somme -- jamais un total unique calcule sur une somme
    d'unites qui melangeait des grandeurs non comparables (R1)."""
    smoke = _smoke()
    rule = build_rule_r1(smoke)
    for c in ("A", "Aprime", "B"):
        expected = 3.0 * smoke["unit_s"][c] * 12 * 5
        assert rule["cellules"][c]["budget_s"] == pytest.approx(expected, rel=1e-9)
    assert rule["budget_family_s"] == pytest.approx(
        sum(rule["cellules"][c]["budget_s"] for c in ("A", "Aprime", "B")), rel=1e-9)


def test_matched_sham_is_read_from_the_pieces_registry_never_typed():
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["A"]["matched_sham"] == PIECES["bilinear"].matched_sham
    assert rule["cellules"]["Aprime"]["matched_sham"] == PIECES["bilinear"].matched_sham
    assert rule["cellules"]["B"]["matched_sham"] == PIECES["recurrent_state"].matched_sham


def test_each_cell_sub_rule_passes_validate_rule_alone():
    rule = build_rule_r1(_smoke())
    for c in ("A", "Aprime", "B"):
        validate_rule(rule["cellules"][c])          # ne doit PAS lever


def test_each_cell_sweep_matches_connectome_learner_sweep():
    """Fix (8) : le sweep de chaque cellule est EXACTEMENT ce que produirait
    `ConnectomeLearner(lrs=(lr0, lr1), n_classes=nc).sweep()` -- `sweep()` ne construit rien (pas de
    torch, pas de monde), donc ce test reste un test PUR."""
    rule = build_rule_r1(_smoke())
    for c, nc in (("A", None), ("Aprime", None), ("B", 6)):
        lrs = tuple(h["lr"] for h in rule["cellules"][c]["sweep"])
        expected = ConnectomeLearner(lrs=lrs, n_classes=nc).sweep()
        assert rule["cellules"][c]["sweep"] == expected


def test_incapable_ceiling_of_A_matches_plain_substrate_ceiling_module():
    """Fix (9) : le plafond de l'incapable est IMPORTE de `tools.plain_substrate_ceiling` (comme
    `CompositionTask`), jamais retapé en dur -- un plafond copié à la main peut diverger silencieusement
    du module qui fait autorité."""
    rule = build_rule_r1(_smoke())
    ceil = rule["cellules"]["A"]["incapable_ceiling"]
    assert ceil["value"] == pytest.approx(float(PLAIN_COMPOSITION_CEILING))
    assert ceil["provenance"] == PLAIN_COMPOSITION_PROVENANCE + " MINORANT, jamais PROUVE."
    assert rule["cellules"]["Aprime"]["incapable_ceiling"] is None
    assert rule["cellules"]["B"]["incapable_ceiling"] is None


def test_control_family_is_declared_per_cell_and_the_family_total_is_twenty():
    """Fix (5) : R1 déclarait `cells=6` pour la famille ENTIÈRE (sous-déclaration E23) ; chaque cellule
    doit porter SA PROPRE famille (n_ablations x len(sweep) : A=3x2=6, A'=3x2=6, B=4x2=8), et le total
    au niveau famille (20) doit être leur somme, pas un chiffre indépendant."""
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["A"]["control_family"]["cells"] == 6
    assert rule["cellules"]["Aprime"]["control_family"]["cells"] == 6
    assert rule["cellules"]["B"]["control_family"]["cells"] == 8
    assert rule["design"]["control_family"]["cells"] == 20


def test_each_cell_carries_n_agents_and_eval_batches():
    """Fix (6) : `n_agents`/`eval_batches` sont désormais scellés à côté d'`episodes` dans chaque
    cellule -- un lecteur du sceau ne devrait pas avoir à deviner le régime d'éval."""
    rule = build_rule_r1(_smoke())
    for c in ("A", "Aprime", "B"):
        assert rule["cellules"][c]["n_agents"] == 16
        assert rule["cellules"][c]["eval_batches"] == 40


def test_each_cell_names_its_expected_branch_and_negative_reading():
    """Fix (4), E2 : un instrument qui ne peut pas rater ne prouve rien -- la lecture du RATAGE (pas
    seulement du succès espéré) doit être écrite AVANT le run."""
    rule = build_rule_r1(_smoke())
    expected = {"A": "PIECE_PARTIAL", "Aprime": "PIECE_NOT_NECESSARY", "B": "DEMANDED_ACQUIRED_NECESSARY"}
    for c, branch in expected.items():
        issues = rule["cellules"][c]["issues"]
        assert issues["attendue"] == branch and branch in BRANCHES
        assert isinstance(issues["sinon"], str) and len(issues["sinon"]) > 10


def test_rule_declares_what_it_replaces_and_why():
    rule = build_rule_r1(_smoke())
    assert rule["remplace"] == "HARNESS-R1"
    assert isinstance(rule["raison_bis"], str) and "E2" in rule["raison_bis"] and "E23" in rule["raison_bis"]


def test_design_drops_the_human_facing_warning_but_keeps_the_rest():
    """Fix (14) : `warning` (texte d'aide au lecteur humain) n'a rien à faire dans un dict SCELLÉ --
    retiré, mais `control_family`/`links`/`n_independent`/`question` restent."""
    rule = build_rule_r1(_smoke())
    assert "warning" not in rule["design"]
    for k in ("control_family", "links", "n_independent", "question", "inferred_links", "inferred_reason"):
        assert k in rule["design"]
