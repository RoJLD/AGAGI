"""Contre-exemples GELÉS du bloc AGAGI:PORTE-ABSENTE de `tools/hooks/pre-commit`.

LE PROBLÈME, MESURÉ LE 2026-09-24. `core.hooksPath` vaut un chemin ABSOLU vers le `.git/hooks` du
dépôt principal : TOUS les worktrees exécutent le MÊME pre-commit, quelle que soit leur branche. Le
jour où l'on déploie une porte nouvelle, chaque worktree dont la branche est ANTÉRIEURE à cette porte
exécute `python tools/check_<porte>.py` sur un fichier qui n'existe pas chez lui. Python rend 2, la
porte lit ce code comme un refus, et TOUS les commits de ce worktree sont bloqués. Cas vivant au
moment du déploiement de la porte 22 : `chantier/pm-portes`, où un implémenteur du PM committait,
avait été coupé avant `tools/check_hook_deployment.py`.

LE REMÈDE, ET POURQUOI IL N'AFFAIBLIT PAS LA GARDE. Une fonction `python()` intercepte UNIQUEMENT les
appels `tools/check_*.py`, et ne saute une porte QUE si elle manque à la fois sur le disque ET dans
HEAD : c'est la signature exacte d'une branche antérieure à la porte. Elle le DIT à voix haute (un
saut silencieux serait la classe E32, une dégradation de périmètre qui ne se dit pas). Une porte
présente dans HEAD mais supprimée sur le disque continue d'échouer : supprimer une garde ne doit pas
suffire à la faire taire. Même technique que la fonction `git()` du bloc AGAGI:FUSION-SCOPE.

Chaque cas bâtit un dépôt JETABLE dans `tmp_path`, environnement `GIT_*` purgé.
"""
import os
import shutil
import subprocess

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PRE_COMMIT = os.path.join(_ROOT, "tools", "hooks", "pre-commit")
_DEBUT = "# >>> AGAGI:PORTE-ABSENTE >>>"
_FIN = "# <<< AGAGI:PORTE-ABSENTE <<<"


def _lire(chemin):
    with open(chemin, encoding="utf-8") as fh:
        return fh.read()


def _bloc():
    src = _lire(_PRE_COMMIT)
    i = src.find(_DEBUT)
    assert i >= 0, f"marqueur « {_DEBUT} » absent de tools/hooks/pre-commit"
    j = src.find(_FIN, i)
    assert j >= 0, f"marqueur « {_FIN} » absent de tools/hooks/pre-commit"
    return src[i:j + len(_FIN)]


def _hook_jouet():
    """Le squelette : le bloc VERBATIM, puis une porte écrite exactement comme celles du vrai hook."""
    return (
        "#!/bin/sh\n"
        "fail=0\n"
        + _bloc() + "\n"
        "PYTHONIOENCODING=utf-8 python tools/check_fantome.py || {\n"
        "  echo \"REFUS DE LA PORTE FANTOME\"\n"
        "  fail=1\n"
        "}\n"
        "exit $fail\n"
    )


_PORTE_QUI_PASSE = (
    "import os, sys\n"
    "print('fantome-execute encodage=' + str(os.environ.get('PYTHONIOENCODING')))\n"
    "sys.exit(0)\n"
)
_PORTE_QUI_REFUSE = "import sys\nprint('fantome-refuse')\nsys.exit(1)\n"


class _Depot:
    def __init__(self, tmp_path, monkeypatch):
        for k in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY"):
            monkeypatch.delenv(k, raising=False)
        if shutil.which("git") is None:
            pytest.skip("git introuvable : le crochet n'est pas mesurable ici")
        self.p = str(tmp_path / "jetable")
        os.makedirs(self.p)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        rc, sortie = self.git("init", "-q", "-b", "base", ".", check=False)
        if rc != 0:
            pytest.skip(f"git refuse d'initialiser un dépôt jetable : {sortie.strip()}")
        hooks = os.path.join(self.p, ".githooks")
        os.makedirs(hooks)
        self.git("config", "core.hooksPath", hooks)
        with open(os.path.join(hooks, "pre-commit"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_hook_jouet())
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)

    def git(self, *args, check=True):
        r = subprocess.run(["git", "-C", self.p, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           capture_output=True, env=self.env)
        sortie = (r.stdout + r.stderr).decode("utf-8", errors="replace")
        if check and r.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} a échoué ({r.returncode}) :\n{sortie}")
        return r.returncode, sortie

    def ecrire(self, rel, texte):
        chemin = os.path.join(self.p, *rel.split("/"))
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texte)

    def commit(self, rel, texte, message):
        self.ecrire(rel, texte)
        self.git("add", "-A")
        return self.git("commit", "-q", "-m", message, check=False)


def _preparer(d, message):
    """Commit de préparation, crochets court-circuités : on construit l'historique, on ne le juge pas."""
    d.git("add", "-A")
    d.git("commit", "-q", "--no-verify", "-m", message)


# --------------------------------------------------------------------------------------------------
# 1. LE CAS QUI MOTIVE LE BLOC : branche antérieure à la porte.
# --------------------------------------------------------------------------------------------------

def test_une_branche_ANTERIEURE_a_la_porte_committe_et_le_hook_le_DIT(tmp_path, monkeypatch):
    d = _Depot(tmp_path, monkeypatch)
    rc, sortie = d.commit("notes.txt", "un\n", "commit ordinaire sur une branche sans la porte")

    assert rc == 0, (
        "une branche qui n'a JAMAIS eu tools/check_fantome.py est bloquée par le hook commun : "
        f"chaque porte ajoutée au hook déployé casserait tous les worktrees plus anciens.\n{sortie}")
    assert "NON vérifiée" in sortie, (
        "la porte a été sautée EN SILENCE : un saut qui ne se dit pas est une dégradation de "
        f"périmètre (E32), indiscernable d'une porte qui a passé.\n{sortie}")
    assert "fantome-execute" not in sortie, f"une porte absente ne peut pas avoir tourné :\n{sortie}"


# --------------------------------------------------------------------------------------------------
# 2. LES CONTRÔLES : le bloc ne doit rien changer quand la porte EXISTE, ni faire taire une suppression.
# --------------------------------------------------------------------------------------------------

def test_controle_une_porte_PRESENTE_qui_passe_tourne_et_recoit_son_encodage(tmp_path, monkeypatch):
    d = _Depot(tmp_path, monkeypatch)
    d.ecrire("tools/check_fantome.py", _PORTE_QUI_PASSE)
    rc, sortie = d.commit("notes.txt", "un\n", "avec la porte")

    assert rc == 0, f"une porte présente qui passe doit laisser passer :\n{sortie}"
    assert "fantome-execute" in sortie, f"la porte présente n'a pas tourné :\n{sortie}"
    assert "encodage=utf-8" in sortie, (
        "PYTHONIOENCODING=utf-8, posé devant l'appel, n'arrive plus au processus python : la fonction "
        f"d'interception a perdu l'environnement de l'appel.\n{sortie}")
    assert "NON vérifiée" not in sortie, f"le bloc accuse une porte qui est là :\n{sortie}"


def test_controle_une_porte_PRESENTE_qui_refuse_bloque_toujours(tmp_path, monkeypatch):
    d = _Depot(tmp_path, monkeypatch)
    d.ecrire("tools/check_fantome.py", _PORTE_QUI_REFUSE)
    rc, sortie = d.commit("notes.txt", "un\n", "avec la porte qui refuse")

    assert rc != 0, (
        f"le code de retour de la porte n'est plus transmis : elle ne peut plus rien refuser.\n{sortie}")
    assert "REFUS DE LA PORTE FANTOME" in sortie, f"le refus ne vient pas de la porte :\n{sortie}"


def test_une_porte_presente_dans_HEAD_mais_SUPPRIMEE_sur_le_disque_bloque_encore(tmp_path, monkeypatch):
    """Le cas qui distingue « branche antérieure » de « garde supprimée » : la porte existe dans
    l'historique de la branche, quelqu'un a retiré le fichier. Le hook doit continuer d'échouer,
    sinon supprimer une garde suffirait à la faire taire."""
    d = _Depot(tmp_path, monkeypatch)
    d.ecrire("tools/check_fantome.py", _PORTE_QUI_PASSE)
    d.ecrire("notes.txt", "base\n")
    _preparer(d, "la porte existe dans l'historique")

    os.remove(os.path.join(d.p, "tools", "check_fantome.py"))
    d.git("add", "-A")
    rc, sortie = d.git("commit", "-q", "-m", "suppression de la porte", check=False)

    assert rc != 0, (
        "une porte présente dans HEAD et supprimée sur le disque a été sautée : retirer un fichier de "
        f"garde suffirait alors à désarmer la garde.\n{sortie}")
    assert "NON vérifiée" not in sortie, (
        f"le bloc a pris une SUPPRESSION pour une branche antérieure à la porte :\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 3. LE FICHIER VERSIONNÉ : le bloc doit précéder la PREMIÈRE porte, sinon il ne protège rien.
# --------------------------------------------------------------------------------------------------

def test_le_bloc_precede_le_premier_appel_de_porte_dans_le_hook_versionne():
    lignes = _lire(_PRE_COMMIT).split("\n")
    debut = [n for n, l in enumerate(lignes) if l.strip() == _DEBUT]
    assert debut, "le bloc AGAGI:PORTE-ABSENTE manque au hook versionné"
    # Premier APPEL réel : une ligne de code (pas un commentaire, pas un echo d'aide) qui lance une porte.
    appels = [n for n, l in enumerate(lignes)
              if "python tools/check_" in l and not l.lstrip().startswith("#")
              and not l.lstrip().startswith("echo")]
    assert appels, "aucun appel de porte trouvé : le motif est faux, ce cas ne mesure rien"
    assert debut[0] < appels[0], (
        f"le bloc (ligne {debut[0] + 1}) est posé APRÈS le premier appel de porte (ligne {appels[0] + 1}) : "
        "les portes d'avant ne sont pas protégées")
