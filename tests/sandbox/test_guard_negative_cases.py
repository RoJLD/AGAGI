"""Contre-exemples GELÉS du cliquet des gardes — il doit pouvoir ÉCHOUER.

Ce fichier est la garde de la garde. `tools/check_guard_negative_cases.py` vérifie que chaque classe
d'erreur `exécutable` nomme le test qui prouve qu'elle sait refuser. Sans les tests ci-dessous, ce
cliquet serait exactement ce qu'il dénonce : un outil qui passe au vert quoi qu'il arrive.

⚠️ Les trois derniers tests sont les contre-exemples des DÉFAUTS RÉELS trouvés en construisant l'outil
(2026-09-01). Chacun est un faux positif qu'il produisait et qui a été mesuré, pas imaginé :

* de la PROSE technique entre backticks (`argmax`, `throw`, `lr`) était comptée comme un artefact
  manquant -> 7 classes saines déclarées creuses ;
* la citation `fichier.py:163`, forme courante du registre, n'était pas reconnue comme un chemin ;
* les noms de test en MAJUSCULES d'emphase (`..._REFUSES_...`) — la convention même du dépôt —
  étaient invisibles au motif d'identifiant.

C'est la boucle d'auto-amélioration du dépôt : tout bug d'instrument trouvé devient un cas gelé, donc
il ne peut plus repasser silencieusement.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_guard_negative_cases as G  # noqa: E402

_ENTETE = "| # | Classe d'erreur | Occurrences | Statut | Garde |\n|---|---|---|---|---|\n"


def _registre(tmp_path, monkeypatch, lignes):
    p = tmp_path / "REGISTRE.md"
    p.write_text(_ENTETE + "\n".join(lignes) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "_REGISTRE", str(p))
    return p


def test_the_ratchet_can_FAIL_on_a_guard_that_names_no_test(tmp_path, monkeypatch):
    """⚠️ LE test. Une garde `exécutable` qui ne pointe aucun test DOIT être signalée.

    S'il tombe, le cliquet ne garde plus rien et la couverture affichée par le registre est fictive."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | `assert_positive_control` |",
    ])
    creuses = G.scan()
    assert "E99" in creuses, "une garde sans test nommé doit être signalée — le cliquet est aveugle"
    assert "CONTRE-EXEMPLE NON NOMME" in creuses["E99"]


def test_the_ratchet_SPARES_a_row_that_names_its_test(tmp_path, monkeypatch):
    """Spécificité : une ligne bien formée ne doit PAS être signalée. Sans ce test, un cliquet qui
    signale TOUT passerait le test précédent tout en étant inutilisable."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | `assert_positive_control` · "
        "contre-exemple GELÉ : `test_positive_control_catches_incapable_arm` |",
    ])
    assert "E99" not in G.scan(), "une garde qui nomme son contre-exemple ne doit pas être signalée"


def test_a_documented_class_is_not_required_to_name_a_test(tmp_path, monkeypatch):
    """Le cliquet ne porte QUE sur `exécutable`. Une classe `documenté` ou `non automatisable` assume
    de ne pas avoir de garde — la signaler serait exiger l'impossible et ferait baisser les statuts."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `documenté` | prose sans artefact |",
        "| **E98** | Classe bidon | occurrence | **`non automatisable`** | revue humaine |",
    ])
    creuses = G.scan()
    assert creuses == {}, f"seules les classes `exécutable` sont concernées, or : {creuses}"


def test_an_executable_class_naming_nothing_at_all_is_flagged(tmp_path, monkeypatch):
    """Le statut `exécutable` sans le moindre artefact nommé est purement déclaratif."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | il faut faire attention |",
    ])
    assert "NON NOMMEE" in G.scan().get("E99", "")


def test_a_renamed_guard_is_flagged_as_missing(tmp_path, monkeypatch):
    """Une garde renommée ou supprimée doit être vue : c'est la dérive silencieuse du registre."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | `assert_qui_nexiste_nulle_part` |",
    ])
    assert "INTROUVABLE" in G.scan().get("E99", "")


# --- contre-exemples des DÉFAUTS RÉELS de l'instrument (cf. docstring) ---------------------------

def test_prose_backticks_are_not_mistaken_for_missing_artifacts(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ : exiger que TOUS les termes backtickés existent déclarait creuses 7 classes
    saines, parce que la colonne cite aussi de la prose technique (`argmax`, `throw`, `lr`)."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | la garde porte sur `argmax` et non "
        "sur `throw`, quel que soit `lr` · `assert_positive_control` · contre-exemple GELÉ : "
        "`test_positive_control_catches_incapable_arm` |",
    ])
    assert "E99" not in G.scan(), "la prose technique ne doit pas être comptée comme artefact manquant"


def test_a_file_line_citation_is_recognised(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ : `test_instrument_calibration.py:163` — la forme `fichier:ligne` est courante
    dans ce registre et n'était pas reconnue comme un chemin, donc E19 restait signalée à tort."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | `tools/experiment_preflight.py` · "
        "contre-exemple : `test_instrument_calibration.py:163` |",
    ])
    assert "E99" not in G.scan(), "une citation `fichier.py:ligne` doit être reconnue"


def test_uppercase_emphasis_in_test_names_is_recognised(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ : le motif d'identifiant n'acceptait que des minuscules, alors que la convention
    du dépôt met l'emphase en capitales — le contre-exemple le mieux nommé du registre était invisible."""
    _registre(tmp_path, monkeypatch, [
        "| **E99** | Classe bidon | occurrence | `exécutable` | `assert_positive_control` · "
        "contre-exemple GELÉ : `test_optimizer_sweep_REFUSES_the_retain_compose_null` |",
    ])
    assert "E99" not in G.scan(), "un nom de test avec majuscules d'emphase doit être reconnu"


def test_the_real_registry_is_and_stays_clean():
    """L'état gelé du dépôt : 0 garde `exécutable` sans contre-exemple nommé.

    Le baseline est à ZÉRO — aucune dette légataire tolérée. Si ce test tombe, une classe a été
    ajoutée ou modifiée sans pointer sa preuve."""
    creuses = G.scan()
    assert creuses == {}, (
        f"garde(s) `exécutable` sans contre-exemple nommé : {creuses}. "
        f"Nommer le test discriminant dans la colonne « Garde » du registre.")
