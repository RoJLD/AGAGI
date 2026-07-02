"""tools/g_bilinear_probe.py — Sonde de fidelite d'un g BILINEAIRE (EDR 193, extension d'EDR 135).

EDR 135 : le g LINEAIRE du modele (delta constant par action, independant de H) est NEUTRE sur obs riches. Dernier
levier G4 non teste = un g BILINEAIRE (etat-dependant) : ΔH = H . W_a (une matrice par action). Le modele n'apprenant
qu'un g lineaire, on fitte le bilineaire OFFLINE par ridge sur les vraies transitions latentes d'un rollout env-grille
(a trajectoire FIXE) et on compare les fidelites a la baseline 'pas de changement' + au g lineaire appris (reference
135). Auto-contenu (numpy pur pour le fit ; MambaAgent en import read-only), ne modifie rien.

Usage : python -m tools.g_bilinear_probe
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.g_fidelity_probe import (
    fidelity_verdict, MambaAgent, MambaBatchModel, _obs_bench, _GRID_L, _N_MOVES, _T_WARN_PERIOD, _OBS_DIM,
)


def _split_temporal(triples, n_moves, frac=0.7):
    """Split TEMPOREL par action : les premiers frac% des triplets d'une action = train, le reste = test.
    Preserve l'ordre (generalisation temporelle, pas memorisation)."""
    train, test = [], []
    for mv in range(n_moves):
        grp = [tr for tr in triples if tr["move"] == mv]
        k = int(len(grp) * frac)
        train.extend(grp[:k])
        test.extend(grp[k:])
    return train, test


def _fit_linear_offline(train, n_moves, N):
    """Delta CONSTANT par action : c_a = moyenne des (H_next - H_prev) du train pour l'action a. Controle 'lineaire
    re-estime offline'. Renvoie dict move -> vecteur (N,)."""
    out = {}
    for mv in range(n_moves):
        deltas = [np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                  for tr in train if tr["move"] == mv]
        out[mv] = np.mean(deltas, axis=0) if deltas else np.zeros(N, dtype=np.float64)
    return out


def _fit_bilinear(train, n_moves, N, lam):
    """g BILINEAIRE par ridge, une matrice W_a (N,N) par action. Convention LIGNE : ΔH_pred = H_prev @ W_a.
    W_a = solve(X^T X + lam*I, X^T ΔY), X=(m,N) empilement H_prev train, ΔY=(m,N) empilement (H_next-H_prev) train."""
    out = {}
    eye = np.eye(N, dtype=np.float64)
    for mv in range(n_moves):
        grp = [tr for tr in train if tr["move"] == mv]
        if len(grp) < 2:
            out[mv] = np.zeros((N, N), dtype=np.float64)
            continue
        X = np.stack([np.asarray(tr["H_prev"], dtype=np.float64) for tr in grp])
        DY = np.stack([np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                       for tr in grp])
        A = X.T @ X + lam * eye
        B = X.T @ DY
        out[mv] = np.linalg.solve(A, B)
    return out


def _ratios_for_predictor(test, predictor_fn, base_thresh=1e-4):
    """ratio = pred_err/base_err par triplet test (filtre base_err > base_thresh). predictor_fn(tr) -> ΔH_pred (N,)."""
    ratios = []
    for tr in test:
        H_prev = np.asarray(tr["H_prev"], dtype=np.float64)
        H_next = np.asarray(tr["H_next"], dtype=np.float64)
        delta_pred = np.asarray(predictor_fn(tr), dtype=np.float64)
        pred_err = float(np.mean((H_prev + delta_pred - H_next) ** 2))
        base_err = float(np.mean((H_prev - H_next) ** 2))
        if base_err > base_thresh:
            ratios.append(pred_err / base_err)
    return ratios


def _verdict_bilinear(ratios_bilin, ratios_learned):
    """GELE. BILINEAR_FIDELE si fidelity_verdict(bilin)=G_FIDELE ET median(bilin)<median(learned) ;
    BILINEAR_NEUTRAL si verdict bilin in {NEUTRE, G_INUTILE} ; sinon PARTIAL."""
    vb = fidelity_verdict(ratios_bilin)
    vl = fidelity_verdict(ratios_learned)
    if vb["verdict"] == "G_FIDELE" and vb["median_ratio"] < vl["median_ratio"]:
        return "BILINEAR_FIDELE"
    if vb["verdict"] in ("NEUTRE", "G_INUTILE"):
        return "BILINEAR_NEUTRAL"
    return "PARTIAL"


def _collect_transitions_env(seed, warmup, measure):
    """Rollout env-grille 1-D deterministe (miroir de collect_ratios_env, EDR 135). Capture les triplets latents
    (H_prev, move, H_next, g_learned) apres warmup. g_learned = colonne g LINEAIRE apprise par le modele (reference).
    Restaure les flags PLAN_* en finally."""
    np.random.seed(seed)
    a = MambaAgent(num_inputs=_OBS_DIM, num_outputs=108, num_nodes=172)
    a.genome.organ_genes = np.array([True, False])
    prev_bias, prev_plan_a, prev_plan_lr = (MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_A = _N_MOVES
    MambaBatchModel.PLAN_LR = 0.1
    triples = []
    try:
        m = MambaBatchModel([a])
        map_idx = m.mappings[0]
        pos = _GRID_L // 2
        pending_danger = None
        prev_hrec = None
        prev_move = None
        for t in range(warmup + measure):
            strike_cell = pending_danger
            pending_danger = None
            if strike_cell is not None and pos == strike_cell:
                pos = _GRID_L // 2
            warn = (t % _T_WARN_PERIOD == 0)
            telegraph = pos if warn else None
            obs = _obs_bench(pos, telegraph)[None, :]
            m.forward(obs)
            move = int(t % _N_MOVES)
            cur_hrec = m.H_rec_batch[0, map_idx].copy()
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_learned = m.G_batch[0][:, map_idx][prev_move].copy()
                triples.append({"H_prev": np.asarray(prev_hrec, dtype=np.float64),
                                "move": int(prev_move),
                                "H_next": np.asarray(cur_hrec, dtype=np.float64),
                                "g_learned": np.asarray(g_learned, dtype=np.float64)})
            reward = 0.1 if (strike_cell is None or pos != strike_cell) else -1.0
            m.compute_policy_gradient(np.array([reward], dtype=np.float32),
                                      [{"move": move, "grab": 0, "rub": 0}])
            new_pos = min(_GRID_L - 1, max(0, pos + (move - 1)))
            if warn:
                pending_danger = pos
            pos = new_pos
            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR = prev_bias, prev_plan_a, prev_plan_lr
    return triples


def _median(ratios):
    return float(fidelity_verdict(ratios)["median_ratio"])


def main_bilinear_check(seeds=(0, 1, 2, 3, 4, 5, 6, 7), warmup=300, measure=600, lam=1.0, _return=False):
    all_bilin, all_learned, all_linoff = [], [], []
    for s in seeds:
        triples = _collect_transitions_env(int(s), warmup, measure)
        if not triples:
            continue
        N = len(triples[0]["H_prev"])
        train, test = _split_temporal(triples, _N_MOVES, 0.7)
        if not train or not test:
            continue
        W = _fit_bilinear(train, _N_MOVES, N, lam)
        C = _fit_linear_offline(train, _N_MOVES, N)
        all_bilin.extend(_ratios_for_predictor(test, lambda tr: tr["H_prev"] @ W[tr["move"]]))
        all_learned.extend(_ratios_for_predictor(test, lambda tr: tr["g_learned"]))
        all_linoff.extend(_ratios_for_predictor(test, lambda tr: C[tr["move"]]))
    if not all_bilin:
        print("Aucune transition collectee -> NO_DATA.")
        res = {"verdict": "NO_DATA", "median_bilin": 1.0, "median_learned": 1.0, "median_linoff": 1.0, "n": 0}
        return res if _return else None
    verdict = _verdict_bilinear(all_bilin, all_learned)
    mb, ml, mo = _median(all_bilin), _median(all_learned), _median(all_linoff)
    print("\n=== g bilineaire vs lineaire (env-grille, ratios test-set) ===")
    print("  median ratio (pred_err/base_err) : bilin=%.3f  learned-lin=%.3f  offline-lin=%.3f  (n=%d)"
          % (mb, ml, mo, len(all_bilin)))
    print("=== VERDICT ===")
    print("  -> %s (FIDELE si bilin G_FIDELE ET bilin<learned ; NEUTRAL si bilin ratio>=0.95)" % verdict)
    res = {"verdict": verdict, "median_bilin": mb, "median_learned": ml, "median_linoff": mo, "n": len(all_bilin)}
    return res if _return else None


if __name__ == "__main__":
    main_bilinear_check()
