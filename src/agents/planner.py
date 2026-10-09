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


def update_transition(G_batch: np.ndarray, prev_H_rec: np.ndarray, next_H_rec: np.ndarray,
                      move_actions: np.ndarray, lr: float) -> np.ndarray:
    """MAJ en ligne de g : rapproche G[b, move_b] de la transition latente observée
    (next_H_rec - prev_H_rec)[b]. Modifie G_batch en place et le renvoie. move hors [0,A) ignoré."""
    B, A, N = G_batch.shape
    target = next_H_rec - prev_H_rec                       # (B, N)
    for b in range(B):
        a = int(move_actions[b])
        if 0 <= a < A:
            G_batch[b, a] += lr * (target[b] - G_batch[b, a])
    return G_batch


def mcts_instrumental_search(
    H_rec: np.ndarray,
    G_batch: np.ndarray,
    value_pos: np.ndarray,
    active_mask: np.ndarray | None = None,
    depth: int = 3,
    num_rollouts: int = 2,
    discount: float = 0.9,
    exploration_c: float = 1.0,
    rng: np.random.Generator | None = None,
    world_model: object | None = None,
    obs_batch: np.ndarray | None = None,
    curiosity_weight: float = 0.2,
) -> tuple[np.ndarray, np.ndarray]:
    """Recherche MCTS instrumentale adaptative (EXP-10 / Test-Time Compute).
    
    Simule des trajectoires contrefactuelles (s_hat, r_hat) sur l'espace latent
    en déroulant le modèle d'action G_batch sur une profondeur `depth` et en
    accumulant la valeur estimée (critique + curiosité intrinsèque World Model).
    """
    B, A, N = G_batch.shape
    if active_mask is None:
        active_mask = np.ones(B, dtype=bool)
    if rng is None:
        rng = np.random.default_rng(42)

    # Base: Q de profondeur 1
    Q_base = plan_rollout(H_rec, G_batch, value_pos)  # (B, A)
    Q_mcts = Q_base.copy()
    compute_spent = np.zeros(B, dtype=np.float32)

    active_indices = np.where(active_mask)[0]
    if len(active_indices) == 0 or depth <= 1:
        return Q_mcts, compute_spent

    for b in active_indices:
        v_idx = int(value_pos[b])
        h0 = H_rec[b]
        G_b = G_batch[b]  # (A, N)

        # Calcul optionnel de la surprise intrinsèque World Model
        wm_surprise = 0.0
        if world_model is not None and obs_batch is not None and b < len(obs_batch):
            try:
                curr_obs = obs_batch[b:b+1]
                pred = world_model.predict(curr_obs)
                targ = world_model.target(curr_obs)
                wm_surprise = float(np.mean(np.square(pred - targ)))
            except Exception:
                wm_surprise = 0.0

        # Pour chaque action initiale a0
        for a0 in range(A):
            total_return = 0.0
            h1 = h0 + G_b[a0]
            r0 = float(h1[v_idx]) if np.isfinite(h1[v_idx]) else 0.0
            r0 += curiosity_weight * wm_surprise

            for _ in range(num_rollouts):
                accumulated_r = r0
                gamma_prod = discount
                curr_h = h1.copy()

                # Déroulage sur la profondeur restante (depth - 1)
                for _d in range(depth - 1):
                    # Évaluation des actions candidates depuis curr_h
                    next_hs = curr_h[None, :] + G_b  # (A, N)
                    next_vals = next_hs[:, v_idx]     # (A,)
                    next_vals = np.nan_to_num(next_vals, nan=0.0, posinf=1.0, neginf=-1.0)

                    # Choix d'action : greedy avec bruit UCB/température
                    noise = rng.standard_normal(A) * 0.1 * exploration_c
                    best_next_a = int(np.argmax(next_vals + noise))
                    
                    r_step = float(next_vals[best_next_a])
                    accumulated_r += gamma_prod * r_step
                    gamma_prod *= discount
                    curr_h = next_hs[best_next_a]

                total_return += accumulated_r
                compute_spent[b] += float(depth)

            mean_return = total_return / max(1, num_rollouts)
            if np.isfinite(mean_return):
                Q_mcts[b, a0] = float(mean_return)

    # Sécurité numérique : élimination des NaN/Inf éventuels
    Q_mcts = np.nan_to_num(Q_mcts, nan=0.0, posinf=10.0, neginf=-10.0).astype(np.float32)
    return Q_mcts, compute_spent

