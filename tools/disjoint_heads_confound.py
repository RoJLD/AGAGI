"""tools/disjoint_heads_confound.py — Controle du confond Adam par-tete (EDR 153).

EDR 152 : les tetes disjointes battent le plat (+43%) MAIS sans interference (cos~0), gain MSE-only -> signature
du conditionnement Adam par-tete, pas de l'isolation architecturale. Ce controle teste si un fix CHEAP cote FLAT
(equilibrage d'echelle de loss, GradNorm-lite) recouvre le gain de DISJOINT. Si oui -> migration #5 refutee comme
levier. Reutilise la machinerie d'EDR 152 (tools/disjoint_heads_ab). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_confound
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


def _train_flat_norm(seed, teachers, steps=STEPS, decay=0.99):
    """FLAT (architecture plate, 1 Adam, meme init au seed) + losses ponderees par tete (GradNorm-lite EMA).
    Ne change QUE l'equilibrage d'echelle de loss. EMA sur pertes detachees -> deterministe."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    model = FlatModel()
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    model.train()
    ema = None
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        opt.zero_grad(set_to_none=True)
        ls = _losses(model(batch[0]), batch)
        det = np.array([float(ls[0]), float(ls[1]), float(ls[2])], dtype=np.float64)
        ema = det.copy() if ema is None else decay * ema + (1.0 - decay) * det
        w = 1.0 / (ema + 1e-8)
        w = w / w.sum() * N_HEADS
        loss = w[0] * ls[0] + w[1] * ls[1] + w[2] * ls[2]
        loss.backward()
        opt.step()
    return _eval_losses(model, held)


def _recovery(flat, flatnorm, disj):
    """Recouvrement moyen (tetes MSE value+pred) du gain DISJOINT par FLAT_NORM. Garde |denom|~0."""
    rec = []
    for k in ("value", "pred"):
        denom = flat[k] - disj[k]
        if abs(denom) < 1e-9:
            continue
        rec.append((flat[k] - flatnorm[k]) / denom)
    return float(np.mean(rec)) if rec else 0.0


def _verdict_confound(per_seed_recovery):
    """CONFIRMED si recovery>=0.50 majorite ; REFUTED si <=0.20 majorite ; sinon PARTIAL. GELE."""
    n = len(per_seed_recovery)
    maj = n // 2 + 1
    conf = sum(1 for r in per_seed_recovery if r >= 0.50)
    ref = sum(1 for r in per_seed_recovery if r <= 0.20)
    if conf >= maj:
        return "CONFOUND_CONFIRMED"
    if ref >= maj:
        return "CONFOUND_REFUTED"
    return "CONFOUND_PARTIAL"
