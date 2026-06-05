import numpy as np
from typing import Tuple

def recurrent_forward(
    genome, 
    obs: np.ndarray, 
    H_prev: np.ndarray, 
    H_history: np.ndarray, 
    H_potentials: np.ndarray,
    env_surprise: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """
    V12 Metacognition Engine (Liquid Mamba + Surprise + Adaptive TTC)
    
    Pilier 1: Signal de Surprise = ||H_t - H_{t-1}||^2 / N
    Pilier 2: Test-Time Compute Adaptatif (T varie avec la surprise)
    Pilier 3: Feedback de lancer injecte via obs (gere par biosphere)
    """
    I = genome.num_inputs
    O = genome.num_outputs
    N = genome.num_nodes
    
    H = H_prev.copy()
    W = genome.W
    
    # Extraction des constantes de temps (Forget Gates) depuis la diagonale
    diag_w = np.clip(np.diagonal(W), -10, 10)
    delta_t = 1.0 / (1.0 + np.exp(-diag_w))  # Sigmoid [0, 1]
    delta_t = delta_t.reshape(1, N)
    
    # W sans diagonale
    W_no_diag = W.copy()
    np.fill_diagonal(W_no_diag, 0.0)
    
    # --- PILIER 1: Signal de Surprise ---
    # Combine surprise interne (delta latent) et surprise environnementale
    internal_surprise = float(np.mean((H - H_prev) ** 2))
    surprise = min(internal_surprise + env_surprise, 1.0)  # Cap a 1.0 pour stabilite
    
    # --- PILIER 2: Test-Time Compute Adaptatif (Macro-NAS MCTS) ---
    has_mcts = getattr(genome, 'organ_genes', None) is not None and genome.organ_genes[0]
    
    if has_mcts:
        # Agent "Penseur" (Cortex activé) : utilise le gène T_micro_ticks et simule l'espace latent
        T_base = int(round(genome.mutation_genes[5]))
        T_base = max(1, T_base)
        T_actual = T_base + int(surprise * 5)  # +5 micro-ticks si tres surpris
        T_actual = min(T_actual, 15)  # Cap absolu a 15
    else:
        # Agent "Réflexe" : pas d'organe MCTS, 1 seule passe rapide
        T_actual = 1
    
    for _ in range(T_actual):
        # 1. Injection sensorielle continue (Grounding)
        H[:, :I] = obs
        
        # 2. Propagation recurrente
        excitation = np.dot(H, W_no_diag)
        
        # 3. Liquid Mamba Update Rule (ODE Step)
        H_new = (1.0 - delta_t) * H + delta_t * np.tanh(excitation)
        H = H_new
        
        # Pilier 1 (Macro-NAS): Neurone Halt (Adaptive Computation Time)
        # L'agent peut décider de s'arrêter de réfléchir si le neurone Halt s'active.
        # On utilise le dernier neurone latent (juste avant les sorties) comme neurone Halt.
        halt_idx = -(O + 1)
        if H.shape[1] > abs(halt_idx) and float(np.mean(H[:, halt_idx])) > 0.5:
            break
            
    # Les sorties sont les O derniers neurones
    preds = H[:, -O:]
    
    return preds, H, H_history, H_potentials, surprise

def recurrent_forward_batch(
    genome, 
    batch_obs: np.ndarray, 
    batch_H_prev: np.ndarray, 
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Version TensorWorld (Batch) de la propagation pour N agents simultanément.
    - batch_obs : (B, I)
    - batch_H_prev : (B, N)
    - return batch_preds (B, O), batch_H_new (B, N), batch_surprise (B,)
    """
    I = genome.num_inputs
    O = genome.num_outputs
    N = genome.num_nodes
    B = batch_obs.shape[0]
    
    H = batch_H_prev.copy()
    W = genome.W
    
    diag_w = np.clip(np.diagonal(W), -10, 10)
    delta_t = 1.0 / (1.0 + np.exp(-diag_w))  # (N,)
    delta_t = delta_t.reshape(1, N) # (1, N) pour broadcasting
    
    W_no_diag = W.copy()
    np.fill_diagonal(W_no_diag, 0.0)
    
    # --- PILIER 1: Surprise (Batch) ---
    surprise = np.mean((H - batch_H_prev) ** 2, axis=1) # (B,)
    surprise = np.clip(surprise, 0.0, 1.0)
    
    # --- PILIER 2: TTC (Macro-NAS MCTS Batch) ---
    has_mcts = getattr(genome, 'organ_genes', None) is not None and genome.organ_genes[0]
    if has_mcts:
        T_base = max(1, int(round(genome.mutation_genes[5]))) if hasattr(genome, 'mutation_genes') else 1
        T_actual = T_base + int(np.max(surprise) * 5)
        T_actual = min(T_actual, 15)
    else:
        T_actual = 1
    
    for _ in range(T_actual):
        H[:, :I] = batch_obs
        excitation = np.dot(H, W_no_diag) # (B, N) x (N, N) -> (B, N)
        H = (1.0 - delta_t) * H + delta_t * np.tanh(excitation)
        
    preds = H[:, -O:]
    return preds, H, surprise

