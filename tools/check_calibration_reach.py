"""Portée de la calibration (P2.49 → P2.56) — parmi les déclarations `CALIBRATED` dont TOUS les cas sont des
GARDES D'ENTRÉE (« garde-seule » : `:raises`, `guard-before-world`, `entree-vide`… — la même expression que
`tests/sandbox/test_perimeter_widening.py`), combien ont un test qui IMPORTE le symbole depuis SON module ET
l'APPELLE ?

  * **DÉCLARATIVE** — un test ailleurs atteint le corps de l'instrument (il l'importe et l'appelle) : la
    déclaration est SOUS-DÉCLARÉE, le coût de résorption est une ligne (dire ce que le témoin affirme) ;
  * **MUETTE** — aucun test n'importe-et-appelle le symbole : la certification ne porte que sur la garde
    d'entrée ; résorber coûte un monde, ou une injection d'orchestrateur ;
  * **NON RÉSOLUE** — clé NUE sur un nom en COLLISION (défini dans plusieurs fichiers) : on ne devine pas
    quel `compare` un test importe (P2.56 : la v2 créditait `import tools.x` de TOUS les symboles de `x`,
    même jamais appelés — six fonctions comptées pour un test qui en appelle une) ; rapportée, jamais
    comptée d'un côté ou de l'autre.

La mesure est STRICTE et par AST : `nom(` après `from m import nom [as a]`, ou `y.nom(` après `import m [as y]`
/ `from p import m`. Un appel INDIRECT (un test appelle un orchestrateur qui appelle l'instrument) ne compte
PAS : c'est un choix déclaré, la couverture par transitivité serait un proxy de ce qu'on ne mesure pas.

Cliquet : `tools/calibration_reach_baseline.json` gèle la liste des MUETTES ; toute NOUVELLE muette bloque ;
une muette résorbée est rapportée (resserrer la baseline). Les deux comptes sont RECOMPUTÉS à chaque appel,
jamais recopiés (P2.56 : 62/39 puis 48/48 puis 35/45 — le chiffre bouge, un chiffre recopié ment).
`--update-baseline` gèle l'état courant. Usage : python tools/check_calibration_reach.py [--update-baseline]
"""
import ast
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.check_instrument_calibration import _CALIB_TESTS, scan_collisions, scan_instruments  # noqa: E402

_BASELINE = os.path.join(_ROOT, "tools", "calibration_reach_baseline.json")
_TESTS_DIR = os.path.join(_ROOT, "tests")
# ⚠️ MÊME expression que test_perimeter_widening.test_the_measured_EXPOSURE_of_head_guard_only_calibration_is_PUBLISHED :
# un test gèle l'égalité des deux (un cliquet qui compterait une AUTRE dette que celle publiée serait un faux vert).
GARDE_SEULE = re.compile(r"(:raises$|^guard-before-world$|^regime-degenere|^plan-vide|^empty-cohort|"
                         r"^entree-vide|^cohorte-vide|^selection-vide|^argument-degenere|^echelle-vide)")


def load_calibrated(path=None):
    """Le dict `CALIBRATED` du fichier de calibration, évalué littéralement (jamais importé : importer le
    module exécuterait ses fixtures). {} si absent ou illisible — RAPPORTÉ par l'appelant, pas avalé."""
    p = path or _CALIB_TESTS
    if not os.path.exists(p):
        return {}
    src = open(p, encoding="utf-8").read()
    m = re.search(r"^CALIBRATED\s*=\s*(\{.*?^\})", src, re.M | re.S)
    if not m:
        return {}
    try:
        return ast.literal_eval(m.group(1))
    except (ValueError, SyntaxError):
        return {}


def garde_seule(calibrated):
    """Clés dont TOUS les cas sont des gardes d'entrée (liste non vide)."""
    return sorted(k for k, cas in calibrated.items()
                  if isinstance(cas, list) and cas and all(GARDE_SEULE.search(str(c)) for c in cas))


def _module_of(rel_path):
    """'tools/evo_runs/x.py' -> 'tools.evo_runs.x'."""
    return rel_path[:-3].replace("/", ".").replace("\\", ".") if rel_path.endswith(".py") else rel_path


def resolve(key, instruments=None, collisions=None):
    """Clé CALIBRATED -> (module, nom) ou (None, raison). Qualifiée « chemin.py::nom » : directe. Nue : via
    le balayage du cliquet, REFUSÉE si le nom est en collision (on ne devine pas)."""
    instruments = scan_instruments() if instruments is None else instruments
    collisions = scan_collisions() if collisions is None else collisions
    if "::" in key:
        rel, name = key.split("::", 1)
        return _module_of(rel), name
    if key in collisions:
        return None, f"nom nu en COLLISION ({len(collisions[key])} fichiers) : qualifier « fichier.py::{key} »"
    if key in instruments:
        return _module_of(instruments[key]), key
    return None, "nom introuvable dans le périmètre du cliquet"


def reached_symbols(src):
    """{(module, nom)} des symboles IMPORTÉS et APPELÉS dans une source de test (AST, strict)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    from_alias = {}      # alias local -> (module, nom)      : from m import nom [as alias]
    mod_alias = {}       # alias local -> module              : import m [as y] / from p import m (sous-module)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                local = a.asname or a.name
                from_alias[local] = (node.module, a.name)
                mod_alias.setdefault(local, node.module + "." + a.name)   # si c'est un sous-module : y.nom(
        elif isinstance(node, ast.Import):
            for a in node.names:
                mod_alias[a.asname or a.name] = a.name
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name) and f.id in from_alias:
            out.add(from_alias[f.id])
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in mod_alias:
            out.add((mod_alias[f.value.id], f.attr))
    return out


def _iter_tests(tests_dir=None):
    d = tests_dir or _TESTS_DIR
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = sorted(x for x in dirnames if x != "__pycache__")
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                try:
                    yield os.path.relpath(p, _ROOT).replace("\\", "/"), open(p, encoding="utf-8").read()
                except OSError:
                    continue


def scan(calibrated=None, tests_dir=None):
    """Le compte, RECOMPUTÉ : {"garde_seule", "declaratives": {clé: [tests]}, "muettes": [clés],
    "non_resolues": {clé: raison}, "n_tests", "n_calibrated"}."""
    calibrated = load_calibrated() if calibrated is None else calibrated
    keys = garde_seule(calibrated)
    instruments, collisions = scan_instruments(), scan_collisions()
    par_test = {rel: reached_symbols(src) for rel, src in _iter_tests(tests_dir)}
    declaratives, muettes, non_resolues = {}, [], {}
    for k in keys:
        module, name = resolve(k, instruments, collisions)
        if module is None:
            non_resolues[k] = name
            continue
        temoins = sorted(rel for rel, syms in par_test.items() if (module, name) in syms)
        if temoins:
            declaratives[k] = temoins
        else:
            muettes.append(k)
    return {"n_calibrated": len(calibrated), "garde_seule": len(keys), "declaratives": declaratives,
            "muettes": sorted(muettes), "non_resolues": non_resolues, "n_tests": len(par_test)}


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return None
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f)


def etat(res, baseline):
    """VERDICT du cliquet, jamais un booléen : `nouvelles` (muettes hors baseline -> BLOQUE), `resorbees`
    (gelées mais plus muettes -> resserrer), `connues`. Baseline absente -> tout est nouveau, dit tel quel."""
    gel = set((baseline or {}).get("muettes", []))
    m = set(res["muettes"])
    return {"nouvelles": sorted(m - gel), "resorbees": sorted(gel - m), "connues": sorted(m & gel),
            "baseline_absente": baseline is None}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    res = scan()
    if not res["n_calibrated"]:
        print("ECHEC : aucun dict CALIBRATED lisible -- la portée ne peut pas être mesurée (rien n'est vérifié).")
        return 1
    print(f"CALIBRATED : {res['n_calibrated']} déclarations | garde-seule : {res['garde_seule']} | "
          f"déclaratives (un test importe ET appelle) : {len(res['declaratives'])} | muettes : {len(res['muettes'])} | "
          f"non résolues (nom nu en collision) : {len(res['non_resolues'])} | tests balayés : {res['n_tests']}")
    for k, why in sorted(res["non_resolues"].items()):
        print(f"  [NON RESOLUE] {k} -- {why}")
    if "--update-baseline" in argv:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({"_comment": "Déclarations CALIBRATED garde-seule dont AUCUN test n'importe-et-appelle le symbole "
                                   "(P2.56). Dette gelée : aucune NOUVELLE muette. tools/check_calibration_reach.py",
                       "muettes": res["muettes"]}, f, indent=1, ensure_ascii=False)
        print(f"baseline gelée : {len(res['muettes'])} muette(s) -> {os.path.relpath(_BASELINE, _ROOT)}")
        return 0
    e = etat(res, _load_baseline())
    if e["baseline_absente"]:
        print("ECHEC : baseline absente -- python tools/check_calibration_reach.py --update-baseline pour geler la dette.")
        return 1
    for k in e["resorbees"]:
        print(f"  [RESORBEE] {k} -- gelée muette, ne l'est plus : resserrer la baseline (--update-baseline)")
    for k in e["nouvelles"]:
        print(f"  [NOUVELLE MUETTE] {k} -- déclaration garde-seule qu'aucun test n'importe-et-appelle : "
              "ajouter un cas CORPS-ATTEINT (injection à dose connue pour un orchestrateur), ou déclarer la dette")
    if e["nouvelles"]:
        print(f"\nECHEC : {len(e['nouvelles'])} NOUVELLE(S) déclaration(s) muette(s). Ou déclarer : --update-baseline")
        return 1
    print(f"OK : {len(e['connues'])} muette(s), toutes légataires (baseline). Aucune nouvelle"
          + (f" ; {len(e['resorbees'])} résorbée(s) à resserrer." if e["resorbees"] else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
