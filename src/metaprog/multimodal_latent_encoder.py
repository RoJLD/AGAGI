"""
src/metaprog/multimodal_latent_encoder.py — Encodeur Spatial et Perception Multimodale Continue (Arc 12 : Jalon M24).

Projette directement les observations physiques spatiales 2D/3D (grilles de voxels,
gradients thermiques, distances d'entités) sur la variété hypersphérique unitaire S^(D-1)
sans captioning textuel. Permet la fusion géométrique unitaire avec les intentions de fondation.

Conforme aux 12 Commandements AGIseed :
- 1. Hyper-Configurable (Dataclass MultimodalEncoderConfig).
- 2. Modulaire (Découplé des mondes physiques).
- 3. Haute Performance (FFT vectorisée NumPy pour convolution circulaire unitaire).
- 9. Stabilité Numérique (Unitarité stricte sur S^(D-1), gestion des NaN/Inf).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
import numpy as np


@dataclass
class MultimodalEncoderConfig:
    """Hyperparamètres pour la projection spatiale et la fusion multimodale continue."""
    latent_dim: int = 64
    grid_size: Tuple[int, int] = (7, 7)  # Champ de vision spatial local
    num_channels: int = 4  # Canaux : 0: Terrain/Obstacle, 1: Ressources, 2: Température/Feu, 3: Entités/Agents
    projection_seed: int = 42
    circular_convolution_norm: bool = True
    eps: float = 1e-12


class MultimodalLatentEncoder:
    """
    Encodeur de perception continue fusionnant l'état spatial perçu et l'intention de fondation
    en un Gigatoken unifié sur S^(D-1).
    """

    def __init__(self, config: Optional[MultimodalEncoderConfig] = None):
        self.config = config or MultimodalEncoderConfig()
        self.latent_dim = self.config.latent_dim
        self.flat_spatial_dim = self.config.grid_size[0] * self.config.grid_size[1] * self.config.num_channels

        # Projecteur spatial semi-orthogonal R^(flat_spatial_dim x latent_dim)
        rng = np.random.RandomState(self.config.projection_seed)
        raw_proj = rng.randn(self.flat_spatial_dim, self.latent_dim).astype(np.float32)
        u, _, vt = np.linalg.svd(raw_proj, full_matrices=False)
        self.spatial_proj = np.dot(u, vt).astype(np.float32)

        # Rôles canoniques unitaires sur S^(D-1) pour la fusion sémantique
        raw_role_spatial = rng.randn(self.latent_dim).astype(np.float32)
        raw_role_goal = rng.randn(self.latent_dim).astype(np.float32)
        self.role_spatial = self._normalize(raw_role_spatial)
        self.role_goal = self._normalize(raw_role_goal)

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Projette sur S^(D-1) avec protection stricte contre les NaN/Inf."""
        arr = np.asarray(vec, dtype=np.float32)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        return (arr / norm).astype(np.float32)

    def encode_spatial_grid(self, grid: np.ndarray) -> np.ndarray:
        """
        Projette une grille spatiale 3D (H, W, C) directement vers un Gigatoken spatial z_spatial in S^(D-1).
        """
        arr = np.asarray(grid, dtype=np.float32)
        if arr.ndim == 3:
            flat = arr.reshape(-1)
        elif arr.ndim == 1:
            flat = arr
        else:
            raise ValueError(f"Format de grille invalide : shape = {arr.shape}")

        if flat.shape[0] != self.flat_spatial_dim:
            # Adaptation dimensionnelle par troncature/padding
            if flat.shape[0] > self.flat_spatial_dim:
                flat = flat[:self.flat_spatial_dim]
            else:
                flat = np.pad(flat, (0, self.flat_spatial_dim - flat.shape[0]))

        # Projection semi-orthogonale
        projected = np.dot(flat, self.spatial_proj)
        return self._normalize(projected)

    def circular_convolution(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Convolution circulaire unitaire dans le domaine de Fourier O(D log D)."""
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        conv = np.fft.irfft(fa * fb, n=len(a)).astype(np.float32)
        return self._normalize(conv)

    def fuse_spatial_and_goal(
        self,
        spatial_grid: np.ndarray,
        goal_latent: np.ndarray,
        weight_spatial: float = 0.5,
    ) -> np.ndarray:
        """
        Fusionne géométriquement la perception spatiale locale et l'objectif téléologique de fondation.
        Retourne z_multi in S^(D-1).
        """
        z_spatial = self.encode_spatial_grid(spatial_grid)
        z_goal = self._normalize(goal_latent)

        # Liane sémantique de rôles via convolution circulaire
        bound_spatial = self.circular_convolution(z_spatial, self.role_spatial)
        bound_goal = self.circular_convolution(z_goal, self.role_goal)

        # Superposition vectorielle pondérée
        alpha = float(np.clip(weight_spatial, 0.0, 1.0))
        superposition = alpha * bound_spatial + (1.0 - alpha) * bound_goal

        return self._normalize(superposition)
