import numpy as np
import logging
import time
import os

from src.seed_ai.evolution import EvolutionConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.rl_evolution import RLPopulation, evaluate_rl_fitness
from src.environments.spaceworld import SpaceWorld

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AGIseed.SpaceWorld")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    logger.info("🌌 Démarrage de l'Usine Évolutive (Phase 10 : Embodied SpaceWorld 3D)")
    
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
        generations=80,     
        lambda_penalty=0.0001,
        survival_rate=0.15
    )

    env_kwargs = {"size": 10, "max_steps": 50, "prey_mode": "semi"}
    
    # 14 Entrées (11 Spatiales + 3 Cognitives) -> 8 Sorties (6 Motrices + 1 Cognitive + 1 Patience O1)
    pop = RLPopulation(
        evo_config, 
        mut_config, 
        num_inputs=14, 
        num_outputs=8,
        env_class=SpaceWorld,
        env_kwargs=env_kwargs
    )
    
    best_fitness = -float('inf')
    best_genome = None
    
    logger.info("🚀 Début de l'Évolution (Chasse 3D)...")
    
    for gen in range(1, evo_config.generations + 1):
        fitness, genome = pop.step()
        
        if fitness > best_fitness:
            best_fitness = fitness
            best_genome = genome
            logger.info(f"🧬 Génération {gen:03d} | Nouvelle meilleure Fitness: {best_fitness:.4f}")

    logger.info(f"✅ Évolution terminée. Meilleur score final : {best_fitness:.4f}")
    logger.info("🎬 Lancement du Rendu ASCII 3D (Simulation en direct)...")
    time.sleep(2)
    
    env = SpaceWorld(**env_kwargs)
    obs = env.reset()
    done = False
    
    from src.seed_ai.rl_evolution import recurrent_forward
    H_prev = np.zeros((1, best_genome.num_nodes))
    H_history = np.zeros((3, 1, best_genome.num_nodes))
    H_potentials = np.zeros((1, best_genome.num_nodes))
    last_action = -1
    
    while not done:
        clear_screen()
        env.render()
        print(f"[*] Score (Fitness du test en cours) : {env.steps}")
        
        preds, H_prev, H_history, H_potentials = recurrent_forward(best_genome, obs, H_prev, H_history, H_potentials)
        
        logits = preds[0].copy()
        if last_action != -1:
            logits[last_action] += 0.1
            
        action = int(np.argmax(logits[:6]))
        cognitive_out = float(logits[6])
        last_action = action
        
        obs, reward, done = env.step(action, cognitive_out)
        
        if env.prey_paralyzed > 0:
            print(f"⚡ PROIE PARALYSÉE ({env.prey_paralyzed} tours) ! Réussite Cognitive !")
            
        time.sleep(0.3)
        
    clear_screen()
    env.render()
    if reward >= 1.0:
        print("[+] L'IA a trouvé et intercepté la cible en 3D !")
    else:
        print("[-] L'IA a perdu la cible dans l'espace.")

if __name__ == "__main__":
    main()
