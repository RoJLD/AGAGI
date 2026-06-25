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


def test_plan_bias_off_is_bit_identical():
    np.random.seed(0)
    a = MambaAgent(); a.genome.organ_genes = np.array([True, False])  # organe dreaming ON
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    MambaBatchModel.PLAN_BIAS = 0.0
    m1 = MambaBatchModel([a.clone()]); p1, _ = m1.forward(obs.copy())
    m2 = MambaBatchModel([a.clone()]); p2, _ = m2.forward(obs.copy())
    assert np.allclose(p1, p2)                       # déterminisme + non-régression OFF


def test_plan_bias_on_shifts_action_logits():
    a = MambaAgent(); a.genome.organ_genes = np.array([True, False])
    N = a.genome.num_nodes
    # G qui privilégie fortement l'action 3 (grand +valeur)
    G = np.zeros((MambaBatchModel.PLAN_A, N), dtype=np.float32)
    val_node = N - a.genome.num_outputs + 28
    G[3, val_node] = 50.0
    a.planner_G = G
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    MambaBatchModel.PLAN_BIAS = 1.0
    try:
        m = MambaBatchModel([a]); preds, _ = m.forward(obs)
        assert int(np.argmax(preds[0, :8])) == 3     # le plan pousse l'action 3
    finally:
        MambaBatchModel.PLAN_BIAS = 0.0              # restaurer le défaut global
