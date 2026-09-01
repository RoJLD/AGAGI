"""Garde EXÉCUTABLE de la classe E10 (occurrences 4 et 5 du 2026-09-01, promotion P2.22) — « hunks
étrangers happés par un commit path-scopé mais pas contenu-scopé ».

Calibration sur la RÉPONSE CONNUE (cf. CLAUDE.md §Calibration des instruments) : ces tests reproduisent
la FORME du cas gelé `e21c1f3` (2026-09-01) — un `git add` path-scopé mais pas contenu-scopé a happé du
travail non committé d'une session parallèle sur `tests/sandbox/test_instrument_calibration.py` — dans un
dépôt git TEMPORAIRE (jamais le dépôt réel), avec le cas POSITIF apparié : seuls MES hunks stagés doit
PASSER. Sans le positif, une garde qui refuse tout serait aussi inutile qu'une garde qui accepte tout.
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.check_staged_authorship import (  # noqa: E402
    snapshot, verify, NoSnapshotError, ForeignHunkDetected)

_FILE = "shared_module.py"


def _git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {args} a échoué : {r.stderr}"
    return r.stdout


def _init_repo(tmp_path):
    """Dépôt git temporaire avec un commit initial portant `shared_module.py` (jamais le dépôt réel)."""
    repo = str(tmp_path)
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    with open(os.path.join(repo, _FILE), "w", encoding="utf-8") as f:
        f.write("def foo():\n    return 1\n")
    _git(["add", _FILE], repo)
    _git(["commit", "-q", "-m", "init"], repo)
    return repo


def _append(repo, text):
    with open(os.path.join(repo, _FILE), "a", encoding="utf-8") as f:
        f.write(text)


def test_verify_without_a_prior_snapshot_is_refused(tmp_path):
    """Sans empreinte, rien n'est comparable — la garde doit le dire, pas laisser passer en silence."""
    repo = _init_repo(tmp_path)
    with pytest.raises(NoSnapshotError):
        verify([_FILE], owner="tache", snapshot_dir=str(tmp_path / "snaps"), cwd=repo)


def test_FORME_e21c1f3_a_foreign_uncommitted_hunk_swept_by_git_add_is_caught(tmp_path):
    """⚠️ LE CŒUR DE LA GARDE — reproduit la forme du cas gelé `e21c1f3` (2026-09-01) :

    1. une session PARALLÈLE édite `shared_module.py` SANS committer (travail étranger, déjà dans
       l'arbre de travail avant que ma tâche ne commence) ;
    2. JE prends mon empreinte (`snapshot`) — elle capture ce contenu étranger + le HEAD réel ;
    3. J'édite le MÊME fichier (mon propre travail) ;
    4. `git add` stage TOUT (mon travail + le hunk étranger, jamais committé) — c'est exactement le
       mécanisme `e21c1f3` : path-scopé, pas contenu-scopé ;
    5. `verify()` doit TIRER et NOMMER le hunk étranger (pas seulement dire non).
    """
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    # 1. session parallèle : hunk étranger, jamais committé.
    _append(repo, "\n\ndef parallel_session_uncommitted():\n    return 'foreign'\n")

    # 2. mon empreinte de départ — capture le hunk étranger ci-dessus + le HEAD réel (juste `foo`).
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # 3. mon propre travail, écrit APRÈS l'empreinte.
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")

    # 4. je stage tout, sans distinguer les hunks (exactement le geste qui a produit e21c1f3).
    _git(["add", _FILE], repo)

    # 5. la garde doit tirer et nommer le hunk étranger.
    with pytest.raises(ForeignHunkDetected) as exc:
        verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    report = exc.value.report
    assert _FILE in report
    foreign_text = "\n".join(l for h in report[_FILE] for l in h["lines"])
    assert "parallel_session_uncommitted" in foreign_text
    assert "'foreign'" in foreign_text
    # le hunk qui EST le mien ne doit PAS apparaître dans le rapport d'ÉTRANGERS.
    assert "my_own_work" not in foreign_text
    # le message doit NOMMER, pas seulement refuser.
    assert "parallel_session_uncommitted" in str(exc.value)


def test_POSITIVE_only_my_own_hunks_staged_PASSES(tmp_path):
    """Cas positif apparié : AUCUN travail étranger dans l'arbre au moment de l'empreinte -> seul MON
    hunk est stagé -> la garde doit PASSER. Sans ce test, une garde qui refuse tout passerait la revue."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    # empreinte prise immédiatement après le commit initial : rien d'étranger dans l'arbre.
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # mon propre travail, écrit après l'empreinte.
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")
    _git(["add", _FILE], repo)

    checked = verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert checked[_FILE] == 1                        # un seul hunk stagé, et il est attribuable


def test_verify_with_nothing_staged_is_a_silent_noop(tmp_path):
    """Un fichier snapshotté mais jamais retouché ni restagé n'a rien à vérifier -> pas d'erreur."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    checked = verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert checked[_FILE] == 0                         # rien de nouveau stagé par rapport au HEAD capturé


def test_different_owners_do_not_share_a_snapshot(tmp_path):
    """Deux tâches sur le même fichier ne doivent pas se marcher dessus : `owner` scope l'empreinte."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="tache-a", snapshot_dir=snap_dir, cwd=repo)
    with pytest.raises(NoSnapshotError):
        verify([_FILE], owner="tache-b", snapshot_dir=snap_dir, cwd=repo)


def test_check_prefix_is_excluded_from_the_instrument_calibration_ratchet():
    """⚠️ Piège de nommage signalé dans la dette P2.22 : ce fichier s'appelle `check_*.py`, donc
    `check_instrument_calibration.scan_instruments` doit l'EXCLURE (comme `check_record_links.py`) —
    sinon cette garde elle-même deviendrait une dette de calibration non calibrée par accident."""
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from tools.check_instrument_calibration import scan_instruments
    found = scan_instruments()
    assert all(not path.endswith("check_staged_authorship.py") for path in found.values())
