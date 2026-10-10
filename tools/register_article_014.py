"""
tools/register_article_014.py — Enregistre l'Article 014 dans KuzuDB.
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

    art_id = "art_014_langage_ultime_gouvernance_metallurgie"
    title = "Article 014: Langage Ultime Phase 5 — Gouvernance Juridique Décentralisée, Arbitrage de Confiance Latente et Métallurgie Distribuée du Monde 3"
    content = (
        "docs/014_Langage_Ultime_Gouvernance_Metallurgie.md - "
        "Algebre de confiance continue et detection de deviation contractuelle (Delta_breach). "
        "Hysteresis de reputation vectorielle resistant a l amnesie sur 10 cycles sans amnistie automatique. "
        "Arbitrage decentralise in-world : embargo commercial acoustique et repulsion physique hors de la place du marche. "
        "Algebre de consortiums tripartites (Bois Monde 1 + Vivres Monde 2 + Minerai Monde 3) debloquant le Haut-Fourneau et la forge d outils metalliques. "
        "Validation empirique sociologique de 60 eres : neutralisation de la predation, surplus energetique et survie garantie. "
        "Consigne immuable dans KuzuDB sous les tables LULaw, LUSanction et LUConsortium."
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
