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


def _losses(out, targets):
    """(logits_a, v, p), (x, a_idx, v_t, p_t) -> (loss_action CE, loss_value MSE, loss_pred MSE)."""
    la = F.cross_entropy(out[0], targets[1])
    lv = F.mse_loss(out[1], targets[2])
    lp = F.mse_loss(out[2], targets[3])
    return la, lv, lp


def _eval_losses(model, held):
    model.eval()
    with torch.no_grad():
        la, lv, lp = _losses(model(held[0]), held)
    return {"action": float(la), "value": float(lv), "pred": float(lp)}


def _interference_cosine(model, batch):
    """FLAT seulement : cosinus moyen des gradients par tete w.r.t. les poids du trunc partage (<0 = conflit)."""
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


def _train_arm(arm, seed, teachers, steps=STEPS):
    """Entraine un bras ('flat'|'disjoint'), deterministe par seed. Retourne (eval_losses, interference|None)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    held = _make_data(HELDOUT, seed + 10_000, teachers)
    if arm == "flat":
        model = FlatModel()
        opt = torch.optim.Adam(model.parameters(), lr=LR)
        model.train()
        for t in range(steps):
            batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
            opt.zero_grad(set_to_none=True)
            la, lv, lp = _losses(model(batch[0]), batch)
            (la + lv + lp).backward()
            opt.step()
        interf = _interference_cosine(model, _make_data(BATCH, seed + 20_000, teachers))
        return _eval_losses(model, held), interf
    model = DisjointModel()
    opts = [torch.optim.Adam(g, lr=LR) for g in model.head_param_groups()]
    model.train()
    for t in range(steps):
        batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)
        for o in opts:
            o.zero_grad(set_to_none=True)
        ls = _losses(model(batch[0]), batch)
        for k in range(N_HEADS):
            ls[k].backward(retain_graph=(k < N_HEADS - 1))   # loss separee -> son sous-reseau seul
        for o in opts:
            o.step()
    return _eval_losses(model, held), None


def _verdict_disjoint(per_seed_improv):
    """HELPS/HURTS si >= majorite des seeds depassent +/-IMPROV_THRESH ; sinon NEUTRAL. GELE."""
    n = len(per_seed_improv)
    maj = n // 2 + 1
    helps = sum(1 for v in per_seed_improv if v >= IMPROV_THRESH)
    hurts = sum(1 for v in per_seed_improv if v <= -IMPROV_THRESH)
    if helps >= maj:
        return "DISJOINT_HELPS"
    if hurts >= maj:
        return "DISJOINT_HURTS"
    return "DISJOINT_NEUTRAL"


def _seed_improv(flat_losses, disj_losses):
    """Moyenne sur 3 tetes de (flat - disjoint) / flat (amelioration relative)."""
    ks = ("action", "value", "pred")
    return float(np.mean([(flat_losses[k] - disj_losses[k]) / max(flat_losses[k], 1e-12) for k in ks]))


def _report(rows, verdict, mean_improv, mean_interf):
    print("\n=== Banc A/B tetes disjointes vs plat (teacher-student) ===")
    print("  seed | headloss FLAT (a/v/p)      | DISJOINT (a/v/p)          | improv | interf")
    for r in rows:
        f, d = r["flat"], r["disj"]
        print("  %4d | %.3f %.3f %.3f | %.3f %.3f %.3f | %+.3f | %+.3f"
              % (r["seed"], f["action"], f["value"], f["pred"],
                 d["action"], d["value"], d["pred"], r["improv"], r["interf"]))
    print("  MOYEN improv=%+.3f  conflit-gradient FLAT (cos)=%+.3f" % (mean_improv, mean_interf))
    print("=== VERDICT ===")
    print("  -> %s (seuil improv >= %.2f, majorite ; interf<0 = interference)" % (verdict, IMPROV_THRESH))


def main_disjoint_heads(K=5, base=2200, steps=STEPS, _return=False):
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
        flat_losses, interf = _train_arm("flat", s, teachers, steps=steps)
        disj_losses, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat_losses, "disj": disj_losses,
                     "improv": _seed_improv(flat_losses, disj_losses), "interf": interf})
    improvs = [r["improv"] for r in rows]
    verdict = _verdict_disjoint(improvs)
    mean_improv = float(np.mean(improvs))
    mean_interf = float(np.mean([r["interf"] for r in rows]))
    _report(rows, verdict, mean_improv, mean_interf)
    res = {"verdict": verdict, "mean_improv": mean_improv, "mean_interference": mean_interf,
           "per_seed": rows, "trunk_params": (_trunk_params_count(FlatModel()), _trunk_params_count(DisjointModel()))}
    return res if _return else None


if __name__ == "__main__":
    main_disjoint_heads()
