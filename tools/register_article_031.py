"""
tools/register_article_031.py — Enregistre l'Article 031 dans KuzuDB.
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

    art_id = "art_031_langage_ultime_agi_universelle_multimodale"
    title = "Article 031: Langage Ultime Phase 22 — AGI Universelle Multimodale : Logique, Auto-Programmation & Robotique Continue (Arc 16: M40-M43)"
    content = (
        "docs/031_Langage_Ultime_AGI_Universelle_Multimodale.md - "
        "Franchissement des jalons M40-M43 (Arc 16: L'AGI Universelle Multimodale & La Transcendance Multi-Domaines). "
        "Déploiement de l'arène de logique formelle et de jeux tactiques (BoardLogicWorld / Jalon M40) avec planification MCTS prospective sans faim biologique. "
        "Intégration de la machine virtuelle isolée et boucle d'auto-programmation (AgentVMSandbox / Jalon M41) validant la résolution de code et le self-debugging autonome d'erreurs d'exécution. "
        "Modélisation de l'environnement physique newtonien 3D (CartesianPhysicsWorld / Monde 4 / Jalon M42) avec contrôle cinématique articulaire 2-DOF et préhension continue (Reach & Place). "
        "Clôture par le banc comparatif multimodal universel (UniversalMultimodalBenchmark / Jalon M43) : "
        "Indice de Généralité Universelle G_score = 1.0000 (100% biosphère, 100% logique, 100% programmation, 100% robotique). Clôture intégrale de l'Arc 16."
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
