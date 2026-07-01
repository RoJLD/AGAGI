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
