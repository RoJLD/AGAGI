"""tools/disjoint_heads_ab.py — Banc A/B tetes disjointes vs plat (EDR 152).

Teste l'hypothese #5 de l'audit : l'isolation de gradient (tetes disjointes + losses separees) aide-t-elle
l'apprentissage multi-facultes vs le substrat PLAT a trunc partage (une loss combinee) ? Proxy SUPERVISE
teacher-student (le RL confondrait par la variance de credit ; cf. mem_nas EDR 064). Auto-contenu PyTorch
(ni Biosphere ni src/ ; ne touche pas le fil torch //). Usage : python -m tools.disjoint_heads_ab
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except Exception:
    torch = None

# --- hyperparametres FIXES (A/B propre, dims figees) ---
D = 32
H = 48
N_HEADS = 3
K_A = 4
P_PRED = 8
TEACHER_SEED = 777
BATCH = 64
HELDOUT = 512
STEPS = 2000
LR = 1e-3
IMPROV_THRESH = 0.10


def _make_teachers(seed=TEACHER_SEED):
    """3 profs FIXES (MLP 2 couches tanh), independants du seed d'entrainement (numpy, cibles reproductibles)."""
    rng = np.random.default_rng(seed)

    def mlp(out):
        w1 = (rng.standard_normal((D, 16)) / np.sqrt(D)).astype(np.float32)
        w2 = (rng.standard_normal((16, out)) / np.sqrt(16)).astype(np.float32)
        return (w1, w2)

    return {"action": mlp(K_A), "value": mlp(1), "pred": mlp(P_PRED)}


def _teacher_forward(x, wpair):
    w1, w2 = wpair
    return np.tanh(x @ w1) @ w2


def _targets(x, teachers):
    a = _teacher_forward(x, teachers["action"])
    v = _teacher_forward(x, teachers["value"])
    p = _teacher_forward(x, teachers["pred"])
    return np.argmax(a, axis=1).astype(np.int64), v.astype(np.float32), p.astype(np.float32)


def _make_data(n, seed, teachers):
    """Retourne (x, action_idx, value, pred) en tenseurs torch, deterministe par seed."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, D)).astype(np.float32)
    a, v, p = _targets(x, teachers)
    return (torch.from_numpy(x), torch.from_numpy(a), torch.from_numpy(v), torch.from_numpy(p))


if torch is not None:

    class FlatModel(nn.Module):
        """Trunc D->H partage + 3 tetes lisant tout H. Une loss combinee (couplage inter-tetes)."""

        def __init__(self):
            super().__init__()
            self.trunk = nn.Linear(D, H)
            self.head_action = nn.Linear(H, K_A)
            self.head_value = nn.Linear(H, 1)
            self.head_pred = nn.Linear(H, P_PRED)

        def forward(self, x):
            h = torch.tanh(self.trunk(x))
            return self.head_action(h), self.head_value(h), self.head_pred(h)

    class DisjointModel(nn.Module):
        """3 sous-reseaux INDEPENDANTS D->(H//N_HEADS)->tete. Losses/optimiseurs separes (isolation gradient)."""

        def __init__(self):
            super().__init__()
            w = H // N_HEADS
            self.trunk_action = nn.Linear(D, w)
            self.trunk_value = nn.Linear(D, w)
            self.trunk_pred = nn.Linear(D, w)
            self.head_action = nn.Linear(w, K_A)
            self.head_value = nn.Linear(w, 1)
            self.head_pred = nn.Linear(w, P_PRED)

        def forward(self, x):
            a = self.head_action(torch.tanh(self.trunk_action(x)))
            v = self.head_value(torch.tanh(self.trunk_value(x)))
            p = self.head_pred(torch.tanh(self.trunk_pred(x)))
            return a, v, p

        def head_param_groups(self):
            return [
                list(self.trunk_action.parameters()) + list(self.head_action.parameters()),
                list(self.trunk_value.parameters()) + list(self.head_value.parameters()),
                list(self.trunk_pred.parameters()) + list(self.head_pred.parameters()),
            ]


def _trunk_params_count(model):
    """Params du/des trunc(s) seulement (parite attendue D*H+H entre les 2 bras)."""
    if isinstance(model, FlatModel):
        return sum(pp.numel() for pp in model.trunk.parameters())
    return sum(pp.numel() for t in (model.trunk_action, model.trunk_value, model.trunk_pred)
               for pp in t.parameters())
