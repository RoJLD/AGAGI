"""tools/disjoint_heads_lr.py — Bras lr-par-tete (EDR 194).

EDR 192 : combiner echelle de loss + moments Adam par-tete ne ferme pas le residu (~0.70, redondant) car
« Adam par-tete annule le scaling » (Adam est ~invariant d'echelle : scaler la loss par c scale le gradient par c,
mais Adam divise par sqrt(v) ~ c -> pas inchange). Il reste UN bouton de credit qu'Adam ne normalise pas : le
learning rate (lr multiplie directement le pas d'Adam). Ce banc teste si un lr adaptatif par-tete
(lr_k proportionnel a 1/EMA(loss_k)) ferme le residu (-> desequilibre de PAS par-tete, archi refutee ~100%) ou
plafonne au niveau des leviers interchangeables ~0.7-0.79 (-> CE bouton de credit ne ferme pas le residu ; N'ETABLIT
PAS qu'il soit architectural — l'espace des mecanismes de credit non testes est non borne). Reutilise 152
(_train_arm, FlatModel) + 153 (_recovery). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_lr
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.disjoint_heads_ab import (
    torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm,
    N_HEADS, HELDOUT, BATCH, STEPS, LR,
)
from tools.disjoint_heads_confound import _recovery


def _norm_weights(ema, eps=1e-8):
    """Poids par-tete normalises a moyenne 1 : w_k proportionnel a 1/(EMA_k+eps), w.sum() == N_HEADS.
    Miroir de la normalisation d'EDR 153/192, extrait ici pour testabilite."""
    w = 1.0 / (np.asarray(ema, dtype=np.float64) + eps)
    return w / w.sum() * N_HEADS


def _train_flat_lr_perhead(seed, teachers, steps=STEPS, decay=0.99):
    """FLAT (archi plate, meme init au seed) + N_HEADS Adam (un par tete, moments propres). Au lieu de scaler la
    loss (192), on module le LEARNING RATE de chaque optimiseur par w_k = _norm_weights(EMA(loss)) — le seul bouton
    de credit qu'Adam ne normalise pas. Forward unique, puis par tete k : lr_k <- LR*w_k ; zero_grad ;
    ls[k].backward(retain_graph si k<N_HEADS-1) [loss BRUTE, non scalee] ; step."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    model = FlatModel()
    opts = [torch.optim.Adam(model.parameters(), lr=LR) for _ in range(N_HEADS)]
    model.train()
    ema = None
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        ls = _losses(model(batch[0]), batch)
        det = np.array([float(ls[0]), float(ls[1]), float(ls[2])], dtype=np.float64)
        ema = det.copy() if ema is None else decay * ema + (1.0 - decay) * det
        w = _norm_weights(ema)
        for k in range(N_HEADS):
            opts[k].param_groups[0]["lr"] = LR * float(w[k])
            opts[k].zero_grad(set_to_none=True)
            ls[k].backward(retain_graph=(k < N_HEADS - 1))
            opts[k].step()
    return _eval_losses(model, held)


def _verdict_lr(per_seed_recovery):
    """LR_CLOSES si recovery>=0.90 majorite ; LR_INTERCHANGEABLE si <=0.79 majorite ; sinon PARTIAL. GELE."""
    n = len(per_seed_recovery)
    maj = n // 2 + 1
    closes = sum(1 for r in per_seed_recovery if r >= 0.90)
    inter = sum(1 for r in per_seed_recovery if r <= 0.79)
    if closes >= maj:
        return "LR_CLOSES"
    if inter >= maj:
        return "LR_INTERCHANGEABLE"
    return "PARTIAL"


def _report_lr(rows, verdict, mean_rec):
    print("\n=== Bras lr-par-tete (FLAT vs FLAT_LR_PERHEAD vs DISJOINT, tetes MSE) ===")
    print("  seed | FLAT v/p     | FLAT_LR v/p   | DISJOINT v/p  | recovery")
    for r in rows:
        f, lr_, d = r["flat"], r["flatlrperhead"], r["disj"]
        print("  %4d | %.3f %.3f | %.3f %.3f | %.3f %.3f | %+.3f"
              % (r["seed"], f["value"], f["pred"], lr_["value"], lr_["pred"],
                 d["value"], d["pred"], r["recovery"]))
    print("  MOYEN recovery=%+.3f" % mean_rec)
    print("=== VERDICT ===")
    print("  -> %s (recovery >= 0.90 majorite = LR_CLOSES ; <= 0.79 = LR_INTERCHANGEABLE)" % verdict)


def main_lr_check(K=5, base=2200, steps=STEPS, _return=False):
    if torch is None:
        print("PyTorch indisponible -> banc saute.")
        res = {"verdict": "SKIPPED_NO_TORCH", "per_seed": []}
        return res if _return else None
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    torch.set_num_threads(1)   # garantit la double passe byte-identique (BLAS multi-thread = non-determinisme bit)
    teachers = _make_teachers()
    rows = []
    for i in range(K):
        s = base + i
        flat, _ = _train_arm("flat", s, teachers, steps=steps)
        flatlrperhead = _train_flat_lr_perhead(s, teachers, steps=steps)
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat, "flatlrperhead": flatlrperhead, "disj": disj,
                     "recovery": _recovery(flat, flatlrperhead, disj)})
    recs = [r["recovery"] for r in rows]
    verdict = _verdict_lr(recs)
    mean_rec = float(np.mean(recs))
    _report_lr(rows, verdict, mean_rec)
    res = {"verdict": verdict, "mean_recovery": mean_rec, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_lr_check()
