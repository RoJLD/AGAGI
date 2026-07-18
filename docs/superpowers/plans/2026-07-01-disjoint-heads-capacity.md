# EDR 191 — sweep de capacité (H réduit) : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un sweep de capacité (H réduit) qui réimplémente FLAT/DISJOINT/FLAT_NORM paramétrés par H (fidèles à 152/153), pour tester si sous un trunc RARE la vraie interférence émerge (cosinus<0) et si le crédit-équilibrage plat recouvre encore l'avantage DISJOINT ou si l'architecture compte enfin.

**Architecture:** Nouveau fichier `tools/disjoint_heads_capacity.py`. Comme `disjoint_heads_ab` (152) fige H=48, on réimplémente localement `FlatModelH(H)`/`DisjointModelH(H)` (ordre de couches IDENTIQUE à 152 → à H=48 init byte-identique), 3 bras d'entraînement paramétrés par H et un cosinus d'interférence, TOUS fidèles au code revu de 152/153. Réutilise par import ce qui est H-indépendant (`_make_teachers` indépendants, `_losses`, `_eval_losses`, `_make_data`, `_seed_improv`, `_recovery`, constantes).

**Tech Stack:** Python, PyTorch (proxy supervisé teacher-student auto-contenu, CPU, déterministe), NumPy.

## Global Constraints

- **TOOLING ADDITIF** : créer SEULEMENT `tools/disjoint_heads_capacity.py` et `tests/sandbox/test_disjoint_heads_capacity.py`. NE modifier AUCUN autre fichier — ni `disjoint_heads_ab.py`, ni `disjoint_heads_confound.py`, ni `disjoint_heads_correlated.py`, ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : toute chaîne passée à `print()` strictement ASCII (`->` en tirets OK, pas d'accent ni flèche unicode). Accents seulement dans les docstrings.
- **Déterminisme** : `main_capacity_check` appelle `torch.set_num_threads(1)` et `torch.use_deterministic_algorithms(True)` (try/except). Run réel = 2 passes byte-identiques.
- **Imports minimaux (pas d'import mort)** : n'importer QUE ce qui est utilisé.
- **Fidélité à 152/153** : `FlatModelH`/`DisjointModelH` définissent les couches dans le MÊME ordre que `FlatModel`/`DisjointModel` (152) ; `_train_arm_h`/`_train_flat_norm_h` gardent le MÊME ordre d'init (`torch.manual_seed(seed)` → `np.random.seed(seed)` → `held=_make_data(HELDOUT, seed+10_000)` → model) et les MÊMES graines (`batch=_make_data(BATCH, seed*1_000_003+t)`, interf `_make_data(BATCH, seed+20_000)`) → à H=48 tout reproduit 152/153.
- **H divisible par N_HEADS(=3)** ; parité de params trunc FLAT (`D·H+H`) = DISJOINT (`3·(D·(H/3)+H/3)`).
- **Verdict gelé** : Axe A `INDUCED` si `cos ≤ −0.05` majorité ; Axe B `CREDIT_ROBUST` recovery≥0.50 / `ARCH_MATTERS` ≤0.20 / `CREDIT_PARTIAL`. Ne PAS ajuster après le run.

---

## Fichiers

- Créer : `tools/disjoint_heads_capacity.py`.
- Créer : `tests/sandbox/test_disjoint_heads_capacity.py`.

Imports disponibles (vérifiés dans le code de 152/153) :
- de `tools.disjoint_heads_ab` : `torch, _make_teachers, _make_data, _losses, _eval_losses, _seed_improv, D, K_A, P_PRED, N_HEADS, HELDOUT, BATCH, STEPS, LR`.
- de `tools.disjoint_heads_confound` : `_recovery`.
- `numpy as np`.
- Dans le TEST seulement : `FlatModel, DisjointModel` de `tools.disjoint_heads_ab` (pour la parité d'init à H=48).

Rappels de types (152/153, ne PAS redéfinir) :
- `_make_teachers(seed=777) -> dict` (profs INDÉPENDANTS `{"action":(w1,w2),...}`).
- `_make_data(n, seed, teachers) -> (x, a_idx, v_t, p_t)` (tenseurs torch).
- `_losses(out, targets) -> (la, lv, lp)` (CE, MSE, MSE).
- `_eval_losses(model, held) -> {"action","value","pred"}` (floats).
- `_seed_improv(flat_eval, disj_eval) -> float` ; `_recovery(flat, mid, disj) -> float`.
- Constantes : `D==32, K_A==4, P_PRED==8, N_HEADS==3, HELDOUT==512, BATCH==64, STEPS==2000, LR==1e-3`.

---

## Task 1 : modèles paramétrés par H + cosinus + verdict gelé

**Files:**
- Create: `tools/disjoint_heads_capacity.py`
- Test: `tests/sandbox/test_disjoint_heads_capacity.py`

**Interfaces:**
- Consumes : `torch, _losses, D, K_A, P_PRED, N_HEADS` (de `disjoint_heads_ab`) ; `numpy as np`.
- Produces : `FlatModelH(H)`, `DisjointModelH(H)`, `_interference_cosine_h(model, batch) -> float`, `_verdict_capacity(cos_list, recovery_list) -> str`.

- [ ] **Step 1 : écrire les tests qui échouent**

Créer `tests/sandbox/test_disjoint_heads_capacity.py` :

```python
import pytest

from tools.disjoint_heads_ab import torch, D, K_A, P_PRED, _make_teachers, _make_data
from tools.disjoint_heads_capacity import _verdict_capacity


def test_verdict_induced_credit_robust():
    assert _verdict_capacity([-0.1, -0.1, -0.2, 0.0, -0.3], [0.8, 0.7, 0.9, 0.6, 0.85]) == "INDUCED+CREDIT_ROBUST"


def test_verdict_induced_arch_matters():
    assert _verdict_capacity([-0.2, -0.15, -0.3, -0.1, -0.25], [0.1, 0.15, 0.05, 0.2, 0.1]) == "INDUCED+ARCH_MATTERS"


def test_verdict_not_induced():
    assert _verdict_capacity([0.0, 0.01, -0.02, 0.03, 0.0], [0.9, 0.8, 0.85, 0.7, 0.9]) == "NOT_INDUCED+CREDIT_ROBUST"


def test_verdict_induced_partial():
    assert _verdict_capacity([-0.2, -0.15, -0.3, -0.1, -0.25], [0.35, 0.4, 0.3, 0.45, 0.38]) == "INDUCED+CREDIT_PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_trunk_parity_at_h6():
    from tools.disjoint_heads_capacity import FlatModelH, DisjointModelH
    flat = FlatModelH(6)
    disj = DisjointModelH(6)
    flat_trunk = sum(p.numel() for p in flat.trunk.parameters())
    disj_trunk = sum(p.numel() for t in (disj.trunk_action, disj.trunk_value, disj.trunk_pred) for p in t.parameters())
    assert flat_trunk == disj_trunk  # D*H+H == 3*(D*(H/3)+H/3)


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flatmodelh48_reproduces_flatmodel_init():
    from tools.disjoint_heads_ab import FlatModel
    from tools.disjoint_heads_capacity import FlatModelH
    torch.manual_seed(0)
    ref = FlatModel()
    torch.manual_seed(0)
    got = FlatModelH(48)
    assert torch.allclose(ref.trunk.weight, got.trunk.weight)
    assert torch.allclose(ref.head_action.weight, got.head_action.weight)
    assert torch.allclose(ref.head_value.weight, got.head_value.weight)
    assert torch.allclose(ref.head_pred.weight, got.head_pred.weight)


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_interference_cosine_h_runs():
    from tools.disjoint_heads_capacity import FlatModelH, _interference_cosine_h
    teachers = _make_teachers()
    batch = _make_data(16, 123, teachers)
    c = _interference_cosine_h(FlatModelH(6), batch)
    assert isinstance(c, float) and c == c  # not NaN
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && python -m pytest tests/sandbox/test_disjoint_heads_capacity.py -v`
Expected : FAIL (ImportError sur `tools.disjoint_heads_capacity`).

- [ ] **Step 3 : implémenter (créer le fichier, EXACTEMENT ce code)**

Créer `tools/disjoint_heads_capacity.py` :

```python
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
```

- [ ] **Step 4 : lancer les tests, vérifier PASS**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && python -m pytest tests/sandbox/test_disjoint_heads_capacity.py -v`
Expected : PASS (7 tests — 4 verdict + parité trunc H=6 + init H=48 reproduit + cosinus tourne). `test_flatmodelh48_reproduces_flatmodel_init` est le sanity clé (fidélité de la réimplémentation).

- [ ] **Step 5 : vérifier zéro modif fichiers existants**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && git status --short`
Expected : seuls `tools/disjoint_heads_capacity.py` et `tests/sandbox/test_disjoint_heads_capacity.py`.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity"
git add tools/disjoint_heads_capacity.py tests/sandbox/test_disjoint_heads_capacity.py
git commit -m "feat(capacity): modeles parametres par H + cosinus + verdict gele

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : bras d'entraînement H + report + main_capacity_check (sweep) + smoke

**Files:**
- Modify: `tools/disjoint_heads_capacity.py` (AJOUTER après `_verdict_capacity`)
- Test: `tests/sandbox/test_disjoint_heads_capacity.py` (AJOUTER à la fin)

**Interfaces:**
- Consumes : `FlatModelH, DisjointModelH, _interference_cosine_h, _verdict_capacity` (Task 1) ; `torch, _make_teachers, _make_data, _losses, _eval_losses, _seed_improv, _recovery, HELDOUT, BATCH, STEPS, LR, N_HEADS, np` (déjà importés en tête).
- Produces : `_train_arm_h(arm, seed, teachers, H, steps=STEPS) -> (eval_dict, cos_or_None)` ; `_train_flat_norm_h(seed, teachers, H, steps=STEPS) -> eval_dict` ; `_report_capacity(h_rows) -> None` ; `main_capacity_check(K=5, base=2200, Hs=(48,6,3), steps=STEPS, _return=False) -> dict|None` (`{verdict, per_H, h_min}` ou `{verdict:"SKIPPED_NO_TORCH", per_H:[]}`).

- [ ] **Step 1 : ajouter le test smoke qui échoue**

Ajouter à la fin de `tests/sandbox/test_disjoint_heads_capacity.py` :

```python
from tools.disjoint_heads_capacity import main_capacity_check


def test_smoke_capacity_returns_verdict():
    res = main_capacity_check(K=1, base=99000, Hs=(48, 3), steps=25, _return=True)
    assert res["verdict"] == "SKIPPED_NO_TORCH" or "+" in res["verdict"]
    assert "per_H" in res
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && python -m pytest tests/sandbox/test_disjoint_heads_capacity.py -k smoke -v`
Expected : FAIL (ImportError sur `main_capacity_check`).

- [ ] **Step 3 : implémenter (AJOUTER après `_verdict_capacity`, EXACTEMENT ce code)**

```python
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
```

- [ ] **Step 4 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && python -m pytest tests/sandbox/test_disjoint_heads_capacity.py -v`
Expected : PASS (8 tests). Le smoke lance 2 H × 1 seed × 3 bras × 25 pas → quelques secondes, laisse finir.

- [ ] **Step 5 : vérifier zéro modif fichiers existants + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity" && git status --short`
Expected : seuls les 2 fichiers du chantier. Vérifier que les `print` de `_report_capacity`/`main_capacity_check` sont strictement ASCII.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-capacity"
git add tools/disjoint_heads_capacity.py tests/sandbox/test_disjoint_heads_capacity.py
git commit -m "feat(capacity): bras H + report + main_capacity_check (sweep) + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 modèles H-param (`FlatModelH`/`DisjointModelH`, ordre couches identique 152) → Task 1 ; cosinus → Task 1. §2 bras (`_train_arm_h`/`_train_flat_norm_h`) → Task 2. §3 sweep → `main_capacity_check` Task 2. §4 verdict gelé → `_verdict_capacity` Task 1. §8 interfaces → T1 (models/cos/verdict) + T2 (arms/report/main). §6(c) sanity H=48 → `test_flatmodelh48_reproduces_flatmodel_init` (T1) + run réel. §7 additif/ASCII/déterminisme → Global Constraints + steps de vérif. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; code complet et exécutable.

**3. Type consistency :** `_train_arm_h`/`_train_flat_norm_h` renvoient un eval dict `{action,value,pred}` consommé par `_recovery`/`_seed_improv`/`_report_capacity`. Clés de row (`flat/disj/flatnorm/cos/improv/recovery`) cohérentes main↔report ; clés de H-row (`H/seeds/mean_cos/mean_improv/mean_recovery`) cohérentes. `_verdict_capacity(cos_list, recovery_list)` seuils (−0.05 / 0.50 / 0.20) cohérents spec §4. `head_param_groups` renvoie 3 groupes `[trunk_k+head_k]` cohérent avec `_train_arm_h` disjoint.
