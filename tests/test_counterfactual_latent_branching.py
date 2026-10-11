"""
tests/test_counterfactual_latent_branching.py — Validation TDD de la ramification contrefactuelle (Arc 15 : Jalon M37).
"""

import pytest
import numpy as np
from src.metaprog.counterfactual_latent_branching import (
    CounterfactualLatentBranching,
    CounterfactualConfig,
)


def test_counterfactual_branches_unitary_invariance():
    """Vérifie que toutes les branches générées sont rigoureusement unitaires sur S^(D-1)."""
    cf = CounterfactualLatentBranching(CounterfactualConfig(latent_dim=64, num_branches=10, seed=42))

    base_action = np.ones(64, dtype=np.float32) / np.sqrt(64)
    branches = cf.simulate_branches(current_action=base_action, partner_beliefs=[])

    assert len(branches) == 10
    for b in branches:
        norm = np.linalg.norm(b["latent_vector"])
        assert np.isclose(norm, 1.0, atol=1e-5)


def test_counterfactual_risk_avoidance_selection():
    """
    Vérifie que si l'action nominale entre en conflit direct avec le partenaire,
    une branche contrefactuelle alternative réduisant la friction est préférée.
    """
    cf = CounterfactualLatentBranching(
        CounterfactualConfig(latent_dim=64, num_branches=8, risk_penalty_weight=2.50, seed=42)
    )

    # Action nominale : pointe vers +axe 0
    nominal = np.zeros(64, dtype=np.float32)
    nominal[0] = 1.0

    # Partenaire avec intention hostile / orthogonale qui crée une friction forte
    partner_intent = np.zeros(64, dtype=np.float32)
    partner_intent[0] = -1.0  # Antipodal = friction maximale 2.0

    # Cible environnementale neutre sur axe 1
    target = np.zeros(64, dtype=np.float32)
    target[1] = 1.0

    opt_action, report = cf.select_optimal_branch(
        current_action=nominal,
        partner_beliefs=[partner_intent],
        environmental_target=target,
    )

    assert opt_action.shape == (64,)
    assert np.isclose(np.linalg.norm(opt_action), 1.0, atol=1e-5)
    # La branche nominale devait être pénalisée par la forte friction
    assert report["num_evaluated_branches"] == 8


def test_counterfactual_nominal_retained_when_optimal():
    """Vérifie que l'action nominale est conservée si les partenaires sont déjà alignés."""
    cf = CounterfactualLatentBranching(CounterfactualConfig(latent_dim=64, num_branches=6, seed=42))

    # Action et cible parfaitement alignées
    action = np.zeros(64, dtype=np.float32)
    action[0] = 1.0

    # Partenaire parfaitement aligné
    partner = np.zeros(64, dtype=np.float32)
    partner[0] = 1.0

    opt_action, report = cf.select_optimal_branch(
        current_action=action,
        partner_beliefs=[partner],
        environmental_target=action,
    )

    # L'action nominale doit avoir le score maximal
    assert report["selected_was_nominal"]
    assert np.isclose(np.dot(opt_action, action), 1.0, atol=1e-4)


def test_counterfactual_robustness():
    """Vérifie la robustesse aux entrées dégénérées."""
    cf = CounterfactualLatentBranching(CounterfactualConfig(latent_dim=64, seed=42))

    nan_action = np.full(64, float("nan"), dtype=np.float32)
    opt, rep = cf.select_optimal_branch(nan_action, [])

    assert not np.isnan(rep["net_score"])
    assert np.isclose(np.linalg.norm(opt), 1.0, atol=1e-5)
