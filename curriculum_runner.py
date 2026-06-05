import os
import sys
import time
import json
import subprocess
import logging
import itertools

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [AutoExplorer] %(message)s")
logger = logging.getLogger("AutoExplorer")

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "curriculum_state.json")

def get_historical_best_agent(world_type: str, keep_memory: str):
    import kuzu
    try:
        db_path = os.path.join(os.path.dirname(__file__), "data", "kuzu_graph.db")
        db = kuzu.Database(db_path, read_only=True)
        conn = kuzu.Connection(db)
        
        trait = "NTM_Memory" if keep_memory == "1" else "Tabula_Rasa"
        
        query = f"""
        MATCH (w:WorldVersion {{name: '{world_type}'}})<-[:RAN_IN_WORLD]-(e:Experiment)-[:CREATED_SPECIES]->(s:Species), 
              (e)-[:YIELDED_RESULT]->(r:Result)-[:YIELDED_BEST_AGENT]->(a:Agent)
        WHERE s.traits CONTAINS '{trait}'
        RETURN a.id, r.max_score
        ORDER BY r.max_score DESC LIMIT 1
        """
        res = conn.execute(query)
        if res.has_next():
            row = res.get_next()
            return row[0], row[1]
    except Exception as e:
        logger.error(f"Error querying historical best agent for {world_type} / {trait}: {e}")
        
    return None, 0.0

def check_if_already_explored(world_type: str, keep_memory: str, experiment_version: str):
    import kuzu
    try:
        db_path = os.path.join(os.path.dirname(__file__), "data", "kuzu_graph.db")
        db = kuzu.Database(db_path, read_only=True)
        conn = kuzu.Connection(db)
        
        trait = "NTM_Memory" if keep_memory == "1" else "Tabula_Rasa"
        
        query = f"""
        MATCH (w:WorldVersion {{name: '{world_type}'}})<-[:RAN_IN_WORLD]-(e:Experiment {{name: '{experiment_version}'}})-[:CREATED_SPECIES]->(s:Species),
              (e)-[:YIELDED_RESULT]->(r:Result)-[:YIELDED_BEST_AGENT]->(a:Agent)
        WHERE s.traits CONTAINS '{trait}'
        RETURN a.id, r.max_score
        LIMIT 1
        """
        res = conn.execute(query)
        if res.has_next():
            row = res.get_next()
            return row[0], row[1]
    except Exception as e:
        pass
    return None, None

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lecture state : {e}")
    return {"current_step": 0, "best_agent_id": None}

def save_state(step_index: int, best_agent_id: str):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"current_step": step_index, "best_agent_id": best_agent_id}, f, indent=4)

def generate_curriculum():
    worlds = ["stoneage", "agricultural"]
    memory_states = ["0", "1"]
    
    # Generate all combinations in a specific progression order
    # Here we just iterate worlds then memory
    curriculum = []
    idx = 1
    for w in worlds:
        for m in memory_states:
            mem_label = "NTM_Memory" if m == "1" else "Tabula_Rasa"
            curriculum.append({
                "world": w,
                "keep_memory": m,
                "name": f"Phase {idx}: {w.capitalize()} + {mem_label}"
            })
            idx += 1
    return curriculum

def main():
    logger.info("🌍 Démarrage du Superviseur Méta-Evolutif (Auto-Explorer)")
    
    curriculum = generate_curriculum()
    total_steps = len(curriculum)
    
    state = load_state()
    current_step = state["current_step"]
    best_agent_id = state["best_agent_id"]
    
    if current_step >= total_steps:
        logger.info("✅ Curriculum déjà complété ! (Utilise 'Reset Curriculum' depuis l'UI pour recommencer)")
        return
        
    # Estimations
    steps_left = total_steps - current_step
    estimated_time_per_run_min = 3 # Hardcoded avg estimate
    logger.info(f"📊 Espace de recherche : {total_steps} combinaisons.")
    logger.info(f"⏳ Restant : {steps_left} runs (~{steps_left * estimated_time_per_run_min} minutes).")
    
    resource_limit = os.getenv("RESOURCE_LIMIT", "4")
    batch_size_str = os.getenv("BATCH_SIZE", "0")
    batch_size = int(batch_size_str) if batch_size_str.isdigit() else 0
    if batch_size <= 0:
        batch_size = steps_left # Runs until completion if 0
        
    logger.info(f"⚙️ Paramètres : CPU Threads = {resource_limit} | Batch Size = {batch_size}")

    runs_completed_in_batch = 0

    while current_step < total_steps and runs_completed_in_batch < batch_size:
        step = curriculum[current_step]
        logger.info(f"\n=======================================================")
        logger.info(f"🚀 [Run {current_step+1}/{total_steps}] Démarrage de {step['name']}")
        logger.info(f"=======================================================")
        
        env = os.environ.copy()
        env["WORLD_TYPE"] = step["world"]
        env["KEEP_MEMORY"] = step["keep_memory"]
        env["OMP_NUM_THREADS"] = resource_limit
        env["MKL_NUM_THREADS"] = resource_limit
        
        experiment_version = "V16_Language_Guided"
        env["EXPERIMENT_VERSION"] = experiment_version
        
        cached_agent_id, cached_score = check_if_already_explored(step["world"], step["keep_memory"], experiment_version)
        if cached_agent_id:
            logger.info(f"⏭️ Combinaison déjà explorée pour la version {experiment_version} ! Cache Hit trouvé : {cached_agent_id} (Score: {cached_score:.1f})")
            logger.info(f"⏭️ Phase sautée pour économiser du CPU.")
            best_agent_id = cached_agent_id
            current_step += 1
            # On ne compte pas ça comme un run consommé dans le batch s'il est instantané
            save_state(current_step, best_agent_id)
            continue
            
        if best_agent_id:
            logger.info(f"🧬 Importation du champion précédent : {best_agent_id}")
            env["IMPORT_AGENT_ID"] = best_agent_id
        else:
            logger.info(f"🌱 Soupe primordiale (Génération Spontanée)")
            
        start_time = time.time()
        
        process = None
        try:
            process = subprocess.Popen(
                [sys.executable, "main_biosphere.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            for line in iter(process.stdout.readline, ""):
                print(line, end="")
                
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                logger.warning(f"⚠️ main_biosphere.py s'est terminé avec le code {return_code}")
                
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt manuel de l'explorateur.")
            if process:
                process.terminate()
            break
            
        new_best_id, score = get_historical_best_agent(step["world"], step["keep_memory"])
        if new_best_id:
            logger.info(f"🏆 Nouveau champion historique trouvé pour {step['world']} : {new_best_id} (Score: {score:.1f})")
            best_agent_id = new_best_id
        else:
            logger.warning("❌ Aucun champion historique trouvé dans cette configuration. L'exploration continue sans transfert.")
            
        # Update State
        current_step += 1
        runs_completed_in_batch += 1
        save_state(current_step, best_agent_id)
        
        time.sleep(2)
        
    if current_step >= total_steps:
        logger.info("🏁 Curriculum totalement terminé avec succès !")
    else:
        logger.info(f"⏸️ Batch terminé ({runs_completed_in_batch} runs). L'explorateur est en pause. Relance pour continuer.")

if __name__ == "__main__":
    main()
