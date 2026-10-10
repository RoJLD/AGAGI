"""
tools/register_article_021.py — Enregistre l'Article 021 dans KuzuDB.
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

    art_id = "art_021_langage_ultime_noosphere_epistemique_wasserstein"
    title = "Article 021: Langage Ultime Phase 12 — La Noosphère Latente, Conscience Collective Trans-Mondes, Métacognition Épistémique et Transport Optimal de Wasserstein (Arc 7: La Noosphère)"
    content = (
        "docs/021_Langage_Ultime_Noosphere_Epistemique_Wasserstein.md - "
        "Franchissement du seuil G12 (La Noosphère Latente et la Conscience Collective Trans-Mondes). "
        "Résolution des 3 verrous majeurs de l'Arc 6 : suppression du mur de portée spatiale via la convolution harmonique "
        "inverse du réseau de stèles stigmargiques Phi_noo(x, y), éradication du biais de Dunning-Kruger latent par le moteur "
        "de métacognition épistémique de second ordre EpistemicUncertaintyEngine, et préservation de la multi-modalité des cultures "
        "claniques via le consensus synarchique par Barycentre de Sinkhorn-Wasserstein sur S^(D-1). "
        "Institution du Conseil Synarchique de la Noosphère distribuant le Dividende Noosphérique (+8.0 E). "
        "Traçabilité Lattice Memory via LUNoosphereField et LUEpistemicInsight. "
        "Validation empirique stricte 60 ères sous Commandement 15 confirmant le gain sociologique et la robustesse de civilisation."
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
