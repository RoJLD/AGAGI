"""P2.142 — GARDE DES ARBRES : pendant une session pytest, aucune entrée de `sys.path` ne pointe vers un AUTRE arbre du
même dépôt (même git-common-dir), et aucun module `tools.*` / `src.*` n'est chargé depuis un autre arbre.

Pourquoi (mesuré par la session E34 le 2026-09-28, P2.142) : dans un worktree, `pytest test_instrument_calibration.py
test_e34_identity_cell.py` finissait avec la racine de l'arbre PRINCIPAL en tête de `sys.path`, en deux graphies à
« c: » minuscule. `tools` étant un paquet-espace-de-noms (pas de fichier d'initialisation), tout import paresseux d'un
`tools.*` y prenait alors la version de l'arbre principal : un test de worktree pouvait passer au VERT en exerçant le
code d'un autre arbre — l'objet vérifié n'est pas l'objet consommé (E35).

Deux rôles, à ne pas confondre (Master 2) : l'ÉCRIVAIN initial met le premier un autre arbre dans `sys.path` ; un
PROPAGATEUR est un module lui-même chargé depuis cet autre arbre, qui insère la racine tirée de son `__file__` — le
motif `if _ROOT not in sys.path: sys.path.insert(0, _ROOT)` compare des CHAÎNES, donc une graphie différente de la même
racine passe (barres obliques d'un chemin rendu par git, antislashs d'un `os.path.abspath`). La garde vise l'ENTRÉE et
le module CONSOMMÉ, quel que soit leur écrivain.

Décisions :
  * propriétaire d'un chemin = la racine d'arbre la plus LONGUE qui le contient, après `normcase` + `realpath` : les
    worktrees vivent SOUS la racine principale (`.worktrees/…`), et la graphie ne doit rien changer ;
  * '' et les chemins relatifs suivent le cwd de l'instant (un `chdir` vers un autre arbre les y emmène) ;
  * les racines viennent de `git worktree list`, lancé avec l'environnement `GIT_*` RETIRÉ : on liste les arbres du
    dépôt désigné par le cwd, jamais celui qu'un commit en cours exporte (règle à deux faces, E5) — lister ne dépend
    pas de l'index ;
  * sans git, ou hors dépôt, la garde est INERTE et le DIT (une ligne), elle ne prétend rien ;
  * REFUS = `pytest.exit(…, returncode=4)` : la session s'arrête sur l'écrivain nommé, sans cascade de rouges ;
  * ce module est chargé par CHEMIN depuis `tests/conftest.py`, jamais par `import tools…` : une garde qui passerait
    par le paquet qu'elle surveille pourrait être elle-même chargée depuis le mauvais arbre.
  * Écarté (Master 2) : rendre `tools` régulier par un fichier d'initialisation — le premier arbre trouvé gagnerait
    ENTIÈREMENT, et le défaut resterait.
"""
import os
import pathlib
import subprocess
import sys

import pytest

_SURVEILLES = ("tools", "src")
_CACHE = {}


def _norm(p):
    try:
        return os.path.normcase(os.path.realpath(os.path.abspath(p)))
    except (OSError, ValueError):
        return os.path.normcase(os.path.abspath(p))


def racines_du_depot(ici):
    """Racines normalisées de tous les arbres (principal + worktrees) du dépôt qui contient `ici`, de la plus LONGUE à
    la plus courte ; None si git est indisponible ou si `ici` n'est dans aucun dépôt."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        r = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=str(ici), env=env, capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    racines = {_norm(l[len("worktree "):]) for l in r.stdout.splitlines() if l.startswith("worktree ")}
    return sorted(racines, key=len, reverse=True) or None


def proprietaire(chemin, racines, cwd=None):
    """La racine la plus LONGUE de `racines` qui contient `chemin`, ou None hors dépôt. '' et un chemin relatif suivent
    `cwd` (défaut : le cwd de l'instant) ; un chemin absolu est normalisé une fois (cache)."""
    if not isinstance(chemin, str):
        return None
    if chemin and os.path.isabs(chemin):
        n = _CACHE.get(chemin)
        if n is None:
            n = _CACHE[chemin] = _norm(chemin)
    else:
        n = _norm(os.path.join(cwd if cwd is not None else os.getcwd(), chemin))
    for r in racines:
        if n == r or n.startswith(r + os.sep):
            return r
    return None


def entrees_etrangeres(sys_path, ici, racines, cwd=None):
    """Les entrées de `sys_path` qui appartiennent à un arbre du dépôt AUTRE que `ici`."""
    out = []
    for p in list(sys_path):
        r = proprietaire(p, racines, cwd)
        if r is not None and r != ici:
            out.append(p)
    return out


def modules_etrangers(modules, ici, racines):
    """Les modules `tools.*` / `src.*` (et leurs paquets) chargés depuis un arbre AUTRE que `ici` : l'objet CONSOMMÉ."""
    out = []
    for nom, m in list(modules.items()):
        if nom.split(".")[0] not in _SURVEILLES or m is None:
            continue
        lieu = getattr(m, "__file__", None)
        if not lieu:
            chemins = list(getattr(m, "__path__", None) or [])
            lieu = chemins[0] if chemins else None
        r = proprietaire(lieu, racines) if lieu else None
        if r is not None and r != ici:
            out.append((nom, lieu))
    return sorted(out)


# --- l'état de la session et les crochets pytest ---------------------------------------------------------------------
_ICI = _norm(str(pathlib.Path(__file__).resolve().parents[1]))       # l'arbre auquel appartient CE fichier
_ETAT = {"racines": None, "inerte": None}


def _refus(ou, entrees, modules):
    lignes = [f"REFUS (garde des arbres, P2.142) — {ou}",
              f"  arbre testé : {_ICI}"]
    if entrees:
        lignes.append(f"  sys.path porte {len(entrees)} entrée(s) d'un AUTRE arbre du dépôt : {entrees}")
    if modules:
        lignes.append(f"  module(s) CONSOMMÉ(S) depuis un autre arbre : {modules[:8]}"
                      + (f" … (+{len(modules) - 8})" if len(modules) > 8 else ""))
    lignes.append("  Un test de cet arbre exercerait le code d'un autre (E35). Trouver l'ÉCRIVAIN de l'entrée ; un module "
                  "qui insère la racine de son __file__ n'en est qu'un PROPAGATEUR.")
    pytest.exit("\n".join(lignes), returncode=4)


def _controle(ou):
    racines = _ETAT["racines"]
    if not racines:
        return
    entrees = entrees_etrangeres(sys.path, _ICI, racines)
    modules = modules_etrangers(sys.modules, _ICI, racines)
    if entrees or modules:
        _refus(ou, entrees, modules)


def pytest_sessionstart(session):
    _ETAT["racines"] = racines_du_depot(_ICI)
    if not _ETAT["racines"]:
        _ETAT["inerte"] = "git indisponible ou hors dépôt"
        return
    _controle("dès le DÉPART de la session (environnement : PYTHONPATH, fichier .pth, ou lanceur)")


def pytest_report_header(config):
    if _ETAT["inerte"]:
        return f"garde des arbres (P2.142) : INERTE — {_ETAT['inerte']}"
    return None


def controle_collecte():
    """Le contrôle de fin de COLLECTE, appelé par l'unique `pytest_collection_modifyitems` de `tests/conftest.py`."""
    _controle("pendant la COLLECTE (import d'un module de test, ou d'un conftest)")


def pytest_collection_finish(session):
    """Pour un emploi AUTONOME du module (un conftest qui n'a pas d'autre crochet de collecte) ; le conftest du projet ne
    l'expose PAS, pour ne pas contrôler deux fois."""
    controle_collecte()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    _controle(f"avant le test {item.nodeid}")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    res = yield                         # les finaliseurs ont tourné : l'état est celui que le test LAISSE
    _controle(f"introduit par le test {item.nodeid} (son appel, ses fixtures ou son démontage)")
    return res
