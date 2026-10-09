"""
Module: lu_state_bridge.py
Projet: AGIseed / AGAGI
Description: StateBridge — Alignement d'espaces latents hétérogènes pour le Langage Ultime (LU).
Permet la communication latente directe (M2M) entre agents dotés de connectomes
ou dimensions asymétriques sans ré-entraînement, via Procruste Orthogonal et Projection Affine Régularisée.

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): StateBridgeConfig dataclass hyper-paramétrable.
- Commandement 2 (Modulaire): Séparation stricte de l'alignement géométrique.
- Commandement 3 (Haute Performance): Algorithmes 100% vectorisés en NumPy (SVD, projection matricielle).
- Commandement 8 (Extensible): Interface BaseLatentBridge.
- Commandement 9 (Stabilité Numérique): Guards contre NaN/Inf, pseudo-inversion régularisée (L2 / Ridge).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
import numpy as np


class AlignmentStrategy(str, Enum):
    """Stratégies d'alignement pour le StateBridge."""
    ORTHOGONAL_PROCRUSTES = "orthogonal_procrustes"  # Préservation isométrique stricte (mêmes dims)
    REGULARIZED_AFFINE = "regularized_affine"        # Ridge Regression (dims variables Da != Db)
    AUTO = "auto"                                    # Sélection automatique selon les dimensions


@dataclass
class StateBridgeConfig:
    """Hyperparamètres pour le StateBridge."""
    source_dim: int = 64
    target_dim: int = 64
    strategy: AlignmentStrategy = AlignmentStrategy.AUTO
    l2_regularization: float = 1e-4
    eps: float = 1e-8
    preserve_scale: bool = True
    normalize_outputs: bool = True


class BaseLatentBridge(ABC):
    """Interface abstraite pour tout pont d'alignement latent (Commandement 8)."""

    @abstractmethod
    def fit(self, anchors_source: np.ndarray, anchors_target: np.ndarray) -> "BaseLatentBridge":
        """Calibre l'alignement à partir d'un ensemble de points d'ancrage synchronisés."""
        pass

    @abstractmethod
    def transform(self, vectors: np.ndarray) -> np.ndarray:
        """Projette un ou plusieurs vecteurs de l'espace source vers l'espace cible."""
        pass

    @abstractmethod
    def compute_fidelity(self, anchors_source: np.ndarray, anchors_target: np.ndarray) -> float:
        """Calcule la fidélité cosinus moyenne après projection."""
        pass


class LUStateBridge(BaseLatentBridge):
    """
    Implémentation haute performance de l'alignement d'espace latent.
    Gère les connectomes identiques (rotation pure) et hétérogènes (projection d'énergie).
    """

    def __init__(self, config: Optional[StateBridgeConfig] = None):
        self.config = config or StateBridgeConfig()
        self.rotation_matrix: Optional[np.ndarray] = None
        self.translation_source: Optional[np.ndarray] = None
        self.translation_target: Optional[np.ndarray] = None
        self.scale_factor: float = 1.0
        self.is_fitted: bool = False

    def fit(self, anchors_source: np.ndarray, anchors_target: np.ndarray) -> "LUStateBridge":
        """
        Ajuste les paramètres d'alignement via Procruste orthogonal ou régression affine.
        anchors_source: shape (N, source_dim)
        anchors_target: shape (N, target_dim)
        """
        anchors_source = np.asarray(anchors_source, dtype=np.float64)
        anchors_target = np.asarray(anchors_target, dtype=np.float64)

        # Vérifications de cohérence et de stabilité (Commandement 9)
        if np.any(np.isnan(anchors_source)) or np.any(np.isinf(anchors_source)):
            raise ValueError("Les ancres sources contiennent des NaN ou Inf.")
        if np.any(np.isnan(anchors_target)) or np.any(np.isinf(anchors_target)):
            raise ValueError("Les ancres cibles contiennent des NaN ou Inf.")

        n_samples_src, d_src = anchors_source.shape
        n_samples_tgt, d_tgt = anchors_target.shape

        if n_samples_src != n_samples_tgt:
            raise ValueError(f"Incohérence du nombre d'ancres: {n_samples_src} vs {n_samples_tgt}")
        if n_samples_src < 2:
            raise ValueError("Au moins 2 points d'ancrage sont requis pour ajuster le bridge.")

        self.config.source_dim = d_src
        self.config.target_dim = d_tgt

        # Centrage (moyennes)
        self.translation_source = np.mean(anchors_source, axis=0, keepdims=True)
        self.translation_target = np.mean(anchors_target, axis=0, keepdims=True)

        x_centered = anchors_source - self.translation_source
        y_centered = anchors_target - self.translation_target

        strategy = self.config.strategy
        if strategy == AlignmentStrategy.AUTO:
            strategy = (
                AlignmentStrategy.ORTHOGONAL_PROCRUSTES
                if d_src == d_tgt
                else AlignmentStrategy.REGULARIZED_AFFINE
            )

        if strategy == AlignmentStrategy.ORTHOGONAL_PROCRUSTES and d_src == d_tgt:
            # Analyse de Procruste Orthogonale : M = X^T * Y
            cross_cov = np.dot(x_centered.T, y_centered)
            u, s, vt = np.linalg.svd(cross_cov, full_matrices=False)
            # R = U * V^T (Garantie de rotation orthogonale pure)
            r = np.dot(u, vt)

            # Échelle optionnelle
            if self.config.preserve_scale:
                var_x = np.sum(x_centered ** 2)
                if var_x > self.config.eps:
                    self.scale_factor = float(np.sum(s) / var_x)
                else:
                    self.scale_factor = 1.0
            else:
                self.scale_factor = 1.0

            self.rotation_matrix = r
        else:
            # Régression Affine Régularisée (Ridge) pour dimensions asymétriques :
            # W = (X^T X + lambda * I)^(-1) X^T Y
            xtx = np.dot(x_centered.T, x_centered)
            reg = self.config.l2_regularization * np.eye(d_src, dtype=np.float64)
            xty = np.dot(x_centered.T, y_centered)

            # Résolution stable par décomposition de Cholesky ou solveur linéaire régularisé
            try:
                w = np.linalg.solve(xtx + reg, xty)
            except np.linalg.LinAlgError:
                w = np.dot(np.linalg.pinv(xtx + reg), xty)

            self.rotation_matrix = w
            self.scale_factor = 1.0

        self.is_fitted = True
        return self

    def transform(self, vectors: np.ndarray) -> np.ndarray:
        """
        Projette un vecteur ou lot de vecteurs de l'espace source vers l'espace cible.
        Supporte les entrées 1D (D_src,) ou 2D (B, D_src).
        """
        if not self.is_fitted or self.rotation_matrix is None:
            raise RuntimeError("Le StateBridge doit être calibré via fit() avant transform().")

        arr = np.asarray(vectors, dtype=np.float64)
        is_1d = arr.ndim == 1
        if is_1d:
            arr = arr.reshape(1, -1)

        if arr.shape[1] != self.config.source_dim:
            raise ValueError(
                f"Dimension d'entrée invalide: attendu {self.config.source_dim}, reçu {arr.shape[1]}"
            )

        # Centrage par rapport aux ancres sources
        centered = arr - self.translation_source

        # Transformation linéaire (rotation / projection) + mise à l'échelle
        projected = self.scale_factor * np.dot(centered, self.rotation_matrix)

        # Recentrage dans l'espace cible
        out = projected + self.translation_target

        # Normalisation unitaire optionnelle (pour gigatokens directionnels)
        if self.config.normalize_outputs:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            norms = np.where(norms < self.config.eps, 1.0, norms)
            out = out / norms

        # Nettoyage des éventuels NaN / Inf résiduels
        out = np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0)

        return out[0] if is_1d else out

    def compute_fidelity(self, anchors_source: np.ndarray, anchors_target: np.ndarray) -> float:
        """
        Évalue la fidélité sémantique de l'alignement via la similarité cosinus moyenne
        entre les cibles réelles et les projections.
        """
        projected = self.transform(anchors_source)
        target = np.asarray(anchors_target, dtype=np.float64)

        # Normalisation de target
        norm_tgt = np.linalg.norm(target, axis=1, keepdims=True)
        norm_tgt = np.where(norm_tgt < self.config.eps, 1.0, norm_tgt)
        target_normed = target / norm_tgt

        # Normalisation de projected
        norm_proj = np.linalg.norm(projected, axis=1, keepdims=True)
        norm_proj = np.where(norm_proj < self.config.eps, 1.0, norm_proj)
        proj_normed = projected / norm_proj

        cosines = np.sum(target_normed * proj_normed, axis=1)
        return float(np.mean(cosines))
