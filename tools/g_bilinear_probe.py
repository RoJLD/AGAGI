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

from tools.g_fidelity_probe import fidelity_verdict


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
