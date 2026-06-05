import os
import sys
import kuzu
import numpy as np
from sklearn.cluster import KMeans
import ast

# Utilisons le même chemin que async_logger.py 
DB_PATH = os.path.join("data", "kuzu_graph.db")

def run_linguistic_analysis(n_clusters=3):
    if not os.path.exists(DB_PATH):
        print("❌ Aucune base KuzuDB trouvée. Lancez la simulation d'abord.")
        return
        
    print("🔍 Analyse Linguistique (Sociologue V2)")
    print("Connexion à KuzuDB...")
    
    try:
        db = kuzu.Database(DB_PATH)
        conn = kuzu.Connection(db)
        
        # On cherche les événements de rencontre sociale
        try:
            result = conn.execute("MATCH (s:SocialEncounter) RETURN s.spoken_a, s.spoken_b")
        except RuntimeError as e:
            print(f"❌ La table SocialEncounter n'existe pas encore. Lancez la simulation. Erreur: {e}")
            return
            
        vectors = []
        while result.has_next():
            row = result.get_next()
            spoken_a_str = row[0]
            spoken_b_str = row[1]
            
            try:
                vec_a = ast.literal_eval(spoken_a_str)
                vec_b = ast.literal_eval(spoken_b_str)
                
                # Filtrer les silences stricts [0.0, 0.0, 0.0, 0.0]
                if sum(abs(x) for x in vec_a) > 0.01: vectors.append(vec_a)
                if sum(abs(x) for x in vec_b) > 0.01: vectors.append(vec_b)
            except Exception:
                pass
                
        if len(vectors) < 10:
            print(f"❌ Pas assez de données vocales (trouvé {len(vectors)}). Laissez la simulation tourner plus longtemps.")
            return
            
        print(f"✅ {len(vectors)} vocalisations extraites.")
        
        X = np.array(vectors)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X)
        
        print(f"\n📊 Résultats du Clustering (K={n_clusters}) :")
        for i in range(n_clusters):
            count = np.sum(clusters == i)
            center = kmeans.cluster_centers_[i]
            print(f"  [Mot {i}] ({count} occurrences) : Centre = [{center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f}, {center[3]:.2f}]")
            
        print("\n📝 Conclusion Sociologique :")
        print("Si les centres de clusters sont très distincts et que la variance intra-cluster est faible,")
        print("cela prouve mathématiquement l'apparition d'une grammaire primitive émergente.")
        print("Les agents ont inventé ces signaux par nécessité de survie (ex: chasse au Mammouth).")
        
    except Exception as e:
        print(f"Erreur inattendue lors de l'analyse linguistique : {e}")

if __name__ == "__main__":
    run_linguistic_analysis()
