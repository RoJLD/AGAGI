"""
src/evolution/tribal_dialect.py — Analyseur Métrologique des Dialectes Tribaux (Arc 5).
Mesure la spécialisation lexicale et l'émergence de sous-dialectes par rôle :
SCOUT (Éclaireur) vs HUNTER (Chasseur) vs CRAFTER (Artisan).
Conforme aux 12 Commandements AGIseed (NumPy, vectorisé, stable, modulaire).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class TribalDialectConfig:
    """Hyperparamètres pour la métrologie des dialectes de meute."""
    vector_dim: int = 4              # Dimension des vecteurs de parole LU
    min_samples_per_role: int = 3    # Échantillons minimaux pour calculer un centroïde valide
    epsilon: float = 1e-7            # Stabilité numérique anti-division par zéro


class TribalDialectAnalyzer:
    """
    Collecte les vecteurs d'émission vocale par rôle et quantifie :
    1. La cohésion intra-rôle (variance autour du centroïde du rôle).
    2. La divergence inter-rôles (distance cosinus entre les répertoires).
    3. L'indice de spécialisation tribale (S_tribal in [0, 1]).
    """
    def __init__(self, config: Optional[TribalDialectConfig] = None):
        self.config = config or TribalDialectConfig()
        self.utterances: Dict[str, List[np.ndarray]] = {
            "SCOUT": [],
            "HUNTER": [],
            "CRAFTER": [],
            "STANDARD": []
        }

    def record_utterance(self, role: str, vector: np.ndarray):
        """Enregistre un vecteur vocal émis par un agent d'un rôle donné."""
        normalized_role = role.upper() if role.upper() in self.utterances else "STANDARD"
        v = np.asarray(vector, dtype=np.float32).flatten()
        if len(v) >= self.config.vector_dim:
            self.utterances[normalized_role].append(v[:self.config.vector_dim])

    def compute_role_centroids(self) -> Dict[str, Optional[np.ndarray]]:
        """Calcule le vecteur centroïde moyen pour chaque rôle."""
        centroids = {}
        for role, samples in self.utterances.items():
            if len(samples) >= self.config.min_samples_per_role:
                mat = np.stack(samples, axis=0)
                mean_v = np.mean(mat, axis=0)
                norm = np.linalg.norm(mean_v) + self.config.epsilon
                centroids[role] = (mean_v / norm).astype(np.float32)
            else:
                centroids[role] = None
        return centroids

    def compute_intra_cohesion(self) -> Dict[str, float]:
        """Mesure la compacité/cohérence sémantique interne de chaque rôle (similarité cosinus moyenne au centroïde)."""
        centroids = self.compute_role_centroids()
        cohesion = {}
        for role, samples in self.utterances.items():
            c = centroids.get(role)
            if c is not None and len(samples) >= self.config.min_samples_per_role:
                mat = np.stack(samples, axis=0)
                norms = np.linalg.norm(mat, axis=1, keepdims=True) + self.config.epsilon
                normalized_mat = mat / norms
                sims = np.dot(normalized_mat, c)
                cohesion[role] = float(np.clip(np.mean(sims), -1.0, 1.0))
            else:
                cohesion[role] = 0.0
        return cohesion

    def compute_inter_divergence(self) -> Dict[str, Any]:
        """
        Calcule la matrice de divergence cosinus entre les rôles principaux.
        Divergence = 1.0 - CosineSimilarity.
        """
        centroids = self.compute_role_centroids()
        roles = ["SCOUT", "HUNTER", "CRAFTER"]
        pairwise_div = {}
        inter_sims = []

        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                r1, r2 = roles[i], roles[j]
                c1, c2 = centroids.get(r1), centroids.get(r2)
                pair_key = f"{r1}_vs_{r2}"
                if c1 is not None and c2 is not None:
                    sim = float(np.dot(c1, c2))
                    sim = float(np.clip(sim, -1.0, 1.0))
                    div = float(1.0 - sim)
                    pairwise_div[pair_key] = round(div, 4)
                    inter_sims.append(sim)
                else:
                    pairwise_div[pair_key] = 0.0

        specialization_index = 0.0
        if inter_sims:
            # S_tribal = 1.0 - mean(cosine_similarity)
            mean_sim = float(np.mean(inter_sims))
            specialization_index = float(np.clip(1.0 - mean_sim, 0.0, 2.0) / 2.0)

        return {
            "pairwise_divergence": pairwise_div,
            "specialization_index": round(specialization_index, 4),
            "is_specialized": specialization_index > 0.05
        }

    def summarize(self) -> Dict[str, Any]:
        """Retourne un bilan synthétique pour observabilité et persistance KuzuDB."""
        cohesion = self.compute_intra_cohesion()
        inter = self.compute_inter_divergence()
        sample_counts = {k: len(v) for k, v in self.utterances.items()}

        return {
            "sample_counts": sample_counts,
            "intra_cohesion": cohesion,
            "pairwise_divergence": inter["pairwise_divergence"],
            "specialization_index": inter["specialization_index"],
            "is_specialized": inter["is_specialized"],
            "verdict": "DIALECTS_EMERGED" if inter["is_specialized"] else "MONOLITHIC_LANGUAGE"
        }
