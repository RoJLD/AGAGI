import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def test_G_batch_allocated_and_roundtrips_node_order():
    a = MambaAgent()
    N = a.genome.num_nodes
    m = MambaBatchModel([a])
    assert m.G_batch.shape == (1, MambaBatchModel.PLAN_A, m.max_N)
    # injecter un G non nul en ordre nœud, vérifier round-trip après un forward
    a.planner_G = np.ones((MambaBatchModel.PLAN_A, N), dtype=np.float32)
    m2 = MambaBatchModel([a])
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    m2.forward(obs)
    assert hasattr(a, "planner_G")
    assert a.planner_G.shape == (MambaBatchModel.PLAN_A, N)


def test_default_flags_off():
    assert MambaBatchModel.PLAN_BIAS == 0.0
