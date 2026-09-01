"""Contre-exemples GELÉS du cliquet de fraîcheur du backlog — il doit pouvoir ÉCHOUER.

Sans ces tests, `tools/check_backlog_freshness.py` serait un outil qui passe au vert quoi qu'il arrive :
exactement le défaut qu'il est censé empêcher ailleurs.

Chaque test forge un backlog minimal contenant UNE péremption connue, et vérifie que le cliquet la voit.
Le dernier vérifie l'inverse — un backlog sain ne doit rien déclencher — parce qu'un détecteur qui
signale tout passerait les autres tests tout en étant inutilisable.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_backlog_freshness as B  # noqa: E402


def _backlog(tmp_path, monkeypatch, texte):
    p = tmp_path / "BACKLOG.md"
    p.write_text(texte, encoding="utf-8")
    monkeypatch.setattr(B, "_BACKLOG", str(p))
    return p


def test_a_dead_record_link_is_DETECTED(tmp_path, monkeypatch):
    """⚠️ Citer un record qui n'existe pas : le lecteur suit un renvoi vers le vide."""
    _backlog(tmp_path, monkeypatch, "Voir [[EDR-NEXISTE-PAS-999]] pour le détail.\n")
    trouve = B.scan()
    assert any(k.startswith("lien-mort:") for k in trouve), (
        f"un lien de record mort doit être détecté, or : {trouve}")


def test_a_real_record_link_is_SPARED(tmp_path, monkeypatch):
    """Spécificité : un renvoi valide ne doit PAS être signalé."""
    _backlog(tmp_path, monkeypatch, "Mesuré par [[EDR-EVO-010]], sans appel.\n")
    assert not any(k.startswith("lien-mort:") for k in B.scan()), (
        "un record qui existe ne doit pas être signalé comme lien mort")


def test_memory_slugs_are_NOT_treated_as_records(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ (2026-09-01) : deux espaces de noms cohabitent dans les `[[...]]`. Les slugs de
    mémoire de session (kebab minuscule) vivent hors du dépôt ; les signaler comme records manquants
    exigeait qu'un fichier existe là où la convention dit qu'il n'existe pas."""
    _backlog(tmp_path, monkeypatch, "Recoupe [[warm-start-transversal-law]] et [[s2-world-demand-thread]].\n")
    assert B.scan() == {}, "les slugs de mémoire ne sont pas des records et ne doivent rien déclencher"


def test_a_duplicated_task_number_is_DETECTED(tmp_path, monkeypatch):
    """Deux entrées sous le même numéro : l'une est forcément périmée et rien ne dit laquelle."""
    _backlog(tmp_path, monkeypatch,
             "**P2.4 — première version, présentée comme ouverte.**\n\n"
             "**P2.4 — ✅ FAIT, deuxième version.**\n")
    assert "numero-double:P2.4" in B.scan()


def test_a_dead_file_path_is_DETECTED(tmp_path, monkeypatch):
    """Un backlog qui pointe un fichier disparu envoie le lecteur dans le vide."""
    _backlog(tmp_path, monkeypatch, "Le correctif vit dans `tools/ce_fichier_nexiste_pas.py`.\n")
    assert any(k.startswith("chemin-mort:") for k in B.scan())


def test_an_existing_file_path_is_SPARED(tmp_path, monkeypatch):
    """Spécificité du volet chemins."""
    _backlog(tmp_path, monkeypatch, "Le cliquet vit dans `tools/check_backlog_freshness.py`.\n")
    assert not any(k.startswith("chemin-mort:") for k in B.scan())


def test_a_clean_backlog_triggers_NOTHING(tmp_path, monkeypatch):
    """⚠️ Sans ce test, un détecteur qui signale TOUT passerait tous les autres."""
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — une tâche unique.**\n\nMesuré par [[EDR-EVO-010]], code dans "
             "`tools/check_backlog_freshness.py`.\n")
    assert B.scan() == {}, "un backlog sain ne doit rien déclencher"


def test_the_real_backlog_has_no_NEW_staleness():
    """L'état gelé du dépôt. Si ce test tombe, une péremption mécanique vient d'être introduite."""
    base = B._load_baseline()
    nouvelles = {k: v for k, v in B.scan().items() if k not in base}
    assert not nouvelles, (
        f"nouvelles péremptions du backlog : {nouvelles}. Corriger, ou les déclarer explicitement "
        f"avec `--update-baseline` en disant POURQUOI.")
