# -*- coding: utf-8 -*-
"""Calibration de `_lecture_pred2` (prediction n 2 de LOCK-001) -- lecture PURE, a reponse connue par
branche, ORDRE IMPOSE, et un balayage du continuum qui prouve que AUTRE n'est atteignable que par une
configuration nommee (mediane entre seuil_seed et seuil_monte : rapportee, jamais inferee)."""
import itertools

from tools.lock001_pred2_r1 import BRAS, CELLULES, SEEDS, _lecture_pred2, cle
from tools.preregister import verify

REGLE = verify("LOCK-001-PRED2-R1")


def _db(retain, present):
    """retain / present : {(lr, ep): [3 valeurs]}."""
    db = {}
    for lr, ep in CELLULES:
        for s, v in zip(SEEDS, retain[(lr, ep)]):
            db[cle("RETAIN", lr, ep, s)] = {"intact": v, "ablated": 0.17}
        for s, v in zip(SEEDS, present[(lr, ep)]):
            db[cle("PRESENT", lr, ep, s)] = {"intact": v, "ablated": v}
    return db


_REF_OK = {c: [0.40, 0.42, 0.38] for c in CELLULES}       # la reference apprend partout
_REF_KO = {c: [0.18, 0.2, 0.17] for c in CELLULES}        # la reference ne apprend nulle part


def test_INCOMPLET_prime():
    db = _db({c: [0.9] * 3 for c in CELLULES}, _REF_OK)
    del db[cle("PRESENT", 0.0005, 14400, 2)]
    assert _lecture_pred2(db, REGLE)["branche"] == "INCOMPLET"


def test_SANS_REFERENCE_quand_PRESENT_n_apprend_nulle_part():
    """E19 : un RETAIN a 0,9 ne se lit PAS si la reference est effondree partout."""
    r = _lecture_pred2(_db({c: [0.9] * 3 for c in CELLULES}, _REF_KO), REGLE)
    assert r["branche"] == "SANS_REFERENCE"


def test_PERCE_sur_un_point_interpretable_seulement():
    ret = {(0.002, 3600): [0.2] * 3, (0.0005, 3600): [0.45, 0.42, 0.50], (0.0005, 14400): [0.2] * 3}
    assert _lecture_pred2(_db(ret, _REF_OK), REGLE)["branche"] == "PERCE"
    # le MEME RETAIN sur un point ou la reference est effondree ne compte pas
    pres = dict(_REF_OK); pres[(0.0005, 3600)] = [0.2, 0.18, 0.19]
    assert _lecture_pred2(_db(ret, pres), REGLE)["branche"] == "NE_PERCE_PAS"


def test_MONTE_entre_le_meilleur_connu_et_la_percee():
    ret = {c: [0.36, 0.35, 0.37] for c in CELLULES}
    assert _lecture_pred2(_db(ret, _REF_OK), REGLE)["branche"] == "MONTE"


def test_NE_PERCE_PAS_exige_la_reference_apprise_PARTOUT_ou_c_est_lu():
    ret = {c: [0.25, 0.28, 0.22] for c in CELLULES}
    assert _lecture_pred2(_db(ret, _REF_OK), REGLE)["branche"] == "NE_PERCE_PAS"
    # le meilleur RETAIN connu du n = 12 plain (0,284) tombe dans NE_PERCE_PAS : c'est le no-op de la regle
    ret_ref = {c: [0.2836, 0.29, 0.27] for c in CELLULES}
    assert _lecture_pred2(_db(ret_ref, _REF_OK), REGLE)["branche"] == "NE_PERCE_PAS"


def test_AUTRE_est_la_zone_NOMMEE_entre_seuil_seed_et_seuil_monte():
    ret = {c: [0.32, 0.31, 0.33] for c in CELLULES}
    assert _lecture_pred2(_db(ret, _REF_OK), REGLE)["branche"] == "AUTRE"


def test_le_continuum_des_medianes_tombe_toujours_dans_une_branche_NOMMEE():
    grille = [i / 50 for i in range(51)]
    vues = set()
    for m, p in itertools.product(grille, grille):
        r = _lecture_pred2(_db({c: [m] * 3 for c in CELLULES}, {c: [p] * 3 for c in CELLULES}), REGLE)
        vues.add(r["branche"])
        assert r["branche"] in {"SANS_REFERENCE", "PERCE", "MONTE", "NE_PERCE_PAS", "AUTRE"}
    assert vues == {"SANS_REFERENCE", "PERCE", "MONTE", "NE_PERCE_PAS", "AUTRE"}


def test_le_design_est_declare():
    from tools.lock001_pred2_r1 import design
    d = design()
    assert d["replication_unit"] == "seed" and d["n_independent"] == 3
    assert len(CELLULES) * len(BRAS) * len(SEEDS) == 18
