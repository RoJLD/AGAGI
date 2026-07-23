"""SP-3 — Le demand-marker récupère-t-il un DAG de prérequis IMPOSÉ (os-taxonomy = clé de réponse) ?

Pour chaque prérequis candidat d'un topic cible, on ABLATE chirurgicalement sa compétence (bras
within-subject) et on lit l'effondrement du score d'acquisition via `ablation_verdict`. On agrège en
précision/rappel des arêtes récupérées vs imposées. Pur numpy, aucun bail.

Calibré sur vérité-terrain dans `tests/sandbox/test_instrument_calibration.py` (le nom `*_probe` /
`*verdict*` trippe volontairement le cliquet). Usage : python tools/prerequisite_recovery_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict
from tools.ground_truth_worlds import acquisition_scores, fixture_world
from tools.os_taxonomy_adapter import fixture_subgraph


def run_prerequisite_recovery_probe(subgraph, world, seeds, T=200, floor=15.0, ceiling=200.0):
    """Récupère les prérequis d'un topic par ablation within-subject. Renvoie les verdicts par arête
    candidate + le recouvrement de graphe. Le bras intact est calculé UNE fois (partagé)."""
    intact = acquisition_scores(subgraph, world, seeds, zeroed=(), T=T)
    strength = {p: "hard" for p in subgraph["hard"]}
    strength.update({p: "soft" for p in subgraph["soft"]})
    candidates = list(subgraph["hard"]) + list(subgraph["soft"]) + list(subgraph["non_edges"])

    edges = []
    for prereq in candidates:
        ablated = acquisition_scores(subgraph, world, seeds, zeroed={prereq}, T=T)
        # intervention_verified=True : zeroer la compétence du nœud PERTURBE bien l'entrée (même si,
        # pour une non-arête, la cible ne la lit pas -> bras identiques, X_DECOY légitime).
        v = ablation_verdict(intact, ablated, intervention_verified=True, floor=floor, ceiling=ceiling)
        edges.append({"prereq": prereq, "strength": strength.get(prereq),
                      "ratio": v["ratio"], "verdict": v["verdict"]})

    return {"edges": edges, "recovery": prerequisite_recovery_verdict(edges, subgraph["hard"])}


def prerequisite_recovery_verdict(edges, imposed_hard):
    """Recouvrement de graphe : une arête est RÉCUPÉRÉE si son verdict est X_DEMANDED. Précision/rappel
    contre les prérequis DURS imposés (les mous ne sont pas une cible de récupération, cf. spec §7)."""
    recovered = sorted(e["prereq"] for e in edges if e["verdict"] == "X_DEMANDED")
    imposed = sorted(set(imposed_hard))
    tp = len(set(recovered) & set(imposed))
    precision = tp / len(recovered) if recovered else 1.0
    recall = tp / len(imposed) if imposed else 1.0
    return {"precision": precision, "recall": recall, "recovered": recovered, "imposed_hard": imposed}
