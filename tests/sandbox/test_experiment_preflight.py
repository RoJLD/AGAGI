"""Tests du pré-vol expérimental. Chaque test rejoue une erreur RÉELLE de la session WARM-005→009 :
si un test échoue, c'est que le garde-fou correspondant ne protège plus contre l'erreur qu'il encode."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.experiment_preflight import (  # noqa: E402
    PreflightError, ReferenceCollapsedError, assert_ablation_changes_something, assert_positive_control,
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

    # POSITIF APPARIÉ (P2.21, LE PLUS IMPORTANT) — le MÊME cas, mais avec `reference_floor` armé : la
    # référence oracle (0.971 puis 0.945) est vivante aux DEUX pas -> `reference_floor` ne doit RIEN
    # changer, la garde doit continuer à lever EXACTEMENT « artefact d'hyperparamètre », PAS
    # `ReferenceCollapsedError`. Sans ce contrôle on remplace une garde trop laxiste par une garde trop
    # stricte (P2.21, même défaut, signe inversé) : `reference_floor` doit épargner une référence VIVANTE.
    with pytest.raises(PreflightError, match="artefact d'hyperparamètre"):
        assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.002),
                                              reference_floor=1 / 6 + 0.15,
                                              label="RETAIN-COMPOSE learned vs oracle (floor armé)")


def test_optimizer_sweep_returns_INCONCLUSIVE_when_the_REFERENCE_collapses():
    """CONTRE-EXEMPLE GELÉ (P2.21) — motif E3 DANS la garde E19 elle-même, constaté EN ACTE sur
    EDR-DELAYED-COORD (2026-09-01) : la garde AVANT ce correctif refusait ce nul comme « artefact
    d'hyperparamètre », alors que le bras TESTÉ n'a jamais bougé — c'est la RÉFÉRENCE qui s'est effondrée.

    Configuration EXACTE qui a produit l'erreur réelle (patron `test_cost_guard`) : bras testé = appris
    (émission Lewis apprise), bras de référence = canal ORACLE (`argmax` du référent perçu), même sonde,
    même seed. `lr=0.02` : testé 0.141, référence 0.436 (écart 0.295) ; `lr=0.08` : testé 0.203, référence
    0.194 (écart −0.009). closure = 1 − (−0.009/0.295) = 103.1 % > 2/3 seuil.

    Le bras testé reste dans **[0.141, 0.203]** tout du long — exactement la bande **0.164–0.206** que le
    crible PUBLIÉ de ce même record mesure pour RETAIN/PRESENT au plancher documenté `1/K = 0.167` (K=6)
    dans `docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md`. C'est la
    RÉFÉRENCE (canal oracle) qui s'effondre : 0.436 (vivant) -> 0.194 (au plancher) à `lr=0.08`. Chiffres
    du couple appris/oracle : notes de session
    `.superpowers/sdd/2026-09-01-delayed-lewis-retention-edge/task-2-report.md` (mêmes seed et `_params`
    que le crible publié ; fichier de travail non committé — le record publié acquitte le motif dans sa
    section « Ce que ça débloque » sans réimprimer le balayage).

    `reference_floor = 1/6 + 0.15` (même barre, même K=6, que le contrôle de spécificité BILINEAR) :
    0.194 <= floor à `lr=0.08` -> `ReferenceCollapsedError`, PAS `artefact d'hyperparamètre`. Sans
    `reference_floor`, le comportement D'AVANT ce correctif est préservé EXACTEMENT (aucune régression
    silencieuse sur les appelants qui n'ont pas encore adopté l'argument) : la garde continue de lever
    « artefact d'hyperparamètre » sur ce même cas."""
    mesure = {0.02: (0.141, 0.436), 0.08: (0.203, 0.194)}     # (appris, oracle) au MÊME lr

    # Sans reference_floor (comportement HISTORIQUE inchangé, non corrigé) : tire, et pour la MAUVAISE
    # raison — documente le bug tel qu'il existait, pour qu'un futur appelant qui oublie l'argument
    # retrouve le même signal (loud), pas un silence.
    with pytest.raises(PreflightError, match="artefact d'hyperparamètre"):
        assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.08),
                                              label="DELAYED-COORD appris vs oracle")

    # Avec reference_floor armé (LE CORRECTIF) : verdict DISTINCT, ni refus muet dans l'ancienne branche,
    # ni pass silencieux -- ReferenceCollapsedError EST une PreflightError (héritage), donc un appelant
    # qui catch encore `except PreflightError:` reste protégé sans rien changer.
    with pytest.raises(ReferenceCollapsedError, match="INCONCLUSIVE_REFERENCE_COLLAPSED"):
        assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.08),
                                              reference_floor=1 / 6 + 0.15,
                                              label="DELAYED-COORD appris vs oracle")
    try:
        assert_verdict_invariant_to_optimizer(lambda lr: mesure[lr], lrs=(0.02, 0.08),
                                              reference_floor=1 / 6 + 0.15,
                                              label="DELAYED-COORD appris vs oracle")
    except PreflightError as e:
        assert isinstance(e, ReferenceCollapsedError), (
            "un `except PreflightError` générique doit toujours l'attraper (sous-classe)")
        assert "artefact d'hyperparamètre" not in str(e), (
            "le verdict DOIT être distinct du message d'artefact -- sinon rien ne les sépare")


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
    # (3) reference_floor (P2.21) ne doit RIEN changer à cette branche « pas de nul à défendre » : la
    # référence 0.94/0.93 est SOUS un plancher volontairement haut (0.99), et pourtant aucune exception --
    # `g_max <= 0.0` court-circuite AVANT toute lecture du plancher, exactement comme sans l'argument.
    assert assert_verdict_invariant_to_optimizer(lambda lr: pas_de_nul[lr], lrs=(0.02, 0.002),
                                                 reference_floor=0.99) is True


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


def test_calibration_ratchet_REFUSES_a_bare_declaration_on_an_ambiguous_name(tmp_path, monkeypatch):
    """TROISIÈME angle mort du cliquet, mesuré le 2026-09-01 — après le motif de nommage (2026-07-21)
    et le périmètre de scan (même jour). L'heuristique est faillible sur TROIS axes : ce qu'elle
    cherche, OÙ elle le cherche, et **comment elle IDENTIFIE ce qu'elle trouve**.

    `scan_instruments` indexe par NOM seul et garde le premier fichier (`setdefault`) : 6 noms sont
    définis dans plusieurs fichiers, donc **8 définitions étaient invisibles** (101 rapportés, 109
    réels). Le danger n'est pas le sous-comptage mais le FAUX VERT : déclarer calibré `run_probe`
    (3 fichiers) aurait verdi DEUX instruments jamais testés — classe E4, dans l'outil écrit pour
    l'empêcher, pour la troisième fois.

    Vérifié au moment du correctif : aucune collision n'était déclarée calibrée, donc aucun faux vert
    n'existait. Le risque était PROSPECTIF — c'est exactement le moment où il faut le fermer."""
    import tools.check_instrument_calibration as C

    collisions = C.scan_collisions()
    assert collisions, "aucune collision détectée -> le détecteur est cassé, il ne peut plus rien voir"
    ambigu = sorted(collisions)[0]
    assert len(collisions[ambigu]) >= 2

    faux = tmp_path / "test_calib.py"
    monkeypatch.setattr(C, "_CALIB_TESTS", str(faux))

    # ⚠️ LE contre-exemple : une déclaration NUE sur un nom ambigu ne doit RIEN valider.
    faux.write_text(f'CALIBRATED = {{\n    "{ambigu}": ["*"],\n}}\n', encoding="utf-8")
    assert ambigu not in C.scan_calibrated(), (
        f"« {ambigu} » est défini dans {len(collisions[ambigu])} fichiers ; une déclaration nue "
        f"validerait des homonymes JAMAIS testés")

    # SPÉCIFICITÉ 1 — qualifiée « fichier::fonction », elle doit être acceptée : sans ça, les 6 noms
    # en collision deviendraient incalibrables et la garde bloquerait le travail au lieu de le guider.
    faux.write_text(f'CALIBRATED = {{\n    "{collisions[ambigu][0]}::{ambigu}": ["*"],\n}}\n',
                    encoding="utf-8")
    assert ambigu in C.scan_calibrated(), "une déclaration QUALIFIÉE doit être acceptée"

    # SPÉCIFICITÉ 2 — un nom NON ambigu reste déclarable nu (aucune régression sur les 36 existants).
    non_ambigu = next(n for n in C.scan_instruments() if n not in collisions)
    faux.write_text(f'CALIBRATED = {{\n    "{non_ambigu}": ["*"],\n}}\n', encoding="utf-8")
    assert non_ambigu in C.scan_calibrated(), (
        "un nom sans homonyme doit rester déclarable simplement — sinon la correction casse tout")


def test_calibration_gate_blocks_only_what_THIS_commit_touches(tmp_path, monkeypatch, capsys):
    """PORTÉE DU BLOCAGE — l'arbre est PARTAGÉ entre sessions parallèles (CLAUDE.md).

    Mesuré le 2026-09-01 : un instrument NON SUIVI écrit par une autre session
    (`run_delayed_coordination_demand_probe`) bloquait un commit sans aucun rapport, parce que la porte
    scannait l'arbre entier. Les deux échappatoires étaient mauvaises — `--no-verify` contourne la
    garde, et `--update-baseline` déclarerait « légataire » un instrument né le jour même, donc le
    laisserait passer EN SILENCE. La porte sœur (`check_record_links.py`) avait déjà résolu ça.

    Ce test gèle les DEUX sens : hors portée -> on passe (mais l'instrument reste VISIBLE dans le
    rapport) ; dans la portée -> on bloque. Sans le second, la porte ne garderait plus rien."""
    import tools.check_instrument_calibration as C

    faux_base = tmp_path / "baseline.json"
    faux_base.write_text('{"uncalibrated": []}', encoding="utf-8")
    monkeypatch.setattr(C, "_BASELINE", str(faux_base))
    monkeypatch.setattr(C, "scan_instruments",
                        lambda: {"verdict_a_moi": "tools/a_moi.py",
                                 "verdict_d_autrui": "tools/d_autrui.py"})
    monkeypatch.setattr(C, "scan_calibrated", lambda: set())
    monkeypatch.setattr(C, "scan_collisions", lambda: {})
    monkeypatch.setattr(C, "scan_declared_branches", lambda: {})

    # HORS PORTÉE : je ne stage que mon fichier, déjà calibré côté baseline -> le leur ne doit pas bloquer.
    faux_base.write_text('{"uncalibrated": ["verdict_a_moi"]}', encoding="utf-8")
    assert C.main(["--only", "tools/a_moi.py"]) == 0
    sortie = capsys.readouterr().out
    assert "HORS PORTÉE" in sortie and "verdict_d_autrui" in sortie, (
        "l'instrument d'autrui doit rester VISIBLE : le scoper ne veut pas dire le cacher")

    # DANS LA PORTÉE : je stage un fichier qui définit un instrument non calibré -> ça DOIT bloquer.
    faux_base.write_text('{"uncalibrated": []}', encoding="utf-8")
    assert C.main(["--only", "tools/a_moi.py"]) == 1, (
        "stager un instrument non calibré doit TOUJOURS bloquer — sinon la porte ne garde plus rien")

    # SANS --only : comportement historique, l'arbre entier bloque.
    assert C.main([]) == 1


# ------------------------------------------- assert_n_per_arm (classe E15, promue 2026-09-02) ----

def test_n_per_arm_catches_the_EDR095_population_shift():
    """⚠️ CONTRE-EXEMPLE GELÉ aux chiffres RÉELS d'EDR-095 : le rêve forcé multipliait `n_lived` par
    13-16 entre bras, et la « chute de 55 % » de la médiane comparait deux populations différentes.
    Sur la cohorte fondatrice appariée, l'effet était ABSENT."""
    from tools.experiment_preflight import PreflightError, assert_n_per_arm
    with pytest.raises(PreflightError, match="INCOMPARABLES"):
        assert_n_per_arm([50.0] * 12, [22.0] * 160, label="dream on/off")


def test_n_per_arm_SPARES_comparable_populations():
    """⚠️ SPÉCIFICITÉ : des cohortes appariées (n égaux) et un déséquilibre modéré sous le seuil
    passent — sinon la garde interdirait toute comparaison réelle."""
    from tools.experiment_preflight import assert_n_per_arm
    assert assert_n_per_arm([1.0] * 12, [2.0] * 12)
    assert assert_n_per_arm([1.0] * 12, [2.0] * 16)          # 1.33x < 1.5x


def test_n_per_arm_refuses_an_empty_arm():
    """Un bras vide n'a pas de médiane à comparer : refus, pas une sentinelle."""
    from tools.experiment_preflight import PreflightError, assert_n_per_arm
    with pytest.raises(PreflightError, match="VIDE"):
        assert_n_per_arm([], [1.0] * 12)
