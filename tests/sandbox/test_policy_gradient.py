"""Tests du vrai policy gradient — crédit d'action (EDR 020)."""
import numpy as np
import pytest

from src.seed_ai.policy_gradient import reinforce_action_update, _softmax, td_error


def test_td_error_temporal_credit():
    # Crédit temporel : récompense immédiate NÉGATIVE (coût du craft) mais état suivant de
    # forte valeur -> avantage POSITIF (ce que le critic MC immédiat ne voyait pas).
    delta = td_error(reward=-2.0, value=1.0, next_value=10.0, gamma=0.9)
    assert delta > 0.0                        # -2 + 0.9*10 - 1 = 6.0
    # Sans futur (état terminal nul) -> se réduit à l'avantage immédiat r - V.
    assert td_error(5.0, 2.0, 0.0, gamma=0.9) == pytest.approx(3.0)
    # γ règle l'horizon : myope (γ=0) ignore le futur.
    assert td_error(-2.0, 1.0, 10.0, gamma=0.0) == pytest.approx(-3.0)


def _move_logit(W, h, N, O, m):
    """Logit de l'action de mouvement m = somme des poids entrants au nœud (N-O+m)."""
    return float((W[:, (N - O) + m] * h).sum())


def test_credits_chosen_movement_punishes_others():
    # Propriété centrale que le Hebbien rustre n'avait PAS : l'action choisie voit son
    # logit AUGMENTER (crédit d'action), les non-choisies baisser.
    N, O = 12, 8
    rng = np.random.default_rng(0)
    W = (rng.standard_normal((N, N)) * 0.1).astype(np.float32)
    h = np.ones(N, dtype=np.float32)
    out_logits = np.zeros(O, dtype=np.float32)
    chosen = 3
    dW = reinforce_action_update(h, out_logits, chosen_move=chosen, binary_actions={},
                                 advantage=1.0, lr=0.1)
    W2 = W + dW
    assert _move_logit(W2, h, N, O, chosen) > _move_logit(W, h, N, O, chosen)   # renforcé
    assert _move_logit(W2, h, N, O, 0) < _move_logit(W, h, N, O, 0)             # affaibli


def test_negative_advantage_punishes_chosen():
    # Avantage négatif -> l'action choisie est DÉCOURAGÉE (logit baisse).
    N, O = 12, 8
    W = np.zeros((N, N), dtype=np.float32)
    h = np.ones(N, dtype=np.float32)
    out_logits = np.zeros(O, dtype=np.float32)
    dW = reinforce_action_update(h, out_logits, chosen_move=2, binary_actions={},
                                 advantage=-1.0, lr=0.1)
    assert _move_logit(dW, h, N, O, 2) < 0.0


def test_binary_grab_is_credited():
    # grab pris (idx 6) + avantage positif -> logit de grab augmente.
    N, O = 10, 8
    W = np.zeros((N, N), dtype=np.float32)
    h = np.ones(N, dtype=np.float32)
    out_logits = np.zeros(O, dtype=np.float32)
    dW = reinforce_action_update(h, out_logits, chosen_move=-1, binary_actions={6: True},
                                 advantage=1.0, lr=0.1)
    node = (N - O) + 6
    assert float((dW[:, node] * h).sum()) > 0.0
    # grab NON pris + avantage positif -> logit de grab baisse (decourage)
    dW2 = reinforce_action_update(h, out_logits, chosen_move=-1, binary_actions={6: False},
                                  advantage=1.0, lr=0.1)
    assert float((dW2[:, node] * h).sum()) < 0.0


def test_repeated_updates_converge_to_chosen_action():
    # Répéter le crédit d'une action (avantage positif) -> sa proba -> ~1 (apprentissage).
    N, O, n_move = 9, 8, 8
    W = np.zeros((N, N), dtype=np.float32)
    h = np.ones(N, dtype=np.float32)
    chosen = 5
    for _ in range(200):
        out_logits = (W[:, N - O:N] * h[:, None]).sum(axis=0)  # logits courants
        dW = reinforce_action_update(h, out_logits, chosen_move=chosen, binary_actions={},
                                     advantage=1.0, lr=0.1)
        W = W + dW
    out_logits = (W[:, N - O:N] * h[:, None]).sum(axis=0)
    pi = _softmax(out_logits[:n_move])
    assert pi[chosen] > 0.9   # le geste récompensé est appris (proba quasi 1)


def test_no_crash_on_degenerate_shapes():
    N, O = 5, 8  # O > N -> base < 0, doit renvoyer dW nul sans crasher
    dW = reinforce_action_update(np.ones(N), np.zeros(O), 2, {4: True}, 1.0, 0.1)
    assert dW.shape == (N, N)
    assert not dW.any()
