import os
import kuzu
import numpy as np
from sklearn.cluster import KMeans
from src.seed_ai.persistence import load_hall_of_fame
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent

DB_PATH = "data/experiment_graph.db"

def extract_h_history(genome, num_ticks=200):
    """Fait tourner un génome dans la Biosphère et enregistre H_history."""
    world = Biosphere3D(size=10)
    agent = MambaAgent(num_inputs=genome.num_inputs, num_outputs=genome.num_outputs)
    agent.genome = genome
    
    world.add_agent(agent, energy=200.0) # Bonus d'énergie pour survivre longtemps
    
    # Simulation pour récolter H_t
    h_series = []
    actions = []
    surprises = []
    
    for t in range(num_ticks):
        world.step()
        if len(world.agents) == 0:
            break
            
        a = world.agents[0]
        h_series.append(a["model"].H_history[-1].copy())
        actions.append(a["last_action"])
        surprises.append(a["model"].surprise)
        
    return np.array(h_series), actions, surprises

def run_hcm_analysis(n_clusters=5):
    """Analyse les génomes du Hall of Fame et extrait des États Cognitifs."""
    hof = load_hall_of_fame()
    if not hof:
        print("❌ Hall of Fame vide. Lancez d'abord la simulation.")
        return
        
    print(f"🧠 Analyse HCM sur le meilleur génome (Score: {hof[0][0]:.1f})")
    best_genome = hof[0][1]
    
    h_series, actions, surprises = extract_h_history(best_genome)
    
    if len(h_series) < 10:
        print("❌ La simulation n'a pas duré assez longtemps pour extraire un HCM.")
        return
        
    # Applatir H_history pour le clustering
    h_flat = h_series.reshape(h_series.shape[0], -1)
    
    # Clustering K-Means
    print(f"🔍 Clustering des {len(h_flat)} états cognitifs en {n_clusters} concepts...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    states = kmeans.fit_predict(h_flat)
    
    # Insérer dans KuzuDB
    print("💾 Insertion dans KuzuDB...")
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    
    # Création des noeuds CognitiveState si la table n'existe pas
    try:
        conn.execute("CREATE NODE TABLE CognitiveState (state_id STRING, type STRING, cluster_center STRING, PRIMARY KEY (state_id))")
        conn.execute("CREATE REL TABLE TRANSITIONS_TO (FROM CognitiveState TO CognitiveState, prob DOUBLE)")
    except RuntimeError:
        pass # La table existe déjà
        
    # Purge et insertion des états
    conn.execute("MATCH (c:CognitiveState) DETACH DELETE c")
    
    for cluster_id in range(n_clusters):
        idx = np.where(states == cluster_id)[0]
        if len(idx) > 0:
            avg_surprise = float(np.mean([surprises[i] for i in idx]))
            dominant_action = int(np.bincount([actions[i] for i in idx]).argmax())
            
            action_map = {0:"N", 1:"S", 2:"E", 3:"W", 4:"UP", 5:"DOWN", -1:"NONE"}
            desc = f"Action Dominante: {action_map.get(dominant_action, str(dominant_action))}"
            desc_safe = desc.replace("'", "")
            conn.execute(f"CREATE (c:CognitiveState {{state_id: '{cluster_id}', type: '{desc_safe}', cluster_center: '{avg_surprise:.4f}'}})")
                         
    # Insertion des transitions de Markov
    transitions = {}
    for i in range(len(states) - 1):
        s_from = states[i]
        s_to = states[i+1]
        pair = (s_from, s_to)
        transitions[pair] = transitions.get(pair, 0) + 1
        
    for (s_from, s_to), count in transitions.items():
        prob = float(count) / len(states)
        conn.execute(
            f"MATCH (a:CognitiveState {{state_id: '{s_from}'}}), (b:CognitiveState {{state_id: '{s_to}'}}) "
            f"CREATE (a)-[:TRANSITIONS_TO {{prob: {prob}}}]->(b)"
        )
        
    print("✅ Extraction HCM terminée. États et Transitions sauvegardés dans KuzuDB.")

if __name__ == "__main__":
    run_hcm_analysis()
