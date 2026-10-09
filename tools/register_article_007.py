"""
tools/register_article_007.py — Enregistre l'Article 007 dans KuzuDB.
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

    art_id = "art_007_emergence_culture_arc5"
    title = "Article 007: Emergence Endogene des Roles, Maitrise du Feu et Transmission Culturelle en Espace Latent (Arcs 5 et 6)"
    content = (
        "docs/0_La_Tribu_Emergence_Culture_Arc5.md - "
        "Inference a posteriori des roles tribaux sans scaffolding rigide (infer_emergent_roles), "
        "thermodynamique sociale du foyer (reduction du bruit acoustique de 80% au coin du feu, vitalite restauree), "
        "transmission culturelle spontanee de recettes artisanales sur S^(D-1), "
        "et divergence dialectale mesuree par distance de Grassmann. Arcs 5 et 6 resolus."
    )
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    title_safe = title.replace("'", "\\'")
    content_safe = content.replace("'", "\\'")

    info = db.execute_cypher("CALL table_info('Article') RETURN *")
    cols = [row[1] for row in info]
    print(f"Table Article colonnes: {cols}")

    props = []
    if "id" in cols: props.append(f"id: '{art_id}'")
    if "title" in cols: props.append(f"title: '{title_safe}'")
    if "content" in cols: props.append(f"content: '{content_safe}'")
    if "date" in cols: props.append(f"date: '{today}'")

    props_str = ", ".join(props)
    try:
        # Check if already exists
        check = db.execute_cypher(f"MATCH (a:Article) WHERE a.id = '{art_id}' RETURN a.id")
        if check:
            db.execute_cypher(f"MATCH (a:Article) WHERE a.id = '{art_id}' SET a.title = '{title_safe}', a.content = '{content_safe}', a.date = '{today}'")
            print(f"✅ Article '{art_id}' mis à jour avec succès dans KuzuDB.")
        else:
            db.execute_cypher(f"CREATE (a:Article {{{props_str}}})")
            print(f"✅ Article '{art_id}' enregistré avec succès dans KuzuDB.")
    except Exception as e:
        print(f"⚠️ Insertion Article: {e}")


if __name__ == "__main__":
    main()
