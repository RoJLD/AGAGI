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


def test_run_arm_smoke_on_and_off():
    from tools.torch_binary_gate_probe import run_arm
    r_on = run_arm(gate_on=True, episodes=60, n_agents=16, seed=0)
    r_off = run_arm(gate_on=False, episodes=60, n_agents=16, seed=0)
    for r in (r_on, r_off):
        assert set(["gate_on", "binding_gap", "comp_rate", "throw_rate"]).issubset(r)
        assert -1.0 <= r["binding_gap"] <= 1.0
        assert 0.0 <= r["throw_rate"] <= 1.0


def test_verdict_pure_on_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.30}, {"diff": 0.25}, {"diff": 0.40}]   # gap_ON - gap_OFF > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
