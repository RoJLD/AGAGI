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

    from tools.check_staged_authorship import snapshot, verify, confirm_commit
    snapshot(["tests/sandbox/test_instrument_calibration.py"], owner="ma-tache")   # AVANT d'éditer
    ...                                                                            # édition + git add
    verify(["tests/sandbox/test_instrument_calibration.py"], owner="ma-tache")     # AVANT de commit
    ...                                                                            # git commit
    confirm_commit(sha, [...], owner="ma-tache")                                   # APRÈS le commit

`verify()` lève `ForeignHunkDetected` — en NOMMANT les hunks (numéros de ligne + contenu), pas en disant
juste non — si le contenu STAGÉ contient un bloc de lignes qui figurait déjà dans le snapshot de départ
SANS être dans le blob HEAD capturé au même instant. Ce que la tâche courante a écrit est, par
construction, ce qui DIFFÈRE du snapshot : `verify()` laisse passer ces hunks-là.

--- SENS B : « quelqu'un a committé MON travail avant moi » (levée de limite, 2026-09-02) -------------

La première livraison déclarait ce sens « sans garde exécutable, par construction (rien à comparer dans
un stage) ». C'est FAUX, et c'est exactement le mode de raisonnement que le pré-vol interdit (§D :
raisonner au lieu de mesurer). Il n'y a en effet rien à comparer DANS LE STAGE — mais l'empreinte donne
un second point de comparaison, et la conjonction de deux faits observables suffit :

  (1) le contenu de l'arbre de travail DIFFÈRE de l'empreinte      -> j'ai bien édité ;
  (2) `git diff HEAD -- <chemin>` est VIDE                          -> il n'y a rien à committer.

(1) ∧ (2) ⇒ mes éditions sont déjà DANS un commit — que je n'ai pas fait. Le cas « je n'ai simplement
rien édité » se sépare proprement : il viole (1) (contenu identique à l'empreinte). `detect_preempted()`
nomme alors le commit porteur, cherché PAR CONTENU (le premier commit de `head_sha..HEAD` touchant le
chemin dont le blob contient un bloc écrit APRÈS mon empreinte), et non par simple `log -1`.

⚠️ C'est un AVERTISSEMENT, pas une erreur bloquante — choix argumenté, pas timidité :
  * il n'y a rien à bloquer : par (2) il n'y a RIEN à committer sur ce chemin ; un `git commit` y serait
    déjà un no-op. Bloquer n'empêcherait aucun dégât, mais ferait échouer le commit LÉGITIME des AUTRES
    chemins de la même tâche (`verify` prend une liste) — un faux positif y coûte un commit valide ;
  * l'action corrective n'est pas « ne committe pas » mais « ne RE-committe pas, vérifie que le contenu
    porté est bien le tien, signale la mauvaise attribution » — hors du pouvoir d'un exit code ;
  * il reste des faux positifs non éliminables mécaniquement : avoir committé soi-même sans le déclarer
    (désamorcé par `confirm_commit(..., owner=...)`, qui inscrit le SHA dans l'empreinte), un
    `git stash`/`checkout` intermédiaire, ou une convergence de contenu identique.
Le CLI l'imprime TOUJOURS (stderr, en tête, même quand `verify` va lever) ; `--strict` le rend bloquant
pour qui veut un hook dur.

--- LIMITE 2 : `git add` et `git commit` ne sont PAS atomiques sur un index partagé ------------------

Constaté le 2026-09-01 : une session parallèle a committé le même chemin ENTRE le `git add` et le
`git commit` d'une autre. Le chemin a alors disparu SILENCIEUSEMENT du commit résultant — aucune erreur,
aucun avertissement, juste un fichier absent du diff-stat (reproduit à l'identique dans le test :
`git commit -- <path>` d'une session parallèle vide la contribution de ce chemin, et le commit suivant
ne porte plus que les autres). Le rituel « inspecter `git diff --cached` avant de committer » est donc
NÉCESSAIRE MAIS PAS SUFFISANT : la fenêtre de course est APRÈS l'inspection. Seule une vérification
APRÈS coup la ferme -> `confirm_commit(sha, paths)`, qui lève `MissingPathsInCommit` en nommant les
chemins que le commit ne porte pas.

⚠️ Ce que cette garde NE fait PAS (portée honnête, cf. le ⚠️ de `preregister.py`) :
  * elle ne détecte que des AJOUTS (blocs présents dans le stage, absents de HEAD). Une suppression
    étrangère (quelqu'un avait déjà retiré des lignes, non committé, avant ton snapshot) n'est pas
    couverte — hors du motif observé le 2026-09-01 ;
  * la comparaison HEAD utilisée par `verify()` est celle capturée AU SNAPSHOT, pas HEAD courant : si
    HEAD avance entre le snapshot et le verify (quelqu'un committe CE MÊME fichier entre-temps), le
    calcul redevient approximatif — c'est précisément la situation que `detect_preempted()` SIGNALE,
    au lieu de la laisser fausser le verdict en silence ;
  * deux tâches qui créent le MÊME nouveau fichier (absent de HEAD ET absent des deux snapshots) restent
    indiscernables entre elles : rien à comparer ;
  * `detect_preempted()` est muet si l'autre session a committé mon travail PUIS remodifié le fichier
    (alors `git diff HEAD` n'est plus vide) — le conflit devient visible autrement ;
  * il observe « l'arbre a CHANGÉ depuis l'empreinte », pas « J'AI édité » : dans un arbre PARTAGÉ, du
    contenu écrit par une session parallèle après mon empreinte, puis committé par elle, déclenche AUSSI
    l'alerte. Le signal est donc « un contenu apparu après ton empreinte est déjà committé — vérifie
    l'attribution », pas une preuve de vol. C'est gravé par un test (`test_LIMITE_CONNUE_sensB_...`) et
    c'est la deuxième raison pour laquelle l'alerte n'est pas bloquante ;
  * `confirm_commit()` compare au(x) parent(s) via `diff-tree` : sur un commit de MERGE, un chemin non
    conflictuel n'apparaît pas dans le diff combiné et serait rapporté manquant (les commits de ce
    dépôt sont path-scopés, pas des merges).

⚠️ Piège de nommage évité délibérément : ce fichier commence par `check_`, donc `check_instrument_
calibration.py` l'EXCLUT de son propre scan (`fn.startswith("check_")`, comme `check_record_links.py`).
Aucune dette de calibration n'est créée par cette convention de nommage — c'est le même mécanisme qui
protège déjà `check_record_links.py` et `check_cost_guard`-like scripts de ce dépôt.

Usage CLI :
  python tools/check_staged_authorship.py snapshot <fichier> [<fichier> ...] [--owner NOM]
  python tools/check_staged_authorship.py verify   <fichier> [<fichier> ...] [--owner NOM] [--strict]
  python tools/check_staged_authorship.py confirm  <sha> <fichier> [<fichier> ...] [--owner NOM]
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


class WorkPreempted(Exception):
    """SENS B : entre le snapshot et le verify, l'arbre de travail a CHANGÉ (j'ai édité) mais
    `git diff HEAD` est VIDE (rien à committer) — donc mon travail est déjà porté par le commit de
    quelqu'un d'autre. AVERTISSEMENT par défaut (cf. le §SENS B du module) : le CLI l'imprime toujours,
    ne la lève qu'en `--strict`."""

    def __init__(self, report: dict):
        self.report = report          # {chemin: {"commit","subject","author","date","matched_by_content"}}
        lignes = ["ATTENTION — travail PRÉEMPTÉ : ces chemins ont été édités par toi APRÈS ton empreinte,",
                  "mais ils n'ont RIEN à committer : le contenu est déjà porté par le commit d'un autre."]
        for path, info in report.items():
            lignes.append(f"  {path} :")
            sha = info.get("commit") or "(commit introuvable)"
            lignes.append(f"    porté par {sha[:8]} — {info.get('subject', '?')}")
            lignes.append(f"    auteur   {info.get('author', '?')}  ({info.get('date', '?')})")
            if info.get("matched_by_content"):
                lignes.append("    ce commit contient LITTÉRALEMENT des lignes écrites après ton empreinte")
            else:
                lignes.append("    ⚠️ apparié par HISTORIQUE seulement (pas de bloc AJOUTÉ retrouvé) —"
                              " vérifier à la main")
        lignes += [
            "Quoi faire : (1) NE PAS re-committer ces chemins — il n'y a rien à committer, un commit",
            "    supplémentaire serait vide ou dupliquerait le contenu ;",
            "  (2) vérifier que le contenu porté est bien LE TIEN (`git show <sha> -- <chemin>`) et",
            "    complet — un `git add` d'autrui a pu n'en happer qu'une partie ;",
            "  (3) SIGNALER la mauvaise attribution (le commit porte ton travail sous une autre tâche).",
            "Si c'est TON propre commit, le déclarer via `confirm <sha> <chemins> --owner <toi>` : il est",
            "  alors inscrit dans l'empreinte et ne sera plus signalé.",
        ]
        super().__init__("\n".join(lignes))


class MissingPathsInCommit(Exception):
    """LIMITE 2 : le commit réalisé ne porte PAS tous les chemins attendus — typiquement parce qu'une
    session parallèle a committé le même chemin ENTRE le `git add` et le `git commit`."""

    def __init__(self, sha: str, missing, present):
        self.sha, self.missing, self.present = sha, list(missing), list(present)
        lignes = [f"le commit {sha[:8]} ne porte PAS tous les chemins attendus :"]
        for p in self.missing:
            lignes.append(f"    MANQUANT : {p}")
        lignes.append(f"  porté(s) : {', '.join(self.present) if self.present else '(aucun)'}")
        lignes += [
            "Cause typique (mesurée le 2026-09-01) : une session parallèle a committé ce chemin ENTRE",
            "  ton `git add` et ton `git commit` — le chemin disparaît alors du commit SANS erreur.",
            "Quoi faire : vérifier si le contenu attendu est déjà porté ailleurs",
            "  (`git log --oneline -3 -- <chemin>`) ; sinon, commit CORRECTIF path-scopé sur ce chemin.",
        ]
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


def _head_sha(cwd: str):
    """SHA de HEAD, ou None (dépôt sans commit)."""
    r = _run_git(["rev-parse", "HEAD"], cwd)
    return r.stdout.strip() if r.returncode == 0 else None


def _commit_content(sha: str, path: str, *, cwd: str):
    """Contenu de `path` dans le commit `sha`, ou None s'il n'y figure pas."""
    r = _run_git(["show", f"{sha}:{_gitpath(path)}"], cwd)
    return r.stdout if r.returncode == 0 else None


def _has_uncommitted_change(path: str, *, cwd: str) -> bool:
    """Reste-t-il quelque chose à committer pour `path` ? (`git diff HEAD -- <path>` non vide)

    ⚠️ Ce test est VIDE pour un fichier non tracké (il n'est pas dans HEAD, donc pas dans le diff) —
    c'est le faux positif principal du sens B, écarté en amont par le test d'appartenance à HEAD."""
    r = _run_git(["diff", "HEAD", "--name-only", "--", _gitpath(path)], cwd)
    if r.returncode != 0:                       # p.ex. dépôt sans HEAD : on ne conclut rien
        return True
    return bool(r.stdout.strip())


def _commits_touching(path: str, *, since: str = None, cwd: str, limit: int = 50):
    """Commits touchant `path`, du plus ANCIEN au plus récent, bornés à `since..HEAD` si `since` est un
    SHA encore valide (sinon on retombe sur les `limit` derniers — rebase, empreinte ancienne)."""
    fmt = "--format=%H%x1f%an%x1f%ad%x1f%s"
    base = ["log", fmt, "--date=short", f"-n{limit}"]
    r = None
    if since:
        r = _run_git(base + [f"{since}..HEAD", "--", _gitpath(path)], cwd)
        if r.returncode != 0:
            r = None
    if r is None:
        r = _run_git(base + ["--", _gitpath(path)], cwd)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) == 4:
            out.append({"commit": parts[0], "author": parts[1], "date": parts[2], "subject": parts[3]})
    out.reverse()                                # `git log` sort du plus récent : on veut chronologique
    return out


def _paths_in_commit(sha: str, *, cwd: str):
    """Chemins portés par le commit `sha` (diff avec son parent). None si le SHA est inconnu."""
    r = _run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha], cwd)
    if r.returncode != 0:
        return None
    return {p.strip() for p in r.stdout.splitlines() if p.strip()}


# --- empreinte ---------------------------------------------------------------------------------------

def _safe_name(owner: str, path: str) -> str:
    raw = f"{owner}__{_gitpath(path)}"
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in raw) + ".json"


def _snapshot_path(path: str, owner: str, snapshot_dir: str) -> str:
    return os.path.join(snapshot_dir, _safe_name(owner, path))


def _load_snapshot(path: str, owner: str, snapshot_dir: str) -> dict:
    sp = _snapshot_path(path, owner, snapshot_dir)
    if not os.path.exists(sp):
        raise NoSnapshotError(
            f"aucune empreinte pour « {path} » (owner={owner!r}) — appeler snapshot() AVANT d'éditer")
    with open(sp, encoding="utf-8") as f:
        return json.load(f)


def snapshot(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT):
    """Prend l'empreinte de `paths` — contenu de l'arbre de travail ET blob HEAD, au même instant —
    AVANT toute édition. Renvoie la liste des fichiers d'empreinte écrits."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    os.makedirs(d, exist_ok=True)
    written = []
    sha = _head_sha(cwd)
    for path in paths:
        payload = {
            "owner": owner,
            "path": path,
            "taken_at": datetime.now(timezone.utc).isoformat(),
            "working_tree_content": _working_tree_content(path, cwd=cwd),
            "head_content": _head_content(path, cwd=cwd),
            "head_sha": sha,        # borne la recherche du commit préempteur (sens B) à `head_sha..HEAD`
            "own_commits": [],      # SHA déclarés miens via `confirm_commit(..., owner=...)`
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


def _runs_present_in(hay_lines, block):
    """Runs MAXIMAUX de `block` qui apparaissent CONTIGUS dans `hay_lines`, balayés de gauche à droite,
    le plus long à chaque position : [(offset dans `block`, longueur), ...].

    ⚠️ Pourquoi PAS un `SequenceMatcher` ici (occurrence 13 d'E10, 2026-09-02) : un alignement GLOBAL
    n'attribue chaque ligne qu'à UN seul rôle, et il ancre sur le PLUS LONG appariement. Un run que la
    tâche courante a RECOPIÉ depuis HEAD (motif banal : écrire un test en partant d'un test existant),
    s'il est plus long que le bloc étranger, VOLE l'ancre — le bloc étranger retombe alors dans un
    opcode non-`equal` et devient INVISIBLE. Mesuré sur le fichier réel de l'incident : un bloc
    étranger de ≤ 41 lignes disparaît face à un run recopié de 40 lignes, et réapparaît à 60.
    Ici chaque position est testée POUR ELLE-MÊME : il n'y a plus de concurrence d'ancre, donc aucun
    run présent dans l'empreinte ne peut être perdu au profit d'un autre."""
    idx = {}
    for k, ln in enumerate(hay_lines):
        idx.setdefault(ln, []).append(k)
    runs, i, n, m = [], 0, len(block), len(hay_lines)
    while i < n:
        best = 0
        for start in idx.get(block[i], ()):
            length = 0
            while start + length < m and i + length < n and hay_lines[start + length] == block[i + length]:
                length += 1
            if length > best:
                best = length
        if best:
            runs.append((i, best))
            i += best
        else:
            i += 1
    return runs


def _foreign_hunks(head_lines, snap_lines, staged_lines):
    """Segments de lignes stagées qui sont ÉTRANGERS : absents de HEAD (donc « ajoutés » par CE stage,
    via `_added_blocks`) ET DÉJÀ présents dans le snapshot de départ (donc pas écrits par cette tâche).

    ⚠️ Un bloc `insert`/`replace` renvoyé par `_added_blocks` mélange souvent DEUX auteurs quand leurs
    ajouts sont contigus (rien de commun avec HEAD entre les deux pour les séparer) — c'était exactement
    le cas dans `e21c1f3` : le hunk étranger et mon propre hunk se suivaient sans ligne HEAD entre les
    deux. Comparer le bloc ENTIER au snapshot (au lieu de le décomposer) le manque : le bloc combiné
    n'est, dans son ENSEMBLE, ni tout à fait dans le snapshot ni tout à fait absent. Il faut donc une
    SECONDE passe À L'INTÉRIEUR du bloc, contre le snapshot.

    ⚠️ Cette seconde passe était elle-même un DIFF (`SequenceMatcher`), et c'est ce qui a produit
    l'occurrence 13 : un alignement global ancre sur le plus long appariement, donc un run recopié de
    HEAD par la tâche courante pouvait masquer un bloc étranger plus court (cf. `_runs_present_in`).
    Elle procède désormais par TEST D'APPARTENANCE, position par position — un run étranger ne peut
    plus être perdu par concurrence d'ancre. Contre-exemple gelé :
    `test_FORME_occ13_a_long_run_copied_from_HEAD_must_not_STEAL_the_anchor`.

    ⚠️ Contrepartie ASSUMÉE : un run peut chevaucher la frontière (contenu à moi immédiatement suivi,
    dans l'empreinte, du contenu d'autrui) et alors quelques-unes de mes lignes sont rapportées avec le
    hunk étranger. Le rapport SUR-couvre, il ne sous-couvre plus : un faux positif se lit et se lève à
    l'œil, un faux négatif laisse committer le travail d'autrui."""
    foreign = []
    for outer in _added_blocks(head_lines, staged_lines):
        block, base_line = outer["lines"], outer["start_line"]
        for off, length in _runs_present_in(snap_lines, block):
            seg = block[off:off + length]
            if not seg or all(not ln.strip() for ln in seg):
                continue                          # segment purement blanc : bruit de diff, pas un signal
            if _contains_block(head_lines, seg):
                continue                          # coïncide avec HEAD par ailleurs : pas étranger
            foreign.append({"start_line": base_line + off, "lines": seg})
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
        snap = _load_snapshot(path, owner, d)
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


# --- SENS B : quelqu'un a committé MON travail avant moi ---------------------------------------------

def detect_preempted(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT):
    """Détecte les chemins dont le travail a été PRÉEMPTÉ : édités par moi après l'empreinte, mais sans
    rien à committer — donc déjà portés par le commit de quelqu'un d'autre. Renvoie
    {chemin: {"commit","subject","author","date","matched_by_content"}} ; vide = rien à signaler.

    Les TROIS cas se séparent mécaniquement, et c'est ce qui rend la détection sûre :
      * contenu identique à l'empreinte          -> je n'ai RIEN édité      -> silence (pas d'alerte) ;
      * contenu différent, `git diff HEAD` NON vide -> travail normal en cours -> silence ;
      * contenu différent, `git diff HEAD` VIDE     -> PRÉEMPTÉ                -> alerte nommant le commit.
    Deux exclusions ferment les faux positifs restants : un chemin ABSENT de HEAD (fichier nouveau/non
    tracké) a lui aussi un `git diff HEAD` vide sans que rien n'ait été committé ; et un commit déclaré
    mien via `confirm_commit(..., owner=...)` n'est pas une préemption."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    report = {}
    for path in paths:
        snap = _load_snapshot(path, owner, d)
        snap_wt = snap.get("working_tree_content")
        cur_wt = _working_tree_content(path, cwd=cwd)
        if cur_wt == snap_wt:
            continue                       # (cas 1) rien édité — NE PAS confondre avec une préemption
        if _head_content(path, cwd=cwd) is None:
            continue                       # absent de HEAD (nouveau/non tracké) : rien n'a été committé
        if _has_uncommitted_change(path, cwd=cwd):
            continue                       # (cas 2) il reste du contenu à committer : travail normal
        # (cas 3) j'ai édité, et il n'y a RIEN à committer -> mon contenu est déjà dans un commit.
        mine = _added_blocks((snap_wt or "").splitlines(), (cur_wt or "").splitlines())
        own = set(snap.get("own_commits") or [])
        carrier, matched = None, False
        for c in _commits_touching(path, since=snap.get("head_sha"), cwd=cwd):
            blob = _commit_content(c["commit"], path, cwd=cwd)
            if blob is None:
                continue
            blob_lines = blob.splitlines()
            if any(_contains_block(blob_lines, b["lines"]) for b in mine):
                carrier, matched = c, True   # recherche PAR CONTENU : ce commit porte mes lignes
                break
            carrier = carrier or c           # à défaut : le plus ancien commit touchant le chemin
        if carrier is None:
            continue                         # aucun commit identifiable : rien de solide à affirmer
        if carrier["commit"] in own:
            continue                         # c'est MON propre commit, déclaré via confirm_commit()
        report[path] = dict(carrier, matched_by_content=matched)
    return report


# --- LIMITE 2 : vérification APRÈS commit (la course est postérieure à l'inspection du stage) --------

def confirm_commit(sha: str, paths, *, owner: str = None, snapshot_dir: str = None, cwd: str = _ROOT):
    """Confirme que le commit `sha` porte bien TOUS les chemins de `paths`. Lève `MissingPathsInCommit`
    en nommant les manquants. Renvoie {"commit","present","unexpected"}.

    `git diff --cached` inspecté avant le commit ne suffit pas : une session parallèle peut committer le
    même chemin ENTRE le `git add` et le `git commit`, et le chemin disparaît alors du commit SANS la
    moindre erreur. Seule cette vérification a posteriori ferme la fenêtre.

    Si `owner` est donné, `sha` est inscrit dans les empreintes correspondantes (`own_commits`) : un
    commit déclaré mien ne sera plus signalé comme préemption par `detect_preempted()`."""
    r = _run_git(["rev-parse", sha], cwd)   # forme LONGUE : `detect_preempted` compare des SHA complets,
    resolved = r.stdout.strip() if r.returncode == 0 else sha   # et le message doit NOMMER le commit
    carried = _paths_in_commit(resolved, cwd=cwd)
    if carried is None:
        raise MissingPathsInCommit(resolved, list(paths), [])   # SHA inconnu : rien n'est confirmé
    wanted = [_gitpath(p) for p in paths]
    present = [p for p in wanted if p in carried]
    missing = [p for p in wanted if p not in carried]
    if owner:
        _record_own_commit(resolved, paths, owner=owner, snapshot_dir=snapshot_dir)
    if missing:
        raise MissingPathsInCommit(resolved, missing, present)
    return {"commit": resolved, "present": present, "unexpected": sorted(carried - set(wanted))}


def _record_own_commit(sha: str, paths, *, owner: str, snapshot_dir: str = None):
    """Inscrit `sha` comme commit de `owner` dans les empreintes existantes (best-effort : une empreinte
    absente n'est pas une erreur — la confirmation post-commit doit marcher sans snapshot préalable)."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    for path in paths:
        sp = _snapshot_path(path, owner, d)
        if not os.path.exists(sp):
            continue
        with open(sp, encoding="utf-8") as f:
            snap = json.load(f)
        own = snap.get("own_commits") or []
        if sha not in own:
            own.append(sha)
        snap["own_commits"] = own
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)


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
    vp.add_argument("--strict", action="store_true",
                    help="rendre BLOQUANT l'avertissement de préemption (sens B), non bloquant par défaut")

    cp = sub.add_parser("confirm", help="vérifier APRÈS commit que le commit porte bien tous les chemins")
    cp.add_argument("sha")
    cp.add_argument("paths", nargs="+")
    cp.add_argument("--owner", default=None,
                    help="inscrire ce SHA comme commit de cet owner (désamorce l'alerte de préemption)")
    cp.add_argument("--dir", default=None)
    cp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    args = ap.parse_args(argv)
    cwd = args.cwd or _ROOT

    if args.cmd == "snapshot":
        for p in snapshot(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd):
            print(f"empreinte écrite : {p}")
        return 0

    if args.cmd == "confirm":
        try:
            res = confirm_commit(args.sha, args.paths, owner=args.owner,
                                 snapshot_dir=args.dir, cwd=cwd)
        except MissingPathsInCommit as e:
            print(f"ERREUR : {e}", file=sys.stderr)
            return 1
        print(f"OK : {res['commit'][:8]} porte les {len(res['present'])} chemin(s) attendu(s) — "
              f"{', '.join(res['present'])}")
        if res["unexpected"]:
            print(f"note : ce commit porte AUSSI {len(res['unexpected'])} chemin(s) non déclaré(s) : "
                  f"{', '.join(res['unexpected'])}")
        return 0

    # SENS B d'abord, et hors du try de `verify` : l'avertissement doit s'afficher MÊME si `verify` lève.
    preempted = {}
    try:
        preempted = detect_preempted(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd)
    except NoSnapshotError:
        pass                                       # `verify` ci-dessous lèvera la même erreur, en clair
    if preempted:
        print(f"{WorkPreempted(preempted)}", file=sys.stderr)

    try:
        checked = verify(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd)
    except (NoSnapshotError, ForeignHunkDetected) as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 1
    for path, n in checked.items():
        print(f"OK : {path} — {n} hunk(s) stagé(s), tous attribuables à owner={args.owner!r}")
    if not checked and not preempted:
        print("OK : rien à vérifier (aucun des chemins donnés n'est stagé)")
    return 2 if (preempted and args.strict) else 0


if __name__ == "__main__":
    sys.exit(_cli())
