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
    assert_predictor_measured_in_situ, assert_verdict_invariant_to_optimizer, declare_design)


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


# ------------------------------------------- assert_verdict_invariant_to_optimizer (classe E19) ----
# CALIBRATION DE LA GARDE — deux réponses CONNUES, toutes deux MESURÉES dans ce dépôt le 2026-09-01, et
# de signes opposés : un ARTEFACT d'hyperparamètre avéré (le nul doit être REFUSÉ) et un nul STRUCTUREL
# avéré (le nul doit être ÉPARGNÉ). Les chiffres sont EN DUR : ce sont les valeurs de vérité-terrain,
# pas des tirages — les tests sont donc PUREMENT NUMÉRIQUES (aucun entraînement, < 1 ms).

def test_optimizer_sweep_REFUSES_the_retain_compose_null():
    """RÉPONSE CONNUE n°1 — ARTEFACT MESURÉ : le verdict `RETENTION` d'EDR-RETAIN-COMPOSE.

    Configuration EXACTE qui a produit l'erreur réelle (contre-exemple gelé, patron `test_cost_guard`) :
    `run_retain_compose_diagnostic_probe`, episodes=600, n_agents=16, K=6, n=12, seule variable = `lr`.
    Bras testé = `learned` (2 `_step`), bras de référence = `oracle` (1 `_step`, rétention par fiat) :
    lr=0.02 -> 0.173 vs 0.971 (écart 0.798, verdict RETENTION) ; lr=0.002 -> 0.923 vs 0.945 (écart 0.022,
    verdict INCONCLUSIVE). Séparation par-seed TOTALE (0.897 > 0.192, 0/144). closure = 1 − 0.022/0.798 =
    **0.972** > 2/3 -> la garde REFUSE le nul. Cause racine : batch effectif 1 (`n_agents` n'est pas un
    minibatch, `src/agents/backend_torch.py:85-86`)."""
    mesure = {0.02: (0.173, 0.971), 0.002: (0.923, 0.945)}      # (learned, oracle) au MÊME lr
    with pytest.raises(PreflightError, match="artefact d'hyperparamètre"):
        assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.002),
                                              label="RETAIN-COMPOSE learned vs oracle")


def test_optimizer_sweep_SPARES_the_bilinear_structural_null():
    """RÉPONSE CONNUE n°2 — NUL STRUCTUREL MESURÉ : le substrat PLAIN ne peut PAS composer (q+key)%K.

    Spécificité : sans elle la garde serait un interrupteur qui refuse tous les négatifs. Bras testé =
    plain, bras de référence = bilinéaire (0.966), opérandes co-présents, episodes=600, 4 seeds :
    lr=0.02 -> 0.3141 (écart 0.652) ; lr=0.1 -> 0.3719 (écart 0.594). closure = 1 − 0.594/0.652 =
    **0.089** << 2/3 -> la garde ÉPARGNE ce nul. Il est structurel au sens FORT : le plafond exact du
    plain en forme close vaut 0.3889 (8 restarts ; contrôle positif du même optimiseur sur une table libre
    non séparable : 1.000), et baisser le pas DÉGRADE vers le hasard (0.1906 à lr=0.002, 1/K = 0.1667).

    CONTRASTE qui justifie le design — un critère de SEUIL ABSOLU se serait trompé ICI : à lr=0.1 le plain
    (0.3719) franchit la barre du dépôt 1/K+0.15 = 0.3167, alors qu'il est PROUVABLEMENT incapable de
    composer. La barre est 0.072 SOUS le plafond structurel. Seul l'ÉCART AU BRAS DE RÉFÉRENCE sépare les
    deux réponses connues.

    ⚠️ PROVENANCE : ces chiffres de spécificité viennent d'UNE seule passe (4 seeds), NON RÉPLIQUÉE — là
    où le cas artefact ci-dessus est établi à n=12. Ce test gèle donc la DIRECTION (un nul structurel ne
    referme pas son écart au bras de référence), pas la troisième décimale de la closure."""
    mesure = {0.02: (0.3141, 0.966), 0.1: (0.3719, 0.966)}      # (plain, bilinéaire) au MÊME lr
    assert assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.1),
                                                 label="BILINEAR plain vs bilinéaire") is True
    bar = 1 / 6 + 0.15
    assert mesure[0.1][0] > bar, "prémisse du contraste : un seuil absolu aurait flagué ce VRAI négatif"


def test_optimizer_sweep_rejects_a_single_step_and_ignores_a_nonexistent_null():
    """Deux bornes du domaine. (1) UN SEUL pas ne peut RIEN dire : c'est exactement la situation qui a
    produit E19 (un seul point d'hyperparamètre, jamais balayé) -> refus explicite plutôt que vert vide
    (classe E4 : une vérification qui ne peut pas échouer). (2) Si le bras testé n'est SOUS sa référence à
    AUCUN pas, il n'y a pas de nul de capacité à défendre -> la garde passe sans rien inventer."""
    with pytest.raises(PreflightError, match="DEUX pas DISTINCTS"):
        assert_verdict_invariant_to_optimizer(lambda lr: (0.173, 0.971), lrs=(0.02, 0.02))
    pas_de_nul = {0.02: (0.95, 0.94), 0.002: (0.97, 0.93)}
    assert assert_verdict_invariant_to_optimizer(lambda lr: pas_de_nul[lr], lrs=(0.02, 0.002)) is True


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
