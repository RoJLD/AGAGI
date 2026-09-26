"""Témoins de tools/ci_diff_failed.py sur deux logs JOUETS à réponse connue (aucun appel à gh, aucun réseau).

Les formes sont celles mesurées dans les vrais logs d'Actions du 2026-09-26 : préfixe d'horodatage, résumé court
`FAILED <nodeid> - <raison>`, et bilans imbriqués (un test qui lance pytest en sous-processus écrit son propre
« 1 passed in 0.01s » AVANT le bilan final)."""
import json

from tools import ci_diff_failed as C

_T = "2026-09-26T09:05:08.7977866Z "

REF = "\n".join([
    _T + "tests/sandbox/test_a.py ..F.",
    _T + "E             1 passed in 0.01s",
    _T + "  1 passed in 0.01s",
    _T + "FAILED tests/sandbox/test_a.py::test_part - AssertionError: x",
    _T + "FAILED tests/sandbox/test_b.py::test_reste[cas-1] - ValueError",
    _T + "ERROR tests/sandbox/test_c.py",
    _T + "3 failed, 100 passed, 10 skipped, 34 warnings, 1 error in 802.14s (0:13:22)",
])
RUN = "\n".join([
    _T + "FAILED tests/sandbox/test_b.py::test_reste[cas-1] - ValueError",
    _T + "FAILED tests/sandbox/test_instrument_calibration.py::test_neuf - AssertionError",
    _T + "2 failed, 105 passed, 12 skipped, 1 xfailed, 34 warnings in 810.00s (0:13:30)",
])


def test_reponse_connue_nouveaux_disparus_erreurs_et_calibration():
    d = C.difference(RUN, REF)
    assert d["nouveaux"] == ["tests/sandbox/test_instrument_calibration.py::test_neuf"]
    assert d["disparus"] == ["tests/sandbox/test_a.py::test_part"]
    assert d["erreurs_nouvelles"] == [] and d["erreurs_disparues"] == ["tests/sandbox/test_c.py"]
    assert d["calibration"] == ["tests/sandbox/test_instrument_calibration.py::test_neuf"]
    assert d["bilan"] == {"failed": 2, "passed": 105, "skipped": 12, "xfailed": 1, "warnings": 34}
    assert d["bilan_ref"] == {"failed": 3, "passed": 100, "skipped": 10, "warnings": 34, "errors": 1}


def test_le_bilan_final_l_emporte_sur_les_bilans_IMBRIQUES():
    """Un test qui lance pytest écrit « 1 passed in 0.01s » dans le log : le bilan retenu est le DERNIER."""
    assert C.lire_bilan(REF)["passed"] == 100


def test_NO_OP_un_run_contre_lui_meme_ne_rend_AUCUNE_difference():
    d = C.difference(REF, REF)
    assert d["nouveaux"] == d["disparus"] == d["erreurs_nouvelles"] == d["erreurs_disparues"] == []
    assert d["bilan"] == d["bilan_ref"]


def test_un_log_SANS_bilan_rend_None_et_le_DIT_jamais_zero():
    """Job interrompu ou pas fini : pas de ligne de bilan. Le module ne fabrique pas « 0 failed »."""
    partiel = _T + "tests/sandbox/test_a.py ..F."
    assert C.lire_bilan(partiel) is None
    texte = C.rapport(C.difference(partiel, REF))
    assert "ILLISIBLE" in texte
    assert "écarts" not in texte, "aucun écart ne se calcule contre un bilan absent"


def test_le_rapport_nomme_chaque_rouge_et_publie_les_ecarts():
    texte = C.rapport(C.difference(RUN, REF), "run B", "run A")
    assert "écarts : failed -1, passed +5, skipped +2" in texte
    assert "--- NOUVEAUX rouges (1) :" in texte and "  tests/sandbox/test_instrument_calibration.py::test_neuf" in texte
    assert "--- DISPARUS (1) :" in texte and "  tests/sandbox/test_a.py::test_part" in texte


def test_main_hors_ligne_sur_deux_fichiers(tmp_path, capsys):
    a, b = tmp_path / "run.log", tmp_path / "ref.log"
    a.write_text(RUN, encoding="utf-8")
    b.write_text(REF, encoding="utf-8")
    assert C.main(["--log", str(a), "--log-ref", str(b), "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["disparus"] == ["tests/sandbox/test_a.py::test_part"]


def test_main_REFUSE_un_fichier_absent_sans_lever(tmp_path, capsys):
    assert C.main(["--log", str(tmp_path / "absent.log"), "--log-ref", str(tmp_path / "absent2.log")]) == 2
    assert "REFUS" in capsys.readouterr().err
