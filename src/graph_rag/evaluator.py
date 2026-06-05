"""
Phase 3: Evaluator module for AGIseed.
Responsible for scoring candidate architectures.
Commandement 3: Haute Performance (NumPy).
Commandement 9: Stabilité Numérique.
"""
import abc
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class EvaluatorConfig:
    """Hyperparameters for evaluation."""
    lambda_penalty: float = 0.01  # Sparsity/Size penalty
    min_accuracy: float = 0.0
    robustness_weight: float = 0.3  # Weight for robustness in scoring
    emergence_weight: float = 0.2   # Weight for emergence in scoring

class BaseEvaluator(abc.ABC):
    """Abstract base class for evaluators (Commandement 8: Extensible)."""
    @abc.abstractmethod
    def evaluate(self, accuracy: float, size_params: int) -> float:
        pass
    
    @abc.abstractmethod
    def score_robustness(self, metrics: dict) -> float:
        pass

class FitnessEvaluator(BaseEvaluator):
    """
    Evaluates proposed neural architectures and robustness metrics.
    """
    def __init__(self, config: EvaluatorConfig = None):
        self.config = config or EvaluatorConfig()

    def evaluate(self, accuracy: float, size_params: int) -> float:
        """
        Calculate fitness score: Score = Acc - lambda * log(Size)
        """
        if not np.isfinite(accuracy) or not np.isfinite(size_params):
            logger.warning("Non-finite values encountered in evaluation.")
            return -np.inf
        
        # Prevent log of negative or zero values
        safe_size = max(0, size_params)
        normalized_size = np.log1p(safe_size) 
        
        fitness = accuracy - (self.config.lambda_penalty * normalized_size)
        
        # Numerical stability handling
        if np.isnan(fitness) or np.isinf(fitness):
            logger.warning("Fitness calculation resulted in NaN or Inf.")
            return -np.inf
            
        return float(fitness)
    
    def score_robustness(self, metrics: dict) -> float:
        """
        Score robustness based on simulation metrics.
        
        Args:
            metrics: dict with keys:
                - energy_stability: how stable agent energy is over time
                - genome_diversity: genetic diversity in population
                - social_density: concentration of agents in same tiles
                - avg_energy: average energy level
        
        Returns:
            float: robustness score in [0, 1]
        """
        if not metrics:
            return 0.0
        
        try:
            energy_stability = float(metrics.get("energy_stability", 0.0))
            genome_diversity = float(metrics.get("genome_diversity", 0.0))
            social_density = float(metrics.get("social_density", 0.0))
            avg_energy = float(metrics.get("avg_energy", 50.0))
            
            # Clamp values to [0, 1]
            energy_stability = np.clip(energy_stability, 0.0, 1.0)
            genome_diversity = np.clip(genome_diversity, 0.0, 1.0)
            social_density = np.clip(social_density, 0.0, 1.0)
            energy_norm = np.clip(avg_energy / 100.0, 0.0, 1.0)
            
            # Composite robustness score
            # Higher stability + diversity = more robust
            # Healthy energy = more robust
            robustness = (
                0.4 * energy_stability +
                0.3 * genome_diversity +
                0.2 * energy_norm +
                0.1 * (1.0 - social_density)  # Avoid clustering
            )
            
            return float(np.clip(robustness, 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error computing robustness score: {e}")
            return 0.0
    
    def score_emergence(self, metrics: dict) -> float:
        """
        Score emergence level based on population metrics.
        Higher emergence = more interesting collective behavior.
        
        Args:
            metrics: dict with keys matching score_robustness
        
        Returns:
            float: emergence score in [0, 1]
        """
        if not metrics:
            return 0.0
        
        try:
            social_density = float(metrics.get("social_density", 0.0))
            genome_diversity = float(metrics.get("genome_diversity", 0.0))
            energy_stability = float(metrics.get("energy_stability", 0.0))
            
            social_density = np.clip(social_density, 0.0, 1.0)
            genome_diversity = np.clip(genome_diversity, 0.0, 1.0)
            energy_stability = np.clip(energy_stability, 0.0, 1.0)
            
            # Emergence = agents cooperating (high density) + genetically diverse
            # But also stable energy (not chaotic)
            emergence = (
                0.4 * social_density +
                0.5 * genome_diversity +
                0.1 * energy_stability
            )
            
            return float(np.clip(emergence, 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error computing emergence score: {e}")
            return 0.0
    
    def score_combined(self, accuracy: float, size_params: int, metrics: dict) -> float:
        """
        Combine accuracy, robustness, and emergence into a single score.
        
        Returns:
            float: combined score
        """
        base_fitness = self.evaluate(accuracy, size_params)
        robustness = self.score_robustness(metrics)
        emergence = self.score_emergence(metrics)
        
        # Normalize base_fitness to roughly [0, 1]
        safe_base = np.clip(base_fitness, 0.0, 1.0)
        
        combined = (
            0.5 * safe_base +
            self.config.robustness_weight * robustness +
            self.config.emergence_weight * emergence
        )
        
        return float(np.clip(combined, 0.0, 1.0))
