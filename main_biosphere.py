import numpy as np
import logging
import time
import os

from src.seed_ai.evolution import EvolutionConfig
from src.seed_ai.mutation import MutationConfig, Genome, apply_mutations
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_2_agricultural import AgriculturalWorld
from src.worlds.world_3_industrial import IndustrialWorld
from src.environments.config import WorldConfig
from src.seed_ai.persistence import load_hall_of_fame
from src.graph_rag.experiment_tracker import ExperimentGraph
from src.agents.mamba_agent import MambaAgent
from src.graph_rag.async_logger import logger as async_logger
import json

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AGIseed.Biosphere")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def init_primordial_soup(num_agents=50, import_agent_id=None, keep_memory=False, shared_db=None):
    mut_config = MutationConfig(weight_init_std=2.0)
    config = WorldConfig()
    num_inputs = config.agent.num_inputs
    num_outputs = config.agent.num_outputs
    
    genomes = []
    
    # IMPORT FROM KUZUDB (Meta-Learning)
    if import_agent_id and shared_db:
        logger.info(f"👽 Transfert Interdimensionnel : Import de l'Agent {import_agent_id}...")
        try:
            import kuzu
            conn = kuzu.Connection(shared_db)
            res = conn.execute(f"MATCH (s:CognitiveSnapshot {{agent_id: '{import_agent_id}'}}) RETURN s.w_connectome, s.ntm_memory ORDER BY s.tick DESC LIMIT 1")
            if res.has_next():
                row = res.get_next()
                imported_W = np.array(json.loads(row[0]))
                imported_ntm = np.array(json.loads(row[1])) if len(row) > 1 and row[1] else None
                
                logger.info(f"🧬 Connectome W extrait ! Clonage pour {num_agents} agents...")
                # We clone this exact connectome for the whole population with slight mutations
                for _ in range(num_agents):
                    N = num_inputs + num_outputs + 5
                    
                    # --- NEURO-SURGERY (HGT Concept Drift) ---
                    current_W = imported_W.copy()
                    old_N = current_W.shape[0]
                    if old_N != N:
                        if _ == 0: # Log only once
                            logger.warning(f"⚠️ Différence de dimension du cerveau (Ancien: {old_N}x{old_N}, Nouveau: {N}x{N}). Application de la Neuro-Chirurgie !")
                        new_W = np.zeros((N, N))
                        min_N = min(old_N, N)
                        # We copy the top-left block (which aligns inputs to inputs, assuming inputs are added at the end)
                        # If inputs were inserted in the middle, it would be more complex, but here we assume append.
                        new_W[:min_N, :min_N] = current_W[:min_N, :min_N]
                        current_W = new_W
                    
                    mut_genes = np.array([mut_config.weight_mutate_rate, mut_config.weight_mutate_power, mut_config.add_node_rate, mut_config.add_connection_rate, mut_config.prune_rate, 3.0])
                    W_router = np.random.normal(0, mut_config.weight_init_std, size=(num_inputs, 3))
                    bytecode = np.array([0, 1, 2, 4, 3], dtype=int)
                    thresholds = np.random.rand(N) * 0.2
                    g = Genome(current_W, num_inputs, num_outputs, mut_genes, W_router, bytecode, thresholds)
                    genomes.append(g)
                    
                # We return early since we filled the population
                return genomes, imported_ntm if keep_memory else None
            else:
                logger.error(f"❌ Impossible de trouver l'agent {import_agent_id} dans KuzuDB. Fallback à Tabula Rasa.")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'import : {e}")

    version, hof_list = load_hall_of_fame()
    valid_hof = []
    
    for entry in hof_list:
        if isinstance(entry, tuple):
            valid_hof.append(entry)
        else:
            valid_hof.append((entry.score, entry.genome, entry.stats))
            
    if len(valid_hof) > 0:
        logger.info(f"🧬 Chargement de {len(valid_hof)} ancêtres depuis le Hall of Fame...")
        for score, genome, stats in valid_hof:
            genomes.append(genome)
            # Remplir le reste avec des mutations des champions
            while len(genomes) < num_agents and np.random.rand() < 0.2:
                import copy
                child = apply_mutations(copy.deepcopy(genome), mut_config)
                genomes.append(child)
    else:
        logger.info("⚠️ Aucun ancêtre trouvé. Tabula Rasa !")
                
    # Compléter avec de l'aléatoire pur si besoin
    while len(genomes) < num_agents:
        N = num_inputs + num_outputs + 5
        W = np.zeros((N, N))
        
        mut_genes = np.array([
            mut_config.weight_mutate_rate,
            mut_config.weight_mutate_power,
            mut_config.add_node_rate,
            mut_config.add_connection_rate,
            mut_config.prune_rate,
            3.0 # T_micro_ticks par défaut
        ])
        
        W_router = np.random.normal(0, mut_config.weight_init_std, size=(num_inputs, 3))
        bytecode = np.array([0, 1, 2, 4, 3], dtype=int)
        thresholds = np.random.rand(N) * 0.2
        
        genomes.append(Genome(W, num_inputs, num_outputs, mut_genes, W_router, bytecode, thresholds))
        
    return genomes, None

def main():
    logger.info("🦠 Démarrage de la Swarm Biosphere (EXP-8 : Learning Inventory & Language)")
    
    # Démarrer le logger global et partager sa base KuzuDB
    async_logger.start()
    
    # Attendre que la DB Kuzu soit initialisée dans le thread worker
    shared_db = None
    for _ in range(50):
        shared_db = async_logger.get_db()
        if shared_db is not None:
            break
        time.sleep(0.1)
        
    if shared_db is None:
        logger.error("Impossible de récupérer la base KuzuDB depuis async_logger.")
        return
        
    # Log initial
    tracker = ExperimentGraph(db=shared_db)
    experiment_version = os.getenv("EXPERIMENT_VERSION", "V16_Language_Guided")
    tracker.log_experiment(
        version=experiment_version, 
        parent_version="V16_Language_Inventaire", 
        capabilities=["Crafting_Friction", "Fire", "Inventory_Penalty", "Language_Alignment_Reward", "Ballistic_Physics"],
        description="EXP-8 : Version Guidée. Micro-récompenses (+0.5) pour alignement vocal et seuil MCTS réduit."
    )
    
    world_type = os.getenv("WORLD_TYPE", "stoneage")
    import_agent_id = os.getenv("IMPORT_AGENT_ID", None)
    keep_memory = os.getenv("KEEP_MEMORY", "0") == "1"
    
    config = WorldConfig()
    os.environ["ACTIVE_EXP_VARIABLE"] = config.active_exp_variable
    
    logger.info(f"🌍 Monde sélectionné : {world_type.upper()}")
    
    # Define species traits based on version capabilities
    traits = ["NTM_Memory" if keep_memory else "Tabula_Rasa", "Language_Enabled" if "Language_Alignment_Reward" in ["Crafting_Friction", "Fire", "Inventory_Penalty", "Language_Alignment_Reward", "Ballistic_Physics"] else "No_Language"]
    
    # Log the World and Species configuration to the graph tracker
    tracker = ExperimentGraph(db=shared_db)
    tracker.log_world_and_species(
        version=experiment_version,
        world_type=world_type,
        species_name="Homo_Linguisticus", # Example name, can be dynamic later
        traits=traits
    )
    
    mutation_rate = os.getenv("MUTATION_RATE", "0.05")
    tracker.log_hyperparameters(
        version=experiment_version,
        params={
            "mutation_rate": float(mutation_rate),
            "resource_limit": int(os.getenv("RESOURCE_LIMIT", "4"))
        }
    )
    
    del tracker
    
    config = WorldConfig()
    generation_auto = 1
    MAX_ERAS = 30
    
    while generation_auto <= MAX_ERAS:
        # Instantiate the requested World
        if world_type == "agricultural":
            env = AgriculturalWorld(size=config.world.grid_size, num_agents=config.world.num_agents)
        elif world_type == "industrial":
            env = IndustrialWorld(size=config.world.grid_size, num_agents=config.world.num_agents)
        else:
            env = Biosphere3D(size=config.world.grid_size, num_agents=config.world.num_agents)

        primordial_genomes, imported_ntm = init_primordial_soup(
            num_agents=100,
            import_agent_id=import_agent_id if generation_auto == 1 else None, # Only import on first era
            keep_memory=keep_memory,
            shared_db=shared_db
        )
        
        for g in primordial_genomes:
            agent = MambaAgent()
            agent.from_genome(g)
            if imported_ntm is not None:
                agent.ntm_memory = imported_ntm.copy()
            env.add_agent(agent, energy=50.0)
            
        logger.info(f"🚀 Début de l'Ère {generation_auto} / {MAX_ERAS}...")
        time.sleep(1)
        
        env.current_era = generation_auto
        while len(env.agents) > 0:
            clear_screen()
            env.render()
            
            max_energy = max([a["energy"] for a in env.agents])
            mean_energy = np.mean([a["energy"] for a in env.agents])
            mean_surprise = np.mean([a.get("last_surprise", 0.0) for a in env.agents])
            mean_doubt = np.mean([a.get("last_entropy", 0.0) for a in env.agents])
            
            print(f"[!] Énergie Max: {max_energy:.1f} | Énergie Moyenne: {mean_energy:.1f}")
            print(f"[META] Metacognition -> Surprise Moy: {mean_surprise:.2f} | Doute Moy: {mean_doubt:.2f}")
            print(f"[i] ERE {generation_auto}")
            
            if env.ticks % 10 == 0:
                os.makedirs("results", exist_ok=True)
                file_path = "results/metacognition_logs.csv"
                write_header = not os.path.exists(file_path)
                with open(file_path, "a", encoding="utf-8") as f:
                    if write_header:
                        f.write("era,tick,mean_energy,mean_surprise,mean_doubt\n")
                    f.write(f"{generation_auto},{env.ticks},{mean_energy:.2f},{mean_surprise:.4f},{mean_doubt:.4f}\n")
            
            if env.ticks % 10 == 0 and len(env.agents) > 0:
                # Snapshot the best agent
                best_agent = max(env.agents, key=lambda a: a["energy"])
                try:
                    import json
                    async_logger.emit("COGNITIVE_SNAPSHOT", {
                        "agent_id": best_agent["id"][:8],
                        "tick": env.ticks,
                        "ntm_memory": json.dumps(best_agent["brain"].ntm_memory.tolist() if hasattr(best_agent["brain"], "ntm_memory") else []),
                        "attention_mask": json.dumps(best_agent["brain"].attention_mask.tolist() if hasattr(best_agent["brain"], "attention_mask") else []),
                        "w_connectome": json.dumps(best_agent["brain"].genome.W.tolist())
                    })
                except Exception as e:
                    pass

            # --- GOD MODE: Interventions ---
            intervention_file = "data/interventions.json"
            if os.path.exists(intervention_file):
                try:
                    with open(intervention_file, "r") as f:
                        interventions = json.load(f)
                    os.remove(intervention_file)
                    for inv in interventions:
                        action = inv.get("action")
                        logger.info(f"⚡ INTERVENTION DIVINE : {action.upper()}")
                        if action == "spawn_food":
                            for _ in range(20):
                                env.spawn_food()
                        elif action == "kill_half":
                            half = len(env.agents) // 2
                            env.agents = env.agents[:half]
                        elif action == "trigger_famine":
                            # Delete 90% of food
                            if hasattr(env, 'food_positions'):
                                num_keep = max(1, len(env.food_positions) // 10)
                                env.food_positions = env.food_positions[:num_keep]
                        elif action == "spawn_predator":
                            # Spawn an agent with max energy and huge mutation
                            if len(env.agents) > 0:
                                predator = apply_mutations(env.agents[0]["genome"], MutationConfig(weight_mutate_rate=0.9))
                                agent = MambaAgent()
                                agent.from_genome(predator)
                                env.add_agent(agent, energy=200.0)
                        elif action == "climate_change":
                            # Randomize environment positions or kill food
                            if hasattr(env, 'food_positions'):
                                env.food_positions.clear()
                            env.current_era += 1 # symbolic
                except Exception as e:
                    logger.error(f"Erreur intervention: {e}")

            env.step()
            
            # --- Meta-NAS: Horizontal Gene Transfer (HGT) ---
            if env.ticks % 5 == 0 and len(env.agents) > 1:
                # Tous les 5 ticks, on vérifie si des agents performants peuvent transférer des gènes
                for i in range(len(env.agents)):
                    for j in range(i + 1, len(env.agents)):
                        a1 = env.agents[i]
                        a2 = env.agents[j]
                        # Proximité spatiale (distance de Manhattan)
                        dist = abs(a1["x"] - a2["x"]) + abs(a1["y"] - a2["y"])
                        if dist <= 2:
                            # Contact social : on regarde qui est le "professeur" (fort delta d'énergie)
                            if a1["energy"] > a2["energy"] * 1.5:
                                prof, eleve = a1, a2
                            elif a2["energy"] > a1["energy"] * 1.5:
                                prof, eleve = a2, a1
                            else:
                                continue
                            
                            # Probabilité de transfert de gène HGT
                            if np.random.rand() < 0.1: # 10% chance
                                # Meta-NAS: l'élève copie un sous-ensemble des poids ou des organes du professeur
                                if np.random.rand() < 0.5 and getattr(prof["brain"].genome, 'organ_genes', None) is not None:
                                    # Transfert d'organes (Macro)
                                    eleve["brain"].genome.organ_genes = prof["brain"].genome.organ_genes.copy()
                                    logger.info(f"[META-NAS HGT] Agent {prof['id'][:4]} a transféré ses Organes à l'Agent {eleve['id'][:4]}")
                                else:
                                    # Transfert d'un motif de poids (Meso/Micro)
                                    # On copie la matrice de poids sur les couches profondes (les concepts)
                                    N = prof["brain"].genome.num_nodes
                                    half_N = N // 2
                                    eleve["brain"].genome.W[half_N:, half_N:] = prof["brain"].genome.W[half_N:, half_N:].copy()
                                    logger.info(f"[META-NAS HGT] Agent {prof['id'][:4]} a transféré son Cerveau Profond à l'Agent {eleve['id'][:4]}")
                                    
            # --- State Sync for Canvas UI ---
            if env.ticks % 2 == 0:
                try:
                    state_data = {
                        "size": env.size,
                        "is_night": getattr(env, "is_night", False),
                        "agents": [{"x": a["x"], "y": a["y"], "energy": a["energy"], "id": str(a["id"])} for a in env.agents],
                        "items": [{"x": it["x"], "y": it["y"], "type": it.get("type", "unknown")} for it in env.items],
                        "preys": [{"x": p["x"], "y": p["y"], "type": p["type"]} for p in env.preys],
                        "trees": [{"x": t[0], "y": t[1]} for t in env.trees]
                    }
                    os.makedirs("data", exist_ok=True)
                    with open("data/state.json", "w") as f:
                        json.dump(state_data, f)
                except Exception as e:
                    logger.error(f"Erreur d'export state.json: {e}")

            # Fast forward in headless mode: removed time.sleep(0.05) to speed up 30 eras.
            
        if hasattr(env, 'memory_retriever'):
            env.memory_retriever.stop()
        
        best_agent_ever_id = best_agent["id"][:8] if "best_agent" in locals() else None
        # Route le log des résultats d'ère via l'AsyncLogger (single writer thread)
        # Cela évite l'erreur "Only one write transaction at a time"
        async_logger.emit_sync("ERA_RESULT", {
            "version": experiment_version,
            "max_score": float(max_energy),
            "mean_score": float(mean_energy),
            "ticks": int(env.ticks),
            "best_agent_id": best_agent_ever_id
        }, timeout=15.0)
        
        if hasattr(env, 'memory_retriever'):
            env.memory_retriever.start()
            
        clear_screen()
        env.render()
        logger.info(f"💀 EXTINCTION TOTALE de l'Ère {generation_auto}. Les meilleurs ont été sauvegardés. Redémarrage Seed AI...")
        generation_auto += 1
        
    logger.info("✅ 30 Ères complétées (Protocole d'Innovation Unitaire terminé).")
    async_logger.stop()

if __name__ == "__main__":
    main()
