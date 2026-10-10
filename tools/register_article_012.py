"""
tools/register_article_012.py — Enregistre l'Article 012 dans KuzuDB.
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

    art_id = "art_012_langage_ultime_tom_deliberation"
    title = "Article 012: Langage Ultime Phase 3 — Recursion Grammaticale, Theorie de l'Esprit Latente et Consensus Deliberatif Distribue"
    content = (
        "docs/012_Langage_Ultime_Recursion_ToM_Deliberation.md - "
        "Extension VSA/HRR a recursion hierarchique avec cle de clause unitaire a spectre plat sur S^{D-1}. "
        "Rappel cyclique a profondeur 2 (Proposition dans Proposition) avec similarite cosinus >= 0.40. "
        "Theorie de l'Esprit Latente (ToM) : modele d'inference bayesienne de la croyance du pair et silence pragmatique (RSA continue) reduisant l'entropie et le cout metabolique. "
        "Protocole deliberatif distribue multi-tours au coin du feu de camp (barycentre geodesique sur la variete spherique de Frechet). "
        "Enregistrement des consensus collectifs dans la table LUDeliberation de KuzuDB et decompilation symbolique ascendante."
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
