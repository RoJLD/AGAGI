"""Cliquet du graphe AGI-Taxonomy — calqué sur check_record_links / check_instrument_calibration.

Une arête « Y demande X » n'existe que si elle porte sa PREUVE mesurée complète :
  - `ablation_verdict == "X_DEMANDED"` (demand-marker SP-3) ;
  - `n >= 12` (n_floor) ;
  - `specificity_control == "pass"` — **TOUJOURS**, quelle que soit la valeur de `functional_aliasing` ;
  - `functional_aliasing` dans {`pass`, `n/a`}, `n/a` réservé à `ablation_target == "input"` ;
  - un record docs/EDR existant.

Pourquoi `specificity_control` est exigé SANS EXCEPTION (durcissement 2026-09-01) : le bras PRINCIPAL
d'une arête est arithmétiquement forcé — après ablation d'une entrée nécessaire l'agent ne peut plus
dépasser le plancher 1/K, donc X_DEMANDED est garanti dès que le bras intact est vivant, et ce bras ne
distingue pas une vraie demande d'une tautologie. Le seul bras dont l'issue négative est RÉELLEMENT
atteignable est le contrôle de demande (NO-COORD pour language->perception, PRESENT pour
memory->perception : même ablation, information redondante disponible ailleurs) — c'est lui qui porte
tout le contenu empirique des arêtes gravées. Preuve que l'issue alternative existe : l'itération 1 de
MEM-PERCEPTION a ÉCHOUÉ ce contrôle (ratio 4.329) et a dû être corrigée. L'ancienne règle acceptait
`functional_aliasing == "pass"` SEUL, c.-à-d. gravait une arête sur son seul bras forcé.

`ablation_target` (dans `evidence`, valeurs `input` | `substrate`, **défaut `input` si absent** —
compatibilité légataire : les deux arêtes gravées ablatent l'ENTRÉE) : couper dans le SUBSTRAT peut
dégrader du calcul hors-demande, donc `functional_aliasing == "n/a"` y est refusé — la garde CALIB-ALIAS
doit être `pass`.

Une arête sans preuve est REJETÉE. Baseline gelée (vide en v0).

Le fichier commence par `check_` -> exclu du scan du cliquet de calibration (pas d'auto-référence).

Usage :
  python tools/check_agi_taxonomy.py                    # exit 1 sur toute NOUVELLE violation
  python tools/check_agi_taxonomy.py --report           # liste tout, exit 0
  python tools/check_agi_taxonomy.py --update-baseline  # gèle l'état courant
"""
import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")
_CAPS = os.path.join(_DATA, "capabilities.json")
_DEMANDS = os.path.join(_DATA, "demands.json")
_BASELINE = os.path.join(_ROOT, "tools", "agi_taxonomy_baseline.json")
_VALID_STRENGTH = {"hard", "soft"}
_VALID_ABLATION_TARGET = {"input", "substrate"}
_DEFAULT_ABLATION_TARGET = "input"  # légataire : les 2 arêtes gravées ablatent l'ENTRÉE
# M4 du brainstorm taxonomies (2026-09-02) : la porte ne lisait JAMAIS le bras intact — une arete dont
# le bras intact est AU PLANCHER passait (X_DEMANDED est arithmetiquement force des que l'able est
# plafonne au hasard, mais si l'intact ne depasse pas la barre d'emergence, il n'y a RIEN dont on
# mesure la demande). Toute NOUVELLE arete declare `coord_intact` (valeur mesuree du bras intact) et
# `emergence_bar` (la barre, DECLAREE par l'auteur — regle « ne pas proxifier », cf. demand_marker) et
# doit avoir coord_intact >= emergence_bar.
#
# P2.15 (2026-09-07) — la porte verifiait la coherence INTERNE de la barre, jamais son PLACEMENT. Une
# arete pouvait declarer `emergence_bar: 0.3167` et passer, alors qu'un substrat prouvablement incapable
# de la tache franchit deja cette valeur : le bras intact aurait alors « emerge » sans rien savoir faire.
# Toute NOUVELLE arete qui declare une barre declare donc AUSSI le plafond du bras incapable
# (`incapable_ceiling`) et d'OU il vient (`ceiling_provenance`), et la barre doit etre STRICTEMENT
# au-dessus. Le plafond ne peut pas etre devine par la porte : le deviner, c'est passer le niveau de
# CHANCE, et c'est l'erreur P2.15 elle-meme (l'incapable y atteignait bien plus que 1/K).
# ⚠️ EXEMPTION LEVEE le 2026-09-08, PAR LA MESURE et non par le gel. Les deux aretes gravees avant
# M4 declarent desormais leur bras intact ET une barre d'emergence DERIVEE DU PLAFOND MESURE d'un
# agent NON ENTRAINE, au regime PUBLIE (flip_p=0.3), MAX sur 12 seeds. Marges : language->perception
# 0.3438 contre 0.1989 (1.87x) ; memory->perception 0.6547 contre 0.2431 (2.89x). L'ensemble reste
# VIDE et doit le rester : une exemption qui survit a la mesure devient une decoration.
_LEGATAIRES_SANS_COORD = frozenset()
# ⚠️ DERNIER GEL LEVE le 2026-09-08, PAR LA MESURE. `language->memory` declarait `emergence_bar:
# 0.5` sans plafond d'incapable, et le gel disait : « ni la forme close du plain ni le bras able
# (~1/K) ne le fournissent ». C'etait vrai des DEUX candidats envisages, et faux de la question :
# le plafond pertinent est celui d'un agent qui n'a RIEN APPRIS, mesurable a COUT NUL dans le
# dispositif (zero episode). Mesure au regime publie (D=0, K=6, bilineaire) : 0.1859 sur 12 seeds
# -- au-dessus du hasard 1/K=0.1667, donc ce n'est PAS le niveau de chance passe par reflexe.
# La barre 0.5 separe (marge 0.30) et le bras intact 0.819 la franchit d'un facteur 4.40.
# LES DEUX ENSEMBLES SONT DESORMAIS VIDES : aucune arete du graphe n'echappe a la preuve.
_LEGATAIRES_SANS_PLAFOND = frozenset()
_PROVENANCE_MIN = 20


def _exists(rel):
    return bool(rel) and os.path.isfile(os.path.join(_ROOT, rel))


def validate_node(node):
    """Violations d'un nœud-capacité (liste vide = conforme)."""
    v = []
    nid = node.get("id", "?")
    for f in ("id", "title", "description", "evidence_criterion", "probe", "record"):
        if not node.get(f):
            v.append(f"nœud {nid} : champ requis manquant/vide '{f}'")
    if node.get("probe") and not _exists(node["probe"]):
        v.append(f"nœud {nid} : probe inexistant '{node['probe']}'")
    if node.get("record") and not _exists(node["record"]):
        v.append(f"nœud {nid} : record inexistant '{node['record']}'")
    return v


def validate_edge(edge, capability_ids):
    """Violations d'une arête-demande. La preuve mesurée COMPLÈTE est exigée (cf. docstring module)."""
    v = []
    lbl = f"{edge.get('capability', '?')}->{edge.get('prerequisite', '?')}"
    for f in ("capability", "prerequisite", "strength", "evidence"):
        if edge.get(f) in (None, ""):
            v.append(f"arête {lbl} : champ requis manquant '{f}'")
    if edge.get("strength") not in _VALID_STRENGTH:
        v.append(f"arête {lbl} : strength invalide '{edge.get('strength')}' (attendu hard|soft)")
    for ref in ("capability", "prerequisite"):
        if edge.get(ref) and edge[ref] not in capability_ids:
            v.append(f"arête {lbl} : {ref} '{edge[ref]}' absent de capabilities.json")
    ev = edge.get("evidence") or {}
    if ev.get("ablation_verdict") != "X_DEMANDED":
        v.append(f"arête {lbl} : ablation_verdict='{ev.get('ablation_verdict')}' "
                 "(exigé X_DEMANDED — demand-marker SP-3)")
    if not isinstance(ev.get("n"), int) or ev.get("n", 0) < 12:
        v.append(f"arête {lbl} : n={ev.get('n')} (exigé entier >= 12, n_floor)")
    # Contrôle de DEMANDE — exigé TOUJOURS, indépendamment de functional_aliasing. Le bras principal est
    # arithmétiquement forcé (sous ablation l'agent est plafonné au hasard) : seul ce contrôle a une issue
    # négative réellement atteignable, donc lui seul rend l'arête non triviale.
    if ev.get("specificity_control") != "pass":
        v.append(f"arête {lbl} : specificity_control='{ev.get('specificity_control')}' "
                 "(exigé 'pass' EN TOUTE CIRCONSTANCE : le bras principal est arithmétiquement forcé — "
                 "après ablation l'agent est plafonné au hasard, X_DEMANDED est garanti —, seul le "
                 "contrôle de demande (même ablation, information redondante ailleurs) peut échouer, "
                 "donc lui seul porte le contenu empirique de l'arête)")
    target = ev.get("ablation_target", _DEFAULT_ABLATION_TARGET)
    if target not in _VALID_ABLATION_TARGET:
        v.append(f"arête {lbl} : ablation_target='{target}' "
                 "(attendu input|substrate ; absent = 'input' par compatibilité légataire)")
    fa = ev.get("functional_aliasing")
    if fa not in ("pass", "n/a"):
        v.append(f"arête {lbl} : functional_aliasing='{fa}' (attendu 'pass' — garde CALIB-ALIAS —, "
                 "ou 'n/a' pour une ablation d'ENTRÉE seulement)")
    elif fa == "n/a" and target == "substrate":
        v.append(f"arête {lbl} : functional_aliasing='n/a' REFUSÉ avec ablation_target='substrate' "
                 "(le 'n/a' ne couvre qu'une ablation d'ENTRÉE ; couper dans le substrat peut dégrader "
                 "du calcul hors-demande, la garde d'aliasing fonctionnel CALIB-ALIAS doit être 'pass')")
    if not _exists(ev.get("record")):
        v.append(f"arête {lbl} : record de preuve manquant/inexistant '{ev.get('record')}'")
    # M4 (2026-09-02) : le bras INTACT doit exister et depasser la barre d'emergence declaree.
    if lbl not in _LEGATAIRES_SANS_COORD:
        ci, bar = ev.get("coord_intact"), ev.get("emergence_bar")
        if not isinstance(ci, (int, float)) or not isinstance(bar, (int, float)):
            v.append(f"arête {lbl} : coord_intact={ci!r} / emergence_bar={bar!r} (exigés NUMERIQUES : "
                     "sans le bras intact, X_DEMANDED est le bras arithmetiquement force d'un agent "
                     "qui n'a rien appris — un intact au plancher passait la porte)")
        elif float(ci) < float(bar):
            v.append(f"arête {lbl} : coord_intact={ci} SOUS emergence_bar={bar} — le bras intact n'a "
                     "pas emerge, la demande mesurée est celle d'une competence ABSENTE")
        elif lbl not in _LEGATAIRES_SANS_PLAFOND:
            # P2.15 : la barre doit SEPARER. Une barre sous le plafond de l'incapable est franchie par
            # un bras qui ne sait rien faire -> « emergence » vide.
            ceil, prov = ev.get("incapable_ceiling"), ev.get("ceiling_provenance")
            if not isinstance(ceil, (int, float)) or isinstance(ceil, bool):
                v.append(f"arête {lbl} : emergence_bar={bar} declaree sans incapable_ceiling NUMERIQUE "
                         "(P2.15 : une barre qu'un bras prouvablement incapable franchit ne separe "
                         "rien — la franchir n'etablit aucune capacite, seulement que le plancher est bas)")
            elif not isinstance(prov, str) or len(prov.strip()) < _PROVENANCE_MIN:
                v.append(f"arête {lbl} : ceiling_provenance manquante ou trop courte ({prov!r}) — "
                         "ecrire d'OU vient incapable_ceiling (forme close, autre substrat, mesure). "
                         "Sans elle, rien ne distingue un plafond ETABLI d'un niveau de CHANCE passe "
                         "par reflexe, et c'est exactement la confusion qui a produit P2.15")
            elif float(bar) <= float(ceil):
                v.append(f"arête {lbl} : emergence_bar={bar} NE SEPARE RIEN — un bras prouvablement "
                         f"incapable atteint deja {ceil} (provenance : {str(prov).strip()}). Relever la "
                         "barre AU-DESSUS du plafond de l'incapable.")
    return v


def validate_graph(capabilities, demands):
    """Toutes les violations du graphe (nœuds puis arêtes)."""
    ids = {c.get("id") for c in capabilities}
    out = []
    for c in capabilities:
        out += validate_node(c)
    for e in demands:
        out += validate_edge(e, ids)
    return out


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="Liste toutes les violations, exit 0.")
    ap.add_argument("--update-baseline", action="store_true", help="Gèle l'état courant.")
    args = ap.parse_args(argv)

    caps = _load(_CAPS, [])
    demands = _load(_DEMANDS, [])
    violations = validate_graph(caps, demands)

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"violations": violations}, fh, indent=2, ensure_ascii=False)
        print(f"baseline gelé : {len(violations)} violations -> {_BASELINE}")
        return 0

    known = set(_load(_BASELINE, {"violations": []}).get("violations", []))
    nouvelles = [x for x in violations if x not in known]
    print(f"AGI-Taxonomy : {len(caps)} capacités, {len(demands)} arêtes | "
          f"{len(violations)} violations (dont {len(nouvelles)} NOUVELLES)")
    if args.report:
        for x in violations:
            print("  -", x)
        return 0
    for x in nouvelles:
        print("  [NOUVELLE VIOLATION]", x)
    if nouvelles:
        print("\nUne arête n'existe que si elle porte sa preuve (X_DEMANDED, n>=12, "
              "specificity_control pass TOUJOURS, aliasing pass — 'n/a' seulement si "
              "ablation_target='input' —, record).")
        return 1
    print("OK : aucune nouvelle violation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
