"""
src/metaprog/self_reflective_latent_critic.py — Critique Réflexive et Auto-Correction Sémantique (Arc 12 : Jalon M26).

Évalue et corrige les dérives sémantiques ou dangereuses d'un Gigatoken d'action z in S^(D-1)
par descente de gradient riemannienne sur la variété hypersphérique unité (I - z z^T) \nabla E(z).
Élimine les hallucinations et assure l'auto-alignement avant toute action physique.

Conforme aux 12 Commandements AGIseed :
- 1. Hyper-Configurable (Dataclass SelfReflectiveCriticConfig).
- 2. Modulaire (Découplé des modèles de fondation amont).
- 3. Haute Performance (Gradient riemannien vectorisé NumPy).
- 9. Stabilité Numérique (Projection tangente stricte, unitarité S^(D-1)).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import numpy as np


@dataclass
class SelfReflectiveCriticConfig:
    """Hyperparamètres pour la critique d'énergie et l'auto-correction géodésique."""
    max_correction_steps: int = 15
    learning_rate: float = 0.20
    energy_convergence_tol: float = 1e-4
    constitutional_weight: float = 1.0
    danger_aversion_weight: float = 1.5
    perception_fidelity_weight: float = 0.8
    danger_safety_margin: float = 0.25  # Seuil maximal d'overlap avec un état létal
    eps: float = 1e-12


@dataclass
class ReflectionResult:
    """Résultat de l'auto-réflexion et correction géodésique."""
    corrected_latent: np.ndarray
    initial_energy: float
    final_energy: float
    energy_reduction: float
    steps_taken: int
    is_fully_aligned: bool
    violations_detected: List[str] = field(default_factory=list)


class SelfReflectiveLatentCritic:
    """
    Critique d'énergie réflexif opérant directement sur la variété hypersphérique S^(D-1).
    """

    def __init__(self, config: Optional[SelfReflectiveCriticConfig] = None):
        self.config = config or SelfReflectiveCriticConfig()

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Projette sur S^(D-1) avec protection stricte contre NaN/Inf."""
        arr = np.asarray(vec, dtype=np.float32)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        return (arr / norm).astype(np.float32)

    def compute_critic_energy_and_gradient(
        self,
        z: np.ndarray,
        constitutional_vector: np.ndarray,
        danger_signatures: List[np.ndarray],
        context_perception: Optional[np.ndarray] = None,
    ) -> Tuple[float, np.ndarray, List[str]]:
        """
        Calcule l'énergie de non-conformité E(z) et le gradient riemannien tangent \nabla_S E(z).
        E(z) = 0 indique une conformité totale.
        """
        D = z.shape[0]
        grad_euclidean = np.zeros(D, dtype=np.float32)
        total_energy = 0.0
        violations = []

        # 1. Énergie de déviation constitutionnelle : E_const = (1 - <z, c>)^2 si <z, c> < 0.70
        const_overlap = float(np.dot(z, constitutional_vector))
        if const_overlap < 0.70:
            deficit = 0.70 - const_overlap
            total_energy += self.config.constitutional_weight * (deficit ** 2)
            grad_euclidean += -2.0 * self.config.constitutional_weight * deficit * constitutional_vector
            violations.append(f"Déficit d'alignement constitutionnel : {const_overlap:.3f} < 0.70")

        # 2. Énergie de danger / létalité : E_danger = (<z, d> - margin)^2 si <z, d> > margin
        for idx, d_sig in enumerate(danger_signatures):
            danger_overlap = float(np.dot(z, d_sig))
            if danger_overlap > self.config.danger_safety_margin:
                excess = danger_overlap - self.config.danger_safety_margin
                total_energy += self.config.danger_aversion_weight * (excess ** 2)
                grad_euclidean += 2.0 * self.config.danger_aversion_weight * excess * d_sig
                violations.append(f"Proximité de signature létale #{idx} : {danger_overlap:.3f}")

        # 3. Énergie de cohérence perceptive locale (optionnelle)
        if context_perception is not None:
            percept_overlap = float(np.dot(z, context_perception))
            if percept_overlap < 0.20:
                p_deficit = 0.20 - percept_overlap
                total_energy += self.config.perception_fidelity_weight * (p_deficit ** 2)
                grad_euclidean += -2.0 * self.config.perception_fidelity_weight * p_deficit * context_perception

        # Projection riemannienne sur l'espace tangent de S^(D-1) : grad_S = (I - z z^T) grad
        grad_tangent = grad_euclidean - float(np.dot(z, grad_euclidean)) * z

        return float(total_energy), grad_tangent.astype(np.float32), violations

    def reflect_and_correct(
        self,
        proposed_latent: np.ndarray,
        constitutional_vector: np.ndarray,
        danger_signatures: Optional[List[np.ndarray]] = None,
        context_perception: Optional[np.ndarray] = None,
    ) -> ReflectionResult:
        """
        Exécute la boucle d'auto-réflexion continue par descente géodésique.
        Corrige z_prop vers z_corr in S^(D-1).
        """
        z_curr = self._normalize(proposed_latent)
        c_vec = self._normalize(constitutional_vector)
        d_sigs = [self._normalize(d) for d in (danger_signatures or [])]
        p_vec = self._normalize(context_perception) if context_perception is not None else None

        initial_energy, _, initial_violations = self.compute_critic_energy_and_gradient(
            z_curr, c_vec, d_sigs, p_vec
        )

        steps = 0
        energy = initial_energy
        for step in range(self.config.max_correction_steps):
            if energy < self.config.energy_convergence_tol:
                break
            steps += 1
            energy, grad_tangent, _ = self.compute_critic_energy_and_gradient(
                z_curr, c_vec, d_sigs, p_vec
            )

            grad_norm = float(np.linalg.norm(grad_tangent))
            if grad_norm < 1e-6:
                break

            # Pas de descente géodésique le long de la sphère
            step_dir = grad_tangent / grad_norm
            z_next = z_curr - self.config.learning_rate * step_dir
            z_curr = self._normalize(z_next)

        final_energy, _, final_violations = self.compute_critic_energy_and_gradient(
            z_curr, c_vec, d_sigs, p_vec
        )
        reduction = max(0.0, initial_energy - final_energy)

        return ReflectionResult(
            corrected_latent=z_curr,
            initial_energy=round(initial_energy, 4),
            final_energy=round(final_energy, 4),
            energy_reduction=round(reduction, 4),
            steps_taken=steps,
            is_fully_aligned=bool(final_energy < self.config.energy_convergence_tol),
            violations_detected=initial_violations,
        )
