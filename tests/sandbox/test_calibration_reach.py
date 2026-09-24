"""`tools/check_calibration_reach.py` (P2.56) confronté à des réponses CONNUES : l'analyse AST « importé ET
appelé » sur des sources synthétiques (chaque forme d'import, l'appel absent, l'appel indirect qui ne compte
PAS), la résolution des clés (qualifiée, nue, nue en collision -> refusée), le verdict du cliquet (une NOUVELLE
muette BLOQUE ; une résorbée est rapportée ; baseline absente = tout est nouveau), et l'égalité entre l'ensemble
« garde-seule » du cliquet et celui que `test_perimeter_widening` publie (même expression : un cliquet qui
compterait une AUTRE dette que celle publiée serait un faux vert). Le compte réel est RECOMPUTÉ, jamais figé."""
import os
import re
import subprocess
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
SRC_RAISES = ("import pytest\nfrom tools.x import fn\n\ndef test_a():\n    with pytest.raises(ValueError):\n"
              "        fn(0)          # leve a la GARDE : le corps n'est pas atteint\n")
SRC_RAISES_THEN_CALL = SRC_RAISES + "\ndef test_b():\n    assert fn(1) == 2\n"


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


def test_a_call_under_pytest_raises_does_NOT_reach_the_body_but_a_real_call_beside_it_does():
    """Mesuré le 2026-09-23 : six déclarations garde-seule passaient pour déclaratives par leur SEUL test de garde
    (`with pytest.raises(...): run_arm(**degenere)`) -- un refus à la garde n'est pas une atteinte du corps."""
    assert ("tools.x", "fn") not in R.reached_symbols(SRC_RAISES)          # (pytest, raises) y est : sans importance
    assert ("tools.x", "fn") in R.reached_symbols(SRC_RAISES_THEN_CALL)


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
    # 2026-09-23 : garde-seule = 0 est l'état ATTEINT (P2.56 (a) et (b) soldées : 32 + 31 + 6 re-déclarées d'après
    # leurs témoins). Le compte reste recomputé ; la partition ci-dessus vaut aussi à zéro.
    assert r["garde_seule"] >= 0
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


CAL_SYNTH = ('CALIBRATED = {\n    "tools/x.py::fn": ["empty-cohort:raises", "guard-before-world"],\n'
             '    "tools/y.py::seul": ["empty-cohort:raises", "guard-before-world"],\n}\n')


def test_index_mode_reads_what_WILL_be_committed_not_the_disk(monkeypatch):
    """Porte 18 (E10 occ. 17, comme la porte 4 durcie) : sous `index=True`, CALIBRATED, les tests ET la baseline
    viennent de l'INDEX. Index SYNTHÉTIQUE ici : un appelant présent dans l'index résout la clé ; la MÊME mesure
    sur le disque (où aucun test n'appelle tools.x.fn) rend une réponse DIFFÉRENTE — c'est ce qui prouve que le
    mode index ne lit pas le disque."""
    blobs = {"tests/sandbox/test_instrument_calibration.py": CAL_SYNTH,
             "tests/sandbox/test_appelant.py": SRC_FROM_CALL,
             "tools/calibration_reach_baseline.json": '{"muettes": ["tools/y.py::seul"]}'}
    monkeypatch.setattr(R, "_index_blobs", lambda prefix: {k: v for k, v in blobs.items() if k.startswith(prefix)})
    r = R.scan(index=True)
    assert r["source"] == "index" and r["n_tests"] == 2 and r["n_calibrated"] == 2
    assert r["declaratives"] == {"tools/x.py::fn": ["tests/sandbox/test_appelant.py"]} and r["muettes"] == ["tools/y.py::seul"]
    e = R.etat(r, R._load_baseline(index=True))
    assert e["nouvelles"] == [] and e["connues"] == ["tools/y.py::seul"] and not e["baseline_absente"]
    d = R.scan(calibrated=R.load_calibrated(index=True), index=False)          # même dict, tests du DISQUE
    assert d["source"] == "disk" and "tools/x.py::fn" in d["muettes"], "sur le disque, rien n'appelle tools.x.fn"
    monkeypatch.setattr(R, "_index_blobs", lambda prefix: {})
    assert R.load_calibrated(index=True) == {} and R._load_baseline(index=True) is None, "index illisible : dit tel quel"
    assert R.main(["--index"]) == 1, "sans CALIBRATED lisible la porte ECHOUE, elle ne rend pas un vert"


def test_index_blobs_reads_the_real_index_in_batch_and_a_removed_test_vanishes_for_it(tmp_path, monkeypatch):
    """Plomberie réelle : un index TEMPORAIRE construit depuis HEAD (`GIT_INDEX_FILE`, comme un commit path-scopé)
    rend pour la baseline exactement le blob de HEAD ; un test RETIRÉ de cet index reste sur le disque mais
    n'existe plus pour `--index` (un commit qui supprime un appelant rend sa déclaration muette)."""
    env = {**os.environ, "GIT_INDEX_FILE": str(tmp_path / "idx")}
    subprocess.run(["git", "read-tree", "HEAD"], cwd=R._ROOT, env=env, check=True)
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "idx"))
    rel = "tools/calibration_reach_baseline.json"
    head = subprocess.run(["git", "show", "HEAD:" + rel], cwd=R._ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    assert R._index_blobs(rel) == {rel: head}
    moi = "tests/sandbox/test_calibration_reach.py"
    subprocess.run(["git", "update-index", "--force-remove", moi], cwd=R._ROOT, env=env, check=True)
    tests = dict(R._iter_tests(index=True))
    assert moi not in tests and os.path.exists(os.path.join(R._ROOT, moi)) and len(tests) > 100
    assert all(k.endswith(".py") and k.startswith("tests/") for k in tests)


def test_a_NEW_mute_injected_in_memory_turns_the_gate_RED_while_the_tree_stays_green(monkeypatch, capsys):
    """Contre-exemple GELÉ de la porte 18, calibrée comme un instrument : sur l'arbre courant la porte est verte
    (aucune fausse alarme) ; une déclaration garde-seule NEUVE qu'aucun test n'appelle, injectée EN MÉMOIRE,
    doit la faire ÉCHOUER (code 1) en la NOMMANT."""
    assert R.main([]) == 0
    calibrated = dict(R.load_calibrated())
    calibrated["tools/fantome.py::fn_fantome"] = ["empty-cohort:raises", "guard-before-world"]
    res = R.scan(calibrated=calibrated)
    assert "tools/fantome.py::fn_fantome" in res["muettes"]
    monkeypatch.setattr(R, "scan", lambda index=False: res)
    assert R.main([]) == 1
    assert "[NOUVELLE MUETTE] tools/fantome.py::fn_fantome" in capsys.readouterr().out
