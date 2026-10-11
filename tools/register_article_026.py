"""
tools/register_article_026.py — Enregistre l'Article 026 dans KuzuDB.
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

    art_id = "art_026_langage_ultime_swarm_foundation_embodied"
    title = "Article 026: Langage Ultime Phase 17 — Swarm Foundation Bridge & Contrôle Incarné In-World: Consensus BFT de Weiszfeld, Embodiment Continu et Rêve Téléologique (Arc 11: Swarm Foundation & Embodied LLMs)"
    content = (
        "docs/026_Langage_Ultime_Swarm_Foundation_Embodied.md - "
        "Franchissement du seuil M20-M23 (Arc 11: Swarm Foundation & Embodied LLMs). "
        "Déploiement d'un essaim distribué de modèles de fondation délibérant sur la variété hypersphérique S^(D-1). "
        "Résolution du consensus continu par Médiane Sphérique de Weiszfeld BFT sous métrique géodésique arccos et Barycentre de Sinkhorn-Wasserstein, "
        "avec filtrage à 100% des agents byzantins déviants et gain d'alignement (+0.1534 vs moyenne naïve). "
        "Incarnation physique sans texte (EmbodiedFoundationAgent) : couplage direct du Gigatoken téléologique aux 108 sorties motrices des mondes physiques 3D "
        "via projection semi-orthogonale et fusion convexe stable avec les ODEs réflexes Liquid Mamba. "
        "Consolidation épisodique nocturne et replay hippocampique continu (NightConsolidator) produisant un gain téléologique (+0.8317) "
        "et une réduction d'erreur prédictive (-0.4159) à coût calorique nul. "
        "Preuve formelle de la capacité des essaims de fondation à délibérer sans tokens et à agir directement dans un monde physique."
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
