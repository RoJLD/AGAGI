import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.environments.config import WorldConfig
import numpy as np
from src.agents.mamba_agent import count_active_nodes, MambaAgent, MambaBatchModel
from src.worlds.world_1_stoneage import Biosphere3D


def _fresh_world(coef, activation_cost):
    """Monde déterministe + 1 agent à (5,5), proies/items vidés, coût d'activation forcé."""
    np.random.seed(0)
    config = WorldConfig()
    config.metabolic_cost_coef = coef
    world = Biosphere3D(config=config)
    agent = MambaAgent(num_inputs=config.agent.num_inputs)
    world.add_agent(agent, x=5, y=5, z=0, energy=50.0)
    world.preys.clear()
    world.items.clear()
    world.agents[0]["model"].last_activation_cost = activation_cost
    return world


def _drain_once(world):
    a = world.agents[0]
    before = a["energy"]
    np.random.seed(123)  # fige toute aléa interne de _resolve_biology
    logits = np.zeros(world.config.agent.num_outputs, dtype=np.float32)
    world._resolve_biology(a, action=4, logits=logits)
    return before - a["energy"]


def test_coef_zero_ignores_activation_cost():
    # Gating : à coef=0, un coût d'activation énorme ne change RIEN (non-régression).
    drain_no_cost = _drain_once(_fresh_world(coef=0.0, activation_cost=0))
    drain_big_cost = _drain_once(_fresh_world(coef=0.0, activation_cost=1000))
    assert abs(drain_big_cost - drain_no_cost) < 1e-6


def test_coef_positive_adds_proportional_drain():
    # À coef>0, le drain augmente de coef * last_activation_cost.
    drain_0 = _drain_once(_fresh_world(coef=0.01, activation_cost=0))
    drain_10 = _drain_once(_fresh_world(coef=0.01, activation_cost=10))
    assert abs((drain_10 - drain_0) - 0.01 * 10) < 1e-6


def test_metabolic_cost_coef_defaults_to_zero():
    # Non-régression : par défaut, aucun coût métabolique (comportement historique).
    config = WorldConfig()
    assert config.metabolic_cost_coef == 0.0


def test_count_active_nodes_ignores_subeps_and_padding():
    # 3 nœuds actifs (>0.1), le reste sous le seuil (padding/zéros) -> compte = 3.
    H = np.array([[0.5, -0.9, 0.2, 0.05, 0.0, 0.0]], dtype=np.float32)
    counts = count_active_nodes(H, eps=0.1)
    assert counts.tolist() == [3]


def test_last_activation_cost_set_after_forward():
    np.random.seed(0)
    a = MambaAgent()
    assert a.last_activation_cost == 0  # init avant tout forward
    model = MambaBatchModel([a])
    I = a.genome.num_inputs
    model.forward(np.ones((1, I), dtype=np.float32))
    N = a.genome.num_nodes
    assert isinstance(a.last_activation_cost, int)
    assert 0 <= a.last_activation_cost <= N
    # Cohérence avec le comptage direct sur l'état final.
    expected = int(count_active_nodes(model.H_prev_batch, MambaBatchModel.METABOLIC_ACTIVE_EPS)[0])
    assert a.last_activation_cost == expected
