"""
tools/register_article_028.py — Enregistre l'Article 028 dans KuzuDB.
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

    art_id = "art_028_langage_ultime_civilisation_autonome_inworld"
    title = "Article 028: Langage Ultime Phase 19 — La Civilisation Autonome Multi-Mondes & Déploiement In-World Hybride (Arc 13: Civilisation Autonome Multi-Mondes)"
    content = (
        "docs/028_Langage_Ultime_Civilisation_Autonome_MultiMondes.md - "
        "Franchissement des jalons M28-M31 (Arc 13: Civilisation Autonome Multi-Mondes & Déploiement In-World Hybride). "
        "Déploiement de l'orchestrateur synchrone CivilizationWorldConductor reliant les 3 biosphères physiques "
        "(Monde 1: Stoneage, Monde 2: Agricole & Greniers, Monde 3: Industriel & Métallurgie). "
        "Intégration d'agents incarnés pilotés par fondation (EmbodiedFoundationAgent), perception spatiale continue (MultimodalLatentEncoder), "
        "consensus robuste d'essaim Weiszfeld BFT (LLMSwarmConsensus), planification par MCTS latent continu sans tokens (LatentMCTSSearch) "
        "et auto-correction réflexive (SelfReflectiveLatentCritic). "
        "Passerelles inter-mondes actives assurant le secours calorique sous gel hivernal et le transfert d'outils métalliques durables. "
        "Validation empirique formelle via le banc comparatif officiel tools/civilization_multiworld_benchmark.py "
        "(survie finale +66.7%, différentiel d'énergie vitale +24.3 E, 24 transferts de secours, exécution à 24.3 ms/pas)."
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
