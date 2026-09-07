"""CLIQUET P2.15 — une BARRE DE VERDICT batie sur le niveau de CHANCE doit etre validee contre le
PLAFOND DE L'INCAPABLE, pas posee a l'estime.

LE DEFAUT, MESURE. Le depot juge ses nuls de composition contre `1/K + 0.15 = 0.3167` (K=6). Le
substrat `plain`, celui que cette barre est censee declarer nul, la FRANCHIT : sa forme close
(`sigmoid(W[j,j])*tanh(W[key,j]+W[K+q,j])`, separable en key et q) atteint bien plus. Une barre qu'un
bras PROUVABLEMENT INCAPABLE franchit ne separe rien : la franchir n'etablit aucune capacite, seulement
que le plancher est bas. Cf. `tools/plain_substrate_ceiling.py` (le plafond, mesure avec son controle
positif apparie) et `tools/experiment_preflight.py::assert_bar_separates_the_incapable` (la garde).

POURQUOI UN CLIQUET ET PAS UNE NOTE. L'idiome `chance + constante` est COPIE : il vit deja dans une
dizaine de sondes, dans des specs et dans des plans, et il se reforme silencieusement a chaque nouvelle
sonde. Critere du depot : ce qui peut se reformer en silence exige un cliquet, pas une note (classe
E10 — une regle documentee sans application executable finit violee).

CE QUE LE CLIQUET CHERCHE (par AST, jamais par regex — les docstrings de ce depot CITENT l'idiome en
prose, et un regex les compterait comme dette) : une expression `<1 ou 1.0>/<x> + <constante dans ]0,1[>`
ou `chance|floor + <constante>`. Si le fichier en contient au moins une et n'APPELLE jamais
`assert_bar_separates_the_incapable`, il porte le defaut `S`. Si l'appel EXISTE mais vit
uniquement dans une branche conditionnelle -- donc rien ne montre qu'il TOURNE -- il porte `C`.

CE QU'IL NE VOIT PAS, et c'est ASSUME (non-detection declaree, pas succes) :
  * un fichier qui appelle la garde sur UNE barre et pose la suivante a l'estime -> juge propre. La
    granularite est le FICHIER, pas la ligne : indexer sur les lignes rendrait la baseline fausse au
    premier deplacement de code, et une fausse dette NOUVELLE est pire qu'une dette manquee ;
  * une barre importee depuis un autre module, ou lue dans un JSON ;
  * une barre ecrite en dur (`0.3167`) sans passer par le niveau de chance.

Baseline legataire gelee dans `tools/bar_separation_baseline.json` ; seul un NOUVEAU defaut bloque.
Usage : python tools/check_bar_separation.py [--only f1 f2 ...] [--update-baseline]
"""
import argparse
import ast
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "bar_separation_baseline.json")
_SCOPES = ("tools", os.path.join("src", "seed_ai"))
_GUARD = "assert_bar_separates_the_incapable"
_CHANCE_NAMES = {"chance", "floor", "hasard", "chance_level"}


def _is_num(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
        and not isinstance(node.value, bool)


def _is_chance_level(node):
    """`1/x` ou `1.0/x` (x quelconque), ou un identifiant qui NOMME le niveau de chance."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) \
            and _is_num(node.left) and float(node.left.value) == 1.0:
        return True
    return isinstance(node, ast.Name) and node.id in _CHANCE_NAMES


def _bar_lines(tree):
    """Lignes des expressions `chance + marge` — la forme exacte du defaut P2.15."""
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)):
            continue
        for a, b in ((n.left, n.right), (n.right, n.left)):
            if _is_chance_level(a) and _is_num(b) and 0.0 < float(b.value) < 1.0:
                out.append(n.lineno)
                break
    return sorted(set(out))


def _guard_calls(tree):
    """-> (appel INCONDITIONNEL ?, appel CONDITIONNEL ?), par descente qui SUIT les branchements.

    ⚠️ Distinction ajoutee le 2026-09-07 apres qu'un refutateur eut montre le trou : la version d'avant
    rendait True des qu'un appel EXISTAIT, y compris enferme dans un `if` dont la branche est ETEINTE au
    reglage par defaut. Mesure : `retain_compose_diagnostic_probe` appelle la garde sous
    `if ceil is not None:` avec `incapable_ceiling=None` par defaut -- elle ne tourne JAMAIS au defaut,
    et le cliquet le declarait PROPRE. Ce n'est pas un defaut vivant la-bas (la sonde refuse AUSSI de
    rendre son verdict dans cette branche), mais une NOUVELLE sonde pourrait garder l'appel eteint et
    rendre quand meme : le cliquet la benirait. D'ou le code `C`.

    ⚠️ Premiere version de CETTE correction egalement fautive, attrapee par sa propre calibration : elle
    parcourait aussi le corps du MODULE, ou une `FunctionDef` est un statement non conditionnel -- donc
    tout appel, meme profondement enfoui dans un `if`, ressortait INCONDITIONNEL. Les deux sondes
    rendaient (True, True). On descend donc explicitement, en portant le drapeau."""
    inconditionnel = conditionnel = False

    def _nom(call):
        f = call.func
        return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)

    def _descend(node, sous_condition):
        nonlocal inconditionnel, conditionnel
        for enfant in ast.iter_child_nodes(node):
            if isinstance(enfant, ast.Call) and _nom(enfant) == _GUARD:
                if sous_condition:
                    conditionnel = True
                else:
                    inconditionnel = True
            # `If`/`Try`/boucles : tout ce qu'ils contiennent est CONDITIONNEL. Une `FunctionDef` ne
            # change pas le drapeau -- l'appel y est inconditionnel DANS sa fonction, ce qui est le sens
            # utile ici (« la garde tourne quand cette fonction tourne »).
            garde = sous_condition or isinstance(enfant, (ast.If, ast.Try, ast.While, ast.For,
                                                          ast.AsyncFor, ast.IfExp))
            _descend(enfant, garde)

    _descend(tree, False)
    return inconditionnel, conditionnel


def _defects(src):
    """`None` = HORS PERIMETRE (aucune barre de cette forme), `set()` = examine et propre.

    ⚠️ Les confondre ferait compter des centaines de fichiers sans rapport comme autant de succes, et le
    cliquet annoncerait une couverture qu'il n'a pas — le defaut « annonce 100 %, en fait 35 » que ce
    depot a deja mesure sur lui-meme."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    if not _bar_lines(tree):
        return None
    inconditionnel, conditionnel = _guard_calls(tree)
    if inconditionnel:
        return set()
    if conditionnel:
        return {"C"}          # la garde EXISTE mais rien ne montre qu'elle TOURNE
    return {"S"}


def _fichiers():
    for scope in _SCOPES:
        base = os.path.join(_ROOT, scope)
        for dirpath, _dirs, names in os.walk(base):
            for nm in names:
                if nm.endswith(".py"):
                    p = os.path.join(dirpath, nm)
                    yield os.path.relpath(p, _ROOT).replace(os.sep, "/")


def scan(only=None):
    """-> (en_defaut {chemin: [codes]}, hors_perimetre [chemins], nb_examines)."""
    cibles = list(only) if only else list(_fichiers())
    en_defaut, hors, examines = {}, [], 0
    for rel in cibles:
        rel = rel.replace(os.sep, "/")
        p = os.path.join(_ROOT, rel)
        if not os.path.isfile(p) or not rel.endswith(".py"):
            continue
        with open(p, encoding="utf-8") as fh:
            d = _defects(fh.read())
        if d is None:
            hors.append(rel)
            continue
        examines += 1
        if d:
            en_defaut[rel] = sorted(d)
    return en_defaut, hors, examines


def _load_baseline():
    if not os.path.isfile(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)

    en_defaut, hors, examines = scan(only=args.only)
    if args.update_baseline:
        tout, _h, _e = scan()
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump(tout, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print(f"baseline ecrite : {len(tout)} fichier(s) en dette gelee")
        return 0

    base = _load_baseline()
    # ⚠️ DIFFERENCE D'ENSEMBLES, jamais egalite : une egalite stricte PUNIRAIT un correctif partiel
    # (un fichier qui perd un defaut deviendrait « different de la baseline » donc bloquant).
    nouveaux = {k: sorted(set(v) - set(base.get(k, []))) for k, v in en_defaut.items()}
    nouveaux = {k: v for k, v in nouveaux.items() if v}

    print(f"barres de verdict : {examines} fichier(s) examine(s), {len(hors)} hors perimetre, "
          f"{len(en_defaut)} en defaut (dont {len(base)} gele(s) en baseline)")
    if not nouveaux:
        print("OK : aucune NOUVELLE barre non validee")
        return 0
    print("")
    print("NOUVELLE(S) barre(s) de verdict non validee(s) contre le plafond de l'incapable :")
    for k, v in sorted(nouveaux.items()):
        print(f"  - {k} : {','.join(v)}")
    print("")
    print("Une barre `chance + marge` ne separe rien tant qu'on n'a pas montre que le bras PROUVABLEMENT")
    print("INCAPABLE reste DESSOUS. Appeler assert_bar_separates_the_incapable(bar, plafond, provenance)")
    print("depuis ce fichier (garde EN TETE de fonction : un refus doit etre instantane), ou declarer la")
    print("dette : python tools/check_bar_separation.py --update-baseline")
    return 1


if __name__ == "__main__":
    sys.exit(main())
