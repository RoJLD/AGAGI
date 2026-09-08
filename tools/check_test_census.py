# -*- coding: utf-8 -*-
"""Cliquet du RECENSEMENT DES TESTS — un test qui disparaît doit le dire.

Problème visé, mesuré le 2026-09-07 sur moi-même. Une réécriture programmatique par expression
régulière (retirer un décorateur `@pytest.mark.xfail` devant quatre fonctions nommées) était ancrée
sur `@pytest.mark.xfail` SANS ancrage de début : `re.search` a donc démarré au PREMIER décorateur du
fichier et effacé tout ce qui séparait celui-ci de la fonction visée — **quatre tests supprimés, aucune
exception levée**. La suite est alors passée de « 28 passés, 15 xfail » à « 32 passés, 7 xfail » : plus
verte qu'avant. Seul un RECOMPTE l'a révélé.

C'est le pire cas de figure du dépôt appliqué à la suite elle-même : une vérification qui s'évapore
rend le vert MEILLEUR, donc rien dans le signal habituel ne peut alerter. Un test supprimé, c'est une
garde désarmée en silence — exactement ce que les cliquets existent pour empêcher, pour les records,
les instruments et les gardes. Il manquait celui qui protège les tests eux-mêmes.

CE QUE CE CLIQUET VÉRIFIE, et rien de plus — deux propriétés DÉCIDABLES :

1. **Aucun fichier de test recensé n'a DISPARU.**
2. **Aucun fichier de test recensé n'a MOINS de fonctions `test_` qu'au gel de la baseline.**

Une AUGMENTATION passe (la suite croît de façon monotone, c'est la règle du dépôt). Un fichier NOUVEAU
passe — il entre dans la baseline au prochain `--update-baseline`.

CE QU'IL NE VÉRIFIE PAS, et pourquoi. Il compte des DÉCLARATIONS `def test_`, pas des assertions : un
test vidé de son corps mais gardé le passerait. Mesurer « ce test discrimine-t-il ? » demanderait du
test de mutation ; plutôt que de proxifier une grandeur qu'on ne sait pas mesurer — l'erreur que ce
dépôt paie le plus cher —, le cliquet se borne à la propriété qu'il sait décider, et le dit. Une
SUPPRESSION légitime (test fusionné, renommé en masse, module découpé) se déclare en re-gelant la
baseline, c.-à-d. par un acte explicite et lisible en revue, jamais par un silence.

Une baisse peut aussi être LÉGITIME et vouloir être gelée : c'est le sens de `--update-baseline`.
⚠️ Comme pour les cliquets frères, la baseline elle-même DOIT déclencher le hook, sinon l'élargir et
la committer seule ne vérifie rien (classe E4 occ. 5, faux vert mesuré le 2026-09-01).

Usage :
  python tools/check_test_census.py                     # cliquet : exit 1 si un test a disparu
  python tools/check_test_census.py --report            # état complet, exit 0
  python tools/check_test_census.py --only a.py b.py    # blocage restreint aux fichiers indiqués
  python tools/check_test_census.py --update-baseline   # gèle l'état courant
"""
import argparse
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS_DIR = os.path.join(_ROOT, "tests")
_BASELINE = os.path.join(_ROOT, "tools", "test_census_baseline.json")

# `def test_` en tête de ligne ou indenté (méthodes de classes de test), async compris.
_DEF_TEST = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(test_\w*)[ \t]*\(", re.M)

# Répertoires ignorés : arbres de travail d'AUTRES sessions et caches. Les compter ferait échouer le
# cliquet sur du travail qui n'est pas le nôtre (arbre PARTAGÉ, cf. CLAUDE.md).
_IGNORES = (".git", "__pycache__", ".pytest_cache", ".worktrees", ".claude", "node_modules", ".venv")


def count_tests(src):
    """Nombre de fonctions de test DÉCLARÉES dans un source. Compte les noms DISTINCTS : deux `def`
    homonymes dans un même fichier ne font qu'un test exécuté (le second écrase le premier), et les
    compter deux fois laisserait passer une suppression compensée par un doublon."""
    return len(set(_DEF_TEST.findall(src)))


def census(root=_TESTS_DIR):
    """{chemin relatif POSIX -> nombre de tests} sur l'arbre de tests."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORES]
        for fn in filenames:
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    src = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            out[os.path.relpath(p, _ROOT).replace("\\", "/")] = count_tests(src)
    return out


def regressions(baseline, current):
    """VERDICT du cliquet : la liste des pertes, jamais un booléen.

    Rend une liste de dicts {chemin, avant, apres, genre} où `genre` vaut :
      * `fichier_disparu`  — le fichier recensé n'existe plus (apres = None) ;
      * `tests_supprimes`  — il existe mais déclare MOINS de tests qu'au gel.
    Une augmentation ou un fichier nouveau ne produisent RIEN : le cliquet ne bloque que la perte."""
    perdus = []
    for chemin, avant in sorted(baseline.items()):
        if chemin not in current:
            perdus.append({"chemin": chemin, "avant": avant, "apres": None, "genre": "fichier_disparu"})
        elif current[chemin] < avant:
            perdus.append({"chemin": chemin, "avant": avant, "apres": current[chemin],
                           "genre": "tests_supprimes"})
    return perdus


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("fichiers", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None,
                    help="ne BLOQUE que sur ces fichiers (l'état complet reste imprimé)")
    args = ap.parse_args(argv)

    current = census()
    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({"_comment": "Recensement gele des tests. Une BAISSE bloque le commit "
                                   "(tools/check_test_census.py). Re-geler = acte explicite.",
                       "fichiers": current}, f, indent=1, sort_keys=True)
        print(f"baseline gelée : {len(current)} fichiers, {sum(current.values())} tests")
        return 0

    baseline = _load_baseline()
    perdus = regressions(baseline, current)
    print(f"fichiers de test : {len(current)} | tests déclarés : {sum(current.values())} "
          f"| recensés au gel : {len(baseline)} / {sum(baseline.values())}")
    if args.report:
        for p in perdus:
            print(f"  PERTE {p['genre']:16s} {p['chemin']} : {p['avant']} -> {p['apres']}")
        return 0

    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
        perdus = [p for p in perdus if p["chemin"] in vises]

    if perdus:
        print("")
        for p in perdus:
            print(f"❌ {p['genre']} : {p['chemin']} — {p['avant']} test(s) au gel, "
                  f"{'fichier absent' if p['apres'] is None else str(p['apres']) + ' aujourd’hui'}")
        print("\n-> Un test disparu est une garde DÉSARMÉE, et la suite en devient plus verte.")
        print("   Si la suppression est voulue (fusion, renommage, découpe), gèle-la explicitement :")
        print("   python tools/check_test_census.py --update-baseline")
        return 1
    print("OK : aucun test disparu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
