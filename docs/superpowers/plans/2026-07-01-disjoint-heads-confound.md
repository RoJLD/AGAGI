# Contrôle du confond Adam par-tête — Implementation Plan (EDR 153)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Un contrôle A/B qui teste si un fix cheap côté FLAT (équilibrage d'échelle de loss) recouvre le gain de DISJOINT observé en EDR 152 — tranchant le confond « Adam par-tête vs isolation architecturale ».

**Architecture:** Nouveau fichier `tools/disjoint_heads_confound.py` réutilisant par IMPORT la machinerie d'`tools/disjoint_heads_ab.py` (sur main, PR #118). 3 bras par seed : FLAT + DISJOINT (via `_train_arm` existant) + FLAT_NORM (nouveau : FlatModel + Adam unique + losses pondérées EMA). Métrique = recouvrement du gain DISJOINT par FLAT_NORM sur les têtes MSE.

**Tech Stack:** PyTorch (CPU), numpy. Auto-contenu.

## Global Constraints

- TOOLING additif : NOUVEAU fichier `tools/disjoint_heads_confound.py` + test. NE modifie AUCUN fichier existant (ni `tools/disjoint_heads_ab.py` = EDR 152, ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*`).
- Réutilise par IMPORT depuis `tools.disjoint_heads_ab` : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR`.
- Prints exécutés = **ASCII-only** (cp1252). Accents seulement en docstrings/commentaires.
- Déterminisme : `torch.manual_seed`+`np.random.seed` par bras ; `torch.set_num_threads(1)` + `use_deterministic_algorithms(True)` (try) dans `main`. Run = **2 passes byte-identiques**.
- Verdict `_verdict_confound` = GELÉ (seuils 0.50 / 0.20, majorité). K=5, base=2200.

**Répertoire de travail** : worktree `c:\Users\robla\VScode_Project\AGAGI\.claude\worktrees\disjoint-confound` (branche `chantier/disjoint-confound`). Toutes commandes git/pytest visent ce répertoire (`cd` chemin absolu). NE COMMITE PAS ailleurs.

---

### Task 1: FLAT_NORM + recovery + verdict

**Files:**
- Create: `tools/disjoint_heads_confound.py`
- Test: `tests/sandbox/test_disjoint_heads_confound.py`

**Interfaces:**
- Consumes (import) : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm, N_HEADS, HELDOUT, BATCH, STEPS, LR` depuis `tools.disjoint_heads_ab`.
- Produces : `_train_flat_norm(seed, teachers, steps=STEPS, decay=0.99) -> dict{action,value,pred}` ; `_recovery(flat, flatnorm, disj) -> float` ; `_verdict_confound(per_seed_recovery) -> str`.

- [ ] **Step 1: Écrire les tests qui échouent**

`tests/sandbox/test_disjoint_heads_confound.py` :

```python
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

torch = pytest.importorskip("torch")

from tools.disjoint_heads_ab import _make_teachers
from tools.disjoint_heads_confound import _train_flat_norm, _recovery, _verdict_confound


def test_verdict_confound_three_branches():
    assert _verdict_confound([0.6, 0.7, 0.8, 0.1, 0.0]) == "CONFOUND_CONFIRMED"
    assert _verdict_confound([0.1, 0.0, 0.15, 0.6, 0.7]) == "CONFOUND_REFUTED"
    assert _verdict_confound([0.3, 0.4, 0.35, 0.6, 0.0]) == "CONFOUND_PARTIAL"


def test_recovery_math():
    flat = {"action": 0.25, "value": 0.030, "pred": 0.030}
    disj = {"action": 0.25, "value": 0.010, "pred": 0.010}
    flatnorm = {"action": 0.25, "value": 0.020, "pred": 0.020}
    assert abs(_recovery(flat, flatnorm, disj) - 0.5) < 1e-9


def test_train_flat_norm_finite():
    te = _make_teachers()
    d = _train_flat_norm(2200, te, steps=40)
    assert set(d.keys()) == {"action", "value", "pred"}
    assert all(v == v and v < 1e6 for v in d.values())
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_disjoint_heads_confound.py -v`
Expected: FAIL (ModuleNotFoundError: tools.disjoint_heads_confound).

- [ ] **Step 3: Créer le module (EXACTEMENT ce contenu)**

`tools/disjoint_heads_confound.py` :

```python
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
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_disjoint_heads_confound.py -v`
Expected: PASS (3 tests). Si torch absent → SKIPPED (importorskip) — valide.

- [ ] **Step 5: Vérifier zéro modif (fichiers existants intacts)**

Run: `git status --short`
Expected: seulement `tools/disjoint_heads_confound.py` et `tests/sandbox/test_disjoint_heads_confound.py` en ajout (`??` ou `A`). AUCUN fichier existant modifié (`M`).

- [ ] **Step 6: Commit**

```bash
git add tools/disjoint_heads_confound.py tests/sandbox/test_disjoint_heads_confound.py
git commit -m "feat(confound): FLAT_NORM (GradNorm-lite) + recovery + verdict gele

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: report + main + smoke

**Files:**
- Modify: `tools/disjoint_heads_confound.py` (AJOUTER après `_verdict_confound`)
- Test: `tests/sandbox/test_disjoint_heads_confound.py` (AJOUTER)

**Interfaces:**
- Consumes : `_train_flat_norm`, `_recovery`, `_verdict_confound` (Task 1) ; `_train_arm`, `_make_teachers`, `torch, STEPS` (import Task 1).
- Produces : `_report_confound(rows, verdict, mean_rec) -> None` ; `main_confound_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None`.

- [ ] **Step 1: Ajouter les tests qui échouent**

Ajouter à `tests/sandbox/test_disjoint_heads_confound.py` :

```python
from tools.disjoint_heads_confound import main_confound_check


def test_smoke_confound_returns_verdict():
    res = main_confound_check(K=1, base=99000, steps=30, _return=True)
    assert res["verdict"] in {"CONFOUND_CONFIRMED", "CONFOUND_REFUTED", "CONFOUND_PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_disjoint_heads_confound.py -k smoke -v`
Expected: FAIL (ImportError sur `main_confound_check`).

- [ ] **Step 3: Implémenter (AJOUTER après `_verdict_confound`, EXACTEMENT ce code)**

```python
def _report_confound(rows, verdict, mean_rec):
    print("\n=== Controle confond Adam par-tete (FLAT vs FLAT_NORM vs DISJOINT, tetes MSE) ===")
    print("  seed | FLAT v/p     | FLAT_NORM v/p | DISJOINT v/p  | recovery")
    for r in rows:
        f, fn, d = r["flat"], r["flatnorm"], r["disj"]
        print("  %4d | %.3f %.3f | %.3f %.3f | %.3f %.3f | %+.3f"
              % (r["seed"], f["value"], f["pred"], fn["value"], fn["pred"],
                 d["value"], d["pred"], r["recovery"]))
    print("  MOYEN recovery=%+.3f" % mean_rec)
    print("=== VERDICT ===")
    print("  -> %s (recovery >= 0.50 majorite = CONFIRMED ; <= 0.20 = REFUTED)" % verdict)


def main_confound_check(K=5, base=2200, steps=STEPS, _return=False):
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
        flatnorm = _train_flat_norm(s, teachers, steps=steps)
        disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
        rows.append({"seed": s, "flat": flat, "flatnorm": flatnorm, "disj": disj,
                     "recovery": _recovery(flat, flatnorm, disj)})
    recs = [r["recovery"] for r in rows]
    verdict = _verdict_confound(recs)
    mean_rec = float(np.mean(recs))
    _report_confound(rows, verdict, mean_rec)
    res = {"verdict": verdict, "mean_recovery": mean_rec, "per_seed": rows}
    return res if _return else None


if __name__ == "__main__":
    main_confound_check()
```

- [ ] **Step 4: Lancer TOUS les tests**

Run: `python -m pytest tests/sandbox/test_disjoint_heads_confound.py -v`
Expected: PASS (4 tests). Le smoke lance 3 entraînements réduits (K=1, 30 pas) → quelques secondes.

- [ ] **Step 5: Vérifier zéro modif fichiers existants + ASCII des prints**

Run: `git status --short`
Expected: seuls les 2 fichiers du chantier touchés. Vérifie que les `print` de `_report_confound`/`main` sont strictement ASCII.

- [ ] **Step 6: Commit**

```bash
git add tools/disjoint_heads_confound.py tests/sandbox/test_disjoint_heads_confound.py
git commit -m "feat(confound): 3-bras report + main_confound_check + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Après les 2 tasks (contrôleur, hors plan subagent)

- **Run réel** : `python -m tools.disjoint_heads_confound` (K=5, base=2200, STEPS=2000), **2 passes byte-identiques**. Sauver la sortie.
- **EDR 153** dans `docs/EDR/153_*.md` (verdict + table 3 bras + interprétation vs EDR 152, caveats hérités).
- **Mémoire** : MAJ `intelligence-typing-flat-connectome` (suite EDR 152 → 153) + index MEMORY.md.
