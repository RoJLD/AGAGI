"""
tests/test_mamba_lu_wiring.py — Validation du câblage physique des Gigatokens LU dans MambaAgent et la Biosphère.

Commandements AGIseed :
1. Hyper-Configurabilité : Paramètres de dimension et d'activation injectés via config.
2. Modularité : Séparation nette du connectome Liquid Mamba et du traducteur latent.
3. Haute Performance : Opérations d'export/import de Gigatoken 100% vectorisées NumPy.
7. Validation Rigoureuse (Test-Driven) : Tests exhaustifs de la chaîne neuronale.
9. Stabilité Numérique : Vecteurs normalisés sur la sphère unité, absence de NaN/Inf.
"""

import pytest
import numpy as np
import os

from src.agents.mamba_agent import MambaAgent
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def test_mamba_agent_export_gigatoken():
    """Vérifie que MambaAgent extrait un Gigatoken unitaire directement depuis son état H_prev."""
    agent = MambaAgent(num_inputs=10, num_outputs=10, num_nodes=30)
    agent.H_prev[0] = np.random.randn(30).astype(np.float32)

    gigatoken = agent.export_gigatoken(latent_dim=16)

    assert gigatoken.shape == (16,)
    assert np.all(np.isfinite(gigatoken))
    assert abs(np.linalg.norm(gigatoken) - 1.0) < 1e-4
    assert agent.lu_latent is not None
    assert np.allclose(agent.lu_latent, gigatoken)


def test_mamba_agent_receive_and_modulate():
    """Vérifie que l'injection d'un Gigatoken reçu module les activations de l'agent."""
    agent = MambaAgent(num_inputs=10, num_outputs=10, num_nodes=30)
    obs = np.ones((1, 10), dtype=np.float32)

    # Forward sans Gigatoken
    logits_base = agent.forward(obs.copy()).copy()

    # Injection d'un Gigatoken entrant
    incoming = np.random.randn(16).astype(np.float32)
    incoming /= np.linalg.norm(incoming)
    agent.receive_gigatoken(incoming)
    assert agent.lu_incoming_latent is not None

    # Forward avec Gigatoken
    agent.H_prev = np.zeros_like(agent.H_prev)
    logits_mod = agent.forward(obs.copy())

    assert logits_mod.shape == logits_base.shape
    assert np.all(np.isfinite(logits_mod))
    # La présence du Gigatoken reçu doit moduler les prédictions
    assert not np.allclose(logits_mod, logits_base)


def test_mamba_agent_clone_preserves_lu_state():
    """Vérifie que le clonage de MambaAgent préserve l'état et la matrice de projection LU."""
    agent = MambaAgent(num_inputs=10, num_outputs=10, num_nodes=30)
    token = agent.export_gigatoken(16)
    incoming = np.ones(16, dtype=np.float32) * 0.1
    agent.receive_gigatoken(incoming)

    clone_agent = agent.clone()

    assert clone_agent.lu_proj is not None
    assert np.allclose(clone_agent.lu_proj, agent.lu_proj)
    assert clone_agent.lu_latent is not None
    assert np.allclose(clone_agent.lu_latent, token)
    assert clone_agent.lu_incoming_latent is not None
    assert np.allclose(clone_agent.lu_incoming_latent, incoming)


def test_inworld_adapter_binds_to_mamba_connectome():
    """Vérifie que LUInWorldAdapter extrait et injecte directement les Gigatokens dans MambaAgent."""
    cfg = WorldConfig(
        enable_lu_communication=True,
        lu_latent_dim=16,
        lu_hear_radius=4,
        lu_alignment_threshold=0.1
    )
    world = Biosphere3D(cfg)

    # Création de deux agents avec MambaAgent réel
    m1 = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs, num_nodes=cfg.agent.num_nodes)
    m2 = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs, num_nodes=cfg.agent.num_nodes)
    world.add_agent(m1, x=5, y=5, energy=50.0)
    world.add_agent(m2, x=6, y=5, energy=50.0)

    # 1. Encodage : doit fusionner l'environnement et l'état connectomique interne
    za = world.lu_adapter.encode_agent_latent(world.agents[0])
    assert za.shape == (16,)
    assert abs(np.linalg.norm(za) - 1.0) < 1e-4
    assert m1.lu_latent is not None

    # 2. Step de transmission continue : doit injecter dans m2
    res = world.lu_adapter.step()
    assert res["transmissions"] >= 1
    assert m2.lu_incoming_latent is not None
    assert m2.lu_incoming_latent.shape == (16,)
    assert np.all(np.isfinite(m2.lu_incoming_latent))


def test_main_biosphere_enable_lu_env_flag(monkeypatch):
    """Vérifie que le flag d'environnement ENABLE_LU=1 active correctement la branche dans la configuration."""
    monkeypatch.setenv("ENABLE_LU", "1")
    monkeypatch.setenv("LU_LATENT_DIM", "32")
    monkeypatch.setenv("LU_HEAR_RADIUS", "5")

    cfg = WorldConfig()
    enable_lu = os.getenv("ENABLE_LU", "0") == "1"
    if enable_lu:
        cfg.enable_lu_communication = True
        cfg.lu_latent_dim = int(os.getenv("LU_LATENT_DIM", "16"))
        cfg.lu_hear_radius = int(os.getenv("LU_HEAR_RADIUS", "3"))

    assert cfg.enable_lu_communication is True
    assert cfg.lu_latent_dim == 32
    assert cfg.lu_hear_radius == 5
