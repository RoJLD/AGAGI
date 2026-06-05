"""
AGIseed Sociologist - Outil d'analyse KuzuDB (Option B : On-Demand)
Interroge le graphe de connaissances pour produire un rapport sociologique
sur l'evolution, la genetique et la culture des agents.
"""
import kuzu
import os
import sys
import datetime

DB_PATH = os.path.join("data", "kuzu_graph.db")

def connect():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    return db, conn

def safe_query(conn, query, label):
    try:
        result = conn.execute(query)
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        return rows
    except Exception as e:
        print(f"  [WARN] {label}: {e}")
        return []

def report():
    if not os.path.exists(DB_PATH):
        print("[!] Aucune base KuzuDB trouvee. Lancez la simulation d'abord.")
        return
        
    db, conn = connect()
    
    print("=" * 60)
    print("  RAPPORT SOCIOLOGIQUE AGIseed")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Combien d'experiences enregistrees ?
    print("\n--- 1. HISTORIQUE DES VERSIONS ---")
    rows = safe_query(conn, "MATCH (e:Experiment) RETURN e.name, e.description ORDER BY e.name", "Versions")
    if rows:
        for r in rows:
            print(f"  [{r[0]}] {r[1]}")
    else:
        print("  Aucune version trouvee.")
    
    # 2. Resultats par version
    print("\n--- 2. RESULTATS PAR VERSION ---")
    rows = safe_query(conn, """
        MATCH (e:Experiment)-[:YIELDED_RESULT]->(res:Result)
        RETURN e.name, res.max_score, res.mean_score, res.ticks
        ORDER BY e.name
    """, "Results")
    if rows:
        print(f"  {'Version':<20} {'Max Score':>10} {'Mean Score':>10} {'Ticks':>6}")
        print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*6}")
        for r in rows:
            ver = str(r[0])[:20]
            mx = f"{r[1]:.1f}" if r[1] is not None else "N/A"
            mn = f"{r[2]:.1f}" if r[2] is not None else "N/A"
            tk = str(r[3]) if r[3] is not None else "N/A"
            print(f"  {ver:<20} {mx:>10} {mn:>10} {tk:>6}")
    else:
        print("  Aucun resultat enregistre.")
    
    # 3. Lignees genetiques (EVOLVED_FROM)
    print("\n--- 3. ARBRE GENEALOGIQUE DES VERSIONS ---")
    rows = safe_query(conn, """
        MATCH (child:Experiment)-[:DERIVED_FROM]->(parent:Experiment)
        RETURN parent.name, child.name
        ORDER BY parent.name
    """, "Genealogy")
    if rows:
        for r in rows:
            print(f"  {r[0]} --> {r[1]}")
    else:
        print("  Aucune lignee trouvee.")
    
    # 4. Capacites cumulees
    print("\n--- 4. CAPACITES ACQUISES (derniere version) ---")
    rows = safe_query(conn, """
        MATCH (e:Experiment)-[:HAS_CAPABILITY]->(c:Capability)
        RETURN e.name, collect(c.name)
        ORDER BY e.name DESC
        LIMIT 1
    """, "Capabilities")
    if rows:
        ver = rows[0][0]
        caps = rows[0][1]
        print(f"  Version: {ver}")
        for cap in caps:
            print(f"    - {cap}")
    else:
        print("  Aucune capacite trouvee.")
    
    # 5. Statistiques globales
    print("\n--- 5. STATISTIQUES GLOBALES ---")
    rows = safe_query(conn, """
        MATCH (res:Result)
        RETURN count(res), max(res.max_score), avg(res.mean_score), max(res.ticks)
    """, "Global Stats")
    if rows and len(rows[0]) == 4:
        print(f"  Nombre d'eres enregistrees : {rows[0][0]}")
        print(f"  Meilleur score all-time    : {rows[0][1]}")
        print(f"  Moyenne des moyennes       : {rows[0][2]:.1f}" if rows[0][2] else "  Moyenne: N/A")
        print(f"  Plus longue ere (ticks)    : {rows[0][3]}")
    
    # 6. NeuronConcepts (Skinner Box)
    print("\n--- 6. CONCEPTS NEURONAUX (Skinner Box) ---")
    rows = safe_query(conn, "MATCH (n:NeuronConcept) RETURN n.id, n.concept", "NeuronConcepts")
    if rows:
        for r in rows:
            print(f"  Neurone {r[0]} = '{r[1]}'")
    else:
        print("  Aucun concept neuronal enregistre (lancez tools/skinner_box.py).")
    
    # 7. Crafting & Feu (EXP-7)
    print("\n--- 7. CRAFTING & FEU (EXP-7) ---")
    rows = safe_query(conn, "MATCH (f:Fire) RETURN count(f)", "FireStats")
    if rows and rows[0][0] > 0:
        print(f"  Feux allumés par friction : {rows[0][0]}")
    else:
        print("  Aucun feu allumé.")
        
    rows = safe_query(conn, "MATCH (a:Agent)-[r:NEAR_FIRE]->(f:Fire) RETURN count(r), avg(r.duration)", "NearFire")
    if rows and rows[0][0] > 0:
        print(f"  Agents réchauffés         : {rows[0][0]}")
        print(f"  Temps moyen près du feu   : {rows[0][1]:.1f} ticks")

    # 8. Langage (EXP-8)
    print("\n--- 8. EMERGENCE VOCALE (EXP-8) ---")
    rows = safe_query(conn, "MATCH (l:LanguageAlignment) RETURN l.item_type, count(l), avg(l.v0), avg(l.v1), avg(l.v2), avg(l.v3) ORDER BY count(l) DESC", "LangAlign")
    if rows:
        print(f"  {'Objet/Contexte':<15} {'Occurrences':>11} {'Vecteur Vocal Moyen (v0, v1, v2, v3)'}")
        print(f"  {'-'*15} {'-'*11} {'-'*40}")
        for r in rows:
            print(f"  {r[0]:<15} {r[1]:>11} [{r[2]:.2f}, {r[3]:.2f}, {r[4]:.2f}, {r[5]:.2f}]")
    else:
        print("  Aucun alignement vocal observé.")

    # 9. Lifespan & Cognition
    print("\n--- 9. ESPERANCE DE VIE & METACOGNITION ---")
    rows = safe_query(conn, "MATCH (l:AgentLifespan) RETURN avg(l.score), avg(l.total_dreams), avg(l.total_reflexes), l.era ORDER BY l.era", "Lifespans")
    if rows:
        print(f"  {'Ere':<6} {'Score Moyen':>12} {'Dreams (MCTS)':>15} {'Reflexes':>10}")
        for r in rows:
            print(f"  {r[3]:<6} {r[0]:>12.1f} {r[1]:>15.1f} {r[2]:>10.1f}")
    else:
        print("  Aucune donnée Lifespan.")

    print("\n" + "=" * 60)
    print("=" * 60)
    
    del conn
    del db

if __name__ == "__main__":
    report()
