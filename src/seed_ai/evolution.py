import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from .mutation import Genome, MutationConfig, apply_mutations

@dataclass
class EvolutionConfig:
    pop_size: int = 100
    generations: int = 50
    lambda_penalty: float = 0.01
    survival_rate: float = 0.2
    local_epochs: int = 10
    learning_rate: float = 0.1
    tournament_size: int = 3
    # New fields for V5 Router, V6 Bytecode and KuzuDB synchronization
    num_recurrent_steps: int = 3          # Number of recurrent state update steps
    bytecode_mapping: str = "per_node"    # How to map bytecode to operations: "per_node", "per_layer", "global"
    kzu_sync_interval: int = 1            # Synchronize with KuzuDB every N generations (1 = every generation)

def forward(genome: Genome, X: np.ndarray, config=None) -> np.ndarray:
    """
    Forward pass supporting V5 Router (recurrent state), V6 Bytecode (operation selection),
    and V6 memory cache (Read operation). If config is None, uses default values.
    X: shape (batch_size, num_inputs)
    Returns: shape (batch_size, num_outputs)
    """
    # Default config values if not provided
    if config is None:
        num_recurrent_steps = 3
        bytecode_mapping = "per_node"
    else:
        num_recurrent_steps = getattr(config, 'num_recurrent_steps', 3)
        bytecode_mapping = getattr(config, 'bytecode_mapping', "per_node")

    B = X.shape[0]
    N = genome.num_nodes
    I = genome.num_inputs
    O = genome.num_outputs

    # State array (includes inputs, hidden, outputs)
    H = np.zeros((B, N))
    H[:, :I] = X  # Clamp inputs at start

    for _ in range(num_recurrent_steps):
        # --- V5 Router: recurrent update ---
        if genome.W_router is not None and I > 0:
            # Use current input portion of state to compute recurrent update
            recurrent_input = H[:, :I]  # shape (B, I)
            recurrent_update = np.tanh(recurrent_input @ genome.W_router)  # (B, 3)
            # Add recurrent update to the first min(3, N-I) hidden nodes (if any)
            if N > I:
                update_len = min(3, N - I)
                H[:, I:I+update_len] += recurrent_update[:, :update_len]
        # --- Forward pass for this recurrent step ---
        for j in range(I, N):
            z = H[:, :j] @ genome.W[:j, j]
            # Determine operation from bytecode
            op = 0  # default: linear
            if genome.bytecode is not None and len(genome.bytecode) > 0:
                if bytecode_mapping == "per_node":
                    op = int(genome.bytecode[j % len(genome.bytecode)])
                elif bytecode_mapping == "per_layer":
                    # For simplicity, fall back to per_node (layer detection would require topological depth)
                    op = int(genome.bytecode[j % len(genome.bytecode)])
                else:  # "global"
                    op = int(genome.bytecode[0])
            # Apply operation
            if op == 0:   # Linear
                h_j = z
            elif op == 1: # ReLU
                h_j = np.maximum(0, z)
            elif op == 2: # Sigmoid
                h_j = 1 / (1 + np.exp(-np.clip(z, -500, 500)))
            elif op == 3: # Write (memory) - identity, no change to h_j
                h_j = z
            elif op == 4: # Read from memory cache
                if genome.memory_cache is not None and j < len(genome.memory_cache):
                    h_j = genome.memory_cache[j]
                else:
                    h_j = z
            else:
                h_j = z  # unknown op defaults to linear
            H[:, j] = h_j
        # --- Clamp memory cache values to [0,1] for stability (if used) ---
        if genome.memory_cache is not None:
            genome.memory_cache = np.clip(genome.memory_cache, 0.0, 1.0)
        # Re-clamp input nodes for next recurrent step (prevent overwriting)
        H[:, :I] = X
    # Return output nodes
    return H[:, -O:]

def local_train(genome: Genome, X: np.ndarray, y: np.ndarray, config: EvolutionConfig) -> None:
    """Lamarckian evolution: local gradient descent (SGD) on the genome's weights."""
    if config.local_epochs <= 0:
        return
        
    B = X.shape[0]
    N = genome.num_nodes
    I = genome.num_inputs
    O = genome.num_outputs
    
    for epoch in range(config.local_epochs):
        # --- FORWARD PASS ---
        H = np.zeros((B, N))
        H[:, :I] = X
        
        for j in range(I, N):
            z = H[:, :j] @ genome.W[:j, j]
            H[:, j] = np.tanh(z)
            
        # --- LOSS & INITIAL GRADIENTS ---
        diff = H[:, -O:] - y
        dH = np.zeros((B, N))
        dH[:, -O:] = (2.0 / (B * O)) * diff
        
        dW = np.zeros_like(genome.W)
        
        # --- BACKWARD PASS ---
        for j in range(N - 1, I - 1, -1):
            if not np.any(genome.W[:j, j]):
                continue # Skip if no incoming connections
                
            # Derivative of tanh(x) is 1 - tanh(x)^2
            dz = dH[:, j] * (1.0 - H[:, j]**2)
            
            # Gradient w.r.t weights
            dW[:j, j] = H[:, :j].T @ dz
            
            # Propagate gradient to previous nodes (H)
            dH[:, :j] += np.outer(dz, genome.W[:j, j])
            
        # --- OPTIMIZATION (SGD + Clipping) ---
        np.clip(dW, -1.0, 1.0, out=dW) # Commandement 9: Numerical Stability
        
        # Update only existing connections (preserve graph topology)
        mask = genome.W != 0
        genome.W[mask] -= config.learning_rate * dW[mask]

def calculate_fitness(genome: Genome, X: np.ndarray, y: np.ndarray, config: EvolutionConfig) -> float:
    preds = forward(genome, X, config)

    mse = np.mean((preds - y)**2)
    acc = 1.0 - mse

    size = genome.num_nodes + np.count_nonzero(genome.W)
    score = acc - config.lambda_penalty * size

    if np.isnan(score) or np.isinf(score):
        return -1e9

    return score

def tournament_selection(population: List[Genome], fitnesses: List[float], tournament_size: int = 3) -> int:
    """
    Select an individual using tournament selection.
    
    Args:
        population: List of genomes
        fitnesses: List of fitness values (same order as population)
        tournament_size: Number of individuals in each tournament
        
    Returns:
        Index of the winning individual in the population
    """
    indices = np.random.choice(len(population), tournament_size, replace=False)
    best_idx = indices[0]
    for i in indices[1:]:
        if fitnesses[i] > fitnesses[best_idx]:
            best_idx = i
    return best_idx

def crossover(p1: Genome, p2: Genome, fitness1: float, fitness2: float, seed: int = None) -> Genome:
    """
    Uniform genetic crossover preserving graph topology.
    
    For each existing connection:
    - Uniformly select weight from p1 or p2 (50/50)
    - If connection exists in only one parent, inherit from that parent
    - Handles different sizes by using minimum dimensions
    - Mutation genes are crossed over with random mask
    - All existing connections are preserved (no topology destruction)
    
    Args:
        p1, p2: Parent genomes
        fitness1, fitness2: Parent fitness values
        seed: Optional random seed for deterministic crossover
        
    Returns:
        Child genome
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Base parent is the fitter one (structural inheritance)
    fitter = p1 if fitness1 > fitness2 else p2
    child = fitter.clone()
    
    # === Hyper-Genetic Crossover: mutation genes ===
    gene_mask = np.random.rand(len(fitter.mutation_genes)) > 0.5
    child.mutation_genes = np.where(gene_mask, p1.mutation_genes, p2.mutation_genes)
    
    # === Weight Matrix Crossover (preserving topology) ===
    min_N = min(p1.W.shape[0], p2.W.shape[0])
    if min_N > 0:
        # Extract submatrices of minimum size
        W1 = p1.W[:min_N, :min_N]
        W2 = p2.W[:min_N, :min_N]
        
        # Connections existing in both parents: uniform crossover
        both_mask = (W1 != 0) & (W2 != 0)
        if np.any(both_mask):
            choice_mask = np.random.rand(min_N, min_N) > 0.5
            child.W[:min_N, :min_N][both_mask] = np.where(
                choice_mask[both_mask],
                W1[both_mask],
                W2[both_mask]
            )
        
        # Connections existing only in p1: inherit from p1
        only_p1_mask = (W1 != 0) & (W2 == 0)
        if np.any(only_p1_mask):
            child.W[:min_N, :min_N][only_p1_mask] = W1[only_p1_mask]
        
        # Connections existing only in p2: inherit from p2
        only_p2_mask = (W1 == 0) & (W2 != 0)
        if np.any(only_p2_mask):
            child.W[:min_N, :min_N][only_p2_mask] = W2[only_p2_mask]
    
    # === W_router Crossover ===
    if p1.W_router is not None and p2.W_router is not None:
        min_rows = min(p1.W_router.shape[0], p2.W_router.shape[0])
        min_cols = min(p1.W_router.shape[1], p2.W_router.shape[1])
        if min_rows > 0 and min_cols > 0:
            W1r = p1.W_router[:min_rows, :min_cols]
            W2r = p2.W_router[:min_rows, :min_cols]
            choice_mask = np.random.rand(min_rows, min_cols) > 0.5
            child.W_router = np.where(choice_mask, W1r, W2r)
    
    # === Bytecode Crossover ===
    if p1.bytecode is not None and p2.bytecode is not None:
        min_len = min(len(p1.bytecode), len(p2.bytecode))
        if min_len > 0:
            bc1 = p1.bytecode[:min_len]
            bc2 = p2.bytecode[:min_len]
            choice_mask = np.random.rand(min_len) > 0.5
            child.bytecode = np.where(choice_mask, bc1, bc2).astype(int)
    
    # === Thresholds Crossover ===
    if p1.thresholds is not None and p2.thresholds is not None:
        min_len = min(len(p1.thresholds), len(p2.thresholds))
        if min_len > 0:
            th1 = p1.thresholds[:min_len]
            th2 = p2.thresholds[:min_len]
            choice_mask = np.random.rand(min_len) > 0.5
            child.thresholds = np.where(choice_mask, th1, th2)
    
    # Restore random state
    if seed is not None:
        np.random.seed(None)
    
    return child

class Population:
    def __init__(self, config: EvolutionConfig, mut_config: MutationConfig, num_inputs: int, num_outputs: int, db=None):
        self.config = config
        self.mut_config = mut_config
        self.db = db
        self.genomes: List[Genome] = []
        self.generation = 0  # Track current generation

        for _ in range(config.pop_size):
            N = num_inputs + num_outputs
            W = np.zeros((N, N))
            for i in range(num_inputs):
                for j in range(num_inputs, N):
                    W[i, j] = np.random.normal(mut_config.weight_init_mean, mut_config.weight_init_std)

            # Init V5 Router: 3 Memory Channels
            W_router = np.random.normal(0, mut_config.weight_init_std, size=(num_inputs, 3))

            # Init V6 Bytecode & Thresholds
            bytecode = np.array([0, 1, 2, 4, 3], dtype=int)
            thresholds = np.random.rand(N) * 0.2 # Faibles seuils pour commencer

            # Init V6 memory cache
            memory_cache = np.zeros(N, dtype=np.float32)

            self.genomes.append(Genome(W, num_inputs, num_outputs, W_router=W_router, bytecode=bytecode, thresholds=thresholds, memory_cache=memory_cache))
            
    def step(self, X: np.ndarray, y: np.ndarray) -> Tuple[float, Genome]:
        # Lamarckian Evolution: Local training
        if getattr(self.config, 'local_epochs', 0) > 0:
            for g in self.genomes:
                local_train(g, X, y, self.config)

        fitnesses = [calculate_fitness(g, X, y, self.config) for g in self.genomes]
        
        sorted_indices = np.argsort(fitnesses)[::-1]
        
        survivor_count = max(1, int(self.config.pop_size * self.config.survival_rate))
        survivors = [self.genomes[i] for i in sorted_indices[:survivor_count]]
        survivor_fitnesses = [fitnesses[i] for i in sorted_indices[:survivor_count]]
        
        # Elitism: Keep survivors unchanged
        new_pop = [s.clone() for s in survivors]
        
        # Fill rest with offspring from tournament selection + crossover + mutation
        while len(new_pop) < self.config.pop_size:
            p1_idx = tournament_selection(survivors, survivor_fitnesses, self.config.tournament_size)
            p2_idx = tournament_selection(survivors, survivor_fitnesses, self.config.tournament_size)

            p1 = survivors[p1_idx]
            p2 = survivors[p2_idx]

            child = crossover(p1, p2, survivor_fitnesses[p1_idx], survivor_fitnesses[p2_idx])
            child = apply_mutations(child, self.mut_config)

            new_pop.append(child)
        
        self.genomes = new_pop
        best_genome = survivors[0]
        return survivor_fitnesses[0], best_genome
