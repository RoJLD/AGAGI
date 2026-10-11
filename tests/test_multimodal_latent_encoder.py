"""
tests/test_multimodal_latent_encoder.py — Validation TDD de l'Encodeur Spatial Multimodal (Arc 12 : Jalon M24).

Vérifie formellement :
1. L'unitarité et la stabilité de la projection de grilles 3D spatiales.
2. La convolution circulaire unitaire FFT sans dérive de norme.
3. La fidélité de fusion géométrique entre la perception physique et le but téléologique.
4. L'immunité numérique absolue contre les NaN et Inf.
"""

import pytest
import numpy as np
from src.metaprog.multimodal_latent_encoder import (
    MultimodalLatentEncoder,
    MultimodalEncoderConfig,
)


def test_spatial_grid_encoding_unitarity():
    """Vérifie que la projection d'une grille 3D respecte strictement ||z||_2 = 1.0."""
    cfg = MultimodalEncoderConfig(latent_dim=64, grid_size=(7, 7), num_channels=4)
    encoder = MultimodalLatentEncoder(cfg)

    grid = np.random.randn(7, 7, 4).astype(np.float32)
    z_spatial = encoder.encode_spatial_grid(grid)

    assert z_spatial.shape == (64,)
    assert pytest.approx(np.linalg.norm(z_spatial), abs=1e-4) == 1.0
    assert not np.any(np.isnan(z_spatial))


def test_circular_convolution_norm_preservation():
    """Vérifie la conservation unitaire de la convolution circulaire unitaire FFT."""
    encoder = MultimodalLatentEncoder(MultimodalEncoderConfig(latent_dim=64))
    rng = np.random.RandomState(42)

    a = encoder._normalize(rng.randn(64))
    b = encoder._normalize(rng.randn(64))

    conv = encoder.circular_convolution(a, b)
    assert conv.shape == (64,)
    assert pytest.approx(np.linalg.norm(conv), abs=1e-4) == 1.0


def test_multimodal_fusion_semantic_balance():
    """
    Vérifie que la fusion multimodale z_multi retient simultanément l'information
    de l'état spatial perçu et du but téléologique de fondation.
    """
    encoder = MultimodalLatentEncoder(MultimodalEncoderConfig(latent_dim=64))
    grid = np.zeros((7, 7, 4), dtype=np.float32)
    grid[3, 3, 2] = 5.0  # Foyer de feu ou ressource au centre

    goal = np.zeros(64, dtype=np.float32)
    goal[0] = 1.0  # Axe téléologique

    z_fused = encoder.fuse_spatial_and_goal(grid, goal, weight_spatial=0.5)

    assert z_fused.shape == (64,)
    assert pytest.approx(np.linalg.norm(z_fused), abs=1e-4) == 1.0

    # Vérification que le vecteur n'est ni purement spatial ni purement but
    z_spatial = encoder.encode_spatial_grid(grid)
    bound_spatial = encoder.circular_convolution(z_spatial, encoder.role_spatial)
    bound_goal = encoder.circular_convolution(encoder._normalize(goal), encoder.role_goal)

    sim_spatial = float(np.dot(z_fused, bound_spatial))
    sim_goal = float(np.dot(z_fused, bound_goal))

    assert sim_spatial > 0.30, f"Composante spatiale perdue dans la fusion : {sim_spatial}"
    assert sim_goal > 0.30, f"Composante téléologique perdue dans la fusion : {sim_goal}"


def test_multimodal_nan_inf_immunity():
    """Vérifie la robustesse absolue aux entrées corrompues (Commandement 9)."""
    encoder = MultimodalLatentEncoder()
    corrupted_grid = np.full((7, 7, 4), np.nan, dtype=np.float32)
    corrupted_goal = np.full(64, np.inf, dtype=np.float32)

    z = encoder.fuse_spatial_and_goal(corrupted_grid, corrupted_goal)
    assert not np.any(np.isnan(z))
    assert not np.any(np.isinf(z))
    assert pytest.approx(np.linalg.norm(z), abs=1e-4) == 1.0
