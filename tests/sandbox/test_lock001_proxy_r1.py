# -*- coding: utf-8 -*-
"""Calibration de `_lecture_r1` (LOCK-001-PROXY, barreau 1) -- la LECTURE de la regle scellee est une
fonction PURE, confrontee ici a une reponse connue par branche, dans l'ORDRE IMPOSE. Un runner dont la
lecture n'est pas calibree produit un verdict (CLAUDE.md) ; celui-ci est calibre AVANT sa premiere
cellule."""
import pytest

from tools.lock001_proxy_r1 import CELLULES, SEEDS, _lecture_r1, cle
from tools.preregister import verify

REGLE = verify("LOCK-001-PROXY-R1")


def _db(haut, lr_bas, mi):
    """Fabrique une base ou chaque cellule a les 3 seeds fixes : haut = 14400/0.002, lr_bas =
    14400/0.0005, mi = 7200/0.002 (listes de 3 lang_i)."""
    db = {}
    for (lr, ep), vals in (((0.002, 14400), haut), ((0.0005, 14400), lr_bas), ((0.002, 7200), mi)):
        for s, v in zip(SEEDS, vals):
            db[cle(lr, ep, s)] = {"lang_i": v, "lang_a": 0.16, "ctrl_i": 0.55, "ctrl_a": 1.0}
    return db


def test_INCOMPLET_prime_sur_tout():
    db = _db([0.9, 0.9, 0.9], [0.9, 0.9, 0.9], [0.9, 0.9, 0.9])
    del db[cle(0.002, 7200, 1)]
    r = _lecture_r1(db, REGLE)
    assert r["branche"] == "INCOMPLET" and r["manquantes"] == [cle(0.002, 7200, 1)]


def test_PERCE_INDICATIF_exige_la_mediane_ET_chaque_seed():
    assert _lecture_r1(_db([0.45, 0.42, 0.50], [0.2, 0.2, 0.2], [0.3, 0.3, 0.3]), REGLE)["branche"] == "PERCE_INDICATIF"
    # mediane >= 0.40 mais UN seed sous 0.30 : pas un PERCE (un seul seed ne doit pas porter le verdict)
    r = _lecture_r1(_db([0.45, 0.60, 0.25], [0.2, 0.2, 0.2], [0.3, 0.3, 0.3]), REGLE)
    assert r["branche"] != "PERCE_INDICATIF"


def test_PERCE_PAR_LR_est_la_clause_E19():
    r = _lecture_r1(_db([0.2, 0.2, 0.2], [0.45, 0.42, 0.50], [0.2, 0.2, 0.2]), REGLE)
    assert r["branche"] == "PERCE_PAR_LR"


def test_TENDANCE_quand_ca_monte_sans_percer():
    # reference 0.183 + 0.10 = 0.283 <= max(mediane) < 0.40
    r = _lecture_r1(_db([0.30, 0.31, 0.29], [0.2, 0.2, 0.2], [0.25, 0.25, 0.25]), REGLE)
    assert r["branche"] == "TENDANCE"


def test_NE_PERCE_PAS_exige_les_DEUX_lr_nuls():
    r = _lecture_r1(_db([0.19, 0.18, 0.21], [0.17, 0.20, 0.18], [0.18, 0.18, 0.18]), REGLE)
    assert r["branche"] == "NE_PERCE_PAS"
    # la reference elle-meme (3600) doit tomber dans NE_PERCE_PAS : c'est le no-op de la regle
    ref = REGLE["reference_3600"]["seeds"]
    assert _lecture_r1(_db(ref, ref, ref), REGLE)["branche"] == "NE_PERCE_PAS"


def test_AUTRE_ramasse_le_reste_sans_inferer():
    # mediane haute a 0.35 (>= 0.30, < 0.40, sans tendance car... non : 0.35 >= 0.283 -> TENDANCE).
    # Cas AUTRE reel : mediane 0.32 a un lr et 0.20 a l'autre ne monte pas de 0.10 ? 0.32 >= 0.283 -> TENDANCE.
    # AUTRE = mediane haute entre 0.283... impossible ; donc AUTRE = 0.30 <= mediane < 0.283 ? vide.
    # La seule region AUTRE : seuil_seed <= max(mediane) < reference + delta, c.-a-d. [0.30, 0.283) --
    # VIDE avec ces seuils. On le CONSTATE (la regle couvre le continuum) plutot que de l'inventer.
    seuils = REGLE["seuils"]
    assert seuils["seuil_seed"] >= REGLE["reference_3600"]["mediane_lang_i_D2"] + seuils["delta_tendance"], (
        "si cette assertion tombe, une region AUTRE non vide existe : la tester explicitement")


def test_la_regle_scellee_couvre_le_CONTINUUM_des_medianes():
    """Balayage exhaustif : toute mediane dans [0, 1] (aux deux lr) tombe dans une branche NOMMEE, et
    jamais dans AUTRE avec les seuils scelles -- la latitude post-hoc est FERMEE."""
    import itertools
    grille = [i / 50 for i in range(51)]
    vues = set()
    for a, b in itertools.product(grille, grille):
        r = _lecture_r1(_db([a, a, a], [b, b, b], [0.2, 0.2, 0.2]), REGLE)
        vues.add(r["branche"])
        assert r["branche"] != "AUTRE", (a, b)
    assert vues >= {"PERCE_INDICATIF", "PERCE_PAR_LR", "TENDANCE", "NE_PERCE_PAS"}


def test_le_runner_declare_son_design_et_sa_famille():
    from tools.lock001_proxy_r1 import design
    d = design()
    assert d["replication_unit"] == "seed" and d["n_independent"] == 3
    assert len(CELLULES) * len(SEEDS) == 9


# --- barreau 1c : la lecture « le pas seul ? », calibree a reponse connue ---------------------------

def _db_1c(vals):
    from tools.lock001_proxy_r1 import cle
    return {cle(0.0005, 3600, s): {"lang_i": v, "lang_a": 0.16, "ctrl_i": 0.9, "ctrl_a": 1.0}
            for s, v in zip((0, 1, 2), vals)}


def test_1c_INCOMPLET_prime():
    from tools.lock001_proxy_r1 import _lecture_r1c
    regle = verify("LOCK-001-PROXY-R1c")
    db = _db_1c([0.8, 0.8, 0.8]); db.pop(next(iter(db)))
    assert _lecture_r1c(db, regle)["branche"] == "INCOMPLET"


def test_1c_les_trois_branches_a_reponse_connue():
    from tools.lock001_proxy_r1 import _lecture_r1c
    regle = verify("LOCK-001-PROXY-R1c")
    assert _lecture_r1c(_db_1c([0.8, 0.7, 0.75]), regle)["branche"] == "PAS_SEUL"
    assert _lecture_r1c(_db_1c([0.17, 0.2, 0.18]), regle)["branche"] == "PAS_ET_DUREE"
    assert _lecture_r1c(_db_1c([0.35, 0.3, 0.33]), regle)["branche"] == "INTERMEDIAIRE"
    # un seed sous 0,30 avec une mediane haute n'est PAS un PAS_SEUL
    assert _lecture_r1c(_db_1c([0.8, 0.8, 0.2]), regle)["branche"] == "INTERMEDIAIRE"
