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
        if _IDENT.match(tok) or _PATH.match(tok):
            found.append(tok)
    return sorted(set(found))


def _is_test_artifact(name):
    return name.startswith("test_") or (bool(_PATH.match(name)) and "test" in os.path.basename(name))


def _walk(dirs, suffix=".py"):
    for d in dirs:
        for root, _, files in os.walk(d):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(suffix):
                    yield os.path.join(root, f)


def _exists(name):
    """Fichier présent, ou fonction définie dans tools/, src/ ou tests/.

    `tests/` est inclus : une garde peut légitimement ÊTRE un test (contre-exemple gelé)."""
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
        # ⚠️ Exiger que TOUS les termes backtickés existent produisait des faux positifs en masse :
        # la colonne cite aussi de la PROSE technique (`argmax`, `throw`, `lr`, `pass`) qui n'est pas
        # un artefact. Le critère est donc « au moins un artefact réel », pas « aucun terme inconnu ».
        existants = [a for a in arts if _exists(a)]
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
