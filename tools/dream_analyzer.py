import kuzu
import numpy as np

def analyze_dreams(db_path="data/kuzu_graph_v16.db"):
    print(f"🔍 Analyse Sociologique MCTS (Dreamer vs Reflex) via KuzuDB...")
    try:
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
    except Exception as e:
        print(f"❌ Erreur de connexion à KuzuDB: {e}")
        return

    # Extraire les statistiques de vie
    try:
        results = conn.execute("MATCH (l:AgentLifespan) RETURN l.agent_id, l.era, l.score, l.energy, l.total_dreams, l.total_reflexes;")
    except Exception as e:
        print(f"❌ Impossible d'extraire les données AgentLifespan (Assurez-vous d'avoir lancé la simulation). {e}")
        return

    lifespans = []
    while results.has_next():
        row = results.get_next()
        lifespans.append({
            "agent_id": row[0],
            "era": row[1],
            "score": row[2],
            "energy": row[3],
            "dreams": row[4],
            "reflexes": row[5]
        })

    if not lifespans:
        print("❌ Aucune donnée AgentLifespan trouvée. Laissez la simulation tourner au moins une Ère entière.")
        return

    dreamers = [l for l in lifespans if l["dreams"] > 5]
    reflexers = [l for l in lifespans if l["dreams"] <= 5]

    print("\n=======================================================")
    print("📊 RAPPPORT AGIseed: MCTS Dreaming vs Pure Reflex")
    print("=======================================================")
    print(f"Total Agents Analysés : {len(lifespans)}")
    print(f"-> Agents 'Rêveurs' (MCTS) : {len(dreamers)}")
    print(f"-> Agents 'Réflexes' purs  : {len(reflexers)}")

    if dreamers:
        avg_score_d = np.mean([d["score"] for d in dreamers])
        avg_energy_d = np.mean([d["energy"] for d in dreamers])
        print(f"\n🌟 RÊVEURS (Dreams > 5):")
        print(f"  - Score moyen   : {avg_score_d:.2f}")
        print(f"  - Énergie moy.  : {avg_energy_d:.2f}")
    
    if reflexers:
        avg_score_r = np.mean([r["score"] for r in reflexers])
        avg_energy_r = np.mean([r["energy"] for r in reflexers])
        print(f"\n⚡ RÉFLEXES (Dreams <= 5):")
        print(f"  - Score moyen   : {avg_score_r:.2f}")
        print(f"  - Énergie moy.  : {avg_energy_r:.2f}")

    if dreamers and reflexers:
        diff_score = avg_score_d - avg_score_r
        print("\n🏆 CONCLUSION:")
        if diff_score > 0:
            print(f"Le 'Dreaming' (MCTS latent) confère un avantage évolutif (+{diff_score:.2f} Score).")
        else:
            print(f"Les réflexes purs sont plus efficaces énergétiquement pour l'instant ({diff_score:.2f} Score).")

if __name__ == "__main__":
    analyze_dreams()
