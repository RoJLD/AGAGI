"""
tools/register_article_031.py — Enregistre l'Article 031 dans KuzuDB.
Conforme au Commandement 16 (Journalisation Scientifique).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import datetime
from src.graph_rag.database import KuzuDatabase, DatabaseConfig


def main():
    db_path = str(Path(__file__).resolve().parents[1] / "data" / "kuzudb" / "kuzu.db")
    db = KuzuDatabase(DatabaseConfig(db_path=db_path))

    art_id = "art_031_franchissement_mur_edr_lock_001_g2_fort"
    title = "Article 031: Percée Historique — Franchissement du Mur EDR-LOCK-001 et Validation de G2-Fort (Émergence Non Supervisée)"
    content = (
        "docs/EDR/LOCK-004_G2_Strong_Emergence_Under_Composition_Demand_The_Wall_Is_Breached.md - "
        "Franchissement officiel du Niveau 2 de la porte SDR-G2 (G2-Fort / Émergence in-loop non supervisée). "
        "Résolution de l'artefact d'optimisation E19 dans tools/compositional_world_probe.py : le bras nu (sans gate) "
        "était structurellement bridé par un TD(0) 1-pas à lr=0.05 coupant le crédit entre S1 (CRAFT) et S2 (USE). "
        "L'alignement sur un crédit épisodique agnostique à pas bas (lr=0.005) libère l'émergence spontanée de la composition "
        "dans les poids synaptiques récurrents sous demande environnementale (d=1.0 vs d=0.0). "
        "Preuve à puissance sur le banc officiel tools/g2_strong_emergence_benchmark.py : 12/12 graines appariées gagnées, "
        "p-value binomiale p=0.000244, médiane comp_rate 0.0150 -> 0.1606, ratio d'émergence x10.73. "
        "Le mur historique EDR-LOCK-001 est intégralement vaincu sur ses trois piliers (écriture, coordination, composition). "
        "La porte SDR-G2 passe au statut 'validated'."
    )
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    title_safe = title.replace("'", "\\'")
    content_safe = content.replace("'", "\\'")

    info = db.execute_cypher("CALL table_info('Article') RETURN *")
    cols = [row[1] for row in info]

    props = []
    if "id" in cols: props.append(f"id: '{art_id}'")
    if "title" in cols: props.append(f"title: '{title_safe}'")
    if "content" in cols: props.append(f"content: '{content_safe}'")
    if "date" in cols: props.append(f"date: '{today}'")

    props_str = ", ".join(props)
    try:
        check = db.execute_cypher(f"MATCH (a:Article) WHERE a.id = '{art_id}' RETURN a.id")
        if check:
            db.execute_cypher(f"MATCH (a:Article) WHERE a.id = '{art_id}' SET a.title = '{title_safe}', a.content = '{content_safe}', a.date = '{today}'")
            print(f"✅ Article '{art_id}' mis a jour avec succes dans KuzuDB.")
        else:
            db.execute_cypher(f"CREATE (a:Article {{{props_str}}})")
            print(f"✅ Article '{art_id}' enregistre avec succes dans KuzuDB.")
    except Exception as e:
        print(f"⚠️ Insertion Article: {e}")


if __name__ == "__main__":
    main()
