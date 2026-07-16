# EDR 194 — Bras lr-par-tête (disjoint_heads) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un banc `tools/disjoint_heads_lr.py` qui teste si un lr adaptatif par-tête (le seul bouton de crédit qu'Adam n'annule pas) ferme le résidu de recouvrement de l'arc têtes disjointes.

**Architecture:** Un seul fichier tool strictement additif, calqué sur `tools/disjoint_heads_synergy.py` (EDR 192). Il importe read-only la machinerie figée de 152 (`disjoint_heads_ab`) et 153 (`disjoint_heads_confound._recovery`). Le cœur `_train_flat_lr_perhead` est un clone de `_train_flat_norm_perhead` (192) à UNE ligne près : on module le `lr` de chaque Adam par-tête (au lieu de la loss). Verdict pré-enregistré gelé.

**Tech Stack:** Python, PyTorch (auto-contenu, proxy teacher-student supervisé), pytest. numpy pour la normalisation des poids.

## Global Constraints

- **Additif strict** : créer UNIQUEMENT `tools/disjoint_heads_lr.py` et `tests/sandbox/test_disjoint_heads_lr.py`. Ne modifier AUCUN fichier existant. Aucun import de `src/`. Ne pas toucher le fil torch // (`torch_batch_model.py`, `backend_torch.py`, `substrate_*`) ni famine/Lewis.
- **Réutilisation par import read-only** : `from tools.disjoint_heads_ab import (torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR)` et `from tools.disjoint_heads_confound import _recovery`. Ne pas re-définir ces symboles.
- **Une seule différence vs 192** : `_train_flat_lr_perhead` doit être IDENTIQUE à `_train_flat_norm_perhead` (192) SAUF que la loss n'est PAS scalée (`ls[k].backward(...)` brute) et le lr est modulé : `opts[k].param_groups[0]["lr"] = LR * float(w[k])` avant `opts[k].step()`.
- **Verdict GELÉ** (ne pas changer les seuils) : `LR_CLOSES` si recovery ≥ 0.90 majorité ; `LR_INTERCHANGEABLE` si recovery ≤ 0.79 majorité ; sinon `PARTIAL`. Majorité = `n // 2 + 1`.
- **Déterminisme** : `main_lr_check` fait `torch.use_deterministic_algorithms(True)` (try/except) et `torch.set_num_threads(1)`. Garde `SKIPPED_NO_TORCH` si `torch is None`.
- **Hyperparamètres figés** hérités de 152 : NE PAS re-définir `D H N_HEADS K_A P_PRED STEPS LR BATCH HELDOUT`. Run scientifique : `K=5, base=2200, steps=2000`.
- **Path-scopé** (tree partagé) : commits `git add -- <chemins exacts>`, jamais `git add -A`.
- **Sécurité autograd** : le motif `forward unique → per-tête {zero_grad ; ls[k].backward(retain_graph=k<N_HEADS-1) ; step}` est sûr (prouvé en 192, merged) — Adam ne met à jour que les leaf params du chemin de chaque tête (grads des autres têtes = None → `step` les saute), et le backward ne relit jamais la *valeur* des params modifiés (seulement les activations/entrées sauvegardées). Moduler le lr au lieu de la loss ne change pas le graphe. Le test 3 garde contre une éventuelle RuntimeError in-place.

---

## File Structure

- `tools/disjoint_heads_lr.py` — le banc : header/imports, `_norm_weights`, `_train_flat_lr_perhead`, `_verdict_lr`, `_report_lr`, `main_lr_check`, bloc `__main__`.
- `tests/sandbox/test_disjoint_heads_lr.py` — 6 tests TDD (verdict ×3, `_norm_weights`, train-arm fini, diffère-de-192, déterminisme, smoke).

Deux tâches : **Task 1** = machinerie unitairement testable (`_norm_weights` + `_train_flat_lr_perhead` + `_verdict_lr`) ; **Task 2** = `main_lr_check` + rapport + déterminisme + smoke.

---

### Task 1: Machinerie cœur (poids, bras lr-par-tête, verdict)

**Files:**
- Create: `tools/disjoint_heads_lr.py`
- Test: `tests/sandbox/test_disjoint_heads_lr.py`

**Interfaces:**
- Consumes (import read-only) : `tools.disjoint_heads_ab.{torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR}` ; `tools.disjoint_heads_confound._recovery` ; `tools.disjoint_heads_synergy._train_flat_norm_perhead` (test 4 seulement).
- Produces (pour Task 2 et les tests) :
  - `_norm_weights(ema, eps=1e-8) -> np.ndarray` (longueur `N_HEADS`, `sum == N_HEADS`, `mean == 1`).
  - `_train_flat_lr_perhead(seed, teachers, steps=STEPS, decay=0.99) -> dict{"action","value","pred": float}`.
  - `_verdict_lr(per_seed_recovery: list[float]) -> str ∈ {"LR_CLOSES","LR_INTERCHANGEABLE","PARTIAL"}`.

- [ ] **Step 1: Écrire les tests qui échouent (machinerie cœur)**

Créer `tests/sandbox/test_disjoint_heads_lr.py` :

```python
import numpy as np
import pytest

from tools.disjoint_heads_ab import torch, _make_teachers, N_HEADS
from tools.disjoint_heads_lr import _norm_weights, _train_flat_lr_perhead, _verdict_lr


def test_verdict_lr_closes():
    # 3/5 seeds >= 0.90 -> LR_CLOSES
    assert _verdict_lr([0.95, 0.92, 0.91, 0.5, 0.4]) == "LR_CLOSES"


def test_verdict_lr_interchangeable():
    # 3/5 seeds <= 0.79 -> LR_INTERCHANGEABLE
    assert _verdict_lr([0.70, 0.60, 0.75, 0.95, 0.92]) == "LR_INTERCHANGEABLE"


def test_verdict_lr_partial():
    # ni majorite >=0.90 ni majorite <=0.79 -> PARTIAL
    assert _verdict_lr([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


def test_norm_weights_mean_one():
    w = _norm_weights(np.array([0.1, 2.0, 0.5]))
    assert w.shape == (N_HEADS,)
    assert abs(float(w.sum()) - N_HEADS) < 1e-9   # -> mean(w) == 1
    # plus la loss (EMA) est basse, plus le poids est haut
    assert w[0] > w[2] > w[1]


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_lr_perhead_runs_and_returns_dict():
    # Garde contre une RuntimeError autograd in-place (forward unique + retain_graph + 3 step).
    teachers = _make_teachers()
    out = _train_flat_lr_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert np.isfinite(out[k])
        assert out[k] >= 0.0


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_lr_perhead_differs_from_loss_scaling():
    # Coeur de l'hypothese : moduler le lr != moduler la loss sous Adam par-tete.
    from tools.disjoint_heads_synergy import _train_flat_norm_perhead
    teachers = _make_teachers()
    lr_out = _train_flat_lr_perhead(2200, teachers, steps=50)
    syn_out = _train_flat_norm_perhead(2200, teachers, steps=50)
    assert (abs(lr_out["value"] - syn_out["value"]) > 1e-6
            or abs(lr_out["pred"] - syn_out["pred"]) > 1e-6)
```

- [ ] **Step 2: Lancer les tests, vérifier l'échec**

Run: `cd .claude/worktrees/disjoint-lr && python -m pytest tests/sandbox/test_disjoint_heads_lr.py -q`
Expected: FAIL — `ImportError: cannot import name '_norm_weights' from 'tools.disjoint_heads_lr'` (le module n'existe pas encore).

- [ ] **Step 3: Écrire la machinerie cœur**

Créer `tools/disjoint_heads_lr.py` :

```python
"""tools/disjoint_heads_lr.py — Bras lr-par-tete (EDR 194).

EDR 192 : combiner echelle de loss + moments Adam par-tete ne ferme pas le residu (~0.70, redondant) car
« Adam par-tete annule le scaling » (Adam est ~invariant d'echelle : scaler la loss par c scale le gradient par c,
mais Adam divise par sqrt(v) ~ c -> pas inchange). Il reste UN bouton de credit qu'Adam ne normalise pas : le
learning rate (lr multiplie directement le pas d'Adam). Ce banc teste si un lr adaptatif par-tete
(lr_k proportionnel a 1/EMA(loss_k)) ferme le residu (-> desequilibre de PAS, archi refutee ~100%) ou plafonne au
niveau des leviers interchangeables ~0.7-0.79 (-> plancher architectural, petit). Reutilise 152 (_train_arm,
FlatModel) + 153 (_recovery). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_lr
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


def _norm_weights(ema, eps=1e-8):
    """Poids par-tete normalises a moyenne 1 : w_k proportionnel a 1/(EMA_k+eps), w.sum() == N_HEADS.
    Miroir de la normalisation d'EDR 153/192, extrait ici pour testabilite."""
    w = 1.0 / (np.asarray(ema, dtype=np.float64) + eps)
    return w / w.sum() * N_HEADS


def _train_flat_lr_perhead(seed, teachers, steps=STEPS, decay=0.99):
    """FLAT (archi plate, meme init au seed) + N_HEADS Adam (un par tete, moments propres). Au lieu de scaler la
    loss (192), on module le LEARNING RATE de chaque optimiseur par w_k = _norm_weights(EMA(loss)) — le seul bouton
    de credit qu'Adam ne normalise pas. Forward unique, puis par tete k : lr_k <- LR*w_k ; zero_grad ;
    ls[k].backward(retain_graph si k<N_HEADS-1) [loss BRUTE, non scalee] ; step."""
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
        w = _norm_weights(ema)
        for k in range(N_HEADS):
            opts[k].param_groups[0]["lr"] = LR * float(w[k])
            opts[k].zero_grad(set_to_none=True)
            ls[k].backward(retain_graph=(k < N_HEADS - 1))
            opts[k].step()
    return _eval_losses(model, held)


def _verdict_lr(per_seed_recovery):
    """LR_CLOSES si recovery>=0.90 majorite ; LR_INTERCHANGEABLE si <=0.79 majorite ; sinon PARTIAL. GELE."""
    n = len(per_seed_recovery)
    maj = n // 2 + 1
    closes = sum(1 for r in per_seed_recovery if r >= 0.90)
    inter = sum(1 for r in per_seed_recovery if r <= 0.79)
    if closes >= maj:
        return "LR_CLOSES"
    if inter >= maj:
        return "LR_INTERCHANGEABLE"
    return "PARTIAL"
```

- [ ] **Step 4: Lancer les tests, vérifier le succès**

Run: `cd .claude/worktrees/disjoint-lr && python -m pytest tests/sandbox/test_disjoint_heads_lr.py -q`
Expected: PASS — 6 tests verts (les 3 verdict + `_norm_weights` + train-arm fini + diffère-de-192). Si `torch is None`, les 2 tests torch sont SKIP (les 4 autres passent).

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/disjoint-lr
git add -- tools/disjoint_heads_lr.py tests/sandbox/test_disjoint_heads_lr.py
git commit -m "feat(EDR-194): machinerie bras lr-par-tete (_norm_weights, _train_flat_lr_perhead, _verdict_lr)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Runner `main_lr_check` + rapport + déterminisme + smoke

**Files:**
- Modify: `tools/disjoint_heads_lr.py` (ajouter `_report_lr`, `main_lr_check`, bloc `__main__`)
- Test: `tests/sandbox/test_disjoint_heads_lr.py` (ajouter déterminisme + smoke)

**Interfaces:**
- Consumes : `_train_flat_lr_perhead`, `_verdict_lr` (Task 1) ; `_train_arm` (152) ; `_recovery` (153).
- Produces : `main_lr_check(K=5, base=2200, steps=STEPS, _return=False) -> dict{"verdict","mean_recovery","per_seed"} | None`. `per_seed` = liste de dicts `{"seed","flat","flatlrperhead","disj","recovery"}`.

- [ ] **Step 1: Écrire les tests qui échouent (déterminisme + smoke)**

Ajouter à la fin de `tests/sandbox/test_disjoint_heads_lr.py` :

```python
from tools.disjoint_heads_lr import main_lr_check


def test_smoke_lr_returns_verdict():
    res = main_lr_check(K=2, base=2200, steps=30, _return=True)
    assert res["verdict"] in {"LR_CLOSES", "LR_INTERCHANGEABLE", "PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_lr_check_deterministic_two_passes():
    a = main_lr_check(K=2, base=2200, steps=50, _return=True)
    b = main_lr_check(K=2, base=2200, steps=50, _return=True)
    assert a["mean_recovery"] == b["mean_recovery"]
    assert [r["recovery"] for r in a["per_seed"]] == [r["recovery"] for r in b["per_seed"]]
```

- [ ] **Step 2: Lancer les nouveaux tests, vérifier l'échec**

Run: `cd .claude/worktrees/disjoint-lr && python -m pytest tests/sandbox/test_disjoint_heads_lr.py::test_smoke_lr_returns_verdict tests/sandbox/test_disjoint_heads_lr.py::test_lr_check_deterministic_two_passes -q`
Expected: FAIL — `ImportError: cannot import name 'main_lr_check' from 'tools.disjoint_heads_lr'`.

- [ ] **Step 3: Ajouter le rapport, le runner et le bloc `__main__`**

Ajouter à `tools/disjoint_heads_lr.py` (après `_verdict_lr`) :

```python
def _report_lr(rows, verdict, mean_rec):
    print("\n=== Bras lr-par-tete (FLAT vs FLAT_LR_PERHEAD vs DISJOINT, tetes MSE) ===")
    print("  seed | FLAT v/p     | FLAT_LR v/p   | DISJOINT v/p  | recovery")
    for r in rows:
        f, lr_, d = r["flat"], r["flatlrperhead"], r["disj"]
        print("  %4d | %.3f %.3f | %.3f %.3f | %.3f %.3f | %+.3f"
              % (r["seed"], f["value"], f["pred"], lr_["value"], lr_["pred"],
                 d["value"], d["pred"], r["recovery"]))
    print("  MOYEN recovery=%+.3f" % mean_rec)
    print("=== VERDICT ===")
    print("  -> %s (recovery >= 0.90 majorite = LR_CLOSES ; <= 0.79 = LR_INTERCHANGEABLE)" % verdict)


def main_lr_check(K=5, base=2200, steps=STEPS, _return=False):
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
        flat, _ = _train_arm("flat", s, teachers, steps=steps)
        flatlrperhead = _train_flat_lr_perhead(s, teachers, steps=steps)
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat, "flatlrperhead": flatlrperhead, "disj": disj,
                     "recovery": _recovery(flat, flatlrperhead, disj)})
    recs = [r["recovery"] for r in rows]
    verdict = _verdict_lr(recs)
    mean_rec = float(np.mean(recs))
    _report_lr(rows, verdict, mean_rec)
    res = {"verdict": verdict, "mean_recovery": mean_rec, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_lr_check()
```

- [ ] **Step 4: Lancer toute la suite, vérifier le succès**

Run: `cd .claude/worktrees/disjoint-lr && python -m pytest tests/sandbox/test_disjoint_heads_lr.py -q`
Expected: PASS — 8 tests (6 de Task 1 + smoke + déterminisme). Si `torch is None` : les tests torch SKIP, le smoke passe (verdict `SKIPPED_NO_TORCH`).

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/disjoint-lr
git add -- tools/disjoint_heads_lr.py tests/sandbox/test_disjoint_heads_lr.py
git commit -m "feat(EDR-194): main_lr_check + rapport + tests determinisme/smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Run scientifique (hors tâches TDD, après revue finale opus + verdict gelé confirmé)

Non exécuté par les implémenteurs. Après la revue finale (validité + verdict gelé), le contrôleur lance :

Run: `cd .claude/worktrees/disjoint-lr && python -m tools.disjoint_heads_lr` (défaut K=5, base=2200, steps=2000), DEUX fois, et vérifie que `mean_recovery` + recoveries par-seed sont byte-identiques entre les deux passes. Consigner les sorties (`lr_pass1.txt`/`lr_pass2.txt`) et le verdict obtenu. PUIS écrire l'EDR doc + mémoire + PR (non couverts par ce plan).
