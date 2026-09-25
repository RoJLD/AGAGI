"""Calibration du cliquet de calibration LUI-MÊME sur les COLLISIONS de noms (2026-09-06).

Défaut trouvé par le réfutateur de la famille run_* : `scan_calibrated` faisait `out.add(bare)` pour une
déclaration QUALIFIÉE `fichier::fonction` — le NOM NU entrait dans l'ensemble des calibrés, donc TOUS les
homonymes étaient verdis dès qu'UN chemin était déclaré. Déclarer `tools/ablation.py::run_condition`
aurait verdi `tools/s2_demand.py::run_condition`, jamais gardé : un faux vert E4 fabriqué par la passe de
calibration elle-même. Même trou pour `NOT_AN_INSTRUMENT` qualifié (déclarer `is_machine_idle::verdict`
non-instrument exemptait `eval_harness::verdict`).

Ces tests gèlent la sémantique corrigée sur la fonction PURE `collision_coverage` : un nom en collision
n'est couvert que si CHAQUE chemin porte une déclaration qualifiée (calibrée OU non-instrument).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_instrument_calibration as M  # noqa: E402
from tools.check_instrument_calibration import collision_coverage  # noqa: E402

_COLL = {"run_condition": ["tools/ablation.py", "tools/ablation_multi.py", "tools/s2_demand.py"]}


def test_a_single_qualified_declaration_does_NOT_cover_the_whole_collision():
    """⚠️ CONTRE-EXEMPLE GELÉ — la configuration exacte du défaut : UN chemin déclaré sur trois."""
    ok, manquants = collision_coverage(_COLL, {"run_condition": ["tools/ablation.py"]}, {})["run_condition"]
    assert ok is False
    assert manquants == ["tools/ablation_multi.py", "tools/s2_demand.py"]


def test_all_paths_declared_calibrated_covers_the_collision():
    """Contrôle positif : les trois chemins déclarés -> couvert, aucun manquant."""
    ok, manquants = collision_coverage(
        _COLL, {"run_condition": ["tools/ablation.py", "tools/ablation_multi.py", "tools/s2_demand.py"]},
        {})["run_condition"]
    assert ok is True and manquants == []


def test_a_qualified_NOT_AN_INSTRUMENT_counts_toward_coverage():
    """Un homonyme déclaré NON-instrument (qualifié) couvre SON chemin — c'est le cas réel
    `is_machine_idle::verdict` (non-instrument) + `eval_harness::verdict` (calibré)."""
    coll = {"verdict": ["src/seed_ai/eval_harness.py", "tools/is_machine_idle.py"]}
    ok, manquants = collision_coverage(coll, {"verdict": ["src/seed_ai/eval_harness.py"]},
                                       {"verdict": ["tools/is_machine_idle.py"]})["verdict"]
    assert ok is True and manquants == []


def test_backslash_paths_are_normalised_before_comparison():
    """Windows : un chemin déclaré avec des antislashs doit compter (le dépôt tourne sous Git Bash)."""
    ok, _ = collision_coverage({"f": ["tools/a.py", "tools/b.py"]},
                               {"f": ["tools\\a.py", "tools/b.py"]}, {})["f"]
    assert ok is True


# --------------------------------------------------------------------------------------------------
# 2026-09-09 — TROU TROUVE PAR `tools/check_gate_mutation.py`. Tout ce fichier testait
# `collision_coverage`, la fonction PURE qui décide si une collision est COUVERTE — et rien ne testait
# `scan_collisions`, celle qui la DÉTECTE. Remplacer son corps par `return {}` laissait les quatre
# tests verts : les collisions redevenaient invisibles, donc déclarer calibré un nom en collision
# aurait de nouveau verdi des homonymes jamais testés — le faux vert E4 que ce fichier existe pour
# fermer. Le SECOND maillon de la chaîne était gardé, le PREMIER ne l'était pas.
# --------------------------------------------------------------------------------------------------

_FAUX_ARBRE = [
    ("tools/a.py", "def run_probe():\n    return 1\n"),
    ("tools/b.py", "def run_probe():\n    return 2\n"),
    ("tools/c.py", "def run_unique():\n    return 3\n"),
]


def test_scan_collisions_SEES_a_name_defined_in_TWO_files(monkeypatch):
    """CONTRE-EXEMPLE GELE de la porte 2, à DOSE CONNUE : un arbre factice de trois sources dont
    exactement une paire est en collision. L'injection remplace `_iter_sources` — la couche qui LIT
    l'arbre — pour que le test porte sur la couche qui IDENTIFIE, à coût de balayage nul."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    coll = M.scan_collisions()
    assert coll == {"run_probe": ["tools/a.py", "tools/b.py"]}, (
        "le nom defini DEUX fois doit sortir avec ses DEUX chemins, et lui seul", coll)


def test_scan_collisions_is_SILENT_when_every_name_is_UNIQUE(monkeypatch):
    """SPECIFICITE (no-op apparié). Sans lui, un détecteur qui déclare TOUT en collision passerait le
    test précédent — et rendrait le cliquet inutilisable en criant sur 200 fichiers."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE[1:]))
    assert M.scan_collisions() == {}


# --------------------------------------------------------------------------------------------------
# P2.83 (2026-09-24) — NEUVIÈME angle mort : une déclaration `CALIBRATED` que le cliquet ne détecte pas
# tombait dans une branche « déclaration périmée » et était ignorée EN SILENCE. Mesuré sur l'arbre :
# 9 déclarations y tombaient et AUCUNE n'était périmée — 6 fonctions présentes qu'aucun des 14 motifs
# ne voit (dont `_cause_de_mort`, nommage FRANÇAIS) et 3 CLASSES (le cliquet ne scanne que `def`).
# L'auteur croyait avoir déclaré ; rien ne le contredisait (E10 appliquée au cliquet lui-même). Les
# remèdes sont OPPOSÉS selon la cause — élargir un motif, étendre aux classes, ou supprimer une
# déclaration morte — donc le cri doit TRANCHER, et ces cas gèlent qu'il tranche juste.
# --------------------------------------------------------------------------------------------------

_ARBRE_CAUSES = [
    ("tools/x.py", "def presente_mais_invisible():\n    return 1\n"),
    ("tools/y.py", "class UneClasse(Base):\n    pass\n"),
    ("tools/z.py", "class SansBase:\n    pass\n"),
]


def test_la_CAUSE_d_une_declaration_ignoree_est_TRANCHEE_et_pas_devinee(monkeypatch):
    """Trois réponses CONNUES, trois remèdes opposés : un `def` présent (élargir un motif), une `class`
    (le cliquet ne scanne que `def`), un symbole absent (supprimer la déclaration morte)."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_ARBRE_CAUSES))
    assert M._cause_ignoree("presente_mais_invisible") == ("MOTIF_AVEUGLE", ["tools/x.py"])
    assert M._cause_ignoree("UneClasse") == ("CLASSE", ["tools/y.py"])
    assert M._cause_ignoree("SansBase") == ("CLASSE", ["tools/z.py"]), "`class C:` sans parenthèses compte aussi"
    assert M._cause_ignoree("jamais_ecrite") == ("PERIMEE", [])


def test_une_declaration_non_detectee_est_RAPPORTEE_avec_sa_cause_jamais_avalee(monkeypatch, tmp_path):
    """Le contre-exemple de la branche silencieuse : `scan_calibrated` doit PUBLIER ce qu'il ignore.
    Sans ce cas, remplacer le cri par `continue` repasserait tous les autres tests du fichier."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_ARBRE_CAUSES))
    monkeypatch.setattr(M, "scan_instruments", lambda: {"presente_mais_invisible": "tools/x.py"})
    monkeypatch.setattr(M, "scan_collisions", lambda: {})
    faux = tmp_path / "test_instrument_calibration.py"
    faux.write_text("\n".join([
        "CALIBRATED = {",
        '    "presente_mais_invisible": ["cas"],',      # détectée : elle compte
        '    "tools/y.py::UneClasse": ["cas"],',        # CLASSE : ignorée, à crier
        '    "jamais_ecrite": ["cas"],',                # PÉRIMÉE : ignorée, à crier
        "}",
        "",
    ]), encoding="utf-8")
    monkeypatch.setattr(M, "_CALIB_TESTS", str(faux))
    assert M.scan_calibrated() == {"presente_mais_invisible"}
    ignorees = M.scan_calibrated.ignorees
    assert set(ignorees) == {"tools/y.py::UneClasse", "jamais_ecrite"}, ignorees
    assert ignorees["tools/y.py::UneClasse"][0] == "CLASSE"
    assert ignorees["jamais_ecrite"][0] == "PERIMEE"
