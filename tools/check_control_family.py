# -*- coding: utf-8 -*-
"""Cliquet E23 — un runner qui exécute une règle SCELLÉE doit DÉCLARER son design.

Pourquoi ce cliquet existe. La garde E23 vit dans `declare_design` : dès qu'un run a plus d'un
réplicat, elle refuse tant que l'auteur n'a pas écrit combien de cellules forment sa famille de
contrôles. Mais une garde d'appel ne protège que ceux qui l'appellent — et la mesure du 2026-09-07
dit que **9 runners scellés sur 12 ne déclarent aucun design**, donc échappent entièrement à la
question. Parmi eux `tools/lang_memory_edge_run.py`, qui a produit la 3ᵉ arête établie du graphe.

C'est la classe **E10** (règle documentée sans application exécutable), la plus récidivante du
registre : une garde qu'il suffit de ne pas appeler est une garde absente.

CE QUE CE CLIQUET VÉRIFIE, et rien de plus — une propriété DÉCIDABLE :

  tout module qui IMPORTE `tools.preregister` et y appelle `verify(` ou `preregister(`
  — c.-à-d. tout module qui scelle ou exécute une règle — appelle aussi `declare_design(`.

CE QU'IL NE VÉRIFIE PAS, et pourquoi. Il ne juge pas si la famille DÉCLARÉE est la bonne : le nombre
de cellules dépend de l'exécution, pas du texte. C'est `assert_control_family` qui le valide À
L'APPEL, et le design PUBLIÉ qui l'expose au lecteur du record. Tenter de deviner statiquement le
nombre de cellules serait proxifier une grandeur qu'on ne sait pas mesurer — l'erreur que ce dépôt
paie le plus cher. Mesure à l'appui : un détecteur syntaxique « seuil littéral dans une boucle »
trouve 2 sites dans tout le dépôt et **aucune des deux occurrences réelles** de la classe, car dans
les deux la famille se forme ENTRE les appels.

Dette LÉGATAIRE gelée dans `tools/control_family_baseline.json` ; aucun NOUVEAU runner scellé sans
design. ⚠️ La baseline elle-même doit déclencher le hook (classe E4 occ. 5).

Usage :
  python tools/check_control_family.py                   # cliquet : exit 1 sur tout NOUVEAU runner nu
  python tools/check_control_family.py --report          # état complet, exit 0
  python tools/check_control_family.py --only a.py b.py  # blocage restreint (arbre PARTAGÉ)
  python tools/check_control_family.py --update-baseline # gèle l'état courant
"""
import argparse
import ast
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCAN_DIRS = ("tools", os.path.join("src", "seed_ai"))
_SKIP_DIRS = ("__pycache__",)
_BASELINE = os.path.join(_ROOT, "tools", "control_family_baseline.json")

# Le module qui DÉFINIT le sceau, et les cliquets, ne sont pas des runners.
_HORS_PERIMETRE = frozenset({"tools/preregister.py", "tools/experiment_preflight.py"})

_APPELS_SCEAU = ("verify", "preregister")


def _sources():
    """(chemin relatif POSIX, source) — récursif : `tools/evo_runs/` contient l'essentiel des runners."""
    for rel in _SCAN_DIRS:
        d = os.path.join(_ROOT, rel)
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = sorted(x for x in dirnames if x not in _SKIP_DIRS)
            for fn in sorted(filenames):
                if not fn.endswith(".py") or fn.startswith("check_"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    src = open(p, encoding="utf-8").read()
                except OSError:
                    continue
                yield os.path.relpath(p, _ROOT).replace("\\", "/"), src


def scan_runners(sources=None):
    """{chemin: {'scelle': bool, 'declare': bool}} — l'analyse est AST, pas textuelle.

    Un `verify(` dans un commentaire ou une docstring ne fait pas d'un module un runner ; c'est
    exactement le genre de faux positif qui a coûté 5 puis 2 corrections aux cliquets du 2026-09-01."""
    out = {}
    for path, src in (sources if sources is not None else _sources()):
        if path in _HORS_PERIMETRE:
            continue
        try:
            arbre = ast.parse(src)
        except SyntaxError:
            continue
        importe_sceau = any(
            isinstance(n, ast.ImportFrom) and (n.module or "").endswith("preregister")
            for n in ast.walk(arbre))
        appels = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                  for n in ast.walk(arbre) if isinstance(n, ast.Call)}
        scelle = importe_sceau and any(a in appels for a in _APPELS_SCEAU)
        if scelle or "declare_design" in appels:
            out[path] = {"scelle": scelle, "declare": "declare_design" in appels}
    return out


def runners_nus(etat):
    """VERDICT du cliquet : les runners qui SCELLENT sans DÉCLARER. Jamais un booléen — la liste."""
    return sorted(p for p, v in etat.items() if v["scelle"] and not v["declare"])


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return []
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("runners_nus", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None, help="ne BLOQUE que sur ces fichiers")
    args = ap.parse_args(argv)

    etat = scan_runners()
    nus = runners_nus(etat)
    scelles = [p for p, v in etat.items() if v["scelle"]]

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({"_comment": "Runners SCELLES sans declare_design (classe E23/E10). Dette "
                                   "legataire GELEE : aucun NOUVEAU. tools/check_control_family.py",
                       "runners_nus": nus}, f, indent=1, sort_keys=True)
        print(f"baseline gelée : {len(nus)} runner(s) scellé(s) sans design")
        return 0

    baseline = set(_load_baseline())
    nouveaux = [p for p in nus if p not in baseline]
    print(f"runners scellés : {len(scelles)} | sans design : {len(nus)} "
          f"(dont {len(nouveaux)} NOUVEAUX) | légataires gelés : {len(baseline)}")
    if args.report:
        for p in nus:
            print(f"  {'NOUVEAU' if p not in baseline else 'légataire'}  {p}")
        return 0

    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
        nouveaux = [p for p in nouveaux if p in vises]

    if nouveaux:
        print("")
        for p in nouveaux:
            print(f"❌ {p} exécute une règle SCELLÉE sans appeler declare_design(...)")
        print("\n-> Un runner qui ne déclare pas son design n'est jamais interrogé sur sa FAMILLE de")
        print("   contrôles (classe E23 : mesuré le 2026-09-07, une bande fixe sur 24 cellules donnait")
        print("   0,216 de fausse alarme sur un harnais PARFAIT). Ajouter :")
        print("     design = declare_design(..., control_family=assert_control_family(cells=N))")
        print("   OU déclarer la dette : python tools/check_control_family.py --update-baseline")
        return 1
    print("OK : aucun nouveau runner scellé sans design déclaré.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
