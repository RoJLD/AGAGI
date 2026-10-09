import pytest
import numpy as np

from src.agents.self_model import SelfModel, SelfModelConfig
from src.agents.world_model import WorldModel
from src.agents.dream_replay import EpisodicMemoryBuffer, NightConsolidator


def test_self_model_metacognition():
    cfg = SelfModelConfig(learning_rate=0.1, confidence_threshold=0.60)
    sm = SelfModel(state_dim=10, config=cfg)

    dummy_state = np.ones(10, dtype=np.float32)
    cost, conf, needs_delib = sm.evaluate_state(dummy_state)

    assert cost >= 0.0, "Le coût prédit doit être positif"
    assert 0.0 <= conf <= 1.0, "La confiance doit être bornée entre 0 et 1"

    # Simuler un échec avec coût élevé
    for _ in range(10):
        sm.learn_step(dummy_state, actual_cost=5.0, task_success=False)

    cost_post, conf_post, needs_delib_post = sm.evaluate_state(dummy_state)
    assert cost_post > cost or np.isclose(cost_post, 5.0, atol=2.0), "Le coût estimé doit converger vers 5.0"
    assert conf_post < conf, "La confiance doit baisser après une série d'échecs"

    # Vérifier l'augmentation du budget TTC en cas de doute
    boost = sm.get_ttc_budget_adjustment(conf_post)
    assert boost >= 1, "Un doute métacognitif doit allouer du budget TTC supplémentaire"


def test_episodic_buffer_and_night_consolidation():
    state_dim = 8
    wm = WorldModel(input_dim=state_dim)
    consolidator = NightConsolidator(world_model=wm, replay_batch_size=8)
    buffer = EpisodicMemoryBuffer(capacity=32)

    # Remplir le buffer avec des observations normalisées in [0, 1]
    rng = np.random.default_rng(42)
    for i in range(12):
        s = rng.uniform(0.1, 0.8, size=state_dim).astype(np.float32)
        s_next = (s * 0.9).astype(np.float32)
        buffer.push(
            state=s,
            action=1,
            reward=1.0,
            next_state=s_next,
            energy_spent=0.1,
            success=True
        )

    assert len(buffer) == 12

    sm = SelfModel(state_dim=state_dim)
    result = consolidator.consolidate_agent("test_agent_alpha", buffer, self_model=sm)

    assert result["status"] == "consolidated"
    assert result["replayed_steps"] == 8
    assert result["post_loss"] <= result["pre_loss"] + 1e-4, "Le replay doit consolider le modèle du monde"
