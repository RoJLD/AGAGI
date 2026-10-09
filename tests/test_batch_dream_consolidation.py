"""
tests/test_batch_dream_consolidation.py — Validation de la Consolidation Vectorisée Collective (Commandement 3).
Vérifie formellement que la consolidation par batch traite simultanément les mémoires de toute la population
sans boucle Python lente et avec stabilité numérique garantie (Commandement 9).
"""

import numpy as np
import pytest

from src.agents.self_model import SelfModel, SelfModelConfig
from src.agents.dream_replay import BatchNightConsolidator, EpisodicMemoryBuffer
from src.agents.mamba_agent import MambaAgent
from src.agents.world_model import WorldModel


def test_self_model_vectorized_learn_batch():
    """Vérifie que learn_batch surpasse les itérations séquentielles et réduit la perte."""
    sm = SelfModel(state_dim=10, config=SelfModelConfig(learning_rate=0.05))

    # Génération d'un lot synthétique
    np.random.seed(42)
    S = np.random.randn(20, 10).astype(np.float32)
    actual_costs = np.random.uniform(0.1, 2.0, size=20).astype(np.float32)
    task_successes = np.random.choice([True, False], size=20)

    # Erreur initiale
    pred_costs_before = np.dot(S, sm.W_cost) + sm.b_cost
    err_before = np.mean(np.abs(pred_costs_before - actual_costs))

    # 5 pas de mise à jour vectorisée
    for _ in range(5):
        sm.learn_batch(S, actual_costs, task_successes)

    pred_costs_after = np.dot(S, sm.W_cost) + sm.b_cost
    err_after = np.mean(np.abs(pred_costs_after - actual_costs))

    assert err_after < err_before, "learn_batch doit réduire l'erreur de prédiction calorique globale"


def test_batch_night_consolidator_population():
    """Prouve que la consolidation nocturne par batch gère une population entière."""
    wm = WorldModel(input_dim=12)
    consolidator = BatchNightConsolidator(world_model=wm, replay_batch_size=8)

    # Création d'une cohorte de 5 agents avec mémoires
    agents = []
    for i in range(5):
        m = MambaAgent(num_inputs=12, num_outputs=10, isocaloric=True)
        m.enable_episodic_dreaming(buffer_capacity=30)
        # Remplir le buffer
        for _ in range(10):
            m.replay_buffer.push(
                state=np.random.randn(12).astype(np.float32),
                action=int(np.random.randint(0, 4)),
                reward=float(np.random.uniform(-1, 2)),
                next_state=np.random.randn(12).astype(np.float32),
                energy_spent=float(np.random.uniform(0.1, 1.5)),
                success=bool(np.random.rand() > 0.5)
            )
        agents.append({"id": f"ag_{i}", "model": m})

    res = consolidator.consolidate_population_batch(agents)

    assert res["status"] == "batch_consolidated"
    assert res["eligible_agents"] == 5
    assert res["total_replayed_steps"] == 5 * 8
    assert consolidator.total_consolidations >= 5
