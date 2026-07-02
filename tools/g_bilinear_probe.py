"""tools/g_bilinear_probe.py — g-fidelite decomposee FULL vs CACHES (EDR 193, re-examine EDR 135).

EDR 135 : g LINEAIRE du modele = delta constant par action. Sur env-grille (obs riches causal) il est G_FIDELE
(median ~0.75), PAS neutre (le neutre = mode synthetique). Mais la position est un one-hot dans les noeuds d'ENTREE,
pos_t = clip(pos_{t-1}+move-1) = decalage deterministe par action -> une fidelite FULL peut n'etre QUE ce re-encodage,
sans anticipation latente. On decompose : ratio sur dims PLEINES (172) vs dims CACHEES [n_in, N-n_out) = [14,64). Si la
fidelite s'effondre sur les caches -> artefact d'encodage (corrige EDR 135). Sinon on demande si le bilineaire (fit
offline par ridge) capte le latent cache mieux que le lineaire. Auto-contenu (numpy pur ; MambaAgent read-only).

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
    """Split TEMPOREL par action : premiers frac% train, reste test. Preserve l'ordre."""
    train, test = [], []
    for mv in range(n_moves):
        grp = [tr for tr in triples if tr["move"] == mv]
        k = int(len(grp) * frac)
        train.extend(grp[:k])
        test.extend(grp[k:])
    return train, test


def _fit_linear_offline(train, n_moves, N):
    """Delta CONSTANT par action : c_a = moyenne train de (H_next - H_prev). Renvoie dict move -> (N,)."""
    out = {}
    for mv in range(n_moves):
        deltas = [np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                  for tr in train if tr["move"] == mv]
        out[mv] = np.mean(deltas, axis=0) if deltas else np.zeros(N, dtype=np.float64)
    return out


def _fit_bilinear(train, n_moves, N, lam):
    """g BILINEAIRE par ridge, W_a (N,N) par action. Convention LIGNE : ΔH_pred = H_prev @ W_a.
    W_a = solve(X^T X + lam*I, X^T ΔY), X=(m,N) H_prev train, ΔY=(m,N) (H_next-H_prev) train."""
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


def _ratios_for_predictor(test, predictor_fn, idx=None, base_thresh=1e-4):
    """ratio = pred_err/base_err par triplet test (filtre base_err > base_thresh). predictor_fn(tr) -> ΔH_pred (N,).
    idx=None -> dims pleines ; idx (array) -> erreur restreinte a ces dims (controle FULL vs CACHES)."""
    ratios = []
    for tr in test:
        H_prev = np.asarray(tr["H_prev"], dtype=np.float64)
        H_next = np.asarray(tr["H_next"], dtype=np.float64)
        delta_pred = np.asarray(predictor_fn(tr), dtype=np.float64)
        resid = H_prev + delta_pred - H_next
        base = H_prev - H_next
        if idx is not None:
            resid = resid[idx]
            base = base[idx]
        pred_err = float(np.mean(resid ** 2))
        base_err = float(np.mean(base ** 2))
        if base_err > base_thresh:
            ratios.append(pred_err / base_err)
    return ratios


def _hidden_idx(N, n_in, n_out):
    """Indices des noeuds CACHES [n_in, N - n_out) (hors blocs one-hot entree/sortie ; cf. mamba_agent map_idx)."""
    return np.arange(n_in, N - n_out)


def _verdict_decomposition(learned_full, bilin_full, learned_hidden, bilin_hidden):
    """GELE (spec S6). Decompose FULL vs HIDDEN pour learned + bilin.
    ENCODING_ARTIFACT : FULL fidele (les 2) MAIS HIDDEN non-fidele (les 2, median>=0.95) -> corrige EDR 135.
    LATENT_BILINEAR : bilin-HIDDEN fidele ET median(bilin-hidden) < median(learned-hidden).
    LATENT_LINEAR : learned-HIDDEN fidele ET bilin ne bat pas. Sinon PARTIAL."""
    lf, bf = fidelity_verdict(learned_full), fidelity_verdict(bilin_full)
    lh, bh = fidelity_verdict(learned_hidden), fidelity_verdict(bilin_hidden)
    full_fidele = (lf["verdict"] == "G_FIDELE" and bf["verdict"] == "G_FIDELE")
    hidden_dead = (lh["verdict"] != "G_FIDELE" and bh["verdict"] != "G_FIDELE"
                   and lh["median_ratio"] >= 0.95 and bh["median_ratio"] >= 0.95)
    if full_fidele and hidden_dead:
        return "ENCODING_ARTIFACT"
    if bh["verdict"] == "G_FIDELE" and bh["median_ratio"] < lh["median_ratio"]:
        return "LATENT_BILINEAR"
    if lh["verdict"] == "G_FIDELE" and bh["median_ratio"] >= lh["median_ratio"]:
        return "LATENT_LINEAR"
    return "PARTIAL"


def _collect_transitions_env(seed, warmup, measure):
    """Rollout env-grille 1-D deterministe (miroir de collect_ratios_env, EDR 135). Capture les triplets latents
    (H_prev, move, H_next, g_learned) apres warmup. g_learned = colonne g LINEAIRE apprise (reference EDR 135).
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


def main_bilinear_check(seeds=(0, 1, 2, 3, 4, 5, 6, 7), warmup=300, measure=600, lam=1.0,
                        n_in=_OBS_DIM, n_out=108, _return=False):
    lf, bf, lh, bh = [], [], [], []
    for s in seeds:
        triples = _collect_transitions_env(int(s), warmup, measure)
        if not triples:
            continue
        N = len(triples[0]["H_prev"])
        hid = _hidden_idx(N, n_in, n_out)
        train, test = _split_temporal(triples, _N_MOVES, 0.7)
        if not train or not test:
            continue
        W = _fit_bilinear(train, _N_MOVES, N, lam)
        learned_fn = lambda tr: tr["g_learned"]
        bilin_fn = lambda tr: tr["H_prev"] @ W[tr["move"]]
        lf.extend(_ratios_for_predictor(test, learned_fn))
        bf.extend(_ratios_for_predictor(test, bilin_fn))
        lh.extend(_ratios_for_predictor(test, learned_fn, idx=hid))
        bh.extend(_ratios_for_predictor(test, bilin_fn, idx=hid))
    if not lf:
        print("Aucune transition collectee -> NO_DATA.")
        res = {"verdict": "NO_DATA", "med_learned_full": 1.0, "med_bilin_full": 1.0,
               "med_learned_hidden": 1.0, "med_bilin_hidden": 1.0, "n": 0}
        return res if _return else None
    verdict = _verdict_decomposition(lf, bf, lh, bh)
    mlf, mbf, mlh, mbh = _median(lf), _median(bf), _median(lh), _median(bh)
    print("\n=== g-fidelite decomposee FULL vs CACHES (env-grille, ratios test-set) ===")
    print("  FULL   : learned-lin=%.3f  bilin=%.3f" % (mlf, mbf))
    print("  HIDDEN : learned-lin=%.3f  bilin=%.3f  (n=%d)" % (mlh, mbh, len(lh)))
    print("=== VERDICT ===")
    print("  -> %s (ARTIFACT si FULL fidele mais HIDDEN neutre ; LATENT_BILINEAR si bilin-hidden fidele et < learned)"
          % verdict)
    res = {"verdict": verdict, "med_learned_full": mlf, "med_bilin_full": mbf,
           "med_learned_hidden": mlh, "med_bilin_hidden": mbh, "n": len(lh)}
    return res if _return else None


if __name__ == "__main__":
    main_bilinear_check()
