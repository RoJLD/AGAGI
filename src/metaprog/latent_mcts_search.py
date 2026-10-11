"""
src/metaprog/latent_mcts_search.py — Recherche Arborescente Monte Carlo dans l'Espace Latent (Arc 12 : Jalon M25).

Remplace le Chain-of-Thought textuel verbeux par un Test-Time Compute (TTC) continu direct :
exploration prospective en arbre d'activations sur la variété S^(D-1) guidée par la proximité géodésique
à l'attracteur téléologique futur z_goal, sans générer un seul token textuel.

Conforme aux 12 Commandements AGIseed :
- 1. Hyper-Configurable (Dataclass LatentMCTSConfig).
- 2. Modulaire (Découplé des environnements physiques).
- 3. Haute Performance (Vectorisation NumPy, recherche arborescente rapide).
- 9. Stabilité Numérique (Scores Q bornés in [-1, 1], normalisation stricte S^(D-1)).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import numpy as np


@dataclass
class LatentMCTSConfig:
    """Hyperparamètres pour la recherche MCTS continue dans l'espace latent."""
    num_simulations: int = 50
    max_depth: int = 5
    num_action_candidates: int = 6  # Éventail d'actions motrices potentielles
    c_puct: float = 1.414  # Constante d'exploration UCB1
    gamma_discount: float = 0.95
    step_size: float = 0.25  # Ampleur de transition dans l'espace latent
    action_seed: int = 42
    eps: float = 1e-12


class LatentMCTSNode:
    """Nœud d'état latent dans l'arbre de recherche MCTS."""

    def __init__(self, state_latent: np.ndarray, parent: Optional["LatentMCTSNode"] = None, action_taken: Optional[int] = None):
        self.state_latent = state_latent
        self.parent = parent
        self.action_taken = action_taken
        self.children: Dict[int, "LatentMCTSNode"] = {}
        self.visit_count: int = 0
        self.total_value: float = 0.0

    @property
    def q_value(self) -> float:
        if self.visit_count == 0:
            return 0.0
        return self.total_value / self.visit_count


class LatentMCTSSearch:
    """
    Moteur de planification prospective dans l'espace latent continu.
    Explore l'arbre des états futurs et sélectionne l'action maximisant l'utilité téléologique.
    """

    def __init__(self, config: Optional[LatentMCTSConfig] = None):
        self.config = config or LatentMCTSConfig()
        # Matrice de générateurs d'actions : A_dirs in R^(num_actions x latent_dim)
        rng = np.random.RandomState(self.config.action_seed)
        dim = 64
        raw_dirs = rng.randn(self.config.num_action_candidates, dim).astype(np.float32)
        # Normalisation unitaire de chaque action candidate
        norms = np.linalg.norm(raw_dirs, axis=1, keepdims=True) + self.config.eps
        self.action_generators = (raw_dirs / norms).astype(np.float32)

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Projette strictement sur S^(D-1)."""
        arr = np.asarray(vec, dtype=np.float32)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        return (arr / norm).astype(np.float32)

    def transition_latent(self, current_state: np.ndarray, action_idx: int) -> np.ndarray:
        """Modèle de dynamique interne : s_{t+1} = norm(s_t + alpha * a)."""
        dim = current_state.shape[0]
        if self.action_generators.shape[1] != dim:
            # Adaptation dimensionnelle si nécessaire
            rng = np.random.RandomState(self.config.action_seed + dim)
            raw = rng.randn(self.config.num_action_candidates, dim).astype(np.float32)
            self.action_generators = (raw / (np.linalg.norm(raw, axis=1, keepdims=True) + self.config.eps)).astype(np.float32)

        action_dir = self.action_generators[action_idx]
        next_state = current_state + self.config.step_size * action_dir
        return self._normalize(next_state)

    def evaluate_leaf(self, state: np.ndarray, goal_latent: np.ndarray) -> float:
        """Évaluation heuristique téléologique : proximité cosinus in [-1, 1]."""
        sim = float(np.dot(self._normalize(state), self._normalize(goal_latent)))
        return float(np.clip(sim, -1.0, 1.0))

    def plan_trajectory(
        self,
        current_state_latent: np.ndarray,
        goal_latent: np.ndarray,
    ) -> Tuple[int, np.ndarray, Dict[str, Any]]:
        """
        Exécute la recherche MCTS et retourne (meilleure_action, prochain_état_anticipé, métadonnées).
        """
        root_state = self._normalize(current_state_latent)
        goal = self._normalize(goal_latent)
        root = LatentMCTSNode(state_latent=root_state)

        for _ in range(self.config.num_simulations):
            node = root
            depth = 0

            # 1. Sélection (Selection)
            while node.children and depth < self.config.max_depth:
                # UCB1 Selection
                best_action = None
                best_ucb = -float("inf")
                total_visits = max(1, node.visit_count)

                for a in range(self.config.num_action_candidates):
                    if a in node.children:
                        child = node.children[a]
                        u = child.q_value + self.config.c_puct * np.sqrt(np.log(total_visits) / (1 + child.visit_count))
                    else:
                        # Priorité d'exploration pour les actions non encore visitées
                        u = 10.0 + np.random.uniform(0, 0.01)

                    if u > best_ucb:
                        best_ucb = u
                        best_action = a

                if best_action not in node.children:
                    break
                node = node.children[best_action]
                depth += 1

            # 2. Expansion
            unexpanded_actions = [a for a in range(self.config.num_action_candidates) if a not in node.children]
            if unexpanded_actions and depth < self.config.max_depth:
                chosen_action = unexpanded_actions[0]
                next_st = self.transition_latent(node.state_latent, chosen_action)
                new_child = LatentMCTSNode(state_latent=next_st, parent=node, action_taken=chosen_action)
                node.children[chosen_action] = new_child
                node = new_child

            # 3. Évaluation / Rollout
            value = self.evaluate_leaf(node.state_latent, goal)

            # 4. Rétropropagation (Backpropagation)
            curr = node
            while curr is not None:
                curr.visit_count += 1
                curr.total_value += value
                value *= self.config.gamma_discount
                curr = curr.parent

        # Sélection de l'action la plus visitée à la racine
        if not root.children:
            best_action = 0
            predicted_next_state = self.transition_latent(root_state, 0)
        else:
            best_action = max(root.children.keys(), key=lambda a: root.children[a].visit_count)
            predicted_next_state = root.children[best_action].state_latent

        initial_proximity = float(np.dot(root_state, goal))
        final_proximity = float(np.dot(predicted_next_state, goal))
        planning_gain = max(0.0, final_proximity - initial_proximity)

        metadata = {
            "best_action": int(best_action),
            "simulations_run": self.config.num_simulations,
            "root_visits": root.visit_count,
            "initial_proximity": round(initial_proximity, 4),
            "final_proximity": round(final_proximity, 4),
            "planning_gain": round(planning_gain, 4),
            "action_visit_counts": {a: child.visit_count for a, child in root.children.items()},
        }

        return int(best_action), predicted_next_state, metadata
