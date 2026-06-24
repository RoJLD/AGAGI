import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.environments.config import WorldConfig
from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def test_kwta_keep_frac_config_default_is_one():
    assert WorldConfig().kwta_keep_frac == 1.0


def test_kwta_class_attr_default_is_one():
    assert MambaBatchModel.KWTA_KEEP_FRAC == 1.0


def _forward_capture(keep_frac):
    np.random.seed(0)
    a = MambaAgent()
    np.random.seed(123)
    m = MambaBatchModel([a])
    MambaBatchModel.KWTA_KEEP_FRAC = keep_frac
    I = a.genome.num_inputs
    np.random.seed(123)
    m.forward(np.ones((1, I), dtype=np.float32))
    MambaBatchModel.KWTA_KEEP_FRAC = 1.0  # reset global
    return m.H_prev_batch.copy(), m.mappings[0], a.genome


def test_kwta_sparsifies_hidden_preserves_io():
    H_off, map_idx, g = _forward_capture(1.0)
    H_on, _, _ = _forward_capture(0.5)
    I, O, N = g.num_inputs, g.num_outputs, g.num_nodes
    # Entrées et sorties INCHANGÉES par KWTA
    np.testing.assert_array_equal(H_off[0, map_idx[:I]], H_on[0, map_idx[:I]])
    np.testing.assert_array_equal(H_off[0, map_idx[N - O:N]], H_on[0, map_idx[N - O:N]])
    # Cachés : KWTA 0.5 a STRICTEMENT plus de zéros que KWTA off
    hid_off = H_off[0, map_idx[I:N - O]]
    hid_on = H_on[0, map_idx[I:N - O]]
    assert np.count_nonzero(hid_on) < np.count_nonzero(hid_off)
    assert np.count_nonzero(hid_on) >= 1   # jamais totalement éteint
