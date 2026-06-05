import copy
import numpy as np
from src.agents.base_agent import BaseAgent
from src.seed_ai.mutation import Genome, apply_mutations, MutationConfig
from src.seed_ai.rl_evolution import recurrent_forward

class MambaAgent(BaseAgent):
    """
    Implémentation de l'Agent utilisant le moteur Liquid Mamba (Genome V13).
    """
    
    def __init__(self, num_inputs=64, num_outputs=126, num_nodes=172):
        # Initialiser le génome sous-jacent
        W = np.random.randn(num_nodes, num_nodes).astype(np.float32) * 0.1
        self.genome = Genome(W, num_inputs, num_outputs)
        
        # S'assurer que le génome a la bonne taille
        # (Dans la vraie version on adapterait self.genome.W)
        if self.genome.W.shape[0] != num_nodes:
            # On recrée une matrice aléatoire de la bonne taille si besoin
            # Mais par défaut Genome() gère ça
            pass
            
        self.H_prev = None
        self.H_history = None
        self.H_potentials = None
        self.surprise = 0.0
        self.surprise_momentum = 0.0
        self.attention_mask = None
        self.explicit_memory = None
        self.goal_vector = None
        self.predictor_head = None
        
        self.reset_state()
        
        self.phenotype_hp_bonus = float(np.sum(np.abs(self.genome.W[0:5])) * 10.0)
        self.phenotype_inv_capacity = max(1, int(np.sum(np.abs(self.genome.W[5:10]))))
        mcts_drain = 0.5 if (self.genome.organ_genes is not None and self.genome.organ_genes[0]) else 0.0
        self.phenotype_energy_drain = 1.0 + (self.phenotype_hp_bonus / 100.0) + (self.phenotype_inv_capacity * 0.1) + mcts_drain
        
    def update_phenotype(self):
        self.phenotype_hp_bonus = float(np.sum(np.abs(self.genome.W[0:5])) * 10.0)
        self.phenotype_inv_capacity = max(1, int(np.sum(np.abs(self.genome.W[5:10]))))
        
        # Macro-NAS penalité: Avoir un organe "Cortex" coûte très cher en énergie
        mcts_drain = 0.5 if (self.genome.organ_genes is not None and self.genome.organ_genes[0]) else 0.0
        self.phenotype_energy_drain = 1.0 + (self.phenotype_hp_bonus / 100.0) + (self.phenotype_inv_capacity * 0.1) + mcts_drain
        
    def reset_state(self):
        """Réinitialise la mémoire courte de l'agent (ex: nouvelle vie)"""
        N = self.genome.num_nodes
        self.H_prev = np.zeros((1, N), dtype=np.float32)
        self.H_history = np.zeros((1, 5, N), dtype=np.float32) # Buffer de T=5
        self.H_potentials = np.zeros((1, N), dtype=np.float32)
        self.surprise = 0.0
        self.surprise_momentum = 0.0
        self.attention_mask = np.ones(self.genome.num_inputs, dtype=np.float32)
        self.explicit_memory = np.zeros(5, dtype=np.float32)
        self.goal_vector = np.zeros(5, dtype=np.float32)
        self.predictor_head = np.zeros(8, dtype=np.float32)
        self.ntm_memory = np.zeros((10, 5), dtype=np.float32)
        
    def forward(self, obs: np.ndarray) -> np.ndarray:
        # Obs doit être un vecteur (1, I)
        if len(obs.shape) == 1:
            obs = obs.reshape(1, -1)
        
        x = obs * self.attention_mask[:obs.shape[1]]
        
        preds, self.H_prev, self.H_history, self.H_potentials, self.surprise = recurrent_forward(
            self.genome, x, self.H_prev, self.H_history, self.H_potentials
        )
        logits = preds[0]
        
        I = self.genome.num_inputs
        # NTM : On extrait 5D pour la mémoire
        self.explicit_memory = logits[-(I+5):-I]
        attention_logits = logits[-I:]
        self.attention_mask = 1.0 / (1.0 + np.exp(-attention_logits))
        
        return logits
        
    def get_size(self) -> int:
        return self.genome.num_nodes
        
    def mutate(self):
        mut_config = MutationConfig(
            weight_mutate_rate=0.8,
            weight_mutate_power=0.5,
            add_node_rate=0.0,  # Désactivé pour garantir le batching TensorWorld
            add_connection_rate=0.3,
            prune_rate=0.0,     # Désactivé pour la même raison
            weight_init_std=2.0
        )
        self.genome = apply_mutations(self.genome, mut_config)
        self.update_phenotype()
        self.reset_state() # Redimensionne H_prev si N a changé
        
    def absorb_knowledge(self, other_genome: Genome, learning_rate: float = 0.1):
        """ARC 4: Transfère une partie du savoir d'un autre agent via langage (synaptic copy)."""
        min_N = min(self.genome.num_nodes, other_genome.num_nodes)
        
        # Copie partielle pondérée
        W_mapped = np.zeros_like(self.genome.W)
        W_mapped[:min_N, :min_N] = other_genome.W[:min_N, :min_N]
        
        self.genome.W = (1.0 - learning_rate) * self.genome.W + learning_rate * W_mapped
        self.update_phenotype()
        
    def clone(self) -> 'MambaAgent':
        new_agent = MambaAgent(
            num_inputs=self.genome.num_inputs, 
            num_outputs=self.genome.num_outputs,
            num_nodes=self.genome.num_nodes
        )
        new_agent.genome = copy.deepcopy(self.genome)
        new_agent.attention_mask = self.attention_mask.copy() if self.attention_mask is not None else None
        new_agent.explicit_memory = self.explicit_memory.copy() if self.explicit_memory is not None else None
        new_agent.goal_vector = self.goal_vector.copy() if self.goal_vector is not None else None
        new_agent.predictor_head = self.predictor_head.copy() if self.predictor_head is not None else None
        return new_agent

    def from_genome(self, genome: Genome):
        """Utile pour charger un génome depuis le Hall of Fame"""
        self.genome = copy.deepcopy(genome)
        
        # Dimensions de la V18 (TensorWorld + NTM + Actor-Critic + Hierarchical + ToM)
        expected_inputs = 64  # 54 + 5 (NTM_Read_Result) + 5 (Manager Goal)
        expected_outputs = 126 # 29 actions + 8 (ToM) + 5 (Goal) + 20 NTM Heads + 64 Attention Mask = 126
        expected_nodes = 172
        
        if self.genome.num_inputs != expected_inputs or self.genome.num_outputs != expected_outputs or self.genome.num_nodes != expected_nodes:
            new_W = np.zeros((expected_nodes, expected_nodes), dtype=np.float32)
            min_N = min(self.genome.num_nodes, expected_nodes)
            new_W[:min_N, :min_N] = self.genome.W[:min_N, :min_N]
            
            new_router = np.zeros((expected_inputs, 3), dtype=np.float32)
            if hasattr(self.genome, 'W_router') and self.genome.W_router is not None:
                min_I = min(self.genome.num_inputs, expected_inputs)
                new_router[:min_I, :] = self.genome.W_router[:min_I, :]
                
            self.genome = Genome(new_W, expected_inputs, expected_outputs, self.genome.mutation_genes, new_router, self.genome.bytecode, np.zeros(expected_nodes))
        
        self.update_phenotype()
        self.reset_state()

    def save_state(self, path: str) -> str:
        """Sauvegarde l'état interne de l'agent."""
        import os
        state = {
            'H_prev': self.H_prev,
            'H_history': self.H_history,
            'H_potentials': self.H_potentials,
            'surprise': np.array([self.surprise]),
            'attention_mask': self.attention_mask,
            'explicit_memory': self.explicit_memory,
            'goal_vector': self.goal_vector,
            'predictor_head': self.predictor_head,
            'ntm_memory': self.ntm_memory,
            'genome_W': self.genome.W,
            'genome_num_inputs': self.genome.num_inputs,
            'genome_num_outputs': self.genome.num_outputs,
            'genome_mutation_genes': self.genome.mutation_genes,
        }
        npz_path = path if path.endswith('.npz') else f"{path}.npz"
        os.makedirs(os.path.dirname(npz_path) if os.path.dirname(npz_path) else '.', exist_ok=True)
        np.savez(npz_path, **state)
        return npz_path

    def load_state(self, path: str) -> bool:
        """Charge l'état interne de l'agent."""
        try:
            data = np.load(path)
            self.H_prev = data['H_prev'].astype(np.float32) if 'H_prev' in data else self.H_prev
            self.H_history = data['H_history'].astype(np.float32) if 'H_history' in data else self.H_history
            self.H_potentials = data['H_potentials'].astype(np.float32) if 'H_potentials' in data else self.H_potentials
            self.surprise = float(data['surprise'][0]) if 'surprise' in data else 0.0
            self.attention_mask = data['attention_mask'].astype(np.float32) if 'attention_mask' in data else self.attention_mask
            self.explicit_memory = data['explicit_memory'].astype(np.float32) if 'explicit_memory' in data else self.explicit_memory
            self.goal_vector = data['goal_vector'].astype(np.float32) if 'goal_vector' in data else self.goal_vector
            self.predictor_head = data['predictor_head'].astype(np.float32) if 'predictor_head' in data else self.predictor_head
            self.ntm_memory = data['ntm_memory'].astype(np.float32) if 'ntm_memory' in data else self.ntm_memory
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load agent state: {e}")
            return False

    def to_dict(self) -> dict:
        """Sérialise l'agent pour sauvegarde."""
        return {
            'H_prev': self.H_prev,
            'H_history': self.H_history,
            'H_potentials': self.H_potentials,
            'surprise': self.surprise,
            'attention_mask': self.attention_mask,
            'explicit_memory': self.explicit_memory,
            'goal_vector': self.goal_vector,
            'predictor_head': self.predictor_head,
            'ntm_memory': self.ntm_memory,
            'genome': self.genome,
        }

    def from_dict(self, state_dict: dict):
        """Désérialise depuis dict."""
        self.H_prev = state_dict.get('H_prev', np.zeros((1, self.genome.num_nodes), dtype=np.float32))
        self.H_history = state_dict.get('H_history', np.zeros((1, 5, self.genome.num_nodes), dtype=np.float32))
        self.H_potentials = state_dict.get('H_potentials', np.zeros((1, self.genome.num_nodes), dtype=np.float32))
        self.surprise = state_dict.get('surprise', 0.0)
        self.attention_mask = state_dict.get('attention_mask', np.ones(self.genome.num_inputs, dtype=np.float32))
        self.explicit_memory = state_dict.get('explicit_memory', np.zeros(5, dtype=np.float32))
        self.goal_vector = state_dict.get('goal_vector', np.zeros(5, dtype=np.float32))
        self.predictor_head = state_dict.get('predictor_head', np.zeros(8, dtype=np.float32))
        self.ntm_memory = state_dict.get('ntm_memory', np.zeros((10, 5), dtype=np.float32))
        if 'genome' in state_dict:
            self.genome = state_dict['genome']
            self.update_phenotype()


class MambaBatchModel:
    """
    Gestionnaire de population pour vectoriser l'inférence de N agents simultanément (TensorWorld).
    """
    def __init__(self, agents: list[MambaAgent]):
        self.agents = agents
        self.B = len(agents)
        if self.B == 0:
            return
            
        self.max_N = max([a.genome.num_nodes for a in agents])
        self.I = agents[0].genome.num_inputs
        self.O = agents[0].genome.num_outputs
        
        self.W_batch = np.zeros((self.B, self.max_N, self.max_N), dtype=np.float32)
        self.H_prev_batch = np.zeros((self.B, self.max_N), dtype=np.float32)
        
        for i, a in enumerate(agents):
            N_i = a.genome.num_nodes
            self.W_batch[i, :N_i, :N_i] = a.genome.W
            self.H_prev_batch[i, :N_i] = a.H_prev[0]
            
        self.surprise_momentum_batch = np.array([a.surprise_momentum for a in agents], dtype=np.float32) # (B,)
        
        # Attentions et mémoires (B, I) et (B, 5)
        self.attention_mask_batch = np.stack([a.attention_mask for a in agents], axis=0) # (B, I)
        self.explicit_memory_batch = np.stack([a.explicit_memory for a in agents], axis=0) # (B, 5)
        self.goal_vector_batch = np.stack([a.goal_vector for a in agents], axis=0) # (B, 5)
        self.predictor_head_batch = np.stack([a.predictor_head for a in agents], axis=0) # (B, 8)
        
        # NTM Buffer
        self.NTM_K = 10 # Nombre de slots mémoire
        self.NTM_M = 5  # Dimension d'un slot
        self.NTM_Memory = np.stack([getattr(a, 'ntm_memory', np.zeros((self.NTM_K, self.NTM_M), dtype=np.float32)) for a in agents], axis=0)
        
        self.tick_count = 0

    def forward(self, batch_obs: np.ndarray, env_surprise_batch: np.ndarray = None) -> tuple:
        """
        - batch_obs : (B, I)
        Retourne : (batch_logits (B, O), compute_spent (B,))
        compute_spent[i] = nombre de passes de Beam Search utilisées par l'agent i.
        """
        if self.B == 0:
            return np.array([]), np.array([])

        x = batch_obs * self.attention_mask_batch[:, :batch_obs.shape[1]]

        # 1. Extrait delta_t depuis la diagonale de W (Liquid Time-Constant)
        diag_w = np.clip(np.diagonal(self.W_batch, axis1=1, axis2=2), -10, 10)  # (B, N)
        delta_t = 1.0 / (1.0 + np.exp(-diag_w))  # (B, N)

        W_no_diag = self.W_batch.copy()
        for i in range(self.B):
            np.fill_diagonal(W_no_diag[i], 0.0)

        H = self.H_prev_batch.copy()

        # 2. Calcul de la surprise (delta entre états latents consécutifs)
        surprise = np.mean((H - self.H_prev_batch) ** 2, axis=1)  # (B,)
        surprise = np.clip(surprise, 0.0, 1.0)

        # Momentum exponentiel pour lisser le signal de surprise
        decay = 0.8
        self.surprise_momentum_batch = (
            decay * self.surprise_momentum_batch + (1.0 - decay) * surprise
        )

        # 3. Passe de base (réflexe) — toujours exécutée pour tous les agents
        H[:, :x.shape[1]] = x
        excitation = np.einsum('bi,bij->bj', H, W_no_diag)
        H = (1.0 - delta_t) * H + delta_t * np.tanh(excitation)

        # --- MESO-NAS (Pilier 2): Organe d'Attention QKV (Self-Attention) ---
        has_attention_batch = np.array([
            (len(a.genome.organ_genes) > 1 and a.genome.organ_genes[1]) if getattr(a.genome, 'organ_genes', None) is not None else False
            for a in self.agents
        ], dtype=bool)
        
        if has_attention_batch.any():
            T_tok, D_tok = 4, 8
            block_size = T_tok * D_tok  # 32
            start_idx = self.I
            end_idx = start_idx + 3 * block_size  # ex: 59 + 96 = 155
            
            if self.max_N >= end_idx:
                Q_flat = H[:, start_idx : start_idx + block_size]
                K_flat = H[:, start_idx + block_size : start_idx + 2*block_size]
                V_flat = H[:, start_idx + 2*block_size : end_idx]
                
                Q = Q_flat.reshape(self.B, T_tok, D_tok)
                K = K_flat.reshape(self.B, T_tok, D_tok)
                V = V_flat.reshape(self.B, T_tok, D_tok)
                
                # Scaled Dot-Product Attention: Softmax(Q @ K^T / sqrt(D)) @ V
                scores = np.einsum('btd,bsd->bts', Q, K) / np.sqrt(D_tok)
                scores_max = np.max(scores, axis=-1, keepdims=True)
                exp_scores = np.exp(scores - scores_max)
                attn_weights = exp_scores / (np.sum(exp_scores, axis=-1, keepdims=True) + 1e-8)
                
                context = np.einsum('bts,bsd->btd', attn_weights, V)
                context_flat = context.reshape(self.B, block_size)
                
                # Residual connection back to Q nodes for agents with the organ
                mask = has_attention_batch[:, None]
                H[:, start_idx : start_idx + block_size] = np.where(
                    mask, 
                    H[:, start_idx : start_idx + block_size] + context_flat, 
                    H[:, start_idx : start_idx + block_size]
                )

        # 4. Lecture des logits intermédiaires pour décider qui va rêver
        preds_mid = np.zeros((self.B, self.O), dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            preds_mid[i] = H[i, N_i - self.O: N_i]

        # do_dream[i] > 0.5 ET surprise_momentum élevé → double condition
        do_dream_batch = preds_mid[:, 26]  # logit 26
        DREAM_THRESHOLD = 0.1
        SURPRISE_THRESHOLD = 0.05
        
        # --- MACRO-NAS (Pilier 1): L'agent n'a le droit de rêver QUE s'il possède l'organe MCTS
        # On lit le premier booléen du tableau organ_genes. S'il n'existe pas, False par défaut.
        has_mcts_batch = np.array([
            (a.genome.organ_genes[0] if getattr(a.genome, 'organ_genes', None) is not None else False) 
            for a in self.agents
        ], dtype=bool)
        
        is_dreaming = (
            has_mcts_batch
            & (do_dream_batch > DREAM_THRESHOLD)
            & (self.surprise_momentum_batch > SURPRISE_THRESHOLD)
        )  # shape (B,) booléen

        # Nombre de passes de beam individuel : K_i = 1..8 selon do_dream
        K_individual = np.where(
            is_dreaming,
            np.clip((do_dream_batch * 8).astype(int), 1, 8),
            0
        )  # (B,) int — 0 pour les non-rêveurs

        T_max = int(K_individual.max()) if is_dreaming.any() else 0
        compute_spent = np.zeros(self.B, dtype=np.float32)  # Tracking par agent

        # 5. Beam Search adaptatif par masque
        best_H = H.copy()
        best_value = np.full(self.B, -np.inf)

        for k in range(T_max):
            # Seuls les agents dont K_i > k participent encore au beam
            active_mask = K_individual > k  # (B,) bool

            if not active_mask.any():
                break

            H_branch = H.copy()
            # Bruit d'exploration dans l'espace latent (petit std pour stabilité)
            noise = np.random.randn(*H_branch.shape).astype(np.float32) * 0.05
            H_branch[active_mask] += noise[active_mask]

            excitation = np.einsum('bi,bij->bj', H_branch, W_no_diag)
            H_branch = (1.0 - delta_t) * H_branch + delta_t * np.tanh(excitation)

            # Évaluation : logit 28 = value_pred
            for i in np.where(active_mask)[0]:
                N_i = self.agents[i].genome.num_nodes
                # Guard : value_pred doit être dans les bornes des outputs
                val_idx = N_i - self.O + 28
                if 0 <= val_idx < N_i:
                    val = float(H_branch[i, val_idx])
                    if np.isfinite(val) and val > best_value[i]:
                        best_value[i] = val
                        best_H[i] = H_branch[i]
                compute_spent[i] += 1.0

            H[active_mask] = H_branch[active_mask]

        # Les rêveurs prennent leur meilleur état trouvé
        dreaming_idx = np.where(is_dreaming)[0]
        if len(dreaming_idx) > 0:
            H[dreaming_idx] = best_H[dreaming_idx]

        # 6. Extraction des logits finals
        preds = np.zeros((self.B, self.O), dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            preds[i] = H[i, N_i - self.O: N_i]

        # 7. Mise à jour de l'état interne du batch
        self.H_prev_batch = H
        attention_logits = preds[:, -self.I:]
        self.attention_mask_batch = 1.0 / (1.0 + np.exp(-attention_logits))
        
        self.tick_count += 1
        
        # --- NTM Memory Operations ---
        # Extractions des têtes NTM (20 params)
        ntm_heads = preds[:, -(self.I + 20):-self.I]
        r_key = ntm_heads[:, 0:5]
        w_key = ntm_heads[:, 5:10]
        w_val = ntm_heads[:, 10:15]
        e_gate = 1.0 / (1.0 + np.exp(-ntm_heads[:, 15:20])) # Sigmoid for erase gate
        
        # --- Hierarchical Goal & Predictor ---
        goal_logits = preds[:, -(self.I + 25):-(self.I + 20)]
        pred_logits = preds[:, -(self.I + 33):-(self.I + 25)]
        
        if self.tick_count % 8 == 0:
            self.goal_vector_batch = np.tanh(goal_logits)
            
        self.predictor_head_batch = pred_logits
        
        def cosine_similarity(keys, memory):
            # keys: (B, M), memory: (B, K, M)
            # return: (B, K)
            dot = np.einsum('bm,bkm->bk', keys, memory)
            norm_k = np.linalg.norm(keys, axis=1, keepdims=True) + 1e-8
            norm_m = np.linalg.norm(memory, axis=2) + 1e-8
            return dot / (norm_k * norm_m)
            
        def softmax(x):
            e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
            return e_x / np.sum(e_x, axis=1, keepdims=True)
            
        # NTM Read
        sim_r = cosine_similarity(r_key, self.NTM_Memory)
        w_read = softmax(sim_r) # (B, K)
        self.explicit_memory_batch = np.einsum('bk,bkm->bm', w_read, self.NTM_Memory)
        
        # NTM Write
        sim_w = cosine_similarity(w_key, self.NTM_Memory)
        w_write = softmax(sim_w) # (B, K)
        
        # Erase and Add
        erase = np.einsum('bk,bm->bkm', w_write, e_gate)
        add = np.einsum('bk,bm->bkm', w_write, w_val)
        self.NTM_Memory = self.NTM_Memory * (1.0 - erase) + add

        for i, a in enumerate(self.agents):
            N_i = a.genome.num_nodes
            a.H_prev[0] = self.H_prev_batch[i, :N_i]
            a.explicit_memory = self.explicit_memory_batch[i]
            a.goal_vector = self.goal_vector_batch[i]
            a.predictor_head = self.predictor_head_batch[i]
            a.attention_mask = self.attention_mask_batch[i]
            a.surprise = float(surprise[i])
            a.surprise_momentum = float(self.surprise_momentum_batch[i])
            a.ntm_memory = self.NTM_Memory[i].copy()

        return preds, compute_spent

    def compute_policy_gradient(self, rewards_batch: np.ndarray):
        """
        Apprentissage Intra-Vie (Actor-Critic Hebbian Update).
        Modifie les poids de la matrice W_batch en fonction de l'Avantage (Reward - Critic_Value).
        Évolution Darwinienne : Les poids modifiés ne remplacent PAS le génome de l'agent.
        """
        if self.B == 0: return
        
        values = np.zeros(self.B, dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            val_idx = N_i - self.O + 28
            if 0 <= val_idx < N_i:
                values[i] = self.H_prev_batch[i, val_idx]
                
        advantages = rewards_batch - values
        lr = 0.005 # Learning rate intra-vie
        
        for i in range(self.B):
            if abs(advantages[i]) > 0.01:
                N_i = self.agents[i].genome.num_nodes
                h_i = self.H_prev_batch[i, :N_i].reshape(-1, 1)
                
                # Trace Hebbienne: les neurones qui s'activent ensemble se lient
                hebbian_trace = np.dot(h_i, h_i.T)
                
                # Mise à jour modulée par l'avantage
                dW = lr * advantages[i] * hebbian_trace
                
                # On applique la mise à jour à W_batch (utilisé pour la vie de l'agent)
                self.W_batch[i, :N_i, :N_i] = np.clip(self.W_batch[i, :N_i, :N_i] + dW, -5.0, 5.0)
                
                # Pilier 3 (RL Intra-Vie): On sauvegarde cet apprentissage dans le génome de l'agent (Lamarckien)
                # Cela permet au HGT (Meta-NAS) de transférer les connaissances acquises pendant l'ère !
                self.agents[i].genome.W = self.W_batch[i, :N_i, :N_i].copy()
