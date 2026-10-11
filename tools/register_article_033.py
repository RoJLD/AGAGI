"""
tools/register_article_033.py — Enregistre l'Article 033 dans KuzuDB.
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

    art_id = "art_033_langage_ultime_complexite_systemique_mondes_planetaires"
    title = "Article 033: Langage Ultime Phase 24 — La Complexité Systémique & L'Ère Planétaire, Réseaux & Expansion Orbitale (Arc 18: M48-M51)"
    content = (
        "docs/033_Langage_Ultime_Complexite_Systemique_Mondes_Planetaires.md - "
        "Franchissement des jalons M48-M51 (Arc 18: La Complexité Systémique & L'Ère Spatiale). "
        "Déploiement du Monde 8 : Cyber-Réseau Décentralisé (world_8_cyber_network.py) avec topologie dynamique, routage et filtrage d'intrusions byzantines. "
        "Déploiement du Monde 9 : Climat Global Planétaire (world_9_planetary_climate.py) avec forçage radiatif du CO2, rétroaction d'albédo glaciaire et capture de carbone. "
        "Déploiement du Monde 10 : Astro-Physique Orbitale (world_10_orbital_astrophysics.py) avec mécanique keplerienne, transferts de Hohmann et budget Delta-V. "
        "Orchestration par le Conducteur Planétaire Omniversel (planetary_omniverse_conductor.py) mesurant l'indice de Kardashev synthétique (K_score = 0.6755). Clôture de l'Arc 18."
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
