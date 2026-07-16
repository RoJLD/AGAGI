import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import inspect
import itertools
from tools.torch_throw_gate_inworld_ab import run_arm, compare_factorial, _factorial_effects


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


def test_factorial_effects_isolates_main_effect():
    """_factorial_effects (pur) : sur 16 cellules synthetiques ou diff=+1 SSI conditional_credit propre,
    l'effet principal de conditional_credit vaut +1.0 et les 3 autres 0.0 (isolation)."""
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        diff = 1.0 if cc else 0.0
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn,
                      "conditional_credit": cc, "diffs": [diff, diff]})
    eff = _factorial_effects(cells)
    assert abs(eff["main"]["conditional_credit"] - 1.0) < 1e-9
    assert abs(eff["main"]["no_consume"]) < 1e-9
    assert abs(eff["main"]["weightless"]) < 1e-9
    assert abs(eff["main"]["dense"]) < 1e-9
    assert "no_consume×conditional_credit" in eff["interactions"]


def test_factorial_effects_detects_interaction():
    """Interaction 2-way : diff=+1 SSI (no_consume ET conditional_credit) tous deux propres (effet
    non-additif). L'interaction no_consume×conditional_credit doit etre positive et non nulle."""
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        diff = 1.0 if (nc and cc) else 0.0
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn,
                      "conditional_credit": cc, "diffs": [diff]})
    eff = _factorial_effects(cells)
    assert eff["interactions"]["no_consume×conditional_credit"] > 0.2   # interaction reelle detectee


def test_compare_factorial_night_param_defaults_false():
    """EDR-178 : night est expose en param de compare_factorial, defaut False (non-regressif :
    le regime neutralise et le mode CLI factorial restent inchanges)."""
    sig = inspect.signature(compare_factorial)
    assert "night" in sig.parameters
    assert sig.parameters["night"].default is False


def test_compare_factorial_accepts_night_true():
    """compare_factorial accepte night=True (regime letal) et complete un run court sans crash,
    en renvoyant les 16 cellules."""
    cells = compare_factorial(seeds=(0,), prey_sparse=15, prey_dense=30, ticks=6, warmup=2,
                              n_agents=4, night=True)
    assert len(cells) == 16
