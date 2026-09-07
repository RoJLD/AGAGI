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
