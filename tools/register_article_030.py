"""
tools/register_article_030.py — Enregistre l'Article 030 dans KuzuDB.
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

    art_id = "art_030_langage_ultime_conscience_theorie_esprit"
    title = "Article 030: Langage Ultime Phase 21 — Conscience Synthétique, Méta-Miroir & Théorie de l'Esprit Latente (Arc 15: M36-M39)"
    content = (
        "docs/030_Langage_Ultime_Conscience_Synthetique_Theorie_Esprit.md - "
        "Franchissement des jalons M36-M39 (Arc 15: Conscience Synthétique, Méta-Miroir & Théorie de l'Esprit Latente). "
        "Intégration du moteur de Théorie de l'Esprit Latente (LatentTheoryOfMindEngine) permettant la modélisation récursive "
        "de second ordre des intentions d'autrui sur S^(D-1) avec mise à jour riemannienne géodésique et détection prédictive de défection byzantine. "
        "Déploiement du module de ramification contrefactuelle sans risque (CounterfactualLatentBranching) simulant des trajectoires 'What-If' "
        "pour arbitrer entre utilité collective et friction sociale avant tout engagement physique. "
        "Intégration native dans CivilizationWorldConductor et validation sur le banc officiel tools/civilization_tom_benchmark.py : "
        "survie finale +12.5%, énergie moyenne 42.93 E (+0.48 E), 27 transferts de solidarité inter-mondes, carte mentale ToM 1.0000 sur S^(D-1) "
        "et cadence d'exécution vectorisée de 37.71 pas/seconde. Clôture intégrale de l'Arc 15."
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
