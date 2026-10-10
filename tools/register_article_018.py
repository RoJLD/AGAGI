"""
tools/register_article_018.py — Enregistre l'Article 018 dans KuzuDB.
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

    art_id = "art_018_langage_ultime_synthese_programmes_ltl_analogies"
    title = "Article 018: Langage Ultime Phase 9 — Synthèse Autonome de Programmes Latents Turing-Complets, Transport Optimal d'Analogies Inter-Mondes et Logique Temporelle Diachronique"
    content = (
        "docs/018_Langage_Ultime_Synthese_Programmes_LTL_Analogies.md - "
        "Franchissement du seuil G9 (La Synthèse de Programmes Neuromorphiques, l'Analogie Catégorielle et la Continuité Diachronique). "
        "Formulation de l'algèbre de programmes vectoriels Turing-complets LatentProgramSynthesizer opérant sur S^(D-1) avec composition "
        "récursive unitaire (BRANCH, LOOP, TERMINATE) et preuve formelle de terminaison par théorème du point fixe de Banach (Lipschitz constant L < 1.0). "
        "Formalisation de la Logique Temporelle Diachronique continue (Vectorial LTL) : opérateurs unitaires R_next, R_eventually, R_always "
        "préservant la platitude spectrale |F(R)| = 1 et permettant aux contrats d'exprimer des garanties d'exécution différées ou promesses énergétiques. "
        "Opérateur d'analogie de structure multivers solve_latent_analogy combinant déconvolution spectrale unitaire et translation géodésique "
        "parallélogrammique (A : B :: C : D, fidélité >= 0.85) assurant le transfert de savoirs technologiques entre les trois mondes (Acier : Charbon :: Moisson : Compost). "
        "Infrastructures in-world au FederalMonument avec escrows temporels et exécution autonome de programmes d'efficience calorique. "
        "Persistance et traçabilité immuable dans KuzuDB via LUSynthesizedProgram, LUTemporalClause et LUAnalogyTransfer. "
        "Validation sociologique PIU sur 60 ères confirmant l'accélération d'apprentissage inter-mondes, la survie et le gain thermodynamique net."
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
