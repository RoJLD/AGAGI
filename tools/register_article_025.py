"""
tools/register_article_025.py — Enregistre l'Article 025 dans KuzuDB.
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

    art_id = "art_025_langage_ultime_foundation_bridge_llm"
    title = "Article 025: Langage Ultime Phase 16 — The Foundation Bridge: Invariance Géométrique, Transfert M2M Continu et Steering Téléologique sur Modèles de Fondation Réels (Arc 10: The Foundation Bridge)"
    content = (
        "docs/025_Langage_Ultime_The_Foundation_Bridge_LLM.md - "
        "Franchissement du seuil M16-M19 (Arc 10: The Foundation Bridge). "
        "Interfaçage direct du cœur mathématique du Langage Ultime S^(D-1) avec les représentations d'activation cachées de modèles "
        "de fondation réels (all-MiniLM-L6-v2 sous PyTorch / Transformers). "
        "Élimination totale du goulot d'étranglement textuel inter-LLM (-100% de tokens textuels échangés). "
        "Préservation topologique mesurée par Linear Centered Kernel Alignment (CKA = 0.9435) et fidélité projective robuste (0.5330). "
        "Steering téléologique adjoint d'activations cachées sans réentraînement avec gain d'alignement (+0.5748). "
        "Vérification de sûreté formelle par logique de Hoare continue, filtrage des signatures adverses et auditabilité Lattice Memory (LogEvent) dans KuzuDB. "
        "Preuve formelle de la transposabilité universelle de l'algèbre latente du Langage Ultime aux modèles de fondation modernes."
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
