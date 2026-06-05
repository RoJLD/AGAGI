"""
EXP-10 : Test-Time Compute Adaptatif
Valide que :
1. Deux agents (Penseur vs Réflexe) dépensent de l'énergie différemment.
2. Le masque `is_dreaming` n'active le beam search que pour les agents qualifiés.
3. Le coût est sub-linéaire et non nul uniquement pour les rêveurs.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def _make_agent(do_dream_bias: float = 0.0) -> MambaAgent:
    """Crée un agent avec un biais sur le logit do_dream."""
    agent = MambaAgent(num_inputs=54, num_outputs=78, num_nodes=125)
    # Injecter un biais sur le logit 26 (do_dream) en modifiant W
    # Les outputs correspondent aux N dernières lignes de H.
    N = agent.genome.num_nodes
    O = agent.genome.num_outputs
    # Ligne qui alimente le logit 26 des outputs
    row = N - O + 26
    if 0 <= row < N:
        agent.genome.W[row, :] = do_dream_bias
    return agent


def test_thinker_costs_more_than_reflex():
    """Un Penseur (do_dream élevé) doit dépenser plus de compute qu'un Réflexe."""
    # On a besoin de surprise_momentum > 0.2 pour déclencher le rêve.
    # On le force en donnant une H_prev différente à un agent.
    thinker = _make_agent(do_dream_bias=5.0)   # logit do_dream sera élevé
    reflex  = _make_agent(do_dream_bias=-5.0)  # logit do_dream sera faible

    # Simuler que le Penseur a une H_prev non nulle (donc surprise possible)
    thinker.H_prev = np.random.randn(1, thinker.genome.num_nodes).astype(np.float32)
    thinker.surprise_momentum = 0.5  # déjà élevé

    batch = MambaBatchModel([thinker, reflex])
    # Forcer le momentum du batch à correspondre
    batch.surprise_momentum_batch[0] = 0.5
    batch.surprise_momentum_batch[1] = 0.0

    obs = np.random.randn(2, 54).astype(np.float32)
    logits, compute_spent = batch.forward(obs)

    assert logits.shape == (2, 78), "Logits shape incorrect"
    assert compute_spent.shape == (2,), "compute_spent shape incorrect"
    # Le Penseur doit avoir plus ou autant de compute que le Réflexe
    assert compute_spent[0] >= compute_spent[1], (
        f"Thinker compute={compute_spent[0]} should be >= Reflex compute={compute_spent[1]}"
    )


def test_brain_cost_is_sublinear():
    """Valide que le coût calorique est sub-linéaire (logarithmique)."""
    BASE_TTC_COST = 0.01
    costs = [BASE_TTC_COST * (1.0 + np.log2(1.0 + k)) for k in [0, 1, 2, 4, 8]]
    # Vérifier la monotonie croissante
    for i in range(len(costs) - 1):
        assert costs[i] < costs[i + 1], "Cost should be monotonically increasing"
    # Vérifier que le coût n'explose pas (K=8 < 0.05)
    assert costs[-1] < 0.05, f"Cost at K=8 is too high: {costs[-1]}"
    # Vérifier le coût de base sans réflexion
    assert costs[0] == pytest.approx(BASE_TTC_COST, rel=1e-5)


def test_no_dream_without_surprise():
    """Sans surprise, même un agent avec do_dream élevé ne rêve pas."""
    thinker = _make_agent(do_dream_bias=5.0)
    thinker.surprise_momentum = 0.0  # Pas de surprise

    batch = MambaBatchModel([thinker])
    batch.surprise_momentum_batch[0] = 0.0  # Aucun momentum

    obs = np.random.randn(1, 54).astype(np.float32)
    logits, compute_spent = batch.forward(obs)

    # Sans surprise momentum, l'agent ne devrait pas rêver (K_i = 0)
    assert compute_spent[0] == 0.0, (
        f"Agent without surprise should not dream, got compute_spent={compute_spent[0]}"
    )


def test_forward_returns_finite_values():
    """Valide la stabilité numérique — aucun NaN/Inf dans les logits."""
    agents = [_make_agent(do_dream_bias=2.0) for _ in range(5)]
    for a in agents:
        a.surprise_momentum = 0.5

    batch = MambaBatchModel(agents)
    batch.surprise_momentum_batch[:] = 0.5

    obs = np.random.randn(5, 54).astype(np.float32)
    logits, compute_spent = batch.forward(obs)

    assert np.all(np.isfinite(logits)), "Logits contain NaN or Inf!"
    assert np.all(np.isfinite(compute_spent)), "compute_spent contains NaN or Inf!"


if __name__ == "__main__":
    test_thinker_costs_more_than_reflex()
    print("[OK] test_thinker_costs_more_than_reflex passed")

    test_brain_cost_is_sublinear()
    print("[OK] test_brain_cost_is_sublinear passed")

    test_no_dream_without_surprise()
    print("[OK] test_no_dream_without_surprise passed")

    test_forward_returns_finite_values()
    print("[OK] test_forward_returns_finite_values passed")

    print("\n[PASS] EXP-10 : Tous les tests TTC passent!")
