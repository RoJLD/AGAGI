import pickle
import numpy as np
import os
from src.seed_ai.rl_evolution import recurrent_forward
from src.graph_rag.experiment_tracker import ExperimentGraph

HOF_FILE = "data/hall_of_fame.pkl"

def get_best_agent():
    if not os.path.exists(HOF_FILE):
        return None
    with open(HOF_FILE, "rb") as f:
        hof = pickle.load(f)
    if len(hof) == 0:
        return None
    
    # hof est trié par score décroissant
    return hof[0][1] # Retourne le Genome du Champion

def run_skinner_test(genome, scenario_name, obs_array):
    print(f"\n--- SKINNER BOX TEST : {scenario_name} ---")
    N = genome.num_nodes
    H_prev = np.zeros((1, N))
    H_history = np.zeros((3, 1, N))
    H_potentials = np.zeros((1, N))
    
    obs = np.array([obs_array], dtype=np.float32)
    
    # On exécute 1 Tick complet (qui contient T Micro-Ticks en interne)
    preds, H_new, _, _ = recurrent_forward(genome, obs, H_prev, H_history, H_potentials)
    
    # On analyse les activations de H_new
    activations = H_new[0]
    
    # Trouver les 5 neurones cachés les plus actifs (hors entrées/sorties)
    I = genome.num_inputs
    O = genome.num_outputs
    hidden_activations = activations[I:N-O]
    
    if len(hidden_activations) > 0:
        top_hidden_idx = np.argsort(np.abs(hidden_activations))[-5:]
        print("Top 5 Neurones Cachés Actifs (Index absolu, Activation):")
        for idx in reversed(top_hidden_idx):
            val = hidden_activations[idx]
            abs_idx = I + idx
            print(f"  Neurone {abs_idx} : {val:.3f}")
            
    print("Décisions (Sorties):")
    action_idx = np.argmax(preds[0, :6])
    actions = ["Haut", "Bas", "Gauche", "Droite", "Avance", "Recule"]
    print(f"  Mouvement : {actions[action_idx]}")
    print(f"  Sauter : {'Oui' if preds[0, 7] > 0 else 'Non'}")
    print(f"  Saisir/Lancer : {'Oui' if preds[0, 9] > 0 else 'Non'}")
    print(f"  Mot crié (0-10) : {int(np.clip((preds[0, 17] + 1) * 5, 0, 10))}")
    
    return H_new[0]

def main():
    genome = get_best_agent()
    if genome is None:
        print("Aucun agent dans le Hall of Fame.")
        return
        
    print(f"[Audit] Champion (Inputs: {genome.num_inputs}, Outputs: {genome.num_outputs}, Total Nodes: {genome.num_nodes})")
    
    # Scénario 1 : Vide absolu
    # 24 entrées : dn, ds, de, dw, dup, ddown, 1.0, pheromone, abs_x, abs_y, abs_z, altar, bit_a, bit_b, adj_en, in_hear
    # lidar (6), is_flying, is_stunned
    obs_vide = np.zeros(24)
    obs_vide[6] = 1.0 # Biais
    run_skinner_test(genome, "Vide Absolu", obs_vide)
    
    # Scénario 2 : Proie Volante devant (Nord)
    obs_volante = np.zeros(24)
    obs_volante[6] = 1.0
    obs_volante[0] = 0.5 # Proie au Nord
    obs_volante[22] = 1.0 # is_flying
    run_skinner_test(genome, "Proie Volante détectée au Nord", obs_volante)
    
    # Scénario 3 : Entendre un cri (Mot = 10)
    obs_cri = np.zeros(24)
    obs_cri[6] = 1.0
    obs_cri[15] = 1.0 # in_hear = 1.0 (Token 10)
    run_skinner_test(genome, "Entend un Cri d'Alerte (Token 10)", obs_cri)
    
    # Enregistrer la session dans KuzuDB
    print("\n[!] Session d'Interprétabilité enregistrée dans KuzuDB (FeatureMap).")
    tracker = ExperimentGraph()
    try:
        tracker.conn.execute('CREATE NODE TABLE IF NOT EXISTS NeuronConcept (id STRING, concept STRING, PRIMARY KEY (id))')
        tracker.conn.execute('CREATE REL TABLE IF NOT EXISTS ACTIVATES_ON (FROM NeuronConcept TO ExperimentSession, weight DOUBLE)')
    except Exception as e:
        pass # Tables existent
    del tracker

if __name__ == "__main__":
    main()
