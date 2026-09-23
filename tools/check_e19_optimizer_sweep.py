# -*- coding: utf-8 -*-
"""Porte 22 — GARDE E19 APPELÉE : un runner SCELLÉ dont la règle compare des bras SOUS GRADIENT
(grille de `lr`, bras à pas distincts, `clause_E19`, `sender_lr`) appelle
`assert_verdict_invariant_to_optimizer`, sinon son nul mesure le RÉGLAGE, pas la capacité.

Cas fondateur, classe **E19** : EDR-RETAIN-COMPOSE a rétracté un record ENTIER parce que son verdict
s'inversait au seul pas d'apprentissage (`learned` 0,173 à `lr=0,02` contre 0,923 à `lr=0,002`, closure
0,97 — le « mur de rétention » était le pas, pas le substrat). La garde `assert_verdict_invariant_to_
optimizer(measure, lrs=…)` existe depuis (`tools/experiment_preflight.py`) mais rien n'obligeait un
runner à l'appeler : E19 vivait en PROSE (clé `clause_E19`, une poignée de règles scellées). Voir
`--report` pour l'état COURANT (jamais recopié ici, il dérive) : combien de runners scellés le dépôt
compte, combien comparent sous gradient, combien appellent la garde. Mesuré le 2026-09-23 : la garde a
UN SEUL appelant réel (par `ast.Call`, hors commentaire/import/docstring) — `tools/learner_calibration.
py:120`, qui balaie `lrs=(0.04, 0.004)` pour juger si l'apprenant in-world apprend la tâche linéaire de
S2-011. Ce module N'A AUCUNE règle scellée via `tools.preregister.verify` : son périmètre ne peut donc
pas se limiter aux appelants de `verify(...)` (c'est le trou que ce cliquet doit fermer, pas reproduire)
— un runner qui APPELLE DIRECTEMENT la garde est ipso facto « sous gradient couvert » : la garde EST le
balayage, l'appeler est la preuve.

CE QUE CE CLIQUET VÉRIFIE, et rien de plus — une propriété DÉCIDABLE, en AST (pas en regex, même forme
que la porte 11 `check_control_family.py`) :

  tout module (`tools/`, `src/seed_ai/`, hors `check_*.py` et hors `_HORS_PERIMETRE` — réutilisés de
  `tools.check_control_family`) qui (a) scelle/exécute une règle via `verify(...)` DONT la règle
  compare des bras à pas distincts, OU (b) appelle directement la garde, entre dans le périmètre.
  Un runner du groupe (a) sans garde est **nu**. Un nom de règle qu'on ne sait pas résoudre
  statiquement (argv, expression) est **NON RÉSOLU** — rapporté, jamais deviné, jamais compté « pas
  sous gradient » ; un nom résolu dont le fichier scellé est introuvable ou illisible est **RÈGLE
  ABSENTE**, distincte du précédent (l'un dit « je ne sais pas lire le nom », l'autre « je sais le nom
  mais pas la règle »).

CE QU'IL NE VÉRIFIE PAS. Il ne juge pas si le balayage `lrs=` couvre les BONS pas (c'est `assert_
verdict_invariant_to_optimizer` elle-même, à l'appel, qui calcule la fermeture d'écart) — proxifier
statiquement « ce balayage est-il suffisant ? » serait deviner une grandeur qu'on ne sait pas lire sans
exécuter. Il ne suit pas non plus les règles dont le CONTENU change de forme après coup (une règle
scellée est immuable par construction, `tools.preregister.verify`).

Dette LÉGATAIRE gelée PAR (chemin, raison) dans `tools/e19_sweep_baseline.json` — trois raisons, PAS
fondues : `nu` (violation confirmée), `regle_absente`, `non_resolu`. Rang `couvert < non_resolu <
regle_absente < nu` : un légataire dont la raison EMPIRE (ex. `non_resolu` -> `nu`, une résolution qui
devient possible et révèle un vrai nu) bloque comme un nu tout neuf ; l'inverse (amélioration) ne
bloque jamais. Aucun NOUVEAU `nu` hors baseline. ⚠️ La baseline elle-même doit déclencher le hook
(classe E4 occ. 5) ; `--update-baseline` refuse d'écrire sous 10 runners scellés trouvés (un `--root`
ou périmètre vide désarmerait la porte en silence — même garde que la porte 20).

Usage :
  python tools/check_e19_optimizer_sweep.py                    # cliquet : exit 1 sur nu NOUVEAU/régressé
  python tools/check_e19_optimizer_sweep.py --report           # état complet, exit 0
  python tools/check_e19_optimizer_sweep.py --only a.py b.py   # blocage restreint (arbre PARTAGÉ)
  python tools/check_e19_optimizer_sweep.py --update-baseline  # gèle l'état courant
"""
import argparse
import ast
import glob
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.check_control_family import _HORS_PERIMETRE, _sources  # noqa: E402,F401 — réutilisés tels quels
_BASELINE = os.path.join(_ROOT, "tools", "e19_sweep_baseline.json")
GARDE = "assert_verdict_invariant_to_optimizer"

# Rang de sévérité d'un légataire : plus haut = pire. Une régression (rang courant > rang gelé) bloque.
_RANG = {"couvert": 0, "non_resolu": 1, "regle_absente": 2, "nu": 3}
_MIN_SCELLES = 10


def _constantes_module(arbre):
    """Constantes CHAÎNE assignées au niveau MODULE (pas dans une fonction — une variable locale
    d'argv n'est jamais une constante résolvable statiquement)."""
    out = {}
    for n in arbre.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            out[n.targets[0].id] = n.value.value
    return out


def _resoudre(node, consts):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value], []
    if isinstance(node, ast.Name) and node.id in consts:
        return [consts[node.id]], []
    if isinstance(node, ast.IfExp):
        a, na = _resoudre(node.body, consts)
        b, nb = _resoudre(node.orelse, consts)
        return a + b, na + nb
    return [], [ast.dump(node)[:80]]


def noms_regles(arbre):
    """{"resolus": [str], "non_resolus": [str]} — arguments des appels `verify(...)`. Une expression
    qu'on ne sait pas réduire à une ou des constantes CHAÎNE est rapportée dans `non_resolus`, jamais
    devinée : c'est le cas `argv[...]` d'un runner piloté en ligne de commande."""
    consts = _constantes_module(arbre)
    resolus, non = [], []
    for n in ast.walk(arbre):
        if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == "verify" \
                and n.args:
            r, nr = _resoudre(n.args[0], consts)
            resolus += r
            non += nr
    return {"resolus": sorted(set(resolus)), "non_resolus": non}


def _nb_valeurs(v):
    if isinstance(v, list):
        return len({str(x) for x in v})
    if isinstance(v, dict):
        return len(v)
    return 0


def sous_gradient(rule):
    """(bool, raison) — vrai si la règle SCELLÉE compare des bras à pas d'apprentissage distincts.
    Cinq formes, aucune combinée en une seule (la raison NOMME laquelle a tiré) : `cellule.lr` à >= 2
    pas, `cellule.bras` à >= 2 bras, `cellules[*].lr` à >= 2 pas distincts, `clause_E19` déclarée en
    PROSE, `sender_lr` (le cas DELAYED-COORD, un lr nommé hors convention `cellule`)."""
    if not isinstance(rule, dict):
        return False, "règle illisible"
    if "clause_E19" in rule:
        return True, "clause_E19 déclarée"
    if "sender_lr" in rule:
        return True, "sender_lr"
    cel = rule.get("cellule") if isinstance(rule.get("cellule"), dict) else {}
    if _nb_valeurs(cel.get("lr")) >= 2:
        return True, f"cellule.lr à {_nb_valeurs(cel.get('lr'))} pas"
    if _nb_valeurs(cel.get("bras")) >= 2:
        return True, f"cellule.bras à {_nb_valeurs(cel.get('bras'))} bras"
    cells = rule.get("cellules") if isinstance(rule.get("cellules"), list) else []
    lrs = {str(c.get("lr")) for c in cells if isinstance(c, dict) and "lr" in c}
    if len(lrs) >= 2:
        return True, f"cellules à {len(lrs)} pas distincts"
    return False, "aucune grille de pas"


def appelle_garde(arbre):
    """Un `ast.Call` nommé `assert_verdict_invariant_to_optimizer` — jamais un import, un commentaire
    ou une mention en docstring (les trois AUTRES occurrences du nom dans le dépôt, au 2026-09-23)."""
    return any(isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == GARDE
               for n in ast.walk(arbre))


def charger_regles(root=_ROOT):
    """{nom -> règle} depuis `docs/preregistrations/*.json` — la clé EST le nom sous lequel `verify()`
    la cherche (`tools/preregister.py::_DIR`, convention `{name}.json`). Une règle introuvable sur
    disque n'est PAS une clé de ce dict (absente) ; une règle présente mais illisible vaut `None` — les
    deux sont fondues sous `regle_absente` par `etat()`, qui ne peut de toute façon RIEN en tirer."""
    out = {}
    for p in glob.glob(os.path.join(root, "docs", "preregistrations", "*.json")):
        nom = os.path.splitext(os.path.basename(p))[0]
        try:
            with open(p, encoding="utf-8") as fh:
                out[nom] = json.load(fh).get("rule", {})
        except (OSError, ValueError):
            out[nom] = None
    return out


def etat(sources, regles):
    """{chemin: {regles, non_resolus, regle_absente, sous_gradient, raison, garde}}.

    Périmètre : un module entre dès qu'il RÉFÉRENCIE une règle (résolue ou non) OU appelle la garde
    directement — l'un ou l'autre suffit, un runner peut comparer des bras sous gradient SANS jamais
    sceller de règle JSON (`tools/learner_calibration.py`, seul appelant réel : ses bras `ARMS` sont
    des littéraux Python, pas une règle `verify()`)."""
    out = {}
    for path, src in sources:
        if path in _HORS_PERIMETRE:
            continue
        try:
            arbre = ast.parse(src)
        except SyntaxError:
            continue
        noms = noms_regles(arbre)
        garde = appelle_garde(arbre)
        if not noms["resolus"] and not noms["non_resolus"] and not garde:
            continue                                            # pas un runner concerné par E19
        sg, raisons, absentes = False, [], []
        for nom in noms["resolus"]:
            r = regles.get(nom)
            if not isinstance(r, dict):
                absentes.append(nom)
                continue
            ok, raison = sous_gradient(r)
            if ok:
                sg = True
                raisons.append(f"{nom} : {raison}")
        if not raisons and garde:
            # aucune règle JSON ne le prouve (ou aucune n'est référencée) mais le module appelle la
            # garde lui-même : la garde EST le balayage, l'appeler EST la preuve d'un design sous gradient.
            sg = True
            raisons.append(f"appelle {GARDE}(...) directement — la garde balaie elle-même le pas")
        out[path] = {"regles": noms["resolus"], "non_resolus": noms["non_resolus"],
                     "regle_absente": absentes, "sous_gradient": sg,
                     "raison": " ; ".join(raisons), "garde": garde}
    return out


def runners_nus(etat_):
    """VERDICT du cliquet : les runners sous gradient qui n'appellent pas la garde. Jamais un
    booléen — la liste, triée."""
    return sorted(p for p, v in etat_.items() if v["sous_gradient"] and not v["garde"])


def classer(etat_, nus_set=None):
    """{chemin: raison} pour tout chemin qui n'est PAS `couvert` — l'ensemble que la baseline gèle.
    Rang (pire en dernier) : `non_resolu` < `regle_absente` < `nu`. Un chemin `couvert` (sous gradient
    ET garde, ou hors gradient) n'entre jamais dans la baseline."""
    nus = nus_set if nus_set is not None else set(runners_nus(etat_))
    out = {}
    for p, v in etat_.items():
        if p in nus:
            out[p] = "nu"
        elif v["regle_absente"]:
            out[p] = "regle_absente"
        elif v["non_resolus"]:
            out[p] = "non_resolu"
    return out


def _load_baseline():
    """{chemin: raison}. Rétro-compatible avec l'ancien format `{"runners_nus": [...]}` (un chemin
    listé y valait la raison `nu`) — aucune donnée gelée n'est perdue au changement de forme."""
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        payload = json.load(fh)
    if "legataires" in payload:
        return dict(payload["legataires"])
    return {p: "nu" for p in payload.get("runners_nus", [])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None, help="ne BLOQUE que sur ces fichiers")
    args = ap.parse_args(argv)

    et = etat(list(_sources()), charger_regles(_ROOT))
    nus_set = set(runners_nus(et))
    legataires_actuels = classer(et, nus_set)

    if args.update_baseline:
        # Garde de compte (leçon des tâches 1/2, porte 20) : un scan quasi-vide (mauvais --root,
        # périmètre partiel) écrirait une baseline VIDE ou tronquée qui désarmerait la porte EN SILENCE.
        if len(et) < _MIN_SCELLES:
            print(f"REFUS : seulement {len(et)} runner(s) scellé(s) trouvé(s) (< {_MIN_SCELLES}) -- "
                  "périmètre vide ou partiel ? Baseline NON écrite (elle désarmerait la porte en silence).")
            return 1
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Runners scelles PAR (chemin, raison) : nu (sous gradient SANS "
                                   "assert_verdict_invariant_to_optimizer), regle_absente (nom resolu "
                                   "mais fichier scelle introuvable/illisible), non_resolu (nom NON "
                                   "resolu statiquement, ex. argv). Dette legataire GELEE : aucun "
                                   "NOUVEAU nu, aucune REGRESSION de raison. tools/check_e19_optimizer_sweep.py",
                       "legataires": legataires_actuels}, fh, indent=1, sort_keys=True, ensure_ascii=False)
        n = {r: sum(1 for x in legataires_actuels.values() if x == r) for r in ("nu", "regle_absente", "non_resolu")}
        print(f"baseline gelée : {len(legataires_actuels)} légataire(s) "
              f"({n['nu']} nu, {n['regle_absente']} règle absente, {n['non_resolu']} non résolu)")
        return 0

    n_sous_gradient = sum(1 for v in et.values() if v["sous_gradient"])
    n_non_resolu = sum(1 for v in et.values() if v["non_resolus"])
    n_regle_absente = sum(1 for v in et.values() if v["regle_absente"])
    n_garde = sum(1 for v in et.values() if v["garde"])
    baseline = _load_baseline()
    print(f"runners scellés : {len(et)} | sous gradient : {n_sous_gradient} | nus : {len(nus_set)} | "
          f"non résolus : {n_non_resolu} | règle absente : {n_regle_absente} | appelants de la garde : "
          f"{n_garde} | gelés : {len(baseline)}")

    if args.report:
        for p in sorted(et):
            statut = legataires_actuels.get(p, "couvert")
            print(f"  [{statut:14s}] {p}" + (f" : {et[p]['raison']}" if et[p]["raison"] else ""))
        return 0

    problemes = []
    for p, s in legataires_actuels.items():
        avant = baseline.get(p)
        if avant is None:
            if s == "nu":
                problemes.append((p, s, "NOUVEAU"))
        elif _RANG[s] > _RANG.get(avant, 0):
            problemes.append((p, s, f"REGRESSE ({avant} -> {s})"))

    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
        problemes = [pr for pr in problemes if pr[0] in vises]

    if problemes:
        print("")
        print("ÉCHEC : un runner scellé compare des bras SOUS GRADIENT sans appeler la garde E19 (ou un "
              "légataire connu a EMPIRÉ) — son nul mesurera le pas, pas la capacité :")
        for p, s, why in sorted(problemes):
            print(f"  [{why}] {p} : {et[p]['raison']}")
        print(f"-> appeler {GARDE}(measure, lrs=...) (tools/experiment_preflight.py:303), ou geler EN "
              "CONNAISSANCE : python tools/check_e19_optimizer_sweep.py --update-baseline")
        return 1
    print("OK : aucun nouveau runner sous gradient sans garde E19, aucune régression de légataire.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
