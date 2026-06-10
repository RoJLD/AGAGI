"""
tools/build_project_graph.py — Peuple le GRAPHE-PROJET dans KuzuDB (EDR 034, Vague 1).

Rend la carte des dimensions (roadmap) et l'historique des EDR **requêtables** : nœuds
`Dimension` (les 10 axes des 4 familles) + `EDR` (les décisions) + relations `TOUCHES`.
Pendant du graphe mermaid (humain) : ici le graphe machine. Complète l'ontologie EDR 032.

Usage : HEADLESS=1 python -m tools.build_project_graph
"""
import time

from src.graph_rag.async_logger import logger as async_logger
from src.graph_rag.experiment_tracker import ExperimentGraph

# Les 10 axes (4 familles) — cf. roadmap §"Dimensions d'Expérimentation".
DIMENSIONS = [
    ("A1", "Ontogenese (intra-vie)",        "A. Temps",            "repaired"),
    ("A2", "Phylogenese (inter-ere)",       "A. Temps",            "repaired"),
    ("B3", "Monde (richesse cognitive)",    "B. Developpemental",  "active"),
    ("B4", "Craft (mecanique)",             "B. Developpemental",  "active"),
    ("B5", "Difficulte (ecologique)",       "B. Developpemental",  "active"),
    ("C6", "Les 7 Arcs (versions)",         "C. Meta-evolution",   "frozen"),
    ("C7", "Architecture agent (NAS)",      "C. Meta-evolution",   "frozen"),
    ("D8", "Recompenses intrinseques",      "D. Mecanismes",       "active"),
    ("D9", "Scaffolds anneales",            "D. Mecanismes",       "active"),
    ("D10", "Genes du connectome",          "D. Mecanismes",       "active"),
]

# EDR -> (titre court, axes touchés)
EDRS = {
    "010": ("Audit cognitif du repo",            ["A2", "D8", "D9"]),
    "011": ("World Model (RND) + surprise",      ["D8", "A1"]),
    "012": ("Monde exigeant",                    ["B5"]),
    "013": ("Scaffold approche/collecte",        ["D9"]),
    "014": ("Curiosite + nouveaute",             ["D8"]),
    "015": ("World Model par agent",             ["D8"]),
    "016": ("Moteur evolutif (HoF sauve)",       ["A2"]),
    "017": ("Craft inemergeable",                ["B4"]),
    "018": ("Axe Craft / auto-craft L0",         ["B4"]),
    "019": ("e-greedy exploration de l'action",  ["D9"]),
    "020": ("Actor-Critic (credit d'action)",    ["A1"]),
    "021": ("Boucle d'emergence (materiaux)",    ["B4", "B5"]),
    "022": ("Coup critique annele",              ["D9"]),
    "023": ("Actor-Critic TD (credit temporel)", ["A1"]),
    "024": ("Progres population (anti-inertes)", ["A2"]),
    "025": ("Curriculum axe Craft",              ["B4"]),
    "026": ("Curriculum axe Monde (rarete)",     ["B5"]),
    "027": ("Integration 2D Monde x Craft",      ["B4", "B5"]),
    "028": ("Persistance / cooperation",         ["D9"]),
    "029": ("Chaine dominante (selection apex)", ["A2", "D9"]),
    "030": ("Sevrage + curriculum unifie",       ["D9"]),
    "031": ("Cabler les genes fantomes",         ["D10"]),
    "032": ("Ablation + ontologie",              ["D8", "D9", "D10"]),
    "033": ("Unifier le moteur des mondes",      ["B3"]),
    "034": ("Graphe-projet KuzuDB",              ["C6"]),
}


def main():
    async_logger.start()
    db = None
    for _ in range(50):
        db = async_logger.get_db()
        if db:
            break
        time.sleep(0.1)
    if db is None:
        print("KuzuDB indisponible.")
        return
    eg = ExperimentGraph(db=db)
    eg.ensure_project_schema()

    for did, name, family, status in DIMENSIONS:
        eg.log_dimension(did, name, family, status)
    for eid, (title, dims) in EDRS.items():
        eg.log_edr(f"EDR{eid}", title)
        for did in dims:
            eg.link_edr_dimension(f"EDR{eid}", did)
    print(f"Graphe-projet peuple : {len(DIMENSIONS)} dimensions, {len(EDRS)} EDR.")

    # --- Requêtes de preuve : le graphe est VIVANT ---
    print("\n=== EDR par axe (les plus travailles) ===")
    r = eg.conn.execute(
        "MATCH (e:EDR)-[:TOUCHES]->(d:Dimension) "
        "RETURN d.id, d.name, count(e) AS n ORDER BY n DESC LIMIT 6")
    while r.has_next():
        did, name, n = r.get_next()
        print(f"  {did:3s} {name:32s} : {n} EDR")

    print("\n=== Couverture par FAMILLE ===")
    r = eg.conn.execute(
        "MATCH (e:EDR)-[:TOUCHES]->(d:Dimension) "
        "RETURN d.family, count(DISTINCT e) AS n ORDER BY n DESC")
    while r.has_next():
        family, n = r.get_next()
        print(f"  {family:22s} : {n} EDR")

    print("\n=== Axes JAMAIS touches par un EDR (la frontiere) ===")
    r = eg.conn.execute("MATCH (e:EDR)-[:TOUCHES]->(d:Dimension) RETURN DISTINCT d.id")
    touched = set()
    while r.has_next():
        touched.add(r.get_next()[0])
    untouched = [(did, name, status) for did, name, fam, status in DIMENSIONS if did not in touched]
    if untouched:
        for did, name, status in untouched:
            print(f"  {did:3s} {name:32s} [{status}]")
    else:
        print("  (aucun — tous les axes ont au moins un EDR)")

    async_logger.stop()


if __name__ == "__main__":
    main()
