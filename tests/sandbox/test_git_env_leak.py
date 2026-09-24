"""CONTRE-EXEMPLE GELÉ de la fixture `_env_git_neutralise` (tests/conftest.py) — E5, 2026-09-24.

Ce qui s'est produit, deux fois : pendant un `git commit`, git exporte `GIT_DIR` vers le hook et vers tous ses
sous-processus, donc vers `pytest`. Un test qui lance `git init` dans un répertoire jetable, en héritant de ce
`GIT_DIR` et sans `GIT_WORK_TREE`, ne crée AUCUN dépôt dans son répertoire : il RÉINITIALISE le dépôt pointé et
y pose `core.bare = true`. Le dépôt réel devient alors sans arbre de travail pour toutes les sessions
(`git status` → « must be run in a work tree »), et un `git config user.email` posé dans la foulée écrase
l'identité du vrai dépôt.

Ces cas mesurent le mécanisme sur DEUX VRAIS dépôts jetables (jamais sur le dépôt du projet), dans les deux
sens : avec l'environnement qui fuit, l'accident se produit ; avec l'environnement nettoyé, il ne se produit
pas. Plus la SPÉCIFICITÉ (un test qui pose délibérément une variable la garde) et l'EMPREINTE textuelle que
l'accident laisse dans la sortie de git.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde.
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True


def _git(args, cwd, env):
    return subprocess.run(["git"] + args, cwd=str(cwd), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _depot(chemin, env):
    """Un VRAI dépôt (jetable) : c'est ce que le mécanisme exige — un `GIT_DIR` inventé ne mesurerait rien."""
    chemin.mkdir(parents=True, exist_ok=True)
    r = _git(["init", "-q", "-b", "base"], chemin, env)
    if r.returncode != 0:
        pytest.skip(f"git refuse d'initialiser un dépôt jetable : {(r.stderr or r.stdout).strip()}")
    return chemin


def _env_nu():
    """L'environnement du processus courant, dont la fixture a DÉJÀ retiré les `GIT_*`."""
    return {k: v for k, v in os.environ.items()}


def test_la_fixture_a_retire_toute_la_famille_GIT_de_l_environnement():
    """Premier sens : la fixture fait ce qu'elle dit. Sans ce cas, tout le reste du fichier pourrait passer
    sur un environnement qui n'a jamais contenu de `GIT_*`, et ne mesurerait rien."""
    assert [k for k in os.environ if k.startswith("GIT_")] == []


def test_un_test_qui_pose_lui_meme_une_variable_la_GARDE(monkeypatch):
    """SPÉCIFICITÉ : la fixture nettoie AVANT le test, elle n'interdit rien pendant. Un test qui a besoin de
    `GIT_INDEX_FILE` (ex. `check_backlog_freshness._en_commit`) continue de fonctionner."""
    monkeypatch.setenv("GIT_INDEX_FILE", "un/chemin/a/moi")
    assert os.environ["GIT_INDEX_FILE"] == "un/chemin/a/moi"


def test_un_GIT_DIR_herite_detourne_le_git_init_vers_le_depot_POINTE(tmp_path):
    """LE MÉCANISME, sur deux vrais dépôts jetables. `A` joue le dépôt du projet, `B` le répertoire que le
    test croit initialiser. Avec `GIT_DIR` qui fuit : B ne reçoit AUCUN `.git`, et c'est A qui est
    réinitialisé — et A passe à `core.bare = true`, donc son arbre de travail disparaît pour tout le monde."""
    env = _env_nu()
    a = _depot(tmp_path / "A_le_vrai", env)
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "false"

    b = tmp_path / "B_le_jetable"
    b.mkdir()
    fuite = dict(env, GIT_DIR=str(a / ".git"))              # exactement ce que le hook exporte
    r = _git(["init", "-q", "-b", "autre"], b, fuite)

    assert not (b / ".git").exists(), "le repertoire jetable n'a RIEN recu : le test croyait operer sur lui"
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "true", (
        "le depot POINTE est passe en bare : son arbre de travail disparait pour toutes les sessions")
    assert "must be run in a work tree" in (_git(["status"], a, env).stderr or "").lower() + \
           (_git(["status"], a, env).stdout or "").lower()
    # EMPREINTE cherchable, mesurée par agagi-52 : une garde à coût nul peut refuser toute sortie qui la porte.
    assert "re-init" in (r.stdout + r.stderr).lower() or "reinitialized" in (r.stdout + r.stderr).lower()


def test_avec_l_environnement_NETTOYE_le_meme_git_init_cree_bien_son_depot(tmp_path):
    """L'autre sens, et c'est ce que la fixture achète : à environnement nettoyé, le même appel crée le dépôt
    DANS le répertoire jetable et ne touche pas au dépôt A. Sans ce cas, une fixture qui casserait `git init`
    passerait le test précédent."""
    env = _env_nu()
    a = _depot(tmp_path / "A_le_vrai", env)
    b = tmp_path / "B_le_jetable"
    b.mkdir()
    r = _git(["init", "-q", "-b", "autre"], b, env)         # AUCUN GIT_* : c'est l'etat que la fixture garantit
    assert r.returncode == 0 and (b / ".git").exists(), "le depot jetable doit naitre dans B"
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "false", "A n'est pas touche"
    assert _git(["rev-parse", "--show-toplevel"], a, env).returncode == 0


def test_l_identite_ecrite_apres_un_init_detourne_ecrase_celle_du_depot_POINTE(tmp_path):
    """Troisième conséquence, mesurée par agagi-52 et à l'origine des commits signés `Test` de P2.86 : le
    `git config user.email` qu'un test pose après son init atterrit dans le dépôt RÉEL."""
    env = _env_nu()
    a = _depot(tmp_path / "A_le_vrai", env)
    _git(["config", "user.email", "vrai@proprietaire.fr"], a, env)
    b = tmp_path / "B_le_jetable"
    b.mkdir()
    fuite = dict(env, GIT_DIR=str(a / ".git"))
    _git(["init", "-q", "-b", "autre"], b, fuite)
    _git(["config", "user.email", "test@example.com"], b, fuite)
    assert _git(["config", "user.email"], a, env).stdout.strip() == "test@example.com", (
        "l'identite du depot REEL est ecrasee par celle du test")
