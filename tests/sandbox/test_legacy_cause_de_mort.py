"""Lecture scellée de `LEGACY-CAUSE-DE-MORT-R1` (`tools/legacy_cause_de_mort.py::_lecture`) — cinq branches sur
bases synthétiques, dans l'ORDRE IMPOSÉ ; un bras sans aucune mort (l'oracle, lr0 sur certains seeds) rend des
parts `None`, jamais 0. Aucun monde ici."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.legacy_cause_de_mort import _lecture, _parts  # noqa: E402
from tools.preregister import verify  # noqa: E402

R = verify("LEGACY-CAUSE-DE-MORT-R1")
SEEDS, BRAS = R["cellule"]["seeds"], list(R["cellule"]["bras"])
E = {"energie_epuisee": 90, "hp_epuise": 5, "les_deux": 5, "AUCUNE": 0}
H = {"energie_epuisee": 5, "hp_epuise": 90, "les_deux": 5, "AUCUNE": 0}
M = {"energie_epuisee": 50, "hp_epuise": 45, "les_deux": 5, "AUCUNE": 0}
Z = {"energie_epuisee": 0, "hp_epuise": 0, "les_deux": 0, "AUCUNE": 0}


def _cell(cdm, res=100):
    return {"hit_last": 0.3, "resurrections": res, "learning": {}, "cause_de_mort": cdm}


def _db(f):
    return {f"{b}|seed={s}": f(b, s) for b in BRAS for s in SEEDS}


def test_parts_of_a_cohort_without_deaths_are_None_never_zero():
    p = _parts(Z)
    assert p["total"] == 0 and p["part_energie"] is None and p["part_hp"] is None


def test_energy_hp_and_mixed_branches():
    assert _lecture(_db(lambda b, s: _cell(E)), R)["branche"] == "ENERGIE"
    assert _lecture(_db(lambda b, s: _cell(H)), R)["branche"] == "HP"
    assert _lecture(_db(lambda b, s: _cell(M)), R)["branche"] == "MIXTE"


def test_a_single_AUCUNE_anywhere_refuses_the_reading():
    A = dict(E, AUCUNE=1)
    db = _db(lambda b, s: _cell(A) if (b, s) == ("lr_low", 2030) else _cell(E))
    assert _lecture(db, R)["branche"] == "INSTRUMENT"


def test_incomplete():
    db = _db(lambda b, s: _cell(E))
    del db["natural|seed=2031"]
    assert _lecture(db, R)["branche"] == "INCOMPLET"


def test_the_non_learner_arm_without_deaths_is_reported_as_such():
    db = _db(lambda b, s: _cell(Z, res=0) if b == "lr0_reference" else _cell(E))
    out = _lecture(db, R)
    assert out["branche"] == "ENERGIE"
    assert out["par_bras"]["lr0_reference"]["seeds_sans_mort"] == 12
    assert out["par_bras"]["lr0_reference"]["part_energie"] is None
