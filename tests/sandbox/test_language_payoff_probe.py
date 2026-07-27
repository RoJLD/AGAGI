"""Tests du payoff du langage (LANG-006, porte G3). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.language_payoff_probe import run_world, fit_protocol, survive
import numpy as np


def test_channel_ablation_collapses_only_when_coordination_demanded():
    # WITHIN : ablater le canal effondre la survie dans DEMAND, pas dans TRIVIAL.
    dem = run_world(True, K=4, seed=0)
    triv = run_world(False, K=4, seed=0)
    assert dem["surv_ablated"] < dem["surv_true"] * 0.6      # coordination : canal porteur
    assert triv["surv_ablated"] > triv["surv_true"] * 0.9    # trivial : ablation inoffensive


def test_channel_used_only_when_it_pays():
    # corroborant : MI(message;action) >0 dans DEMAND, ~0 dans TRIVIAL (canal ignoré s'il ne paie pas).
    dem = run_world(True, K=4, seed=1)
    triv = run_world(False, K=4, seed=1)
    assert dem["mi"] > 0.3
    assert triv["mi"] < 0.15


def test_nocomm_survives_trivial_but_not_demanding():
    # la tâche TRIVIAL est résoluble SANS canal (action fixe) ; la DEMANDING non -> le canal apporte de la valeur.
    dem = run_world(True, K=4, seed=2)
    triv = run_world(False, K=4, seed=2)
    assert triv["surv_nocomm"] > triv["surv_true"] * 0.9
    assert dem["surv_nocomm"] < dem["surv_true"] * 0.6


def test_fit_protocol_shapes():
    Ws, Wr = fit_protocol(True, K=4, M=4, seed=3, iters=80, episodes=3, ticks=100)
    assert Ws.shape == (4, 4) and Wr.shape == (4, 4)
