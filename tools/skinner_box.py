import pickle
import numpy as np
import os
from src.seed_ai.rl_evolution import recurrent_forward
from src.graph_rag.experiment_tracker import ExperimentGraph

HOF_FILE = "data/hall_of_fame.pkl"

from src.seed_ai.persistence import load_hall_of_fame

def get_best_agent():
    try:
        version, hof = load_hall_of_fame()
        if len(hof) == 0:
            return None
        best = hof[0]
        if hasattr(best, 'genome'):
            return best.genome
        elif isinstance(best, tuple) and len(best) > 1:
            return best[1]
        return best
    except Exception as e:
        print(f"[WARN] Failed to load champion from Hall of Fame: {e}")
        return None

def run_skinner_test(genome, scenario_name, obs_array, tracker=None):
    print(f"\n--- SKINNER BOX TEST : {scenario_name} ---")
    N = genome.num_nodes
    H_prev = np.zeros((1, N))
    H_history = np.zeros((3, 1, N))
    H_potentials = np.zeros((1, N))
    
    obs = np.array([obs_array], dtype=np.float32)
    
    # recurrent_forward returns 5 outputs
    outputs = recurrent_forward(genome, obs, H_prev, H_history, H_potentials)
    preds = outputs[0]
    H_new = outputs[1]
    
    activations = H_new[0]
    
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
            
            # Enregistrer le concept neuronal identifié dans KuzuDB
            if tracker is not None:
                try:
                    concept_desc = f"Active pour le scenario '{scenario_name}' (activation: {val:.3f})"
                    safe_desc = concept_desc.replace("'", "\\'")
                    query = f"MERGE (n:NeuronConcept {{id: 'Neuron_{abs_idx}'}}) SET n.concept = '{safe_desc}'"
                    tracker.conn.execute(query)
                except Exception as e:
                    print(f"  [WARN] Failed to write NeuronConcept to KuzuDB: {e}")
            
    print("Décisions (Sorties):")
    action_idx = np.argmax(preds[0, :6])
    actions = ["Haut", "Bas", "Gauche", "Droite", "Avance", "Recule"]
    print(f"  Mouvement : {actions[action_idx]}")
    print(f"  Sauter : {'Oui' if preds[0, 7] > 0 else 'Non'}")
    print(f"  Saisir/Lancer : {'Oui' if preds[0, 9] > 0 else 'Non'}")
    
    # Word spoken index safety check (if output dimension allows)
    word_val = int(np.clip((preds[0, 17] + 1) * 5, 0, 10)) if preds.shape[1] > 17 else 0
    print(f"  Mot crié (0-10) : {word_val}")
    
    return H_new[0]

def main(db_path="data/kuzu_graph.db", db=None):
    genome = get_best_agent()
    if genome is None:
        print("Aucun agent dans le Hall of Fame.")
        return
        
    print(f"[Audit] Champion (Inputs: {genome.num_inputs}, Outputs: {genome.num_outputs}, Total Nodes: {genome.num_nodes})")
    
    # Connexion à KuzuDB pour y écrire les observations
    tracker = None
    try:
        tracker = ExperimentGraph(db_path=db_path, db=db)
        # S'assurer de la présence de la table
        try:
            tracker.conn.execute('CREATE NODE TABLE IF NOT EXISTS NeuronConcept (id STRING, concept STRING, PRIMARY KEY (id))')
        except Exception:
            pass
    except Exception as e:
        print(f"[WARN] Impossible de se connecter à KuzuDB pour enregistrer l'audit : {e}")

    # Scénario 1 : Vide absolu (taille dynamique selon les entrées du génome)
    obs_vide = np.zeros(genome.num_inputs)
    obs_vide[6] = 1.0 # Biais
    run_skinner_test(genome, "Vide Absolu", obs_vide, tracker=tracker)
    
    # Scénario 2 : Proie devant (Nord)
    obs_volante = np.zeros(genome.num_inputs)
    obs_volante[6] = 1.0
    obs_volante[0] = 0.5 # Proie au Nord
    if genome.num_inputs > 22:
        obs_volante[22] = 1.0 # is_flying
    run_skinner_test(genome, "Proie détectée au Nord", obs_volante, tracker=tracker)
    
    # Scénario 3 : Entendre un cri
    obs_cri = np.zeros(genome.num_inputs)
    obs_cri[6] = 1.0
    if genome.num_inputs > 15:
        obs_cri[15] = 1.0 # in_hear = 1.0 (Token 10)
    run_skinner_test(genome, "Entend un Cri d'Alerte", obs_cri, tracker=tracker)
    
    print("\n[!] Session d'Interprétabilité enregistrée dans KuzuDB (NeuronConcept).")
    if tracker is not None:
        del tracker

if __name__ == "__main__":
    main()
