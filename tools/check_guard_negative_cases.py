"""Garde-fou des GARDES — une garde `exécutable` doit NOMMER le test qui prouve qu'elle sait dire NON.

Problème visé. `docs/REF/REGISTRE_ERREURS.md` attribue à chaque classe d'erreur un statut : `exécutable`,
`documenté` ou `non automatisable`. Le statut `exécutable` est une PROMESSE — et rien ne la vérifiait.
C'est la classe **E1** (« contrôle qui ne peut pas échouer ») appliquée au méta-niveau : une garde sans
contre-exemple passe au vert quel que soit le code, et le registre affiche une couverture qu'il n'a pas.

CE QUE CE CLIQUET VÉRIFIE (et rien de plus) — trois propriétés DÉCIDABLES :

1. **Artefact nommé** — la colonne « Garde » nomme au moins un identifiant ou fichier.
2. **Artefact existant** — il se trouve réellement dans `tools/`, `src/` ou `tests/`.
3. **Contre-exemple nommé** — elle nomme aussi un TEST (`test_*` ou `tests/**.py`) qui existe.

CE QU'IL NE VÉRIFIE PAS, et pourquoi. Il ne juge pas si le test DISCRIMINE vraiment. Une première
version tentait de le deviner lexicalement (chercher `pytest.raises` près du nom de la garde) : elle a
produit CINQ gardes creuses, puis deux après correction, **toutes fausses**. Les raisons sont
instructives et valent d'être gardées :

* le test importe le module et n'emploie plus que le symbole importé (`classify_record`) ;
* la garde est ASSERTIONNELLE, pas exceptionnelle — elle discrimine sans jamais lever ;
* le test passe par un helper local (`_score`), donc plus aucune mention de l'artefact.

« Ce test discrimine-t-il ? » n'est pas une propriété lexicale ; la mesurer demanderait du test de
mutation (casser la garde, vérifier qu'un test rougit). Plutôt que de proxifier une grandeur qu'on ne
sait pas mesurer — l'erreur que ce dépôt paie le plus cher — le cliquet exige que l'AUTEUR pointe son
contre-exemple. C'est la convention qu'**E6** applique déjà exemplairement.

Effet de bord voulu : le registre devient navigable. Un lecteur va de la classe d'erreur à la preuve
qu'elle est gardée, sans chercher.

RÈGLE À CLIQUET, identique à `check_record_links.py` et `check_instrument_calibration.py` : la dette
LÉGATAIRE est gelée dans un baseline, aucune NOUVELLE garde sans contre-exemple nommé.

Usage :
  python tools/check_guard_negative_cases.py                    # cliquet : exit 1 sur toute NOUVELLE garde creuse
  python tools/check_guard_negative_cases.py --report           # état complet, exit 0
  python tools/check_guard_negative_cases.py --update-baseline  # gèle l'état courant comme dette légataire
"""
import argparse
import ast
import functools
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRE = os.path.join(_ROOT, "docs", "REF", "REGISTRE_ERREURS.md")
_BASELINE = os.path.join(_ROOT, "tools", "guard_negative_cases_baseline.json")
_TESTS_DIR = os.path.join(_ROOT, "tests")
_CODE_DIRS = (os.path.join(_ROOT, "tools"), os.path.join(_ROOT, "src"))

# Une ligne du registre : | **E1** | classe | occurrences | statut | garde |
_ROW = re.compile(r"^\|\s*\*\*(E\d+)\*\*\s*\|(.*)$", re.M)

# ⚠️ Majuscules ADMISES : les tests de ce dépôt mettent l emphase en capitales
# (test_optimizer_sweep_REFUSES_..., test_..._is_REFUSED). Un motif minuscule-seul
# rendait invisible le contre-exemple le mieux nommé du registre.
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PATH = re.compile(r"^[\w/]+\.py$")


def _cells(row_text):
    return [c.strip() for c in row_text.strip().strip("|").split(" | ")]


def _rows():
    """Renvoie [(classe, statut, cellule_garde)] pour toutes les lignes du registre."""
    txt = open(_REGISTRE, encoding="utf-8").read()
    out = []
    for m in _ROW.finditer(txt):
        cells = _cells(m.group(0))
        if len(cells) < 5:
            continue
        out.append((cells[0].strip("* "), cells[3], cells[4]))
    return out


def _named_artifacts(cell):
    """Artefacts nommés dans la colonne « Garde » : identifiants et chemins, entre backticks."""
    found = []
    for span in re.findall(r"`([^`]+)`", cell):
        tok = span.split("(")[0].strip()
        # Le registre cite volontiers `fichier.py:163` — forme légitime que le motif brut rejetait.
        tok = re.sub(r":\d+$", "", tok)
        # ⚠️ ET LA FORME QUALIFIÉE `fichier.py::fonction` (2026-09-24, P2.108). C'est la convention
        # du dépôt pour lever une collision de noms (elle est OBLIGATOIRE dans `CALIBRATED`), et
        # c'est la façon naturelle de désigner UN cas gelé parmi les seize d'un fichier. Ce cliquet
        # ne la lisait pas : le token entier ne passait ni `_IDENT` ni `_PATH`, la colonne Garde
        # paraissait ne nommer AUCUN artefact, et deux classes inscrites avec leur contre-exemple
        # étaient refusées comme « déclaratives ». Un cliquet qui refuse la notation que le dépôt
        # recommande crie au loup, et une garde qui crie toujours est une garde qu'on désarme.
        # Les deux moitiés sont retenues : le fichier DOIT exister, la fonction est vérifiée comme
        # n'importe quel identifiant.
        for moitie in (tok.split("::") if "::" in tok else [tok]):
            moitie = moitie.strip()
            if _IDENT.match(moitie) or _PATH.match(moitie):
                found.append(moitie)
    return sorted(set(found))


def _is_test_artifact(name):
    return name.startswith("test_") or (bool(_PATH.match(name)) and "test" in os.path.basename(name))


_CACHE_WALK = {}


def _walk(dirs, suffix=".py"):
    """⚠️ MÉMOÏSÉ, et ce n'est pas du confort (mesuré le 2026-09-24). `_exists` appelle ce parcours
    puis RELIT chaque fichier du dépôt pour y chercher un `def <nom>` ; à une vingtaine d'appels par
    passe, c'est autant de balayages complets de `tools/`, `src/` et `tests/`. En ajoutant la
    vérification de la forme qualifiée, la suite de ce cliquet est passée de 104 s à un dépassement
    de 900 s — un durcissement correct rendu inutilisable par son coût, donc désarmé en pratique.
    La liste des fichiers est figée pour la durée du processus : ces cliquets sont des passes
    courtes, jamais des démons."""
    cle = (tuple(dirs), suffix)
    if cle not in _CACHE_WALK:
        trouves = []
        for d in dirs:
            for root, _, files in os.walk(d):
                if "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith(suffix):
                        trouves.append(os.path.join(root, f))
        _CACHE_WALK[cle] = trouves
    return list(_CACHE_WALK[cle])


def _collectibles():
    """Noms de tests que pytest COLLECTERAIT vraiment : `def test*` au niveau MODULE (ou methode d'une
    classe `Test*`), dans un fichier `tests/**/test_*.py` ou `*_test.py`.

    ⚠️ Pourquoi ce n'est pas la meme chose que « le nom existe » (2026-09-08). `_exists` cherche
    `^ *def <nom>(` n'importe ou sous tools/, src/ ou tests/ : un test DEFINI DANS UNE AUTRE FONCTION,
    ou pose dans un fichier que pytest ne collecte pas (`helpers.py`, `conftest_old.py`), y passe pour
    present alors qu'il ne s'executera JAMAIS. Une classe `executable` nommerait alors un contre-exemple
    FANTOME -- indiscernable d'une garde absente, ce qui est exactement le defaut que ce cliquet ferme
    (E1 au meta-niveau).

    ⚠️ Le trou est PROSPECTIF : mesure le 2026-09-08, ZERO classe du registre est concernee. C'est
    precisement le moment de le fermer -- meme situation que le trou des collisions de noms, ferme le
    2026-09-01 alors qu'aucun faux vert n'existait encore."""
    out = {}
    for root, _dirs, files in os.walk(_TESTS_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            if not (f.endswith(".py") and (f.startswith("test_") or f.endswith("_test.py"))):
                continue
            chemin = os.path.join(root, f)
            try:
                tree = ast.parse(open(chemin, encoding="utf-8").read())
            except (SyntaxError, OSError):
                continue
            for n in tree.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                    out.setdefault(n.name, []).append(chemin)
                elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
                    for meth in n.body:
                        if isinstance(meth, (ast.FunctionDef, ast.AsyncFunctionDef))                                 and meth.name.startswith("test"):
                            out.setdefault(meth.name, []).append(chemin)
    return out


@functools.lru_cache(maxsize=None)
def _exists(name):
    """Fichier présent, ou fonction définie dans tools/, src/ ou tests/.

    `tests/` est inclus : une garde peut légitimement ÊTRE un test (contre-exemple gelé).
    ⚠️ MÉMOÏSÉ pour la même raison que `_walk` : le registre cite le même artefact dans plusieurs
    classes, et chaque appel non mis en cache relit le dépôt entier."""
    if _PATH.match(name):
        if os.path.exists(os.path.join(_ROOT, name)):
            return True
        # Le registre cite souvent un fichier par son nom NU (`check_record_links.py`) sans son
        # dossier : le chercher partout plutôt que de le déclarer disparu.
        base = os.path.basename(name)
        return any(os.path.basename(p) == base for p in _walk(_CODE_DIRS + (_TESTS_DIR,)))
    pat = re.compile(r"^\s*def\s+" + re.escape(name) + r"\s*\(", re.M)
    for p in _walk(_CODE_DIRS + (_TESTS_DIR,)):
        try:
            if pat.search(open(p, encoding="utf-8", errors="ignore").read()):
                return True
        except OSError:
            continue
    return False


def scan():
    """Renvoie {classe: raison} pour toute garde `exécutable` qui ne prouve pas qu'elle peut échouer."""
    creuses = {}
    for classe, statut, cell in _rows():
        if "exécutable" not in statut:
            continue
        arts = _named_artifacts(cell)
        if not arts:
            creuses[classe] = ("NON NOMMEE : statut `executable` mais la colonne Garde ne nomme aucun "
                               "artefact -- il n'y a rien a executer, le statut est declaratif")
            continue
        # ⚠️ LA FORME QUALIFIEE EST UNE PROMESSE PRECISE, DONC VERIFIEE PRECISEMENT (2026-09-24).
        # La tolerance ci-dessous (« au moins un artefact reel ») est justifiee pour de la prose
        # technique en backticks ; elle ne l'est PAS pour `fichier.py::fonction`, qui ne peut pas
        # etre de la prose. Mesure du controle positif ecrit dans la meme passe : avec la seule
        # tolerance, un fichier REEL suivi d'une fonction INVENTEE passait -- la moitie droite
        # n'etait jamais lue, et le lecteur croyait pourtant qu'on lui nommait UN cas precis.
        for tok in re.findall(r"`([^`]+)`", cell):
            tok = tok.split("(")[0].strip()
            if "::" not in tok:
                continue
            fichier, _, fonction = tok.partition("::")
            fichier, fonction = fichier.strip(), fonction.strip()
            # ⚠️ ET SEULEMENT SUR LA FORME REELLE `*.py::identifiant`. Premier tir de cette
            # stricture : UN faux positif immediat, sur E1, dont la colonne cite une clause de
            # peremption de backlog (`grep_present=docs/EDR/….md::verdict: TD0_INERTE`) — deux
            # points doubles qui ne sont pas une qualification python. Un cliquet qui durcit doit
            # etre confronte au registre REEL avant d'etre cru : celui-ci l'a ete, et il avait tort.
            if not (_PATH.match(fichier) and _IDENT.match(fonction)):
                continue
            manquants = [m for m in (fichier, fonction) if m and not _exists(m)]
            if manquants:
                creuses[classe] = (f"CITATION QUALIFIEE FAUSSE : `{tok}` nomme {manquants}, qui "
                                   f"n'existe(nt) pas. La forme fichier.py::fonction annonce UN cas "
                                   f"precis : ses deux moities doivent exister, sinon elle est plus "
                                   f"trompeuse qu'une absence de citation")
                break
        if classe in creuses:
            continue
        # ⚠️ Exiger que TOUS les termes backtickés existent produisait des faux positifs en masse :
        # la colonne cite aussi de la PROSE technique (`argmax`, `throw`, `lr`, `pass`) qui n'est pas
        # un artefact. Le critère est donc « au moins un artefact réel », pas « aucun terme inconnu ».
        # Un artefact de TEST doit etre COLLECTIBLE par pytest, pas seulement present quelque part.
        coll = _collectibles()

        def _ok(a):
            if _is_test_artifact(a) and not _PATH.match(a):
                return a in coll
            return _exists(a)

        existants = [a for a in arts if _ok(a)]
        if not existants:
            creuses[classe] = (f"INTROUVABLE : aucun des termes nommes {arts} n'existe dans tools/, "
                               f"src/ ou tests/ -- la garde a ete renommee, supprimee, ou n'est que "
                               f"de la prose")
            continue
        tests = [a for a in existants if _is_test_artifact(a)]
        if not tests:
            creuses[classe] = (f"CONTRE-EXEMPLE NON NOMME : {existants} existe(nt), mais la colonne Garde ne "
                               f"pointe aucun test. Rien ne dit OU est la preuve que cette garde sait "
                               f"refuser une entree fautive -- nommer le test discriminant (cf. E6)")
    return creuses


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("legataires", {})


def main():
    ap = argparse.ArgumentParser(description="Cliquet : toute garde `executable` nomme son contre-exemple.")
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    args = ap.parse_args()

    creuses = scan()
    total = sum(1 for _, s, _ in _rows() if "exécutable" in s)

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({
                "_comment": ("Dette LEGATAIRE : gardes `executable` qui ne nomment pas leur "
                             "contre-exemple. Gelee. Le cliquet refuse toute NOUVELLE entree. Retirer "
                             "une ligne d'ici quand la ligne du registre pointe son test -- jamais en "
                             "ajouter pour faire passer le hook."),
                "legataires": creuses,
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline gelé : {len(creuses)} garde(s) sans contre-exemple nommé sur {total} `exécutable`")
        return 0

    base = _load_baseline()
    nouvelles = {k: v for k, v in creuses.items() if k not in base}
    resorbees = [k for k in base if k not in creuses]

    if args.report:
        print(f"classes `exécutable` : {total} | sans contre-exemple nommé : {len(creuses)} "
              f"(dont {len(base)} légataires, {len(nouvelles)} NOUVELLES)")
        for k, v in sorted(creuses.items()):
            marque = "LÉGATAIRE" if k in base else "NOUVELLE "
            print(f"  [{marque}] {k} : {v}")
        if resorbees:
            print(f"\n  résorbées depuis le baseline : {', '.join(sorted(resorbees))} "
                  f"-> les retirer avec --update-baseline")
        return 0

    if nouvelles:
        print("ÉCHEC : garde(s) déclarée(s) `exécutable` sans contre-exemple nommé.\n")
        for k, v in sorted(nouvelles.items()):
            print(f"  {k} : {v}")
        print("\nUne garde dont personne ne sait montrer le test discriminant est indiscernable")
        print("d'une garde absente. Nommer le test dans la colonne « Garde », puis relancer.")
        return 1

    print(f"OK : {total} classes `exécutable`, {len(creuses)} sans contre-exemple nommé, toutes "
          f"légataires (baseline). Aucune nouvelle.")
    if resorbees:
        print(f"  ({len(resorbees)} résorbée(s) : {', '.join(sorted(resorbees))} — "
              f"`--update-baseline` pour resserrer le cliquet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
