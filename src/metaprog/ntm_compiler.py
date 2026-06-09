import numpy as np

class NTMProgramCompiler:
    """
    NTM Program Compiler.
    Translates agent NTM memory slots into discrete synapses (Self-Wiring neuronal).
    Commandment 3: Haute Performance (Vectorisation & Tensorisation).
    Commandment 9: Stabilité Numérique.
    """
    @staticmethod
    def compile_and_apply(ntm_memory: np.ndarray, W_batch: np.ndarray, agents: list) -> np.ndarray:
        """
        Translates NTM memory slots of shape (B, K, 5) into synaptic updates on W_batch of shape (B, max_N, max_N).
        Each slot contains: [src_val, dst_val, weight_val, unused_val, enable_val].
        
        Args:
            ntm_memory: array of shape (B, K, 5) representing memory slots.
            W_batch: current connection weights matrix of shape (B, max_N, max_N).
            agents: list of agents in the current batch.
            
        Returns:
            np.ndarray: updated W_batch.
        """
        if ntm_memory is None or W_batch is None or not agents:
            return W_batch
            
        B, K, M = ntm_memory.shape
        if M < 5:
            return W_batch
            
        # 1. Extract raw slot components and sanitize NaN/Infs (Commandment 9)
        src_raw = np.nan_to_num(ntm_memory[:, :, 0], nan=0.0, posinf=1.0, neginf=-1.0)
        dst_raw = np.nan_to_num(ntm_memory[:, :, 1], nan=0.0, posinf=1.0, neginf=-1.0)
        weight_raw = np.nan_to_num(ntm_memory[:, :, 2], nan=0.0, posinf=0.0, neginf=0.0)
        enable_raw = np.nan_to_num(ntm_memory[:, :, 4], nan=0.0, posinf=0.0, neginf=0.0)
        
        # 2. Extract number of nodes for each agent to restrict within actual boundaries
        num_nodes = np.array([a.genome.num_nodes for a in agents], dtype=np.int32)
        
        # Scale absolute floats to maps within [0, N_i - 1]
        # Using a deterministic scaling factor of 100
        src_idx = np.abs(src_raw) * 100.0
        dst_idx = np.abs(dst_raw) * 100.0
        
        # Scale weight values to a reasonable synaptic range [-5.0, 5.0]
        weights = np.clip(weight_raw * 5.0, -10.0, 10.0)
        
        # A slot is enabled if its activation state is positive (enable_val > 0.0)
        active = enable_raw > 0.0
        
        # 3. Vectorized updates across the batch dimension
        # Since K is a small constant (10), a simple loop over K keeps operations fully vectorised over B.
        b_idx = np.arange(B)
        for k in range(K):
            s = np.clip(src_idx[:, k].astype(np.int32), 0, num_nodes - 1)
            d = np.clip(dst_idx[:, k].astype(np.int32), 0, num_nodes - 1)
            w = weights[:, k]
            act = active[:, k]
            
            # Apply update in-place on W_batch where active is True
            W_batch[b_idx, s, d] = np.where(act, w, W_batch[b_idx, s, d])
            
        return W_batch
