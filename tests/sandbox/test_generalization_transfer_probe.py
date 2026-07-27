"""Tests du transfert / vraie généralisation (G1-001, porte G1). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.generalization_transfer_probe import run, fit_policy, evaluate


def test_core_transfers_in_both_regimes():
    # le noyau (θ-indépendant) transfère dans les deux régimes.
    r = run(K=6, seed=0)
    assert r["MONO"]["core"] > 0.8
    assert r["MULTI"]["core"] > 0.8


def test_specific_generalizes_only_under_varied_training():
    # le skill world-spécifique ne transfère qu'en entraînement multi-mondes.
    r = run(K=6, seed=1)
    assert r["MULTI"]["spec_true"] > 0.6
    assert r["MONO"]["spec_true"] < 0.4


def test_ablation_collapses_multi_but_not_mono():
    # WITHIN : ablater θ effondre le spécifique MULTI (causal) et est inerte sur MONO (θ jamais utilisé).
    r = run(K=6, seed=2)
    assert r["MULTI"]["spec_true"] - r["MULTI"]["spec_ablated"] > 0.3
    assert abs(r["MONO"]["spec_true"] - r["MONO"]["spec_ablated"]) < 0.15


def test_theta_weight_corroborates():
    # corroborant : la tête spécifique pèse θ en MULTI, ~pas en MONO (biais).
    r = run(K=6, seed=3)
    assert r["MULTI"]["theta_w"] > r["MONO"]["theta_w"] + 0.3


def test_evaluate_shapes():
    Wc, Ws = fit_policy(True, theta_A=0, K=4, seed=4)
    core, spec = evaluate(Wc, Ws, theta_B=2, theta_obs_mode="true", K=4, seed=4, n=200)
    assert 0.0 <= core <= 1.0 and 0.0 <= spec <= 1.0
