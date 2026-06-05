import numpy as np
from pydantic import BaseModel, Field
from typing import Dict, Optional

class RouterConfig(BaseModel):
    """Configuration for the Cognitive Router."""
    similarity_threshold: float = Field(default=0.5, description="Minimum similarity to route to an agent.")
    metric: str = Field(default="cosine", description="Distance metric: 'cosine' or 'l2'.")

class CognitiveRouter:
    """
    BGP-inspired Cognitive Router.
    Routes input semantic vectors to the most appropriate sub-network/agent based on a semantic routing table.
    """
    def __init__(self, config: RouterConfig):
        self.config = config
        # Routing table: agent_id -> centroid_vector (numpy array)
        self.routing_table: Dict[str, np.ndarray] = {}
        
    def announce_route(self, agent_id: str, centroid: np.ndarray) -> None:
        """
        Equivalent to a BGP UPDATE message. Adds or updates a route in the cognitive network.
        """
        self.routing_table[agent_id] = np.asarray(centroid, dtype=np.float32)
        
    def withdraw_route(self, agent_id: str) -> None:
        """
        Equivalent to a BGP WITHDRAW. Removes an agent from the routing table.
        """
        if agent_id in self.routing_table:
            del self.routing_table[agent_id]

    def route(self, query_vector: np.ndarray) -> Optional[str]:
        """
        Routes the query vector to the best agent based on highest similarity.
        Uses vectorized NumPy operations for high performance (AGIseed Commandment 3).
        """
        if not self.routing_table:
            return None
            
        query_vector = np.asarray(query_vector, dtype=np.float32)
        
        # Vectorized implementation for scalability
        agents = list(self.routing_table.keys())
        centroids = np.stack(list(self.routing_table.values()))
        
        if self.config.metric == "cosine":
            # Normalize query
            q_norm = np.linalg.norm(query_vector)
            if q_norm == 0:
                return None
            q_normalized = query_vector / q_norm
            
            # Normalize centroids
            c_norms = np.linalg.norm(centroids, axis=1)
            # Avoid division by zero
            c_norms[c_norms == 0] = 1e-9
            c_normalized = centroids / c_norms[:, np.newaxis]
            
            similarities = np.dot(c_normalized, q_normalized)
        elif self.config.metric == "l2":
            diffs = centroids - query_vector
            dists = np.linalg.norm(diffs, axis=1)
            # Convert L2 distance to similarity in [0, 1]
            similarities = 1.0 / (1.0 + dists)
        else:
            raise ValueError(f"Unknown metric: {self.config.metric}")
            
        best_idx = int(np.argmax(similarities))
        best_sim = similarities[best_idx]
        
        if best_sim >= self.config.similarity_threshold:
            return agents[best_idx]
        return None
