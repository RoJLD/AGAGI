"""tools/disjoint_heads_v4.py — Bras FLAT + lr-PAR-TETE (T2/M1, ferme le caveat EDR 154).

EDR 152 : DISJOINT bat le PLAT (+43%) sans interference (cos~0) -> gain = conditionnement d'optim par-tete.
EDR 153 : FLAT_NORM (echelle de loss GradNorm-lite, 1 Adam) recouvre 79%. EDR 154 : FLAT_PERHEAD (moments Adam
separes, meme lr) recouvre 73%. **lr-par-tete N'A PAS ete teste** (le caveat 154). Ce banc l'isole ET compare
les TROIS knobs d'equilibrage cote-a-cote (meme archi/init/donnees par seed) :

  FLAT_NORM      (153) : echelle de loss ponderee   -> equilibre AUSSI le trunc partage
  FLAT_PERHEAD   (154) : N Adam, moments separes, meme lr
  FLAT_PERHEAD_LR (M1) : 1 Adam a GROUPES, lr propre PAR READOUT (GradNorm-lite), trunc au lr de base,
                         moments UNIQUES, loss combinee NON ponderee -> isole 'lr-par-tete'

Question : lr-par-tete recouvre-t-il comme les deux autres (~0.75) -> « tout knob d'equilibrage de credit
recouvre, robustement crediT-pas-archi » ? Reutilise entierement la machinerie d'EDR 152-154. Auto-contenu
PyTorch, ne modifie rien (git diff src/ VIDE). Usage : python -m tools.disjoint_heads_v4
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
from tools.disjoint_heads_confound import _train_flat_norm, _recovery
from tools.disjoint_heads_v3 import _train_flat_perhead


def _train_flat_perhead_lr(seed, teachers, steps=STEPS, decay=0.99):
    """FLAT (archi plate, meme init au seed) + 1 Adam a GROUPES de params : chaque tete-readout a un lr
    PROPRE equilibre GradNorm-lite (lr_k = LR/ema_k normalise), le trunc partage reste au lr de base LR.
    Moments UNIQUES (chaque param dans un seul groupe), loss combinee NON ponderee. Isole 'lr-par-tete' :
    distinct de FLAT_NORM (echelle de loss, 153) et FLAT_PERHEAD (moments separes, 154).

    NB : l'equilibrage n'agit que sur les readouts (le trunc partage garde LR) -> teste si equilibrer les
    tetes de lecture SUFFIT (vs 153 qui equilibre aussi le gradient du trunc via l'echelle de loss)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    model = FlatModel()
    heads = [model.head_action, model.head_value, model.head_pred]      # ordre = action, value, pred
    groups = [{"params": list(model.trunk.parameters()), "lr": LR}]     # groupe 0 = trunc (lr de base)
    for hd in heads:
        groups.append({"params": list(hd.parameters()), "lr": LR})      # groupes 1..3 = readouts
    opt = torch.optim.Adam(groups)
    model.train()
    ema = None
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        opt.zero_grad(set_to_none=True)
        ls = _losses(model(batch[0]), batch)
        det = np.array([float(ls[0]), float(ls[1]), float(ls[2])], dtype=np.float64)
        ema = det.copy() if ema is None else decay * ema + (1.0 - decay) * det
        w = 1.0 / (ema + 1e-8)
        w = w / w.sum() * N_HEADS                                        # meme formule que FLAT_NORM (153)
        for k in range(N_HEADS):
            opt.param_groups[k + 1]["lr"] = LR * float(w[k])            # lr propre par readout ; trunc inchange
        (ls[0] + ls[1] + ls[2]).backward()
        opt.step()
    return _eval_losses(model, held)


def _verdict_v4(lr_recs):
    """Le knob lr-par-tete rejoint-il la famille d'equilibrage de credit ? Meme grille que le confond (153) :
    LR_RECOVERS si recovery>=0.50 majorite ; LR_INSUFFICIENT si <=0.20 majorite ; sinon LR_PARTIAL. GELE."""
    n = len(lr_recs)
    maj = n // 2 + 1
    conf = sum(1 for r in lr_recs if r >= 0.50)
    ref = sum(1 for r in lr_recs if r <= 0.20)
    if conf >= maj:
        return "LR_RECOVERS"
    if ref >= maj:
        return "LR_INSUFFICIENT"
    return "LR_PARTIAL"


def _report_v4(rows, verdict, means):
    print("\n=== T2/M1 : 3 knobs d'equilibrage de credit (recovery du gain DISJOINT, tetes MSE value+pred) ===")
    print("  seed | rec(echelle 153) | rec(moments 154) | rec(lr-par-tete M1)")
    for r in rows:
        print("  %4d |      %+.3f      |      %+.3f      |       %+.3f" %
              (r["seed"], r["rec_norm"], r["rec_perhead"], r["rec_lr"]))
    print("  MOYEN|      %+.3f      |      %+.3f      |       %+.3f" %
          (means["norm"], means["perhead"], means["lr"]))
    print("=== VERDICT (lr-par-tete) ===")
    print("  -> %s (recovery >= 0.50 majorite = LR_RECOVERS = rejoint la famille credit-pas-archi)" % verdict)


def main_v4_check(K=5, base=2200, steps=STEPS, _return=False):
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
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        norm = _train_flat_norm(s, teachers, steps=steps)
        perhead = _train_flat_perhead(s, teachers, steps=steps)
        lr = _train_flat_perhead_lr(s, teachers, steps=steps)
        rows.append({"seed": s,
                     "rec_norm": _recovery(flat, norm, disj),
                     "rec_perhead": _recovery(flat, perhead, disj),
                     "rec_lr": _recovery(flat, lr, disj)})
    means = {"norm": float(np.mean([r["rec_norm"] for r in rows])),
             "perhead": float(np.mean([r["rec_perhead"] for r in rows])),
             "lr": float(np.mean([r["rec_lr"] for r in rows]))}
    verdict = _verdict_v4([r["rec_lr"] for r in rows])
    _report_v4(rows, verdict, means)
    res = {"verdict": verdict, "means": means, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_v4_check()
