"""
tools/register_article_020.py — Enregistre l'Article 020 dans KuzuDB.
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

    art_id = "art_020_langage_ultime_meta_simulation_reve_contrefactuel"
    title = "Article 020: Langage Ultime Phase 11 — Méta-Simulation Contrefactuelle, Rêve Sémantique Partagé et Délibération dans le World Model Latent (Arc 6: Le Penseur)"
    content = (
        "docs/020_Langage_Ultime_Meta_Simulation_Reve_Contrefactuel.md - "
        "Franchissement du seuil G11 (L'Imagination Collective et la Méta-Simulation Intérieure). "
        "Formulation du protocole de transmission d'hypothèses de rêve en Gigatokens DREAM_HYPOTHESIS = DREAM ⊛ WHAT_IF ⊛ SCENARIO, "
        "permettant aux agents d'inviter leurs pairs à simuler collectivement une trajectoire contrefactuelle sans coût moteur. "
        "Développement du moteur de rollout contrefactuel vectorisé LatentDreamEngine déroulant 10 pas de dynamique intérieure dans l'espace "
        "latent sous contraction lipschitzienne stricte en un seul tick physique, et calculant le Gain Espéré Contrefactuel (CEG). "
        "Institution du Conseil Délibératif du Feu de Camp (Campfire Council of Dreams) : consensus sphérique de Weiszfeld sur les simulations de rêve, "
        "rejet systématique des scénarios conduisant à une famine ou mort simulée, et ratification des stratégies anticipatrices avec dividende "
        "prédictif (+6.0 E). "
        "Persistance et traçabilité intégrale dans KuzuDB via LUSharedDream et LUCounterfactualRollout. "
        "Validation empirique 60 ères sous Commandement 15 démontrant que la méta-simulation contrefactuelle anticipe les famines hivernales, "
        "augmente la rétention calorique et surpasse la Phase 10 en score sociologique composite."
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
