"""Garde EXÉCUTABLE de la classe E10 (occurrences 8 et 9 du 2026-09-01, promotion P2.22) — « hunks
étrangers happés par un commit path-scopé mais pas contenu-scopé », sur un fichier PARTAGÉ à forte
contention (`tests/sandbox/test_instrument_calibration.py`).

Le fait déclencheur (2026-09-01, arbre partagé entre sessions parallèles) :
  (a) un commit a happé ~159 lignes de travail NON committé d'une session parallèle via un
      `git add <fichier>` — path-scopé (le bon fichier) mais PAS contenu-scopé (n'importe quel hunk
      présent dans ce fichier au moment du `add`, y compris celui d'un autre auteur) ;
  (b) en sens inverse, des sessions parallèles ont committé le contenu d'un implémenteur AVANT lui.
Le registre (E10) note : « une garde disponible et NON DÉCLENCHÉE vaut zéro » — la discipline manuelle
(« git add explicite », inspection visuelle) a déjà échoué deux fois sur CE fichier. Ce module remplace
l'inspection visuelle par une comparaison MÉCANIQUE.

Le mécanisme (et il est détectable, contrairement à E9/E14 qui exigent de deviner une INTENTION) :
les hunks étrangers sont précisément ceux qui étaient DÉJÀ dans l'arbre de travail AVANT que la tâche ne
commence, mais qui sont ABSENTS de HEAD à ce moment-là — c'est-à-dire du travail non committé d'autrui.
Avec une EMPREINTE prise au démarrage, la détection est exacte :

    from tools.check_staged_authorship import snapshot, verify
    snapshot(["tests/sandbox/test_instrument_calibration.py"], owner="ma-tache")   # AVANT d'éditer
    ...                                                                            # édition + git add
    verify(["tests/sandbox/test_instrument_calibration.py"], owner="ma-tache")     # AVANT de commit

`verify()` lève `ForeignHunkDetected` — en NOMMANT les hunks (numéros de ligne + contenu), pas en disant
juste non — si le contenu STAGÉ contient un bloc de lignes qui figurait déjà dans le snapshot de départ
SANS être dans le blob HEAD capturé au même instant. Ce que la tâche courante a écrit est, par
construction, ce qui DIFFÈRE du snapshot : `verify()` laisse passer ces hunks-là.

⚠️ Ce que cette garde NE fait PAS (portée honnête, cf. le ⚠️ de `preregister.py`) :
  * elle ne couvre que le SENS (a) — un hunk étranger happé par TON commit. Le sens (b) — quelqu'un
    committe TON travail avant toi — n'est pas un défaut d'AUTHORSHIP du stage, rien à comparer ;
  * elle ne détecte que des AJOUTS (blocs présents dans le stage, absents de HEAD). Une suppression
    étrangère (quelqu'un avait déjà retiré des lignes, non committé, avant ton snapshot) n'est pas
    couverte — hors du motif observé le 2026-09-01 ;
  * la comparaison HEAD utilisée est celle capturée AU SNAPSHOT, pas HEAD courant : si HEAD avance entre
    le snapshot et le verify (quelqu'un committe CE MÊME fichier entre-temps), le calcul redevient
    approximatif — cas hors du motif observé (ici HEAD n'avait pas bougé) ;
  * deux tâches qui créent le MÊME nouveau fichier (absent de HEAD ET absent des deux snapshots) restent
    indiscernables entre elles : rien à comparer.

⚠️ Piège de nommage évité délibérément : ce fichier commence par `check_`, donc `check_instrument_
calibration.py` l'EXCLUT de son propre scan (`fn.startswith("check_")`, comme `check_record_links.py`).
Aucune dette de calibration n'est créée par cette convention de nommage — c'est le même mécanisme qui
protège déjà `check_record_links.py` et `check_cost_guard`-like scripts de ce dépôt.

Usage CLI :
  python tools/check_staged_authorship.py snapshot <fichier> [<fichier> ...] [--owner NOM]
  python tools/check_staged_authorship.py verify   <fichier> [<fichier> ...] [--owner NOM]
"""
import argparse
import difflib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SNAPSHOT_DIR = os.path.join(_ROOT, "runs", "staged_authorship")  # `runs/` est gitignored


class NoSnapshotError(Exception):
    """`verify()` appelé sur un chemin jamais `snapshot()`é pour cet `owner` — rien à quoi comparer."""


class ForeignHunkDetected(Exception):
    """Le stage contient un bloc de lignes déjà présent dans le snapshot de départ, absent de HEAD à ce
    moment — donc du travail non committé d'une AUTRE session, happé par ce commit."""

    def __init__(self, report: dict):
        self.report = report                      # {chemin: [{"start_line": int, "lines": [str, ...]}]}
        lignes = ["hunks ÉTRANGERS détectés dans le stage (travail non committé d'une autre session) :"]
        for path, hunks in report.items():
            lignes.append(f"  {path} :")
            for h in hunks:
                fin = h["start_line"] + len(h["lines"]) - 1
                lignes.append(f"    lignes {h['start_line']}-{fin} :")
                for ln in h["lines"][:5]:
                    lignes.append(f"      + {ln}")
                if len(h["lines"]) > 5:
                    lignes.append(f"      ... (+{len(h['lines']) - 5} lignes)")
        lignes.append("Abandonner le commit, ou `git restore --staged` ces lignes avant de recommitter.")
        super().__init__("\n".join(lignes))


# --- accès git -------------------------------------------------------------------------------------

def _gitpath(path: str) -> str:
    """git veut des `/`, jamais `\\`, dans une pathspec — même sur Windows."""
    return path.replace(os.sep, "/").replace("\\", "/")


def _run_git(args, cwd):
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _head_content(path: str, *, cwd: str):
    """Contenu de `path` dans HEAD, ou None si absent de HEAD (fichier nouveau)."""
    r = _run_git(["show", f"HEAD:{_gitpath(path)}"], cwd)
    return r.stdout if r.returncode == 0 else None


def _index_content(path: str, *, cwd: str):
    """Contenu de `path` dans l'INDEX (ce qui sera committé), ou None si rien n'y est indexé."""
    r = _run_git(["show", f":{_gitpath(path)}"], cwd)
    return r.stdout if r.returncode == 0 else None


def _working_tree_content(path: str, *, cwd: str):
    full = os.path.join(cwd, path)
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8", errors="replace") as f:
        return f.read()


# --- empreinte ---------------------------------------------------------------------------------------

def _safe_name(owner: str, path: str) -> str:
    raw = f"{owner}__{_gitpath(path)}"
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in raw) + ".json"


def _snapshot_path(path: str, owner: str, snapshot_dir: str) -> str:
    return os.path.join(snapshot_dir, _safe_name(owner, path))


def snapshot(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT):
    """Prend l'empreinte de `paths` — contenu de l'arbre de travail ET blob HEAD, au même instant —
    AVANT toute édition. Renvoie la liste des fichiers d'empreinte écrits."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    os.makedirs(d, exist_ok=True)
    written = []
    for path in paths:
        payload = {
            "owner": owner,
            "path": path,
            "taken_at": datetime.now(timezone.utc).isoformat(),
            "working_tree_content": _working_tree_content(path, cwd=cwd),
            "head_content": _head_content(path, cwd=cwd),
        }
        p = _snapshot_path(path, owner, d)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written.append(p)
    return written


# --- comparaison ----------------------------------------------------------------------------------

def _added_blocks(base_lines, target_lines):
    """Blocs de lignes ajoutés dans `target_lines` par rapport à `base_lines` (opcodes 'insert'/
    'replace' de `SequenceMatcher`) : [{"start_line": i (1-indexé dans target), "lines": [...]}]."""
    sm = difflib.SequenceMatcher(None, base_lines, target_lines, autojunk=False)
    blocks = []
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            block = target_lines[j1:j2]
            if block:
                blocks.append({"start_line": j1 + 1, "lines": block})
    return blocks


def _contains_block(haystack, block) -> bool:
    """`block` apparaît-il comme sous-séquence CONTIGUË de `haystack` ?"""
    n, m = len(haystack), len(block)
    if m == 0 or m > n:
        return False
    return any(haystack[start:start + m] == block for start in range(n - m + 1))


def _foreign_hunks(head_lines, snap_lines, staged_lines):
    """Segments de lignes stagées qui sont ÉTRANGERS : absents de HEAD (donc « ajoutés » par CE stage,
    via `_added_blocks`) ET DÉJÀ présents dans le snapshot de départ (donc pas écrits par cette tâche).

    ⚠️ Un bloc `insert`/`replace` renvoyé par `_added_blocks` mélange souvent DEUX auteurs quand leurs
    ajouts sont contigus (rien de commun avec HEAD entre les deux pour les séparer) — c'était exactement
    le cas dans `e21c1f3` : le hunk étranger et mon propre hunk se suivaient sans ligne HEAD entre les
    deux. Comparer le bloc ENTIER au snapshot (au lieu de le décomposer) le manque : le bloc combiné
    n'est, dans son ENSEMBLE, ni tout à fait dans le snapshot ni tout à fait absent. Il faut donc une
    SECONDE passe de diff, à l'intérieur du bloc, contre le snapshot : ses runs `equal` sont le contenu
    étranger, ses runs non-`equal` sont ce que la tâche courante a écrit."""
    foreign = []
    for outer in _added_blocks(head_lines, staged_lines):
        block, base_line = outer["lines"], outer["start_line"]
        sm = difflib.SequenceMatcher(None, snap_lines, block, autojunk=False)
        for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                continue
            seg = block[j1:j2]
            if not seg or all(not ln.strip() for ln in seg):
                continue                          # segment purement blanc : bruit de diff, pas un signal
            if _contains_block(head_lines, seg):
                continue                          # coïncide avec HEAD par ailleurs : pas étranger
            foreign.append({"start_line": base_line + j1, "lines": seg})
    return foreign


def verify(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT):
    """Vérifie que le contenu STAGÉ de `paths` ne contient que des hunks attribuables à `owner`.

    Lève `NoSnapshotError` si `snapshot()` n'a pas été appelé pour ce (owner, path). Lève
    `ForeignHunkDetected` si un bloc de lignes stagé était DÉJÀ dans le snapshot de départ sans être
    dans le HEAD capturé au même instant (travail non committé d'une autre session). Renvoie
    {chemin: nombre de hunks vérifiés} si tout est attribuable."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    report, checked = {}, {}
    for path in paths:
        sp = _snapshot_path(path, owner, d)
        if not os.path.exists(sp):
            raise NoSnapshotError(
                f"aucune empreinte pour « {path} » (owner={owner!r}) — appeler snapshot() AVANT d'éditer")
        with open(sp, encoding="utf-8") as f:
            snap = json.load(f)
        staged = _index_content(path, cwd=cwd)
        if staged is None:
            continue                                   # rien de stagé pour ce chemin : rien à vérifier
        head_lines = (snap["head_content"] or "").splitlines()
        snap_lines = (snap["working_tree_content"] or "").splitlines()
        staged_lines = staged.splitlines()
        foreign = _foreign_hunks(head_lines, snap_lines, staged_lines)
        if foreign:
            report[path] = foreign
        else:
            checked[path] = len(_added_blocks(head_lines, staged_lines))
    if report:
        raise ForeignHunkDetected(report)
    return checked


# --- CLI ---------------------------------------------------------------------------------------------

def _cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("snapshot", help="prendre l'empreinte AVANT édition")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--owner", default="default")
    sp.add_argument("--dir", default=None)
    sp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    vp = sub.add_parser("verify", help="vérifier AVANT commit — sort en erreur si un hunk est étranger")
    vp.add_argument("paths", nargs="+")
    vp.add_argument("--owner", default="default")
    vp.add_argument("--dir", default=None)
    vp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    args = ap.parse_args(argv)
    cwd = args.cwd or _ROOT

    if args.cmd == "snapshot":
        for p in snapshot(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd):
            print(f"empreinte écrite : {p}")
        return 0

    try:
        checked = verify(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd)
    except (NoSnapshotError, ForeignHunkDetected) as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 1
    for path, n in checked.items():
        print(f"OK : {path} — {n} hunk(s) stagé(s), tous attribuables à owner={args.owner!r}")
    if not checked:
        print("OK : rien à vérifier (aucun des chemins donnés n'est stagé)")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
