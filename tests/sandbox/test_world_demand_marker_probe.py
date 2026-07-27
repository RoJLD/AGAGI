"""Tests du marqueur de demande d'intelligence (S2-001). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.world_demand_marker_probe import run_world, fit_policy
import numpy as np


def test_ablation_collapses_survival_only_when_demanded():
    # WITHIN : ablater la perception effondre la survie dans DEMANDING, pas dans TRIVIAL.
    dem = run_world(True, K=4, seed=0)
    triv = run_world(False, K=4, seed=0)
    assert dem["fit_ablated"] < dem["fit_true"] * 0.6      # demanding : perception porteuse
    assert triv["fit_ablated"] > triv["fit_true"] * 0.9    # trivial : ablation ~inoffensive


def test_policy_weights_obs_only_when_informative():
    # corroborant : |W| (poids sur l'obs) >0 dans DEMANDING, ~0 dans TRIVIAL.
    dem = run_world(True, K=4, seed=1)
    triv = run_world(False, K=4, seed=1)
    assert dem["obs_weight"] > 0.2
    assert triv["obs_weight"] < 0.1


def test_between_subject_false_positive_on_trivial():
    # BETWEEN « un survivant existe » crie « demande » même dans TRIVIAL (faux positif).
    triv = run_world(False, K=4, seed=2)
    assert triv["fit_true"] > triv["random_action"] * 1.5   # survivant compétent existe...
    # ... alors que la perception n'est PAS demandée (validé par les autres tests) -> marqueur trompeur.


def test_fit_policy_returns_shapes():
    W, b, score = fit_policy(True, K=4, seed=3, iters=80, episodes=3, ticks=100)
    assert W.shape == (4, 4) and b.shape == (4,)
    assert score > 0
