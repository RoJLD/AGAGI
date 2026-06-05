import pickle
import os
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

HOF_FILE = "data/hall_of_fame.pkl"

def migrate():
    if not os.path.exists(HOF_FILE):
        logging.info("Aucun Hall of Fame a migrer.")
        return

    with open(HOF_FILE, "rb") as f:
        hof = pickle.load(f)

    if len(hof) == 0:
        logging.info("Hall of Fame vide.")
        return

    migrated_hof = []
    
    for score, genome, stats in hof:
        if genome.num_inputs == 23 and genome.num_outputs == 17:
            W = genome.W
            N_old = W.shape[0]
            
            # 1. Insert input at index 23
            W = np.insert(W, 23, 0.0, axis=0)
            W = np.insert(W, 23, 0.0, axis=1)
            
            # 2. Append output at the end
            W = np.append(W, np.zeros((1, W.shape[1])), axis=0)
            W = np.append(W, np.zeros((W.shape[0], 1)), axis=1)
            
            genome.W = W
            genome.num_inputs = 24
            genome.num_outputs = 18
            
            if genome.W_router is not None:
                genome.W_router = np.insert(genome.W_router, 23, 0.0, axis=0)
                
            logging.info(f"Genome migre ! Score: {score}, N_old: {N_old}, N_new: {W.shape[0]}")
            migrated_hof.append((score, genome, stats))
        elif genome.num_inputs == 24 and genome.num_outputs == 18:
            logging.info("Genome deja en V10.")
            migrated_hof.append((score, genome, stats))
        else:
            logging.info(f"Genome de taille inconnue ({genome.num_inputs}x{genome.num_outputs}). Ignore.")
            
    with open(HOF_FILE, "wb") as f:
        pickle.dump(migrated_hof, f)
        
    logging.info("Migration V10 (Zero-Padding) terminee.")

if __name__ == "__main__":
    migrate()
