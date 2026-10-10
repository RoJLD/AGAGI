"""
tests/test_llm_latent_extractor.py — Suite de validation TDD pour la passerelle LLM Latente (Arc 10).

Vérifie l'extraction d'activations, la projection hypersphérique unitaire S^(D-1),
le transfert continu direct M2M sans régénération textuelle et la préservation géométrique CKA.
"""

import pytest
import numpy as np
from src.metaprog.llm_latent_extractor import (
    LLMLatentConfig,
    LLMLatentExtractor,
    LLMThoughtBridge,
    PoolingStrategy,
)


def test_latent_extractor_initialization_and_sphere_projection():
    """Vérifie l'initialisation et la projection stricte sur la variété S^(D-1)."""
    cfg = LLMLatentConfig(target_latent_dim=64, normalize_to_sphere=True)
    extractor = LLMLatentExtractor(cfg)

    prompt = "L'intelligence artificielle générale émerge de la clôture opérationnelle."
    z = extractor.extract_latent(prompt)

    assert isinstance(z, np.ndarray)
    assert z.shape == (64,)
    assert z.dtype == np.float32
    assert np.all(np.isfinite(z)), "Le Gigatoken contient des NaN ou Inf"
    # Vérification unitaire stricte ||z|| = 1.0
    norm = np.linalg.norm(z)
    assert abs(norm - 1.0) < 1e-5, f"Norme attendue 1.0, obtenue {norm}"


def test_semantic_proximity_and_consistency():
    """Vérifie que la proximité sémantique est préservée sur la sphère latente."""
    cfg = LLMLatentConfig(target_latent_dim=64, normalize_to_sphere=True)
    extractor = LLMLatentExtractor(cfg)

    text_base = "Wheat harvesting in fertile agricultural farm fields."
    text_similar = "Grain crops reaping in fertile farmland soil."
    text_different = "Thermonuclear fusion reactions inside massive supernova stars."

    sim_similar = extractor.compute_cosine_similarity(text_base, text_similar)
    sim_different = extractor.compute_cosine_similarity(text_base, text_different)

    assert sim_similar > sim_different, (
        f"Similarité attendue plus forte pour concepts proches : {sim_similar} vs {sim_different}"
    )


def test_batch_extraction_shape_and_orthonormality():
    """Vérifie l'extraction par lot vectorisée."""
    cfg = LLMLatentConfig(target_latent_dim=32)
    extractor = LLMLatentExtractor(cfg)

    texts = [
        "Théorème de Novikov et cohérence causale.",
        "Transport optimal de Sinkhorn et Wasserstein.",
        "Barycentre de Fréchet sur variété riemannienne.",
    ]
    batch = extractor.extract_batch(texts)

    assert batch.shape == (3, 32)
    for i in range(3):
        assert abs(np.linalg.norm(batch[i]) - 1.0) < 1e-5


def test_cross_model_latent_thought_bridge_heterogeneous():
    """Vérifie le transfert M2M continu direct entre deux modèles de dimensions asymétriques."""
    # Modèle A : dimension latente 48
    cfg_a = LLMLatentConfig(target_latent_dim=48, projection_seed=101)
    extractor_a = LLMLatentExtractor(cfg_a)

    # Modèle B : dimension latente 64
    cfg_b = LLMLatentConfig(target_latent_dim=64, projection_seed=202)
    extractor_b = LLMLatentExtractor(cfg_b)

    bridge = LLMThoughtBridge(extractor_a, extractor_b)

    corpus_calibration = [
        "Convergence de l'attracteur téléologique.",
        "Auto-reprogrammation conservative sans explosion de gradient.",
        "Équation de réaction-diffusion sur tore bidimensionnel.",
        "Paire intriquée et violation des inégalités classiques.",
        "Clôture homéostatique opérationnelle et autopoïèse.",
        "Graphe de connaissances et mémoire Lattice immuable.",
    ]

    # 1. Calibration Procruste
    fidelity = bridge.calibrate(corpus_calibration)
    assert bridge.is_calibrated is True
    assert fidelity > 0.60, f"Fidélité de calibration insuffisante: {fidelity}"

    # 2. Transfert continu direct d'une nouvelle pensée sans aucun mot généré
    new_thought_prompt = "Déploiement d'un agent autonome dans un environnement complexe."
    z_a, z_b_pred, sim = bridge.transfer_latent_thought(new_thought_prompt)

    assert z_a.shape == (48,)
    assert z_b_pred.shape == (64,)
    assert abs(np.linalg.norm(z_a) - 1.0) < 1e-4
    assert abs(np.linalg.norm(z_b_pred) - 1.0) < 1e-4
    assert sim > 0.50, f"Fidélité de transfert trop basse: {sim}"


def test_linear_cka_geometric_alignment():
    """Vérifie la préservation géométrique globale via CKA linéaire."""
    cfg_a = LLMLatentConfig(target_latent_dim=64, projection_seed=42)
    extractor_a = LLMLatentExtractor(cfg_a)

    cfg_b = LLMLatentConfig(target_latent_dim=64, projection_seed=43)
    extractor_b = LLMLatentExtractor(cfg_b)

    bridge = LLMThoughtBridge(extractor_a, extractor_b)

    corpus = [
        "Chasse coopérative du mammouth.",
        "Forgeage de l'acier et outils métalliques.",
        "Moisson de blé et silos agricoles.",
        "Négociation de traité commercial sur la place du marché.",
        "Prière aux stèles et stigmargie culturelle.",
    ]
    cka = bridge.compute_linear_cka(corpus)

    assert 0.0 <= cka <= 1.0
    assert not np.isnan(cka)
    assert cka > 0.65, f"Score CKA trop bas: {cka}"
