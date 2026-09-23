"""Cliquet de FRAÎCHEUR du backlog — un backlog qui ment sur son état fait refaire ce qui est fait.

Problème visé, mesuré le 2026-09-01. `docs/roadmap/PRIORITES_ET_DETTES.md` est le document que CLAUDE.md
désigne comme « à consulter avant de choisir quoi faire ». Un audit systématique y a trouvé **douze**
péremptions, dont :

* une direction présentée comme « à faire » que le dépôt avait déjà tranchée (D1 = EDR-EVO-019) — trouvée
  en allant y chercher quoi faire, c'est-à-dire au pire moment ;
* une piste listée « reste ouvert » que [[EDR-EVO-010]] a RÉFUTÉE, en contradiction avec le bloc de
  clôture situé 65 lignes plus haut dans le même fichier ;
* une classe d'erreur déclarée « la SEULE sans aucune garde » alors qu'elle est close depuis un mois ;
* un chiffre-phare faux d'un facteur 3 (« 71 instruments, 1 calibré » contre 101 / 32) ;
* quatre numéros de tâche (P2.0-bis, P2.1, P2.2, P2.3) présents DEUX fois avec des contenus différents.

Le coût de cette dette n'est pas cosmétique : c'est du temps de calcul dépensé à relancer une expérience
déjà faite, exactement ce que le protocole de pré-vol cherche à éviter.

CE QUE CE CLIQUET VÉRIFIE — trois propriétés DÉCIDABLES, et rien d'autre :

1. **Liens morts** — un `[[EDR-XXX]]` cité dans le backlog dont aucun record ne porte l'id.
2. **Numéros dupliqués** — un même `P<n>.<m>` en tête de deux entrées : l'une des deux est forcément
   périmée, et rien ne dit laquelle. Une tête COMPOSITE (`**P1.x / P2.45 —`) vote pour chacun de
   ses numéros ; `P1.x` est un substitut (« à numéroter »), pas un numéro.
3. **Chemins morts** — un `chemin/fichier.py` cité entre backticks qui n'existe plus.

CE QU'IL NE VÉRIFIE PAS. Il ne juge pas si une entrée « ouverte » a été tranchée par un record : ça
demande de lire et de comprendre les deux, et aucune heuristique lexicale ne le fait honnêtement. C'est
le travail d'un audit — ce cliquet attrape seulement la dérive MÉCANIQUE, celle qui s'accumule sans que
personne décide rien.

RÈGLE À CLIQUET, comme `check_record_links.py` : la dette LÉGATAIRE est gelée, aucune NOUVELLE.

Usage :
  python tools/check_backlog_freshness.py                    # cliquet : exit 1 sur toute NOUVELLE péremption
  python tools/check_backlog_freshness.py --report           # état complet, exit 0
  python tools/check_backlog_freshness.py --update-baseline  # gèle l'état courant
"""
import argparse
import collections
import json
import re
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKLOG = os.path.join(_ROOT, "docs", "roadmap", "PRIORITES_ET_DETTES.md")
_BASELINE = os.path.join(_ROOT, "tools", "backlog_freshness_baseline.json")
_DOCS = os.path.join(_ROOT, "docs")

_WIKILINK = re.compile(r"\[\[([A-Za-z0-9_.\-]+)\]\]")
# P3.5 (a), 2026-09-15 : TITRES COMPOSITES. `**P1.x / P2.45 — ...` porte DEUX numeros et un `x` de
# substitution (« a numeroter »). L'ancien motif exigeait `P\d+\.\d+` et le titre ENTIER lui
# echappait : ni entree (son bloc etait avale par la precedente), ni numero (P2.45 est en tete d'une
# SECONDE entree, l.2981, et le compte de doublons rendait OK). Un titre que le cliquet ne lit pas ne
# peut pas etre en double : entree invisible -> succes, la forme (a) de CLAUDE.md, commise par une garde.
_NUM = r"P\d+\.(?:\d+|x)(?:-bis)?"
_TETE = rf"^\*\*({_NUM}(?:\s*/\s*{_NUM})*)"
_TASKNUM = re.compile(_TETE + r"\b", re.M)
_BACKTICK_PATH = re.compile(r"`([\w][\w./-]*\.(?:py|md|json|yml|yaml))`")

# --- P2.29 : PÉREMPTION SÉMANTIQUE, par CLAUSE DÉCLARÉE ---------------------------------------------
# Le cliquet ne voyait que du SYNTAXIQUE (liens morts, numéros doubles, chemins disparus). Six entrées
# ont pu annoncer l'INVERSE de l'état mesuré pendant qu'il rendait « OK » — et elles ont été trouvées en
# relisant le backlog pour choisir quoi faire, c'est-à-dire au pire moment.
#
# Deviner la péremption depuis le TEXTE (dates, mot « OUVERTE ») serait proxifier ce qu'on ne sait pas
# mesurer — déjà déclaré non automatisable (E10 occ. 4). On fait donc DÉCLARER : une entrée fermable
# écrit sa CONDITION DE FERMETURE, et le cliquet vérifie CETTE clause.
#
#     <!-- closes_when:grep_present=tools/hooks/pre-commit::check_bar_separation -->
#
# ⚠️ Vocabulaire FERMÉ et prédicats PURS. Pas d'exécution de commande arbitraire depuis un document :
# un backlog est un fichier que n'importe quelle session édite, et un cliquet qui lance ce qu'on y écrit
# est une porte d'entrée, pas une garde. Un prédicat INCONNU est REFUSÉ bruyamment (jamais ignoré :
# un refus muet ferait croire à l'auteur qu'il a déclaré ce qu'il n'a pas déclaré).
#
# Les DEUX sens sont des violations, et le second est le plus utile :
#   * clause SATISFAITE + entrée déclarée OUVERTE  -> la fermeture est acquise et non enregistrée ;
#   * clause NON satisfaite + entrée déclarée CLOSE -> la fermeture a RÉGRESSÉ en silence.
_CLAUSE = re.compile(r"<!--\s*closes_when:([a-z_]+)=(.+?)\s*-->")
# `holds_when:` — SECOND predicat, ajoute le 2026-09-08 apres que le premier a mal vise.
# `closes_when:` decrit la fermeture de l'ENTREE ; pose sur un SOUS-ITEM il est mal attribue,
# et le cliquet reclame alors la fermeture de toute l'entree (mesure : P4.3, dont le sous-item
# SP-2 etait clos pendant que l'entree restait ouverte a juste titre).
# `holds_when:` dit autre chose : « cette affirmation doit RESTER vraie ». Une seule direction est
# une violation -- la clause CESSE d'etre satisfaite --, quel que soit l'etat de l'entree. C'est
# ce qu'il faut pour un fait etabli cite dans une entree encore ouverte, cas tres frequent.
_HOLDS = re.compile(r"<!--\s*holds_when:([a-z_]+)=(.+?)\s*-->")
_ENTREE = re.compile(_TETE + r"\s*[—-]", re.M)
_CLOSE_MARQUEURS = ("✅", "CLOS", "CLOSE", "FAIT", "PÉRIMÉE", "RETIRÉE", "TERMINÉ")


def _entrees(txt):
    """[(numéro, texte de l'entrée, déclarée close ?)] — une entrée va de son titre au titre suivant."""
    bornes = [(m.start(), m.group(1)) for m in _ENTREE.finditer(txt)]
    out = []
    for i, (deb, num) in enumerate(bornes):
        fin = bornes[i + 1][0] if i + 1 < len(bornes) else len(txt)
        bloc = txt[deb:fin]
        lignes = bloc.split("\n")
        entete = " ".join(lignes[:2])          # le statut vit sur le titre ou la ligne suivante
        out.append((num, bloc, any(m in entete for m in _CLOSE_MARQUEURS)))
    return out


def _tracked_by_git(rel):
    """True/False si `rel` est SUIVI par git dans `_ROOT` ; None si `_ROOT` n'est pas un depot (ou git absent) :
    indecidable, on ne refuse rien. P1.8 (b) : un fichier present ICI mais ignore ou non ajoute est ABSENT sur
    tout clone -- la CI est restee ROUGE trois pushes (2026-09-07 -> 09-09, `5b0025e`) sur une clause qui passait
    en local ; le cliquet mentait sur ce que la CI verrait."""
    try:
        r = subprocess.run(["git", "-C", _ROOT, "ls-files", "--error-unmatch", "--", rel],
                           capture_output=True)
    except OSError:
        return None
    if r.returncode == 0:
        return True
    if b"not a git repository" in r.stderr.lower():
        return None
    return False


def _evalue_clause(pred, arg):
    """-> (satisfaite ?, raison si le prédicat est REFUSÉ). Prédicats PURS uniquement."""
    if pred in ("path_present", "path_absent"):
        existe = _existe(arg)
        if existe and _tracked_by_git(arg) is False:
            return None, (f"`{pred}` cite {arg!r}, qui existe ICI mais n'est PAS SUIVI par git (ignore ou non" 
                          "ajoute) : la clause est INVERIFIABLE sur un clone -- c'est la CI rouge du 2026-09-07" 
                          "(`5b0025e`, un .pkl gitignore). Committer le fichier, ou ne pas le citer.")
        return (existe if pred == "path_present" else not existe), None
    if pred in ("grep_present", "grep_absent"):
        if "::" not in arg:
            return None, f"`{pred}` attend `chemin::motif` (reçu {arg!r})"
        rel, motif = arg.split("::", 1)
        contenu = _lire_fichier(rel)
        if contenu is None:
            return None, f"`{pred}` cite {rel!r}, qui n'existe pas — la clause est invérifiable"
        present = re.search(motif, contenu) is not None
        return (present if pred == "grep_present" else not present), None
    return None, (f"prédicat `{pred}` INCONNU — vocabulaire fermé : path_present, path_absent, "
                  "grep_present, grep_absent")


def _en_commit():
    """Sommes-nous DANS un commit (hook pre-commit) ? git pose alors `GIT_INDEX_FILE`, et pour un commit
    path-scopé cet index vaut HEAD + les seuls chemins du commit. Tout ce que la porte juge doit alors
    l'être contre CET index — ce qu'un clone verra — et non contre le disque, qui porte les hunks EN VOL
    de toutes les sessions de l'arbre partagé."""
    return bool(os.environ.get("GIT_INDEX_FILE"))


def _lire_backlog():
    """Le TEXTE du backlog à juger. En commit : la version de l'INDEX (`git show :chemin`) — c'est elle
    qui sera committée, pas celle du disque. Mesuré le 2026-09-22 (blocage circulaire à trois sessions) :
    la porte lisait le backlog sur disque, où l'entrée d'une session B citait des fichiers stagés par B
    mais absents de l'index temporaire de la session A qui committait — rouge chez A, à cause de B, sur
    un texte qu'A ne committait pas. Hors commit, ou si le chemin n'est pas dans l'index : le disque."""
    if _en_commit():
        try:
            rel = os.path.relpath(_BACKLOG, _ROOT).replace(os.sep, "/")
            r = subprocess.run(["git", "-C", _ROOT, "show", f":{rel}"], capture_output=True,
                               timeout=60)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="replace")
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return open(_BACKLOG, encoding="utf-8").read()


def _existe(rel):
    """Le chemin cité existe-t-il POUR CE QU'ON JUGE ? En commit : présent dans l'index (donc dans le
    commit à venir) ; hors commit : présent sur le disque. `_tracked_by_git` rend None hors dépôt —
    alors on ne conclut rien de l'index et on regarde le disque."""
    if _en_commit():
        t = _tracked_by_git(rel)
        if t is not None:
            return t
    return os.path.exists(os.path.join(_ROOT, rel))


def _lire_fichier(rel):
    """Contenu d'un fichier CIBLE de clause `grep_*`, ou None s'il n'existe pas POUR CE QU'ON JUGE (même
    règle que `_existe`). En commit : la version de l'INDEX. Mesuré le 2026-09-22, troisième point de
    lecture disque de cette porte : `def claude_code_llm_fn` écrit sur disque par une autre session (P2.66,
    non committé) satisfaisait la clause de P2.66 DANS LE COMMIT d'une session qui ne le committait pas —
    « entrée ouverte à condition satisfaite », rouge chez l'une à cause du travail en vol de l'autre."""
    if _en_commit():
        try:
            r = subprocess.run(["git", "-C", _ROOT, "show", f":{rel}"], capture_output=True, timeout=60)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="ignore")
            if _tracked_by_git(rel) is False:
                return None                   # absent de l'index : n'existe pas pour ce commit
        except (OSError, subprocess.SubprocessError):
            pass                              # git indécidable -> le disque, comme hors commit
    chemin = os.path.join(_ROOT, rel)
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def _chemins_suivis():
    """Chemins connus de git — lus dans l'INDEX (`git ls-files`), pas dans HEAD.

    Lire l'index et non HEAD est ce qui rend la garde utilisable : le commit qui AJOUTE un fichier le
    stage d'abord, donc un fichier stagé compte déjà comme suivi et ne bloque pas sa propre citation.
    `GIT_INDEX_FILE` est honoré par git, donc un index TEMPORAIRE (la méthode de commit du dépôt)
    fonctionne aussi. Git absent ou en erreur -> ensemble VIDE **signalé par `None`** serait un piège
    (tout deviendrait « non suivi ») : on rend alors un ensemble qui contient TOUT, c'est-à-dire qu'on
    ne conclut RIEN — une vérification qu'on ne peut pas faire ne produit pas de verdict (E4)."""
    try:
        r = subprocess.run(["git", "ls-files"], cwd=_ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return _TOUT_SUIVI
    if r.returncode != 0:
        return _TOUT_SUIVI
    return frozenset(l.strip() for l in r.stdout.splitlines() if l.strip())


class _ToutSuivi(frozenset):
    """Ensemble qui contient tout : `x in _TOUT_SUIVI` est vrai pour n'importe quel chemin."""

    def __contains__(self, item):
        return True


_TOUT_SUIVI = _ToutSuivi()


def scan_clauses(txt):
    """-> ({clef: description} des violations, nb d'entrées SANS clause)."""
    viol, sans = {}, 0
    for num, bloc, close in _entrees(txt):
        for pred, arg in _HOLDS.findall(bloc):
            ok, refus = _evalue_clause(pred, arg.strip())
            if refus:
                viol[f"holds-refusee:{num}:{pred}"] = f"{num} : {refus}"
            elif not ok:
                viol[f"holds-rompue:{num}:{pred}"] = (
                    f"{num} : une affirmation declaree PERMANENTE a cesse d'etre vraie "
                    f"(`{pred}={arg}`) -- l'entree cite un fait qui n'est plus etabli")
        clauses = _CLAUSE.findall(bloc)
        if not clauses:
            if not _HOLDS.findall(bloc):
                sans += 1
            continue
        for pred, arg in clauses:
            ok, refus = _evalue_clause(pred, arg.strip())
            if refus:
                viol[f"clause-refusee:{num}:{pred}"] = f"{num} : {refus}"
            elif ok and not close:
                viol[f"clause-close:{num}:{pred}"] = (
                    f"{num} : la condition de fermeture DÉCLARÉE est SATISFAITE "
                    f"(`{pred}={arg}`) mais l'entrée s'annonce encore ouverte")
            elif not ok and close:
                viol[f"clause-rouverte:{num}:{pred}"] = (
                    f"{num} : l'entrée s'annonce CLOSE mais sa condition de fermeture DÉCLARÉE "
                    f"n'est plus satisfaite (`{pred}={arg}`) — fermeture régressée en silence")
    return viol, sans



def _known_ids():
    """Tous les identifiants de records déclarés en frontmatter, plus les noms de fichiers."""
    ids = set()
    for root, _, files in os.walk(_DOCS):
        for f in files:
            if not f.endswith(".md"):
                continue
            ids.add(f[:-3])
            try:
                head = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read(2000)
            except OSError:
                continue
            m = re.search(r"^id:\s*(\S+)", head, re.M)
            if m:
                ids.add(m.group(1).strip())
            # `EVO-021_Titre.md` porte l'id `EDR-EVO-021` : indexer aussi le préfixe du nom de fichier.
            ids.add(f.split("_")[0])
    return ids


def scan():
    """Renvoie {clef: description} pour chaque péremption MÉCANIQUE trouvée."""
    txt = _lire_backlog()
    trouve = {}

    connus = _known_ids()
    for cible in sorted(set(_WIKILINK.findall(txt))):
        # ⚠️ Deux espaces de noms cohabitent dans ces `[[...]]` : les RECORDS (`EDR-`, `REF-`, `SDR-`,
        # `ADR-`, majuscules) et les slugs de MÉMOIRE de session (kebab minuscule), qui vivent hors du
        # dépôt. Ne juger que les premiers : signaler les seconds serait exiger qu'un fichier existe
        # là où la convention dit qu'il n'existe pas.
        if not re.match(r"^(EDR|REF|SDR|ADR)-", cible):
            continue
        court = cible[4:] if cible.startswith("EDR-") else cible
        if cible in connus or court in connus:
            continue
        trouve[f"lien-mort:{cible}"] = (
            f"le backlog cite [[{cible}]] mais aucun record ne porte cet identifiant")

    # Une tete composite vote pour CHACUN de ses numeros ; `P1.x` est un substitut, pas un numero :
    # deux entrees « a numeroter » ne sont pas deux versions d'une meme tache, ne pas le fabriquer.
    compte = collections.Counter(
        num for tete in _TASKNUM.findall(txt) for num in re.findall(_NUM, tete) if ".x" not in num)
    for num, n in sorted(compte.items()):
        if n > 1:
            trouve[f"numero-double:{num}"] = (
                f"{num} apparaît {n} fois en tête d'entrée : l'une des versions est périmée et rien "
                f"ne dit laquelle")

    # ⚠️ UN CHEMIN PROPOSE N'EST PAS UN CHEMIN MORT (2026-09-01). Un backlog PROPOSE legitimement des
    # fichiers qui n'existent pas encore -- c'est meme sa fonction. Le detecteur confondait « reference
    # perimee » et « travail a faire » : il a signale `tools/check_staged_authorship.py`, introduit par
    # « *Correctif candidat, plus fort* : un script ... A evaluer ». Geler ce cas dans la baseline
    # aurait masque une classe de faux positifs qui se reproduira a chaque proposition.
    suivis = _chemins_suivis()
    _PROPOSE = ("candidat", "propos", "à écrire", "a ecrire", "à évaluer", "a evaluer",
                "TODO", "futur", "il faudra", "piste")
    lignes_proposition = {l for l in txt.splitlines()
                          if any(marq.lower() in l.lower() for marq in _PROPOSE)}
    for chemin in sorted(set(_BACKTICK_PATH.findall(txt))):
        if "/" not in chemin:
            continue                      # nom nu : trop ambigu pour conclure
        if any(chemin in l for l in lignes_proposition):
            continue                      # cite comme A FAIRE, pas comme existant
        if not _existe(chemin):
            trouve[f"chemin-mort:{chemin}"] = (
                f"le backlog cite `{chemin}`, qui n'existe plus")
        elif chemin not in suivis:
            # 2026-09-22 : EXISTE ICI, INCONNU DE GIT -> vert chez l'auteur, ROUGE sur tout clone (là-bas
            # le chemin « n'existe plus », juste au-dessus). La porte connaissait pourtant la leçon : son
            # message pour les clauses `closes_when` cite la CI rouge du 2026-09-07 (`5b0025e`) — elle ne
            # l'appliquait qu'aux CLAUSES, pas à la PROSE. Mesuré sur le commit 72ce45a, qui a introduit
            # trois citations de ce genre sans que rien ne crie chez son auteur.
            trouve[f"chemin-non-suivi:{chemin}"] = (
                f"le backlog cite `{chemin}`, qui existe ICI mais n'est PAS SUIVI par git : sur un clone "
                "il est ABSENT et la citation devient un renvoi vers le vide. Committer le fichier (un "
                "fichier STAGÉ compte déjà), ou ne pas le citer.")

    viol, sans = scan_clauses(txt)
    trouve.update(viol)
    scan.entrees_sans_clause = sans
    return trouve


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("legataires", {})


def _charger_plancher():
    """Plancher d'entrees, lu sur le JSON COMPLET.

    ⚠️ La premiere version de la garde lisait `_load_baseline().get("plancher_entrees", 0)` -- or
    `_load_baseline()` rend le SOUS-DICTIONNAIRE `legataires`, donc le plancher valait TOUJOURS 0 et
    la garde etait INERTE. Elle a passe son propre contre-exemple : backlog vide, exit 0. C'est la
    classe E1 (un controle qui ne peut pas echouer), commise en armant une garde contre exactement
    ca. Seul le contre-exemple gele l'a dit ; la relecture ne l'avait pas vu."""
    if not os.path.exists(_BASELINE):
        return 0
    with open(_BASELINE, encoding="utf-8") as f:
        return int(json.load(f).get("plancher_entrees", 0))


def compter_entrees(txt=None):
    """Nombre d'ENTREES de backlog (lignes commencant par `**Pn.m`). Garde d'AMPUTATION.

    ⚠️ ARMEE SUR UN INCIDENT REEL du 2026-09-09. Une reecriture programmatique a VIDE
    `PRIORITES_ET_DETTES.md` -- 2352 lignes -> 0 -- sans lever :
    `io.open(p, "w").write(io.open(p).read().replace(...))` evalue ses arguments de GAUCHE A DROITE,
    donc le mode "w" TRONQUE le fichier AVANT que le `read()` interne ne le lise ; le read rend "",
    le replace rend "", et le fichier est ecrase par du vide.

    Ce cliquet a alors rendu **exit 0 et « OK »** sur un backlog VIDE -- et pire, il a INVITE a
    resserrer sa baseline (« 2 resorbee(s) -> --update-baseline »), ce qui aurait fige l'amputation.
    C'est le biais que ce depot traque chez ses sondes, commis par une GARDE : entree vide ->
    succes. Meme famille qu'E22 (une suppression rend le signal plus vert), avec un mecanisme neuf :
    l'ORDRE D'EVALUATION DES ARGUMENTS.

    Le plancher est un CLIQUET : il ne peut que MONTER. Une baisse est une amputation, et une
    amputation ne se declare pas -- elle se refuse."""
    if txt is None:
        with open(os.path.join(_ROOT, "docs", "roadmap", "PRIORITES_ET_DETTES.md"),
                  encoding="utf-8") as f:
            txt = f.read()
    # Meme TETE que `_ENTREE` : une entree invisible au compte serait effacable sans que le plancher bouge.
    return sum(1 for ln in txt.splitlines() if re.match(_TETE, ln.strip()))


def main():
    ap = argparse.ArgumentParser(description="Cliquet de fraicheur du backlog.")
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    args = ap.parse_args()

    # GARDE D'AMPUTATION, EN TETE et AVANT `--update-baseline` : geler une baseline contre un
    # backlog ampute FIGERAIT l'amputation. Le plancher vit dans la baseline et ne peut que monter.
    n_entrees = compter_entrees()
    plancher = _charger_plancher()
    if n_entrees < plancher:
        print(f"ECHEC : le backlog est passe de {plancher} a {n_entrees} entrees.\n")
        print("  Une entree de backlog ne DISPARAIT pas : on la marque CLOSE, on ne l'efface pas.")
        print("  Cause la plus probable : une reecriture programmatique a tronque le fichier sans")
        print("  lever. Le 2026-09-09, la forme open(p,'w').write(open(p).read()...) l'a vide de")
        print("  2352 lignes a 0, et ce cliquet a rendu OK. Restaurer depuis git AVANT tout le reste.")
        return 1

    trouve = scan()

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({
                "_comment": ("Peremptions MECANIQUES legataires du backlog, gelees. Le cliquet refuse "
                             "toute NOUVELLE entree. Retirer une ligne quand elle est corrigee -- "
                             "jamais en ajouter pour faire passer le hook."),
                "legataires": trouve,
                # Plancher d'entrees : ne peut que MONTER (max avec l'ancien). Geler un plancher plus
                # BAS reviendrait a enteriner une amputation, ce que la garde existe pour empecher.
                "plancher_entrees": max(n_entrees, plancher),
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline gelé : {len(trouve)} péremption(s) mécanique(s) légataire(s)")
        return 0

    base = _load_baseline()
    nouvelles = {k: v for k, v in trouve.items() if k not in base}
    resorbees = [k for k in base if k not in trouve]

    if args.report:
        print(f"péremptions mécaniques : {len(trouve)} "
              f"(dont {len(base)} légataires, {len(nouvelles)} NOUVELLES)")
        for k, v in sorted(trouve.items()):
            print(f"  [{'LÉGATAIRE' if k in base else 'NOUVELLE '}] {v}")
        if resorbees:
            print(f"\n  résorbées : {len(resorbees)} -> `--update-baseline` pour resserrer")
        return 0

    if nouvelles:
        print("ÉCHEC : le backlog a de NOUVELLES péremptions mécaniques.\n")
        for k, v in sorted(nouvelles.items()):
            print(f"  {v}")
        print("\nUn backlog qui ment sur son état fait relancer ce qui est déjà tranché.")
        return 1

    print(f"OK : {len(trouve)} péremption(s) mécanique(s), toutes légataires (baseline). Aucune nouvelle.")
    sans = getattr(scan, "entrees_sans_clause", None)
    if sans:
        print(f"  ({sans} entrée(s) SANS clause `closes_when:` — hors périmètre sémantique, "
              "RAPPORTÉ et non compté comme succès)")
    if resorbees:
        print(f"  ({len(resorbees)} résorbée(s) — `--update-baseline` pour resserrer le cliquet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
