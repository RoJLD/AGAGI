#!/usr/bin/env python
import kuzu
import json
import numpy as np
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Kuzu Sociologist: Analyze Swarm Vocabulary")
    parser.add_argument("--db", type=str, default="data/kuzu_graph.db", help="Path to KuzuDB")
    args = parser.parse_args()
    
    db_path = args.db
    # Try different paths just in case
    paths_to_try = [db_path, "data/experiment_graph.db", "data/kuzudb/kuzu.db"]
    
    db = None
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                db = kuzu.Database(path)
                print(f"Connected to KuzuDB at {path}")
                break
            except Exception as e:
                print(f"Could not open database at {path}: {e}")
                
    if db is None:
        print("Could not connect to any KuzuDB instances.")
        return

    conn = kuzu.Connection(db)
    
    # Query for LANGUAGE_ALIGNMENT LogEvents
    try:
        query = "MATCH (e:LogEvent) WHERE e.type = 'LANGUAGE_ALIGNMENT' RETURN e.payload"
        results = conn.execute(query)
    except Exception as e:
        print(f"No LogEvent table or LANGUAGE_ALIGNMENT events found: {e}")
        return

    item_vectors = {}
    
    count = 0
    while results.has_next():
        payload_str = results.get_next()[0]
        try:
            payload = json.loads(payload_str)
            item = payload.get("item")
            vector = payload.get("vector")
            if item and vector:
                if item not in item_vectors:
                    item_vectors[item] = []
                item_vectors[item].append(vector)
                count += 1
        except Exception as e:
            pass

    if not item_vectors:
        print("No LANGUAGE_ALIGNMENT events found with valid item and vector.")
        return

    print("\n--- The Swarm's Vocabulary Dictionary ---")
    for item, vectors in item_vectors.items():
        arr = np.array(vectors)
        mean_vec = np.mean(arr, axis=0)
        # Format the vector for printing
        vec_str = ", ".join([f"{v:.4f}" for v in mean_vec])
        print(f"'{item}' -> [{vec_str}] (based on {len(vectors)} samples)")

    # Observateur Sémantique : Le Graphe des Pensées
    try:
        query_intents = "MATCH (a:Intent)-[r:LEADS_TO]->(b:Intent) RETURN a.action, b.action, count(r) AS weight ORDER BY weight DESC LIMIT 10"
        res_intents = conn.execute(query_intents)
        if res_intents.has_next():
            print("\n--- The Swarm's Semantic Graph (Top Intent Chains) ---")
            while res_intents.has_next():
                a_act, b_act, w = res_intents.get_next()
                print(f"[Action {a_act}] --(LEADS_TO)--> [Action {b_act}] : {w} occurrences")
    except Exception as e:
        print(f"Erreur requête Intents: {e}")
        pass

    # Commandement 16 : Articles Scientifiques
    try:
        query_articles = "MATCH (a:Article) RETURN a.id, a.title, a.content, a.date ORDER BY a.date DESC LIMIT 5"
        res_articles = conn.execute(query_articles)
        if res_articles.has_next():
            print("\n--- Derniers Articles Scientifiques (KuzuDB) ---")
            while res_articles.has_next():
                a_id, title, content, date = res_articles.get_next()
                print(f"📰 {date[:10]} | {title}")
                print(f"   {content[:150]}...")
    except Exception as e:
        print(f"Erreur requête Articles: {e}")
        pass

if __name__ == "__main__":
    main()
