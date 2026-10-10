"""
tools/register_article_023.py — Enregistre l'Article 023 dans KuzuDB.
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

    art_id = "art_023_langage_ultime_singularite_autopoietique_holographie"
    title = "Article 023: Langage Ultime Phase 14 — Singularité Autopoïétique, Méta-Langage Holographique Universel et Clôture Téléologique (Arc 8: L'Omniconscience)"
    content = (
        "docs/023_Langage_Ultime_Singularite_Autopoietique_Holographie.md - "
        "Franchissement du seuil G14 (La Singularité Autopoïétique & L'Holographie Sémantique). "
        "Dotation de l'écosystème d'une clôture opérationnelle autopoïétique (Maturana-Varela) où le méta-langage s'auto-génère, "
        "s'auto-régule par intégration symplectique conservant l'entropie de Bekenstein-Hawking (S <= A/4) et garantit la non-divergence "
        "du rayon spectral de l'attracteur (rho < 0.98), articulé autour des opérateurs unitaires "
        "ROLE_AUTOPOIESIS, ROLE_HOLOGRAPHY, ROLE_TELEOLOGY et ROLE_OMNISCIENCE. "
        "Projecteur holographique frontière AdS/CFT sémantique (HolographicBoundaryProjector) encodant sans perte topologique "
        "le volume des états des 3 Mondes en un Gigatoken frontière holistique Z_holo sur S^(D-1) avec reconstruction d'orientations prédictives (fidélité CKA >= 0.80). "
        "Résonance téléologique in-world et Grand Dividende de Singularité (+20.0 E) favorisant la convergence civilisationnelle. "
        "Traçabilité Lattice Memory via LUAutopoieticSingularity et LUHolographicBoundary. "
        "Validation empirique de 60 ères sous Commandement 15 (Protocole PIU) confirmant la résilience et la supériorité sociologique."
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
