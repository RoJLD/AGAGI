"""
tools/register_article_032.py — Enregistre l'Article 032 dans KuzuDB.
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

    art_id = "art_032_langage_ultime_coevolution_mondes_autoteliques"
    title = "Article 032: Langage Ultime Phase 23 — L'Expansion des Mondes & La Co-Évolution Autotélique des Environnements et des Modèles (Arc 17: M44-M47)"
    content = (
        "docs/032_Langage_Ultime_Coevolution_Mondes_Autoteliques.md - "
        "Franchissement des jalons M44-M47 (Arc 17: L'Expansion des Mondes & La Co-Évolution Autotélique). "
        "Déploiement du Monde 5 : Marché Économique Décentralisé (world_5_economic_market.py) avec monnaie d'échange Coin, contrats d'achat/vente et fixation dynamique des prix par élasticité offre/demande. "
        "Déploiement du Monde 6 : Écosystème Co-Évolutif Proies/Prédateurs Adaptatifs (world_6_coevolution_biosphere.py) avec dynamique de fuite réactive Boids, toxicité sélective et course aux armements Red Queen. "
        "Déploiement du Monde 7 : Raisonnement Symbolique, Algèbre & Preuves Formelles (world_7_symbolic_reasoning.py) avec Modus Ponens et résolution d'équations formelles. "
        "Orchestration par le Conducteur de Curriculum Autotélique (autotelic_curriculum_conductor.py) : élévation procédurale de la difficulté des mondes dès que les modèles atteignent le top de compétence (mastery >= 0.80). Clôture de l'Arc 17."
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
