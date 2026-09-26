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

--- SENS B, ATTRIBUTION AUTOMATIQUE (P2.26, 2026-09-06) : la déclaration ne dépend plus de l'opérateur ----

Mesuré le 2026-09-02 sur les 8 empreintes réelles : `detect_preempted()` rendait 2 faux positifs + 1 vrai,
les deux faux désignant un commit de l'auteur LUI-MÊME, non déclaré ; déclarer ces commits les fait
disparaître et garde le vrai. La précision est donc CONDITIONNÉE À LA DÉCLARATION — et rien n'obligeait
à appeler `confirm_commit(..., owner=)`. Le hook `tools/hooks/post-commit` appelle désormais `declare`
après CHAQUE commit (y compris `--no-verify`, qui ne saute que pre-commit/commit-msg).

LA question dure : un post-commit tourne pour TOUTES les sessions du même `.git`. Si le commit de la
session A inscrivait son SHA dans les empreintes de B, il ANNULERAIT la détection de préemption. Une
recherche PAR CONTENU ne peut PAS trancher (le contenu ne porte pas d'auteur — c'est le test gelé
`test_LIMITE_CONNUE_sensB_content_from_another_session_also_alerts`) ; l'arbre est PARTAGÉ, donc rien
dans l'arbre, l'index ou le cwd ne distingue A de B non plus. La seule grandeur qui sépare les sessions
est une IDENTITÉ DE SESSION, déclarée par l'environnement : `snapshot()` l'inscrit (`session_id`, lu de
`$AGAGI_SESSION_ID` puis `$CLAUDE_CODE_SESSION_ID`, ou passé explicitement), et `declare` n'inscrit le
SHA QUE dans les empreintes dont `session_id` est CELUI du processus qui commite ET dont le chemin est
porté par le commit. Sans identité (terminal nu, empreinte légataire sans clé) : RIEN n'est déclaré —
le pire cas est le statu quo (faux positif à lever à la main), jamais une détection annulée. C'est
« faire DÉCLARER plutôt que deviner », déclaré UNE fois par l'environnement au lieu d'à chaque commit.
L'unité de « moi » est la SESSION, pas l'owner : toutes les empreintes de la session sur le chemin sont
déclarées (les 2 faux positifs réels étaient sous un AUTRE owner que le commit).

--- LIMITE 2 : `git add` et `git commit` ne sont PAS atomiques sur un index partagé ------------------

Constaté le 2026-09-01 : une session parallèle a committé le même chemin ENTRE le `git add` et le
`git commit` d'une autre. Le chemin a alors disparu SILENCIEUSEMENT du commit résultant — aucune erreur,
aucun avertissement, juste un fichier absent du diff-stat (reproduit à l'identique dans le test :
`git commit -- <path>` d'une session parallèle vide la contribution de ce chemin, et le commit suivant
ne porte plus que les autres). Le rituel « inspecter `git diff --cached` avant de committer » est donc
NÉCESSAIRE MAIS PAS SUFFISANT : la fenêtre de course est APRÈS l'inspection. Seule une vérification
APRÈS coup la ferme -> `confirm_commit(sha, paths)`, qui lève `MissingPathsInCommit` en nommant les
chemins que le commit ne porte pas.

--- P2.122 : l'OBJET inspecté, et la FENÊTRE entre l'empreinte et le commit (2026-09-26) ---------------

Occurrence réelle `9bf30520` : un bloc écrit par une AUTRE session APRÈS l'empreinte et AVANT
`git commit -- <chemin>` est parti avec le fichier ENTIER, sous le message d'une autre tâche ; `verify`
avait rendu `{ci.yml: 0}`. Deux défauts, pas un :
  (1) l'OBJET. `verify` inspecte l'INDEX ; or `git commit -- <chemins>` emporte le DISQUE (mesuré en dépôt
      jouet : version X stagée, version Y sur le disque -> le commit porte Y, et l'index est réaligné sur
      Y). Rien n'était stagé : « 0 hunk » voulait dire « rien d'inspecté », lu comme un succès (E4). Le
      mode empreinte le DIT désormais sur stderr (DISQUE_NON_INSPECTE) quand le disque diffère de l'index ;
  (2) l'INSTANT. Une empreinte ne voit que ce qui existait à T1 : un bloc arrivé entre T1 et le commit est
      indiscernable d'un bloc à moi — sauf DÉCLARATION de ce qui est à moi. D'où `attendu` : l'appelant
      passe le contenu qu'IL a produit, et tout bloc du disque absent de HEAD ET de l'attendu est ÉTRANGER.

    from tools.check_staged_authorship import commit_exact
    commit_exact(["ci.yml"], message, {"ci.yml": contenu_produit_par_mon_script}, owner="ma-tache")

`commit_exact` lit HEAD UNE fois et refuse — rien n'est committé — si l'attendu reprend un travail
étranger pré-existant (empreinte de `owner`, forme e21c1f3), si le disque porte un bloc étranger (forme
9bf30520), s'il ne porte pas EXACTEMENT l'attendu, ou si l'attendu est identique à HEAD. Il calcule par
GIT le delta attendu (blob du disque brut, filtre `clean` compris), committe par pathspec, puis confronte
le blob ET le compte (`--numstat`) du commit à l'attendu. La fenêtre résiduelle — quelques millisecondes
entre la vérification et la lecture du disque par git — n'est pas fermée par construction : elle est
MESURÉE après coup, et un écart lève `CommitNotExact` en nommant le commit, les deux comptes et les
lignes étrangères. Le compte de `9bf30520` valait +20/-14 pour un remplacement voulu de 13 lignes par 13 :
un compte lu mais comparé à RIEN n'est pas un contrôle.

⚠️ Limites de P2.122 (portée honnête) :
  * un attendu RELU sur le disque vide le mode de son sens : il doit venir de ce que TU as écrit (sortie de
    ton script de patch, copie prise juste après ta dernière édition). Avec `owner`, l'empreinte rattrape
    la forme e21c1f3 ; sans elle, un bloc étranger pré-existant repris dans l'attendu passe (gravé par
    `test_FORME_P2_122_commit_exact_avec_owner_REFUSE_un_attendu_qui_reprend_un_travail_PREEXISTANT`) ;
  * `commit_exact` REFUSE quand un bloc étranger est sur le disque : il ne committe pas « autour ». Pour
    committer un bloc dans un fichier dont d'autres ont du travail en vol, le protocole par index
    temporaire (blob = HEAD + bloc, crochet lancé sur cet index, compare-and-swap de la branche) reste la
    voie ;
  * chemins MODIFIÉS ou NEUFS seulement : une suppression de fichier ne passe pas par ce helper.

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
  python tools/check_staged_authorship.py verify   <fichier> ... --attendu <fichier>=<contenu> [...]   # P2.122
  python tools/check_staged_authorship.py commit-exact --attendu <fichier>=<contenu> [...] -F <message>
                                                       [--owner NOM]      # P2.122 : 0 ok, 1 refusé, 3 inexact
  python tools/check_staged_authorship.py confirm  <sha> <fichier> [<fichier> ...] [--owner NOM]
  python tools/check_staged_authorship.py declare  [<sha>=HEAD] [--session-id ID]   # hook post-commit
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SNAPSHOT_DIR = os.path.join(_ROOT, "runs", "staged_authorship")  # `runs/` est gitignored
# Identité de session (P2.26) : surcharge explicite d'abord, puis celle que Claude Code pose dans
# l'environnement de CHAQUE session (vérifié propagé à `sh` et `python`, donc aux hooks git).
_SESSION_ENV_VARS = ("AGAGI_SESSION_ID", "CLAUDE_CODE_SESSION_ID")


def _current_session_id():
    """Identité de la session COURANTE, ou None — et None veut dire « ne rien déclarer », jamais deviner."""
    for var in _SESSION_ENV_VARS:
        v = (os.environ.get(var) or "").strip()
        if v:
            return v
    return None


class NoSnapshotError(Exception):
    """`verify()` appelé sur un chemin jamais `snapshot()`é pour cet `owner` — rien à quoi comparer."""


class ForeignHunkDetected(Exception):
    """Le stage contient un bloc de lignes déjà présent dans le snapshot de départ, absent de HEAD à ce
    moment — donc du travail non committé d'une AUTRE session, happé par ce commit.

    P2.122 : `objet` dit CE QUI a été inspecté, parce que le remède en dépend — « stage » (mode empreinte),
    « disque » (`verify(attendu=…)` et `commit_exact` : l'objet que `git commit -- <chemins>` emporte) ou
    « attendu » (le contenu que `commit_exact` committerait, confronté à l'empreinte de `owner`)."""

    _TETES = {
        "stage": "hunks ÉTRANGERS détectés dans le stage (travail non committé d'une autre session) :",
        "disque": ("blocs ÉTRANGERS sur le DISQUE, absents de HEAD ET du contenu ATTENDU — "
                   "`git commit -- <chemin>` les emporterait sous ton message (forme 9bf30520) :"),
        "attendu": ("blocs ÉTRANGERS dans le contenu ATTENDU — présents sur le disque AVANT ton empreinte et "
                    "absents de HEAD : le travail non committé d'une autre session, repris dans ce que tu "
                    "committerais (forme e21c1f3) :"),
    }
    _REMEDES = {
        "stage": "Abandonner le commit, ou `git restore --staged` ces lignes avant de recommitter.",
        "disque": ("Ne pas committer ce chemin tant qu'ils y sont : ils sont à leur auteur, sur SON disque — "
                   "le prévenir. S'ils sont à toi, ils manquent à ton contenu attendu."),
        "attendu": "Retirer ces blocs de l'attendu : ils restent sur le disque, à leur auteur.",
    }

    def __init__(self, report: dict, dirty_at_snapshot=(), objet: str = "stage"):
        if objet not in self._TETES:
            raise ValueError(f"objet inconnu : {objet!r} (connus : {', '.join(self._TETES)})")
        self.report = report                      # {chemin: [{"start_line": int, "lines": [str, ...]}]}
        self.dirty_at_snapshot = tuple(dirty_at_snapshot)
        self.objet = objet
        lignes = [self._TETES[objet]]
        for path, hunks in report.items():
            lignes.append(f"  {path} :")
            for h in hunks:
                fin = h["start_line"] + len(h["lines"]) - 1
                lignes.append(f"    lignes {h['start_line']}-{fin} :")
                for ln in h["lines"][:5]:
                    lignes.append(f"      + {ln}")
                if len(h["lines"]) > 5:
                    lignes.append(f"      ... (+{len(h['lines']) - 5} lignes)")
        lignes.append(self._REMEDES[objet])
        if self.dirty_at_snapshot:
            # P2.71 (2026-09-15) : une empreinte prise APRÈS avoir édité classe VOTRE travail comme
            # étranger (observé le 2026-09-07). La garde ne peut pas trancher — elle le DIT.
            lignes.append("⚠️ EMPREINTE_TARDIVE possible pour : " + ", ".join(self.dirty_at_snapshot)
                          + " — l'empreinte a été prise sur un fichier DÉJÀ modifié. Si ces hunks sont les "
                          "vôtres, cette vérification est NON CONCLUANTE : inspecter les hunks un par un, "
                          "puis committer par chemin ; la prochaine fois, snapshot() AVANT la première édition.")
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


def _decrire_bloc(bloc, titre, signe):
    """Lignes de message nommant un bloc : ses numéros de ligne, puis au plus cinq de ses lignes."""
    fin = bloc["start_line"] + len(bloc["lines"]) - 1
    out = [f"    lignes {bloc['start_line']}-{fin} {titre} :"]
    out += [f"      {signe} {ln}" for ln in bloc["lines"][:5]]
    if len(bloc["lines"]) > 5:
        out.append(f"      ... (+{len(bloc['lines']) - 5} lignes)")
    return out


def _fmt_numstat(ns):
    """(ajoutées, supprimées) -> « +a/-s » ; None (chemin non porté) -> « (aucun) »."""
    return "(aucun)" if ns is None else f"+{ns[0]}/-{ns[1]}"


class ExpectedContentMismatch(Exception):
    """P2.122 : le contenu ATTENDU n'est pas committable tel quel — le DISQUE ne le porte pas EXACTEMENT
    (sans bloc étranger nommable : sinon c'est `ForeignHunkDetected`, objet « disque »), le fichier manque,
    ou l'attendu est identique à HEAD. `commit_exact` refuse AVANT de committer : `git commit -- <chemins>`
    emporte le disque, pas l'attendu. Rien n'est committé."""

    def __init__(self, report: dict):
        self.report = report          # {chemin: {"raison": str, "absentes": [bloc], "en_trop": [bloc]}}
        lignes = ["le contenu ATTENDU n'est pas committable tel quel — refusé AVANT tout commit :"]
        for path, info in report.items():
            lignes.append(f"  {path} : {info['raison']}")
            for b in info.get("absentes") or []:
                lignes += _decrire_bloc(b, "de l'attendu, ABSENTES du disque", "-")
            for b in info.get("en_trop") or []:
                lignes += _decrire_bloc(b, "du disque, EN TROP par rapport à l'attendu", "+")
        super().__init__("\n".join(lignes))


class CommitFailed(Exception):
    """P2.122 : `git commit` a échoué dans `commit_exact` (porte du crochet rouge, HEAD déplacé pendant le
    crochet…). Rien n'est committé ; la sortie COMPLÈTE de git est jointe — c'est elle qui nomme la porte."""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode, self.stdout, self.stderr = returncode, stdout or "", stderr or ""
        corps = "\n".join(x for x in (self.stdout.rstrip(), self.stderr.rstrip()) if x)
        super().__init__(f"git commit a échoué (code {returncode}) — rien n'est committé :\n{corps}")


class CommitNotExact(Exception):
    """P2.122 (c) : le commit EXISTE, mais son contenu ou son compte (`--numstat`) diffère de l'attendu, ou il
    ne porte pas un chemin — le disque a été écrit entre la vérification et sa lecture par git, ou un commit
    s'est intercalé. Le commit est NOMMÉ, jamais défait en silence : défaire est une décision (ni amend ni
    reset sur un arbre partagé)."""

    def __init__(self, sha: str, report: dict, *, parent: str = None, parent_attendu: str = None):
        self.sha, self.report = sha, report   # {chemin: {"porte", "numstat_attendu", "numstat_observe",
        self.parent = parent                  #           "etrangeres": [bloc], "absentes": [bloc]}}
        self.parent_attendu = parent_attendu
        lignes = [f"le commit {sha[:8]} EXISTE mais ne porte PAS exactement le contenu ATTENDU (P2.122 c) — "
                  "ne pas le pousser en l'état :"]
        if parent != parent_attendu:
            lignes.append(f"  son parent {(parent or '(aucun)')[:8]} n'est pas le HEAD lu avant le commit "
                          f"({(parent_attendu or '(aucun)')[:8]}) : un commit s'est intercalé")
        for path, e in report.items():
            porte = "" if e.get("porte") else " — NON PORTÉ par le commit"
            lignes.append(f"  {path} : compte du commit {_fmt_numstat(e.get('numstat_observe'))}, attendu "
                          f"{_fmt_numstat(e.get('numstat_attendu'))}{porte}")
            for b in e.get("etrangeres") or []:
                lignes += _decrire_bloc(b, "du commit, ÉTRANGÈRES à l'attendu", "+")
            for b in e.get("absentes") or []:
                lignes += _decrire_bloc(b, "de l'attendu, ABSENTES du commit", "-")
        lignes += ["Cause typique : le disque a été écrit entre la vérification et sa lecture par git.",
                   "Prévenir l'auteur des lignes étrangères : leur contenu reste à lui, sur son disque."]
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


def snapshot(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT,
             session_id: str = None):
    """Prend l'empreinte de `paths` — contenu de l'arbre de travail ET blob HEAD, au même instant —
    AVANT toute édition. Renvoie la liste des fichiers d'empreinte écrits."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    os.makedirs(d, exist_ok=True)
    written = []
    sha = _head_sha(cwd)
    for path in paths:
        # P2.71 : une empreinte prise sur un fichier DÉJÀ modifié classera ses hunks comme étrangers.
        # Décidable ici, à coût nul ; mémorisé pour que `verify` puisse dire « non concluant ».
        dirty = _has_uncommitted_change(path, cwd=cwd)
        payload = {
            "owner": owner,
            "path": path,
            "taken_at": datetime.now(timezone.utc).isoformat(),
            "dirty_at_snapshot": bool(dirty),
            "working_tree_content": _working_tree_content(path, cwd=cwd),
            "head_content": _head_content(path, cwd=cwd),
            "head_sha": sha,        # borne la recherche du commit préempteur (sens B) à `head_sha..HEAD`
            "own_commits": [],      # SHA déclarés miens via `confirm_commit(..., owner=...)` ou `declare`
            # P2.26 : identité de la session qui prend l'empreinte. `declare` (hook post-commit) n'inscrit
            # un SHA ici QUE si la session qui commite porte la MÊME identité. None = jamais déclaré auto.
            "session_id": session_id or _current_session_id(),
        }
        p = _snapshot_path(path, owner, d)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written.append(p)
        if dirty:
            print(f"[check_staged_authorship] ⚠️ EMPREINTE_TARDIVE possible : {path} est déjà modifié par "
                  f"rapport à HEAD au moment du snapshot ; ses hunks présents seront classés ÉTRANGERS. "
                  f"Si c'est votre travail, verify() sera NON CONCLUANT sur ce chemin.", file=sys.stderr)
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


def verify(paths, *, owner: str = "default", snapshot_dir: str = None, cwd: str = _ROOT,
           attendu: dict = None):
    """Vérifie que le contenu STAGÉ de `paths` ne contient que des hunks attribuables à `owner`.

    Lève `NoSnapshotError` si `snapshot()` n'a pas été appelé pour ce (owner, path). Lève
    `ForeignHunkDetected` si un bloc de lignes stagé était DÉJÀ dans le snapshot de départ sans être
    dans le HEAD capturé au même instant (travail non committé d'une autre session). Renvoie
    {chemin: nombre de hunks vérifiés} si tout est attribuable.

    ⚠️ P2.122 — ce mode inspecte l'INDEX, or `git commit -- <chemins>` emporte le DISQUE. Quand les deux
    diffèrent pour un chemin vérifié, il l'écrit sur stderr (DISQUE_NON_INSPECTE) : sur `9bf30520`, rien
    n'était stagé, « 0 hunk » voulait dire « rien d'inspecté », et il a été lu comme un succès (E4).

    P2.122 — avec `attendu={chemin: contenu}` (le contenu que l'APPELANT a produit), l'objet change : c'est
    le DISQUE, jugé contre HEAD (lu une fois) et contre l'attendu. Tout bloc du disque absent de HEAD ET de
    l'attendu lève `ForeignHunkDetected(objet="disque")`, lignes nommées ; un chemin non déclaré lève
    `ValueError`. L'empreinte n'est pas consultée : c'est la fenêtre APRÈS elle que ce mode ferme. Renvoie
    {chemin: nombre de blocs du disque absents de HEAD, tous couverts par l'attendu} — ce qui ne dit PAS que
    le disque porte TOUT l'attendu : c'est `commit_exact` qui l'exige."""
    if attendu is not None:
        etat = _confronter_disque(_attendu_par_chemin(paths, attendu), _head_sha(cwd), cwd=cwd)
        report = {p: e["etrangers"] for p, e in etat.items() if e["etrangers"]}
        if report:
            raise ForeignHunkDetected(report, objet="disque")
        return {p: len(_added_blocks(e["head_lines"], e["disk_lines"])) for p, e in etat.items()}
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    report, checked, tardives, non_inspectes = {}, {}, [], []
    for path in paths:
        snap = _load_snapshot(path, owner, d)
        staged = _index_content(path, cwd=cwd)
        if staged is None:
            continue                                   # rien de stagé pour ce chemin : rien à vérifier
        if _disque_differe_de_l_index(path, cwd=cwd):
            non_inspectes.append(path)
        head_lines = (snap["head_content"] or "").splitlines()
        snap_lines = (snap["working_tree_content"] or "").splitlines()
        staged_lines = staged.splitlines()
        foreign = _foreign_hunks(head_lines, snap_lines, staged_lines)
        if foreign:
            report[path] = foreign
            if snap.get("dirty_at_snapshot"):
                tardives.append(path)
        else:
            checked[path] = len(_added_blocks(head_lines, staged_lines))
    if non_inspectes:
        print(f"[check_staged_authorship] DISQUE_NON_INSPECTE : {', '.join(non_inspectes)} — le disque diffère "
              f"de l'INDEX, seul inspecté ici ; or `git commit -- <chemin>` emporte le DISQUE (forme 9bf30520 : "
              f"0 hunk rendu, un bloc étranger committé). Pour juger ce qui sera committé : "
              f"verify(..., attendu=...) ou commit_exact(...).", file=sys.stderr)
    if report:
        raise ForeignHunkDetected(report, dirty_at_snapshot=tardives)
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


# --- P2.26 : déclaration AUTOMATIQUE après commit, scopée par identité de session -------------------

def declare_head_commit(sha: str = "HEAD", *, session_id: str = None, snapshot_dir: str = None,
                        cwd: str = _ROOT):
    """Appelé par le hook `post-commit` : inscrit `sha` dans `own_commits` de CHAQUE empreinte qui
    (1) porte l'identité de la session COURANTE (`session_id`, ou `$AGAGI_SESSION_ID` / `$CLAUDE_CODE_
    SESSION_ID`) ET (2) dont le chemin est PORTÉ par le commit. Renvoie [{"owner","path","commit"}].

    Conservateur par construction : sans identité courante, ou pour une empreinte sans `session_id`
    (légataire) ou d'une AUTRE session, RIEN n'est déclaré — un post-commit qui inscrirait le commit de
    la session A dans l'empreinte de B annulerait exactement la détection de préemption (sens B). Le
    contenu ne peut pas trancher (il ne porte pas d'auteur) ; seule l'identité déclarée le peut.
    Best-effort : un JSON illisible est sauté, jamais levé — un post-commit ne doit rien casser."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    sid = session_id or _current_session_id()
    if not sid or not os.path.isdir(d):
        return []
    r = _run_git(["rev-parse", sha], cwd)
    if r.returncode != 0:
        return []
    resolved = r.stdout.strip()
    carried = _paths_in_commit(resolved, cwd=cwd)
    if not carried:
        return []
    declared = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                snap = json.load(f)
        except (OSError, ValueError):
            continue                                  # empreinte illisible : on ne déclare rien dessus
        if not isinstance(snap, dict) or snap.get("session_id") != sid:
            continue                                  # AUTRE session, ou légataire sans identité : intact
        path, owner = snap.get("path"), snap.get("owner") or "default"
        if not path or _gitpath(path) not in carried:
            continue                                  # ce commit ne porte pas ce chemin
        _record_own_commit(resolved, [path], owner=owner, snapshot_dir=d)
        declared.append({"owner": owner, "path": path, "commit": resolved})
    return declared


def scan_own_snapshots(*, session_id: str = None, snapshot_dir: str = None, cwd: str = _ROOT):
    """Balaye les empreintes de LA SESSION COURANTE et renvoie {owner: report} des préemptions (sens B).

    ⚠️ SCOPÉ PAR SESSION, et ce n'est pas un détail de confort. Un balayage NON scopé parlerait à qui
    commite des préemptions subies par D'AUTRES sessions : du bruit adressé à la mauvaise personne, et
    un cliquet qu'on apprend à ignorer. Ici, on ne signale que TON travail à TOI.

    Une empreinte LÉGATAIRE (sans `session_id`, prises avant P2.26) est SAUTÉE : on ne peut pas
    l'attribuer, et deviner rejouerait la forme rétrospective déclarée non automatisable (E10 occ. 4).
    Conséquence assumée et mesurée : le vrai positif légataire de `bar-reachable` reste invisible à ce
    balayage — il est visible au balayage manuel, qui reste la voie pour les empreintes anciennes.

    Ne lève JAMAIS : la préemption n'est pas réparable par celui qui commite (son travail est déjà dans
    HEAD). La réponse juste est d'ÊTRE AVERTI, pas d'être bloqué."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    sid = session_id or _current_session_id()
    if not sid or not os.path.isdir(d):
        return {}
    par_owner = {}
    for fn_ in sorted(os.listdir(d)):
        if not fn_.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn_), encoding="utf-8") as f:
                snap = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(snap, dict) or snap.get("session_id") != sid:
            continue
        if snap.get("path"):
            par_owner.setdefault(snap.get("owner") or "default", []).append(snap["path"])
    out = {}
    for owner, paths in sorted(par_owner.items()):
        try:
            rep = detect_preempted(paths, owner=owner, snapshot_dir=d, cwd=cwd)
        except Exception:
            continue                                  # best-effort : un balayage ne casse rien
        if rep:
            out[owner] = rep
    return out


def retire_snapshots(paths=None, *, owner: str = None, snapshot_dir: str = None):
    """Retire des empreintes dont le travail est FINI. Renvoie la liste des fichiers supprimes.

    ⚠️ UNE EMPREINTE EST UNE UNITE DE TRAVAIL, PAS UN ABONNEMENT -- et ne pas la retirer fabrique du
    bruit. Mesure du 2026-09-07 : l'empreinte `p226-scan` couvrait `tools/hooks/pre-commit`, dont le
    travail etait committe et DECLARE (`084a676`) ; une session parallele y a ensuite ajoute sa propre
    porte, et le balayage a signale une preemption. Le contenu ne portant pas d'auteur, la garde ne
    PEUT pas distinguer « on a committe mon travail en attente » de « quelqu'un a legitimement edite
    ce chemin apres que le mien fut fini » -- c'est la meme indecidabilite qui interdit de declarer
    par contenu (cf. le SS SENS B). La seule issue saine est operatoire : refermer l'unite de travail.
    Une NOUVELLE unite reprend une NOUVELLE empreinte, ce que le module demande deja (snapshot AVANT
    d'editer). Un cliquet qui crie a tort est pire qu'absent : on apprend a l'ignorer."""
    d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
    if not os.path.isdir(d):
        return []
    cibles = {_gitpath(x) for x in (paths or [])}
    retires = []
    for fn_ in sorted(os.listdir(d)):
        if not fn_.endswith(".json"):
            continue
        full = os.path.join(d, fn_)
        try:
            with open(full, encoding="utf-8") as f:
                snap = json.load(f)
        except (OSError, ValueError):
            continue
        if owner and snap.get("owner") != owner:
            continue
        if cibles and _gitpath(snap.get("path") or "") not in cibles:
            continue
        os.remove(full)
        retires.append(full)
    return retires


# --- P2.122 : le contenu ATTENDU, et le commit qui ne prend que lui ------------------------------------

def _normaliser(texte: str) -> str:
    """Fins de ligne ramenées à LF, comme la lecture en mode texte du reste du module
    (`_working_tree_content`, `subprocess(text=True)`) : la garde compare des CONTENUS, pas des conventions."""
    return texte.replace("\r\n", "\n").replace("\r", "\n")


def _lire_octets(path: str, *, cwd: str):
    """Octets BRUTS du fichier sur le disque, ou None s'il n'existe pas."""
    full = os.path.join(cwd, path)
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as f:
        return f.read()


def _disque_differe_de_l_index(path: str, *, cwd: str) -> bool:
    """`git diff --quiet -- <chemin>` rend 1 quand le disque diffère de l'index, 0 quand ils sont égaux."""
    return _run_git(["diff", "--quiet", "--", _gitpath(path)], cwd).returncode == 1


def _attendu_par_chemin(paths, attendu):
    """{chemin git: contenu normalisé}, dans l'ordre de `paths`. Refuse un chemin que l'attendu ne DÉCLARE
    pas, ou une clé de l'attendu hors de `paths` : jamais deviner ce qui est à l'appelant."""
    if not isinstance(attendu, dict):
        raise TypeError(f"attendu doit être un dict {{chemin: contenu}}, pas {type(attendu).__name__}")
    norm = {}
    for cle, contenu in attendu.items():
        if not isinstance(contenu, str):
            raise TypeError(f"attendu[{cle!r}] doit être le CONTENU du fichier (str), "
                            f"pas {type(contenu).__name__}")
        norm[_gitpath(cle)] = _normaliser(contenu)
    voulus = [_gitpath(p) for p in paths]
    manquants = [p for p in voulus if p not in norm]
    en_trop = sorted(set(norm) - set(voulus))
    if manquants or en_trop:
        details = [f"chemins NON DÉCLARÉS dans l'attendu : {', '.join(manquants)}"] if manquants else []
        details += [f"clés de l'attendu HORS des chemins : {', '.join(en_trop)}"] if en_trop else []
        raise ValueError("l'attendu ne couvre pas exactement les chemins — " + " ; ".join(details))
    return {p: norm[p] for p in voulus}


def _confronter_disque(voulu: dict, sha0, *, cwd: str) -> dict:
    """Pour chaque chemin : le disque lu UNE fois (octets bruts), confronté à HEAD (`sha0`, figé par
    l'appelant) et à l'attendu. Un bloc du disque absent de l'attendu est ÉTRANGER, sauf s'il est blanc ou
    s'il coïncide avec HEAD — la forme demandée par P2.122 : « absent de HEAD ET de l'attendu ». Comme
    `_foreign_hunks`, le rapport SUR-couvre plutôt que de sous-couvrir : un bloc qui mêle des lignes de HEAD
    et des lignes étrangères est rapporté entier."""
    etat = {}
    for path, contenu in voulu.items():
        head = _commit_content(sha0, path, cwd=cwd) if sha0 else None
        head_lines = _normaliser(head or "").splitlines()
        brut = _lire_octets(path, cwd=cwd)
        disque = _normaliser(brut.decode("utf-8", errors="replace")) if brut is not None else None
        disk_lines = (disque or "").splitlines()
        attendu_lines = contenu.splitlines()
        etrangers = [b for b in _added_blocks(attendu_lines, disk_lines)
                     if any(ln.strip() for ln in b["lines"]) and not _contains_block(head_lines, b["lines"])]
        etat[path] = {"brut": brut, "disque": disque, "head_lines": head_lines, "disk_lines": disk_lines,
                      "attendu_lines": attendu_lines, "etrangers": etrangers}
    return etat


def _blob_de(octets: bytes, path, *, cwd: str) -> str:
    """SHA du blob que git stockerait pour `octets` au chemin `path` — mêmes attributs, même autocrlf (mesuré
    en dépôt jouet : le disque BRUT en CRLF rend exactement le blob que `git commit` en tire). Écrit dans la
    base d'objets (`-w`) : `git diff --numstat` doit pouvoir le lire ; non référencé, gc le ramasse."""
    args = ["git", "hash-object", "-w", "--stdin"] + (["--path", _gitpath(path)] if path else [])
    r = subprocess.run(args, cwd=cwd, input=octets, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git hash-object a échoué ({path}) : {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("ascii").strip()


def _blob_au(rev, path: str, *, cwd: str):
    """SHA du blob de `path` dans `rev`, ou None s'il n'y figure pas (ou si `rev` est None)."""
    if not rev:
        return None
    r = _run_git(["rev-parse", "--verify", "-q", f"{rev}:{_gitpath(path)}"], cwd)
    return r.stdout.strip() if r.returncode == 0 else None


# Myers IMPOSÉ des deux côtés : les comptes de `--numstat` dépendent de l'algorithme (Myers est minimal,
# histogram et patience ne le sont pas), et `git diff` lit `diff.algorithm` là où `diff-tree` l'ignore —
# laisser la configuration choisir fabriquerait des écarts entre le compte attendu et le compte observé.
_DIFF_STABLE = ["--no-ext-diff", "--no-textconv", "--diff-algorithm=myers"]


def _lire_numstat(sortie: str):
    """Première ligne `ajoutées<TAB>supprimées<TAB>…` -> (int, int), ("-", "-") pour un binaire ; None s'il
    n'y en a AUCUNE — l'appelant dit ce que l'absence signifie, cette fonction ne l'invente pas."""
    for ligne in (sortie or "").splitlines():
        parts = ligne.split("\t")
        if len(parts) >= 3:
            a, s = parts[0].strip(), parts[1].strip()
            return (int(a), int(s)) if a.isdigit() and s.isdigit() else ("-", "-")
    return None


def _numstat_blobs(avant: str, apres: str, *, cwd: str):
    """Delta (ajoutées, supprimées) de `avant` à `apres`, calculé par GIT — jamais par difflib, dont les
    comptes ne sont pas ceux que `git commit` affiche."""
    if avant == apres:
        return (0, 0)                               # même SHA : aucune différence, MESURÉE
    r = _run_git(["diff", "--numstat"] + _DIFF_STABLE + [avant, apres], cwd)
    ns = _lire_numstat(r.stdout) if r.returncode == 0 else None
    if ns is None:
        raise RuntimeError(f"git diff --numstat {avant[:8]} {apres[:8]} n'a rendu aucun compte : "
                           f"{r.stderr.strip()}")
    return ns


def _numstat_commit(sha: str, path: str, *, cwd: str):
    """(ajoutées, supprimées) que le commit `sha` porte pour `path` — le compte que `git commit` affiche — ou
    None s'il ne le porte pas."""
    r = _run_git(["diff-tree", "--no-commit-id", "--numstat", "-r", "--root"] + _DIFF_STABLE
                 + [sha, "--", _gitpath(path)], cwd)
    return _lire_numstat(r.stdout) if r.returncode == 0 else None


def _parent(sha: str, *, cwd: str):
    """Premier parent de `sha`, ou None (commit racine)."""
    r = _run_git(["rev-parse", "--verify", "-q", f"{sha}^"], cwd)
    return r.stdout.strip() if r.returncode == 0 else None


def _dans_index(path: str, *, cwd: str) -> bool:
    return _run_git(["ls-files", "--error-unmatch", "--", _gitpath(path)], cwd).returncode == 0


def _git_commit_pathspec(chemins, message: str, *, cwd: str):
    """`git commit -F - -- <chemins>` : le message par l'entrée standard (aucun shell, donc ni backticks ni
    guillemets à échapper), les crochets tournent. Point d'injection des tests de P2.122 (c)."""
    return subprocess.run(["git", "commit", "-F", "-", "--"] + list(chemins), cwd=cwd, input=message,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# « [branche abc1234] sujet », « [main (root-commit) abc1234] sujet », « [detached HEAD abc1234] sujet »
_RESUME_COMMIT = re.compile(r"^\[[^\]\n]*?([0-9a-f]{7,64})\] ", re.M)


def _sha_du_commit(sortie: str, *, cwd: str):
    """Le commit que `git commit` vient de créer, lu dans SA sortie — jamais `rev-parse HEAD`, qu'un commit
    concurrent peut avoir déjà déplacé. None si la sortie ne le nomme pas."""
    trouves = _RESUME_COMMIT.findall(sortie or "")
    if not trouves:
        return None
    r = _run_git(["rev-parse", "--verify", "-q", f"{trouves[-1]}^{{commit}}"], cwd)
    return r.stdout.strip() if r.returncode == 0 else None


def commit_exact(paths, message: str, attendu: dict, *, owner: str = None, snapshot_dir: str = None,
                 cwd: str = _ROOT):
    """P2.122 (b)+(c) — committe EXACTEMENT `attendu` sur `paths` : vérification et commit dans le MÊME appel,
    puis le compte du commit confronté au delta attendu. Renvoie {"commit", "parent", "parent_attendu",
    "numstat": {chemin: {"attendu": (a, s), "observe": (a, s)}}, "sortie": stdout de git, "sortie_crochets":
    stderr de git — où git renvoie la sortie des crochets, donc le chiffre des portes qui signalent sans bloquer}.

    AVANT le commit, refus — rien n'est committé, le disque n'est jamais touché :
      * `ValueError` : aucun chemin (un commit sans pathspec emporterait l'index ENTIER), message vide, ou
        attendu qui ne couvre pas exactement les chemins ;
      * `NoSnapshotError` / `ForeignHunkDetected(objet="attendu")` : avec `owner`, l'attendu reprend un bloc
        présent sur le disque AVANT l'empreinte et absent de HEAD (forme e21c1f3) ;
      * `ForeignHunkDetected(objet="disque")` : le disque porte un bloc absent de HEAD et de l'attendu
        (forme 9bf30520) ;
      * `ExpectedContentMismatch` : fichier absent, disque différent de l'attendu, ou attendu identique à
        HEAD (rien à committer — peut-être déjà porté par le commit d'un autre : `detect_preempted`) ;
      * `CommitFailed` : `git commit` a échoué (porte rouge…), sortie complète jointe.
    APRÈS le commit : `CommitNotExact` si un chemin n'est pas porté, ou si son blob ou son compte diffère de
    l'attendu — le commit existe, il est nommé, jamais défait.

    Le commit passe par `git commit -F - -- <chemins>` : les crochets tournent (jamais `--no-verify`), le
    compare-and-swap de git sur HEAD aussi, et l'index est réaligné sur le contenu committé. HEAD est lu UNE
    fois (`sha0`) : contenus, delta attendu et parent se jugent contre lui."""
    voulus = [_gitpath(p) for p in (paths or [])]
    if not voulus:
        raise ValueError("commit_exact : aucun chemin — un commit sans pathspec emporterait l'index ENTIER "
                         "(E10 occ. 19) : refusé")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("commit_exact : message de commit vide")
    voulu = _attendu_par_chemin(voulus, attendu)
    sha0 = _head_sha(cwd)

    # (1) forme e21c1f3 — l'attendu ne reprend pas un travail étranger PRÉ-EXISTANT : l'empreinte le sait
    if owner is not None:
        d = snapshot_dir or _DEFAULT_SNAPSHOT_DIR
        report, tardives = {}, []
        for path, contenu in voulu.items():
            snap = _load_snapshot(path, owner, d)
            head_now = _normaliser(_commit_content(sha0, path, cwd=cwd) or "").splitlines() if sha0 else []
            foreign = [h for h in _foreign_hunks((snap["head_content"] or "").splitlines(),
                                                 (snap["working_tree_content"] or "").splitlines(),
                                                 contenu.splitlines())
                       if not _contains_block(head_now, h["lines"])]   # committé depuis : plus étranger
            if foreign:
                report[path] = foreign
                if snap.get("dirty_at_snapshot"):
                    tardives.append(path)
        if report:
            raise ForeignHunkDetected(report, dirty_at_snapshot=tardives, objet="attendu")

    # (2) forme 9bf30520, (3) exactitude, (4) delta attendu calculé par git — le disque lu UNE fois
    etat = _confronter_disque(voulu, sha0, cwd=cwd)
    etrangers = {p: e["etrangers"] for p, e in etat.items() if e["etrangers"]}
    if etrangers:
        raise ForeignHunkDetected(etrangers, objet="disque")
    ecarts, prevu, vide = {}, {}, None
    for path, e in etat.items():
        if e["brut"] is None:
            ecarts[path] = {"raison": "fichier ABSENT du disque"}
            continue
        if e["disque"] != voulu[path]:
            absentes = _added_blocks(e["disk_lines"], e["attendu_lines"])
            en_trop = _added_blocks(e["attendu_lines"], e["disk_lines"])
            raison = ("le disque DIFFÈRE de l'attendu" if (absentes or en_trop) else
                      "le disque ne diffère de l'attendu que par la FIN DE FICHIER (saut de ligne final)")
            ecarts[path] = {"raison": raison, "absentes": absentes, "en_trop": en_trop}
            continue
        blob = _blob_de(e["brut"], path, cwd=cwd)      # le disque BRUT : c'est lui que git lira
        avant = _blob_au(sha0, path, cwd=cwd)
        if avant == blob:
            ecarts[path] = {"raison": "l'attendu est IDENTIQUE à HEAD : rien à committer — si tu l'avais "
                                      "modifié, ton travail est peut-être déjà dans le commit d'un autre "
                                      "(detect_preempted)"}
            continue
        if avant is None and vide is None:
            vide = _blob_de(b"", None, cwd=cwd)
        prevu[path] = {"blob": blob, "neuf": avant is None,
                       "numstat": _numstat_blobs(avant or vide, blob, cwd=cwd)}
    if ecarts:
        raise ExpectedContentMismatch(ecarts)

    # (5) le commit — par pathspec, jamais nu ; un chemin NEUF est d'abord annoncé, sinon git le refuse
    annonces = []

    def _retirer_annonces():
        for p in annonces:                             # l'annonce n'a pas servi : retirée de l'index
            _run_git(["rm", "--cached", "-q", "--", p], cwd)

    for path in voulus:
        if prevu[path]["neuf"] and not _dans_index(path, cwd=cwd):
            r = _run_git(["add", "--intent-to-add", "--", path], cwd)
            if r.returncode != 0:
                _retirer_annonces()
                raise CommitFailed(r.returncode, r.stdout, r.stderr)
            annonces.append(path)
    r = _git_commit_pathspec(voulus, message, cwd=cwd)
    if r.returncode != 0:
        _retirer_annonces()
        raise CommitFailed(r.returncode, r.stdout, r.stderr)
    sha = _sha_du_commit(r.stdout, cwd=cwd)
    if sha is None:
        raise RuntimeError("git commit a réussi mais sa sortie ne NOMME pas le commit : il n'est PAS vérifié "
                           f"(`git log -1` pour le retrouver).\n{r.stdout}")

    # (6) ce que le commit PORTE, confronté à ce qui était attendu — blob ET compte
    parent = _parent(sha, cwd=cwd)
    porte = _paths_in_commit(sha, cwd=cwd) or set()
    ecarts, observes = {}, {}
    for path in voulus:
        est_porte = path in porte
        observes[path] = _numstat_commit(sha, path, cwd=cwd) if est_porte else None
        if (est_porte and observes[path] == prevu[path]["numstat"]
                and _blob_au(sha, path, cwd=cwd) == prevu[path]["blob"]):
            continue
        commit_lines = _normaliser(_commit_content(sha, path, cwd=cwd) or "").splitlines()
        attendu_lines = voulu[path].splitlines()
        ecarts[path] = {"porte": est_porte, "numstat_attendu": prevu[path]["numstat"],
                        "numstat_observe": observes[path],
                        "etrangeres": _added_blocks(attendu_lines, commit_lines),
                        "absentes": _added_blocks(commit_lines, attendu_lines)}
    if owner is not None:
        _record_own_commit(sha, voulus, owner=owner, snapshot_dir=snapshot_dir)
    if ecarts:
        raise CommitNotExact(sha, ecarts, parent=parent, parent_attendu=sha0)
    return {"commit": sha, "parent": parent, "parent_attendu": sha0, "sortie": r.stdout,
            "sortie_crochets": r.stderr,    # git y renvoie la sortie des crochets : les portes qui SIGNALENT
            "numstat": {p: {"attendu": prevu[p]["numstat"], "observe": observes[p]} for p in voulus}}


def _lire_attendus(specs):
    """`CHEMIN=FICHIER` répétés (CLI) -> {chemin: contenu lu dans FICHIER}, dans l'ordre donné."""
    out = {}
    for spec in specs or []:
        chemin, sep, fichier = spec.partition("=")
        if not sep or not chemin or not fichier:
            raise ValueError(f"--attendu attend CHEMIN=FICHIER, reçu {spec!r}")
        with open(fichier, encoding="utf-8") as f:
            out[chemin] = f.read()
    return out


# --- CLI ---------------------------------------------------------------------------------------------

def _cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("snapshot", help="prendre l'empreinte AVANT édition")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--owner", default="default")
    sp.add_argument("--dir", default=None)
    sp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")
    sp.add_argument("--session-id", default=None,
                    help="identité de session inscrite dans l'empreinte (défaut : $AGAGI_SESSION_ID puis"
                         " $CLAUDE_CODE_SESSION_ID ; sans identité, `declare` ne la touchera jamais)")

    vp = sub.add_parser("verify", help="vérifier AVANT commit — sort en erreur si un hunk est étranger")
    vp.add_argument("paths", nargs="+")
    vp.add_argument("--owner", default="default")
    vp.add_argument("--dir", default=None)
    vp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")
    vp.add_argument("--strict", action="store_true",
                    help="rendre BLOQUANT l'avertissement de préemption (sens B), non bloquant par défaut")
    vp.add_argument("--attendu", action="append", default=None, metavar="CHEMIN=FICHIER",
                    help="P2.122 : juger le DISQUE contre le contenu attendu de CHEMIN, lu dans FICHIER "
                         "(répétable, un par chemin) — tout bloc absent de HEAD et de l'attendu est refusé")

    xp = sub.add_parser("commit-exact", help="P2.122 : committer EXACTEMENT le contenu attendu — vérification "
                        "et commit dans le même appel, compte du commit confronté au delta attendu")
    xp.add_argument("--attendu", action="append", required=True, metavar="CHEMIN=FICHIER",
                    help="contenu attendu de CHEMIN, lu dans FICHIER (répétable) : ce que TU as produit, "
                         "jamais relu sur le disque partagé")
    xm = xp.add_mutually_exclusive_group(required=True)
    xm.add_argument("-m", "--message", default=None)
    xm.add_argument("-F", "--message-file", default=None)
    xp.add_argument("--owner", default=None,
                    help="confronter aussi l'attendu à l'empreinte de cet owner (forme e21c1f3)")
    xp.add_argument("--dir", default=None)
    xp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    cp = sub.add_parser("confirm", help="vérifier APRÈS commit que le commit porte bien tous les chemins")
    cp.add_argument("sha")
    cp.add_argument("paths", nargs="+")
    cp.add_argument("--owner", default=None,
                    help="inscrire ce SHA comme commit de cet owner (désamorce l'alerte de préemption)")
    cp.add_argument("--dir", default=None)
    cp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    dp = sub.add_parser("declare", help="APRÈS commit (hook post-commit) : inscrire le SHA dans les "
                        "empreintes de LA SESSION COURANTE dont le chemin est porté par le commit")
    dp.add_argument("sha", nargs="?", default="HEAD")
    dp.add_argument("--session-id", default=None,
                    help="identité de session (défaut : $AGAGI_SESSION_ID puis $CLAUDE_CODE_SESSION_ID ;"
                         " SANS identité, rien n'est déclaré — jamais deviné)")
    dp.add_argument("--dir", default=None)
    dp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")

    kp = sub.add_parser("scan", help="balayer MES empreintes et signaler les préemptions (avertissement)")
    kp.add_argument("--dir", default=None)
    kp.add_argument("--cwd", default=None, help="racine du dépôt (défaut : ce dépôt-ci)")
    kp.add_argument("--session-id", default=None, help="identité explicite (défaut : environnement)")

    rp = sub.add_parser("retire", help="refermer une unite de travail : retirer ses empreintes")
    rp.add_argument("paths", nargs="*")
    rp.add_argument("--owner", default=None)
    rp.add_argument("--dir", default=None)

    args = ap.parse_args(argv)
    # `retire` ne touche pas au depot : il n'a pas de `--cwd`, et le lire durement le cassait.
    cwd = getattr(args, "cwd", None) or _ROOT

    if args.cmd == "snapshot":
        for p in snapshot(args.paths, owner=args.owner, snapshot_dir=args.dir, cwd=cwd,
                          session_id=args.session_id):
            print(f"empreinte écrite : {p}")
        return 0

    if args.cmd == "retire":
        for f in retire_snapshots(args.paths, owner=args.owner, snapshot_dir=args.dir):
            print(f"empreinte retiree : {f}")
        return 0

    if args.cmd == "scan":
        rapport = scan_own_snapshots(session_id=args.session_id, snapshot_dir=args.dir, cwd=cwd)
        for owner, rep in rapport.items():
            print(f"[owner={owner}] {WorkPreempted(rep)}", file=sys.stderr)
        if not rapport:
            print("OK : aucune préemption sur les empreintes de cette session.")
        return 0                                      # JAMAIS bloquant : cf. scan_own_snapshots

    if args.cmd == "declare":
        # Un post-commit ne peut ni bloquer ni faire échouer le commit : sortie 0 QUOI QU'IL ARRIVE, et
        # une ligne par déclaration seulement (silence = rien à déclarer pour cette session).
        try:
            declared = declare_head_commit(args.sha, session_id=args.session_id,
                                           snapshot_dir=args.dir, cwd=cwd)
        except Exception as e:  # noqa: BLE001 — best-effort assumé, cf. docstring de declare_head_commit
            print(f"authorship : déclaration ignorée ({e})", file=sys.stderr)
            return 0
        for dcl in declared:
            print(f"authorship : {dcl['commit'][:8]} déclaré pour owner={dcl['owner']!r} sur {dcl['path']}")
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

    if args.cmd == "commit-exact":
        try:
            attendu = _lire_attendus(args.attendu)
            if args.message_file:
                with open(args.message_file, encoding="utf-8") as f:
                    message = f.read()
            else:
                message = args.message
            res = commit_exact(list(attendu), message, attendu, owner=args.owner,
                               snapshot_dir=args.dir, cwd=cwd)
        except CommitNotExact as e:
            print(f"ERREUR : {e}", file=sys.stderr)
            return 3                                   # le commit EXISTE : code distinct, ne pas pousser
        except (ValueError, TypeError, OSError, NoSnapshotError, ForeignHunkDetected,
                ExpectedContentMismatch, CommitFailed) as e:
            print(f"ERREUR (rien n'est committé) : {e}", file=sys.stderr)
            return 1
        if res["sortie_crochets"].strip():            # une porte qui signale sans bloquer : son chiffre
            print(res["sortie_crochets"].rstrip(), file=sys.stderr)   # reste sous les yeux (porte 16)
        if res["sortie"].strip():
            print(res["sortie"].rstrip())
        for path, ns in res["numstat"].items():
            print(f"OK : {res['commit'][:8]} porte EXACTEMENT l'attendu — {path} : compte "
                  f"{_fmt_numstat(ns['observe'])} (attendu {_fmt_numstat(ns['attendu'])})")
        if res["parent"] != res["parent_attendu"]:
            print(f"note : un commit s'est intercalé ({(res['parent_attendu'] or '(aucun)')[:8]} -> "
                  f"{(res['parent'] or '(aucun)')[:8]}) sans toucher ces chemins")
        return 0

    if args.attendu:                                   # verify --attendu (P2.122) : le DISQUE, pas l'index
        try:
            checked = verify(args.paths, cwd=cwd, attendu=_lire_attendus(args.attendu))
        except (ValueError, TypeError, OSError, ForeignHunkDetected) as e:
            print(f"ERREUR : {e}", file=sys.stderr)
            return 1
        for path, n in checked.items():
            print(f"OK : {path} — {n} bloc(s) du disque absent(s) de HEAD, tous couverts par l'attendu")
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
