"""Cliquet du graphe AGI-Taxonomy — calqué sur check_record_links / check_instrument_calibration.

Une arête « Y demande X » n'existe que si elle porte sa PREUVE mesurée complète : verdict d'ablation
X_DEMANDED (demand-marker SP-3), n >= 12 (n_floor), garde d'aliasing fonctionnel `pass` (CALIB-ALIAS) —
ou `n/a` accompagné de `specificity_control` `pass` (contrôle de demande, ablation inerte hors demande) —,
et un record docs/EDR existant. Une arête sans preuve est REJETÉE. Baseline gelée (vide en v0).

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
    fa = ev.get("functional_aliasing")
    if fa == "pass":
        pass  # garde structurel/comportemental appliqué (CALIB-ALIAS)
    elif fa == "n/a":
        if ev.get("specificity_control") != "pass":
            v.append(f"arête {lbl} : functional_aliasing='n/a' EXIGE specificity_control='pass' "
                     "(contrôle de demande : ablation inerte là où la capacité n'est pas demandée)")
    else:
        v.append(f"arête {lbl} : functional_aliasing='{fa}' (attendu 'pass', ou 'n/a' + specificity_control)")
    if not _exists(ev.get("record")):
        v.append(f"arête {lbl} : record de preuve manquant/inexistant '{ev.get('record')}'")
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
              "aliasing pass (ou n/a + specificity_control pass), record).")
        return 1
    print("OK : aucune nouvelle violation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
