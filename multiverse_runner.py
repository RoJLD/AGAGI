import os
import sys
import copy
import concurrent.futures
import multiprocessing
import numpy as np

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.seed_ai.persistence import save_to_hall_of_fame, load_hall_of_fame
from src.graph_rag.experiment_tracker import ExperimentGraph

def run_world_era(args):
    world_id, seed_population_genomes, max_ticks = args
    # GARDE D'ARGUMENTS, EN TETE (2026-09-09, 9e elargissement du cliquet -- perimetre RACINE). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte vide
    # ou un horizon nul rend une liste vide que l'aval lit comme une MESURE (biais negatif
    # systematique du depot). Posee AVANT toute construction de monde -> refus instantane.
    if int(max_ticks) <= 0 or not list(seed_population_genomes):
        raise ValueError(
            f"run_world_era : argument degenere (max_ticks={max_ticks}, "
            f"n_genomes={len(list(seed_population_genomes))}) -- aucune mesure possible ; "
            "ne pas confondre avec une ere ou tout le monde meurt.")
    np.random.seed((os.getpid() * int(1e5) + world_id) % (2**31 - 1))
    
    world = Biosphere3D(size=10)
    for genome in seed_population_genomes:
        agent = MambaAgent(num_inputs=genome.num_inputs, num_outputs=genome.num_outputs, num_nodes=96)
        agent.from_genome(genome)
        world.add_agent(agent, energy=100.0)
        
    stats = world.run_era(num_ticks=max_ticks)
    
    results = []
    for s in stats:
        # Transfer the genome explicitly to avoid pickling the entire MambaAgent which might have unpicklable components
        results.append({
            "score": s["score"],
            "genome": copy.deepcopy(s["model"].genome),
            "age": s["age"],
            "preys": s["preys"],
            "energy": s["energy"]
        })
        
    results.sort(key=lambda x: x["score"], reverse=True)
    return world_id, results

def init_primordial_genomes(num_agents=100) -> list:
    print("🧬 Initialisation de la Soupe Primordiale (Génomes)...")
    genomes = []
    
    # ⚠️ CORRIGE le 2026-09-09. Deux defauts du contrat, plus un troisieme qui les rendait
    # invisibles. (1) `load_hall_of_fame()` rend `(version, entries)`, pas une liste : iterer le
    # 2-uplet donnait l'entier de version, d'ou `TypeError: 'int' object is not subscriptable`.
    # (2) une entree est un `AgentSnapshot`, non indexable : `g[1]` echouait aussi. (3) le
    # `except Exception` avalait la TypeError en imprimant « Erreur lors du chargement de KuzuDB »
    # -- un diagnostic FAUX qui envoie chercher le probleme a l'oppose de sa cause, exactement le
    # defaut que la docstring de `load_hall_of_fame` decrit et corrige. Resultat : la soupe partait
    # SANS ancetre, silencieusement, en accusant la base de donnees.
    try:
        _version, entries = load_hall_of_fame()
        valid_hof = [e for e in entries if e.genome.num_inputs == 35]
    except Exception as e:
        print(f"Erreur lors du chargement du Hall of Fame ({type(e).__name__}): {e}")
        valid_hof = []
    
    if valid_hof:
        print(f"🧬 Chargement de {len(valid_hof)} ancêtres compatibles (V14) depuis le Hall of Fame...")
        for _ in range(num_agents):
            parent = valid_hof[np.random.randint(len(valid_hof))].genome
            agent = MambaAgent(num_inputs=35, num_outputs=59, num_nodes=96)
            agent.from_genome(parent)
            agent.mutate()
            genomes.append(agent.genome)
    else:
        print("🌱 Création de nouveaux génomes V14 (35 entrées) from scratch...")
        for _ in range(num_agents):
            agent = MambaAgent(num_inputs=35, num_outputs=59, num_nodes=96)
            genomes.append(agent.genome)
            
    return genomes

def main():
    print("🌍 Démarrage du Multivers AGIseed (Horizontal Gene Transfer)")
    
    try:
        tracker = ExperimentGraph()
        tracker.log_experiment(
            "V13_Multiverse", 
            "V13_Multiverse", 
            ["Multiverse", "Parallelization", "Horizontal Gene Transfer"], 
            "Exécution parallèle de plusieurs mondes et migration des agents."
        )
    except Exception as e:
        print(f"⚠️ Impossible de logger l'expérience: {e}")
    
    num_worlds = 2
    pop_size_per_world = 50
    max_eras = 100
    ticks_per_era = 200
    migration_count = 5
    
    world_populations = []
    for i in range(num_worlds):
        world_populations.append(init_primordial_genomes(pop_size_per_world))
        
    best_score_ever = 0.0
    
    for era in range(1, max_eras + 1):
        print(f"\n🚀 Début de l'Ère {era} dans le Multivers ({num_worlds} mondes parallèles)")
        
        args_list = [
            (i, world_populations[i], ticks_per_era)
            for i in range(num_worlds)
        ]
        
        world_results = {}
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_worlds) as executor:
            for world_id, results in executor.map(run_world_era, args_list):
                world_results[world_id] = results
                
        new_populations = [[] for _ in range(num_worlds)]
        
        for world_id in range(num_worlds):
            stats = world_results[world_id]
            
            alive = sum(1 for s in stats if s["energy"] > 0)
            if len(stats) > 0:
                top_score = stats[0]["score"] if stats else 0
                avg_score = np.mean([s["score"] for s in stats]) if stats else 0
                
                print(f"🌍 Monde {world_id} | Survivants: {alive}/{pop_size_per_world} | Top Score: {top_score:.1f} | Avg: {avg_score:.1f}")
                
                try:
                    speech = stats[0].get("last_spoken", [0.0]*4)
                    cluster_str = f"[{speech[0]:.2f}, {speech[1]:.2f}, {speech[2]:.2f}, {speech[3]:.2f}]"
                    tracker.log_cognitive_state("V13_Multiverse", f"alpha_speech_era{era}_w{world_id}", "speech_vector", cluster_str)
                except Exception as e:
                    pass
                
                if top_score > best_score_ever:
                    best_score_ever = top_score
                    print(f"🏆 NOUVEAU RECORD ABSOLU : {best_score_ever:.1f} (Monde {world_id}) !")
                best_agent_dict = {
                    "age": stats[0]["age"],
                    "preys_eaten": stats[0]["preys"],
                    "altars_solved": 0,
                    "model": MambaAgent(num_inputs=stats[0]["genome"].num_inputs, num_outputs=stats[0]["genome"].num_outputs, num_nodes=96)
                }
                best_agent_dict["model"].from_genome(stats[0]["genome"])
                try:
                    save_to_hall_of_fame(best_agent_dict)
                except Exception as e:
                    print(f"Erreur lors de la sauvegarde dans le Hall of Fame: {e}")
                
            if len(stats) > 0:
                elites = [s["genome"] for s in stats[:5]]
            else:
                elites = [MambaAgent(num_inputs=35, num_outputs=59, num_nodes=96).genome for _ in range(5)]

            for elite in elites:
                new_populations[world_id].append(copy.deepcopy(elite))
                
        print(f"🔄 Migration ({migration_count} meilleurs agents transférés au monde voisin)")
        for world_id in range(num_worlds):
            target_world_id = (world_id + 1) % num_worlds
            stats = world_results[world_id]
            
            if len(stats) > 0:
                migrants = [s["genome"] for s in stats[:migration_count]]
                for migrant in migrants:
                    new_populations[target_world_id].append(copy.deepcopy(migrant))
                    
        for world_id in range(num_worlds):
            parents = copy.deepcopy(new_populations[world_id])
            if not parents:
                parents = [MambaAgent(num_inputs=35, num_outputs=59, num_nodes=96).genome]
                
            while len(new_populations[world_id]) < pop_size_per_world:
                parent_genome = parents[np.random.randint(len(parents))]
                temp_agent = MambaAgent(num_inputs=parent_genome.num_inputs, num_outputs=parent_genome.num_outputs, num_nodes=96)
                temp_agent.from_genome(parent_genome)
                temp_agent.mutate()
                new_populations[world_id].append(temp_agent.genome)
                
            world_populations[world_id] = new_populations[world_id]

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
