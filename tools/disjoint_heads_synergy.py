"""tools/disjoint_heads_synergy.py — Bras combine echelle x moments (EDR 192, V4).

EDR 153 : echelle de loss seule recouvre 0.79 du gain DISJOINT. EDR 154 : moments Adam par-tete seuls recouvrent 0.73.
Aucun ne ferme seul le residu ~21%. V4 teste la SYNERGIE : un bras FLAT_NORM_PERHEAD (plat + 3 Adam a moments propres
ET echelle de loss EMA) ferme-t-il le residu (-> archi refutee a ~100%) ou reste-t-il au niveau des leviers seuls
(redondance : Adam par-tete normalise deja par-tete) ? Reutilise 152 (_train_arm) + 153 (_recovery). Auto-contenu
PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_synergy
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


def _train_flat_norm_perhead(seed, teachers, steps=STEPS, decay=0.99):
    """FLAT (archi plate, meme init au seed) + N_HEADS Adam (un par tete, moments propres) ET echelle de loss EMA
    (GradNorm-lite, w_k=1/EMA(loss_k)). Combine STRICTEMENT les deux leviers non-archi (153 echelle + 154 moments).
    Forward unique, puis par tete k : zero_grad -> (w_k*ls_k).backward(retain_graph si k<N_HEADS-1) -> step. Chaque
    Adam a ses moments m/v propres ; l'echelle w_k rescale la loss de la tete k."""
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
        w = 1.0 / (ema + 1e-8)
        w = w / w.sum() * N_HEADS
        for k in range(N_HEADS):
            opts[k].zero_grad(set_to_none=True)
            (float(w[k]) * ls[k]).backward(retain_graph=(k < N_HEADS - 1))
            opts[k].step()
    return _eval_losses(model, held)


def _verdict_v4(per_seed_recovery):
    """SYNERGY_CLOSES si recovery>=0.90 majorite ; NO_SYNERGY si <=0.79 majorite ; sinon PARTIAL. GELE."""
    n = len(per_seed_recovery)
    maj = n // 2 + 1
    closes = sum(1 for r in per_seed_recovery if r >= 0.90)
    no_syn = sum(1 for r in per_seed_recovery if r <= 0.79)
    if closes >= maj:
        return "SYNERGY_CLOSES"
    if no_syn >= maj:
        return "NO_SYNERGY"
    return "PARTIAL"
