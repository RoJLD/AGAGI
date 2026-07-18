# EDR 192 (V4) — bras combiné échelle×moments : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bras `FLAT_NORM_PERHEAD` (plat + 3 Adam à moments propres ET échelle de loss EMA) au banc têtes disjointes pour trancher si la synergie des deux leviers non-architecturaux ferme le résidu ~21 % d'EDR 153/154 (→ archi réfutée à ~100 %) ou reste au niveau des leviers seuls (redondance).

**Architecture:** Nouveau fichier `tools/disjoint_heads_synergy.py` qui réutilise par import la machinerie d'EDR 152 (`disjoint_heads_ab`) et le calcul de recouvrement d'EDR 153 (`disjoint_heads_confound._recovery`). Trois bras par seed : FLAT + DISJOINT (via `_train_arm`) et FLAT_NORM_PERHEAD (nouveau, combine 153+154).

**Tech Stack:** Python, PyTorch (proxy supervisé teacher-student auto-contenu, CPU, déterministe), NumPy.

## Global Constraints

- **TOOLING ADDITIF** : créer SEULEMENT `tools/disjoint_heads_synergy.py` et `tests/sandbox/test_disjoint_heads_synergy.py`. NE modifier AUCUN autre fichier — ni `disjoint_heads_ab.py`, ni `disjoint_heads_confound.py`, ni `disjoint_heads_v3.py`, ni `disjoint_heads_correlated.py`, ni `disjoint_heads_capacity.py`, ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : toute chaîne passée à `print()` strictement ASCII (`->` en tirets OK, pas d'accent ni flèche unicode). Accents seulement dans les docstrings.
- **Déterminisme** : `main_v4_check` appelle `torch.set_num_threads(1)` et `torch.use_deterministic_algorithms(True)` (try/except). Run réel = 2 passes byte-identiques.
- **Imports minimaux (pas d'import mort)** : n'importer QUE ce qui est utilisé.
- **Équité 1-variable (Commandement 15)** : `_train_flat_norm_perhead` partage avec `_train_arm`/`_train_flat_norm` l'ordre init `torch.manual_seed(seed)` → `np.random.seed(seed)` → `FlatModel()`, et les graines `held=_make_data(HELDOUT, seed+10_000, teachers)`, `batch=_make_data(BATCH, seed*1_000_003+t, teachers)`.
- **Verdict gelé** : `SYNERGY_CLOSES` recovery≥0.90 majorité / `NO_SYNERGY` ≤0.79 majorité / sinon `PARTIAL`. Ne PAS ajuster après le run.

---

## Fichiers

- Créer : `tools/disjoint_heads_synergy.py`.
- Créer : `tests/sandbox/test_disjoint_heads_synergy.py`.

Imports disponibles (déjà exportés, vérifiés dans le code de 152/153) :
- de `tools.disjoint_heads_ab` : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR`.
- de `tools.disjoint_heads_confound` : `_recovery`.
- `numpy as np`.

Rappels de types (152/153, ne PAS redéfinir) :
- `FlatModel()` : `nn.Module`, `forward(x) -> (logits_a, v, p)`.
- `_losses(out, batch) -> (la, lv, lp)` : tuple de 3 tensors scalaires (CE, MSE, MSE).
- `_eval_losses(model, held) -> dict` : `{"action","value","pred"}` (floats).
- `_train_arm(arm, seed, teachers, steps=STEPS) -> (eval_dict, interf_or_None)` (`arm in {"flat","disjoint"}`).
- `_recovery(flat, mid, disj) -> float` (moyenne value+pred de `(flat−mid)/(flat−disj)`, garde `|denom|<1e-9`).
- `N_HEADS == 3` (ordre têtes action=0, value=1, pred=2).

---

## Task 1 : bras combiné FLAT_NORM_PERHEAD + verdict gelé

**Files:**
- Create: `tools/disjoint_heads_synergy.py`
- Test: `tests/sandbox/test_disjoint_heads_synergy.py`

**Interfaces:**
- Consumes : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, N_HEADS, HELDOUT, BATCH, STEPS, LR` (de `disjoint_heads_ab`) ; `_recovery` (de `disjoint_heads_confound`) ; `numpy as np`.
- Produces : `_train_flat_norm_perhead(seed, teachers, steps=STEPS, decay=0.99) -> dict` ; `_verdict_v4(per_seed_recovery) -> str`.

- [ ] **Step 1 : écrire les tests qui échouent**

Créer `tests/sandbox/test_disjoint_heads_synergy.py` :

```python
import pytest

from tools.disjoint_heads_ab import torch, _make_teachers
from tools.disjoint_heads_synergy import _train_flat_norm_perhead, _verdict_v4


def test_verdict_synergy_closes():
    # 3/5 seeds >= 0.90 -> SYNERGY_CLOSES
    assert _verdict_v4([0.95, 0.92, 0.91, 0.5, 0.4]) == "SYNERGY_CLOSES"


def test_verdict_no_synergy():
    # 3/5 seeds <= 0.79 -> NO_SYNERGY
    assert _verdict_v4([0.70, 0.60, 0.75, 0.95, 0.92]) == "NO_SYNERGY"


def test_verdict_partial():
    assert _verdict_v4([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_norm_perhead_runs_and_returns_dict():
    # Attrape une eventuelle RuntimeError autograd in-place (forward unique + retain_graph + 3 step sequentiels).
    teachers = _make_teachers()
    out = _train_flat_norm_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert out[k] == out[k]  # not NaN
        assert out[k] >= 0.0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && python -m pytest tests/sandbox/test_disjoint_heads_synergy.py -v`
Expected : FAIL (ImportError sur `tools.disjoint_heads_synergy`).

- [ ] **Step 3 : implémenter (créer le fichier, EXACTEMENT ce code)**

Créer `tools/disjoint_heads_synergy.py` :

```python
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
```

- [ ] **Step 4 : lancer les tests, vérifier PASS**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && python -m pytest tests/sandbox/test_disjoint_heads_synergy.py -v`
Expected : PASS (4 tests — 3 verdict + 1 smoke du bras). Le smoke lance 1 entraînement réduit (10 pas). **Si `test_flat_norm_perhead_runs_and_returns_dict` lève une RuntimeError autograd « inplace operation »**, rapporter BLOCKED (ne PAS masquer avec un try/except).

- [ ] **Step 5 : vérifier zéro modif fichiers existants**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && git status --short`
Expected : seuls `tools/disjoint_heads_synergy.py` et `tests/sandbox/test_disjoint_heads_synergy.py`.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy"
git add tools/disjoint_heads_synergy.py tests/sandbox/test_disjoint_heads_synergy.py
git commit -m "feat(synergy): bras FLAT_NORM_PERHEAD (echelle x moments) + verdict gele

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : report 3-bras + main_v4_check + smoke

**Files:**
- Modify: `tools/disjoint_heads_synergy.py` (AJOUTER après `_verdict_v4`)
- Test: `tests/sandbox/test_disjoint_heads_synergy.py` (AJOUTER à la fin)

**Interfaces:**
- Consumes : `_train_flat_norm_perhead, _verdict_v4` (Task 1) ; `torch, _make_teachers, _train_arm, _recovery, STEPS, np` (déjà importés en tête).
- Produces : `_report_v4(rows, verdict, mean_rec) -> None` ; `main_v4_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None` retournant `{verdict, mean_recovery, per_seed}` (ou `{verdict:"SKIPPED_NO_TORCH", per_seed:[]}`).

- [ ] **Step 1 : ajouter le test smoke qui échoue**

Ajouter à la fin de `tests/sandbox/test_disjoint_heads_synergy.py` :

```python
from tools.disjoint_heads_synergy import main_v4_check


def test_smoke_v4_returns_verdict():
    res = main_v4_check(K=1, base=99000, steps=30, _return=True)
    assert res["verdict"] in {"SYNERGY_CLOSES", "NO_SYNERGY", "PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && python -m pytest tests/sandbox/test_disjoint_heads_synergy.py -k smoke_v4 -v`
Expected : FAIL (ImportError sur `main_v4_check`).

- [ ] **Step 3 : implémenter (AJOUTER après `_verdict_v4`, EXACTEMENT ce code)**

```python
def _report_v4(rows, verdict, mean_rec):
    print("\n=== Bras combine echelle x moments (FLAT vs FLAT_NORM_PERHEAD vs DISJOINT, tetes MSE) ===")
    print("  seed | FLAT v/p     | FLAT_NP v/p   | DISJOINT v/p  | recovery | gain-152 v/p")
    for r in rows:
        f, np_, d = r["flat"], r["flatnormperhead"], r["disj"]
        print("  %4d | %.3f %.3f | %.3f %.3f | %.3f %.3f | %+.3f  | %.3f %.3f"
              % (r["seed"], f["value"], f["pred"], np_["value"], np_["pred"],
                 d["value"], d["pred"], r["recovery"],
                 f["value"] - d["value"], f["pred"] - d["pred"]))
    print("  MOYEN recovery=%+.3f" % mean_rec)
    print("=== VERDICT ===")
    print("  -> %s (recovery >= 0.90 majorite = SYNERGY_CLOSES ; <= 0.79 = NO_SYNERGY)" % verdict)


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
        flatnormperhead = _train_flat_norm_perhead(s, teachers, steps=steps)
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat, "flatnormperhead": flatnormperhead, "disj": disj,
                     "recovery": _recovery(flat, flatnormperhead, disj)})
    recs = [r["recovery"] for r in rows]
    verdict = _verdict_v4(recs)
    mean_rec = float(np.mean(recs))
    _report_v4(rows, verdict, mean_rec)
    res = {"verdict": verdict, "mean_recovery": mean_rec, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_v4_check()
```

- [ ] **Step 4 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && python -m pytest tests/sandbox/test_disjoint_heads_synergy.py -v`
Expected : PASS (5 tests). Le smoke `main_v4_check` lance 3 entraînements réduits (K=1, 30 pas) → quelques secondes.

- [ ] **Step 5 : vérifier zéro modif fichiers existants + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy" && git status --short`
Expected : seuls les 2 fichiers du chantier. Vérifier que les `print` de `_report_v4`/`main_v4_check` sont strictement ASCII.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-synergy"
git add tools/disjoint_heads_synergy.py tests/sandbox/test_disjoint_heads_synergy.py
git commit -m "feat(synergy): report 3-bras + main_v4_check + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 bras (FLAT/DISJOINT via `_train_arm`, FLAT_NORM_PERHEAD nouveau) → Task 1+2. §3 verdict gelé → `_verdict_v4` Task 1. §8 interfaces → `_train_flat_norm_perhead`/`_verdict_v4` (T1), `_report_v4`/`main_v4_check` (T2). §7 périmètre additif + ASCII + déterminisme → Global Constraints + steps de vérif. Caveat forward-unique/retain_graph §5(b) → encodé (`retain_graph=(k<N_HEADS-1)`) + test smoke qui l'attrape. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; tout le code complet et exécutable.

**3. Type consistency :** `_train_flat_norm_perhead` renvoie un eval dict `{action,value,pred}` (via `_eval_losses`) consommé par `_recovery` (value/pred) et `_report_v4`. Clé `"flatnormperhead"` cohérente entre `main_v4_check` et `_report_v4`. Seuils `_verdict_v4` (0.90/0.79) cohérents spec §3. `float(w[k])` évite un tensor-scalaire mixte dans le scaling.
