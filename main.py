import numpy as np
import logging
from pathlib import Path
from src.graph_rag.database import KuzuDatabase, DatabaseConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.evolution import EvolutionConfig, Population, forward
from src.visualization import (
    genome_to_json,
    plot_evolution_curve,
    render_genome_graphviz,
    save_experiments_dashboard_html,
    save_genome_graphviz_html,
    save_genome_graphviz_svg,
    save_genome_interactive_html,
    save_experiment_history_csv,
    save_experiment_history_json,
    save_experiment_dashboard_html,
    save_genome_topology_txt,
    save_genome_topology_edge_list_csv,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(message)s"
)
logger = logging.getLogger("AGIseed.Supervisor")

def main():
    logger.info("🚀 Démarrage de l'Usine Évolutive AGIseed (Test de tous les opérateurs logiques)")
    
    # --- PHASE 1 : Initialisation de KuzuDB ---
    db_config = DatabaseConfig(db_path="./data/kuzudb/agiseed.db")
    db = KuzuDatabase(db_config)
    db.bootstrap_schema()
    
    # Entrées de la table de vérité (avec Neurone de Biais constant à +1.0)
    X_raw = np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]], dtype=np.float32)
    X = np.c_[X_raw, np.ones(X_raw.shape[0], dtype=np.float32)]
    
    # Définition des 6 portes logiques fondamentales (Ground Truths)
    logic_gates = {
        "AND":  np.array([[-1], [-1], [-1], [ 1]], dtype=np.float32),
        "OR":   np.array([[-1], [ 1], [ 1], [ 1]], dtype=np.float32),
        "NAND": np.array([[ 1], [ 1], [ 1], [-1]], dtype=np.float32),
        "NOR":  np.array([[ 1], [-1], [-1], [-1]], dtype=np.float32),
        "XOR":  np.array([[-1], [ 1], [ 1], [-1]], dtype=np.float32),
        "XNOR": np.array([[ 1], [-1], [-1], [ 1]], dtype=np.float32)
    }
    
    mut_config = MutationConfig(
        weight_mutate_rate=0.8,
        weight_mutate_power=1.0,
        add_node_rate=0.3,
        add_connection_rate=0.5,
        prune_rate=0.1
    )
    
    evo_config = EvolutionConfig(
        pop_size=500,        # Population massive pour forcer l'émergence
        generations=200,     # Nombre de générations
        lambda_penalty=0.0001, # Pénalité TRÈS FAIBLE pour laisser l'innovation (couches cachées) survivre
        survival_rate=0.2
    )

    results_dir = Path("./results")
    results_dir.mkdir(parents=True, exist_ok=True)
    experiments = []

    for gate_name, y in logic_gates.items():
        logger.info(f"\n==================================================")
        logger.info(f"🧠 Défi Évolutif : Apprentissage de la porte {gate_name}")
        logger.info(f"==================================================")
        
        # num_inputs = 3 (A, B, Bias)
        pop = Population(evo_config, mut_config, num_inputs=3, num_outputs=1, db=db)
        best_fitness = -float('inf')
        best_genome = None
        solved_gen = -1

        fitness_history = []
        accuracy_history = []
        size_history = []
        
        for gen in range(1, evo_config.generations + 1):
            fitness, genome = pop.step(X, y)
            fitness_history.append(fitness)
            size_history.append(genome.num_nodes + np.count_nonzero(genome.W))
            
            preds = forward(genome, X)
            preds_rounded = np.sign(preds)
            preds_rounded[preds_rounded == 0] = 1
            accuracy = np.mean(preds_rounded == y)
            accuracy_history.append(accuracy)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_genome = genome
                
            if best_fitness > 0.95:
                solved_gen = gen
                logger.info(f"🏆 {gate_name} parfaitement résolu à la génération {gen} !")
                break
                
        if solved_gen == -1:
            logger.warning(f"❌ Échec de convergence absolue pour {gate_name}. (Fitness max: {best_fitness:.4f})")

        results_csv = save_experiment_history_csv(
            gate_name,
            fitness_history,
            accuracy_history,
            size_history,
            results_dir,
        )
        result_plot = plot_evolution_curve(
            gate_name,
            fitness_history,
            accuracy_history,
            size_history,
            results_dir,
        )
        history_json = save_experiment_history_json(
            gate_name,
            fitness_history,
            accuracy_history,
            size_history,
            results_dir,
        )
        dashboard_html = save_experiment_dashboard_html(
            gate_name,
            best_genome,
            fitness_history,
            accuracy_history,
            size_history,
            results_dir,
        )
        experiments.append({
            "gate": gate_name,
            "history": {
                "generation": list(range(1, len(fitness_history) + 1)),
                "fitness": fitness_history,
                "accuracy": accuracy_history,
                "size": size_history,
            },
            "graph": genome_to_json(best_genome),
        })
        topology_txt = save_genome_topology_txt(gate_name, best_genome, results_dir)
        topology_edges = save_genome_topology_edge_list_csv(gate_name, best_genome, results_dir)
        graphviz_image = render_genome_graphviz(gate_name, best_genome, results_dir)
        graphviz_svg = save_genome_graphviz_svg(gate_name, best_genome, results_dir)
        graphviz_html = save_genome_graphviz_html(gate_name, best_genome, results_dir)
        interactive_html = save_genome_interactive_html(gate_name, best_genome, results_dir)

        logger.info(f"📈 Résultats enregistrés : {results_csv}")
        logger.info(f"📊 Visualisation enregistrée : {result_plot}")
        logger.info(f"🗄️ Historique JSON : {history_json}")
        logger.info(f"🌐 Tableau de bord HTML : {dashboard_html}")
        logger.info(f"🧩 Topologie du meilleur modèle : {topology_txt}")
        logger.info(f"🗂️ Liste d'arêtes enregistrée : {topology_edges}")
        logger.info(f"🖼️ Graphique du graphe enregistré : {graphviz_image}")
        logger.info(f"🖼️ SVG interactif généré : {graphviz_svg}")
        logger.info(f"🌐 Page HTML interactive Graphviz : {graphviz_html}")
        logger.info(f"🌐 Page HTML interactive D3 : {interactive_html}")

        # Test final et évaluation de la précision sur le meilleur génome global
        preds = forward(best_genome, X)
        preds_rounded = np.sign(preds)
        preds_rounded[preds_rounded == 0] = 1 # Gestion des zéros stricts
        accuracy = np.mean(preds_rounded == y)
        
        logger.info(f"📊 Bilan {gate_name} -> Précision finale de l'Essaim : {accuracy * 100:.2f}%")

    dashboard_overview = save_experiments_dashboard_html(experiments, results_dir)
    logger.info(f"🌐 Tableau de bord global évolutif : {dashboard_overview}")

if __name__ == "__main__":
    main()
