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


# --- EXPORT vers os-taxonomy (SP-1 residuel, 2026-09-09) -------------------------------------------
#
# L'adaptateur ne savait que LIRE le format. SP-4 (« forker et contribuer en retour ») etait donc
# bloque en amont : rien ne pouvait produire un graphe publiable. Ces deux fonctions ferment le trou.
#
# ⚠️ CE QUE L'EXPORT PERD, et il faut le dire plutot que de le laisser deviner. os-taxonomy porte
# quatre champs par arete (topicId, prerequisiteId, strength, reason) ; l'AGI-Taxonomy en porte
# QUATORZE, dont tout le bloc `evidence` -- verdict d'ablation, ratio, n, controle de specificite,
# plafond de l'incapable et sa provenance. L'export est donc une PROJECTION LOSSY, et c'est le sens
# meme du fork : notre critere d'evidence est plus strict que celui du format cible. On ecrit la
# provenance dans `reason` pour qu'un lecteur du graphe exporte sache d'ou vient l'arete.

_AGI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "agi_taxonomy")


def to_os_topics(capabilities):
    """`capabilities.json` -> lignes `topics.json` d'os-taxonomy : {id, title}."""
    return [{"id": c["id"], "title": c["title"]} for c in capabilities]


def to_os_dependencies(demands, with_provenance=True):
    """`demands.json` -> lignes `dependencies.json` d'os-taxonomy.

    `capability`/`prerequisite` deviennent `topicId`/`prerequisiteId` ; `strength` et `reason`
    passent tels quels. Avec `with_provenance`, la ligne `reason` est suffixee par le record et le
    ratio : sans cela, une arete exportee perdrait toute trace de ce qui l'etablit, et le fork ne
    contribuerait pas ce qu'il a de plus strict."""
    lignes = []
    for e in demands:
        raison = e.get("reason", "")
        if with_provenance:
            ev = e.get("evidence", {})
            raison = (f"{raison} [AGI-Taxonomy : ablation within-subject, ratio {ev.get('ratio')}, "
                      f"n={ev.get('n')}, {ev.get('record')}]").strip()
        lignes.append({"topicId": e["capability"], "prerequisiteId": e["prerequisite"],
                       "strength": e["strength"], "reason": raison})
    return lignes


def export_os_taxonomy(dest_dir=None, agi_dir=None):
    """Ecrit `topics.json` + `dependencies.json` au format os-taxonomy. Renvoie les deux chemins.

    GARDE EN TETE : un graphe VIDE n'est pas un export, c'est une perte. On refuse plutot que
    d'ecrire deux fichiers vides que l'aval lirait comme « la taxonomie ne contient rien »."""
    agi = agi_dir or _AGI_DIR
    with open(os.path.join(agi, "capabilities.json"), encoding="utf-8") as fh:
        caps = json.load(fh)
    with open(os.path.join(agi, "demands.json"), encoding="utf-8") as fh:
        dem = json.load(fh)
    if not caps or not dem:
        raise ValueError(
            f"export_os_taxonomy : graphe VIDE ({len(caps)} capacites, {len(dem)} aretes) -- "
            "ce n'est pas un export, c'est une perte ; ne pas confondre avec une taxonomie sans arete.")
    dest = dest_dir or os.path.join(agi, "export")
    os.makedirs(dest, exist_ok=True)
    p_t = os.path.join(dest, "topics.json")
    p_d = os.path.join(dest, "dependencies.json")
    with open(p_t, "w", encoding="utf-8") as fh:
        json.dump(to_os_topics(caps), fh, ensure_ascii=False, indent=2)
    with open(p_d, "w", encoding="utf-8") as fh:
        json.dump(to_os_dependencies(dem), fh, ensure_ascii=False, indent=2)
    return p_t, p_d
