"""`tools/check_calibration_reach.py` (P2.56) confronté à des réponses CONNUES : l'analyse AST « importé ET
appelé » sur des sources synthétiques (chaque forme d'import, l'appel absent, l'appel indirect qui ne compte
PAS), la résolution des clés (qualifiée, nue, nue en collision -> refusée), le verdict du cliquet (une NOUVELLE
muette BLOQUE ; une résorbée est rapportée ; baseline absente = tout est nouveau), et l'égalité entre l'ensemble
« garde-seule » du cliquet et celui que `test_perimeter_widening` publie (même expression : un cliquet qui
compterait une AUTRE dette que celle publiée serait un faux vert). Le compte réel est RECOMPUTÉ, jamais figé."""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_calibration_reach as R  # noqa: E402

SRC_FROM_CALL = "from tools.x import fn as f\n\ndef test_a():\n    assert f(1) == 2\n"
SRC_FROM_NOCALL = "from tools.x import fn\n\ndef test_a():\n    assert fn is not None\n"
SRC_IMPORT_ATTR = "import tools.x as M\n\ndef test_a():\n    assert M.fn(1) == 2\n"
SRC_IMPORT_NOCALL = "import tools.x\n\ndef test_a():\n    pass\n"
SRC_SUBMODULE = "from tools import x\n\ndef test_a():\n    x.fn(1)\n"
SRC_LOCAL = "def test_a():\n    from tools.x import fn\n    fn(1)\n"
SRC_INDIRECT = "from tools.orch import run_all\n\ndef test_a():\n    run_all()   # run_all appelle fn : ne compte PAS\n"


def test_reached_means_imported_AND_called_for_every_import_form():
    assert R.reached_symbols(SRC_FROM_CALL) == {("tools.x", "fn")}
    assert R.reached_symbols(SRC_IMPORT_ATTR) == {("tools.x", "fn")}
    assert R.reached_symbols(SRC_SUBMODULE) == {("tools.x", "fn")}
    assert R.reached_symbols(SRC_LOCAL) == {("tools.x", "fn")}


def test_imported_but_never_called_does_NOT_count_and_neither_does_an_indirect_call():
    # la v2 de P2.56 créditait `import tools.x` de TOUS les symboles de x : six fonctions comptées pour un appel
    assert R.reached_symbols(SRC_FROM_NOCALL) == set()
    assert R.reached_symbols(SRC_IMPORT_NOCALL) == set()
    assert ("tools.orch", "fn") not in R.reached_symbols(SRC_INDIRECT)
    assert R.reached_symbols("def test_a(:\n") == set()          # source illisible : vide, pas une exception


def test_key_resolution_qualified_bare_and_collision_refused():
    instruments = {"fn": "tools/x.py", "seul": "tools/y.py"}
    collisions = {"fn": ["tools/x.py", "tools/z.py"]}
    assert R.resolve("tools/evo_runs/x.py::fn", instruments, collisions) == ("tools.evo_runs.x", "fn")
    assert R.resolve("seul", instruments, collisions) == ("tools.y", "seul")
    module, why = R.resolve("fn", instruments, collisions)
    assert module is None and "COLLISION" in why
    module, why = R.resolve("inconnu", instruments, collisions)
    assert module is None and "introuvable" in why


def test_garde_seule_is_the_SAME_set_as_the_published_exposure_test():
    """La dette que le cliquet mesure est celle que test_perimeter_widening publie : même expression."""
    calibrated = R.load_calibrated()
    assert calibrated, "CALIBRATED illisible : la portée ne peut pas être mesurée"
    garde = re.compile(r"(:raises$|^guard-before-world$|^regime-degenere|^plan-vide|^empty-cohort|"
                       r"^entree-vide|^cohorte-vide|^selection-vide|^argument-degenere|^echelle-vide)")
    publie = sorted(n for n, cas in calibrated.items()
                    if isinstance(cas, list) and cas and all(garde.search(c) for c in cas))
    assert R.garde_seule(calibrated) == publie
    assert R.GARDE_SEULE.pattern == garde.pattern


def test_the_real_count_is_RECOMPUTED_and_partitions_the_guard_only_set():
    r = R.scan()
    assert r["n_calibrated"] > 0 and r["n_tests"] > 0
    assert len(r["declaratives"]) + len(r["muettes"]) + len(r["non_resolues"]) == r["garde_seule"]
    assert r["garde_seule"] > 0, "si plus AUCUNE déclaration n'est garde-seule, mettre à jour P2.49/P2.56 AVANT de retirer ce test"
    for k, temoins in r["declaratives"].items():
        assert temoins and all(t.startswith("tests/") for t in temoins), k
    assert not (set(r["declaratives"]) & set(r["muettes"]))


def test_the_ratchet_BLOCKS_a_new_mute_and_REPORTS_a_resolved_one_and_says_when_the_baseline_is_absent():
    res = {"muettes": ["a", "b", "c"]}
    e = R.etat(res, {"muettes": ["a", "b"]})
    assert e["nouvelles"] == ["c"] and e["resorbees"] == [] and e["connues"] == ["a", "b"] and not e["baseline_absente"]
    e = R.etat({"muettes": ["a"]}, {"muettes": ["a", "b"]})
    assert e["nouvelles"] == [] and e["resorbees"] == ["b"]
    e = R.etat(res, None)
    assert e["baseline_absente"] and e["nouvelles"] == ["a", "b", "c"]


def test_the_frozen_baseline_matches_the_current_count_and_the_gate_is_green_on_it():
    """La baseline est gelée dans le MÊME commit que l'outil (E4 occ. 5) : elle doit être exactement l'état
    courant, sinon le premier passage de la porte serait déjà un faux vert ou un faux rouge."""
    base = R._load_baseline()
    assert base is not None, "baseline absente : python tools/check_calibration_reach.py --update-baseline"
    e = R.etat(R.scan(), base)
    assert e["nouvelles"] == [], e["nouvelles"]
