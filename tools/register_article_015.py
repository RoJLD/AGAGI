"""
tools/register_article_015.py — Enregistre l'Article 015 dans KuzuDB.
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

    art_id = "art_015_langage_ultime_ecriture_mathematiques_science"
    title = "Article 015: Langage Ultime Phase 6 — Émergence de l'Écriture Stigmargique, Arithmétique Vectorielle Discrète et Transmission Scientifique Intergénérationnelle"
    content = (
        "docs/015_Langage_Ultime_Ecriture_Mathematiques_Science.md - "
        "Franchissement du seuil G6 (La Bibliotheque d Alexandrie et la Memoire Stigmargique Externe). "
        "Algebre d arithmetique vectorielle FPE (Phasor Binding) assurant l homomorphisme d addition spectrale Z(a) * Z(b) = Z(a+b). "
        "Substrats physiques in-world : InscriptionStone (steles fixes a demi-vie geologique) et SlateTablet (ardoises portables de grand livre de marche). "
        "Academie scientifique in-world et transmission epigenetique : les nouveau-nes lisent les steles, recoivent un prior boost et un bonus calorique (+5.0 pts). "
        "Banc sociologique de 60 eres validant le maintien de la production metallurgique malgre le renouvellement demographique. "
        "Consigne immuable dans KuzuDB sous les tables LUScripture, LUMathematics et LUScience."
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
