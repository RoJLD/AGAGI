"""
src/metaprog/latent_theory_of_mind.py — Moteur de Théorie de l'Esprit Latente (Arc 15 : Jalon M36).

Permet aux agents et aux essaims de modéliser les états mentaux d'autrui (Theory of Mind de 2nd ordre)
directement sur la variété hypersphérique S^(D-1) sans génération de tokens textuels.

Fonctionnalités clés :
1. Modélisation récursive des croyances et intentions d'autrui : z_hat_j in S^(D-1).
2. Mise à jour bayésienne / filtre géodésique riemannien sur S^(D-1).
3. Détection prédictive de défection byzantine avant délibération formelle.
4. Synthèse de carte mentale collective (barycentre d'intentions perçues).

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass ToMConfig).
- 2. Modulaire (Découplé du moteur physique et des modèles de langage).
- 3. Haute Performance (Vectorisation NumPy stricte).
- 9. Stabilité Numérique (Projection géodésique unitaire, élimination des NaN/Inf).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


@dataclass
class ToMConfig:
    """Hyperparamètres pour le moteur de Théorie de l'Esprit Latente."""
    latent_dim: int = 64
    learning_rate: float = 0.20
    byzantine_divergence_threshold: float = 0.40  # Seuil de distance cosinus suspecte
    max_tracked_agents: int = 64
    decay_rate: float = 0.05
    seed: int = 42
    eps: float = 1e-12


class LatentTheoryOfMindEngine:
    """
    Moteur de Théorie de l'Esprit (ToM) continue pour agents autonomes sur S^(D-1).
    Estime et met à jour les croyances sur les intentions d'autrui par descente riemannienne.
    """

    def __init__(self, config: Optional[ToMConfig] = None):
        self.config = config or ToMConfig()
        self.rng = np.random.RandomState(self.config.seed)

        # Croyances : observer_id -> (target_id -> z_hat in S^(D-1))
        self.mental_models: Dict[str, Dict[str, np.ndarray]] = {}

        # Confiances : observer_id -> (target_id -> confidence in [0, 1])
        self.confidence_scores: Dict[str, Dict[str, float]] = {}

        # Historiques d'observations
        self.observation_counts: Dict[str, Dict[str, int]] = {}

    def _ensure_model_exists(self, observer_id: str, target_id: str) -> np.ndarray:
        """Garantit qu'une croyance a priori unitaire existe pour la cible."""
        if observer_id not in self.mental_models:
            self.mental_models[observer_id] = {}
            self.confidence_scores[observer_id] = {}
            self.observation_counts[observer_id] = {}

        if target_id not in self.mental_models[observer_id]:
            # Initialisation sur S^(D-1)
            v = self.rng.randn(self.config.latent_dim).astype(np.float32)
            norm = float(np.linalg.norm(v)) + self.config.eps
            self.mental_models[observer_id][target_id] = (v / norm).astype(np.float32)
            self.confidence_scores[observer_id][target_id] = 0.10
            self.observation_counts[observer_id][target_id] = 0

        return self.mental_models[observer_id][target_id]

    def observe_agent_step(
        self,
        observer_id: str,
        target_id: str,
        target_action_vector: np.ndarray,
        target_context: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Observe une manifestation motrice ou communicationnelle de l'agent cible
        et raffine le modèle mental de ses intentions par mise à jour géodésique.
        """
        z_prior = self._ensure_model_exists(observer_id, target_id)

        # Nettoyage et normalisation du vecteur d'action observé
        act = np.asarray(target_action_vector, dtype=np.float32)
        if np.any(np.isnan(act)) or np.any(np.isinf(act)):
            act = np.nan_to_num(act, nan=0.0, posinf=1.0, neginf=-1.0)

        # Si l'action a une dimension différente de latent_dim, la projeter ou la padder
        if act.shape[0] != self.config.latent_dim:
            if act.shape[0] < self.config.latent_dim:
                act = np.pad(act, (0, self.config.latent_dim - act.shape[0]))
            else:
                act = act[:self.config.latent_dim]

        act_norm = float(np.linalg.norm(act)) + self.config.eps
        act_unit = (act / act_norm).astype(np.float32)

        # Si un contexte est fourni, le combiner
        if target_context is not None:
            ctx = np.asarray(target_context, dtype=np.float32)
            ctx = np.nan_to_num(ctx, nan=0.0, posinf=1.0, neginf=-1.0)
            if ctx.shape[0] == self.config.latent_dim:
                ctx_norm = float(np.linalg.norm(ctx)) + self.config.eps
                act_unit = 0.70 * act_unit + 0.30 * (ctx / ctx_norm)
                act_unit = act_unit / (float(np.linalg.norm(act_unit)) + self.config.eps)

        # Gradient tangentiel riemannien vers l'observation sur S^(D-1)
        # G = (I - z z^T) * act_unit
        z_col = z_prior.reshape(-1, 1)
        proj_tangent = act_unit - np.dot(z_col, np.dot(z_col.T, act_unit)).reshape(-1)

        # Déplacement géodésique
        lr = self.config.learning_rate
        z_updated = z_prior + lr * proj_tangent
        norm_up = float(np.linalg.norm(z_updated)) + self.config.eps
        z_posterior = (z_updated / norm_up).astype(np.float32)

        self.mental_models[observer_id][target_id] = z_posterior

        # Mise à jour de la confiance bayésienne
        obs_count = self.observation_counts[observer_id][target_id] + 1
        self.observation_counts[observer_id][target_id] = obs_count
        conf = float(np.clip(1.0 - np.exp(-0.15 * obs_count), 0.10, 0.99))
        self.confidence_scores[observer_id][target_id] = conf

        # Mesure d'alignement a posteriori
        cos_align = float(np.dot(z_prior, z_posterior))

        return {
            "target_id": target_id,
            "observations_count": obs_count,
            "confidence": conf,
            "cosine_update_alignment": cos_align,
            "z_posterior_norm": float(np.linalg.norm(z_posterior)),
        }

    def predict_target_intention(self, observer_id: str, target_id: str) -> np.ndarray:
        """Retourne l'estimation unitaire courante de l'intention de la cible."""
        return self._ensure_model_exists(observer_id, target_id).copy()

    def assess_cooperation_risk(
        self,
        observer_id: str,
        target_id: str,
        common_goal: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Évalue le risque de trahison ou de défection byzantine de la cible
        vis-à-vis d'un objectif de coopération commun sur S^(D-1).
        """
        z_hat = self._ensure_model_exists(observer_id, target_id)
        conf = self.confidence_scores[observer_id][target_id]

        g = np.asarray(common_goal, dtype=np.float32)
        g = np.nan_to_num(g, nan=0.0, posinf=1.0, neginf=-1.0)
        g_norm = float(np.linalg.norm(g)) + self.config.eps
        g_unit = (g / g_norm).astype(np.float32)

        # Distance cosinus = 1 - dot(z_hat, g_unit)
        cos_sim = float(np.dot(z_hat, g_unit))
        cos_dist = float(np.clip(1.0 - cos_sim, 0.0, 2.0))

        # Risque de défection calibré
        is_suspicious = bool(cos_dist > self.config.byzantine_divergence_threshold and conf >= 0.25)
        defection_prob = float(np.clip(0.50 * cos_dist * conf, 0.0, 1.0))

        return {
            "target_id": target_id,
            "cosine_alignment_to_goal": cos_sim,
            "cosine_distance": cos_dist,
            "confidence": conf,
            "is_suspicious": is_suspicious,
            "defection_probability": defection_prob,
        }

    def synthesize_collective_mental_map(
        self,
        observer_id: str,
        target_ids: Optional[List[str]] = None,
    ) -> np.ndarray:
        """
        Synthétise le barycentre géodésique des intentions perçues de l'essaim.
        Permet à l'agent de se représenter l'ambiance intentionnelle globale du groupe.
        """
        if observer_id not in self.mental_models or not self.mental_models[observer_id]:
            v = self.rng.randn(self.config.latent_dim).astype(np.float32)
            return (v / (float(np.linalg.norm(v)) + self.config.eps)).astype(np.float32)

        targets = target_ids or list(self.mental_models[observer_id].keys())
        active_latents = [
            self.mental_models[observer_id][t]
            for t in targets
            if t in self.mental_models[observer_id]
        ]

        if not active_latents:
            v = self.rng.randn(self.config.latent_dim).astype(np.float32)
            return (v / (float(np.linalg.norm(v)) + self.config.eps)).astype(np.float32)

        # Barycentre pondéré par la confiance
        weights = [self.confidence_scores[observer_id][t] for t in targets if t in self.mental_models[observer_id]]
        w_sum = sum(weights) + self.config.eps
        weights_norm = [w / w_sum for w in weights]

        barycenter = np.zeros(self.config.latent_dim, dtype=np.float32)
        for w, z in zip(weights_norm, active_latents):
            barycenter += w * z

        bary_norm = float(np.linalg.norm(barycenter)) + self.config.eps
        return (barycenter / bary_norm).astype(np.float32)
