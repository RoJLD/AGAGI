import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import run_arm, compare_factorial


def test_run_arm_accepts_factorial_knobs():
    """run_arm accepte no_consume/weightless/conditional_credit et complete un run court sans crash,
    en renvoyant les cles attendues (les flags sont poses sur le monde avant la boucle)."""
    out = run_arm(shuffle=False, seed=0, ticks=6, warmup=2, n_agents=4, prey_count=15,
                  no_consume=True, weightless=True, conditional_credit=True,
                  base_metabolism=0.05, forage_payoff=3.0, energy=250.0, night=False,
                  penalty=0.0, antisat=0.3)
    assert "binding_gap_inworld" in out and "kills_with_tool" in out
    assert isinstance(out["binding_gap_inworld"], float)


def test_compare_factorial_returns_16_cells():
    """compare_factorial produit les 16 cellules 2^4 distinctes, dont la cellule-0 tout-propre
    (T,T,T,T), chacune avec verdict + diffs. Config minuscule (smoke)."""
    cells = compare_factorial(seeds=(0,), prey_sparse=15, prey_dense=30, ticks=6, warmup=2, n_agents=4)
    assert len(cells) == 16
    keys = {(c["no_consume"], c["weightless"], c["dense"], c["conditional_credit"]) for c in cells}
    assert len(keys) == 16                                    # toutes les combinaisons distinctes
    assert (True, True, True, True) in keys                   # cellule-0 (tout-propre)
    for c in cells:
        assert "verdict" in c and "median_diff" in c and isinstance(c["diffs"], list)
        assert c["prey_count"] == (30 if c["dense"] else 15)  # densite mappee sur prey_count
