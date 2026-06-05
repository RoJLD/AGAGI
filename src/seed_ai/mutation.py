import numpy as np
from dataclasses import dataclass

@dataclass
class MutationConfig:
    weight_mutate_rate: float = 0.8
    weight_mutate_power: float = 0.5
    add_node_rate: float = 0.2
    add_connection_rate: float = 0.5
    prune_rate: float = 0.1
    weight_init_mean: float = 0.0
    weight_init_std: float = 1.0
    meta_mutate_rate: float = 0.1
    meta_mutate_power: float = 0.1
    meso_skip_rate: float = 0.05
    meso_gate_rate: float = 0.05

@dataclass
class Genome:
    W: np.ndarray  # Adjacency matrix, shape (N, N)
    num_inputs: int
    num_outputs: int
    mutation_genes: np.ndarray = None
    W_router: np.ndarray = None  # Routeur V5 : (num_inputs, 3)
    bytecode: np.ndarray = None  # V6: Programme assembleur [0,1,2,4,3]
    thresholds: np.ndarray = None  # V6: Seuils d'activation Spiking (N,)
    memory_cache: np.ndarray = None  # Short-term memory for Read operation (N,)
    organ_genes: np.ndarray = None # Macro-NAS: [enable_mcts, enable_symbolic_memory, reserved...]


    
    def __post_init__(self):
        if self.mutation_genes is None:
            # [weight_mutate_rate, weight_mutate_power, add_node_rate, add_connection_rate, prune_rate, T_micro_ticks]
            self.mutation_genes = np.array([0.8, 0.5, 0.1, 0.3, 0.1, 3.0], dtype=float)
            
        if self.organ_genes is None:
            # Organes de base (par défaut, désactivés pour favoriser la sélection naturelle)
            # 0: MCTS (Test-Time Compute)
            # 1: Self-Attention QKV (Cortex Visuel / Meso-NAS)
            self.organ_genes = np.array([False, False], dtype=bool)
            
    @property
    def num_nodes(self):
        return self.W.shape[0]
        
    def clone(self):
        w_r = self.W_router.copy() if self.W_router is not None else None
        bc = self.bytecode.copy() if self.bytecode is not None else None
        th = self.thresholds.copy() if self.thresholds is not None else None
        og = self.organ_genes.copy() if self.organ_genes is not None else np.array([False, False], dtype=bool)
        return Genome(self.W.copy(), self.num_inputs, self.num_outputs, self.mutation_genes.copy(), w_r, bc, th, memory_cache=None, organ_genes=og)

def add_node(genome: Genome, config: MutationConfig) -> None:
    """Inserts a node by splitting an existing connection, preserving topological sort."""
    W = genome.W
    nz = np.nonzero(W)
    if len(nz[0]) == 0:
        return
    idx = np.random.randint(len(nz[0]))
    i, j = nz[0][idx], nz[1][idx]
    
    old_weight = W[i, j]
    W[i, j] = 0.0
    
    # Insert new node at index j. Old j moves to j+1.
    new_W = np.insert(W, j, 0, axis=0)
    new_W = np.insert(new_W, j, 0, axis=1)
    
    new_W[i, j] = 1.0
    new_W[j, j+1] = old_weight
    
    genome.W = new_W

def add_connection(genome: Genome, config: MutationConfig) -> None:
    """Adds a random forward connection between existing nodes (DAG)."""
    W = genome.W
    N = genome.num_nodes
    
    # All possible connections (including self-loops for memory)
    valid_i, valid_j = np.indices((N, N))
    valid_i = valid_i.flatten()
    valid_j = valid_j.flatten()
    
    # Filter out connections originating from output nodes
    mask = valid_i < (N - genome.num_outputs)
    valid_i = valid_i[mask]
    valid_j = valid_j[mask]
    
    # Filter out already existing connections
    zeros_mask = W[valid_i, valid_j] == 0
    valid_i = valid_i[zeros_mask]
    valid_j = valid_j[zeros_mask]
    
    if len(valid_i) == 0:
        return
        
    idx = np.random.randint(len(valid_i))
    i, j = valid_i[idx], valid_j[idx]
    
    genome.W[i, j] = np.random.normal(config.weight_init_mean, config.weight_init_std)

def mutate_weights(genome: Genome) -> None:
    """Adds Gaussian noise to existing weights based on mutation genes."""
    W = genome.W
    nz = np.nonzero(W)
    if len(nz[0]) == 0:
        return
        
    weight_mutate_rate = genome.mutation_genes[0]
    weight_mutate_power = genome.mutation_genes[1]
    
    mutates = np.random.rand(len(nz[0])) < weight_mutate_rate
    mut_i = nz[0][mutates]
    mut_j = nz[1][mutates]
    
    noise = np.random.normal(0, weight_mutate_power, size=len(mut_i))
    genome.W[mut_i, mut_j] += noise
    
    # Mutate W_router
    if genome.W_router is not None:
        mutates_router = np.random.rand(*genome.W_router.shape) < weight_mutate_rate
        if np.any(mutates_router):
            noise_r = np.random.normal(0, weight_mutate_power, size=np.count_nonzero(mutates_router))
            genome.W_router[mutates_router] += noise_r

def prune(genome: Genome) -> None:
    """Removes an existing connection based on mutation genes."""
    W = genome.W
    nz = np.nonzero(W)
    if len(nz[0]) == 0:
        return
        
    prune_rate = genome.mutation_genes[4]
    if np.random.rand() < prune_rate:
        idx = np.random.randint(len(nz[0]))
        genome.W[nz[0][idx], nz[1][idx]] = 0.0

def mutate_bytecode_and_thresholds(genome: Genome) -> None:
    """Mutation du programme assembleur et des seuils spiking."""
    if genome.bytecode is not None:
        if np.random.rand() < 0.1: # 10% chance to mutate bytecode length/order
            action = np.random.choice(['insert', 'delete', 'swap', 'mutate'])
            if action == 'insert' and len(genome.bytecode) < 20:
                idx = np.random.randint(len(genome.bytecode) + 1)
                inst = np.random.randint(0, 8) # Instructions 0 to 7
                genome.bytecode = np.insert(genome.bytecode, idx, inst)
            elif action == 'delete' and len(genome.bytecode) > 3:
                idx = np.random.randint(len(genome.bytecode))
                genome.bytecode = np.delete(genome.bytecode, idx)
            elif action == 'swap' and len(genome.bytecode) > 1:
                i, j = np.random.randint(0, len(genome.bytecode), size=2)
                genome.bytecode[i], genome.bytecode[j] = genome.bytecode[j], genome.bytecode[i]
            elif action == 'mutate':
                idx = np.random.randint(len(genome.bytecode))
                genome.bytecode[idx] = np.random.randint(0, 8)
                
    if genome.thresholds is not None:
        mutates_th = np.random.rand(*genome.thresholds.shape) < 0.1
        if np.any(mutates_th):
            noise_th = np.random.normal(0, 0.1, size=np.count_nonzero(mutates_th))
            genome.thresholds[mutates_th] += noise_th
            genome.thresholds = np.clip(genome.thresholds, 0.0, 1.0) # Seuils positifs


def add_meso_skip_connection(genome: Genome, config: MutationConfig) -> None:
    """
    Macro-mutation (Meso-NAS): Ajoute une connexion résiduelle directe (Skip Connection)
    contournant les couches intermédiaires pour lutter contre la disparition du gradient.
    """
    W = genome.W
    N = genome.num_nodes
    
    # Cherche un nœud d'entrée (proche des inputs)
    potential_sources = list(range(genome.num_inputs))
    # Cherche un nœud de sortie (proche des outputs)
    potential_targets = list(range(N - genome.num_outputs, N))
    
    if not potential_sources or not potential_targets:
        return
        
    src = np.random.choice(potential_sources)
    tgt = np.random.choice(potential_targets)
    
    # La Skip Connection s'installe avec un poids fort (1.0) pour passer l'information brute
    W[src, tgt] = 1.0

def add_meso_gated_unit(genome: Genome, config: MutationConfig) -> None:
    """
    Macro-mutation (Meso-NAS): Insère un motif de régulation (Gating Motif).
    Utilise 3 nœuds (1 linear, 1 porte, 1 multiplicateur) pour agir comme un filtre.
    Dans notre graphe d'adjacence, cela se traduit par la création de sous-nœuds.
    """
    W = genome.W
    N = genome.num_nodes
    
    nz = np.nonzero(W)
    if len(nz[0]) == 0:
        return
        
    # Choisir une connexion existante à "gater"
    idx = np.random.randint(len(nz[0]))
    i, j = nz[0][idx], nz[1][idx]
    old_w = W[i, j]
    W[i, j] = 0.0
    
    # On ajoute 2 nouveaux nœuds (Porte et Combinateur)
    new_W = np.insert(W, j, 0, axis=0)
    new_W = np.insert(new_W, j, 0, axis=1)
    
    new_W = np.insert(new_W, j+1, 0, axis=0)
    new_W = np.insert(new_W, j+1, 0, axis=1)
    
    gate_node = j
    combiner_node = j + 1
    target_node = j + 2
    
    # Câblage du motif Gated Unit
    # Source -> Combinateur (Voie principale)
    new_W[i, combiner_node] = old_w
    # Source -> Porte (Voie de contrôle)
    new_W[i, gate_node] = 1.0 
    
    # Porte -> Combinateur (La porte régule le combinateur)
    new_W[gate_node, combiner_node] = 1.0
    
    # Combinateur -> Cible
    new_W[combiner_node, target_node] = 1.0
    
    genome.W = new_W

def apply_mutations(genome: Genome, config: MutationConfig) -> Genome:
    """Applies mutations and meta-mutations based on their respective probabilities."""
    genome = genome.clone()
    
    # Self-Tuning: Meta-mutation of mutation genes
    meta_rate = getattr(config, 'meta_mutate_rate', 0.1)
    meta_power = getattr(config, 'meta_mutate_power', 0.1)
    
    mask = np.random.rand(6) < meta_rate
    if np.any(mask):
        noise = np.random.normal(0, meta_power, size=np.count_nonzero(mask))
        genome.mutation_genes[mask] += noise
        # Clip rates to [0.0, 1.0]
        genome.mutation_genes[[0, 2, 3, 4]] = np.clip(genome.mutation_genes[[0, 2, 3, 4]], 0.0, 1.0)
        # Power must remain positive
        genome.mutation_genes[1] = max(0.01, genome.mutation_genes[1])
        # T_micro_ticks must be between 1.0 and 10.0
        genome.mutation_genes[5] = np.clip(genome.mutation_genes[5], 1.0, 10.0)
        
    # Mutation de la matrice W
    if np.random.rand() < config.weight_mutate_rate:
        mutate_weights(genome)
    
    # Meso-NAS: Ajout de Motifs Complexes
    if np.random.rand() < config.meso_skip_rate:
        add_meso_skip_connection(genome, config)
        
    if np.random.rand() < config.meso_gate_rate:
        add_meso_gated_unit(genome, config)
        
    # Micro-NAS: Ajout de Noeuds et Connexions
    if np.random.rand() < config.add_node_rate:
        add_node(genome, config)
        if genome.thresholds is not None:
            # Expand thresholds array for new node
            genome.thresholds = np.append(genome.thresholds, np.random.rand() * 0.5)
    if np.random.rand() < config.add_connection_rate:
        add_connection(genome, config)
        
    # Macro-NAS: Mutation des organes
    if np.random.rand() < meta_rate: # On utilise le meta_rate pour la fréquence de mutation des organes majeurs
        organ_idx = np.random.randint(len(genome.organ_genes))
        genome.organ_genes[organ_idx] = not genome.organ_genes[organ_idx]
        
    mutate_bytecode_and_thresholds(genome)
    prune(genome)
    
    import os
    if os.getenv("ACTIVE_EXP_VARIABLE", "NONE") == "METAPROG" and np.random.rand() < 0.05:
        # Metaprogramming check via Sandbox (Commandement 6 & 7)
        try:
            from src.metaprog.sandbox import inject_and_test
            from src.metaprog.compiler import compile_bytecode_to_python
            
            if genome.bytecode is not None:
                code = compile_bytecode_to_python(genome.bytecode)
                if inject_and_test(code):
                    # Simulated: the agent invented a valid operation. We strongly boost its connectivity.
                    print("[META-PROG] Agent a écrit un nouvel outil valide !")
                    for _ in range(5):
                        add_connection(genome, config)
                    # Boost mutation rates for this genome lineage
                    genome.mutation_genes[3] = min(1.0, genome.mutation_genes[3] + 0.2)
        except Exception as e:
            pass
            
    return genome
