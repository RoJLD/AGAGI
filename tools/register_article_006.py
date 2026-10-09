"""
tools/register_article_006.py — Enregistre l'Article 006 dans KuzuDB.
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

    art_id = "art_lu_resolution_arc4"
    title = "Resolution Arc 4: Emergence causale et perennite HGT du langage latent continu (LU)"
    content = "docs/0_Langage_Ultime_Resolution_Arc4.md - CKA 0.8842, survie 138 ticks, gain +245%, Arc 4 resolu et cloture."
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    info = db.execute_cypher("CALL table_info('Article') RETURN *")
    cols = [row[1] for row in info]
    print(f"Table Article colonnes: {cols}")

    props = []
    if "id" in cols: props.append(f"id: '{art_id}'")
    if "title" in cols: props.append(f"title: '{title}'")
    if "content" in cols: props.append(f"content: '{content}'")
    if "date" in cols: props.append(f"date: '{today}'")

    props_str = ", ".join(props)
    try:
        db.execute_cypher(f"CREATE (a:Article {{{props_str}}})")
        print(f"✅ Article '{art_id}' enregistré avec succès dans KuzuDB.")
    except Exception as e:
        print(f"⚠️ Insertion Article: {e}")


if __name__ == "__main__":
    main()
