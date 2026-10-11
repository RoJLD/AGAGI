"""
src/graph_rag/realtime_graphrag_bridge.py — Pont Graph-RAG Bidirectionnel Temps Réel (Arc 14 : Jalon M33).

Assure le monitoring continu de la santé cognitive et de la dispersion sémantique
de la civilisation in-world. Détecte les stagnations d'entropie collective et injecte
dynamiquement des attracteurs téléologiques orthogonaux rafraîchis depuis la mémoire KuzuDB.

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass RealtimeBridgeConfig).
- 2. Modulaire (Découplage KuzuDB et contrôleurs in-world).
- 3. Haute Performance (Vectorisation NumPy).
- 5. Transparent & Auditable (Journalisation des interventions).
- 9. Stabilité Numérique (Protection stricte contre NaN/Inf).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import datetime
import numpy as np

from src.graph_rag.database import KuzuDatabase


@dataclass
class RealtimeBridgeConfig:
    """Hyperparamètres pour le pont Graph-RAG bidirectionnel temps réel."""
    latent_dim: int = 64
    stagnation_variance_threshold: float = 0.08
    min_history_steps: int = 4
    history_window_size: int = 15
    intervention_boost: float = 0.35
    seed: int = 42
    eps: float = 1e-12


class RealtimeGraphRAGBridge:
    """
    Pont synchrone entre le flux d'inférence continue in-world
    et le graphe de connaissances symbolique KuzuDB.
    """

    def __init__(
        self,
        config: Optional[RealtimeBridgeConfig] = None,
        db: Optional[KuzuDatabase] = None,
    ):
        self.config = config or RealtimeBridgeConfig()
        self.db = db
        self.rng = np.random.RandomState(self.config.seed)

        self.step_count = 0
        self.interventions_count = 0
        self.history_consensus: List[np.ndarray] = []
        self.intervention_history: List[Dict[str, Any]] = []

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Projette sur S^(D-1) avec protection stricte contre les NaN/Inf."""
        arr = np.asarray(vec, dtype=np.float32)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        return (arr / norm).astype(np.float32)

    def compute_consensus_variance(self) -> float:
        """
        Calcule la variance angulaire et la dispersion des consensus récents.
        Retourne la variance ou float('nan') si l'historique est insuffisant.
        """
        if len(self.history_consensus) < 2:
            return float("nan")

        stack = np.stack(self.history_consensus, axis=0)
        center = np.mean(stack, axis=0)
        center_norm = float(np.linalg.norm(center)) + self.config.eps
        center_unit = center / center_norm

        # Variance euclidienne moyenne par rapport au barycentre unitaire
        diffs = stack - center_unit
        variance = float(np.mean(np.sum(diffs ** 2, axis=1)))
        return variance

    def synthesize_innovative_goal(self, current_stagnant_goal: np.ndarray) -> np.ndarray:
        """
        Génère un attracteur orthogonal perturbateur sur S^(D-1) brisant la stagnation.
        """
        z_curr = self._normalize(current_stagnant_goal)
        # Générer une direction exploratoire
        rand_dir = self.rng.randn(self.config.latent_dim).astype(np.float32)
        rand_dir = self._normalize(rand_dir)

        # Projection de Gram-Schmidt pour obtenir une composante orthogonale pure
        proj = float(np.dot(rand_dir, z_curr)) * z_curr
        ortho = rand_dir - proj
        ortho_norm = float(np.linalg.norm(ortho)) + self.config.eps
        ortho_dir = ortho / ortho_norm

        # Interpolation sphérique injectant de la nouveauté
        alpha = float(np.clip(self.config.intervention_boost, 0.1, 0.9))
        innov_vec = (1.0 - alpha) * z_curr + alpha * ortho_dir
        return self._normalize(innov_vec)

    def record_graph_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Enregistre un événement de supervision dans la base KuzuDB si connectée.
        """
        if self.db is None:
            return
        try:
            now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cypher = f"CREATE (e:LogEvent {{id: '{event_type}_{self.step_count}', type: '{event_type}', timestamp: '{now_iso}'}})"
            self.db.execute_cypher(cypher)
        except Exception:
            pass  # Non-bloquant si la table n'est pas encore déclarée

    def monitor_and_sync(
        self,
        current_consensus: np.ndarray,
        conductor_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Observe le pas de civilisation, évalue la diversité sémantique
        et déclenche une intervention réparatrice si une stagnation est détectée.
        """
        self.step_count += 1
        conductor_metrics = conductor_metrics or {}

        z_clean = self._normalize(current_consensus)
        self.history_consensus.append(z_clean)
        if len(self.history_consensus) > self.config.history_window_size:
            self.history_consensus.pop(0)

        var = self.compute_consensus_variance()
        stagnation = False
        intervention_triggered = False
        refreshed_goal = None

        if not np.isnan(var) and len(self.history_consensus) >= self.config.min_history_steps:
            if var < self.config.stagnation_variance_threshold:
                stagnation = True
                intervention_triggered = True
                self.interventions_count += 1

                # Génération d'un nouveau cap téléologique
                refreshed_goal = self.synthesize_innovative_goal(z_clean)

                event_dict = {
                    "step": self.step_count,
                    "variance": var,
                    "reason": "STAGNATION_ENTROPY_COLLAPSE",
                    "intervention_id": self.interventions_count,
                }
                self.intervention_history.append(event_dict)
                self.record_graph_event("TELEOLOGICAL_INTERVENTION", event_dict)

        return {
            "step": self.step_count,
            "variance": float(var) if not np.isnan(var) else 0.0,
            "stagnation_detected": stagnation,
            "intervention_triggered": intervention_triggered,
            "refreshed_goal": refreshed_goal,
            "interventions_count": self.interventions_count,
        }
