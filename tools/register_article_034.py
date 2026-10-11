"""
tools/register_article_034.py — Enregistre l'Article 034 dans KuzuDB.
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

    art_id = "art_034_langage_ultime_passerelle_unity_moteur_jeu_realiste"
    title = "Article 034: Langage Ultime Phase 25 — La Passerelle Unity 3D & L'Intégration du Moteur de Jeu Réaliste (Arc 19: Jalon M52)"
    content = (
        "docs/034_Langage_Ultime_Passerelle_Unity_Moteur_Jeu_Realiste.md - "
        "Franchissement du Jalon M52 (Arc 19: L'Ère des Mondes Réalistes & Moteurs 3D). "
        "Déploiement de UnityBridgeWorld (src/worlds/unity_bridge_world.py) : passerelle bidirectionnelle TCP "
        "reliant les agents Liquid Mamba ODE aux moteurs 3D PhysX. Supporte l'envoi d'actions neuromotrices 3D (25D), "
        "la réception d'observations sensorielles 3D incluant 16 faisceaux LiDAR raycastés (45D). "
        "Fourniture du script C# Unity AGIseedAgentBridge.cs (src/worlds/unity/AGIseedAgentBridge.cs) pour intégration "
        "immédiate sur les avatars 3D. Validation par le banc tools/unity_bridge_benchmark.py démontrant un débit "
        "record de 62 119 pas/seconde en mode simulation locale certifiée CI/CD."
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
