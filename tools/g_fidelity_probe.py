"""tools/g_fidelity_probe.py — Sonde de fidélité de g (NAS Axe 3, spec dream-offline, composant A).
go/no-go : g(H,a)→H' prédit-il les transitions latentes mieux que la baseline « pas de changement » ?
Si NON -> escalader vers g bilinéaire avant de bâtir Dyna. AUCUN changement du code cœur.

Deux mesures disponibles :
  collect_ratios     — obs synthétiques (artefact corrigé : round-robin + obs variables σ=0.3)
  collect_ratios_env — env grille 1-D réel (action→pos→obs couplé) : mesure CAUSALE de référence

Usage : GFP_SEEDS=0,1,2 python tools/g_fidelity_probe.py
        GFP_SEEDS=0,1,2 GFP_ENV=0 python tools/g_fidelity_probe.py  (mode synthétique)"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel

# --- Constantes env grille (bench-compatible) ---
_GRID_L = 7           # longueur de la grille 1-D
_T_WARN_PERIOD = 6    # période de télégraphe du danger
_N_MOVES = 3          # espace d'action : 0=gauche, 1=rester, 2=droite
_OBS_DIM = 2 * _GRID_L   # = 14 : one-hot(pos) ++ one-hot(danger)


def _obs_bench(pos: int, danger_cell) -> np.ndarray:
    """Obs 1-D grille : one-hot position (L) ++ one-hot danger télégraphié (L)."""
    o = np.zeros(_OBS_DIM, dtype=np.float32)
    o[pos] = 1.0
    if danger_cell is not None:
        o[_GRID_L + danger_cell] = 1.0
    return o


def transition_error(H_prev, g_delta, H_next):
    """(g_err, base_err) pour une transition latente. g_err = prédiction de g ; base_err = baseline."""
    H_prev = np.asarray(H_prev, dtype=np.float32)
    g_delta = np.asarray(g_delta, dtype=np.float32)
    H_next = np.asarray(H_next, dtype=np.float32)
    g_err = float(np.mean((H_prev + g_delta - H_next) ** 2))
    base_err = float(np.mean((H_prev - H_next) ** 2))
    return g_err, base_err


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def fidelity_verdict(ratios) -> dict:
    """ratios[i] = g_err/base_err par transition. g UTILE = ratio < 1 (g bat la baseline)."""
    ratios = [float(r) for r in ratios]
    n = len(ratios)
    if n == 0:
        return {"median_ratio": 1.0, "n_favorable": 0, "n": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = st.median(ratios)
    n_fav = sum(1 for r in ratios if r < 1.0)            # favorable = g meilleur
    eff = [r for r in ratios if r != 1.0]
    sign_p = _sign_p(sum(1 for r in eff if r < 1.0), len(eff))
    if med < 0.95 and 2 * n_fav > n:
        verdict = "G_FIDELE"
    elif med > 1.05:
        verdict = "G_INUTILE"
    else:
        verdict = "NEUTRE"
    return {"median_ratio": float(med), "n_favorable": int(n_fav), "n": int(n),
            "sign_p": float(sign_p), "verdict": verdict}


def collect_ratios(seed: int, warmup: int = 300, measure: int = 300):
    """Boucle pilotée : exercice en round-robin des PLAN_A actions (diversité d'actions),
    obs non-nulles variables (régime non-trivial), g apprend en ligne (PLAN_BIAS>0).
    Enregistre g_err/base_err par transition (action RÉELLEMENT jouée à ce tick).
    Restaure les flags en finally.
    Retourne aussi action_abs_by_action : dict action -> list |G[a]| moyens pour diagnostic."""
    rng = np.random.default_rng(seed)
    a = MambaAgent()
    a.genome.organ_genes = np.array([True, False])          # organe planificateur actif (g se met à jour)
    prev_bias, prev_a, prev_lr = (MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_LR = 0.1
    ratios = []
    action_abs_by_action: dict = {a_idx: [] for a_idx in range(MambaBatchModel.PLAN_A)}
    try:
        m = MambaBatchModel([a])
        n_in = a.genome.num_inputs
        n_actions = MambaBatchModel.PLAN_A
        map_idx = m.mappings[0]
        prev_hrec = None
        prev_move = None
        for t in range(warmup + measure):
            # FIX 2 — obs non-nulles VARIABLES par tick (régime non-trivial, déterministe par seed)
            obs = rng.standard_normal((1, n_in)).astype(np.float32) * 0.3
            preds, _ = m.forward(obs)
            # FIX 1 — round-robin des actions pour exercer les 8 colonnes de G
            move = int(t % n_actions)
            # H_rec courant en ordre nœud (capturé par forward, avant le rêve)
            cur_hrec = m.H_rec_batch[0, map_idx].copy()
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_delta = m.G_batch[0][:, map_idx][prev_move]    # colonne de l'action JOUÉE au tick précédent
                g_err, base_err = transition_error(prev_hrec, g_delta, cur_hrec)
                # FIX 3 — seuil relevé : ignorer les transitions de très faible amplitude
                if base_err > 0.01:
                    ratios.append(g_err / base_err)
            # Diagnostic diversité : mean|G[a]| pour l'action jouée à ce tick
            g_col = m.G_batch[0][:, map_idx][move]               # (N_i,)
            action_abs_by_action[move].append(float(np.mean(np.abs(g_col))))
            # apprentissage en ligne de g (transition différée) : nécessite compute_policy_gradient
            m.compute_policy_gradient(np.array([0.1], dtype=np.float32),
                                      [{"move": move, "grab": 0, "rub": 0}])
            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR = prev_bias, prev_a, prev_lr
    return ratios, action_abs_by_action


def run_probe(seeds, warmup: int = 300, measure: int = 300) -> dict:
    """Agrège collect_ratios sur plusieurs seeds. Retourne le verdict + diagnostics action."""
    all_ratios = []
    # accumulate mean|G[a]| per action across seeds
    n_actions = MambaBatchModel.PLAN_A
    action_abs_accum: dict = {a_idx: [] for a_idx in range(n_actions)}
    for s in seeds:
        ratios, action_abs = collect_ratios(int(s), warmup, measure)
        all_ratios.extend(ratios)
        for a_idx in range(n_actions):
            action_abs_accum[a_idx].extend(action_abs[a_idx])
    result = fidelity_verdict(all_ratios)
    result["mean_G_abs_by_action"] = {
        a_idx: float(np.mean(vals)) if vals else 0.0
        for a_idx, vals in action_abs_accum.items()
    }
    return result


def collect_ratios_env(seed: int, warmup: int = 300, measure: int = 300):
    """Mesure de fidélité de g dans un env où les ACTIONS ONT DE VRAIES CONSEQUENCES.

    Env : grille 1-D de longueur L=7 (bench-compatible).
    - obs = one-hot(pos) ++ one-hot(danger_telegraph) — 14 dimensions
    - move ∈ {0=gauche, 1=rester, 2=droite} change réellement la position
    - Donc : action → pos' → obs' : le lien action→next-obs EST présent par construction.

    Couverture des actions : round-robin sur {0,1,2} (force G[0..2] tous entraînés et mesurés).
    PLAN_A=3 (aligne g sur l'espace d'action réel du bench).
    Restaure PLAN_BIAS/PLAN_A/PLAN_LR en finally.

    Retourne
    --------
    ratios              : list[float]   g_err/base_err par transition (base_err > 0.01 filtrée)
    action_abs_by_action: dict          action -> list mean|G[a]| (preuve de diversité)
    """
    np.random.seed(seed)   # reproductibilité du réseau (MambaAgent utilise np.random)
    # Agent dimensionné pour l'obs du bench (14 entrées)
    a = MambaAgent(num_inputs=_OBS_DIM, num_outputs=108, num_nodes=172)
    a.genome.organ_genes = np.array([True, False])          # organe planificateur actif

    prev_bias = MambaBatchModel.PLAN_BIAS
    prev_plan_a = MambaBatchModel.PLAN_A
    prev_plan_lr = MambaBatchModel.PLAN_LR
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_A = _N_MOVES     # 3 : aligne g sur l'espace action réel
    MambaBatchModel.PLAN_LR = 0.1
    # Seuil adapté aux obs one-hot (amplitude ~10× plus faible qu'obs gaussiennes σ=0.3)
    _BASE_ERR_THRESH = 1e-4
    ratios = []
    action_abs_by_action: dict = {a_idx: [] for a_idx in range(_N_MOVES)}
    try:
        m = MambaBatchModel([a])
        map_idx = m.mappings[0]

        # État env : déterministe via seed numpy
        pos = _GRID_L // 2
        pending_danger = None

        prev_hrec = None
        prev_move = None

        for t in range(warmup + measure):
            # --- Résoudre la frappe du tick précédent (gap temporel F1 du bench) ---
            strike_cell = pending_danger
            pending_danger = None
            if strike_cell is not None:
                if pos == strike_cell:
                    # Respawn au centre (comme bench R1)
                    pos = _GRID_L // 2

            # --- Construire l'obs depuis l'état réel de l'env ---
            warn = (t % _T_WARN_PERIOD == 0)
            telegraph = pos if warn else None
            obs = _obs_bench(pos, telegraph)[None, :]    # (1, 14)

            # --- Forward ---
            preds, _ = m.forward(obs)

            # --- Action : round-robin pour couvrir toutes les colonnes de G ---
            move = int(t % _N_MOVES)

            # --- Capturer H_rec APRÈS forward (latent pré-rêve) ---
            cur_hrec = m.H_rec_batch[0, map_idx].copy()

            # --- Mesurer fidélité APRÈS warmup ---
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_delta = m.G_batch[0][:, map_idx][prev_move]    # colonne de l'action jouée t-1
                g_err, base_err = transition_error(prev_hrec, g_delta, cur_hrec)
                if base_err > _BASE_ERR_THRESH:
                    ratios.append(g_err / base_err)

            # --- Diagnostic mean|G[a]| pour l'action jouée ---
            g_col = m.G_batch[0][:, map_idx][move]
            action_abs_by_action[move].append(float(np.mean(np.abs(g_col))))

            # --- Apprentissage en ligne de g via policy_gradient ---
            reward = 0.1 if (strike_cell is None or pos != strike_cell) else -1.0
            m.compute_policy_gradient(
                np.array([reward], dtype=np.float32),
                [{"move": move, "grab": 0, "rub": 0}])

            # --- Appliquer le mouvement dans l'env ---
            new_pos = min(_GRID_L - 1, max(0, pos + (move - 1)))
            if warn:
                # Telegraph : danger frappe au prochain tick sur la pos ACTUELLE
                pending_danger = pos
            pos = new_pos

            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS = prev_bias
        MambaBatchModel.PLAN_A = prev_plan_a
        MambaBatchModel.PLAN_LR = prev_plan_lr
    return ratios, action_abs_by_action


def run_probe_env(seeds, warmup: int = 300, measure: int = 300) -> dict:
    """Agrège collect_ratios_env sur plusieurs seeds. Mesure CAUSALE (env réel)."""
    all_ratios = []
    action_abs_accum: dict = {a_idx: [] for a_idx in range(_N_MOVES)}
    for s in seeds:
        ratios, action_abs = collect_ratios_env(int(s), warmup, measure)
        all_ratios.extend(ratios)
        for a_idx in range(_N_MOVES):
            action_abs_accum[a_idx].extend(action_abs[a_idx])
    result = fidelity_verdict(all_ratios)
    result["mean_G_abs_by_action"] = {
        a_idx: float(np.mean(vals)) if vals else 0.0
        for a_idx, vals in action_abs_accum.items()
    }
    return result


def main():
    seeds = [int(s) for s in os.environ.get("GFP_SEEDS", "0,1,2,3,4,5,6,7").split(",") if s.strip()]
    warmup = int(os.environ.get("GFP_WARMUP", "300"))
    measure = int(os.environ.get("GFP_MEASURE", "300"))
    use_env = os.environ.get("GFP_ENV", "1").strip() not in ("0", "false", "False")

    if use_env:
        print(f"=== g-fidelity probe ENV (grille 1-D, action->obs couple) seeds={seeds} ===")
        out = run_probe_env(seeds, warmup, measure)
    else:
        print(f"=== g-fidelity probe SYNTHÉTIQUE seeds={seeds} ===")
        out = run_probe(seeds, warmup, measure)

    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    g_abs = out.get("mean_G_abs_by_action", {})
    if g_abs:
        vals_str = " ".join(f"G[{a}]={v:.4f}" for a, v in sorted(g_abs.items()))
        print(f"ACTION_DIVERSITY mean|G[a]|: {vals_str}")
    return out


if __name__ == "__main__":
    main()
