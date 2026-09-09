# -*- coding: utf-8 -*-
"""Cliquet des CHEMINS DE DONNÉES — aucun NOUVEAU chemin écrit en dur.

Problème visé, mesuré le 2026-09-09 : **57 chemins de données en dur dans 26 fichiers**, 16
constantes de module, et une seule variable d'environnement liée aux données. Héberger les données
ailleurs — un NAS, un autre disque, une autre machine — demandait donc d'éditer 26 fichiers. Le
stockage était une propriété du CODE alors que c'est une propriété du DÉPLOIEMENT.

`src/paths.py` fournit le point d'indirection ; ce cliquet empêche la dette de se reformer. C'est le
critère explicite du dépôt : une règle qui peut se re-violer SILENCIEUSEMENT exige un cliquet, pas
une note — sans quoi c'est la classe E10, la plus récidivante du registre.

CE QU'IL VÉRIFIE, et rien de plus — une propriété DÉCIDABLE :

    aucune chaîne littérale commençant par une racine de données (`data/`, `results/`, `/app/data/`)
    n'apparaît dans le code, hors de celles GELÉES dans la baseline.

CE QU'IL NE VÉRIFIE PAS. Il ne dit pas si un site GELÉ devrait être migré — c'est un jugement, pas
une propriété. Il ne suit pas non plus les chemins construits dynamiquement (`os.path.join(racine,
nom)` où `racine` est une variable) : ceux-là sont DÉJÀ indirects, donc hors sujet. Et il ne juge pas
`src/paths.py`, qui doit contenir les défauts — c'est sa raison d'être.

Dette LÉGATAIRE gelée dans `tools/data_paths_baseline.json` ; aucun NOUVEAU littéral.
⚠️ La baseline elle-même doit déclencher le hook (classe E4 occ. 5), sinon l'élargir et la committer
seule ne vérifierait rien.

Usage :
  python tools/check_data_paths.py                    # cliquet : exit 1 sur tout NOUVEAU littéral
  python tools/check_data_paths.py --report           # état complet, exit 0
  python tools/check_data_paths.py --only a.py b.py   # blocage restreint (arbre PARTAGÉ)
  python tools/check_data_paths.py --update-baseline  # gèle l'état courant
"""
import argparse
import ast
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCAN_DIRS = ("tools", "src", "backend", "scripts")
_SKIP_DIRS = ("__pycache__", ".worktrees", ".claude", "node_modules", ".venv")
_BASELINE = os.path.join(_ROOT, "tools", "data_paths_baseline.json")

# Le module d'indirection DOIT porter les défauts : le juger serait s'interdire d'en avoir un.
_HORS_PERIMETRE = frozenset({"src/paths.py"})

# Une racine de données, et rien d'autre : ni regex, ni chemin de documentation, ni URL.
_EST_DONNEE = re.compile(r"^(?:\./)?(?:data|results)/|^/app/data/", re.I)


def _sources():
    for rel in _SCAN_DIRS:
        d = os.path.join(_ROOT, rel)
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = sorted(x for x in dirnames if x not in _SKIP_DIRS)
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                rel_p = os.path.relpath(p, _ROOT).replace("\\", "/")
                if rel_p in _HORS_PERIMETRE:
                    continue
                try:
                    yield rel_p, open(p, encoding="utf-8").read()
                except (OSError, UnicodeDecodeError):
                    continue


def scan_literals(sources=None):
    """{chemin: [littéraux DISTINCTS triés]}. Analyse AST, pas textuelle : un chemin cité dans un
    commentaire ou une docstring n'est pas un chemin utilisé, et le compter ferait crier le cliquet
    sur de la prose — c'est ainsi qu'une garde devient du bruit, puis se fait désarmer."""
    out = {}
    for path, src in (sources if sources is not None else _sources()):
        try:
            arbre = ast.parse(src)
        except SyntaxError:
            continue
        vus = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and _EST_DONNEE.match(n.value):
                vus.add(n.value)
        if vus:
            out[path] = sorted(vus)
    return out


def nouveaux(baseline, courant):
    """VERDICT : la liste des (fichier, littéral) qui n'étaient PAS gelés. Jamais un booléen.

    Un littéral qui DISPARAÎT ne produit rien : migrer un site vers `src/paths.py` est précisément
    ce qu'on encourage, et un cliquet qui s'en plaindrait travaillerait contre son propre but."""
    out = []
    for path, lits in sorted(courant.items()):
        gelés = set(baseline.get(path, []))
        for lit in lits:
            if lit not in gelés:
                out.append({"chemin": path, "litteral": lit})
    return out


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("fichiers", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None, help="ne BLOQUE que sur ces fichiers")
    args = ap.parse_args(argv)

    courant = scan_literals()
    n_sites = sum(len(v) for v in courant.values())

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({"_comment": "Chemins de donnees ECRITS EN DUR, geles comme dette legataire. "
                                   "Aucun NOUVEAU (tools/check_data_paths.py). Migrer un site vers "
                                   "src/paths.py ne declenche RIEN : c'est le but.",
                       "fichiers": courant}, f, indent=1, sort_keys=True, ensure_ascii=False)
        print(f"baseline gelée : {n_sites} littéraux dans {len(courant)} fichiers")
        return 0

    baseline = _load_baseline()
    n_gel = sum(len(v) for v in baseline.values())
    neufs = nouveaux(baseline, courant)
    migres = n_gel - (n_sites - len(neufs))
    print(f"chemins de données en dur : {n_sites} dans {len(courant)} fichiers "
          f"| gelés : {n_gel} | NOUVEAUX : {len(neufs)}"
          + (f" | MIGRÉS depuis le gel : {migres}" if migres > 0 else ""))

    if args.report:
        for x in neufs:
            print(f"  NOUVEAU  {x['chemin']} : {x['litteral']}")
        return 0

    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
        neufs = [x for x in neufs if x["chemin"] in vises]

    if neufs:
        print("")
        for x in neufs:
            print(f"❌ chemin de données ÉCRIT EN DUR : {x['chemin']} -> {x['litteral']!r}")
        print("\n-> Passer par `src/paths.py` : hall_of_fame(), agent_states(), results_file(),")
        print("   kuzu_graph(), data_file(...). Le stockage est une propriété du DÉPLOIEMENT, pas du")
        print("   code — 57 littéraux dans 26 fichiers rendaient un NAS impossible sans tout éditer.")
        print("   Si le littéral est légitime (script jetable, chemin de test), geler la dette :")
        print("   python tools/check_data_paths.py --update-baseline")
        return 1
    print("OK : aucun nouveau chemin de données écrit en dur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
