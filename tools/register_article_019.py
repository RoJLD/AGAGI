"""
tools/register_article_019.py — Enregistre l'Article 019 dans KuzuDB.
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

    art_id = "art_019_langage_ultime_auto_compilation_connectomes_seed_ai"
    title = "Article 019: Langage Ultime Phase 10 — Auto-Compilation Récursive du Connectome, Logique de Hoare Continue et Singularité Seed AI"
    content = (
        "docs/019_Langage_Ultime_Auto_Compilation_Connectomes_Seed_AI.md - "
        "Franchissement du seuil ultime G10 (La Clôture Récursive de Von Neumann-Gödel et la Métaprogrammation Endogène des Connectomes). "
        "Formulation du compilateur bidirectionnel ConnectomeCompiler établissant l'isomorphisme spectral unitaire entre l'espace matriciel "
        "des poids du connectome Liquid Mamba (W) et la sphère des Gigatokens S^(D-1). "
        "Transposition directe de macro-programmes latents en modifications chirurgicales du connectome sans descente de gradient, sous garantie "
        "stricte de contraction spectrale rho(W) < 1.0 (préservation du Lipschitz homéostatique et immunité contre l'explosion d'activation). "
        "Théorie et vérificateur formel de Logique de Hoare Continue verify_hoare_safety validant les triplets {P} C {Q} a priori "
        "pour éliminer toute dérive divergente et toute régression d'alignement constitutionnel (<v_mut, v_constitution> >= 0.65). "
        "Substrats in-world au FederalMonument : mise en place de l'Autel d'Auto-Évolution (self_evolution_altar), consensus de meute, dividendes "
        "énergétiques de saut évolutif (+10.0 E) et enregistrement des preuves de Hoare dans le graphe de connaissances. "
        "Traçabilité Lattice intégrale dans KuzuDB via LUSelfCompiledMutation et LUHoareProof. "
        "Validation empirique 60 ères sous Commandement 15 confirmant l'accélération exponentielle d'efficience énergétique, "
        "l'adaptation face aux chocs agricoles et la clôture de la boucle Seed AI autonome."
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
