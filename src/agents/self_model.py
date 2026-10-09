"""
src/agents/self_model.py — Métacognition & Modèle de Soi (Self-Model / EXP-11).
Permet à un agent d'évaluer ses propres capacités avant d'agir :
- Prédit la dépense métabolique (fatigue/caloric cost) associée à une tâche.
- Estime un indice de confiance métacognitive [0, 1].
- Ajuste dynamiquement le budget de calcul Test-Time Compute (TTC) selon le doute interne.
Conforme aux 12 Commandements AGIseed (1. Flexible, 3. NumPy vectorisé, 8. Extensible).
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


@dataclass
class SelfModelConfig:
    """Hyperparamètres du Self-Model métacognitif."""
    latent_dim: int = 16
    learning_rate: float = 0.05
    confidence_threshold: float = 0.65
    max_ttc_budget_boost: int = 4
    epsilon: float = 1e-6


class SelfModel:
    """
    Réseau métacognitif compact prédisant l'état interne de l'agent :
    1. Estimation de la dépense calorique Delta_E
    2. Score de confiance prédictive
    """

    def __init__(self, state_dim: int, config: Optional[SelfModelConfig] = None):
        self.state_dim = state_dim
        self.config = config or SelfModelConfig()
        
        # Poids de projection métacognitive : state -> latent -> [pred_cost, pred_confidence]
        limit = 1.0 / np.sqrt(max(1, state_dim))
        self.W_cost = np.random.uniform(-limit, limit, (state_dim,)).astype(np.float32)
        self.b_cost = 0.0
        
        self.W_conf = np.random.uniform(-limit, limit, (state_dim,)).astype(np.float32)
        self.b_conf = 0.0
        
        # Statistiques d'étalonnage
        self.total_evaluations: int = 0
        self.cumulative_prediction_error: float = 0.0

    def evaluate_state(self, state_vec: np.ndarray) -> Tuple[float, float, bool]:
        """
        Évalue un état ou une observation.
        Retourne :
        - predicted_cost : coût énergétique estimé (>= 0.0)
        - confidence : certitude interne in [0, 1]
        - needs_deliberation : booléen activant un surplus de TTC (MCTS/rêve)
        """
        s = np.asarray(state_vec, dtype=np.float32).flatten()
        if len(s) != self.state_dim:
            if len(s) < self.state_dim:
                s = np.pad(s, (0, self.state_dim - len(s)))
            else:
                s = s[:self.state_dim]

        # 1. Estimation du coût métabolique
        raw_cost = float(np.dot(s, self.W_cost) + self.b_cost)
        pred_cost = max(0.01, float(raw_cost))

        # 2. Estimation de la confiance via sigmoïde
        raw_conf = float(np.dot(s, self.W_conf) + self.b_conf)
        confidence = 1.0 / (1.0 + np.exp(-np.clip(raw_conf, -10.0, 10.0)))

        # 3. Arbitrage de délibération cognitive
        needs_deliberation = bool(confidence < self.config.confidence_threshold)

        self.total_evaluations += 1
        return pred_cost, float(confidence), needs_deliberation

    def learn_step(self, state_vec: np.ndarray, actual_cost: float, task_success: bool):
        """
        Mise à jour en ligne des poids du modèle de soi.
        Apprentissage supervisé léger (MSE sur le coût et BCE sur le succès).
        """
        s = np.asarray(state_vec, dtype=np.float32).flatten()
        if len(s) != self.state_dim:
            if len(s) < self.state_dim:
                s = np.pad(s, (0, self.state_dim - len(s)))
            else:
                s = s[:self.state_dim]

        lr = self.config.learning_rate

        # Mise à jour coût énergétique
        pred_cost = float(np.dot(s, self.W_cost) + self.b_cost)
        err_cost = pred_cost - actual_cost
        grad_W_cost = np.clip(err_cost * s, -5.0, 5.0)
        self.W_cost -= lr * grad_W_cost
        self.b_cost -= lr * np.clip(err_cost, -5.0, 5.0)

        # Mise à jour confiance
        raw_conf = float(np.dot(s, self.W_conf) + self.b_conf)
        prob_conf = 1.0 / (1.0 + np.exp(-np.clip(raw_conf, -10.0, 10.0)))
        target_conf = 1.0 if task_success else 0.0
        err_conf = prob_conf - target_conf
        grad_W_conf = np.clip(err_conf * s, -5.0, 5.0)
        self.W_conf -= lr * grad_W_conf
        self.b_conf -= lr * np.clip(err_conf, -5.0, 5.0)

        self.cumulative_prediction_error += abs(err_cost)

    def get_ttc_budget_adjustment(self, confidence: float) -> int:
        """
        Calcule l'ajustement du budget de recherche MCTS.
        Plus l'agent doute (confiance basse), plus il alloue de profondeur de calcul.
        """
        uncertainty = max(0.0, 1.0 - confidence)
        return int(np.round(uncertainty * self.config.max_ttc_budget_boost))
