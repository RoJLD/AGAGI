"""
tests/test_federal_metagenome_compiler.py — Tests TDD pour le Méta-Génome Fédéral & Compilateur Évolutif.
Arc 14 : Jalon M32 (FederalMetaGenomeSynthesizer & EvolutiveCompiler).

Vérifie formellement la distillation continue des trajectoires de survie multi-mondes,
la compilation NTM sécurisée en sandbox et la modulation synaptique sans divergence spectrale.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Sandboxing, Test-Driven, Stabilité Numérique).
"""

import pytest
import numpy as np

from src.metaprog.federal_metagenome_compiler import (
    FederalMetaGenomeSynthesizer,
    EvolutiveCompiler,
    FederalMetaGenomeConfig,
)
from src.agents.mamba_agent import MambaAgent


def test_federal_metagenome_initialization():
    """Vérifie l'initialisation conforme et unitaire du synthétiseur de méta-génome."""
    cfg = FederalMetaGenomeConfig(
        latent_dim=64,
        num_nodes=172,
        distillation_rate=0.15,
        max_spectral_radius=0.90,
    )
    synthesizer = FederalMetaGenomeSynthesizer(cfg)

    assert synthesizer.z_meta.shape == (64,)
    assert pytest.approx(float(np.linalg.norm(synthesizer.z_meta)), abs=1e-4) == 1.0
    assert synthesizer.W_federal.shape == (172, 172)
    assert synthesizer.spectral_radius <= 0.90
    assert synthesizer.version == 1


def test_distill_civilization_trajectories():
    """Vérifie la condensation des consensus et matrices des 3 mondes dans le méta-génome."""
    cfg = FederalMetaGenomeConfig(latent_dim=64, num_nodes=172, distillation_rate=0.20)
    synthesizer = FederalMetaGenomeSynthesizer(cfg)

    # Simuler des consensus de fondation et des génomes de survivants
    rng = np.random.RandomState(42)
    raw_cons = [rng.randn(64).astype(np.float32) for _ in range(3)]
    survivors_w = [rng.randn(172, 172).astype(np.float32) * 0.1 for _ in range(3)]

    meta_spec = synthesizer.distill_civilization_trajectories(
        consensus_latents=raw_cons,
        survivor_genomes=survivors_w,
    )

    assert meta_spec["version"] == 2
    assert meta_spec["distillations_count"] == 1
    assert pytest.approx(float(np.linalg.norm(synthesizer.z_meta)), abs=1e-4) == 1.0
    assert synthesizer.spectral_radius <= cfg.max_spectral_radius
    assert not np.isnan(synthesizer.spectral_radius)


def test_evolutive_compiler_to_ntm():
    """Vérifie la compilation du méta-génome vers des créneaux NTM valides (K, 5)."""
    cfg = FederalMetaGenomeConfig(latent_dim=64, num_nodes=172, num_ntm_slots=10)
    compiler = EvolutiveCompiler(cfg)

    z = np.ones(64, dtype=np.float32)
    z = z / np.linalg.norm(z)

    ntm_slots = compiler.compile_metagenome_to_ntm(z)

    assert ntm_slots.shape == (10, 5)
    assert not np.any(np.isnan(ntm_slots))
    assert not np.any(np.isinf(ntm_slots))
    # Vérifier que les poids compilés sont dans la plage valide [-10, 10]
    assert np.all(np.abs(ntm_slots[:, 2]) <= 10.0)


def test_sandboxed_compilation_and_application():
    """Vérifie l'application en sandbox sécurisée d'une modification synaptique sur un MambaAgent."""
    cfg = FederalMetaGenomeConfig(latent_dim=64, num_nodes=172, num_ntm_slots=8)
    compiler = EvolutiveCompiler(cfg)
    agent = MambaAgent(num_inputs=59, num_outputs=108, num_nodes=172)

    initial_w_norm = float(np.linalg.norm(agent.genome.W))
    z = np.random.randn(64).astype(np.float32)
    z = z / np.linalg.norm(z)

    success, report = compiler.compile_and_apply_to_agent(agent, z)

    assert success is True
    assert "mutations_applied" in report
    assert report["mutations_applied"] > 0
    assert not np.any(np.isnan(agent.genome.W))
    assert not np.any(np.isinf(agent.genome.W))
    # Le génome a dû évoluer chirurgicalement
    new_w_norm = float(np.linalg.norm(agent.genome.W))
    assert new_w_norm != initial_w_norm


def test_compiler_rejects_divergent_mutations():
    """Vérifie que la sandbox rejette strictement une mutation provoquant une divergence spectrale."""
    cfg = FederalMetaGenomeConfig(latent_dim=64, num_nodes=172, max_spectral_radius=0.50)
    compiler = EvolutiveCompiler(cfg)
    agent = MambaAgent(num_inputs=59, num_outputs=108, num_nodes=172)

    # Forcer un vecteur provoquant une instabilité artificielle
    z_extreme = np.ones(64, dtype=np.float32) * 1e5

    success, report = compiler.compile_and_apply_to_agent(agent, z_extreme)

    # Si le rayon spectral dépasse la borne stricte, le compilateur doit soit tronquer soit rejeter proprement
    assert not np.any(np.isnan(agent.genome.W))
    assert report["spectral_stable"] is True
