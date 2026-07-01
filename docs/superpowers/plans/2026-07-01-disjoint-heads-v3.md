# EDR 154 (V3) — bras FLAT+Adam-par-tête : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bras `FLAT_PERHEAD` (archi plate, trunc partagé, 3 Adam à moments propres, sans équilibrage d'échelle) au banc têtes disjointes pour trancher si le résidu ~21 % d'EDR 153 est les moments Adam séparés (vs l'architecture).

**Architecture:** Nouveau fichier `tools/disjoint_heads_v3.py` qui réutilise par import toute la machinerie d'EDR 152 (`disjoint_heads_ab`) et le calcul de recouvrement d'EDR 153 (`disjoint_heads_confound._recovery`). Trois bras par seed : FLAT + DISJOINT (via `_train_arm` existant) et FLAT_PERHEAD (nouveau). Verdict pré-enregistré sur le recouvrement du gain DISJOINT.

**Tech Stack:** Python, PyTorch (proxy supervisé teacher-student auto-contenu, CPU, déterministe).

## Global Constraints

- **TOOLING ADDITIF** : créer SEULEMENT `tools/disjoint_heads_v3.py` et `tests/sandbox/test_disjoint_heads_v3.py`. NE modifier AUCUN autre fichier — ni `tools/disjoint_heads_ab.py`, ni `tools/disjoint_heads_confound.py`, ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : toute chaîne passée à `print()` est strictement ASCII (`->` en tirets OK, pas d'accent ni flèche unicode). Accents seulement dans les docstrings.
- **Déterminisme** : `main_v3_check` appelle `torch.set_num_threads(1)` et `torch.use_deterministic_algorithms(True)` (dans un try/except). Le run réel = 2 passes byte-identiques.
- **Équité 1-variable (Commandement 15)** : `_train_flat_perhead` partage avec `_train_arm`/`_train_flat_norm` l'ordre init `torch.manual_seed(seed)` puis `np.random.seed(seed)` puis `FlatModel()`, et les mêmes graines `held=_make_data(HELDOUT, seed+10_000, teachers)`, `batch=_make_data(BATCH, seed*1_000_003+t, teachers)`.
- **Verdict gelé** : seuils `OPTIMIZER_CONFIRMED` recovery≥0.90 majorité / `REFUTED` recovery≤0.79 majorité / sinon `PARTIAL`. Ne PAS ajuster après avoir vu des chiffres.

---

## Fichiers

- Créer : `tools/disjoint_heads_v3.py` (le bras + verdict + report + main).
- Créer : `tests/sandbox/test_disjoint_heads_v3.py` (unit verdict + smoke du bras + smoke main).

Imports disponibles (déjà exportés, vérifiés) :
- de `tools.disjoint_heads_ab` : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR`.
- de `tools.disjoint_heads_confound` : `_recovery(flat, mid, disj)` — moyenne sur têtes {value, pred} de `(flat[k]-mid[k])/(flat[k]-disj[k])`, garde `|denom|<1e-9`.

Rappels de types (EDR 152, ne PAS redéfinir) :
- `FlatModel()` : `nn.Module`, `forward(x) -> (logits_a, v, p)`.
- `_losses(out, batch) -> (la, lv, lp)` : tuple de 3 tensors scalaires (CE action, MSE value, MSE pred).
- `_eval_losses(model, held) -> dict` : `{"action": float, "value": float, "pred": float}`.
- `_train_arm(arm, seed, teachers, steps=STEPS) -> (eval_dict, interf_or_None)` : `arm in {"flat","disjoint"}`.
- `N_HEADS == 3`, ordre des têtes = (action=0, value=1, pred=2).

---

## Task 1 : bras FLAT_PERHEAD + verdict gelé

**Files:**
- Create: `tools/disjoint_heads_v3.py`
- Test: `tests/sandbox/test_disjoint_heads_v3.py`

**Interfaces:**
- Consumes : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, N_HEADS, HELDOUT, BATCH, STEPS, LR` (de `disjoint_heads_ab`) ; `_recovery` (de `disjoint_heads_confound`).
- Produces : `_train_flat_perhead(seed, teachers, steps=STEPS) -> dict` ; `_verdict_v3(per_seed_recovery) -> str`.

- [ ] **Step 1 : écrire les tests qui échouent**

Créer `tests/sandbox/test_disjoint_heads_v3.py` :

```python
import pytest

from tools.disjoint_heads_ab import torch, _make_teachers
from tools.disjoint_heads_v3 import _train_flat_perhead, _verdict_v3


def test_verdict_optimizer_confirmed():
    # 3/5 seeds >= 0.90 -> CONFIRMED (majorite = 3)
    assert _verdict_v3([0.95, 0.92, 0.91, 0.5, 0.4]) == "OPTIMIZER_CONFIRMED"


def test_verdict_refuted():
    # 3/5 seeds <= 0.79 -> REFUTED
    assert _verdict_v3([0.70, 0.60, 0.75, 0.95, 0.92]) == "REFUTED"


def test_verdict_partial():
    # ni majorite >=0.90 ni majorite <=0.79
    assert _verdict_v3([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_perhead_runs_and_returns_dict():
    # Critique : ce test attrape une eventuelle erreur autograd in-place
    # (forward unique + retain_graph + 3 step sequentiels sur trunc partage).
    teachers = _make_teachers()
    out = _train_flat_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert out[k] == out[k]  # not NaN
        assert out[k] >= 0.0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && python -m pytest tests/sandbox/test_disjoint_heads_v3.py -v`
Expected : FAIL (ImportError sur `tools.disjoint_heads_v3`).

- [ ] **Step 3 : implémenter le bras + verdict (créer le fichier, EXACTEMENT ce code)**

Créer `tools/disjoint_heads_v3.py` :

```python
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
```

- [ ] **Step 4 : lancer les tests, vérifier PASS**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && python -m pytest tests/sandbox/test_disjoint_heads_v3.py -v`
Expected : PASS (4 tests — 3 verdict + 1 smoke du bras). Le smoke lance 1 entraînement réduit (10 pas) → quelques secondes. **Si `test_flat_perhead_runs_and_returns_dict` lève une RuntimeError autograd « inplace operation »**, c'est un vrai blocage du mécanisme : rapporter BLOCKED (ne PAS masquer avec un `try/except`).

- [ ] **Step 5 : vérifier zéro modif fichiers existants**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && git status --short`
Expected : seuls `tools/disjoint_heads_v3.py` et `tests/sandbox/test_disjoint_heads_v3.py` apparaissent.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3"
git add tools/disjoint_heads_v3.py tests/sandbox/test_disjoint_heads_v3.py
git commit -m "feat(v3): bras FLAT+Adam-par-tete + verdict gele

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : report 3-bras + main_v3_check + smoke

**Files:**
- Modify: `tools/disjoint_heads_v3.py` (AJOUTER après `_verdict_v3`)
- Test: `tests/sandbox/test_disjoint_heads_v3.py` (AJOUTER à la fin)

**Interfaces:**
- Consumes : `_train_flat_perhead, _verdict_v3` (Task 1) ; `torch, _make_teachers, _train_arm, _recovery, STEPS` (déjà importés en tête).
- Produces : `_report_v3(rows, verdict, mean_rec) -> None` ; `main_v3_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None`.

- [ ] **Step 1 : ajouter le test smoke qui échoue**

Ajouter à la fin de `tests/sandbox/test_disjoint_heads_v3.py` :

```python
from tools.disjoint_heads_v3 import main_v3_check


def test_smoke_v3_returns_verdict():
    res = main_v3_check(K=1, base=99000, steps=30, _return=True)
    assert res["verdict"] in {"OPTIMIZER_CONFIRMED", "REFUTED", "PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && python -m pytest tests/sandbox/test_disjoint_heads_v3.py -k smoke_v3 -v`
Expected : FAIL (ImportError sur `main_v3_check`).

- [ ] **Step 3 : implémenter (AJOUTER après `_verdict_v3`, EXACTEMENT ce code)**

```python
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
```

- [ ] **Step 4 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && python -m pytest tests/sandbox/test_disjoint_heads_v3.py -v`
Expected : PASS (5 tests). Le smoke `main_v3_check` lance 3 entraînements réduits (K=1, 30 pas) → quelques secondes, laisse finir.

- [ ] **Step 5 : vérifier zéro modif fichiers existants + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3" && git status --short`
Expected : seuls les 2 fichiers du chantier touchés. Vérifier que les `print` de `_report_v3`/`main_v3_check` sont strictement ASCII.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-v3"
git add tools/disjoint_heads_v3.py tests/sandbox/test_disjoint_heads_v3.py
git commit -m "feat(v3): report 3-bras + main_v3_check + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 bras (FLAT/DISJOINT via `_train_arm`, FLAT_PERHEAD nouveau) → Task 1+2. §3 verdict gelé → `_verdict_v3` Task 1. §7 interfaces → `_train_flat_perhead`/`_verdict_v3` (T1), `_report_v3`/`main_v3_check` (T2). §6 périmètre additif + ASCII + déterminisme → Global Constraints + steps de vérif. Caveat forward-unique/retain_graph §5(a) → encodé dans le code (`retain_graph=(k<N_HEADS-1)`) + test smoke qui l'attrape. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; tout le code est complet et exécutable.

**3. Type consistency :** `_train_flat_perhead` retourne un eval dict `{action,value,pred}` (via `_eval_losses`) consommé par `_recovery` (clés value/pred) et `_report_v3` — cohérent. `main_v3_check` clé `"flatperhead"` cohérente entre `main` et `_report_v3`. Seuils `_verdict_v3` (0.90/0.79) cohérents spec §3.
