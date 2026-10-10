"""
tools/register_article_017.py — Enregistre l'Article 017 dans KuzuDB.
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

    art_id = "art_017_langage_ultime_neural_vm_causalite_bft"
    title = "Article 017: Langage Ultime Phase 8 — Machine Virtuelle Latente Auto-Exécutable, Causalité Formelle Do-Calculus et Consensus Byzantin Sphérique"
    content = (
        "docs/017_Langage_Ultime_Neural_VM_Causalite_BFT.md - "
        "Franchissement du seuil G8 (L'Exécution Latente Programmable, la Démarche Scientifique Causale et la Résilience Byzantine). "
        "Formulation de la Machine Virtuelle Latente continue LatentNeuralVM opérant sur S^(D-1) préservant strictement ||F(S)||=1 "
        "avec rôles unitaires d'état, de transition, de trigger et d'escrow calorique décentralisé. "
        "Formalisation du Do-Calculus vectoriel via l'opérateur d'intervention unitaire do(X) = R_do * X orthogonal aux corrélations passives, "
        "et mesure d'Effet Moyen de Traitement latent ATE = ||E[Y|do(X)] - E[Y|do(~X)]|| réfutant expérimentalement les fausses théories. "
        "Consensus Byzantin Sphérique de Weiszfeld robuste sur S^(D-1) garantissant l'immunité contre le poisoning latent jusqu'à f < n/3 déviations. "
        "Smart contracts d'escrow in-world intégrés au FederalMonument avec auto-exécution dynamique et primes caloriques sans tiers de confiance. "
        "Traçabilité immuable dans KuzuDB via LUNeuralVM, LUCausalInference et LUBFTConsensus. "
        "Validation sociologique PIU sur 60 ères confirmant le gain d'énergie, de survie et la neutralisation totale des attaques adversariales."
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
