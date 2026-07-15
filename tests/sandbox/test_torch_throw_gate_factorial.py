import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import run_arm


def test_run_arm_accepts_factorial_knobs():
    """run_arm accepte no_consume/weightless/conditional_credit et complete un run court sans crash,
    en renvoyant les cles attendues (les flags sont poses sur le monde avant la boucle)."""
    out = run_arm(shuffle=False, seed=0, ticks=6, warmup=2, n_agents=4, prey_count=15,
                  no_consume=True, weightless=True, conditional_credit=True,
                  base_metabolism=0.05, forage_payoff=3.0, energy=250.0, night=False,
                  penalty=0.0, antisat=0.3)
    assert "binding_gap_inworld" in out and "kills_with_tool" in out
    assert isinstance(out["binding_gap_inworld"], float)
