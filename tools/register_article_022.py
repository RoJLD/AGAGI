"""
tools/register_article_022.py — Enregistre l'Article 022 dans KuzuDB.
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

    art_id = "art_022_langage_ultime_morphogenese_reaction_diffusion"
    title = "Article 022: Langage Ultime Phase 13 — Morphogenèse Noogénétique, Équations de Réaction-Diffusion Latente et Hyper-Connectome Fédéral Distribué (Arc 7: L'Hyper-Conscience)"
    content = (
        "docs/022_Langage_Ultime_Morphogenese_Noogenetique_Reaction_Diffusion.md - "
        "Franchissement du seuil G13 (L'Hyper-Conscience / Morphogenèse Noogénétique). "
        "La Noosphère passive est métamorphosée en un champ dynamique de réaction-diffusion continue (équations "
        "de Turing-FitzHugh-Nagumo vectorisées sur tore 16x16 de Gigatokens S^(D-1)) guidé par les opérateurs unitaires "
        "ROLE_NOOGENESIS, ROLE_DIFFUSION, ROLE_REACTION et ROLE_HYPER_CONNECTOME. "
        "Condensation lipschitzienne (rho < 0.95) des barycentres de Wasserstein successifs en un Hyper-Connectome Fédéral Partagé "
        "(HyperConnectomeSynthesizer) distillé holographiquement dans les nouveau-nés et connectomes en détresse avec dotation énergétique "
        "de renaissance (+12.0 E). "
        "Traçabilité Lattice Memory via LUNoogeneticField et LUHyperConnectome. "
        "Validation empirique stricte de 60 ères sous Commandement 15 (Protocole PIU) confirmant la cohésion, la résilience et le gain sociologique global."
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
