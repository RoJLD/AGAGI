"""Lecture scellée de `BILINEAR-ALIGNED-R1` (`tools/bilinear_aligned_run.py::_lecture`) — chaque branche
atteinte par une base synthétique, dans l'ORDRE IMPOSÉ, et le résultat publié relu contre la règle scellée.
Aucun entraînement ici."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.bilinear_aligned_run import _lecture  # noqa: E402
from tools.preregister import verify  # noqa: E402

RULE = verify("BILINEAR-ALIGNED-R1")
C = RULE["cellule"]


def _db(plain_002, bil_002, plain_0002=0.18, bil_0002=0.43, per_seed=None):
    db = {}
    for s in C["seeds"]:
        p, b = (per_seed(s) if per_seed else (plain_002, bil_002))
        db[f"plain|lr={C['lr'][0]}|seed={s}"] = p
        db[f"bilinear|lr={C['lr'][0]}|seed={s}"] = b
        db[f"plain|lr={C['lr'][1]}|seed={s}"] = plain_0002
        db[f"bilinear|lr={C['lr'][1]}|seed={s}"] = bil_0002
    return db


def test_incomplete_gives_no_reading():
    db = _db(0.28, 0.94)
    del db[f"bilinear|lr={C['lr'][0]}|seed=7"]
    assert _lecture(db, RULE)["branche"] == "INCOMPLET"


def test_separation_holds():
    assert _lecture(_db(0.28, 0.94), RULE)["branche"] == "SEPARATION_TIENT"


def test_separation_falls_when_plain_exceeds_its_closed_form_ceiling():
    assert _lecture(_db(0.45, 0.94), RULE)["branche"] == "SEPARATION_TOMBE"


def test_separation_falls_when_one_seed_too_many_is_not_separated():
    # 10/12 séparés : sous la convention 11/12
    db = _db(0.28, 0.94, per_seed=lambda s: (0.28, 0.94) if s <= 10 else (0.28, 0.35))
    assert _lecture(db, RULE)["branche"] == "SEPARATION_TOMBE"


def test_bilinear_below_threshold_at_both_steps():
    assert _lecture(_db(0.28, 0.40, bil_0002=0.30), RULE)["branche"] == "BILINEAIRE_SOUS_SEUIL"


def test_other_is_reported_not_inferred():
    # bilinéaire sous 0,5 au pas publié mais au-dessus à 0,002, plain sous son plafond, 12/12 séparés
    assert _lecture(_db(0.28, 0.45, bil_0002=0.80), RULE)["branche"] == "AUTRE"


def test_published_result_rereads_to_its_sealed_branch():
    p = os.path.join(os.path.dirname(__file__), "..", "..", "results", "bilinear_aligned_r1.json")
    db = json.load(open(p, encoding="utf-8"))
    lec = _lecture(db, RULE)
    assert lec["branche"] == db["_lecture"]["branche"] == "SEPARATION_TIENT"
    assert lec["separation_par_seed"] == "12/12"
