"""
src/agents/embodied_foundation_agent.py — Contrôleur Incarné In-World pour Modèles de Fondation (Arc 11 : Jalon M21).

Permet à un modèle de fondation ou à un consensus d'essaim (Gigatoken continu z in S^(D-1))
de piloter ou guider directement un agent physique incarné dans la biosphère 3D (World 1/2/3)
sans aucune invite textuelle ni tokenisation.

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass EmbodiedAgentConfig).
- 2. Modulaire (Découplage perception/fondation/actionneur).
- 3. Haute Performance (Opérations matricielles NumPy vectorisées).
- 9. Stabilité Numérique (Bornes tanh, gestion stricte des NaN/Inf).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import numpy as np

from src.agents.mamba_agent import MambaAgent


@dataclass
class EmbodiedAgentConfig:
    """Hyperparamètres pour le contrôleur incarné piloté par modèle de fondation."""
    latent_dim: int = 64
    num_inputs: int = 59
    num_outputs: int = 108
    foundation_coupling_strength: float = 0.40  # beta : poids du guidage de fondation
    actuator_seed: int = 42
    isocaloric: bool = True  # Règle métabolique stricte (P4.2)
    eps: float = 1e-12


class EmbodiedFoundationAgent:
    """
    Agent incarné dont les décisions motrices combinent la réactivité réflexe locale
    (ODE Liquid Mamba) et les directives téléologiques continues du modèle de fondation.
    """

    def __init__(
        self,
        config: Optional[EmbodiedAgentConfig] = None,
        base_agent: Optional[MambaAgent] = None,
    ):
        self.config = config or EmbodiedAgentConfig()
        self.num_inputs = self.config.num_inputs
        self.num_outputs = self.config.num_outputs

        # Agent moteur sous-jacent
        if base_agent is not None:
            self.base_agent = base_agent
        else:
            self.base_agent = MambaAgent(
                num_inputs=self.config.num_inputs,
                num_outputs=self.config.num_outputs,
                isocaloric=self.config.isocaloric,
            )

        # Matrice d'actionnement semi-orthogonale reliant la sphère latente aux sorties motrices
        # W_act in R^(latent_dim x num_outputs)
        rng = np.random.RandomState(self.config.actuator_seed)
        raw_w = rng.randn(self.config.latent_dim, self.config.num_outputs).astype(np.float32)
        u, _, vt = np.linalg.svd(raw_w, full_matrices=False)
        self.actuator_matrix = np.dot(u, vt).astype(np.float32)

        # Dernier vecteur téléologique reçu (z in S^(D-1))
        self.current_goal_latent: Optional[np.ndarray] = None

    def set_foundation_goal(self, goal_latent: np.ndarray):
        """
        Injecte un nouveau Gigatoken de but téléologique issu du modèle de fondation ou du consensus d'essaim.
        """
        arr = np.asarray(goal_latent, dtype=np.float32)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        self.current_goal_latent = (arr / norm).astype(np.float32)

    def compute_foundation_actuation(self, goal_latent: np.ndarray) -> np.ndarray:
        """
        Projette le Gigatoken latent continu vers l'espace moteur [num_outputs] via saturation tanh.
        """
        if goal_latent.shape[0] != self.config.latent_dim:
            # Adaptation dimensionnelle par troncature/padding
            if goal_latent.shape[0] > self.config.latent_dim:
                g = goal_latent[:self.config.latent_dim]
            else:
                g = np.pad(goal_latent, (0, self.config.latent_dim - goal_latent.shape[0]))
        else:
            g = goal_latent

        actuation = np.dot(g, self.actuator_matrix)
        return np.tanh(actuation).astype(np.float32)

    def forward(self, observation: np.ndarray) -> np.ndarray:
        """
        Exécute un pas de décision motrice combinant le réflexe local et le guidage de fondation.
        """
        obs = np.asarray(observation, dtype=np.float32)
        # 1. Action réflexe de l'agent moteur local
        if hasattr(self.base_agent, "step") and callable(self.base_agent.step):
            u_reactive = self.base_agent.step(obs)
        elif hasattr(self.base_agent, "forward") and callable(self.base_agent.forward):
            u_reactive = self.base_agent.forward(obs)
        else:
            raise AttributeError("L'agent sous-jacent ne possède ni forward() ni step().")

        if u_reactive.ndim > 1:
            u_reactive = u_reactive.squeeze(0)

        # 2. Si aucune directive de fondation n'est injectée, comportement réflexe pur
        if self.current_goal_latent is None or self.config.foundation_coupling_strength <= 0.0:
            return u_reactive.astype(np.float32)

        # 3. Calcul de la composante téléologique continue
        u_foundation = self.compute_foundation_actuation(self.current_goal_latent)

        # 4. Fusion convexe stable
        beta = float(np.clip(self.config.foundation_coupling_strength, 0.0, 1.0))
        u_combined = (1.0 - beta) * u_reactive + beta * u_foundation

        # Protection NaN/Inf (Commandement 9)
        if np.any(np.isnan(u_combined)) or np.any(np.isinf(u_combined)):
            u_combined = np.nan_to_num(u_combined, nan=0.0, posinf=1.0, neginf=-1.0)

        return u_combined.astype(np.float32)

    def step(self, observation: np.ndarray) -> np.ndarray:
        """Alias pour compatibilité avec l'API Gym/RL standard."""
        return self.forward(observation)
