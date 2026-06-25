"""Planificateur latent Dreamer-lite (NAS Axe 3 — activation du dreaming).
Anticipation conditionnée par l'action : pour chaque action a, prédire le latent suivant
H'_a = H_rec + G[a] et le scorer par la value head. Fonctions PURES (testables isolément)."""
import numpy as np


def plan_rollout(H_rec: np.ndarray, G_batch: np.ndarray, value_pos: np.ndarray) -> np.ndarray:
    """Q_plan[b,a] = valeur prédite si l'agent b joue l'action a (profondeur 1).
    H_rec: (B,N) latent post-récurrence. G_batch: (B,A,N) deltas action. value_pos: (B,) index valeur."""
    B, A, N = G_batch.shape
    Hp = H_rec[:, None, :] + G_batch                       # (B, A, N)
    rows = np.arange(B)[:, None]                           # (B,1)
    cols = np.arange(A)[None, :]                           # (1,A)
    Q = Hp[rows, cols, value_pos[:, None]]                 # (B, A)
    return Q.astype(np.float32)


def normalize_q(Q: np.ndarray) -> np.ndarray:
    """Centre (moyenne 0) + échelle robuste par agent -> biais comparable quelle que soit
    l'échelle de la value head. std+1e-6 évite la division par 0 (ligne constante)."""
    mean = Q.mean(axis=1, keepdims=True)
    std = Q.std(axis=1, keepdims=True) + 1e-6
    return ((Q - mean) / std).astype(np.float32)
