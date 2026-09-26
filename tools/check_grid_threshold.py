"""Porte 24 — seuil comparé en FLOTTANTS sur une grandeur de GRILLE (classe E30, P2.105).

Ce que la porte vérifie, et rien de plus : dans le périmètre des runners (`tools/` + `src/seed_ai/`, le même que
les portes 11 et 23 — `check_control_family._sources`, réutilisé tel quel), AUCUNE comparaison NOUVELLE de la
forme « a OP b ± marge » n'est écrite en flottants nus. La forme est reconnue par l'AST : un `Compare` à un seul
opérateur (<, <=, >, >=) dont un côté est un `BinOp` Add/Sub avec, à droite, un flottant littéral (`+ 0.05`) ou
un nom qui se lit comme une marge (`marge`, `margin`, `tol`, `eps`, `s["marge"]`). Un site est DÉCLARÉ — donc
invisible à la porte — quand il passe par `tools/grid_compare.py` : `cmp_grille(x, y, marge, n_grille)` (la
grandeur est un compte, comparé sur la grille) ou `cmp_continu(x, y, marge)` (la grandeur est continue, déclarée
telle). Le helper lui-même est HORS périmètre : c'est lui qui porte le repli ordinaire.

Pourquoi. Une accuracy est un COMPTE k/N (640 évaluations) et une marge scellée à 0,05 vaut EXACTEMENT 32 pas ;
en float32 une ÉGALITÉ exacte devient un ÉCHEC, toujours du côté qui refuse. Cas fondateur (E30 occ. 1,
BILINEAR-SHAM-R1, seed 3) : 210/640 contre 178/640 + 32 → égalité, comptée échec de 1,19e-08 ; 8/12 publié pour
9/12 exact, à TROIS endroits. Second cas (P2.105) : `tools/td_step_pilot.py`, trois lectures. ⚠️ MESURÉ en
écrivant cette porte : la rétro-application du 2026-09-24 annonçait « ses trois lectures », et `_lecture_r1.n_sup`
comparait encore en flottants nus — 0 occurrence de `_cmp_grille` dans cette fonction sur les 4 versions du
fichier depuis le 2026-09-22 ; deux lectures sur trois. Corrigé dans la même passe (lectures rejouées depuis leurs
JSON suivis : bit-identiques, le défaut restait latent), et la porte existe pour que la troisième fois ne soit
pas silencieuse.

Ce qu'elle NE vérifie PAS, et c'est dit :
  (a) la forme « barre » (`x < 0.5`, sans marge) — même défaut possible quand la barre est un multiple du pas
      (le contrôle positif de R0, `max(médianes) < 0,5`, vit sur la grille 2N : routé par le helper dans cette
      passe, mais la forme n'est pas dans le motif — elle ratisserait des centaines de comparaisons continues) ;
  (b) si la grandeur comparée EST une grille : un site nu sur des moyennes ou des probabilités
      (`np.mean(a) > np.mean(b) + 0.15`, `pr <= obs + 1e-12`) est un FAUX POSITIF de la forme. La porte ne sait
      pas lire la nature d'une grandeur ; la réponse du dépôt est de faire DÉCLARER l'auteur (`cmp_continu`),
      jamais de deviner (cf. `tools/demand_marker._degeneracy`, porte 3).

Cliquet : `tools/grid_threshold_baseline.json` gèle les sites légataires PAR (chemin, fonction, texte de la
comparaison) — jamais par numéro de ligne, qui bouge à chaque édition. Toute NOUVELLE comparaison nue bloque ;
un site gelé qui a disparu est rapporté (resserrer la baseline). Un fichier ILLISIBLE est RAPPORTÉ, jamais
compté 0. `--update-baseline` refuse d'écrire sous `_MIN_SITES` sites trouvés (un arbre vide ou partiel
désarmerait la porte en silence — leçon des portes 19/20/23) et laisse le disque intact ; `--only` donné SANS
fichier est REFUSÉ (un filtre vide filtrerait tout et rendrait un vert trompeur).

Usage :
  python tools/check_grid_threshold.py                    # cliquet : exit 1 sur tout NOUVEAU site nu
  python tools/check_grid_threshold.py --report           # état complet, exit 0
  python tools/check_grid_threshold.py --only a.py b.py   # blocage restreint aux fichiers stagés (arbre PARTAGÉ)
  python tools/check_grid_threshold.py --update-baseline  # gèle l'état courant comme dette légataire
"""
import argparse
import ast
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.check_control_family import _HORS_PERIMETRE, _sources  # noqa: E402

_BASELINE = os.path.join(_ROOT, "tools", "grid_threshold_baseline.json")
_HELPER = "tools/grid_compare.py"                      # porte le repli ordinaire : hors périmètre par construction
_EXCLUS = frozenset(_HORS_PERIMETRE) | {_HELPER}
_MIN_SITES = 20                                        # sous ce nombre, --update-baseline REFUSE (arbre partiel)
_HELPERS = ("cmp_grille", "cmp_continu")
_MARGE = re.compile(r"marge|margin|\btol\b|_tol\b|\btol_|\beps\b|epsilon", re.I)
_OPS = (ast.Gt, ast.GtE, ast.Lt, ast.LtE)


def _lit_marge(node):
    """Un `BinOp` Add/Sub dont l'opérande DROIT est un flottant littéral (`y + 0.05`) ou un nom/attribut/indice
    qui se lit comme une marge (`y - marge`, `y + s["marge"]`, `y + self.tol`). Fonction PURE."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, (ast.Add, ast.Sub)):
        return False
    r = node.right
    if isinstance(r, ast.Constant):
        return isinstance(r.value, float)
    try:
        return bool(_MARGE.search(ast.unparse(r)))
    except Exception:                                 # nœud non dé-parsable : pas une marge lisible
        return False


def _fonction_de(node, parents):
    n = node
    while n in parents and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        n = parents[n]
    return n.name if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<module>"


def sites(path, src):
    """[{cle, chemin, fonction, ligne, texte}] des comparaisons NUES de la forme, ou None si le fichier est
    ILLISIBLE (SyntaxError) — rapporté par l'appelant, jamais compté 0. La clé ne contient PAS le numéro de
    ligne : (chemin, fonction, texte) survit aux éditions au-dessus du site."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    parents = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parents[c] = n
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], _OPS)):
            continue
        if _lit_marge(n.left) or _lit_marge(n.comparators[0]):
            fn = _fonction_de(n, parents)
            texte = ast.unparse(n)
            out.append({"cle": f"{path}::{fn}::{texte}", "chemin": path, "fonction": fn,
                        "ligne": int(getattr(n, "lineno", 0)), "texte": texte})
    return out


def appels_helper(src):
    """Nombre d'appels à `cmp_grille(` / `cmp_continu(` — les sites DÉCLARÉS (AST, pas textuel : un nom dans une
    docstring ne compte pas)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            nom = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if nom in _HELPERS:
                n += 1
    return n


def scan(sources=None):
    """{"sites": [...], "illisibles": [chemins], "declares": {chemin: n_appels}} — RECOMPUTÉ à chaque appel."""
    res = {"sites": [], "illisibles": [], "declares": {}}
    for path, src in (_sources() if sources is None else sources):
        if path in _EXCLUS:
            continue
        s = sites(path, src)
        if s is None:
            res["illisibles"].append(path)
            continue
        res["sites"].extend(s)
        n = appels_helper(src)
        if n:
            res["declares"][path] = n
    return res


def cles(res):
    """L'ensemble des clés (un site écrit deux fois dans la même fonction compte UNE clé, deux occurrences)."""
    return sorted({s["cle"] for s in res["sites"]})


def _load_baseline():
    if os.path.exists(_BASELINE):
        with open(_BASELINE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"sites": []}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None, help="ne BLOQUE que sur ces fichiers")
    args = ap.parse_args(argv)
    if args.only is not None and not args.only:
        print("REFUS : --only donné SANS aucun fichier filtre tout silencieusement (vert trompeur). "
              "Omettre --only pour un run complet, ou lister au moins un fichier.")
        return 2

    res = scan()
    toutes = cles(res)
    n_occ = len(res["sites"])
    fichiers = sorted({s["chemin"] for s in res["sites"]})
    n_decl = sum(res["declares"].values())
    print(f"sites nus (a OP b ± marge) : {len(toutes)} clé(s), {n_occ} occurrence(s) dans {len(fichiers)} fichier(s) | "
          f"déclarés par helper : {n_decl} appel(s) dans {len(res['declares'])} fichier(s) | "
          f"illisibles : {len(res['illisibles'])}")
    for p in res["illisibles"]:
        print(f"  [ILLISIBLE] {p} -- SyntaxError : rapporté, jamais compté 0")

    if args.update_baseline:
        if len(toutes) < _MIN_SITES:
            print(f"REFUS : {len(toutes)} site(s) trouvé(s) < {_MIN_SITES} — arbre vide ou partiel ; la baseline sur "
                  f"disque reste INCHANGÉE (une baseline gelée sur un arbre partiel désarmerait la porte en silence).")
            return 2
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Porte 24 (E30) : sites LÉGATAIRES de comparaison nue « a OP b ± marge », gelés PAR "
                                   "(chemin::fonction::texte). Toute NOUVELLE clé bloque ; router par "
                                   "tools/grid_compare.py (cmp_grille / cmp_continu) plutôt que geler.",
                       "sites": toutes}, fh, indent=2, ensure_ascii=False)
        print(f"baseline gelée : {len(toutes)} site(s) -> {_BASELINE}")
        return 0

    geles = set(_load_baseline().get("sites", []))
    nouveaux = [k for k in toutes if k not in geles]
    resorbes = sorted(geles - set(toutes))
    hors_portee = []
    if args.only is not None:
        portee = {f.replace("\\", "/") for f in args.only}
        dans = [k for k in nouveaux if k.split("::", 1)[0] in portee]
        hors_portee = [k for k in nouveaux if k not in dans]
        nouveaux = dans
    print(f"gelés (baseline) : {len(geles)} | NOUVEAUX : {len(nouveaux)} | résorbés depuis le gel : {len(resorbes)}")

    if args.report:
        par_cle = {}
        for s in res["sites"]:
            par_cle.setdefault(s["cle"], []).append(s["ligne"])
        for k in toutes:
            etat = "gelé" if k in geles else "NOUVEAU"
            print(f"  [{etat}] {k}  (l. {', '.join(str(l) for l in par_cle[k])})")
        for p, n in sorted(res["declares"].items()):
            print(f"  [déclaré] {p} : {n} appel(s) à cmp_grille/cmp_continu")
        for k in resorbes:
            print(f"  [résorbé] {k} -- plus dans l'arbre : resserrer la baseline (--update-baseline)")
        return 0

    for k in hors_portee:
        print(f"  [NOUVEAU, HORS PORTÉE de ce commit] {k} -> à traiter par la session qui l'a écrit")
    for k in resorbes:
        print(f"  [résorbé] {k} -- plus dans l'arbre : resserrer la baseline")
    for k in nouveaux:
        print(f"  [NOUVELLE COMPARAISON NUE] {k}")
    if nouveaux:
        print("\nUne comparaison a marge en FLOTTANTS sur une grandeur de grille perd l'EGALITE (E30 : 8/12 publie "
              "pour 9/12 exact).\nRouter par tools/grid_compare.py : cmp_grille(x, y, marge, n_grille) si la grandeur "
              "est un COMPTE, cmp_continu(x, y, marge) si elle est continue (DECLARE) --\nou geler EN CONNAISSANCE : "
              "python tools/check_grid_threshold.py --update-baseline")
        return 1
    print("OK : aucune nouvelle comparaison nue hors baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
