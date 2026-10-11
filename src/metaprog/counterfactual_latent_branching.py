"""
src/metaprog/counterfactual_latent_branching.py — Raisonnement Contrefactuel sans Risque (Arc 15 : Jalon M37).

Permet aux agents d'effectuer des simulations intérieures "What-If" sur S^(D-1)
en évaluant plusieurs trajectoires d'action alternatives et leurs conséquences
face aux intentions d'autrui modélisées par la Théorie de l'Esprit (ToM),
sans dépenser d'énergie ni s'exposer physiquement dans le monde réel.

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass CounterfactualConfig).
- 2. Modulaire (Composant pur de raisonnement latent découplé).
- 3. Haute Performance (Vectorisation NumPy des branches contrefactuelles).
- 9. Stabilité Numérique (Toutes les branches projetées sur S^(D-1)).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


@dataclass
class CounterfactualConfig:
    """Hyperparamètres pour la ramification contrefactuelle latente."""
    latent_dim: int = 64
    num_branches: int = 8
    perturbation_scale: float = 0.25
    risk_penalty_weight: float = 1.20
    seed: int = 42
    eps: float = 1e-12


class CounterfactualLatentBranching:
    """
    Simulateur de branches contrefactuelles évaluant mentalement
    les scénarios d'action alternatifs avant passage à l'acte.
    """

    def __init__(self, config: Optional[CounterfactualConfig] = None):
        self.config = config or CounterfactualConfig()
        self.rng = np.random.RandomState(self.config.seed)

    def _generate_orthogonal_perturbations(self, base_vector: np.ndarray, count: int) -> np.ndarray:
        """
        Génère `count` perturbations strictement tangentes à base_vector.
        Retourne un tenseur de forme (count, latent_dim).
        """
        dim = self.config.latent_dim
        raw_noise = self.rng.randn(count, dim).astype(np.float32)

        base_col = base_vector.reshape(-1, 1)
        # Projection orthogonale : v_perp = v - (v . base) * base
        dots = np.dot(raw_noise, base_col)  # (count, 1)
        perp = raw_noise - dots * base_vector  # (count, dim)

        norms = np.linalg.norm(perp, axis=1, keepdims=True) + self.config.eps
        return (perp / norms).astype(np.float32)

    def simulate_branches(
        self,
        current_action: np.ndarray,
        partner_beliefs: List[np.ndarray],
        environmental_target: Optional[np.ndarray] = None,
    ) -> List[Dict[str, Any]]:
        """
        Déploie plusieurs scénarios contrefactuels autour de l'action envisagée
        et prédit l'issue de chaque scénario face aux intentions supposées des partenaires.
        """
        act = np.asarray(current_action, dtype=np.float32)
        act = np.nan_to_num(act, nan=0.0, posinf=1.0, neginf=-1.0)
        norm_a = float(np.linalg.norm(act))
        if norm_a < 1e-6:
            act = self.rng.randn(self.config.latent_dim).astype(np.float32)
            norm_a = float(np.linalg.norm(act)) + self.config.eps
        base_unit = (act / norm_a).astype(np.float32)

        # Cible environnementale par défaut = base_unit
        if environmental_target is not None:
            tgt = np.asarray(environmental_target, dtype=np.float32)
            tgt = np.nan_to_num(tgt, nan=0.0, posinf=1.0, neginf=-1.0)
            t_norm = float(np.linalg.norm(tgt))
            if t_norm < 1e-6:
                tgt = self.rng.randn(self.config.latent_dim).astype(np.float32)
                t_norm = float(np.linalg.norm(tgt)) + self.config.eps
            target_unit = (tgt / t_norm).astype(np.float32)
        else:
            target_unit = base_unit

        # Génération des perturbations tangentielles
        num_branches = max(2, self.config.num_branches)
        tangents = self._generate_orthogonal_perturbations(base_unit, num_branches - 1)

        branches = []

        # Branche 0 : Action nominale inchangée
        branches.append(base_unit)

        # Branches 1..N : Variantes géodésiques
        scale = self.config.perturbation_scale
        for t in tangents:
            v_cand = base_unit + scale * t
            v_norm = float(np.linalg.norm(v_cand)) + self.config.eps
            branches.append((v_cand / v_norm).astype(np.float32))

        # Évaluation des branches
        evaluations = []
        for idx, b_vec in enumerate(branches):
            # 1. Alignement sur la cible environnementale (gain primaire)
            env_utility = float(np.dot(b_vec, target_unit))

            # 2. Risque d'incompatibilité avec les partenaires perçus
            partner_risks = []
            if partner_beliefs:
                for p_hat in partner_beliefs:
                    p = np.asarray(p_hat, dtype=np.float32)
                    p = np.nan_to_num(p, nan=0.0, posinf=1.0, neginf=-1.0)
                    pn = float(np.linalg.norm(p)) + self.config.eps
                    p_unit = p / pn

                    # Si l'action s'oppose à l'intention du partenaire, friction/risque élevé
                    cos_p = float(np.dot(b_vec, p_unit))
                    friction = float(np.clip(1.0 - cos_p, 0.0, 2.0))
                    partner_risks.append(friction)

            mean_risk = float(np.mean(partner_risks)) if partner_risks else float("nan")

            # Score d'utilité contrefactuelle net
            if np.isnan(mean_risk):
                net_score = env_utility
            else:
                net_score = env_utility - self.config.risk_penalty_weight * mean_risk

            evaluations.append({
                "branch_id": idx,
                "is_nominal": bool(idx == 0),
                "latent_vector": b_vec,
                "environmental_utility": env_utility,
                "mean_partner_friction": mean_risk,
                "net_score": float(net_score),
            })

        return evaluations

    def select_optimal_branch(
        self,
        current_action: np.ndarray,
        partner_beliefs: List[np.ndarray],
        environmental_target: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Simule toutes les ramifications et sélectionne l'action contrefactuelle
        maximisant le bien-être net sans risque de collision ou de trahison.
        """
        branches = self.simulate_branches(
            current_action=current_action,
            partner_beliefs=partner_beliefs,
            environmental_target=environmental_target,
        )

        # Sélection de la branche avec le meilleur score
        best_branch = max(branches, key=lambda b: b["net_score"])

        decision_report = {
            "selected_branch_id": best_branch["branch_id"],
            "selected_was_nominal": best_branch["is_nominal"],
            "net_score": best_branch["net_score"],
            "environmental_utility": best_branch["environmental_utility"],
            "partner_friction": best_branch["mean_partner_friction"],
            "num_evaluated_branches": len(branches),
        }

        return best_branch["latent_vector"], decision_report
