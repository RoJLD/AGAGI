"""
src/metaprog/llm_latent_steerer.py — Guidage Téléologique et Activation Steering Continu pour LLMs.

Projet: AGIseed / AGAGI (Arc 10 : The Foundation Bridge — Jalon M18)
Objectif: Orienter continûment les représentations internes des LLMs vers un attracteur de but
          (z_goal in S^(D-1)) sans rallonger le contexte textuel, via l'état adjoint (Adjoint State)
          et l'ingénierie d'activations continues (Representation Engineering).

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): SteeringConfig hyper-paramétrable par Dataclass.
- Commandement 2 (Modulaire): Découplage strict entre la mécanique d'orientation et le modèle hôte.
- Commandement 3 (Haute Performance): Opérations 100% vectorisées NumPy sans allocations redondantes.
- Commandement 8 (Extensible): Extensible à tout backend PyTorch / Transformers ou API.
- Commandement 9 (Stabilité Numérique): Bornage lipschitzien strict et préservation de la norme ||h||.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class SteeringMode(str, Enum):
    """Modes de guidage d'activation interne."""
    ADDITIVE_PROJECTION = "additive_projection"   # h' = normalize(h + alpha * P^T z_goal)
    ORTHOGONAL_ROTATION = "orthogonal_rotation"   # Rotation géodésique sur la variété vers z_goal
    TELEOLOGICAL_ADJOINT = "teleological_adjoint" # Équation adjointe combinant prédiction et attracteur futur


@dataclass
class SteeringConfig:
    """Hyperparamètres pour le guidage continu des activations de LLMs."""
    steering_strength: float = 0.35              # Facteur d'injection alpha dans [0.0, 1.0]
    mode: SteeringMode = SteeringMode.ADDITIVE_PROJECTION
    teleological_horizon_steps: int = 4          # Pas de projection prospective intérieure
    regularization_lambda: float = 0.05          # Pénalité de déviation pour préserver la cohérence syntaxique
    preserve_norm: bool = True                   # Maintien de l'énergie d'activation native du LLM
    eps: float = 1e-12


class LLMLatentSteerer:
    """
    Moteur de guidage téléologique continu pour modèles de fondation.
    Injecte un attracteur de but z_goal in S^(D-1) dans l'état caché natif h in R^(D_model).
    """

    def __init__(self, config: Optional[SteeringConfig] = None):
        self.config = config or SteeringConfig()
        self.total_steer_events = 0
        self.cumulative_goal_gain = 0.0

    def backproject_goal_to_hidden(
        self,
        goal_latent: np.ndarray,
        projection_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Rétro-projette un Gigatoken de but z_goal in S^(D-1) vers l'espace d'activations natif R^(D_model).
        Utilise la pseudo-inverse ou la transposée de la matrice d'isométrie semi-orthogonale.
        """
        z_norm = goal_latent / (np.linalg.norm(goal_latent) + self.config.eps)
        # Comme projection_matrix est semi-orthogonale (Q in R^(D_model x D_latent)), P^T est son adjointe
        h_goal = np.dot(projection_matrix, z_norm)
        norm_h = np.linalg.norm(h_goal) + self.config.eps
        return (h_goal / norm_h).astype(np.float32)

    def steer_hidden_state(
        self,
        raw_hidden_state: np.ndarray,
        goal_latent: np.ndarray,
        projection_matrix: np.ndarray,
        strength: Optional[float] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Oriente un état d'activation natif h vers l'attracteur z_goal.
        Retourne (h_steered, gain_cosinus_vers_but).
        """
        alpha = strength if strength is not None else self.config.steering_strength
        orig_norm = float(np.linalg.norm(raw_hidden_state))
        if orig_norm < self.config.eps:
            orig_norm = 1.0

        h_goal = self.backproject_goal_to_hidden(goal_latent, projection_matrix)

        if self.config.mode == SteeringMode.ORTHOGONAL_ROTATION:
            # Rotation géodésique sur la sphère unitaire
            u_h = raw_hidden_state / orig_norm
            u_g = h_goal / (np.linalg.norm(h_goal) + self.config.eps)
            # Composante orthogonale
            overlap = float(np.dot(u_h, u_g))
            ortho = u_g - overlap * u_h
            ortho_norm = np.linalg.norm(ortho) + self.config.eps
            ortho_dir = ortho / ortho_norm
            # Rotation continue d'angle theta proportionnel à alpha
            theta = alpha * np.arccos(np.clip(overlap, -1.0, 1.0))
            steered_unit = np.cos(theta) * u_h + np.sin(theta) * ortho_dir
            steered_hidden = steered_unit * orig_norm
        else:
            # Mode ADDITIVE_PROJECTION ou TELEOLOGICAL_ADJOINT
            # h' = (1 - alpha) * h + alpha * (||h|| * h_goal)
            steered_raw = (1.0 - alpha) * raw_hidden_state + alpha * (orig_norm * h_goal)
            if self.config.preserve_norm:
                steered_norm = np.linalg.norm(steered_raw) + self.config.eps
                steered_hidden = (steered_raw / steered_norm) * orig_norm
            else:
                steered_hidden = steered_raw

        # Évaluation du gain d'alignement avec le but dans l'espace latent
        z_orig = np.dot(raw_hidden_state, projection_matrix)
        z_steered = np.dot(steered_hidden, projection_matrix)
        sim_before = float(np.dot(z_orig, goal_latent) / (np.linalg.norm(z_orig) * np.linalg.norm(goal_latent) + self.config.eps))
        sim_after = float(np.dot(z_steered, goal_latent) / (np.linalg.norm(z_steered) * np.linalg.norm(goal_latent) + self.config.eps))
        gain = sim_after - sim_before

        self.total_steer_events += 1
        self.cumulative_goal_gain += gain

        return steered_hidden.astype(np.float32), gain

    def compute_teleological_rollout(
        self,
        initial_hidden: np.ndarray,
        goal_latent: np.ndarray,
        projection_matrix: np.ndarray,
        steps: Optional[int] = None,
    ) -> List[np.ndarray]:
        """
        Déroule une trajectoire de guidage téléologique intérieure en K pas discrets.
        Modélise la convergence de pensée vers la cible avant émission de réponse.
        """
        n_steps = steps if steps is not None else self.config.teleological_horizon_steps
        trajectory = [initial_hidden.copy()]

        curr = initial_hidden.copy()
        for s in range(n_steps):
            # Annealing progressif de l'attraction téléologique
            step_alpha = self.config.steering_strength * (1.0 + 0.1 * s)
            curr, _ = self.steer_hidden_state(
                curr, goal_latent, projection_matrix, strength=min(0.85, step_alpha)
            )
            trajectory.append(curr.copy())

        return trajectory

    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques d'orientation de pensée."""
        mean_gain = (self.cumulative_goal_gain / max(1, self.total_steer_events)) if self.total_steer_events > 0 else 0.0
        return {
            "total_steer_events": self.total_steer_events,
            "mean_goal_alignment_gain": round(mean_gain, 4),
            "mode": self.config.mode.value,
            "steering_strength": self.config.steering_strength,
        }
