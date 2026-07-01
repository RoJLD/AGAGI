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


def _train_arm_h(arm, seed, teachers, H, steps=STEPS):
    """Entraine un bras ('flat'|'disjoint') a capacite H, deterministe par seed. Fidele a _train_arm (152).
    Retourne (eval_losses, interference|None)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    if arm == "flat":
        model = FlatModelH(H)
        opt = torch.optim.Adam(model.parameters(), lr=LR)
        model.train()
        for t in range(steps):
            batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
            opt.zero_grad(set_to_none=True)
            la, lv, lp = _losses(model(batch[0]), batch)
            (la + lv + lp).backward()
            opt.step()
        interf = _interference_cosine_h(model, _make_data(BATCH, seed + 20_000, teachers))
        return _eval_losses(model, held), interf
    model = DisjointModelH(H)
    opts = [torch.optim.Adam(g, lr=LR) for g in model.head_param_groups()]
    model.train()
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        for o in opts:
            o.zero_grad(set_to_none=True)
        ls = _losses(model(batch[0]), batch)
        for k in range(N_HEADS):
            ls[k].backward(retain_graph=(k < N_HEADS - 1))
        for o in opts:
            o.step()
    return _eval_losses(model, held), None


def _train_flat_norm_h(seed, teachers, H, steps=STEPS, decay=0.99):
    """FLAT_NORM a capacite H (plat + equilibrage d'echelle de loss GradNorm-lite, 1 Adam). Fidele a _train_flat_norm
    (153)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    model = FlatModelH(H)
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


def _report_capacity(h_rows):
    print("\n=== Sweep de capacite (FLAT vs DISJOINT vs FLAT_NORM par H, tetes MSE) ===")
    for hr in h_rows:
        print("  H=%2d | cos=%+.3f | improv=%+.3f | recovery=%+.3f"
              % (hr["H"], hr["mean_cos"], hr["mean_improv"], hr["mean_recovery"]))
        for r in hr["seeds"]:
            print("    seed %4d | cos %+.3f | improv %+.3f | recovery %+.3f | gain(FLAT-DISJ) v/p %.3f %.3f"
                  % (r["seed"], r["cos"], r["improv"], r["recovery"],
                     r["flat"]["value"] - r["disj"]["value"], r["flat"]["pred"] - r["disj"]["pred"]))
    print("=== VERDICT (mesure a H_min) ===")


def main_capacity_check(K=5, base=2200, Hs=(48, 6, 3), steps=STEPS, _return=False):
    if torch is None:
        print("PyTorch indisponible -> banc saute.")
        res = {"verdict": "SKIPPED_NO_TORCH", "per_H": []}
        return res if _return else None
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    torch.set_num_threads(1)
    teachers = _make_teachers()
    h_rows = []
    for H in Hs:
        seeds = []
        for i in range(K):
            s = base + i
            flat, cos = _train_arm_h("flat", s, teachers, H, steps=steps)
            disj, _ = _train_arm_h("disjoint", s, teachers, H, steps=steps)
            flatnorm = _train_flat_norm_h(s, teachers, H, steps=steps)
            seeds.append({"seed": s, "flat": flat, "disj": disj, "flatnorm": flatnorm,
                          "cos": cos, "improv": _seed_improv(flat, disj),
                          "recovery": _recovery(flat, flatnorm, disj)})
        h_rows.append({"H": H, "seeds": seeds,
                       "mean_cos": float(np.mean([r["cos"] for r in seeds])),
                       "mean_improv": float(np.mean([r["improv"] for r in seeds])),
                       "mean_recovery": float(np.mean([r["recovery"] for r in seeds]))})
    h_min = min(Hs)
    top = [hr for hr in h_rows if hr["H"] == h_min][0]
    verdict = _verdict_capacity([r["cos"] for r in top["seeds"]], [r["recovery"] for r in top["seeds"]])
    _report_capacity(h_rows)
    print("  -> %s (A: cos<=-0.05 majorite=INDUCED ; B: recovery>=0.50=CREDIT_ROBUST, <=0.20=ARCH_MATTERS)" % verdict)
    res = {"verdict": verdict, "per_H": h_rows, "h_min": h_min}
    return res if _return else None


if __name__ == "__main__":
    main_capacity_check()
