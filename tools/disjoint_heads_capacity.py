"""tools/disjoint_heads_capacity.py — Sweep de capacite (H reduit) sous pression, EDR 191.

EDR 152 : disjoint aide, cos~0 (pas d'interference). EDR 153/154 : le credit-equilibrage plat recouvre ~75% -> credit
pas archi. EDR 190 : correler les profs n'induit PAS de conflit (readout absorbe le signe ; trunc H=48 surdimensionne).
Le regime interferent n'a jamais ete atteint. V3 : reduire H (uniforme -> PRESERVE la parite inter-bras) cree une
PRESSION DE CAPACITE ; sous un trunc RARE le plat NE PEUT PAS servir toutes les tetes -> vraie interference. On teste
si, quand la rarete force le conflit (cos<0), le credit plat (FLAT_NORM, 153) recouvre encore l'avantage DISJOINT
(-> 153/154 robuste) ou si l'architecture compte enfin (-> conclusion bornee au regime sur-capacite). Profs
INDEPENDANTS (152 ; 190 a montre que correler AIDE, donc pour induire le conflit sous rarete il faut des taches
DIVERSES). disjoint_heads_ab fige H=48 -> modeles/bras reimplementes PARAMETRES par H, fideles a 152/153 (a H=48 tout
reproduit). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_capacity
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.disjoint_heads_ab import (
    torch, _make_teachers, _make_data, _losses, _eval_losses, _seed_improv,
    D, K_A, P_PRED, N_HEADS, HELDOUT, BATCH, STEPS, LR,
)
from tools.disjoint_heads_confound import _recovery

COS_INDUCED = -0.05   # seuil axe A (gele)


if torch is not None:

    class FlatModelH(torch.nn.Module):
        """Trunc D->H partage + 3 tetes lisant tout H, PARAMETRE par H. Ordre des couches IDENTIQUE a FlatModel (152)
        -> a H=48 l'init est byte-identique."""

        def __init__(self, H):
            super().__init__()
            self.trunk = torch.nn.Linear(D, H)
            self.head_action = torch.nn.Linear(H, K_A)
            self.head_value = torch.nn.Linear(H, 1)
            self.head_pred = torch.nn.Linear(H, P_PRED)

        def forward(self, x):
            h = torch.tanh(self.trunk(x))
            return self.head_action(h), self.head_value(h), self.head_pred(h)

    class DisjointModelH(torch.nn.Module):
        """3 sous-reseaux D->(H//N_HEADS)->tete, PARAMETRE par H. Ordre IDENTIQUE a DisjointModel (152)."""

        def __init__(self, H):
            super().__init__()
            w = H // N_HEADS
            self.trunk_action = torch.nn.Linear(D, w)
            self.trunk_value = torch.nn.Linear(D, w)
            self.trunk_pred = torch.nn.Linear(D, w)
            self.head_action = torch.nn.Linear(w, K_A)
            self.head_value = torch.nn.Linear(w, 1)
            self.head_pred = torch.nn.Linear(w, P_PRED)

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


def _interference_cosine_h(model, batch):
    """FLAT (FlatModelH) : cosinus moyen des gradients par tete w.r.t. trunk.weight (<0 = conflit). Fidele a 152."""
    grads = []
    for k in range(N_HEADS):
        model.zero_grad(set_to_none=True)
        losses = _losses(model(batch[0]), batch)
        losses[k].backward()
        grads.append(model.trunk.weight.grad.detach().reshape(-1).clone())
    cos = []
    for i in range(N_HEADS):
        for j in range(i + 1, N_HEADS):
            denom = (grads[i].norm() * grads[j].norm()).clamp_min(1e-12)
            cos.append(float((grads[i] @ grads[j]) / denom))
    model.zero_grad(set_to_none=True)
    return float(np.mean(cos))


def _verdict_capacity(cos_list, recovery_list):
    """Verdict combine 2 axes a H_min. GELE.
    Axe A : INDUCED si cos<=COS_INDUCED majorite, sinon NOT_INDUCED.
    Axe B : CREDIT_ROBUST recovery>=0.50 majorite / ARCH_MATTERS <=0.20 majorite / sinon CREDIT_PARTIAL."""
    n = len(cos_list)
    maj = n // 2 + 1
    axis_a = "INDUCED" if sum(1 for c in cos_list if c <= COS_INDUCED) >= maj else "NOT_INDUCED"
    robust = sum(1 for r in recovery_list if r >= 0.50)
    arch = sum(1 for r in recovery_list if r <= 0.20)
    if robust >= maj:
        axis_b = "CREDIT_ROBUST"
    elif arch >= maj:
        axis_b = "ARCH_MATTERS"
    else:
        axis_b = "CREDIT_PARTIAL"
    return axis_a + "+" + axis_b
