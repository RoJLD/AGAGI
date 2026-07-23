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


def main():
    """Pré-vol + go/no-go SP-3. Renvoie 0 (PASS = la spécificité tient sous corrélation) ou 1 (FAIL)."""
    import numpy as np
    from tools.experiment_preflight import (declare_design, assert_positive_control,
                                            assert_not_degenerate, assert_ablation_changes_something,
                                            assert_no_aliasing, PreflightError)
    sg, world = fixture_subgraph(), fixture_world()
    seeds = list(range(12))

    design = declare_design(
        question="L'ablation within-subject récupère-t-elle un DAG de prérequis imposé, sans "
                 "faux-positiver sur un non-prérequis corrélé ?",
        replication_unit="seed", n_independent=len(seeds),
        links={"gate_impose->score": "measured", "ablation->effondrement": "measured"},
        cost_estimate="pur numpy, < 1 s")
    print(f"DESIGN: {design['replication_unit']} n={design['n_independent']}")

    intact = acquisition_scores(sg, world, seeds)
    hard = sg["hard"][0]
    ablated_hard = acquisition_scores(sg, world, seeds, zeroed={hard})
    try:
        assert_not_degenerate(intact, label="score intact")                    # métrique vivante
        assert_ablation_changes_something(intact, ablated_hard, label="ablation dure")  # pas tautologique
        assert_no_aliasing(np.asarray(intact), np.asarray(ablated_hard))       # pas d'état partagé (n/a en A1)
        assert_positive_control(
            lambda: np.median(intact) / max(np.median(ablated_hard), 1e-9),
            expect_better_than=1.5, label="récupération du prérequis dur")
    except PreflightError as e:
        print(f"PRÉ-VOL ÉCHOUE: {e}")
        return 1

    out = run_prerequisite_recovery_probe(sg, world, seeds)
    by = {e["prereq"]: e for e in out["edges"]}
    rec = out["recovery"]
    non_edge = by["Aprime_rainforest_web"]
    passed = (by[hard]["verdict"] == "X_DEMANDED"
              and non_edge["verdict"] == "X_DECOY"
              and rec["precision"] == 1.0 and rec["recall"] == 1.0)
    verdict = "GO (spécificité tient sous corrélation)" if passed else "NO-GO (faux positif corrélé)"
    print(f"VERDICT SP-3 = {verdict} | dur={by[hard]['ratio']:.2f} ({by[hard]['verdict']}) "
          f"non-arête={non_edge['ratio']:.2f} ({non_edge['verdict']}) "
          f"| précision={rec['precision']} rappel={rec['recall']}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
