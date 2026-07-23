"""Adaptateur : un sous-graphe au format os-taxonomy (arêtes topicId/prerequisiteId/strength/reason)
-> structure regroupée pour la sonde de récupération de prérequis (SP-3).

Responsabilité UNIQUE : parsing et regroupement. Aucune affirmation scientifique ici (les noms ne
matchent volontairement AUCUN motif d'instrument du cliquet de calibration)."""
import json
import os

_FIXTURE_DEPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "os_taxonomy", "dependencies.json")


def load_dependencies(path):
    """Lit un fichier de dépendances au format os-taxonomy. Renvoie la liste brute des lignes."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def subgraph_for(rows, target_id):
    """Regroupe les prérequis DIRECTS de `target_id` par force, et liste les non-prérequis présents.

    non_edges = tout identifiant du graphe qui n'est NI le target NI un prérequis TRANSITIF (fermeture)
    du target : ce sont les candidats du test de spécificité (dont le non-prérequis CORRÉLÉ). ⚠️ On
    exclut la FERMETURE, pas seulement les prérequis directs : un ancêtre d'un prérequis (ex. Z, ancêtre
    du dur Ah) reste un VRAI prérequis de B — l'ablater effondre B à juste titre, donc ce n'est pas une
    non-arête."""
    hard = [r["prerequisiteId"] for r in rows
            if r["topicId"] == target_id and r["strength"] == "hard"]
    soft = [r["prerequisiteId"] for r in rows
            if r["topicId"] == target_id and r["strength"] == "soft"]
    prereqs_of = {}
    for r in rows:
        prereqs_of.setdefault(r["topicId"], []).append(r["prerequisiteId"])
    transitive, stack = set(), list(hard) + list(soft)
    while stack:                                    # fermeture transitive des prérequis du target
        node = stack.pop()
        if node in transitive:
            continue
        transitive.add(node)
        stack.extend(prereqs_of.get(node, []))
    ids = set()
    for r in rows:
        ids.add(r["topicId"])
        ids.add(r["prerequisiteId"])
    non_edges = sorted(ids - transitive - {target_id})
    return {"target": target_id, "hard": hard, "soft": soft, "non_edges": non_edges}


def fixture_subgraph(target_id="B_matter_movement"):
    """Le sous-graphe de la fixture SP-3 — SOURCE UNIQUE, importée par les tests et le CLI."""
    return subgraph_for(load_dependencies(_FIXTURE_DEPS), target_id)
