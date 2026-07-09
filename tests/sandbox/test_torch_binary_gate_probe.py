import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def test_energy_binary():
    from tools.torch_binary_gate_probe import _energy_binary
    assert _energy_binary(True, True) == 1.0        # composition reussie
    assert _energy_binary(True, False) == -0.3      # throw sans craft -> faim
    assert _energy_binary(False, True) == -0.3      # craft sans throw -> faim
    assert _energy_binary(False, False) == -0.3     # abstention -> faim


def test_binding_gap():
    from tools.torch_binary_gate_probe import _binding_gap
    # throw parfaitement conditionne sur craft -> gap = 1
    throws = [1, 1, 0, 0]; craft = [True, True, False, False]
    assert abs(_binding_gap(throws, craft) - 1.0) < 1e-6
    # throw independant du craft -> gap = 0
    throws2 = [1, 0, 1, 0]; craft2 = [True, True, False, False]
    assert abs(_binding_gap(throws2, craft2) - 0.0) < 1e-6
