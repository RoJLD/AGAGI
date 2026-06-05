import numpy as np
from pydantic import BaseModel, Field
from typing import Dict

class HGTConfig(BaseModel):
    """Configuration for Horizontal Gene Transfer."""
    crossover_rate: float = Field(default=0.5, description="Probability of taking a gene from donor.")
    mutation_rate: float = Field(default=0.01, description="Probability of random mutation during transfer.")
    mutation_scale: float = Field(default=0.1, description="Scale of Gaussian noise for mutation.")

class HorizontalGeneTransfer:
    """
    Horizontal Gene Transfer (HGT).
    Transfers or merges weights (synapses) between two networks (NumPy arrays).
    """
    def __init__(self, config: HGTConfig):
        self.config = config
        
    def check_compatibility(self, recipient: np.ndarray, donor: np.ndarray) -> bool:
        """
        Ensures the two weight matrices have the same shape before transfer.
        """
        return recipient.shape == donor.shape

    def transfer_layer(self, recipient_weights: np.ndarray, donor_weights: np.ndarray) -> np.ndarray:
        """
        Performs a crossover between recipient and donor weights.
        Returns the new offspring weights using NumPy vectorization (AGIseed Commandment 3).
        """
        if not self.check_compatibility(recipient_weights, donor_weights):
            raise ValueError(f"Shape mismatch: Recipient {recipient_weights.shape} vs Donor {donor_weights.shape}")
            
        # Create a mask for crossover (1 means take from donor, 0 means take from recipient)
        mask = np.random.rand(*recipient_weights.shape) < self.config.crossover_rate
        
        # Combine weights based on mask
        offspring_weights = np.where(mask, donor_weights, recipient_weights)
        
        # Apply mutation
        mutation_mask = np.random.rand(*offspring_weights.shape) < self.config.mutation_rate
        noise = np.random.normal(loc=0.0, scale=self.config.mutation_scale, size=offspring_weights.shape)
        
        offspring_weights = np.where(mutation_mask, offspring_weights + noise, offspring_weights)
        
        # Clip to prevent explosive weights (AGIseed Commandment 9)
        offspring_weights = np.clip(offspring_weights, -1e3, 1e3)
        
        return offspring_weights
        
    def merge_graphs(self, recipient_graph: Dict[str, np.ndarray], donor_graph: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Applies HGT across an entire network graph represented as a dictionary of layer weights.
        """
        offspring_graph = {}
        for layer_name, recipient_w in recipient_graph.items():
            if layer_name in donor_graph:
                offspring_graph[layer_name] = self.transfer_layer(recipient_w, donor_graph[layer_name])
            else:
                # If layer doesn't exist in donor, keep recipient's layer
                offspring_graph[layer_name] = recipient_w.copy()
                
        return offspring_graph
