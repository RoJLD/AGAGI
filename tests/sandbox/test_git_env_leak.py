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

⚠️ LA FORME DU `GIT_DIR` DÉCIDE DE LA BASCULE (P2.121 famille 6, mesuré le 2026-09-26 sur Linux git 2.43 ET
Windows git 2.54). Un hook ne reçoit JAMAIS `GIT_DIR=<dépôt>/.git` : depuis l'arbre principal il est ABSENT,
depuis un WORKTREE il vaut `<dépôt>/.git/worktrees/<nom>` (absolu, barres obliques, sur les deux plateformes).
Et `git init` réinitialisant un dépôt pointé DEVINE sa nature (`guess_repository_type`) : un chemin qui finit
par « /.git » est jugé non-bare, tout autre est jugé BARE. Le premier témoin injectait `str(a / ".git")` : sous
Windows les antislashs cachaient le suffixe et le dépôt basculait ; sous POSIX le suffixe était vu, rien ne
basculait, et les deux témoins de la famille rougissaient en CI — une preuve fausse pour une conclusion juste
(E33). La forme réelle, le gitdir d'un worktree, fait basculer le dépôt PRINCIPAL sur les deux plateformes :
c'est elle que les cas ci-dessous injectent, et c'est le commit DEPUIS un worktree qui expose la flotte.

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


def _depot_avec_worktree(tmp_path, env):
    """A (un commit vide) et son worktree W : rend (A, le gitdir de W tel que git l'exporte à un hook quand on
    committe DEPUIS W — absolu, barres obliques, jamais suffixé « /.git »)."""
    a = _depot(tmp_path / "A_le_vrai", env)
    for args in (["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base"],
                 ["worktree", "add", "-q", str(tmp_path / "W"), "-b", "w"]):
        r = _git(args, a, env)
        if r.returncode != 0:
            pytest.skip(f"git refuse de préparer le worktree jetable : {(r.stderr or r.stdout).strip()}")
    return a, (a / ".git" / "worktrees" / "W").as_posix()


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
    test croit initialiser. Avec `GIT_DIR` qui fuit — le gitdir d'un WORKTREE de A, la forme exacte qu'un hook
    reçoit quand on committe depuis ce worktree : B ne reçoit AUCUN `.git`, c'est A qui est réinitialisé — et A
    passe à `core.bare = true`, donc son arbre de travail disparaît pour tout le monde. Sur Linux ET Windows."""
    env = _env_nu()
    a, gitdir_w = _depot_avec_worktree(tmp_path, env)
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "false"

    b = tmp_path / "B_le_jetable"
    b.mkdir()
    fuite = dict(env, GIT_DIR=gitdir_w)                      # exactement ce que le hook exporte (commit depuis W)
    r = _git(["init", "-q", "-b", "autre"], b, fuite)

    assert not (b / ".git").exists(), "le repertoire jetable n'a RIEN recu : le test croyait operer sur lui"
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "true", (
        "le depot POINTE est passe en bare : son arbre de travail disparait pour toutes les sessions")
    assert "must be run in a work tree" in (_git(["status"], a, env).stderr or "").lower() + \
           (_git(["status"], a, env).stdout or "").lower()
    # EMPREINTE cherchable, mesurée par agagi-52 : une garde à coût nul peut refuser toute sortie qui la porte.
    assert "re-init" in (r.stdout + r.stderr).lower() or "reinitialized" in (r.stdout + r.stderr).lower()


def test_un_GIT_DIR_suffixe_point_git_DETOURNE_aussi_mais_ne_fait_PAS_basculer_le_depot(tmp_path):
    """SPÉCIFICITÉ de la forme, et pourquoi le premier témoin rougissait sur POSIX : avec `GIT_DIR=<A>/.git` en
    barres obliques, le `git init` est TOUJOURS détourné (B ne reçoit rien : une écriture de config qui suivrait
    atterrirait dans A) — mais git devine « non-bare » pour ce suffixe, et A garde son arbre de travail. Le danger
    de détournement ne dépend pas de la forme ; la bascule `bare`, si."""
    env = _env_nu()
    a = _depot(tmp_path / "A_le_vrai", env)
    b = tmp_path / "B_le_jetable"
    b.mkdir()
    _git(["init", "-q", "-b", "autre"], b, dict(env, GIT_DIR=(a / ".git").as_posix()))
    assert not (b / ".git").exists(), "le git init doit etre detourne vers A, quelle que soit la forme"
    assert _git(["config", "core.bare"], a, env).stdout.strip() == "false"


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
