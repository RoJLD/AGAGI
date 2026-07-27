"""Tests du pré-vol expérimental. Chaque test rejoue une erreur RÉELLE de la session WARM-005→009 :
si un test échoue, c'est que le garde-fou correspondant ne protège plus contre l'erreur qu'il encode."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.experiment_preflight import (  # noqa: E402
    PreflightError, assert_ablation_changes_something, assert_positive_control,
    assert_not_degenerate, assert_selection_nonempty, assert_no_aliasing,
    assert_predictor_measured_in_situ, declare_design)


def test_tautological_control_is_rejected():
    """WARM-007 : 6/8 agents rendaient des tableaux intact/ablé BIT-IDENTIQUES, comptés comme contrôle."""
    reel = [35.0, 33.0, 41.0]
    with pytest.raises(PreflightError, match="tautologique|IDENTIQUES"):
        assert_ablation_changes_something(reel, list(reel))
    assert assert_ablation_changes_something(reel, [70.0, 66.0, 82.0]) is True


def test_positive_control_catches_incapable_arm():
    """WARM-009 : bras censé montrer que grabber PAIE, dans un monde sans aucun item `Fruit`."""
    with pytest.raises(PreflightError, match="ÉCHOUE"):
        assert_positive_control(lambda: 7.0, expect_better_than=7.0, label="grab paie")
    assert assert_positive_control(lambda: 42.0, expect_better_than=7.0) is True


def test_degenerate_metric_is_rejected_on_floor_and_ceiling():
    """WARM-009 : 24 génomes tous à 6.0-7.2 ticks (plancher). WARM-008 : 32/48 déjà à move_acc=1.000."""
    plancher = [7.0] * 24
    with pytest.raises(PreflightError, match="DÉGÉNÉRÉE"):
        assert_not_degenerate(plancher, label="survie")
    plafond = [1.0] * 32
    with pytest.raises(PreflightError, match="DÉGÉNÉRÉE"):
        assert_not_degenerate(plafond, label="move_acc")
    assert assert_not_degenerate([6.0, 124.0, 35.0]) is True


def test_empty_selection_is_rejected():
    """Cette session, sur ma propre vérification : `pytest -k` a désélectionné 1034 tests -> « 0 échec »."""
    with pytest.raises(PreflightError, match="VIDE"):
        assert_selection_nonempty(0, label="tests torch")
    assert assert_selection_nonempty(28) is True


def test_aliasing_is_detected_on_a_real_view():
    """WARM-007 (bug réel) : `forward` renvoyait une VUE de H -> écrire dans les logits mutait l'état."""
    H = np.zeros((4, 172), dtype=np.float32)
    vue = H[:, 64:172]                                    # exactement le motif du backend
    assert np.shares_memory(vue, H)
    with pytest.raises(PreflightError, match="ALIASÉE"):
        assert_no_aliasing(vue, H, label="logits")
    assert assert_no_aliasing(vue.copy(), H) is True
    assert assert_no_aliasing("pas un array", H) is True   # types non-array : tolérés


def test_predictor_context_mismatch_is_rejected():
    """WARM-007 : prédicteur mesuré sur la trajectoire ORACLE, intervention opérant IN-WORLD."""
    with pytest.raises(PreflightError, match="in situ|opère"):
        assert_predictor_measured_in_situ("oracle_trajectory", "in_world")
    assert assert_predictor_measured_in_situ("in_world", "in_world") is True


def test_declare_design_surfaces_inferred_links():
    """WARM-008 : le maillon final était INFÉRÉ pour économiser 7 h ; mesuré NUL par la revue."""
    d = declare_design(question="aux_off améliore-t-il la survie ?",
                       replication_unit="seed", n_independent=4,
                       links={"canal annulé": "measured", "gain de survie": "inferred"})
    assert d["inferred_links"] == ["gain de survie"]
    assert "signe" in d["warning"] and "amplitude" in d["warning"]
    propre = declare_design(question="q", replication_unit="ère", n_independent=12,
                            links={"tout": "measured"})
    assert propre["warning"] is None


def test_declare_design_rejects_malformed_input():
    with pytest.raises(PreflightError, match="invalides"):
        declare_design("q", "seed", 4, {"x": "peut-être"})
    with pytest.raises(PreflightError, match="n_independent"):
        declare_design("q", "seed", 0, {"x": "measured"})


def test_calibration_ratchet_requires_explicit_declaration(tmp_path, monkeypatch):
    """RÉGRESSION d'un bug RÉEL de mon propre outil (2026-07-21, trouvé par workflow adversarial).

    `scan_calibrated()` comptait un instrument calibré dès que son NOM apparaissait en SUBSTRING dans le
    fichier de tests. `_torch_survival_eras` passait donc pour calibré alors que seule sa branche
    `grab_off` l'était — la branche `perception`, qui porte les ratios publiés de WARM-001/003, n'avait
    aucun cas. Classe E4 (une vérification qui ne peut pas échouer) DANS l'outil écrit pour l'empêcher.
    """
    import tools.check_instrument_calibration as C

    faux = tmp_path / "test_calib.py"
    # Le nom apparaît partout, mais AUCUN dict CALIBRATED : ne doit rien valider.
    faux.write_text("# ablation_verdict _torch_survival_eras compute_ab_verdict\n"
                    "def test_rien(): pass\n", encoding="utf-8")
    monkeypatch.setattr(C, "_CALIB_TESTS", str(faux))
    assert C.scan_calibrated() == set(), "substring accepté -> faux vert (le bug est revenu)"

    # Déclaration explicite : seul l'instrument déclaré compte, et ses branches sont visibles.
    faux.write_text('CALIBRATED = {\n    "_torch_survival_eras": ["grab_off"],\n}\n', encoding="utf-8")
    assert C.scan_calibrated() == {"_torch_survival_eras"}
    assert C.scan_declared_branches()["_torch_survival_eras"] == ["grab_off"]

    # Déclaration vide = non calibré (on ne valide pas une liste de branches vide).
    faux.write_text('CALIBRATED = {\n    "_torch_survival_eras": [],\n}\n', encoding="utf-8")
    assert C.scan_calibrated() == set()

    # Déclaration périmée (instrument inexistant) : ignorée, jamais de faux vert.
    faux.write_text('CALIBRATED = {\n    "instrument_qui_nexiste_pas": ["*"],\n}\n', encoding="utf-8")
    assert C.scan_calibrated() == set()
