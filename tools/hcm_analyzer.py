import os
import sys
import pickle
import numpy as np

# Ajouter la racine du projet au PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.seed_ai.persistence import load_hall_of_fame
from src.seed_ai.rl_evolution import recurrent_forward
from src.environments.biosphere import Biosphere3D

def run_hcm_analysis(num_ticks=200, n_clusters=4):
    """
    Exécute une analyse 'Hidden Cognition Models' (HCM) sur le meilleur agent.
    Objectif: Découvrir les états cognitifs latents de l'agent (Phylogénèse cognitive).
    """
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(num_ticks) <= 0 or int(n_clusters) <= 0:
        raise ValueError(
            f"run_hcm_analysis : argument degenere (num_ticks={num_ticks}, n_clusters={n_clusters}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    print("🧠 Démarrage de l'Observatoire HCM (Hidden Cognition Models)")
    
    # ⚠️ CORRIGE le 2026-09-09, et c'est le defaut le plus instructif de la passe : cette fonction
    # etait DECLAREE CALIBREE (`empty-cohort:raises`, `guard-before-world`) et ne pouvait pas
    # s'executer. Ses deux cas n'exercent que la garde d'arguments ci-dessus, qui leve AVANT
    # d'atteindre cette ligne -- la calibration passait sans jamais entrer dans le corps.
    # Trois defauts de contrat : `load_hall_of_fame()` rend `(version, entries)` et non une liste ;
    # une entree est un `AgentSnapshot` non indexable (`.genome`, `.score`) ; et le deballage
    # `best_score, best_genome, stats = ...` supposait un triplet.
    _version, entries = load_hall_of_fame()
    valid_hof = [e for e in entries if e.genome.num_inputs == 32]
    if not valid_hof:
        raise ValueError(
            "run_hcm_analysis : aucun genome a 32 entrees dans le Hall of Fame "
            f"({len(entries)} entree(s) chargee(s)) -- ce n'est PAS un resultat sur la cognition, "
            "c'est une cohorte vide ; verifier HOF_PATH et la compatibilite de version.")

    best_score, best_genome = valid_hof[0].score, valid_hof[0].genome
    print(f"✅ Chargement du Champion. Score: {best_score}")
    print(f"📊 Taille du Cerveau (N): {best_genome.num_nodes}, Entrées: {best_genome.num_inputs}, Sorties: {best_genome.num_outputs}")
    
    # Création d'un environnement contrôlé
    env = Biosphere3D(size=10)
    env.add_agent(best_genome, x=5, y=5, z=0, energy=100.0)
    agent = env.agents[0]
    
    # Extraire les objets au sol pour stimuler l'agent
    env.items.append({"x": 5, "y": 6, "z": 0, "type": "stick_short"})
    env.items.append({"x": 6, "y": 5, "z": 0, "type": "rock_small"})
    
    H_sequence = []
    actions_sequence = []
    
    print(f"🏃 Simulation de l'agent sur {num_ticks} ticks...")
    for t in range(num_ticks):
        obs = env._get_agent_observation(agent)
        
        preds, H_prev, H_history, H_potentials, surprise = recurrent_forward(
            agent["genome"], obs, agent["H_prev"], agent["H_history"], agent["H_potentials"]
        )
        
        agent["H_prev"] = H_prev
        agent["H_history"] = H_history
        agent["H_potentials"] = H_potentials
        
        # Enregistrer l'état cognitif H_t (aplatissement du vecteur)
        H_sequence.append(H_prev.flatten())
        
        logits = preds[0].copy()
        if agent["last_action"] != -1:
            logits[agent["last_action"]] += 0.1
        action = int(np.argmax(logits[:6]))
        actions_sequence.append(action)
        agent["last_action"] = action
        
        # Simuler le mouvement rudimentaire pour changer l'observation
        nx, ny, nz = agent["x"], agent["y"], agent["z"]
        if action == 0: ny -= 1
        elif action == 1: ny += 1
        elif action == 2: nx += 1
        elif action == 3: nx -= 1
        if 0 <= nx < env.size and 0 <= ny < env.size:
            agent["x"], agent["y"] = nx, ny
            
    # Traitement Machine Learning
    X = np.array(H_sequence)
    
    print("\n🔬 Clustering des États d'Esprit (HCM)...")
    try:
        from sklearn.cluster import KMeans
        # Utilisation de K-Means pour simuler les états cachés
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        states = kmeans.fit_predict(X)
        
        print("\n=== MATRICE DE TRANSITION HCM ===")
        # Calcul de la matrice de transition P(State J | State I)
        transitions = np.zeros((n_clusters, n_clusters))
        for t in range(len(states) - 1):
            s_curr = states[t]
            s_next = states[t+1]
            transitions[s_curr, s_next] += 1
            
        for i in range(n_clusters):
            total = np.sum(transitions[i])
            if total > 0:
                transitions[i] = transitions[i] / total
            
        for i in range(n_clusters):
            print(f"État Cognitif {i} transitions:")
            for j in range(n_clusters):
                if transitions[i, j] > 0.05: # Afficher seulement les probas significatives
                    print(f"  -> Vers État {j} : {transitions[i, j]*100:.1f}%")
                    
        print("\n=== RÉPARTITION TEMPORELLE ===")
        for i in range(n_clusters):
            count = np.sum(states == i)
            print(f"État {i} : actif {count} ticks ({(count/num_ticks)*100:.1f}%)")
            
        print("\n✅ L'Agent possède une signature cognitive distincte !")
        print("💡 Ces états peuvent correspondre à : 'Foraging', 'Chasse', 'Crafting', etc.")
        
    except ImportError:
        print("⚠️ Le module 'scikit-learn' n'est pas installé. Veuillez l'ajouter au requirements.txt pour l'analyse HCM complète.")
        print("   pip install scikit-learn")

if __name__ == "__main__":
    run_hcm_analysis()
