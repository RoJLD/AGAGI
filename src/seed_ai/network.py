import numpy as np
from pydantic import BaseModel
from typing import List, Tuple
import logging

logger = logging.getLogger("AGIseed.MicroEngine")

class MicroEngineConfig(BaseModel):
    max_nodes: int = 100

class MicroEngine:
    """
    Micro-NAS Execution Engine.
    Executes a DAG of basic mathematical operations purely via NumPy.
    """
    def __init__(self, config: MicroEngineConfig = None):
        self.config = config or MicroEngineConfig()
        
        # Adjacency matrix for weights: self.weights[source, target]
        self.weights = np.zeros((self.config.max_nodes, self.config.max_nodes), dtype=np.float32)
        # Biases for each node
        self.biases = np.zeros((self.config.max_nodes,), dtype=np.float32)
        
        # Operations per node (0=Linear, 1=ReLU, 2=Sigmoid, 3=Write, 4=Read)
        self.operations = np.zeros((self.config.max_nodes,), dtype=np.int32)
        
        # Active nodes flag
        self.active_nodes = np.zeros((self.config.max_nodes,), dtype=bool)
        
        self.input_nodes = []
        self.output_nodes = []
        
        # Memory structures for Active Graph-RAG Fusion (Commandments 2 & 4)
        # memory_buffer caches writes to be synced asynchronously to KuzuDB
        self.memory_buffer: List[Tuple[int, float, np.ndarray]] = [] 
        # memory_cache stores fetched values from KuzuDB for fast sync reads
        self.memory_cache = np.zeros((self.config.max_nodes,), dtype=np.float32)
        
        # Short-Term Working Memory (Phase 6.5)
        self.recurrent_state = np.zeros((self.config.max_nodes,), dtype=np.float32)
        
    def reset_memory(self):
        """Réinitialise la mémoire à court terme (utile au début d'un nouvel épisode)"""
        self.recurrent_state.fill(0.0)
        self.memory_buffer.clear()
        
    def add_node(self, node_id: int, operation: int, is_input: bool = False, is_output: bool = False):
        self.active_nodes[node_id] = True
        self.operations[node_id] = operation
        if is_input:
            self.input_nodes.append(node_id)
        if is_output:
            self.output_nodes.append(node_id)
            
    def set_weight(self, source: int, target: int, weight: float):
        if not self.active_nodes[source] or not self.active_nodes[target]:
            raise ValueError(f"Nodes {source} and {target} must be active.")
        self.weights[source, target] = weight
        
    def set_bias(self, node: int, bias: float):
        if not self.active_nodes[node]:
            raise ValueError(f"Node {node} must be active.")
        self.biases[node] = bias

    def _activate(self, x: np.ndarray, ops: np.ndarray) -> np.ndarray:
        """Vectorized activation application"""
        out = np.copy(x)
        
        # 1: ReLU
        relu_mask = (ops == 1)
        out[relu_mask] = np.maximum(0, out[relu_mask])
        
        # 2: Sigmoid
        sigmoid_mask = (ops == 2)
        # Avoid overflow
        np.clip(out[sigmoid_mask], -500, 500, out=out[sigmoid_mask])
        out[sigmoid_mask] = 1 / (1 + np.exp(-out[sigmoid_mask]))
        
        # 3: Neurone-Greffier (Write) uses identity (linear), handled during forward pass
        
        # 4: Neurone-Sonde (Read)
        read_mask = (ops == 4)
        out[read_mask] = self.memory_cache[read_mask]
        
        # 5: Swish / GELU approximation (x * sigmoid(x))
        swish_mask = (ops == 5)
        if np.any(swish_mask):
            x_swish = out[swish_mask]
            # Create a safe copy for exp to avoid modifying original array in-place before calculation
            x_safe = np.clip(x_swish, -500, 500)
            sig = 1.0 / (1.0 + np.exp(-x_safe))
            out[swish_mask] = x_swish * sig
            
        # 6: Sine (periodic activation)
        sine_mask = (ops == 6)
        if np.any(sine_mask):
            out[sine_mask] = np.sin(out[sine_mask])
        
        return out
        
    def _activation_derivative(self, h: np.ndarray, x: np.ndarray, ops: np.ndarray) -> np.ndarray:
        """Derivative of activation functions.
        h: post-activation value
        x: pre-activation value
        """
        deriv = np.ones_like(h)
        
        # 1: ReLU (if h > 0 then 1 else 0)
        relu_mask = (ops == 1)
        deriv[relu_mask] = (h[relu_mask] > 0).astype(np.float32)
        
        # 2: Sigmoid (h * (1 - h))
        sigmoid_mask = (ops == 2)
        deriv[sigmoid_mask] = h[sigmoid_mask] * (1.0 - h[sigmoid_mask])
        
        # 4: Neurone-Sonde (Read) is disconnected from gradient in standard way
        read_mask = (ops == 4)
        deriv[read_mask] = 0.0
        
        # 5: Swish
        swish_mask = (ops == 5)
        if np.any(swish_mask):
            x_safe = np.clip(x[swish_mask], -500, 500)
            sig = 1.0 / (1.0 + np.exp(-x_safe))
            deriv[swish_mask] = sig + x[swish_mask] * sig * (1.0 - sig)
            
        # 6: Sine
        sine_mask = (ops == 6)
        if np.any(sine_mask):
            deriv[sine_mask] = np.cos(x[sine_mask])
        
        return deriv

    def forward(self, inputs: List[float], iterations: int = 3) -> List[float]:
        """
        Executes a forward pass using synchronous propagation.
        Multi-step iteration allows depth propagation across the graph.
        """
        if len(inputs) != len(self.input_nodes):
            raise ValueError(f"Expected {len(self.input_nodes)} inputs, got {len(inputs)}")
            
        # La mémoire de travail injecte l'état du pas de temps précédent
        state = np.copy(self.recurrent_state)
        
        # Simplified propagation: run for N iterations to let signals propagate deep
        for _ in range(iterations):
            # 1. Feed inputs
            for i, input_val in enumerate(inputs):
                state[self.input_nodes[i]] = input_val
                
            # 2. Compute pre-activations
            pre_act = state @ self.weights + self.biases
            
            # 3. Apply activations (vectorized)
            state = self._activate(pre_act, self.operations)
            
            # Re-enforce input states (they shouldn't be overridden by network back-feed in simple FF)
            for i, input_val in enumerate(inputs):
                state[self.input_nodes[i]] = input_val
                
            # 3.5 Handle Memory Writes (Neurone-Greffier) without blocking NumPy execution
            # Commandment 3 (Performance) and 4 (Scalability)
            write_mask = (self.operations == 3) & (state > 0.5)
            if np.any(write_mask):
                write_indices = np.where(write_mask)[0]
                for idx in write_indices:
                    self.memory_buffer.append((int(idx), float(state[idx]), state.copy()))
                    
        # Sauvegarde de l'état final pour le prochain pas de temps (Short-Term Memory)
        self.recurrent_state = np.copy(state)
                    
        # Extract outputs
        return [float(state[out_id]) for out_id in self.output_nodes]

    def backward(self, inputs: List[float], targets: List[float], learning_rate: float = 0.1, iterations: int = 3) -> float:
        """
        Executes a forward pass then a backward pass to update weights via Gradient Descent.
        Returns the MSE loss.
        """
        # Forward pass caching states
        state = np.zeros((self.config.max_nodes,), dtype=np.float32)
        
        # We need to cache states to compute gradients properly, but for this simple 
        # MicroEngine, we'll just run forward to get the final steady state.
        for _ in range(iterations):
            for i, input_val in enumerate(inputs):
                state[self.input_nodes[i]] = input_val
            pre_act = state @ self.weights + self.biases
            state = self._activate(pre_act, self.operations)
            for i, input_val in enumerate(inputs):
                state[self.input_nodes[i]] = input_val
                
        # Compute Loss and initial gradients at outputs
        loss = 0.0
        grad_state = np.zeros_like(state)
        
        for i, out_id in enumerate(self.output_nodes):
            diff = state[out_id] - targets[i]
            loss += diff**2
            grad_state[out_id] = 2.0 * diff / len(self.output_nodes)
            
        loss /= len(self.output_nodes)
        
        # Backpropagate through iterations
        dW = np.zeros_like(self.weights)
        db = np.zeros_like(self.biases)
        
        for _ in range(iterations):
            # Derivative of activation
            dz = grad_state * self._activation_derivative(state, pre_act, self.operations)
            
            # Gradients for weights and biases
            # weight[source, target], so dz is at target, state is at source
            dW += np.outer(state, dz)
            db += dz
            
            # Propagate gradient backward to state for next unrolled step
            grad_state = self.weights @ dz
            
            # Inputs don't receive gradients that affect their state
            for i in self.input_nodes:
                grad_state[i] = 0.0
                
        # Clip gradients
        np.clip(dW, -1.0, 1.0, out=dW)
        np.clip(db, -1.0, 1.0, out=db)
        
        # Apply gradients
        self.weights -= learning_rate * dW
        self.biases -= learning_rate * db
        
        return float(loss)

