import numpy as np
from pydantic import BaseModel, Field
from typing import List, Tuple

class ConsensusConfig(BaseModel):
    """Configuration for the Weighted Consensus mechanism."""
    temperature: float = Field(default=1.0, description="Temperature for softmax weighting. Lower means sharper distribution.")
    min_fitness_threshold: float = Field(default=0.0, description="Minimum fitness required to participate in consensus.")

class WeightedConsensus:
    """
    Simplified Raft/Paxos voting mechanism based on historical fitness scores.
    Aggregates predictions from multiple agents into a single consensus prediction.
    """
    def __init__(self, config: ConsensusConfig = None):
        self.config = config or ConsensusConfig()

    def _safe_softmax(self, x: np.ndarray) -> np.ndarray:
        """
        Numerically stable softmax to avoid exploding gradients and NaNs.
        (AGIseed Commandment 9: Stabilité Numérique)
        """
        x_safe = np.nan_to_num(x, nan=np.nanmean(x) if not np.isnan(x).all() else 0.0, posinf=1e6, neginf=-1e6)
        # Shift to prevent overflow
        x_shifted = x_safe - np.max(x_safe)
        exp_x = np.exp(x_shifted / max(self.config.temperature, 1e-6))
        sum_exp_x = np.sum(exp_x)
        if sum_exp_x == 0:
            return np.ones_like(exp_x) / len(exp_x)
        return exp_x / sum_exp_x

    def vote(self, predictions: List[Tuple[str, np.ndarray, float]]) -> np.ndarray:
        """
        Takes a list of (agent_id, prediction_vector, fitness_score).
        Returns the weighted consensus prediction.
        """
        if not predictions:
            raise ValueError("No predictions provided for consensus.")
            
        # Filter out agents below fitness threshold
        valid_preds = [(pred, fit) for _, pred, fit in predictions if fit >= self.config.min_fitness_threshold]
        
        if not valid_preds:
            # Fallback if everyone is below threshold: take all
            valid_preds = [(pred, fit) for _, pred, fit in predictions]
            
        vectors = np.stack([p[0] for p in valid_preds])
        fitnesses = np.array([p[1] for p in valid_preds], dtype=np.float32)
        
        # Calculate weights using stable softmax
        weights = self._safe_softmax(fitnesses)
        
        # Weighted sum of predictions (vectorized)
        # weights shape: (N,) -> (N, 1) to broadcast with vectors shape (N, D)
        consensus = np.sum(vectors * weights[:, np.newaxis], axis=0)
        
        return consensus
