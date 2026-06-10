"""Câblage des gènes fantômes (EDR 031) : prouver qu'ils sont désormais LUS."""
import numpy as np

from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def test_thresholds_are_read_not_ghost():
    # Deux agents IDENTIQUES (même W, même H initial, même obs) sauf les SEUILS.
    # S'ils produisent des états DIFFÉRENTS, c'est que `thresholds` est lu (plus fantôme).
    np.random.seed(0)
    a0, a1 = MambaAgent(), MambaAgent()
    a1.genome.W = a0.genome.W.copy()
    if getattr(a0.genome, "W_router", None) is not None:
        a1.genome.W_router = a0.genome.W_router.copy()

    N = a0.genome.num_nodes
    a0.genome.thresholds = np.zeros(N, dtype=np.float32)        # neurones « faciles »
    a1.genome.thresholds = np.full(N, 3.0, dtype=np.float32)    # neurones « durs à exciter »
    a0.H_prev = np.zeros((1, N), dtype=np.float32)
    a1.H_prev = np.zeros((1, N), dtype=np.float32)

    model = MambaBatchModel([a0, a1])
    I = a0.genome.num_inputs
    model.forward(np.zeros((2, I), dtype=np.float32))

    # Avant le câblage : H_prev_batch[0] == [1] (seuils ignorés). Après : ils diffèrent.
    assert not np.allclose(model.H_prev_batch[0], model.H_prev_batch[1]), \
        "Les seuils n'affectent pas l'état -> gène encore fantôme."


def test_router_is_read_not_ghost():
    # Deux agents identiques sauf W_router -> avec une obs NON nulle, le gain neuromodulateur
    # diffère -> états différents => W_router est lu (plus fantôme).
    np.random.seed(2)
    a0, a1 = MambaAgent(), MambaAgent()
    a1.genome.W = a0.genome.W.copy()
    N = a0.genome.num_nodes
    a0.genome.thresholds = np.zeros(N, dtype=np.float32)
    a1.genome.thresholds = np.zeros(N, dtype=np.float32)
    I = a0.genome.num_inputs
    a0.genome.W_router = np.zeros((I, 3), dtype=np.float32)        # gain neutre (=1)
    a1.genome.W_router = np.full((I, 3), 0.5, dtype=np.float32)    # gain modulé par l'obs
    a0.H_prev = np.zeros((1, N), dtype=np.float32)
    a1.H_prev = np.zeros((1, N), dtype=np.float32)

    model = MambaBatchModel([a0, a1])
    obs = np.ones((2, I), dtype=np.float32)        # obs NON nulle (sinon mod=0, gain=1)
    model.forward(obs)
    assert not np.allclose(model.H_prev_batch[0], model.H_prev_batch[1]), \
        "W_router n'affecte pas l'état -> gène encore fantôme."


def test_zero_thresholds_is_identity():
    # Garde-fou : seuils nuls == comportement d'avant (pas de régression silencieuse).
    np.random.seed(1)
    a = MambaAgent()
    a.genome.thresholds = np.zeros(a.genome.num_nodes, dtype=np.float32)
    model = MambaBatchModel([a])
    assert np.all(model.thresholds_batch == 0.0)
