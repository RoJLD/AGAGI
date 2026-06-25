import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.anticipation_bench import run_bench, compare
from src.agents.mamba_agent import MambaBatchModel


def test_run_bench_returns_survival():
    out = run_bench(plan_bias=0.0, seeds=[0, 1], steps=40)
    assert "survival_mean" in out and 0.0 <= out["survival_mean"] <= 1.0
    assert len(out["per_seed"]) == 2


def test_compare_structure():
    out = compare(seeds=[0, 1, 2], steps=40)
    assert set(["verdict", "median_ratio", "sign_p", "n_favorable", "n"]).issubset(out)
    assert out["verdict"] in ("PLAN_GAGNE", "PLAN_PERD", "NEUTRE")


def test_plan_flags_restored_after_bench():
    """PLAN_A et PLAN_BIAS doivent être restaurés à leurs valeurs d'origine après run_bench,
    même si plan_bias != 0. Vérifie que le finally restaure correctement."""
    orig_bias = MambaBatchModel.PLAN_BIAS
    orig_a = MambaBatchModel.PLAN_A
    run_bench(plan_bias=0.5, seeds=[0], steps=10)
    assert MambaBatchModel.PLAN_BIAS == orig_bias, "PLAN_BIAS non restauré"
    assert MambaBatchModel.PLAN_A == orig_a, "PLAN_A non restauré"


def test_temporal_gap_exists():
    """Vérifie que la récompense −1 n'est PAS donnée au tick d'avertissement lui-même
    (tick 0 = premier warn) mais au tick de frappe (tick 1 si l'agent reste).
    On use d'une heuristique : si l'agent reste immobile (move=1) et meurt,
    alive_ticks doit valoir 1 (a survécu le tick d'avertissement, mort au tick suivant)."""
    import numpy as np
    from src.agents.mamba_agent import MambaAgent, MambaBatchModel
    # Forcer l'agent à toujours rester (patch argmax → 1)
    orig = np.argmax
    results = []
    def fake_argmax(arr, **kw):
        results.append(1)   # toujours action 1 = rester
        return np.int64(1)
    np.argmax = fake_argmax
    try:
        out = run_bench(plan_bias=0.0, seeds=[42], steps=20)
        # L'agent démarre au centre (L//2 = 3), tick 0 = warn, danger_cell = 3.
        # Tick 1 : frappe → l'agent est mort. alive_ticks = 1.
        assert out["per_seed"][0]["survival"] == 1 / 20, \
            f"Attendu 1/20 = 0.05, obtenu {out['per_seed'][0]['survival']}"
    finally:
        np.argmax = orig
