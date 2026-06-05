from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import numpy as np

class BaseWorld(ABC):
    """
    Interface Abstraite pour les Environnements (Worlds).
    Implémente le pattern Gymnasium (OpenAI Gym).
    """
    
    def __init__(self, size: int):
        self.size = size
        self.agents = []
        self.dead_agents = []
        self.tick_count = 0
        
    @abstractmethod
    def reset(self):
        """Réinitialise le monde et retourne les observations initiales."""
        pass
        
    @abstractmethod
    def step(self):
        """
        Avance la simulation d'un tick.
        Demande les actions aux agents via agent.forward(obs), puis applique la physique.
        """
        pass
        
    def get_agent_observation(self, agent_dict: Dict) -> np.ndarray:
        """Calcule le vecteur d'observation pour un agent spécifique."""
        pass

    @abstractmethod
    def add_agent(self, agent_model, **kwargs):
        """Ajoute un agent (model) dans l'environnement."""
        pass
        
    def run_era(self, num_ticks: int = 200) -> List[Dict]:
        """
        Exécute une ère complète.
        Retourne la liste des statistiques des agents à la fin de l'ère.
        """
        self.reset()
        self.dead_agents = []
        for t in range(num_ticks):
            self.step()
            # Si tous les agents meurent avant la fin, on arrête
            if len(self.agents) == 0:
                break
                
        # Calculer le fitness pour tous les agents survivants ou morts
        stats = []
        for a in self.agents + self.dead_agents:
            fitness = max(0.0, a["energy"] * 0.5) + (a["age"] * 0.1)
            # Pénalité de taille
            penalty = a["model"].get_size() * 0.005
            fitness -= penalty
            
            stats.append({
                "score": fitness,
                "age": a["age"],
                "energy": a["energy"],
                "preys": a.get("preys_eaten", 0),
                "last_spoken": a.get("last_spoken", [0.0, 0.0, 0.0, 0.0]),
                "total_dreams": a.get("total_dreams", 0),
                "total_reflexes": a.get("total_reflexes", 0),
                "model": a["model"]
            })
            
        return sorted(stats, key=lambda x: x["score"], reverse=True)
