"""
tests/test_isocaloric_deconfounding.py — Validation du Dé-confounding Métabolique (Fait Neuf 2 / P1 Science).
Prouve formellement que l'agent isocalorique immunise le métabolisme contre les altérations de W[0:10],
permettant d'isoler strictement la politique cognitive sans artefact corporel.
Commandements 1, 3, 9, 14.
"""

import numpy as np
import pytest
from src.agents.mamba_agent import MambaAgent


def test_standard_agent_suffers_from_metabolic_confounding():
    """Confirme le fait neuf n°2 : l'agent standard couple W[0:10] avec son métabolisme."""
    agent = MambaAgent(isocaloric=False)
    initial_drain = agent.phenotype_energy_drain
    initial_hp_bonus = agent.phenotype_hp_bonus

    # Annulation des lignes W[0:10] (comme dans make_blind ou ablations d'entrées)
    agent.genome.W[:10, :] = 0.0
    agent.update_phenotype()

    # Le drain et le hp_bonus s'effondrent artificiellement
    assert agent.phenotype_energy_drain < initial_drain
    assert agent.phenotype_hp_bonus == 0.0


def test_isocaloric_agent_guarantees_metabolic_invariance():
    """Prouve que l'agent isocalorique découple strictement la politique du métabolisme."""
    agent = MambaAgent(isocaloric=True)
    baseline_drain = agent.phenotype_energy_drain
    baseline_hp = agent.phenotype_hp_bonus
    baseline_inv = agent.phenotype_inv_capacity

    assert baseline_drain == 1.3
    assert baseline_hp == 0.0
    assert baseline_inv == 3

    # Test 1 : Annulation totale de W[:10]
    agent.genome.W[:10, :] = 0.0
    agent.update_phenotype()
    assert agent.phenotype_energy_drain == baseline_drain
    assert agent.phenotype_hp_bonus == baseline_hp
    assert agent.phenotype_inv_capacity == baseline_inv

    # Test 2 : Amplification massive x10 de W[:10]
    agent.genome.W[:10, :] = 50.0
    agent.update_phenotype()
    assert agent.phenotype_energy_drain == baseline_drain
    assert agent.phenotype_hp_bonus == baseline_hp
    assert agent.phenotype_inv_capacity == baseline_inv


def test_isocaloric_inheritance_and_cloning():
    """Prouve que le mode isocalorique est fidèlement transmis par clonage."""
    parent = MambaAgent(isocaloric=True)
    parent.enable_episodic_dreaming(buffer_capacity=50)

    clone = parent.clone()
    assert clone.isocaloric is True
    assert clone.phenotype_energy_drain == 1.3
    assert clone.replay_buffer is not None
    assert clone.replay_buffer.capacity == 50
    assert clone.night_consolidator is not None


def test_inworld_night_consolidation_execution():
    """Vérifie que les transitions sont stockées et consolidées in-world durant la nuit."""
    from src.environments.config import WorldConfig
    from src.worlds.world_1_stoneage import Biosphere3D

    np.random.seed(42)
    cfg = WorldConfig(size=12, num_altars=1, prey_mode="none")
    world = Biosphere3D(cfg)
    world.night_enabled = True

    model = MambaAgent(num_inputs=cfg.agent.num_inputs, num_outputs=cfg.agent.num_outputs, isocaloric=True)
    model.enable_episodic_dreaming(buffer_capacity=30)
    world.add_agent(model, x=6, y=6, energy=100.0)

    # Faire 5 pas de simulation de jour pour accumuler des mémoires
    world.is_night = False
    for _ in range(5):
        world.step()

    agent = world.agents[0]
    assert len(agent["model"].replay_buffer) >= 5

    # Avancer à la phase nocturne naturelle (ticks >= 50) et vérifier la consolidation
    world.ticks = 50
    world.step()

    assert world.is_night is True
    assert agent["model"].night_consolidator.total_consolidations >= 1

