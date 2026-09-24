"""
tests/sandbox/test_harness_run_r1.py — contre-exemples de la garde `--rule` de `tools/harness/run_r1.py
::main` (finding de re-revue : la garde est CORRECTE dans le code mais AUCUN test ne la couvrait --
aucun fichier de test du dépôt ne référençait `run_r1`, donc rien ne prouvait qu'elle puisse ÉCHOUER).

Trois cas, AUCUN n'exécute de cellule (aucun entraînement, aucune construction de tâche/learner) : la
garde et les erreurs de nom lèvent AVANT toute construction.
  1. `--rule` en dernier argument de argv -- la garde `if i + 1 >= len(argv)` lève AVANT tout `verify()`.
  2. `--rule` suivi d'un nom de règle qui n'a jamais été scellée -- l'erreur remonte de
     `tools.preregister.verify` (`FileNotFoundError`, jamais une erreur inventée par `run_r1`), preuve
     que le nom EST pris de la ligne de commande et transmis tel quel.
  3. une cellule inconnue sur une règle qui EXISTE (`HARNESS-R1-ter`, scellée sur disque, donc `verify`
     passe) -- c'est `rule["cellules"]["Z"]` qui lève un `KeyError` nommant la cellule, avant
     `_TASKS["Z"]()` et toute construction de `ConnectomeLearner`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.harness.run_r1 import main  # noqa: E402


def test_rule_as_last_argument_raises_before_any_verify():
    """`argv = ["--rule"]` : `i + 1 >= len(argv)` est vrai immédiatement, donc la garde lève avant
    `verify()` -- aucun sceau n'est même tenté. Le message doit nommer l'option ET dire qu'un argument
    est requis (pas juste "--rule" isolé, qui ne prouverait rien sur le CONTENU du message)."""
    with pytest.raises(ValueError) as excinfo:
        main(["--rule"])
    msg = str(excinfo.value)
    assert "--rule" in msg
    assert "requiert" in msg and "argument" in msg


def test_unknown_rule_name_is_passed_through_to_verify_untouched():
    """Le nom de règle n'est jamais validé par `run_r1` lui-même -- il est transmis TEL QUEL à
    `tools.preregister.verify`, qui lève `FileNotFoundError` pour une règle jamais scellée. Si `run_r1`
    inventait ou tronquait le nom, ce test échouerait (match sur le nom exact fourni sur la ligne de
    commande)."""
    with pytest.raises(FileNotFoundError, match="HARNESS-R1-inexistante"):
        main(["--rule", "HARNESS-R1-inexistante"])


def test_unknown_cell_raises_keyerror_before_any_task_or_learner_construction():
    """`HARNESS-R1-ter` existe sur disque : `verify()` et `declare_design()` passent (aucune cellule
    n'est encore lue). C'est la première itération de la boucle, `rule["cellules"]["Z"]`, qui lève un
    `KeyError` -- avant `_TASKS["Z"]()` (qui lèverait un `KeyError` différent) et avant toute
    construction de `ConnectomeLearner` : aucune cellule ne s'exécute."""
    with pytest.raises(KeyError, match="Z"):
        main(["--rule", "HARNESS-R1-ter", "Z"])
