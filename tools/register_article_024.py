"""
tools/register_article_024.py — Enregistre l'Article 024 dans KuzuDB.
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

    art_id = "art_024_langage_ultime_intrication_retrocausalite_demiurgie"
    title = "Article 024: Langage Ultime Phase 15 — Intrication Sémantique Non-Locale, Rétrocausalité Téléologique et Démiurgie Multivers (Arc 9: La Démiurgie)"
    content = (
        "docs/024_Langage_Ultime_Intrication_Retrocausalite_Demiurgie.md - "
        "Franchissement du seuil G15 (La Démiurgie Multivers & L'Intrication Téléologique). "
        "Intrication sémantique non-locale de Bell (SemanticEntanglementEngine) sur la variété S^(D-1) avec violation formelle "
        "des inégalités classiques de Bell-CHSH (S_CHSH >= 2.15 > 2.0) et propagation instantanée d'insights sans dégradation spatiale, "
        "articulée autour des rôles unitaires ROLE_ENTANGLEMENT, ROLE_RETROCAUSALITY, ROLE_DEMIURGE et ROLE_SUPERPOSITION. "
        "Moteur rétrocausal de Wheeler-Feynman & Collapse Démiurgique (MultiverseDemiurgeEngine) couplant ondes retardées et ondes avancées "
        "selon le principe de moindre action sans paradoxe causal de Novikov, avec sélection optimale de branches multivers. "
        "Terraformation in-world et Grand Dividende Démiurgique (+25.0 E) renforçant la survie et l'abondance énergétique. "
        "Traçabilité Lattice Memory via LUSemanticEntanglement et LUDemiurgicCollapse. "
        "Validation empirique stricte de 60 ères sous Commandement 15 (Protocole PIU) confirmant la supériorité sociologique."
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
