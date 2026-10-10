"""
tools/register_article_013.py — Enregistre l'Article 013 dans KuzuDB.
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

    art_id = "art_013_langage_ultime_speciation_contrats"
    title = "Article 013: Langage Ultime Phase 4 — Speciation Dialectale, Contrats Latents de Troc et Negociation Commerciale Inter-Mondes"
    content = (
        "docs/013_Langage_Ultime_Speciation_Contrats.md - "
        "Geometrie des varietes de Grassmann Gr(k, D) pour quantifier la derive dialectale inter-clans par distance geodesique canonique. "
        "Algebre de contrats latents d'engagement bilateral (ROLE_GIVE, ROLE_DEMAND, ROLE_QUORUM) et condition de reciprocite d'equilibre de Nash vectoriel continue (score >= 0.60). "
        "Architecture de mediation MultiTribalTranslator reliant les sous-espaces de clans via un sous-espace pivot (Lingua Franca de marche). "
        "Validation sociologique in-world dans l'Age Agricole (Monde 2) : 24.3 contrats/ere, +2.80 ticks de survie, abolition des disettes autarciques. "
        "Enregistrement immuable des traites commerciaux et dialectes dans les tables LUContract et LUDialect de KuzuDB."
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
