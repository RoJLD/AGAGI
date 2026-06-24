import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.environments.config import WorldConfig
import numpy as np
from src.agents.mamba_agent import count_active_nodes, MambaAgent, MambaBatchModel


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
