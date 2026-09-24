"""Lecture scellée de `BILINEAR-SHAM-R1` (`tools/bilinear_sham_run.py::_lecture`) — chaque branche atteinte par
une base synthétique, dans l'ORDRE IMPOSÉ ; le contrôle de bit-identité confronté à une réponse connue ; le
résultat publié relu contre la règle scellée. Aucun entraînement ici."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.bilinear_sham_run import BRAS, _bit_identite, _lecture, _sous_barre  # noqa: E402
from tools.preregister import verify  # noqa: E402

RULE = verify("BILINEAR-SHAM-R1")
C = RULE["cellule"]
LR_PUB, LR_BAS = C["lr"]


def _db(plain=0.27, bil=0.93, sham=0.29, plain_bas=0.18, bil_bas=0.43, sham_bas=0.20, per_seed=None):
    db = {}
    for s in C["seeds"]:
        p, b, sh = (per_seed(s) if per_seed else (plain, bil, sham))
        db[f"plain|lr={LR_PUB}|seed={s}"], db[f"bilinear|lr={LR_PUB}|seed={s}"], db[f"sham|lr={LR_PUB}|seed={s}"] = p, b, sh
        db[f"plain|lr={LR_BAS}|seed={s}"], db[f"bilinear|lr={LR_BAS}|seed={s}"] = plain_bas, bil_bas
        db[f"sham|lr={LR_BAS}|seed={s}"] = sham_bas
    return db


def test_the_rule_names_the_pre_seal_smoke_and_excludes_seed_0():
    # E11 : le seed 0 (sham 0,309) a été VU avant scellement -- la règle le dit et l'exclut du n.
    assert "0,30937498807907104" in RULE["provenance"] and "EXCLU" in RULE["provenance"]
    assert 0 not in C["seeds"] and len(C["seeds"]) == 12
    assert [b[0] for b in BRAS] == C["bras"]


def test_incomplete_gives_no_reading():
    db = _db()
    del db[f"sham|lr={LR_PUB}|seed=7"]
    assert _lecture(db, RULE) == {"branche": "INCOMPLET", "manquantes": 1}


def test_sham_inert_when_it_sits_on_the_plain_at_matched_dose_and_stays_under_the_bar_at_low_step():
    lec = _lecture(_db(), RULE)
    assert lec["branche"] == "SHAM_INERTE" and lec["sham_sous_plain_plus_marge"] == "12/12"


def test_sham_inert_needs_eleven_seeds_under_plain_plus_margin():
    # 10/12 sous plain + marge : la médiane tient encore mais la convention 11/12 non -> pas INERTE
    db = _db(per_seed=lambda s: (0.27, 0.93, 0.29) if s <= 10 else (0.27, 0.93, 0.45))
    lec = _lecture(db, RULE)
    assert lec["sham_sous_plain_plus_marge"] == "10/12" and lec["branche"] == "SHAM_PARTIEL"


def test_sham_composes_at_the_published_step():
    assert _lecture(_db(sham=0.90), RULE)["branche"] == "SHAM_COMPOSE"


def test_sham_composes_at_the_low_step_only_is_still_compose_E19():
    # inerte au pas publié, mais >= barre à 0,002 : la clause E19 tranche COMPOSE avant INERTE
    assert _lecture(_db(sham=0.29, sham_bas=0.55), RULE)["branche"] == "SHAM_COMPOSE"


def test_partial_is_reported_not_inferred():
    # sham à 0,40 : au-dessus de plain + marge, sous la barre -> ni INERTE ni COMPOSE
    lec = _lecture(_db(sham=0.40), RULE)
    assert lec["branche"] == "SHAM_PARTIEL" and lec["mediane_sham_002"] == pytest.approx(0.40)


def test_bit_identity_control_counts_equalities_against_the_published_json_and_names_each_gap():
    ref = {"decisive_same_tick_supervised": {"per_seed": {
        "plain": [0.1 * i for i in range(12)], "bilinear": [0.5 + 0.01 * i for i in range(12)]}}}
    db = _db(per_seed=lambda s: (0.1 * s, 0.5 + 0.01 * s, 0.29))
    ok = _bit_identite(db, RULE, ref)
    assert ok == {"n_egal": 22, "n_attendu": 22, "ecarts": []}          # seeds 1-11 x 2 bras ; seed 12 hors JSON
    db[f"bilinear|lr={LR_PUB}|seed=4"] = 0.999
    ko = _bit_identite(db, RULE, ref)
    assert ko["n_egal"] == 21 and ko["ecarts"] == [{"cellule": f"bilinear|lr={LR_PUB}|seed=4", "mesure": 0.999,
                                                    "publie": pytest.approx(0.54)}]
    # une cellule ABSENTE est un écart (mesure None), jamais une égalité : une base vide rend 0/22, pas 22/22
    vide = _bit_identite({}, RULE, ref)
    assert vide["n_egal"] == 0 and len(vide["ecarts"]) == 22 and vide["ecarts"][0]["mesure"] is None


def test_lecture_publishes_the_bit_identity_control_when_present():
    db = _db()
    db["_controles"] = {"bit_identite": {"n_egal": 21, "n_attendu": 22, "ecarts": [{"cellule": "x"}]}}
    assert _lecture(db, RULE)["bit_identite"] == "21/22"


_PUB = os.path.join(os.path.dirname(__file__), "..", "..", "results", "bilinear_sham_r1.json")


def _publie():
    if not os.path.exists(_PUB):
        return None
    db = json.load(open(_PUB, encoding="utf-8"))
    return db if "_lecture" in db else None          # run en cours : cellules sans lecture


@pytest.mark.skipif(_publie() is None, reason="run BILINEAR-SHAM-R1 non encore publié (ou en cours)")
def test_published_result_rereads_to_its_sealed_branch_with_matched_params_and_bit_identity():
    db = _publie()
    lec = _lecture(db, RULE)
    assert lec["branche"] == db["_lecture"]["branche"] != "INCOMPLET"
    n = db["_regime"]["n_params_par_agent"]
    assert n["sham"] == n["bilinear"] > n["plain"]
    assert db["_controles"]["bit_identite"]["n_egal"] == db["_controles"]["bit_identite"]["n_attendu"] == 22


def test_le_critere_se_compare_sur_la_GRILLE_et_pas_en_flottants():
    """2026-09-24 — l'accuracy est un COMPTE sur 640 evaluations et la marge scellee (0,05) vaut EXACTEMENT
    32 pas : le critere tombe donc sur des EGALITES, qui se perdent en binaire. Reponses connues, tirees des
    cellules publiees : le seed 3 (210/640 contre 178/640 + 32/640) est une egalite VRAIE que la comparaison
    flottante rendait fausse pour 1,19e-08 -- le compte publie valait 8/12 au lieu de 9/12.
    """
    assert _sous_barre(210 / 640, 178 / 640, 0.05, 640) is True, "egalite exacte : comptee"
    assert _sous_barre(212 / 640, 176 / 640, 0.05, 640) is False, "un pas au-dessus : non comptee"
    assert _sous_barre(179 / 640, 174 / 640, 0.05, 640) is True
    # le float32 du depot : 178/640 est stocke 0,27812498807907104 -- la grille doit RESISTER a ce bruit
    import numpy as np
    assert _sous_barre(float(np.float32(210 / 640)), float(np.float32(178 / 640)), 0.05, 640) is True


def test_hors_grille_le_critere_retombe_sur_la_comparaison_ordinaire():
    """SPECIFICITE : si la marge n'est pas un multiple du pas, il n'y a pas de grille a utiliser -- le
    critere ne doit pas inventer d'arrondi (sans ce cas, un arrondi silencieux deplacerait un seuil).
    """
    assert _sous_barre(0.5, 0.48, 0.037, 640) is True
    assert _sous_barre(0.5, 0.40, 0.037, 640) is False
