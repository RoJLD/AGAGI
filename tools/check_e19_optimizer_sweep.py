# -*- coding: utf-8 -*-
"""Porte 22 — GARDE E19 APPELÉE : un runner SCELLÉ dont la règle compare des bras SOUS GRADIENT
(grille de `lr`, bras à pas distincts, `clause_E19`, `sender_lr`) appelle
`assert_verdict_invariant_to_optimizer`, sinon son nul mesure le RÉGLAGE, pas la capacité.

Cas fondateur, classe **E19** : EDR-RETAIN-COMPOSE a rétracté un record ENTIER parce que son verdict
s'inversait au seul pas d'apprentissage (`learned` 0,173 à `lr=0,02` contre 0,923 à `lr=0,002`, closure
0,97 — le « mur de rétention » était le pas, pas le substrat). La garde `assert_verdict_invariant_to_
optimizer(measure, lrs=…)` existe depuis (`tools/experiment_preflight.py`) mais rien n'obligeait un
runner à l'appeler : E19 vivait en PROSE. Voir `--report` pour l'état COURANT (jamais recopié ici, il
dérive) : combien de runners scellés le dépôt compte, combien comparent sous gradient, combien
appellent la garde. Ce module N'A AUCUNE règle scellée via `tools.preregister.verify` : son périmètre
ne peut donc pas se limiter aux appelants de `verify(...)` (c'est le trou que ce cliquet doit fermer,
pas reproduire) — un runner qui APPELLE DIRECTEMENT la garde est ipso facto « sous gradient couvert » :
la garde EST le balayage, l'appeler est la preuve. C'est ce périmètre élargi qui donne à la porte son
seul CONTRÔLE POSITIF sur données réelles (`tools/learner_calibration.py:120`, seul appelant réel du
dépôt au 2026-09-23).

CE QUE CE CLIQUET VÉRIFIE, et rien de plus — une propriété DÉCIDABLE, en AST (pas en regex, même forme
que la porte 11 `check_control_family.py`) :

  tout module (`tools/`, `src/seed_ai/`, hors `check_*.py` et hors `_HORS_PERIMETRE` — réutilisés de
  `tools.check_control_family`) qui (a) scelle/exécute une règle via `verify(...)` DONT la règle
  compare des bras à pas distincts, OU (b) appelle directement la garde, entre dans le périmètre.
  Un runner du groupe (a) sans garde est **nu**. Un nom de règle qu'on ne sait pas résoudre
  statiquement (argv, expression) est **NON RÉSOLU** — rapporté, jamais deviné, jamais compté « pas
  sous gradient ». Un nom résolu dont le fichier scellé est introuvable ou illisible est **RÈGLE
  ABSENTE**, distincte. Une règle dont le contenu SÉRIALISÉ mentionne le pas (`lr`, `learning_rate`,
  « pas d'apprentissage », `E19`) HORS des clés structurées reconnues, mais dont AUCUNE de ces formes
  ne tire, est **INDÉTERMINÉE** — rapportée, gelée, jamais lue comme « pas sous gradient » : c'est la
  correction du défaut trouvé en revue le 2026-09-23 (voir plus bas).

CE QU'IL NE VÉRIFIE PAS, et la cécité se DÉCLARE plutôt que de se prononcer :
  (a) une règle qui décrit ses bras UNIQUEMENT en prose (`mesure`, `discrimination`, `question` — texte
      libre, jamais une clé structurée) n'est pas détectable PAR FORME : ce cliquet ne lit pas le
      FRANÇAIS. C'est exactement pour ça que l'état `indetermine` existe — déclarer l'aveuglement au
      lieu de trancher « aucune grille de pas » sur une règle qui, en toutes lettres, en a une.
  (b) un appel à la garde est compté même s'il est DÉCORATIF — code mort, helper jamais appelé,
      `measure` factice passé en argument. Cette porte prouve la PRÉSENCE SYNTAXIQUE de l'appel
      (`ast.Call` nommé `assert_verdict_invariant_to_optimizer`), jamais son EXÉCUTION ni la validité
      de ce qu'il mesure — comme `appelle_garde` ne distingue pas un appel réel d'un appel mort, un
      helper qui définit la fonction sans jamais la déclencher compterait pareil.
  Elle ne juge pas non plus si le balayage `lrs=` couvre les BONS pas (c'est `assert_verdict_invariant_
  to_optimizer` elle-même, à l'appel, qui calcule la fermeture d'écart) — proxifier statiquement « ce
  balayage est-il suffisant ? » serait deviner une grandeur qu'on ne sait pas lire sans exécuter.

⚠️ **Défaut trouvé en REVUE le 2026-09-23, corrigé dans cette passe.** `sous_gradient` rendait une
affirmation NÉGATIVE DE FOND (« aucune grille de pas ») pour toute règle dont le contenu ne collait pas
à ses formes structurées — y compris des règles dont la PROSE SCELLÉE nomme explicitement `lr` ou
`E19`. Sur les 68 règles scellées : 14 détectées par les formes structurées, 17 mentionnent le pas sans
qu'aucune ne tire — dont AU MOINS TROIS runners VIVANTS comparant réellement sous gradient et sortant
`couvert` sans ligne de rapport ni entrée de baseline (`tools/evo_runs/s2_credit_ablation.py`, bras
`(b_lr) lr=…`, clause « 6a » nommant `E19` ; `s2_credit_ablation_2.py` ; `s2_reward_ablation.py`).
Formes invisibles trouvées : bras décrits en PROSE (`mesure`/`discrimination`) ; `cellule.lr_importe` /
`lr_nouveau` (TD-STEP-PILOT-R1, désormais reconnu via le préfixe `lr_`) ; une question scellée portant
sur le pas SANS clé `sender_lr` racine (DELAYED-COORD-LR-N12, `sender_lr` y vit dans `regime_scelle`,
fixe, pas la variable balayée) ; `cellule.lr = null` → `_nb_valeurs(None) = 0` (LEGACY-NAN-GUARD-R1,
LEGACY-WM-GUARD-R1, désormais reconnu directement). Corrigé : `cellule.lr` à valeur `null` et les clés
`cellule.lr_*` (préfixe, >= 2 valeurs distinctes) rejoignent les formes RECONNUES (positives) ; tout ce
qui reste mentionne le pas sans forme reconnue devient `indetermine`, jamais silencieusement « pas sous
gradient ». ⚠️ **Les comptes publiés par `--report` (sous gradient / nus) sont donc un PLANCHER** : la
détection PAR FORME ne peut pas couvrir la prose, et une règle encore invisible aujourd'hui peut exister.

Dette LÉGATAIRE gelée PAR (chemin, raison) dans `tools/e19_sweep_baseline.json` — CINQ raisons, jamais
fondues : `illisible` (le module ne s'analyse pas, `SyntaxError`), `non_resolu`, `regle_absente`,
`indetermine`, `nu`. Rang `couvert < illisible < non_resolu < regle_absente < indetermine < nu` — un
légataire dont la raison EMPIRE (ex. `non_resolu` -> `nu`) bloque comme un nu tout neuf ; l'inverse
(amélioration) ne bloque jamais. ⚠️ `nu` ET `indetermine` bloquent aussi quand ils sont TOUT NEUFS
(« couvert -> indetermine bloque », exigence explicite de la revue) : les deux sont ACTIONNABLES dans
le commit qui les introduit (appeler la garde, ou écrire `clause_E19`/`cellule.lr`) — contrairement à
`non_resolu`/`regle_absente`/`illisible`, des limites de l'ANALYSE plutôt que des choix de l'auteur,
qui restent seulement RAPPORTÉS (jamais bloquants) tant qu'ils ne régressent pas depuis un état déjà
connu. La baseline gèle aussi la LISTE des chemins qui appellent la garde
(`appelants_garde`) : c'est le SEUL contrôle positif réel de cette porte, et rien d'autre ne le protège
— si `tools/learner_calibration.py` perdait son appel, la porte resterait verte sans cette garde
dédiée. Aucun NOUVEAU `nu`, aucune régression de raison, aucune PERTE d'appelant gelé. ⚠️ La baseline
elle-même doit déclencher le hook (classe E4 occ. 5) ; `--update-baseline` refuse d'écrire sous 10
runners scellés trouvés (un `--root` ou périmètre vide désarmerait la porte en silence — même garde
que la porte 20), et REFUSE un `--only` donné SANS aucun fichier (un filtre vide filtrerait tout et
rendrait un vert trompeur).

Usage :
  python tools/check_e19_optimizer_sweep.py                    # cliquet : exit 1 sur nu/régression/perte
  python tools/check_e19_optimizer_sweep.py --report           # état complet, exit 0
  python tools/check_e19_optimizer_sweep.py --only a.py b.py   # blocage restreint (arbre PARTAGÉ)
  python tools/check_e19_optimizer_sweep.py --update-baseline  # gèle l'état courant
"""
import argparse
import ast
import copy
import glob
import json
import os
import sys
import unicodedata

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.check_control_family import _HORS_PERIMETRE, _sources  # noqa: E402,F401 — réutilisés tels quels
_BASELINE = os.path.join(_ROOT, "tools", "e19_sweep_baseline.json")
GARDE = "assert_verdict_invariant_to_optimizer"

# Rang de sévérité d'un légataire : plus haut = pire. Une régression (rang courant > rang gelé) bloque.
# `indetermine` vit STRICTEMENT entre `couvert` et `nu`, comme l'exige la revue.
_RANG = {"couvert": 0, "illisible": 1, "non_resolu": 2, "regle_absente": 3, "indetermine": 4, "nu": 5}
_MIN_SCELLES = 10

# Mots qui trahissent une mention du PAS D'APPRENTISSAGE ou de la classe E19, cherchés HORS des clés
# structurées que `sous_gradient` sait déjà lire — insensible à la casse ET aux accents.
_MOTS_PAS = ("learning_rate", "pas d'apprentissage", "lr", "e19")


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
    Sept formes structurées, aucune combinée en une seule (la raison NOMME laquelle a tiré) :
    `clause_E19` déclarée en PROSE ; `sender_lr` racine (DELAYED-COORD, un lr nommé hors convention
    `cellule`) ; `cellule.lr = null` (comparaison de pas hors grille littérale, DÉCLARÉE — jamais lue
    comme « pas de grille », null est un signal, pas un silence) ; `cellule.lr` à >= 2 pas ;
    `cellule.bras` à >= 2 bras ; `cellule.lr_*` (préfixe, ex. `lr_importe`/`lr_nouveau`) à >= 2 valeurs
    distinctes ; `cellules[*].lr` à >= 2 pas distincts. Ce qui ne tire PAS mais mentionne quand même le
    pas ailleurs dans la règle est du ressort de `mentionne_le_pas`, jamais de cette fonction : elle ne
    rend JAMAIS « aucune grille de pas » sans que l'appelant ait eu la chance de vérifier la prose."""
    if not isinstance(rule, dict):
        return False, "règle illisible"
    if "clause_E19" in rule:
        return True, "clause_E19 déclarée"
    if "sender_lr" in rule:
        return True, "sender_lr"
    cel = rule.get("cellule") if isinstance(rule.get("cellule"), dict) else {}
    if "lr" in cel and cel.get("lr") is None:
        return True, "cellule.lr=null (comparaison de pas hors grille littérale, déclarée)"
    if _nb_valeurs(cel.get("lr")) >= 2:
        return True, f"cellule.lr à {_nb_valeurs(cel.get('lr'))} pas"
    if _nb_valeurs(cel.get("bras")) >= 2:
        return True, f"cellule.bras à {_nb_valeurs(cel.get('bras'))} bras"
    cles_lr_prefixees = sorted(k for k in cel if isinstance(k, str) and k.startswith("lr_"))
    valeurs_prefixees = {str(cel[k]) for k in cles_lr_prefixees}
    if len(valeurs_prefixees) >= 2:
        return True, f"cellule.{{{', '.join(cles_lr_prefixees)}}} à {len(valeurs_prefixees)} pas distincts"
    cells = rule.get("cellules") if isinstance(rule.get("cellules"), list) else []
    lrs = {str(c.get("lr")) for c in cells if isinstance(c, dict) and "lr" in c}
    if len(lrs) >= 2:
        return True, f"cellules à {len(lrs)} pas distincts"
    return False, "aucune grille de pas"


def _redacte_cles_reconnues(rule):
    """Copie de `rule` dont les clés STRUCTURÉES que `sous_gradient` sait déjà lire sont retirées —
    sert à chercher si le pas est mentionné AILLEURS, sans se re-déclencher sur une clé déjà inspectée
    et légitimement insuffisante (ex. `cellule.lr = [0.04]`, un seul pas : ni sweep, ni aveuglement)."""
    if not isinstance(rule, dict):
        return {}
    r = copy.deepcopy(rule)
    r.pop("clause_E19", None)
    r.pop("sender_lr", None)
    cel = r.get("cellule")
    if isinstance(cel, dict):
        cel.pop("lr", None)
        for k in [k for k in cel if isinstance(k, str) and k.startswith("lr_")]:
            cel.pop(k, None)
    cellules = r.get("cellules")
    if isinstance(cellules, list):
        for c in cellules:
            if isinstance(c, dict):
                c.pop("lr", None)
    return r


def _sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def mentionne_le_pas(rule):
    """Vrai si le JSON sérialisé de `rule`, une fois les clés STRUCTURÉES retirées, mentionne encore
    `lr` / `learning_rate` / « pas d'apprentissage » / `E19` (insensible casse/accents). C'est le signal
    d'une règle dont le CONTENU parle du pas sans exposer une forme structurée reconnue — une
    INDÉTERMINATION à déclarer, jamais une négation à affirmer."""
    texte = _sans_accents(json.dumps(_redacte_cles_reconnues(rule), ensure_ascii=False))
    texte = texte.replace("’", "'").casefold()
    return any(mot in texte for mot in _MOTS_PAS)


def appelle_garde(arbre):
    """Un `ast.Call` nommé `assert_verdict_invariant_to_optimizer` — jamais un import, un commentaire
    ou une mention en docstring. ⚠️ Ne distingue PAS un appel réel d'un appel DÉCORATIF (code mort,
    helper jamais invoqué, `measure` factice) : cette porte prouve la présence syntaxique de l'appel,
    pas son exécution (cf. « CE QU'IL NE VÉRIFIE PAS » en tête de module)."""
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


def _module_pertinent(src):
    """Pré-filtre TEXTUEL bon marché (pas d'AST, la source ne PARSE pas) : ce module a-t-il une chance
    de concerner E19 ? Évite qu'un `SyntaxError` sur un fichier sans rapport (WIP d'une autre session)
    n'entre dans la baseline de cette porte — mais un fichier PERTINENT et illisible est RAPPORTÉ,
    jamais avalé (leçon de la porte 17 : une absence de signal n'est pas un signal négatif)."""
    return "verify(" in src or GARDE in src


def etat(sources, regles):
    """{chemin: {regles, non_resolus, regle_absente, indetermines, sous_gradient, raison, garde,
    illisible}}.

    Périmètre : un module entre dès qu'il RÉFÉRENCIE une règle (résolue ou non) OU appelle la garde
    directement — l'un ou l'autre suffit, un runner peut comparer des bras sous gradient SANS jamais
    sceller de règle JSON (`tools/learner_calibration.py`, seul appelant réel : ses bras `ARMS` sont
    des littéraux Python, pas une règle `verify()`). Un module qui ne PARSE pas (`SyntaxError`) mais
    dont la source brute mentionne `verify(` ou la garde entre quand même, marqué `illisible` — jamais
    silencieusement ignoré."""
    out = {}
    for path, src in sources:
        if path in _HORS_PERIMETRE:
            continue
        try:
            arbre = ast.parse(src)
        except SyntaxError:
            if _module_pertinent(src):
                out[path] = {"regles": [], "non_resolus": [], "regle_absente": [], "indetermines": [],
                             "sous_gradient": False, "raison": "ILLISIBLE (SyntaxError) — verify()/"
                             + GARDE + " mentionnés dans la source, jamais analysés", "garde": False,
                             "illisible": True}
            continue
        noms = noms_regles(arbre)
        garde = appelle_garde(arbre)
        if not noms["resolus"] and not noms["non_resolus"] and not garde:
            continue                                            # pas un runner concerné par E19
        sg, raisons, absentes, indetermines = False, [], [], []
        for nom in noms["resolus"]:
            r = regles.get(nom)
            if not isinstance(r, dict):
                absentes.append(nom)
                continue
            ok, raison = sous_gradient(r)
            if ok:
                sg = True
                raisons.append(f"{nom} : {raison}")
            elif mentionne_le_pas(r):
                indetermines.append(nom)
                raisons.append(f"{nom} : mentionne le pas (lr/E19) sans forme reconnue -- declarer "
                               "clause_E19 ou employer cellule.lr")
        if not raisons and garde:
            # aucune règle JSON ne le prouve (ou aucune n'est référencée) mais le module appelle la
            # garde lui-même : la garde EST le balayage, l'appeler EST la preuve d'un design sous gradient.
            sg = True
            raisons.append(f"appelle {GARDE}(...) directement — la garde balaie elle-même le pas")
        out[path] = {"regles": noms["resolus"], "non_resolus": noms["non_resolus"],
                     "regle_absente": absentes, "indetermines": indetermines, "sous_gradient": sg,
                     "raison": " ; ".join(raisons), "garde": garde, "illisible": False}
    return out


def runners_nus(etat_):
    """VERDICT du cliquet : les runners sous gradient qui n'appellent pas la garde. Jamais un
    booléen — la liste, triée."""
    return sorted(p for p, v in etat_.items() if v["sous_gradient"] and not v["garde"])


def classer(etat_, nus_set=None):
    """{chemin: raison} pour tout chemin qui n'est PAS `couvert` — l'ensemble que la baseline gèle.
    Un chemin peut relever de PLUSIEURS catégories à la fois (ex. une règle `regle_absente` et une
    autre `non_resolu` référencées par le même fichier) : la raison retenue est TOUJOURS la PIRE (rang
    maximal), jamais la première trouvée. Un chemin `couvert` (sous gradient ET garde, ou hors
    gradient, ou toutes ses règles référencées lisibles et non ambiguës) n'entre jamais dans la
    baseline."""
    nus = nus_set if nus_set is not None else set(runners_nus(etat_))
    out = {}
    for p, v in etat_.items():
        candidats = []
        if v.get("illisible"):
            candidats.append("illisible")
        if p in nus:
            candidats.append("nu")
        if v.get("indetermines"):
            candidats.append("indetermine")
        if v.get("regle_absente"):
            candidats.append("regle_absente")
        if v.get("non_resolus"):
            candidats.append("non_resolu")
        if candidats:
            out[p] = max(candidats, key=lambda s: _RANG[s])
    return out


def _load_baseline():
    """{chemin: raison} — le bloc `legataires` de la baseline sur disque, ou `{}` si absente."""
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return dict(json.load(fh).get("legataires", {}))


def _load_appelants_geles():
    """[chemin] — les chemins gelés comme appelants RÉELS de la garde à la dernière `--update-baseline`.
    C'est le SEUL contrôle positif de cette porte (`tools/learner_calibration.py`, au 2026-09-23) :
    sans ce gel dédié, un commit qui retire l'appel laisserait `sous_gradient` retomber à False pour ce
    chemin (il ne référence aucune règle JSON) et la porte resterait verte — silencieusement désarmée."""
    if not os.path.exists(_BASELINE):
        return []
    with open(_BASELINE, encoding="utf-8") as fh:
        return sorted(json.load(fh).get("appelants_garde", []))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    ap.add_argument("--only", nargs="*", default=None, help="ne BLOQUE que sur ces fichiers")
    args = ap.parse_args(argv)

    if args.only is not None and len(args.only) == 0:
        # E4-like : un `--only` VIDE filtrerait tout et rendrait un vert trompeur (un bug de citation
        # shell dans le hook, ex. une variable vide, désarmerait la porte sans qu'aucun signal ne le dise).
        print("REFUS : --only donné SANS aucun fichier filtre tout silencieusement (vert trompeur). "
              "Omettre --only pour un run complet, ou lister au moins un fichier.")
        return 1

    et = etat(list(_sources()), charger_regles(_ROOT))
    nus_set = set(runners_nus(et))
    legataires_actuels = classer(et, nus_set)
    appelants_actuels = sorted(p for p, v in et.items() if v["garde"])

    if args.update_baseline:
        # Garde de compte (leçon des tâches 1/2, porte 20) : un scan quasi-vide (mauvais --root,
        # périmètre partiel) écrirait une baseline VIDE ou tronquée qui désarmerait la porte EN SILENCE.
        if len(et) < _MIN_SCELLES:
            print(f"REFUS : seulement {len(et)} runner(s) scellé(s) trouvé(s) (< {_MIN_SCELLES}) -- "
                  "périmètre vide ou partiel ? Baseline NON écrite (elle désarmerait la porte en silence).")
            return 1
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Runners scelles PAR (chemin, raison) : nu (sous gradient SANS "
                                   "assert_verdict_invariant_to_optimizer), indetermine (mentionne le "
                                   "pas/E19 sans forme reconnue), regle_absente (nom resolu mais fichier "
                                   "scelle introuvable/illisible), non_resolu (nom NON resolu "
                                   "statiquement, ex. argv), illisible (le MODULE ne parse pas). "
                                   "'appelants_garde' gele les chemins qui appellent REELLEMENT la garde "
                                   "-- le controle positif de cette porte ; en PERDRE un bloque. Dette "
                                   "legataire GELEE : aucun NOUVEAU nu, aucune REGRESSION de raison, "
                                   "aucune perte d'appelant. tools/check_e19_optimizer_sweep.py",
                       "legataires": legataires_actuels,
                       "appelants_garde": appelants_actuels}, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        n = {r: sum(1 for x in legataires_actuels.values() if x == r)
             for r in ("nu", "indetermine", "regle_absente", "non_resolu", "illisible")}
        print(f"baseline gelée : {len(legataires_actuels)} légataire(s) ({n['nu']} nu, {n['indetermine']} "
              f"indéterminé, {n['regle_absente']} règle absente, {n['non_resolu']} non résolu, "
              f"{n['illisible']} illisible) | {len(appelants_actuels)} appelant(s) réel(s) de la garde gelé(s)")
        return 0

    n_sous_gradient = sum(1 for v in et.values() if v["sous_gradient"])
    n_non_resolu = sum(1 for v in et.values() if v["non_resolus"])
    n_regle_absente = sum(1 for v in et.values() if v["regle_absente"])
    n_indetermine = sum(1 for v in et.values() if v["indetermines"])
    n_illisible = sum(1 for v in et.values() if v["illisible"])
    baseline = _load_baseline()
    appelants_geles = _load_appelants_geles()
    print(f"runners scellés : {len(et)} | sous gradient (PLANCHER) : {n_sous_gradient} | nus (PLANCHER) : "
          f"{len(nus_set)} | indéterminés : {n_indetermine} | non résolus : {n_non_resolu} | règle absente : "
          f"{n_regle_absente} | illisibles : {n_illisible} | appelants de la garde : {len(appelants_actuels)} "
          f"| gelés : {len(baseline)}")

    if args.report:
        for p in sorted(et):
            statut = legataires_actuels.get(p, "couvert")
            print(f"  [{statut:14s}] {p}" + (f" : {et[p]['raison']}" if et[p]["raison"] else ""))
        return 0

    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
    else:
        vises = None

    problemes = []
    for p, s in legataires_actuels.items():
        avant = baseline.get(p)
        if avant is None:
            # `nu` ET `indetermine` bloquent NEUFS (« couvert -> indetermine bloque », exigence de la
            # revue) : les deux sont ACTIONNABLES dans le MÊME commit (garde à appeler, ou clause_E19/
            # cellule.lr à écrire) -- contrairement à `non_resolu`/`regle_absente`/`illisible`, des
            # limites de l'ANALYSE plutôt que des choix de l'auteur, qui restent non bloquants tant
            # qu'ils ne RÉGRESSENT pas depuis un état déjà connu.
            if s in ("nu", "indetermine"):
                problemes.append((p, s, "NOUVEAU"))
        elif _RANG[s] > _RANG.get(avant, 0):
            problemes.append((p, s, f"REGRESSE ({avant} -> {s})"))
    perdus = sorted(set(appelants_geles) - set(appelants_actuels))
    for p in perdus:
        problemes.append((p, "perte_garde", "PERTE DU CONTROLE POSITIF -- n'appelle plus la garde"))

    if vises is not None:
        problemes = [pr for pr in problemes if pr[0] in vises]

    # NOMME (minor ii) les non_resolu/regle_absente/illisible NOUVEAUX -- non bloquants (`nu` et
    # `indetermine` le sont déjà, via `problemes`, et apparaissent dans le bloc ÉCHEC ci-dessous), mais
    # un commit qui les introduit doit les VOIR, pas seulement le compteur agrégé de tête.
    nouveaux_signales = [(p, s) for p, s in legataires_actuels.items()
                         if s not in ("nu", "indetermine") and baseline.get(p) is None
                         and (vises is None or p in vises)]

    if nouveaux_signales:
        print("")
        print("NOUVEAU (non bloquant, à geler au prochain --update-baseline) :")
        for p, s in sorted(nouveaux_signales):
            print(f"  [{s}] {p} : {et[p]['raison']}")

    if problemes:
        print("")
        print("ÉCHEC : un runner scellé compare des bras SOUS GRADIENT sans appeler la garde E19, un "
              "légataire connu a EMPIRÉ, ou le contrôle positif de cette porte a perdu son appel :")
        for p, s, why in sorted(problemes):
            detail = et[p]["raison"] if p in et else ""
            print(f"  [{why}] {p}" + (f" : {detail}" if detail else ""))
        print(f"-> appeler {GARDE}(measure, lrs=...) (tools/experiment_preflight.py:303), ou geler EN "
              "CONNAISSANCE : python tools/check_e19_optimizer_sweep.py --update-baseline")
        return 1
    print("OK : aucun nouveau runner sous gradient sans garde E19, aucune régression, aucune perte "
          "d'appelant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
