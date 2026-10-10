"""
tools/register_article_011.py — Enregistre l'Article 011 dans KuzuDB.
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

    art_id = "art_011_langage_ultime_compositionnel"
    title = "Article 011: Langage Ultime Phase 2 — Compositionnalite Semantique HRR, Relais Multi-Hop Acoustique et Decompilation Hybride KuzuDB"
    content = (
        "docs/011_Langage_Ultime_Compositionnel_MultiHop.md - "
        "Emergence compositionnelle VSA (Holographic Reduced Representations) avec convolution circulaire unitaire a spectre plat sur S^{D-1}. "
        "Synthese et decompilation de triplets semantiques (Sujet, Predicat, Cible, Urgence). "
        "Protocole de relais acoustique multi-hop in-world et consensus spatial au-dela de la portee visuelle directe. "
        "Pont symbolique-neuronal bidirectionnel LangGraph / KuzuDB pour lexemes emergents et injection d'ordres top-down."
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
