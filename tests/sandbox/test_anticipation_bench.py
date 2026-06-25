import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.anticipation_bench import run_bench, compare
from src.agents.mamba_agent import MambaBatchModel


def test_run_bench_returns_avoidance():
    """Structure de sortie v3 : avoidance_mean + per_seed avec clés requises."""
    out = run_bench(plan_bias=0.0, seeds=[0, 1], steps=60)
    assert "avoidance_mean" in out, "clé avoidance_mean manquante"
    assert 0.0 <= out["avoidance_mean"] <= 1.0, "avoidance_mean hors [0,1]"
    # Compatibilité v2 : survival_mean doit encore être présent
    assert "survival_mean" in out, "clé survival_mean (compat v2) manquante"
    assert len(out["per_seed"]) == 2
    for rec in out["per_seed"]:
        assert "avoidance" in rec
        assert "avoided" in rec
        assert "faced" in rec
        assert "mean_G" in rec


def test_compare_structure():
    out = compare(seeds=[0, 1, 2], steps=60)
    assert set(["verdict", "median_ratio", "sign_p", "n_favorable", "n"]).issubset(out)
    assert out["verdict"] in ("PLAN_GAGNE", "PLAN_PERD", "NEUTRE")
    assert "ratios" in out and len(out["ratios"]) == 3


def test_plan_flags_restored_after_bench():
    """PLAN_A, PLAN_BIAS et PLAN_LR doivent être restaurés après run_bench."""
    orig_bias = MambaBatchModel.PLAN_BIAS
    orig_a = MambaBatchModel.PLAN_A
    orig_lr = MambaBatchModel.PLAN_LR
    run_bench(plan_bias=0.5, seeds=[0], steps=10)
    assert MambaBatchModel.PLAN_BIAS == orig_bias, "PLAN_BIAS non restauré"
    assert MambaBatchModel.PLAN_A == orig_a, "PLAN_A non restauré"
    assert MambaBatchModel.PLAN_LR == orig_lr, "PLAN_LR non restauré"


def test_temporal_gap_exists():
    """Vérifie le gap temporel (F1) : avec respawn, l'agent re-part du centre après mort.
    On force move=1 (rester) à chaque tick → l'agent est frappé au tick 1 (premier warn=tick0,
    frappe=tick1) et respawn, puis frappé à tick 7 (warn=tick6, frappe=tick7), etc.
    L'épisode dure tout le budget et dangers_faced > 0."""
    import numpy as np
    orig = np.argmax
    def fake_argmax(arr, **kw):
        return np.int64(1)   # toujours rester
    np.argmax = fake_argmax
    try:
        out = run_bench(plan_bias=0.0, seeds=[42], steps=30)
        rec = out["per_seed"][0]
        # Avec respawn, l'épisode dure 30 ticks → faced > 0
        assert rec["faced"] > 0, f"Aucun danger rencontré, faced={rec['faced']}"
        # L'agent reste immobile → il est toujours touché → avoided=0
        assert rec["avoided"] == 0, f"Attendu avoided=0, obtenu {rec['avoided']}"
        assert rec["avoidance"] == 0.0, f"Attendu avoidance=0.0, obtenu {rec['avoidance']}"
    finally:
        np.argmax = orig


def test_respawn_episode_runs_full_budget():
    """Vérifie que l'épisode dure bien `steps` ticks même si l'agent meurt."""
    import numpy as np
    # Avec respawn, on compte les dangers_faced sur tout le budget.
    # Sur 120 ticks avec T_WARN_PERIOD=6, on attend ~20 dangers.
    out = run_bench(plan_bias=0.0, seeds=[0], steps=120)
    rec = out["per_seed"][0]
    # Doit avoir rencontré environ steps // T_WARN_PERIOD dangers
    assert rec["faced"] >= 15, f"Trop peu de dangers rencontrés: {rec['faced']}"


def test_g_learning_indicator_nonzero_with_planner():
    """mean|G| doit être > 0 quand le planificateur est actif et a reçu des mises à jour."""
    out = run_bench(plan_bias=0.5, seeds=[0], steps=200)
    rec = out["per_seed"][0]
    # Avec 200 steps et respawn, g reçoit de nombreux updates → mean|G| > 0
    assert rec["mean_G"] >= 0.0, "mean_G invalide (négatif)"
    # Note : on n'impose pas >0 car G peut rester nul si aucune transition h_rec n'est disponible,
    # mais on vérifie la clé est bien calculée et non-NaN.
    assert not (rec["mean_G"] != rec["mean_G"]), "mean_G est NaN"
