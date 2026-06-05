import numpy as np
import logging
import time
import os

from src.seed_ai.evolution import EvolutionConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.rl_evolution import RLPopulation, evaluate_rl_fitness, forward
from src.environments.gridworld import GridWorld

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AGIseed.RL")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    logger.info("🌍 Démarrage de l'Usine Évolutive (Phase 5 : Embodied GridWorld)")
    
    # Paramètres d'évolution (Darwiniens)
    mut_config = MutationConfig(
        weight_mutate_rate=0.8,
        weight_mutate_power=0.5,
        add_node_rate=0.1,
        add_connection_rate=0.3,
        prune_rate=0.1,
        weight_init_std=2.0
    )
    
    evo_config = EvolutionConfig(
        pop_size=200,        
        generations=50,     
        lambda_penalty=0.0001, # Faible pénalité pour laisser le réseau grossir
        survival_rate=0.15
    )

    # 8 Entrées (Nord, Sud, Est, Ouest, Biais, Phéromone, AbsX, AbsY) -> 4 Sorties
    pop = RLPopulation(evo_config, mut_config, num_inputs=8, num_outputs=4)
    
    best_fitness = -float('inf')
    best_genome = None
    
    logger.info("🚀 Début de l'Évolution (Chasse à la Pomme)...")
    
    for gen in range(1, evo_config.generations + 1):
        fitness, genome = pop.step()
        
        if fitness > best_fitness:
            best_fitness = fitness
            best_genome = genome
            logger.info(f"🧬 Génération {gen:03d} | Nouvelle meilleure Fitness: {best_fitness:.4f}")

    logger.info(f"✅ Évolution terminée. Meilleur score final : {best_fitness:.4f}")
    logger.info("🎬 Lancement du Rendu ASCII (Simulation en direct)...")
    time.sleep(2)
    
    # Simulation visuelle du meilleur agent
    env = GridWorld(size=10, max_steps=50, prey_mode="semi")
    obs = env.reset()
    done = False
    
    from src.seed_ai.rl_evolution import recurrent_forward
    H_history = np.zeros((3, 1, best_genome.num_nodes))
    last_action = -1
    
    while not done:
        clear_screen()
        env.render()
        print(f"[*] Score (Fitness du test en cours) : {env.steps}")
        
        preds, H_history = recurrent_forward(best_genome, obs, H_history)
        
        logits = preds[0].copy()
        if last_action != -1:
            logits[last_action] += 0.1
            
        action = int(np.argmax(logits))
        last_action = action
        
        obs, reward, done = env.step(action)
        time.sleep(0.3)
        
    clear_screen()
    env.render()
    if reward >= 1.0:
        print("[+] L'IA a trouvé et mangé la cible !")
    else:
        print("[-] L'IA n'a pas réussi à trouver la cible à temps.")

if __name__ == "__main__":
    main()
