# -*- coding: utf-8 -*-
"""Calibration de `tools/evo_runs/s2_subject_variance.py` — l'instrument de verdict est PUR, donc
chaque branche se confronte à une réponse connue sans construire un seul monde.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule. `map_fn` est injectée, et les
génomes sont des sentinelles — si une garde tombe, le test le dit sans rien charger.

Ce que ces cas protègent en priorité, c'est le **bras de réplication** : sans lui, le critère de
lecture d'origine (« ≥ 2 sujets divergent ») pouvait être franchi par le seul bruit de mesure sur
21 paires — classe E23, exactement le défaut mesuré sur EVO-011 (0,216 de fausse alarme).
"""
import pytest

from tools.evo_runs.s2_subject_variance import (ROLE_NEG, ROLE_POS, ROLE_REPLICAT, ROLE_SUJET,
                                                run_subject_variance, subject_variance_verdict)

_LEASE_GUARD_EXEMPT = True


def _c(name, role, verdict, intact=40.0, floor=24.0, ratio=1.0):
    return {"name": name, "role": role, "verdict": verdict, "within_ratio": ratio,
            "ratio": ratio, "intact_median": intact, "floor": floor}


def _controles_ok():
    return [_c("lecteur", ROLE_POS, "PERCEPTION_DEMANDED"),
            _c("reflexe", ROLE_NEG, "PERCEPTION_DECOY")]


# --------------------------------------------------------------------------------------------------
# 1. Les CONTRÔLES passent avant toute lecture de la DV
# --------------------------------------------------------------------------------------------------

def test_un_controle_ABSENT_ne_vaut_pas_un_controle_qui_PASSE():
    """Forme (a) du biais du dépôt : ne pas avoir lancé un contrôle n'est pas l'avoir réussi. Sans ce
    cas, un plan amputé de ses contrôles rendrait un verdict de fond."""
    v = subject_variance_verdict([_c("a", ROLE_SUJET, "PERCEPTION_DEMANDED"),
                                  _c("b", ROLE_SUJET, "PERCEPTION_DECOY")])
    assert v["verdict"] == "INDETERMINE-INSTRUMENT"
    assert v["controles"][ROLE_POS] == "ABSENT" and v["controles"][ROLE_NEG] == "ABSENT"


def test_un_controle_POSITIF_qui_ECHOUE_interdit_toute_lecture():
    """Si le lecteur CÂBLÉ ne rend pas PERCEPTION_DEMANDED, l'instrument est aveugle in-world et le
    reste ne veut rien dire — c'est exactement ce qui manquait à WARM-002 et S2-006."""
    rows = [_c("lecteur", ROLE_POS, "PERCEPTION_DECOY"),
            _c("reflexe", ROLE_NEG, "PERCEPTION_DECOY"),
            _c("a", ROLE_SUJET, "PERCEPTION_DEMANDED"), _c("b", ROLE_SUJET, "PERCEPTION_DECOY"),
            _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    v = subject_variance_verdict(rows)
    assert v["verdict"] == "INDETERMINE-INSTRUMENT"
    assert "attendu PERCEPTION_DEMANDED" in " ".join(v["raisons"])


def test_un_controle_NEGATIF_qui_MORD_interdit_toute_lecture():
    """Branche symétrique : si le réflexe câblé — qui ne PEUT pas lire — rend PERCEPTION_DEMANDED,
    le marqueur mord sur quelque chose qui n'est pas la perception."""
    rows = [_c("lecteur", ROLE_POS, "PERCEPTION_DEMANDED"),
            _c("reflexe", ROLE_NEG, "PERCEPTION_DEMANDED"),
            _c("a", ROLE_SUJET, "PERCEPTION_DEMANDED"), _c("b", ROLE_SUJET, "PERCEPTION_DECOY"),
            _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    assert subject_variance_verdict(rows)["verdict"] == "INDETERMINE-INSTRUMENT"


# --------------------------------------------------------------------------------------------------
# 2. LA branche que le bras de réplication achète (classe E23)
# --------------------------------------------------------------------------------------------------

def test_SUBJECT_BOUND_quand_la_divergence_DEPASSE_le_bruit():
    """RÉPONSE CONNUE : 2 verdicts distincts entre sujets, 1 seul entre réplicats du MÊME sujet →
    la divergence dépasse le bruit → S6 se transporte."""
    rows = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED"),
        _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY"),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED"),
        _c("r1", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    v = subject_variance_verdict(rows)
    assert v["verdict"] == "VERDICT_IS_SUBJECT_BOUND"
    assert (v["d_inter"], v["d_intra"]) == (2, 1)


def test_INDETERMINE_BRUIT_quand_le_MEME_sujet_diverge_AUTANT():
    """LE cas qui justifie tout l'amendement, et la branche NÉGATIVE du test précédent : la MÊME
    divergence inter-sujets, mais le même sujet répliqué diverge autant. Sans ce bras, le design
    aurait rendu SUBJECT_BOUND sur du bruit pur — classe E23."""
    rows = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED"),
        _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY"),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED"),
        _c("r1", ROLE_REPLICAT, "PERCEPTION_DECOY")]
    v = subject_variance_verdict(rows)
    assert v["verdict"] == "INDETERMINE-BRUIT"
    assert (v["d_inter"], v["d_intra"]) == (2, 2)


def test_WORLD_BOUND_exige_AUSSI_un_instrument_STABLE():
    """`VERDICT_IS_WORLD_BOUND` n'est prononçable que si les sujets sont d'accord ET que l'instrument
    est stable : sinon on ne distingue pas « le monde décide » de « l'instrument ne voit rien »."""
    accord = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DECOY"), _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY"),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DECOY"), _c("r1", ROLE_REPLICAT, "PERCEPTION_DECOY")]
    assert subject_variance_verdict(accord)["verdict"] == "VERDICT_IS_WORLD_BOUND"

    instable = list(accord)
    instable[-1] = _c("r1", ROLE_REPLICAT, "PERCEPTION_DEMANDED")     # le bruit, seul, bouge
    v = subject_variance_verdict(instable)
    assert v["verdict"] == "INDETERMINE-BRUIT", (
        "accord entre sujets + instrument instable ne peut pas se lire WORLD_BOUND")


def test_SANS_replicat_le_verdict_REFUSE_de_conclure():
    """Sans référence de bruit, une divergence ne prouve rien. L'instrument doit le DIRE, pas
    supposer un bruit nul — c'est précisément l'hypothèse implicite du design d'origine."""
    rows = _controles_ok() + [_c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED"),
                              _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY")]
    assert subject_variance_verdict(rows)["verdict"] == "INDETERMINE-SANS-REFERENCE-DE-BRUIT"


# --------------------------------------------------------------------------------------------------
# 3. Domaine, corps, et l'absence de mesure
# --------------------------------------------------------------------------------------------------

def test_un_sujet_SOUS_son_plancher_est_ECARTE_et_NOMME():
    """Issue légitime déclarée d'avance (c'est ce qui est arrivé à `soup` dans S2-013) : le sujet
    dégénéré sort du contraste, mais il est NOMMÉ — un écart silencieux serait une mesure perdue."""
    rows = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED"),
        _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY", intact=10.0),      # sous le plancher 24.0
        _c("bruit", ROLE_SUJET, "PERCEPTION_DECOY"),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    v = subject_variance_verdict(rows)
    assert v["degeneres"] == ["soupe"] and v["n_sujets"] == 2
    assert v["verdict"] == "VERDICT_IS_SUBJECT_BOUND"


def test_MOINS_DE_DEUX_sujets_exploitables_ne_rend_AUCUN_verdict():
    rows = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED"),
        _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY", intact=1.0),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    assert subject_variance_verdict(rows)["verdict"] == "INDETERMINE-DEGENERE"


def test_le_confond_de_CORPS_est_RAPPORTE_sans_bloquer():
    """Déclaré d'avance : si les survies intactes diffèrent de plus de 2x, le contraste confond
    « repli » et « corps ». On le RAPPORTE — le taire serait publier un contraste ambigu."""
    rows = _controles_ok() + [
        _c("champion", ROLE_SUJET, "PERCEPTION_DEMANDED", intact=100.0),
        _c("soupe", ROLE_SUJET, "PERCEPTION_DECOY", intact=30.0),
        _c("r0", ROLE_REPLICAT, "PERCEPTION_DEMANDED")]
    v = subject_variance_verdict(rows)
    assert v["corps"]["confondu"] and v["corps"]["ratio_max_min"] > 2.0
    assert v["verdict"] == "VERDICT_IS_SUBJECT_BOUND"       # rapporté, PAS bloquant


def test_une_entree_VIDE_ne_fabrique_JAMAIS_un_verdict_de_fond():
    """Forme (a) du biais systématique du dépôt : donnée absente → affirmation négative. Refusé."""
    for vide in ([], None, ()):
        assert subject_variance_verdict(vide)["verdict"] == "INDETERMINE-SANS-MESURE"


# --------------------------------------------------------------------------------------------------
# 4. Le RUNNER — garde d'arguments EN TÊTE, et le régime passe bien à chaque cellule
# --------------------------------------------------------------------------------------------------

def _map_fn_dose(par_nom):
    vus = []

    def map_fn(worlds=None, seed=None, K=None, subject=None, **kw):
        vus.append({"world_seed": seed, "K": K, "subject": subject, **kw})
        return {worlds[0]: {"verdict": par_nom[subject], "within_ratio": 1.0, "n": K,
                            "intact_median": 40.0, "floor": 24.0, "between_ratio": 1.0}}
    map_fn.vus = vus
    return map_fn


def test_le_runner_REFUSE_un_plan_VIDE_ou_un_regime_degenere():
    """Garde EN TÊTE : le refus doit être instantané, aucun génome construit. La sentinelle lèverait
    si une cellule était lancée."""
    def _sentinelle(**kw):
        raise AssertionError("une cellule a été lancée alors que la garde aurait dû refuser AVANT")

    with pytest.raises(ValueError, match="degenere"):
        run_subject_variance(plan=[], map_fn=_sentinelle)
    plan = [("x", ROLE_SUJET, lambda: "G", 1)]
    for mauvais in ({"k": 0}, {"regime": {"num_agents": 0, "max_ticks": 200}},
                    {"regime": {"num_agents": 12, "max_ticks": 0}}):
        with pytest.raises(ValueError, match="degenere"):
            run_subject_variance(plan=plan, map_fn=_sentinelle, **mauvais)


def test_le_runner_CABLE_le_meme_regime_dans_CHAQUE_cellule():
    """Si une cellule tournait dans un autre régime, le contraste inter-sujets comparerait deux
    protocoles — et le plancher MESURÉ ne s'appliquerait plus."""
    plan = [("a", ROLE_SUJET, lambda: "GA", 7), ("b", ROLE_SUJET, lambda: "GB", 9)]
    mf = _map_fn_dose({"GA": "PERCEPTION_DEMANDED", "GB": "PERCEPTION_DECOY"})
    lignes, _ = run_subject_variance(plan=plan, map_fn=mf, k=12, verbose=False)

    assert [l["name"] for l in lignes] == ["a", "b"]
    assert [l["verdict"] for l in lignes] == ["PERCEPTION_DEMANDED", "PERCEPTION_DECOY"]
    assert {v["K"] for v in mf.vus} == {12}
    assert {v["num_agents"] for v in mf.vus} == {12} and {v["max_ticks"] for v in mf.vus} == {200}
    assert [v["world_seed"] for v in mf.vus] == [7, 9], "la graine de monde de chaque cellule est perdue"


def test_le_runner_MESURE_le_sujet_de_la_cellule_et_pas_un_autre():
    """Contrôle E1 par construction : si le runner ignorait `genome_fn`, les deux cellules
    rendraient le même verdict et ce test mourrait."""
    plan = [("a", ROLE_SUJET, lambda: "GA", 1), ("b", ROLE_SUJET, lambda: "GB", 1)]
    mf = _map_fn_dose({"GA": "PERCEPTION_DEMANDED", "GB": "PERCEPTION_DECOY"})
    run_subject_variance(plan=plan, map_fn=mf, verbose=False)
    assert [v["subject"] for v in mf.vus] == ["GA", "GB"]
