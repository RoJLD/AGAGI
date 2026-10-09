"""
Unit tests for LUStateBridge (Alignement d'espaces latents hétérogènes).
Conforme au Commandement 7 (Test-Driven Metaprogramming) et Commandement 9 (Stabilité Numérique).
"""

import pytest
import numpy as np
from src.metaprog.lu_state_bridge import (
    LUStateBridge,
    StateBridgeConfig,
    AlignmentStrategy,
)


def test_state_bridge_unfitted_raises_error():
    bridge = LUStateBridge()
    v = np.random.randn(64)
    with pytest.raises(RuntimeError):
        bridge.transform(v)


def test_orthogonal_procrustes_same_dim():
    """Vérifie que pour deux espaces de même dimension sous rotation pure, la fidélité est quasi-parfaite."""
    rng = np.random.RandomState(42)
    dim = 32
    n_anchors = 100

    # Source anchors
    x = rng.randn(n_anchors, dim)

    # Création d'une vraie matrice orthogonale de rotation (Q via QR decomposition)
    h = rng.randn(dim, dim)
    q, _ = np.linalg.qr(h)

    # Translation
    t = rng.randn(1, dim) * 0.5
    y = np.dot(x, q) + t

    config = StateBridgeConfig(
        source_dim=dim,
        target_dim=dim,
        strategy=AlignmentStrategy.ORTHOGONAL_PROCRUSTES,
        preserve_scale=True,
        normalize_outputs=True,
    )
    bridge = LUStateBridge(config)
    bridge.fit(x, y)

    fidelity = bridge.compute_fidelity(x, y)
    assert fidelity > 0.98, f"La fidélité cosinus attendue est > 0.98, obtenu {fidelity}"

    # Vérification sur un nouveau vecteur non vu (généralisation)
    x_test = rng.randn(dim)
    y_test_expected = np.dot(x_test.reshape(1, -1), q) + t
    y_test_expected /= np.linalg.norm(y_test_expected)

    y_test_proj = bridge.transform(x_test)
    cos_sim = np.dot(y_test_proj, y_test_expected.ravel())
    assert cos_sim > 0.98


def test_regularized_affine_asymmetric_dimensions():
    """Vérifie l'alignement pour dimensions asymétriques (128D -> 64D)."""
    rng = np.random.RandomState(1337)
    d_src = 128
    d_tgt = 64
    n_anchors = 150

    x = rng.randn(n_anchors, d_src)
    # Matrice de projection linéaire avec du bruit
    w_true = rng.randn(d_src, d_tgt) / np.sqrt(d_src)
    y = np.dot(x, w_true) + rng.randn(n_anchors, d_tgt) * 0.05

    config = StateBridgeConfig(
        source_dim=d_src,
        target_dim=d_tgt,
        strategy=AlignmentStrategy.REGULARIZED_AFFINE,
        l2_regularization=1e-3,
        normalize_outputs=True,
    )
    bridge = LUStateBridge(config)
    bridge.fit(x, y)

    fidelity = bridge.compute_fidelity(x, y)
    assert fidelity > 0.85, f"La fidélité pour 128D->64D doit être > 0.85, obtenu {fidelity}"

    # Test batch projection
    batch_x = rng.randn(10, d_src)
    proj_batch = bridge.transform(batch_x)
    assert proj_batch.shape == (10, d_tgt)
    assert not np.any(np.isnan(proj_batch))
    assert not np.any(np.isinf(proj_batch))


def test_numerical_stability_guards():
    """Garantit l'absence de NaN/Inf même avec données dégénérées ou quasi-nulles."""
    dim = 16
    bridge = LUStateBridge(StateBridgeConfig(source_dim=dim, target_dim=dim))

    # Cas avec NaN dans les ancres -> doit lever ValueError
    bad_x = np.ones((10, dim))
    bad_x[0, 0] = np.nan
    good_y = np.ones((10, dim))

    with pytest.raises(ValueError):
        bridge.fit(bad_x, good_y)

    # Entraînement avec petites valeurs (proche de zéro)
    x = np.random.randn(20, dim) * 1e-6
    y = np.random.randn(20, dim) * 1e-6
    bridge.fit(x, y)

    zero_v = np.zeros(dim)
    transformed = bridge.transform(zero_v)
    assert not np.any(np.isnan(transformed))
    assert not np.any(np.isinf(transformed))
