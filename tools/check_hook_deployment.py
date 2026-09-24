#!/usr/bin/env python
"""P2.108 — LA COPIE DÉPLOYÉE DES CROCHETS EST-ELLE CELLE QUE LE DÉPÔT A RELUE ?

`.git/hooks/` n'est pas versionné : les crochets de `tools/hooks/` y sont recopiés **à la main**.
Entre les deux, rien ne tient. Ce cliquet compare les deux côtés et refuse la divergence que
personne ne peut voir autrement.

POURQUOI, ET DANS LES DEUX SENS — les deux occurrences sont RÉELLES, pas hypothétiques :

  (1) COPIE EN RETARD. Une porte ajoutée à `tools/hooks/pre-commit` et committée ne s'exécute chez
      personne tant que la copie n'est pas refaite. Le dépôt annonce alors N gardes et en fait
      tourner N-1 : un compteur juste, une garde absente, et AUCUN signal — c'est la forme (a) du
      biais de ce dépôt (une absence devient une affirmation de fond).

  (2) COPIE EN AVANCE. Mesuré par la session PM : un worktree a écrit dans le crochet COMMUN une
      porte qui n'existe dans AUCUN commit. ⚠️ `core.hooksPath` vaut ici un chemin ABSOLU vers le
      `.git/hooks` du dépôt PRINCIPAL, donc TOUS les worktrees et toutes les sessions exécutent le
      MÊME fichier : y écrire arme la flotte entière. Du code que personne n'a relu bloquait chaque
      session qui committait un record. C'est le sens grave, et c'est le seul que ce cliquet REFUSE.

CE QU'IL NE PEUT PAS VOIR, et il faut l'écrire parce qu'un lecteur le croira couvert : **ce cliquet
est lancé PAR le pre-commit déployé**. Si `.git/hooks/pre-commit` est absent ou tronqué, il ne
tourne pas du tout — l'absence du pre-commit est structurellement indétectable de l'intérieur. En
revanche l'absence de TOUT AUTRE crochet (`commit-msg`, `post-commit`) est parfaitement visible
d'ici, et c'est elle qui compte : un `commit-msg` manquant rouvre le trou de la fusion (git ne lance
AUCUN pre-commit sur une fusion propre — 0 appel mesuré).

LES QUATRE ÉTATS, et pourquoi un seul bloque :
  CONFORME   la copie déployée == la version que ce commit livre (ou HEAD hors commit).
  PÉRIMÉ     la copie déployée == une version PLUS ANCIENNE, déjà committée. Personne n'a écrit de
             code non relu : quelqu'un a oublié un `cp`. On CRIE avec la commande exacte, on ne
             bloque pas — bloquer arrêterait toute la flotte sur un fichier partagé, et le commit
             qui MET À JOUR un crochet est toujours dans cet état par construction.
  INCONNU    la copie déployée ne correspond à AUCUNE version jamais committée. C'est (2). REFUSE.
  ABSENT     un crochet versionné n'est pas déployé. REFUSE, sauf tolérance déclarée dans la
             baseline (un déploiement arme toute la flotte : c'est un acte annoncé, pas un effet de
             bord d'un commit).
  ORPHELIN   un crochet déployé sans aucune source versionnée. REFUSE : c'est (2) sans même un
             fichier à relire.

⚠️ NORMALISER LES FINS DE LIGNE AVANT DE COMPARER. Mesuré le 2026-09-24 : `core.autocrlf=true` sur
cette machine, donc la copie déployée est en CRLF sur le disque alors que le blob de git est en LF.
Un `diff` brut rend 46 lignes d'écart sur deux fichiers IDENTIQUES ; sans `\r\n -> \n` des deux
côtés, ce cliquet crierait au loup en permanence sous Windows — et une garde qui crie toujours est
une garde qu'on désactive.

⚠️ LA RÉFÉRENCE EST L'INDEX, PAS LE DISQUE. L'arbre est PARTAGÉ entre une dizaine de sessions :
`tools/hooks/pre-commit` peut porter, à cet instant, l'édition en cours de quelqu'un d'autre. Juger
contre le disque ferait rougir ce commit-ci pour le travail non committé d'un autre. On lit donc le
contenu que CE commit livre (`git show :<chemin>`, qui suit `GIT_INDEX_FILE`), et HEAD hors commit.

Sortie : 0 si tout est CONFORME ou PÉRIMÉ (ou toléré par la baseline), 1 sinon.
Baseline : `tools/hook_deployment_baseline.json`, `{"<nom>": "<état toléré>"}`.
"""
import json
import os
import subprocess
import sys

_ICI = os.path.dirname(os.path.abspath(__file__))
_RACINE = os.path.dirname(_ICI)
_SOURCE = os.path.join("tools", "hooks")
_BASELINE = os.path.join(_ICI, "hook_deployment_baseline.json")
_MAX_REVISIONS = 200  # borne de coût ; au 2026-09-24 le plus vieux crochet en porte 20.

CONFORME, PERIME, INCONNU, ABSENT, ORPHELIN = "CONFORME", "PERIME", "INCONNU", "ABSENT", "ORPHELIN"
_BLOQUANTS = (INCONNU, ABSENT, ORPHELIN)


def _git(*args, binaire=False):
    """Rend (rc, sortie). Jamais d'exception : hors dépôt, ce cliquet doit se TAIRE, pas planter."""
    r = subprocess.run(["git", *args], capture_output=True, cwd=_RACINE)
    return r.returncode, (r.stdout if binaire else r.stdout.decode("utf-8", "replace"))


def norme(contenu):
    """Fins de ligne normalisées et queue rognée. `None` reste `None` : une absence n'est pas un
    contenu vide (porte 14 — un défaut fabriqué rendrait ABSENT et CONFORME indiscernables)."""
    if contenu is None:
        return None
    return contenu.replace(b"\r\n", b"\n").replace(b"\r", b"\n").rstrip() + b"\n"


def repertoire_deploye():
    """Le répertoire que git lance VRAIMENT. `core.hooksPath` l'emporte sur `.git/hooks`, et ce
    dépôt le fixe à un chemin ABSOLU — c'est pourquoi tous les worktrees partagent un seul fichier.
    Rend `None` hors d'un dépôt git (l'export temporaire d'un commit, par exemple)."""
    rc, chemin = _git("config", "--get", "core.hooksPath")
    if rc == 0 and chemin.strip():
        return os.path.normpath(chemin.strip())
    rc, commun = _git("rev-parse", "--git-common-dir")
    if rc != 0 or not commun.strip():
        return None
    commun = commun.strip()
    if not os.path.isabs(commun):
        commun = os.path.join(_RACINE, commun)
    return os.path.normpath(os.path.join(commun, "hooks"))


def crochets_versionnes():
    """Les crochets que le dépôt PUBLIE, lus dans l'INDEX (donc : ce que ce commit livre)."""
    rc, sortie = _git("ls-files", "--", _SOURCE.replace(os.sep, "/"))
    if rc != 0:
        return []
    noms = []
    for ligne in sortie.splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.endswith("/"):
            noms.append(os.path.basename(ligne))
    return sorted(set(noms))


def contenu_livre(nom):
    """Contenu que CE commit livre : l'index d'abord (il suit `GIT_INDEX_FILE`), HEAD ensuite."""
    chemin = f"{_SOURCE}/{nom}".replace(os.sep, "/")
    for spec in (f":{chemin}", f"HEAD:{chemin}"):
        rc, blob = _git("show", spec, binaire=True)
        if rc == 0:
            return blob
    return None


def revisions_connues(nom, limite=_MAX_REVISIONS):
    """Tous les contenus que ce crochet a EU, normalisés. Sert à séparer « quelqu'un a oublié un
    cp » (le contenu déployé a existé dans un commit) de « quelqu'un a écrit dans le crochet
    commun » (il n'a jamais existé nulle part) — deux diagnostics aux remèdes opposés."""
    chemin = f"{_SOURCE}/{nom}".replace(os.sep, "/")
    rc, sortie = _git("rev-list", f"--max-count={limite}", "HEAD", "--", chemin)
    if rc != 0:
        return set()
    vus = set()
    for sha in sortie.split():
        rc, blob = _git("show", f"{sha}:{chemin}", binaire=True)
        if rc == 0:
            vus.add(norme(blob))
    return vus


_MESURER = object()
"""Sentinelle d'injection. ⚠️ `None` ne peut PAS jouer ce rôle : ici `None` est un CONTENU — celui
d'un crochet ABSENT — et le confondre avec « paramètre non fourni » rend l'absence inexprimable, donc
INTESTABLE. Défaut trouvé par les cas gelés à leur premier tir (`livre=None` allait relire le dépôt
réel au lieu de simuler un crochet sans source) : la même confusion absence/vide que ce dépôt traque
chez ses sondes, commise dans le paramétrage de la garde."""


def etat_un_crochet(nom, dossier, livre=_MESURER, deploye=_MESURER, anciennes=None):
    """INSTRUMENT. Rend l'état d'UN crochet, et JAMAIS un verdict de fond sur une entrée vide :
    sans contenu versionné NI contenu déployé, il rend `None` — « je ne sais pas » — plutôt que
    CONFORME. Les trois contenus sont injectables, pour une calibration à dose connue sans dépôt."""
    if livre is _MESURER:
        livre = contenu_livre(nom)
    if deploye is _MESURER:
        deploye = None
        chemin = os.path.join(dossier, nom) if dossier else None
        if chemin and os.path.isfile(chemin):
            with open(chemin, "rb") as fh:
                deploye = fh.read()
    a, b = norme(livre), norme(deploye)
    if a is None and b is None:
        return None
    if a is None:
        return {"nom": nom, "etat": ORPHELIN, "detail":
                "déployé sans aucune source versionnée dans tools/hooks/"}
    if b is None:
        return {"nom": nom, "etat": ABSENT, "detail": f"tools/hooks/{nom} n'est pas déployé"}
    if a == b:
        return {"nom": nom, "etat": CONFORME, "detail": "identique à la version livrée"}
    if anciennes is None:
        anciennes = revisions_connues(nom)
    if b in anciennes:
        return {"nom": nom, "etat": PERIME, "detail":
                "la copie déployée est une version ANCIENNE, déjà committée : un cp a été oublié"}
    return {"nom": nom, "etat": INCONNU, "detail":
            "la copie déployée ne correspond à AUCUNE version jamais committée — du code que "
            "personne n'a relu tourne sur toute la flotte"}


def etats(dossier=None):
    """Rend {nom: état} pour l'UNION des crochets versionnés et des crochets déployés."""
    dossier = repertoire_deploye() if dossier is None else dossier
    noms = set(crochets_versionnes())
    if dossier and os.path.isdir(dossier):
        for f in os.listdir(dossier):
            if f.endswith(".sample"):
                continue
            if os.path.isfile(os.path.join(dossier, f)):
                noms.add(f)
    sortie = {}
    for nom in sorted(noms):
        e = etat_un_crochet(nom, dossier)
        if e is not None:
            sortie[nom] = e
    return sortie


def baseline():
    if not os.path.isfile(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return {k: v for k, v in json.load(fh).items() if not k.startswith("_")}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dossier = repertoire_deploye()
    if dossier is None:
        print("crochets : hors d'un dépôt git (export temporaire ?) — rien à juger, et je le DIS")
        return 0
    if not crochets_versionnes():
        print(f"crochets : AUCUN crochet versionné sous {_SOURCE}/ — je ne peux rien affirmer.")
        print("   Soit l'inventaire est cassé, soit le dépôt a perdu ses crochets : les deux se")
        print("   corrigent, aucun ne se tait.")
        return 1

    mesures = etats(dossier)
    gelés = baseline()
    if "--update-baseline" in argv:
        # Les clés « _ » portent la JUSTIFICATION de chaque gel et sa condition de sortie : les
        # perdre à la première mise à jour ferait d'une dette expliquée une dette anonyme.
        notes = {}
        if os.path.isfile(_BASELINE):
            with open(_BASELINE, encoding="utf-8") as fh:
                notes = {k: v for k, v in json.load(fh).items() if k.startswith("_")}
        nouvelle = dict(notes)
        nouvelle.update({n: e["etat"] for n, e in mesures.items() if e["etat"] in _BLOQUANTS})
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump(nouvelle, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        print(f"baseline de déploiement des crochets figée : {nouvelle}")
        return 0

    fautifs = []
    for nom, e in sorted(mesures.items()):
        marque = {CONFORME: "ok ", PERIME: "!! ", INCONNU: "KO ", ABSENT: "KO ", ORPHELIN: "KO "}[e["etat"]]
        toléré = gelés.get(nom) == e["etat"]
        if e["etat"] in _BLOQUANTS and toléré:
            marque = "(gelé) "
        print(f"  {marque}{nom:14s} {e['etat']:9s} {e['detail']}")
        if e["etat"] in _BLOQUANTS and not toléré:
            fautifs.append(e)

    perimes = [n for n, e in mesures.items() if e["etat"] == PERIME]
    if perimes:
        print("")
        print("⚠️ COPIE EN RETARD — les portes qui tournent ne sont pas celles que le dépôt publie :")
        for n in perimes:
            print(f'   cp tools/hooks/{n} "{os.path.join(dossier, n)}"')
    print(f"crochets : {len(mesures)} examinés, {len(fautifs)} refusés, {len(perimes)} périmés "
          f"(déployés dans {dossier})")
    if fautifs:
        print("")
        for e in fautifs:
            print(f"-> {e['nom']} : {e['etat']} — {e['detail']}")
        print("   Un crochet déployé s'exécute chez TOUTES les sessions (core.hooksPath absolu).")
        print("   Remettre la copie en conformité, ou committer ce qui a été écrit dans le crochet")
        print("   commun pour qu'il soit relu. Geler EN CONNAISSANCE (dernier recours) :")
        print("   python tools/check_hook_deployment.py --update-baseline")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
