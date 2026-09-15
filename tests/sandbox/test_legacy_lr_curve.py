"""Lecture scellée de `LEGACY-LR-CURVE-R1` (`tools/legacy_lr_curve.py::_lecture`) — chaque branche atteinte par une
base synthétique dans l'ORDRE IMPOSÉ ; un seed NON MESURÉ (apprenant divergent) compte au dénominateur et dans
`non_mesures`, jamais dans la médiane. Aucun monde ici (la référence lr=0 est lue dans le JSON de P3.4)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.legacy_lr_curve import _lecture, _reference  # noqa: E402
from tools.preregister import verify  # noqa: E402

R = verify("LEGACY-LR-CURVE-R1")
SEEDS = R["cellule"]["seeds"]


def _cell(h, ok=True):
    if not ok:
        return {"hit_last": None, "learning": None, "erreur": "aucune decision"}
    return {"hit_last": h, "learning": {"legacy_updates": 50, "dW_abs_sum": 1.0}}


def _db(a, b):
    return {**{f"lr=0.01|seed={s}": a(s) for s in SEEDS}, **{f"lr=0.001|seed={s}": b(s) for s in SEEDS}}


def test_reference_is_imported_per_seed_from_P3_4():
    ref = _reference()
    assert set(ref) == set(SEEDS) and all(0.0 <= v <= 0.5 for v in ref.values())


def test_incomplete():
    db = _db(lambda s: _cell(0.45), lambda s: _cell(0.40))
    del db["lr=0.01|seed=2030"]
    assert _lecture(db, R, _reference())["branche"] == "INCOMPLET"


def test_stable_at_001_reads_threshold_above():
    out = _lecture(_db(lambda s: _cell(0.45), lambda s: _cell(0.40)), R, _reference())
    assert out["branche"] == "SEUIL_AU_DESSUS_DE_001" and out["par_lr"]["0.01"]["seeds_au_dessus"] == 12


def test_one_collapse_at_001_and_learning_at_0001_reads_threshold_between():
    db = _db(lambda s: _cell(0.0) if s == 2027 else _cell(0.45), lambda s: _cell(0.40))
    out = _lecture(db, R, _reference())
    assert out["branche"] == "SEUIL_ENTRE_0001_ET_001" and out["par_lr"]["0.01"]["effondres"] == 1


def test_a_NaN_seed_is_counted_unmeasured_and_never_in_the_median():
    db = _db(lambda s: _cell(0.45, ok=(s != 2030)), lambda s: _cell(0.15))
    out = _lecture(db, R, _reference())
    a = out["par_lr"]["0.01"]
    assert a["non_mesures"] == 1 and a["seeds_au_dessus"] == 11 and a["mediane_hit_last"] == 0.45
    assert out["branche"] == "TROP_BAS_A_0001"


def test_other_is_reported():
    # 0,01 : un effondrement ; 0,001 : pas 11/12 ET un seed NaN -> aucune des trois lectures nommées
    db = _db(lambda s: _cell(0.0) if s == 2027 else _cell(0.45),
             lambda s: _cell(0.15, ok=(s != 2031)))
    assert _lecture(db, R, _reference())["branche"] == "AUTRE"


def test_order_is_sealed_a_collapse_at_001_with_a_too_low_0001_reads_TROP_BAS_first():
    """L'ORDRE IMPOSÉ décide : 0,01 effondré (branche 2 refusée car 0,001 n'apprend pas) et 0,001 trop bas
    sans divergence -> TROP_BAS_A_0001, pas AUTRE. Gelé pour que personne ne « corrige » l'ordre après coup."""
    db = _db(lambda s: _cell(0.0) if s == 2027 else _cell(0.45), lambda s: _cell(0.15))
    assert _lecture(db, R, _reference())["branche"] == "TROP_BAS_A_0001"
