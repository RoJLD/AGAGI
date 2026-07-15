import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.factorial_regime_sweep import (REGIMES, run_sweep, _regime_main_effects_table)


def test_regimes_defined():
    """Les 3 régimes attendus sont définis, chacun avec les knobs de régime."""
    assert set(REGIMES) == {"neutralise", "letal", "rare"}
    for rk in REGIMES.values():
        assert set(rk) == {"night", "energy", "base_metabolism", "prey_sparse", "prey_dense"}
    assert REGIMES["neutralise"]["night"] is False        # baseline = EDR-177
    assert REGIMES["letal"]["night"] is True               # régime nuit létal


def test_regime_main_effects_table_pivots_by_factor():
    """_regime_main_effects_table (pur) pivote {régime: effects} en {facteur: {régime: effet}}."""
    regime_effects = {
        "A": {"main": {"no_consume": 0.4, "weightless": 0.0, "dense": 0.1, "conditional_credit": 0.0}},
        "B": {"main": {"no_consume": 0.5, "weightless": 0.3, "dense": 0.2, "conditional_credit": 0.0}},
    }
    tbl = _regime_main_effects_table(regime_effects)
    assert tbl["no_consume"] == {"A": 0.4, "B": 0.5}
    assert tbl["weightless"] == {"A": 0.0, "B": 0.3}       # F2 émerge en régime B
    assert set(tbl) == {"no_consume", "weightless", "dense", "conditional_credit"}


def test_run_sweep_smoke():
    """run_sweep tourne un sous-ensemble de régimes en config minuscule et renvoie cells+effects par régime."""
    tiny = {"neutralise": REGIMES["neutralise"], "rare": REGIMES["rare"]}
    out = run_sweep(tiny, seeds=(0,), ticks=6, warmup=2, n_agents=4)
    assert set(out) == {"neutralise", "rare"}
    for name, res in out.items():
        assert len(res["cells"]) == 16
        assert "main" in res["effects"] and "no_consume" in res["effects"]["main"]
