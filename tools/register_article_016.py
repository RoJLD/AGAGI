"""
tools/register_article_016.py — Enregistre l'Article 016 dans KuzuDB.
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

    art_id = "art_016_langage_ultime_metalangage_diplomatie"
    title = "Article 016: Langage Ultime Phase 7 — Métalangage Auto-Évolutif, Preuve Formelle Latente et Fédération Diplomatique Inter-Connectomes"
    content = (
        "docs/016_Langage_Ultime_Metalangage_Diplomatie_Federale.md - "
        "Franchissement du seuil G7 (La Constitution Federale et l Auto-Evolution Metasemantique). "
        "Algebre de derivation de macro-roles unitaires d ordre superieur R_macro = R_A * R_B preservant un spectre de Fourier plat |F(R)| = 1. "
        "Logique de preuve formelle vectorielle et detection d antipodalite contradictoire (P et ~P, cosinus < -0.50) invalidant les lois auto-contradictoires. "
        "Pont diplomatique asymetrique FederalDiplomaticBridge unifiant les connectomes NAS heterogenes (D_A != D_B) avec CKA >= 0.85. "
        "Monument federal in-world (FederalMonument) et ratification de traites constitutionnels multilateraux avec prime calorique (+2.5 pts) et protection pacifique. "
        "Banc sociologique de 60 eres validant le gain d energie (+1.32 pts) et de survie (+0.10 ticks) sous renouvellement demographique. "
        "Consigne immuable dans KuzuDB sous LUMetaGrammar, LUProofCheck et LUFederalTreaty."
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
