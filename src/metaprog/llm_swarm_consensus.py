"""
src/metaprog/llm_swarm_consensus.py — Consensus Latent Distribué Multi-LLMs (Arc 11 : Jalon M20).

Permet à un essaim de modèles de fondation hétérogènes de délibérer et converger
vers une décision unifiée sur la variété hypersphérique S^(D-1) sans aucune tokenisation textuelle.
Intègre le Barycentre de Sinkhorn-Wasserstein et la Médiane Sphérique de Weiszfeld BFT (Byzantine Fault Tolerant).

Conforme aux 12 Commandements AGIseed :
- 1. Hyper-Configurable (Dataclass SwarmConsensusConfig).
- 2. Modulaire (Découplé des architectures amont).
- 3. Haute Performance (NumPy vectorisé).
- 5. Transparent & Auditable (Traçabilité KuzuDB).
- 8. Extensible (Stratégies de consensus via Enum).
- 9. Stabilité Numérique (Unitarité hypersphérique, gestion des NaN/Inf).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import datetime
import numpy as np

from src.graph_rag.database import KuzuDatabase, DatabaseConfig


class ConsensusStrategy(str, Enum):
    """Stratégie d'agrégation d'intentions sur la sphère unitaire S^(D-1)."""
    WEIGHTED_SPHERICAL = "weighted_spherical"
    WEISZFELD_MEDIAN_BFT = "weiszfeld_median_bft"
    SINKHORN_BARYCENTER = "sinkhorn_barycenter"


@dataclass
class SwarmConsensusConfig:
    """Hyperparamètres pour la délibération continue de l'essaim multi-fondations."""
    consensus_strategy: ConsensusStrategy = ConsensusStrategy.WEISZFELD_MEDIAN_BFT
    max_weiszfeld_iters: int = 25
    convergence_tol: float = 1e-5
    sinkhorn_reg: float = 0.05
    sinkhorn_iters: int = 15
    polarization_threshold: float = 0.35  # Détection de schisme clanique
    byzantine_filter_enabled: bool = True
    byzantine_outlier_sigma: float = 2.5
    eps: float = 1e-12
    enable_kuzudb_logging: bool = True


@dataclass
class SwarmDeliberationResult:
    """Résultat formel d'un consensus d'essaim de fondation."""
    consensus_latent: np.ndarray
    cohesion_score: float
    angular_variance: float
    is_polarized: bool
    iterations_run: int
    participating_agents: int
    byzantine_agents_rejected: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMSwarmConsensus:
    """
    Moteur de délibération et de consensus continu pour essaims de modèles de fondation.
    Calcule le barycentre ou la médiane géodésique sur S^(D-1).
    """

    def __init__(self, config: Optional[SwarmConsensusConfig] = None, db: Optional[KuzuDatabase] = None):
        self.config = config or SwarmConsensusConfig()
        self.db = db

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Projette strictement sur la variété hypersphérique unitaire S^(D-1)."""
        if np.any(np.isnan(vec)) or np.any(np.isinf(vec)):
            vec = np.nan_to_num(vec, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(vec)) + self.config.eps
        return (vec / norm).astype(np.float32)

    def filter_byzantine_outliers(
        self,
        latents: np.ndarray,
        weights: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        Détecte et rejette les vecteurs d'activations d'agents byzantins ou corrompus
        dont l'écart angulaire à la médiane préliminaire excède k sigma.
        """
        N, D = latents.shape
        if N <= 3 or not self.config.byzantine_filter_enabled:
            w = np.ones(N, dtype=np.float32) / N if weights is None else weights
            return latents, w, 0

        # Médiane naïve de référence
        raw_mean = np.mean(latents, axis=0)
        ref_center = self._normalize(raw_mean)

        # Calcul des similarités cosinus et angles géodésiques
        cosines = np.clip(np.dot(latents, ref_center), -1.0, 1.0)
        angles = np.arccos(cosines)

        med_angle = float(np.median(angles))
        mad = float(np.median(np.abs(angles - med_angle))) + self.config.eps
        # Seuil de coupure robuste par MAD (Median Absolute Deviation)
        threshold = med_angle + self.config.byzantine_outlier_sigma * mad * 1.4826

        valid_mask = angles <= threshold
        rejected_count = int(np.sum(~valid_mask))

        if rejected_count == 0 or np.sum(valid_mask) < 2:
            w = np.ones(N, dtype=np.float32) / N if weights is None else weights
            return latents, w, 0

        filtered_latents = latents[valid_mask]
        w = np.ones(N, dtype=np.float32) if weights is None else weights
        filtered_weights = w[valid_mask]
        filtered_weights = filtered_weights / (np.sum(filtered_weights) + self.config.eps)

        return filtered_latents, filtered_weights.astype(np.float32), rejected_count

    def compute_weighted_spherical(
        self,
        latents: np.ndarray,
        weights: np.ndarray,
    ) -> Tuple[np.ndarray, int]:
        """Agrégation projective pondérée directe sur S^(D-1)."""
        combined = np.sum(latents * weights[:, np.newaxis], axis=0)
        return self._normalize(combined), 1

    def compute_weiszfeld_median(
        self,
        latents: np.ndarray,
        weights: np.ndarray,
    ) -> Tuple[np.ndarray, int]:
        """
        Calcule la Médiane Sphérique de Weiszfeld BFT sous métrique géodésique arccos.
        Garantit une robustesse maximale aux agents malveillants ou déviants.
        """
        N, D = latents.shape
        # Initialisation par le centroïde projectif pondéré
        current = self._normalize(np.sum(latents * weights[:, np.newaxis], axis=0))

        iters = 0
        for it in range(self.config.max_weiszfeld_iters):
            iters += 1
            cosines = np.clip(np.dot(latents, current), -1.0, 1.0)
            angles = np.arccos(cosines)  # Distances géodésiques sur S^(D-1)

            # Poids de Weiszfeld : w_i / sin(theta_i) ou w_i / max(theta_i, eps)
            safe_dist = np.maximum(angles, 1e-4)
            inv_dist = weights / safe_dist
            inv_sum = np.sum(inv_dist) + self.config.eps

            step_vector = np.sum(latents * (inv_dist[:, np.newaxis]), axis=0) / inv_sum
            next_center = self._normalize(step_vector)

            shift = float(np.linalg.norm(next_center - current))
            current = next_center
            if shift < self.config.convergence_tol:
                break

        return current, iters

    def compute_sinkhorn_barycenter(
        self,
        latents: np.ndarray,
        weights: np.ndarray,
    ) -> Tuple[np.ndarray, int]:
        """
        Barycentre de Sinkhorn-Wasserstein géodésique régularisé par entropie.
        Préserve la géométrie multi-modale tout en favorisant la convergence douce.
        """
        N, D = latents.shape
        current = self._normalize(np.sum(latents * weights[:, np.newaxis], axis=0))

        iters = 0
        for it in range(self.config.sinkhorn_iters):
            iters += 1
            # Matrice de coût géodésique (1 - cos)
            costs = 1.0 - np.clip(np.dot(latents, current), -1.0, 1.0)
            # Pondération de Gibbs régularisée
            gibbs_weights = np.exp(-costs / max(1e-4, self.config.sinkhorn_reg)) * weights
            gibbs_weights = gibbs_weights / (np.sum(gibbs_weights) + self.config.eps)

            next_center = self._normalize(np.sum(latents * gibbs_weights[:, np.newaxis], axis=0))
            shift = float(np.linalg.norm(next_center - current))
            current = next_center
            if shift < self.config.convergence_tol:
                break

        return current, iters

    def deliberate(
        self,
        agent_latents: List[np.ndarray],
        agent_weights: Optional[List[float]] = None,
        swarm_context: str = "general_deliberation",
    ) -> SwarmDeliberationResult:
        """
        Exécute la délibération continue de l'essaim et retourne le Gigatoken de consensus.
        """
        if not agent_latents:
            raise ValueError("Au moins un agent doit participer à la délibération.")

        arr_latents = np.stack([self._normalize(l) for l in agent_latents], axis=0)
        N, D = arr_latents.shape

        if agent_weights is None:
            weights = np.ones(N, dtype=np.float32) / N
        else:
            weights = np.asarray(agent_weights, dtype=np.float32)
            weights = weights / (np.sum(weights) + self.config.eps)

        # 1. Filtrage byzantin si activé
        clean_latents, clean_weights, byz_count = self.filter_byzantine_outliers(arr_latents, weights)

        # 2. Résolution du consensus selon la stratégie
        if self.config.consensus_strategy == ConsensusStrategy.WEISZFELD_MEDIAN_BFT:
            consensus_vec, iters = self.compute_weiszfeld_median(clean_latents, clean_weights)
        elif self.config.consensus_strategy == ConsensusStrategy.SINKHORN_BARYCENTER:
            consensus_vec, iters = self.compute_sinkhorn_barycenter(clean_latents, clean_weights)
        else:
            consensus_vec, iters = self.compute_weighted_spherical(clean_latents, clean_weights)

        # 3. Métrologie de cohésion et polarisation
        cosines = np.clip(np.dot(clean_latents, consensus_vec), -1.0, 1.0)
        cohesion = float(np.mean(cosines))
        ang_var = float(1.0 - np.linalg.norm(np.mean(clean_latents, axis=0)))
        is_polar = bool(ang_var >= self.config.polarization_threshold)

        result = SwarmDeliberationResult(
            consensus_latent=consensus_vec,
            cohesion_score=round(cohesion, 4),
            angular_variance=round(ang_var, 4),
            is_polarized=is_polar,
            iterations_run=iters,
            participating_agents=N,
            byzantine_agents_rejected=byz_count,
            metadata={"context": swarm_context, "strategy": self.config.consensus_strategy.value},
        )

        # 4. Traçabilité KuzuDB (Commandement 5)
        if self.config.enable_kuzudb_logging and self.db is not None:
            self._log_deliberation_to_kuzudb(result, swarm_context)

        return result

    def _log_deliberation_to_kuzudb(self, res: SwarmDeliberationResult, context: str):
        """Persiste le consensus d'essaim dans KuzuDB sous forme de LogEvent."""
        try:
            now = int(datetime.datetime.now().timestamp() * 1000)
            evt_id = f"evt_swarm_consensus_{now}"
            msg = (
                f"Consensus Essaim ({res.metadata.get('strategy')}) : N={res.participating_agents} | "
                f"Cohésion={res.cohesion_score} | Rejets Byz={res.byzantine_agents_rejected} | "
                f"Polarisé={res.is_polarized}"
            )
            cypher = (
                f"CREATE (e:LogEvent {{"
                f"id: '{evt_id}', "
                f"event_type: 'SWARM_LATENT_CONSENSUS', "
                f"message: '{msg}', "
                f"timestamp: {now}, "
                f"level: 'INFO'"
                f"}})"
            )
            self.db.execute_cypher(cypher)
        except Exception:
            pass
