from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Tuple

class BaseAgent(ABC):
    """
    Interface Abstraite pour les Agents.
    Encapsule la logique du cerveau (MLP, Mamba, Jeepa).
    """
    
    @abstractmethod
    def reset_state(self):
        """Réinitialise l'état interne (mémoire, H_prev, etc.) de l'agent au début d'une ère."""
        pass
        
    @abstractmethod
    def forward(self, obs: np.ndarray) -> np.ndarray:
        """
        Calcule les logits d'actions à partir de l'observation.
        Met à jour l'état interne automatiquement.
        """
        pass
        
    @abstractmethod
    def get_size(self) -> int:
        """Retourne la taille du modèle pour le calcul de la pénalité de fitness."""
        pass
        
    @abstractmethod
    def mutate(self):
        """Mute les poids internes pour l'algorithme génétique."""
        pass
        
    @abstractmethod
    def clone(self) -> 'BaseAgent':
        """Retourne une copie profonde de l'agent (sans historique cognitif)."""
        pass
