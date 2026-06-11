import copy
import numpy as np
from src.agents.base_agent import BaseAgent
from src.seed_ai.mutation import Genome, apply_mutations, MutationConfig
from src.seed_ai.rl_evolution import recurrent_forward
from src.metaprog.ntm_compiler import NTMProgramCompiler
from src.agents.world_model import WorldModel
from src.seed_ai.policy_gradient import reinforce_action_update, td_error

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
        self.ref_head = None        # EDR 074 : tête référentielle dédiée (apex->token), co-entraînée par gradient
        self.predictor_head = None
        
        self.reset_state()
        
        self.phenotype_hp_bonus = float(np.sum(np.abs(self.genome.W[0:5])) * 10.0)
        self.phenotype_inv_capacity = max(3, int(np.sum(np.abs(self.genome.W[5:10]))))  # min 3 : pouvoir tenir rock+stick (gate craft, EDR 017)
        mcts_drain = 0.5 if (self.genome.organ_genes is not None and self.genome.organ_genes[0]) else 0.0
        self.phenotype_energy_drain = 1.0 + (self.phenotype_hp_bonus / 100.0) + (self.phenotype_inv_capacity * 0.1) + mcts_drain
        
    def update_phenotype(self):
        self.phenotype_hp_bonus = float(np.sum(np.abs(self.genome.W[0:5])) * 10.0)
        self.phenotype_inv_capacity = max(3, int(np.sum(np.abs(self.genome.W[5:10]))))  # min 3 : pouvoir tenir rock+stick (gate craft, EDR 017)
        
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
        self.last_obs = None  # World Model : observation du tick précédent (Vague 0)
        self.world_model_Wp = None  # World Model PAR AGENT : prédicteur appris (EDR 015)
        self._td = None  # Actor-Critic TD : transition (s,a,r,V) différée d'un tick (EDR 023)

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

_cached_activation = np.tanh
_cached_mtime = 0.0

def _get_activation_function():
    global _cached_activation, _cached_mtime
    import importlib.util
    import os
    
    sandbox_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "metaprog", "sandbox")
    ops_file = os.path.join(sandbox_dir, "generated_ops.py")
    
    if os.path.exists(ops_file):
        try:
            mtime = os.path.getmtime(ops_file)
            if mtime > _cached_mtime:
                # Défense en profondeur (EDR 035) : re-valider (gate AST) AVANT d'exécuter
                # ce code en LIVE dans le process. Refus -> on garde l'activation courante.
                from src.metaprog.secure_sandbox import validate_code
                with open(ops_file, "r", encoding="utf-8") as _f:
                    _ok, _reason = validate_code(_f.read())
                if not _ok:
                    import logging
                    logging.getLogger("AGIseed.Mamba").error(
                        f"[METAPROG] generated_ops REJETE par la securite ({_reason}) — non charge.")
                    _cached_mtime = mtime   # ne pas re-tenter ce fichier
                    return _cached_activation
                spec = importlib.util.spec_from_file_location("generated_ops", ops_file)
                generated_ops = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(generated_ops)
                if hasattr(generated_ops, "custom_activation"):
                    _cached_activation = generated_ops.custom_activation
                    _cached_mtime = mtime
                    import logging
                    logging.getLogger("AGIseed.Mamba").info(f"[METAPROG] Loaded custom activation function from {ops_file}")
        except Exception:
            pass
            
    return _cached_activation

class MambaBatchModel:
    """
    Gestionnaire de population pour vectoriser l'inférence de N agents simultanément (TensorWorld).
    Supporte le Connectome Élastique avec dynamic padding et alignement des nœuds sensoriels, cachés et moteurs.
    """
    # Flags d'ablation (EDR 032) : neutralisent un gène câblé pour mesurer son apport réel.
    ABLATE_THRESHOLDS = False   # ignore les seuils d'excitabilité
    ABLATE_ROUTER = False       # gain neuromodulateur neutre (=1)

    def __init__(self, agents: list[MambaAgent], world_model=None):
        self.agents = agents
        self.B = len(agents)
        # World Model (Vague 0) : possédé par le monde, partagé par la population.
        # None -> surprise neutre (rétro-compat : world_0 legacy, tests isolés).
        self.world_model = world_model
        if self.B == 0:
            return
            
        # Piliers Connectome Élastique: Dimensions maximales
        self.max_I = max([a.genome.num_inputs for a in agents])
        self.max_O = max([a.genome.num_outputs for a in agents])
        self.max_H = max([a.genome.num_nodes - a.genome.num_inputs - a.genome.num_outputs for a in agents])
        self.max_N = self.max_I + self.max_H + self.max_O
        
        # Limite de sécurité connectique (Commandement 9: Stabilité)
        LIMIT_N = 256
        if self.max_N > LIMIT_N:
            import logging
            logger = logging.getLogger("AGIseed.MambaBatch")
            logger.warning(
                f"🚨 ALERTE CONNECTOME : La taille maximale des agents ({self.max_N}) dépasse la limite de sécurité fixée ({LIMIT_N}). "
                f"Il faudrait peut-être augmenter ce paramètre pour éviter des dysfonctionnements !"
            )
            self.max_N = LIMIT_N
        
        self.I = self.max_I
        self.O = self.max_O
        
        self.W_batch = np.zeros((self.B, self.max_N, self.max_N), dtype=np.float32)
        self.H_prev_batch = np.zeros((self.B, self.max_N), dtype=np.float32)
        # Gène CÂBLÉ (EDR 031) : seuil d'excitabilité par neurone -> tanh(excitation - seuil).
        # Auparavant muté mais jamais lu (fantôme) ; désormais substrat évolutif réel.
        self.thresholds_batch = np.zeros((self.B, self.max_N), dtype=np.float32)
        # Gène CÂBLÉ (EDR 031) : W_router (I,3) = neuromodulation. L'obs produit 3 modulateurs
        # qui ajustent le GAIN global du réseau (traitement dépendant du contexte). Choix de
        # design (sémantique laissée vide à l'origine) ; conservateur (gain ~1), évolvable.
        self.router_batch = np.zeros((self.B, self.max_I, 3), dtype=np.float32)
        
        # Construction des index-mappings pour le alignement élastique
        self.mappings = []
        for i, a in enumerate(agents):
            I_i = a.genome.num_inputs
            O_i = a.genome.num_outputs
            N_i = a.genome.num_nodes
            
            map_idx = np.zeros(N_i, dtype=int)
            # 1. Capteurs (Inputs) : 0 -> I_i - 1
            for s in range(I_i):
                map_idx[s] = s
            # 2. Cachés (Hidden) : I_i -> N_i - O_i - 1
            for s in range(I_i, N_i - O_i):
                map_idx[s] = self.max_I + (s - I_i)
            # 3. Moteurs (Outputs) : N_i - O_i -> N_i - 1
            for s in range(N_i - O_i, N_i):
                map_idx[s] = (self.max_I + self.max_H) + (s - (N_i - O_i))
                
            # Caper les index pour la sécurité
            map_idx = np.clip(map_idx, 0, self.max_N - 1)
            self.mappings.append(map_idx)
            
            # Application de la projection élastique
            self.W_batch[i][map_idx[:, None], map_idx[None, :]] = a.genome.W
            self.H_prev_batch[i][map_idx] = a.H_prev[0]
            thr = getattr(a.genome, "thresholds", None)
            if thr is not None and len(thr) >= N_i:
                self.thresholds_batch[i][map_idx] = np.asarray(thr[:N_i], dtype=np.float32)
            wr = getattr(a.genome, "W_router", None)
            if wr is not None and wr.shape[0] >= I_i:
                self.router_batch[i, :I_i, :] = np.asarray(wr[:I_i, :], dtype=np.float32)
            
        self.surprise_momentum_batch = np.array([a.surprise_momentum for a in agents], dtype=np.float32)
        
        # Extraction élastique des attributs de population
        self.attention_mask_batch = np.zeros((self.B, self.max_I), dtype=np.float32)
        self.explicit_memory_batch = np.zeros((self.B, 5), dtype=np.float32)
        self.goal_vector_batch = np.zeros((self.B, 5), dtype=np.float32)
        self.predictor_head_batch = np.zeros((self.B, 8), dtype=np.float32)
        
        for i, a in enumerate(agents):
            self.attention_mask_batch[i, :a.genome.num_inputs] = a.attention_mask
            self.explicit_memory_batch[i] = a.explicit_memory
            self.goal_vector_batch[i] = a.goal_vector
            self.predictor_head_batch[i] = a.predictor_head
            
        # NTM Buffer
        self.NTM_K = 10 # Nombre de slots mémoire
        self.NTM_M = 5  # Dimension d'un slot
        self.NTM_Memory = np.stack([getattr(a, 'ntm_memory', np.zeros((self.NTM_K, self.NTM_M), dtype=np.float32)) for a in agents], axis=0)

        # World Model : observation précédente par agent (round-trip comme surprise_momentum).
        self.last_obs_batch = np.zeros((self.B, self.max_I), dtype=np.float32)
        self.has_last_batch = np.zeros(self.B, dtype=bool)
        for i, a in enumerate(agents):
            lo = getattr(a, 'last_obs', None)
            if lo is not None:
                L = min(len(lo), self.max_I)
                self.last_obs_batch[i, :L] = lo[:L]
                self.has_last_batch[i] = True
        self.curiosity_batch = np.zeros(self.B, dtype=np.float32)

        # World Model PAR AGENT (EDR 015) : un prédicteur Wp (input_dim, out) par agent,
        # round-trip via les agents. P reste partagé (porté par self.world_model).
        self.Wp_batch = None
        if self.world_model is not None:
            dim, od = self.world_model.input_dim, self.world_model.out_dim
            self.Wp_batch = np.zeros((self.B, dim, od), dtype=np.float32)
            for i, a in enumerate(agents):
                w = getattr(a, 'world_model_Wp', None)
                if w is not None and getattr(w, 'shape', None) == (dim, od):
                    self.Wp_batch[i] = w

        self.tick_count = 0

    def forward(self, batch_obs: np.ndarray, env_surprise_batch: np.ndarray = None) -> tuple:
        """
        - batch_obs : (B, I)
        """
        if self.B == 0:
            return np.array([]), np.array([])

        # Self-wiring neuronal: compile memory slots to W_batch
        self.W_batch = NTMProgramCompiler.compile_and_apply(self.NTM_Memory, self.W_batch, self.agents)

        # Padding/slicing de batch_obs s'il ne correspond pas à max_I
        x_obs = np.zeros((self.B, self.max_I), dtype=np.float32)
        x_obs[:, :batch_obs.shape[1]] = batch_obs
        
        x = x_obs * self.attention_mask_batch

        # 1. Extrait delta_t depuis la diagonale de W (Liquid Time-Constant)
        diag_w = np.clip(np.diagonal(self.W_batch, axis1=1, axis2=2), -10, 10)  # (B, N)
        delta_t = 1.0 / (1.0 + np.exp(-diag_w))  # (B, N)

        W_no_diag = self.W_batch.copy()
        for i in range(self.B):
            np.fill_diagonal(W_no_diag[i], 0.0)

        H = self.H_prev_batch.copy()

        # 2. Surprise = erreur du World Model : prédiction de obs(t+1) depuis obs(t)
        #    (Vague 0, levier 1). Remplace l'ancien calcul (delta d'états latents) qui
        #    valait TOUJOURS 0 — H venait d'être copié de H_prev_batch. Cf. EDR 010.
        #    Effet de bord réparé : le déclencheur du dreaming (surprise_momentum) et la
        #    récompense intrinsèque du monde (a.surprise) redeviennent vivants.
        surprise = np.zeros(self.B, dtype=np.float32)
        if self.world_model is not None and self.Wp_batch is not None and self.has_last_batch.any():
            m = self.has_last_batch
            err, self.Wp_batch[m] = self.world_model.observe_batch(
                self.Wp_batch[m], self.last_obs_batch[m], x_obs[m], train=True)
            surprise[m] = err
        surprise = np.clip(surprise, 0.0, 1.0)
        self.curiosity_batch = surprise.copy()

        # Momentum exponentiel pour lisser le signal de surprise
        decay = 0.8
        self.surprise_momentum_batch = (
            decay * self.surprise_momentum_batch + (1.0 - decay) * surprise
        )

        # 3. Passe de base (réflexe)
        H[:, :self.max_I] = x
        # Neuromodulation (EDR 031) : gain global dépendant du contexte (W_router câblé).
        if MambaBatchModel.ABLATE_ROUTER:
            gain = 1.0
        else:
            mod = np.tanh(np.einsum('bi,bij->bj', x, self.router_batch))    # (B, 3)
            gain = 1.0 + 0.3 * mod.mean(axis=1, keepdims=True)             # (B, 1) dans [0.7, 1.3]
        excitation = np.einsum('bi,bij->bj', H, W_no_diag) * gain
        thr = 0.0 if MambaBatchModel.ABLATE_THRESHOLDS else self.thresholds_batch
        H = (1.0 - delta_t) * H + delta_t * _get_activation_function()(excitation - thr)

        # --- MESO-NAS (Pilier 2): Organe d'Attention QKV (Self-Attention) ---
        has_attention_batch = np.array([
            (len(a.genome.organ_genes) > 1 and a.genome.organ_genes[1]) if getattr(a.genome, 'organ_genes', None) is not None else False
            for a in self.agents
        ], dtype=bool)
        
        if has_attention_batch.any():
            T_tok, D_tok = 4, 8
            block_size = T_tok * D_tok  # 32
            start_idx = self.max_I
            end_idx = start_idx + 3 * block_size
            
            if self.max_N >= end_idx:
                Q_flat = H[:, start_idx : start_idx + block_size]
                K_flat = H[:, start_idx + block_size : start_idx + 2*block_size]
                V_flat = H[:, start_idx + 2*block_size : end_idx]
                
                Q = Q_flat.reshape(self.B, T_tok, D_tok)
                K = K_flat.reshape(self.B, T_tok, D_tok)
                V = V_flat.reshape(self.B, T_tok, D_tok)
                
                scores = np.einsum('btd,bsd->bts', Q, K) / np.sqrt(D_tok)
                scores_max = np.max(scores, axis=-1, keepdims=True)
                exp_scores = np.exp(scores - scores_max)
                attn_weights = exp_scores / (np.sum(exp_scores, axis=-1, keepdims=True) + 1e-8)
                
                context = np.einsum('bts,bsd->btd', attn_weights, V)
                context_flat = context.reshape(self.B, block_size)
                
                mask = has_attention_batch[:, None]
                H[:, start_idx : start_idx + block_size] = np.where(
                    mask, 
                    H[:, start_idx : start_idx + block_size] + context_flat, 
                    H[:, start_idx : start_idx + block_size]
                )

        # 4. Lecture des logits intermédiaires
        preds_mid = np.zeros((self.B, self.max_O), dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            O_i = self.agents[i].genome.num_outputs
            map_idx = self.mappings[i]
            preds_mid[i, :O_i] = H[i, map_idx[N_i - O_i : N_i]]

        do_dream_batch = preds_mid[:, 26]  # logit 26
        DREAM_THRESHOLD = 0.1
        SURPRISE_THRESHOLD = 0.05
        
        has_mcts_batch = np.array([
            (a.genome.organ_genes[0] if getattr(a.genome, 'organ_genes', None) is not None else False) 
            for a in self.agents
        ], dtype=bool)
        
        is_dreaming = (
            has_mcts_batch
            & (do_dream_batch > DREAM_THRESHOLD)
            & (self.surprise_momentum_batch > SURPRISE_THRESHOLD)
        )

        K_individual = np.where(
            is_dreaming,
            np.clip((do_dream_batch * 8).astype(int), 1, 8),
            0
        )

        T_max = int(K_individual.max()) if is_dreaming.any() else 0
        compute_spent = np.zeros(self.B, dtype=np.float32)

        best_H = H.copy()
        best_value = np.full(self.B, -np.inf)

        for k in range(T_max):
            active_mask = K_individual > k

            if not active_mask.any():
                break

            H_branch = H.copy()
            noise = np.random.randn(*H_branch.shape).astype(np.float32) * 0.05
            H_branch[active_mask] += noise[active_mask]

            excitation = np.einsum('bi,bij->bj', H_branch, W_no_diag)
            H_branch = (1.0 - delta_t) * H_branch + delta_t * _get_activation_function()(excitation - self.thresholds_batch)

            for i in np.where(active_mask)[0]:
                N_i = self.agents[i].genome.num_nodes
                O_i = self.agents[i].genome.num_outputs
                map_idx = self.mappings[i]
                
                # Le logit 28 est au décalage N_i - O_i + 28
                val_idx = map_idx[N_i - O_i + 28]
                val = float(H_branch[i, val_idx])
                if np.isfinite(val) and val > best_value[i]:
                    best_value[i] = val
                    best_H[i] = H_branch[i]
                compute_spent[i] += 1.0

            H[active_mask] = H_branch[active_mask]

        dreaming_idx = np.where(is_dreaming)[0]
        if len(dreaming_idx) > 0:
            H[dreaming_idx] = best_H[dreaming_idx]

        # 6. Extraction des logits finals
        preds = np.zeros((self.B, self.max_O), dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            O_i = self.agents[i].genome.num_outputs
            map_idx = self.mappings[i]
            preds[i, :O_i] = H[i, map_idx[N_i - O_i : N_i]]

        # 7. Mise à jour de l'état interne du batch
        self.H_prev_batch = H
        
        # Construction individuelle des sous-sorties avec gestion sécurisée des indices négatifs
        attention_logits = np.zeros((self.B, self.max_I), dtype=np.float32)
        ntm_heads = np.zeros((self.B, 20), dtype=np.float32)
        goal_logits = np.zeros((self.B, 5), dtype=np.float32)
        pred_logits = np.zeros((self.B, 8), dtype=np.float32)
        
        for i in range(self.B):
            O_i = self.agents[i].genome.num_outputs
            I_i = self.agents[i].genome.num_inputs
            
            # Slicing attention_logits
            start_a, end_a = O_i - I_i, O_i
            if end_a > 0:
                a_slice = preds[i, max(0, start_a) : end_a]
                attention_logits[i, :len(a_slice)] = a_slice
                
            # Slicing ntm_heads
            start_n, end_n = O_i - I_i - 20, O_i - I_i
            if end_n > 0:
                n_slice = preds[i, max(0, start_n) : end_n]
                ntm_heads[i, -len(n_slice):] = n_slice
                
            # Slicing goal_logits
            start_g, end_g = O_i - I_i - 25, O_i - I_i - 20
            if end_g > 0:
                g_slice = preds[i, max(0, start_g) : end_g]
                goal_logits[i, -len(g_slice):] = g_slice
                
            # Slicing pred_logits
            start_p, end_p = O_i - I_i - 33, O_i - I_i - 25
            if end_p > 0:
                p_slice = preds[i, max(0, start_p) : end_p]
                pred_logits[i, -len(p_slice):] = p_slice
            
        self.attention_mask_batch = 1.0 / (1.0 + np.exp(-attention_logits))
        self.tick_count += 1
        
        # --- NTM Memory Operations ---
        r_key = ntm_heads[:, 0:5]
        w_key = ntm_heads[:, 5:10]
        w_val = ntm_heads[:, 10:15]
        e_gate = 1.0 / (1.0 + np.exp(-ntm_heads[:, 15:20]))
        
        if self.tick_count % 8 == 0:
            self.goal_vector_batch = np.tanh(goal_logits)
            
        self.predictor_head_batch = pred_logits
        
        def cosine_similarity(keys, memory):
            dot = np.einsum('bm,bkm->bk', keys, memory)
            norm_k = np.linalg.norm(keys, axis=1, keepdims=True) + 1e-8
            norm_m = np.linalg.norm(memory, axis=2) + 1e-8
            return dot / (norm_k * norm_m)
            
        def softmax(x):
            e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
            return e_x / np.sum(e_x, axis=1, keepdims=True)
            
        # NTM Read
        sim_r = cosine_similarity(r_key, self.NTM_Memory)
        w_read = softmax(sim_r)
        self.explicit_memory_batch = np.einsum('bk,bkm->bm', w_read, self.NTM_Memory)
        
        # NTM Write
        sim_w = cosine_similarity(w_key, self.NTM_Memory)
        w_write = softmax(sim_w)
        
        erase = np.einsum('bk,bm->bkm', w_write, e_gate)
        add = np.einsum('bk,bm->bkm', w_write, w_val)
        self.NTM_Memory = self.NTM_Memory * (1.0 - erase) + add

        for i, a in enumerate(self.agents):
            N_i = a.genome.num_nodes
            map_idx = self.mappings[i]
            a.H_prev[0] = self.H_prev_batch[i, map_idx]
            a.explicit_memory = self.explicit_memory_batch[i]
            a.goal_vector = self.goal_vector_batch[i]
            a.predictor_head = self.predictor_head_batch[i]
            a.attention_mask = self.attention_mask_batch[i, :a.genome.num_inputs]
            a.surprise = float(surprise[i])
            a.surprise_momentum = float(self.surprise_momentum_batch[i])
            a.ntm_memory = self.NTM_Memory[i].copy()
            a.last_obs = x_obs[i].copy()  # World Model : mémoriser obs(t) pour prédire t+1
            if self.Wp_batch is not None:
                a.world_model_Wp = self.Wp_batch[i].copy()  # World Model par-agent (EDR 015)
            a.genome.W = self.W_batch[i][map_idx[:, None], map_idx[None, :]].copy()

        return preds, compute_spent

    def compute_policy_gradient(self, rewards_batch: np.ndarray, actions_batch=None):
        """
        Apprentissage Intra-Vie. Si actions_batch est fourni : vrai ACTOR-CRITIC TD(0)
        avec crédit d'action (EDR 020) ET crédit temporel (EDR 023) — l'action choisie est
        renforcée par l'erreur TD δ = r + γ·V(s') − V(s) (transition différée d'un tick),
        le critic (value head, sortie 28) apprend vers r + γ·V(s'). Sinon : ancien Hebbien
        rustre (rétro-compat pour les appelants sans actions).

        actions_batch : liste alignée sur self.agents, chaque entrée = dict
            {"move": int 0..7, "grab": 0/1, "rub": 0/1}.
        """
        if self.B == 0:
            return

        values = np.zeros(self.B, dtype=np.float32)
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            O_i = self.agents[i].genome.num_outputs
            map_idx = self.mappings[i]
            values[i] = self.H_prev_batch[i, map_idx[N_i - O_i + 28]]
        advantages = rewards_batch - values

        # --- Rétro-compat : ancien Hebbien si pas d'actions ---
        if actions_batch is None:
            lr = 0.005
            for i in range(self.B):
                if abs(advantages[i]) > 0.01:
                    N_i = self.agents[i].genome.num_nodes
                    map_idx = self.mappings[i]
                    h_i = self.H_prev_batch[i, map_idx].reshape(-1, 1)
                    dW = lr * advantages[i] * np.dot(h_i, h_i.T)
                    self.W_batch[i][map_idx[:, None], map_idx[None, :]] = np.clip(
                        self.W_batch[i][map_idx[:, None], map_idx[None, :]] + dW, -5.0, 5.0)
                    self.agents[i].genome.W = self.W_batch[i][map_idx[:, None], map_idx[None, :]].copy()
            return

        # --- Actor-Critic TD(0) : crédit d'action + crédit TEMPOREL (EDR 020/023) ---
        # La transition (s,a,r) est mise à jour au tick SUIVANT, quand V(s') est connu :
        #   δ = r + γ·V(s') − V(s)  sert d'avantage (actor) ET d'erreur du critic.
        # -> une action coûteuse mais qui mène à un bon état (crafter -> pouvoir chasser)
        #    reçoit un avantage positif. _td est stocké sur le modèle (robuste au re-batch).
        lr_actor, lr_critic, gamma = 0.04, 0.05, 0.9
        for i in range(self.B):
            N_i = self.agents[i].genome.num_nodes
            O_i = self.agents[i].genome.num_outputs
            map_idx = self.mappings[i]
            h_t = self.H_prev_batch[i, map_idx]                          # (N_i,)
            out_t = self.H_prev_batch[i, map_idx[N_i - O_i:N_i]]         # (O_i,)
            v_t = float(values[i])
            act = actions_batch[i] if i < len(actions_batch) else None

            prev = getattr(self.agents[i], "_td", None)
            if prev is not None and prev["act"] is not None:
                delta = td_error(prev["reward"], prev["value"], v_t, gamma)   # δ = r + γV(s') − V(s)
                pa = prev["act"]
                binaries = {24: int(pa.get("grab", 0)), 25: int(pa.get("rub", 0))}
                dW = reinforce_action_update(prev["h"], prev["out"], int(pa.get("move", -1)),
                                             binaries, delta, lr_actor)        # ACTOR (avantage = δ)
                vn = prev["v_node"]
                if 0 <= vn < prev["h"].shape[0]:
                    dW[:, vn] += lr_critic * delta * prev["h"]                 # CRITIC (vers r + γV')
                W_block = np.clip(self.W_batch[i][map_idx[:, None], map_idx[None, :]] + dW, -5.0, 5.0)
                self.W_batch[i][map_idx[:, None], map_idx[None, :]] = W_block
                self.agents[i].genome.W = W_block.copy()

            # Mémoriser la transition courante pour l'update différé du prochain tick.
            self.agents[i]._td = {"h": h_t.copy(), "out": out_t.copy(), "value": v_t,
                                  "reward": float(rewards_batch[i]), "act": act,
                                  "v_node": N_i - O_i + 28}
