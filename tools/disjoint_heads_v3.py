"""tools/disjoint_heads_v3.py — Bras FLAT + Adam-par-tete (EDR 154, V3).

EDR 153 : FLAT_NORM (plat + equilibrage d'echelle de loss, 1 Adam) recouvre 79% du gain DISJOINT ; residu ~21%
(tete pred) non recouvre. Ce bras teste l'AUTRE facteur non-architectural : les MOMENTS Adam SEPARES. FLAT_PERHEAD
= FlatModel (archi plate, trunc partage, meme init) mais 3 Adam (un par tete) sur TOUS les params, SANS echelle de
loss. Si les moments separes ferment le residu -> architecture refutee a ~100% comme levier. Reutilise la machinerie
d'EDR 152/153. Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_v3
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


def _train_flat_perhead(seed, teachers, steps=STEPS):
    """FLAT (archi plate, trunc partage, meme init au seed) + N_HEADS optimiseurs Adam (un par tete) sur TOUS les
    params. Isole les moments Adam separes SANS split architectural ni echelle de loss. Un forward par step, puis
    pour chaque tete k : zero_grad -> backward(ls[k], retain_graph si k<N_HEADS-1) -> step. Les gradients sont
    evalues au MEME point (forward unique + retain_graph), appliques en sequence, chacun avec les moments m/v
    propres de son Adam. Ordre des tetes fixe (action, value, pred)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    model = FlatModel()
    opts = [torch.optim.Adam(model.parameters(), lr=LR) for _ in range(N_HEADS)]
    model.train()
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        ls = _losses(model(batch[0]), batch)
        for k in range(N_HEADS):
            opts[k].zero_grad(set_to_none=True)
            ls[k].backward(retain_graph=(k < N_HEADS - 1))
            opts[k].step()
    return _eval_losses(model, held)


def _verdict_v3(per_seed_recovery):
    """OPTIMIZER_CONFIRMED si recovery>=0.90 majorite ; REFUTED si <=0.79 majorite ; sinon PARTIAL. GELE."""
    n = len(per_seed_recovery)
    maj = n // 2 + 1
    conf = sum(1 for r in per_seed_recovery if r >= 0.90)
    ref = sum(1 for r in per_seed_recovery if r <= 0.79)
    if conf >= maj:
        return "OPTIMIZER_CONFIRMED"
    if ref >= maj:
        return "REFUTED"
    return "PARTIAL"


def _report_v3(rows, verdict, mean_rec):
    print("\n=== Bras FLAT+Adam-par-tete (FLAT vs FLAT_PERHEAD vs DISJOINT, tetes MSE) ===")
    print("  seed | FLAT v/p     | FLAT_PH v/p   | DISJOINT v/p  | recovery | gain-152 v/p")
    for r in rows:
        f, ph, d = r["flat"], r["flatperhead"], r["disj"]
        print("  %4d | %.3f %.3f | %.3f %.3f | %.3f %.3f | %+.3f  | %.3f %.3f"
              % (r["seed"], f["value"], f["pred"], ph["value"], ph["pred"],
                 d["value"], d["pred"], r["recovery"],
                 f["value"] - d["value"], f["pred"] - d["pred"]))
    print("  MOYEN recovery=%+.3f" % mean_rec)
    print("=== VERDICT ===")
    print("  -> %s (recovery >= 0.90 majorite = OPTIMIZER_CONFIRMED ; <= 0.79 = REFUTED)" % verdict)


def main_v3_check(K=5, base=2200, steps=STEPS, _return=False):
    if torch is None:
        print("PyTorch indisponible -> banc saute.")
        res = {"verdict": "SKIPPED_NO_TORCH", "per_seed": []}
        return res if _return else None
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    torch.set_num_threads(1)
    teachers = _make_teachers()
    rows = []
    for i in range(K):
        s = base + i
        flat, _ = _train_arm("flat", s, teachers, steps=steps)
        flatperhead = _train_flat_perhead(s, teachers, steps=steps)
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat, "flatperhead": flatperhead, "disj": disj,
                     "recovery": _recovery(flat, flatperhead, disj)})
    recs = [r["recovery"] for r in rows]
    verdict = _verdict_v3(recs)
    mean_rec = float(np.mean(recs))
    _report_v3(rows, verdict, mean_rec)
    res = {"verdict": verdict, "mean_recovery": mean_rec, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_v3_check()
