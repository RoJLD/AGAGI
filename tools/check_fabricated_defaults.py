"""Cliquet : aucune NOUVELLE agrégation qui fabrique une CONSTANTE sur une collection vide.

    python tools/check_fabricated_defaults.py            # état + refus des NOUVEAUX sites
    python tools/check_fabricated_defaults.py --report   # liste tout, exit 0
    python tools/check_fabricated_defaults.py --only a.py b.py
    python tools/check_fabricated_defaults.py --update-baseline

LA FORME TRAQUÉE, et pourquoi elle est la plus coûteuse de ce dépôt :

    med = float(np.median(ages)) if ages else 0.0

Une cohorte vide n'est pas une cohorte qui a survécu 0 tick. Le premier cas est une **absence de
mesure**, le second une **mesure**. La forme ci-dessus les rend INDISCERNABLES — et dans un dépôt dont
la plupart des résultats sont NÉGATIFS, un négatif fabriqué ressemble à tous les autres. C'est la
forme (a) des trois documentées dans `CLAUDE.md` (entrée vide → verdict de fond), et elle a déjà
produit des conclusions gravées : `PAS DE RUNG`, `AUTEL MORT`, `N_EMERGE_PAS`.

⚠️ **Le pire cas mesuré est un défaut à 1.0 sur un RATIO** (`tools/g_fidelity_probe.py`) : l'absence
de donnée y prend exactement la valeur du résultat NUL — « l'ablation n'a rien fait ». Une absence
n'y devient pas seulement un chiffre, elle devient LA conclusion.

CE QUI EST ACCEPTÉ, et ce n'est pas une tolérance mais la bonne réponse : `None`, `float("nan")`,
`np.nan`. Ils DISENT « je ne sais pas ». Le dépôt a déjà corrigé un site dans ce sens
(`tools/s2_openloop_probe.py`, dont le commentaire explique la faute) : ce cliquet généralise ce
correctif au lieu de le laisser isolé.

INVENTAIRE AU GEL (2026-09-09) : 147 sites hors tests — **49 honnêtes** (nan/None) et **98 qui
FABRIQUENT** une constante (88 à `0.0`, 5 à `1.0`). Les 98 sont gelés comme dette légataire : ce
cliquet ne les corrige pas, il empêche le 99ᵉ.

⚠️ DÉTECTION PAR AST, jamais par regex : un `if ... else` peut s'écrire sur plusieurs lignes, et une
regex y verrait moins que ce que sa docstring promet — l'angle mort qui a coûté huit élargissements
au cliquet de calibration. Comparaison par DIFFÉRENCE D'ENSEMBLES, jamais par égalité : corriger un
site ne doit jamais faire échouer le cliquet.
"""
import argparse
import ast
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "fabricated_defaults_baseline.json")
_SCAN_DIRS = ("tools", "src", "backend")
_SCAN_SKIP = ("__pycache__", "node_modules")

# Les agrégateurs qui résument une COLLECTION en un scalaire. `sum`/`len` sont exclus à dessein :
# `sum([])` vaut 0 et c'est ARITHMÉTIQUEMENT juste, alors que `median([])` n'a pas de valeur.
_AGREGATEURS = {"mean", "median", "average", "nanmean", "nanmedian", "std", "var", "max", "min"}


def _est_agregation(noeud):
    """Le nœud est-il un appel d'agrégation sur une collection ? (np.mean, statistics.median, …)"""
    while isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and \
            noeud.func.id in ("float", "int", "round") and noeud.args:
        noeud = noeud.args[0]              # `float(np.median(...))` → on descend
    if not isinstance(noeud, ast.Call):
        return None
    f = noeud.func
    if isinstance(f, ast.Attribute) and f.attr in _AGREGATEURS:
        base = f.value
        nom = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
        if nom in ("np", "numpy", "statistics", "stat"):
            return f"{nom}.{f.attr}"
    return None


def _est_constante_numerique(noeud):
    """`0.0`, `1.0`, `0`, `-1` … mais PAS `None`, `nan`, une variable, ni un appel."""
    if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
        noeud = noeud.operand
    while isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and \
            noeud.func.id in ("float", "int") and noeud.args:
        noeud = noeud.args[0]
    if not isinstance(noeud, ast.Constant):
        return None
    v = noeud.value
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and v != v:     # nan : honnête, on l'accepte
        return None
    return repr(v)


def sites_dans(src, chemin):
    """{clé: description} des agrégations à défaut FABRIQUÉ dans une source."""
    try:
        arbre = ast.parse(src)
    except SyntaxError:
        return {}
    out = {}
    for n in ast.walk(arbre):
        if not isinstance(n, ast.IfExp):
            continue
        agg = _est_agregation(n.body)
        if agg is None:
            continue
        cst = _est_constante_numerique(n.orelse)
        if cst is None:
            continue                        # None / nan / expression : HONNÊTE, on passe
        cle = f"{chemin}:{n.lineno}"
        out[cle] = (f"{chemin}:{n.lineno} — `{agg}(...) if ... else {cst}` : une collection VIDE y "
                    f"devient {cst}, indiscernable d'une mesure")
    return out


def _iter_sources(only=None):
    if only:
        for p in only:
            q = p if os.path.isabs(p) else os.path.join(_ROOT, p)
            if q.endswith(".py") and os.path.exists(q):
                yield os.path.relpath(q, _ROOT).replace("\\", "/"), open(q, encoding="utf-8").read()
        return
    for rel in _SCAN_DIRS:
        d = os.path.join(_ROOT, rel)
        if not os.path.isdir(d):
            continue
        for dp, dn, fns in os.walk(d):
            dn[:] = sorted(x for x in dn if x not in _SCAN_SKIP and not x.startswith("."))
            for fn in sorted(fns):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    src = open(p, encoding="utf-8").read()
                except OSError:
                    continue
                yield os.path.relpath(p, _ROOT).replace("\\", "/"), src


def scan(only=None):
    trouve = {}
    for chemin, src in _iter_sources(only):
        trouve.update(sites_dans(src, chemin))
    return trouve


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("legataires", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cliquet des defauts FABRIQUES.")
    ap.add_argument("--report", action="store_true", help="liste tout, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gele l'etat courant")
    ap.add_argument("--only", nargs="*", default=None, help="restreint le scan (arbre partage)")
    args = ap.parse_args(argv)

    if args.update_baseline:
        trouve = scan()                     # le gel porte TOUJOURS sur l'arbre entier
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({"_comment": ("Sites LEGATAIRES ou une agregation fabrique une constante sur "
                                    "une collection vide. Le cliquet refuse tout NOUVEAU site. "
                                    "Retirer une ligne quand elle est corrigee -- jamais en ajouter "
                                    "pour faire passer le hook."),
                       "legataires": trouve}, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline gele : {len(trouve)} site(s) legataire(s) -> {_BASELINE}")
        return 0

    trouve = scan(args.only)
    base = _load_baseline()
    # DIFFERENCE D'ENSEMBLES, jamais egalite : corriger un site ne doit pas faire echouer le cliquet.
    nouveaux = {k: v for k, v in trouve.items() if k not in base}
    resorbes = [k for k in base if k not in trouve] if not args.only else []

    if args.report:
        print(f"defauts fabriques : {len(trouve)} (dont {len(base)} legataires, "
              f"{len(nouveaux)} NOUVEAUX)")
        for k, v in sorted(trouve.items()):
            print(f"  [{'LEGATAIRE' if k in base else 'NOUVEAU  '}] {v}")
        if resorbes:
            print(f"\n  resorbes : {len(resorbes)} -> `--update-baseline` pour resserrer")
        return 0

    if nouveaux:
        print("ECHEC : de NOUVELLES agregations fabriquent une constante sur une collection vide.\n")
        for k, v in sorted(nouveaux.items()):
            print(f"  {v}")
        print("\nUne collection VIDE n'est pas une mesure a zero : rendre `None` ou `float('nan')`,")
        print("ou LEVER si l'etat est impossible. Un negatif fabrique ressemble a tous les autres.")
        print("  OU declare la dette : python tools/check_fabricated_defaults.py --update-baseline")
        return 1

    print(f"OK : {len(trouve)} defaut(s) fabrique(s), tous legataires (baseline). Aucun nouveau.")
    if resorbes:
        print(f"  ({len(resorbes)} resorbe(s) -- `--update-baseline` pour resserrer le cliquet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
