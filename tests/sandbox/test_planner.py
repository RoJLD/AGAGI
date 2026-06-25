import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.agents.planner import plan_rollout, normalize_q


def test_plan_rollout_reads_value_after_action_delta():
    # B=1, A=2, N=3 ; value_pos=2. G ajoute +5 à la position valeur pour l'action 1.
    H_rec = np.array([[0.0, 0.0, 1.0]], dtype=np.float32)
    G = np.zeros((1, 2, 3), dtype=np.float32)
    G[0, 1, 2] = 5.0                       # action 1 -> +5 sur la valeur
    value_pos = np.array([2])
    Q = plan_rollout(H_rec, G, value_pos)
    assert Q.shape == (1, 2)
    assert np.isclose(Q[0, 0], 1.0)        # action 0 : valeur inchangée
    assert np.isclose(Q[0, 1], 6.0)        # action 1 : 1 + 5


def test_plan_rollout_per_agent_value_pos():
    H_rec = np.array([[2.0, 0.0], [0.0, 3.0]], dtype=np.float32)
    G = np.zeros((2, 1, 2), dtype=np.float32)
    value_pos = np.array([0, 1])           # agent 0 lit pos 0, agent 1 lit pos 1
    Q = plan_rollout(H_rec, G, value_pos)
    assert np.isclose(Q[0, 0], 2.0)
    assert np.isclose(Q[1, 0], 3.0)


def test_normalize_q_centers_and_scales():
    Q = np.array([[1.0, 3.0]], dtype=np.float32)
    Z = normalize_q(Q)
    assert np.isclose(Z.mean(), 0.0, atol=1e-5)
    assert Z[0, 1] > Z[0, 0]               # ordre préservé


def test_normalize_q_constant_row_no_nan():
    Q = np.zeros((1, 4), dtype=np.float32)
    Z = normalize_q(Q)
    assert np.all(np.isfinite(Z))          # std+eps évite la division par 0
