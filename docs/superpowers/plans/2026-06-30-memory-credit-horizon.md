# Banc « horizon de credit » (frontiere K,D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire un banc qui fait VARIER le delai D d'une tache K-bit recall et compare la frontiere (delai max appris) entre BPTT et mutation, pour trancher : l'avantage du gradient s'elargit-il quand le delai croit (horizon de credit) ?

**Architecture:** Tooling pur. On AJOUTE un bras mutation ((1+1)-ES) au reseau simplifie de `tools/grad_mem.py` (qui n'a que du BPTT), puis un nouveau `tools/memory_credit_horizon.py` qui balaie (K,D) sur les deux bras et rend un verdict gele. Aucun `src/`, aucun `make_population`/torch/Biosphere.

**Tech Stack:** Python, numpy. Reutilise `tools/grad_mem.py` (`run_bptt`, `train`) et `src.seed_ai.harness` (`Harness`).

## Global Constraints

- **Zero fichier partage** : SEULS `tools/grad_mem.py` (ajout non-regressif), `tools/memory_credit_horizon.py` (nouveau) et les tests sont modifies. AUCUN `src/`, AUCUN `make_population`/torch/`substrate_ab*` (fichiers actifs de la session // moteur torch). `git diff src/` doit rester VIDE.
- **Non-regression `grad_mem.py`** : `main()` et `train`/`run_bptt` existants inchanges ; on AJOUTE seulement `train_mutation`.
- **Comparaison appariee** : BPTT et mutation tournent sur le MEME reseau, MEME tache, MEME budget (`epochs`), MEMES seeds.
- **ASCII-only dans tout `print` execute** (Windows cp1252) : `->`, `+/-` ASCII OK, pas de fleche/accent unicode.
- **Provenance** : `Harness(name="memory_credit_horizon")` -> JSON distinct ; seed reel 1167, smoke 99167 distinct. Run reel APRES revue ; AUCUN test relance apres.
- **Verdict gele** : `HORIZON CONFIRME` si `gap(D_max_grille) - gap(D_min_grille) >= 0.20` ET il existe D avec `acc_bptt>=0.90` ET `acc_mut<=0.65` ; `HORIZON REFUTE` sinon ; `INDETERMINE` si une frontiere est vide. `gap(D) = acc_bptt(D) - acc_mut(D)`.

---

### Task 1: bras mutation ((1+1)-ES) sur le reseau simplifie

**Files:**
- Modify: `tools/grad_mem.py` (ajouter `train_mutation` apres `train`, ~l.83)
- Test: `tests/sandbox/test_grad_mem_mutation.py` (creer)

**Interfaces:**
- Consumes: `run_bptt(W, I, O, K, D, bits) -> (loss, dW, acc)` (existant, `tools/grad_mem.py:19`) ; `np`.
- Produces: `train_mutation(N, I=8, O=8, K=6, D=3, epochs=700, batch=64, sigma=0.1, seed=0) -> float` (accuracy sign-match finale).

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_grad_mem_mutation.py` :

```python
from tools.grad_mem import train_mutation


def test_train_mutation_deterministic():
    # memes args + meme seed -> accuracy identique (reproductible).
    a = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=50, seed=7)
    b = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=50, seed=7)
    assert a == b


def test_train_mutation_returns_valid_accuracy():
    a = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=20, seed=1)
    assert 0.0 <= a <= 1.0


def test_train_mutation_learns_trivial_recall():
    # 1 bit, sans delai (D=0), budget genereux -> doit depasser le hasard (0.5) nettement.
    a = train_mutation(N=12, I=8, O=8, K=1, D=0, epochs=600, seed=3)
    assert a >= 0.7, f"mutation doit apprendre le rappel 1-bit sans delai (acc={a})"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_grad_mem_mutation.py -v`
Expected: FAIL — `ImportError: cannot import name 'train_mutation' from 'tools.grad_mem'`.

- [ ] **Step 3: Implement `train_mutation` in `tools/grad_mem.py`**

Dans `tools/grad_mem.py`, ajouter APRES la fonction `train` (apres l.82, avant `def main`) :

```python
def train_mutation(N, I=8, O=8, K=6, D=3, epochs=700, batch=64, sigma=0.1, seed=0):
    """(1+1)-ES sur le reseau simplifie : perturbe W += N(0,sigma), compare candidat vs incumbent sur
    la MEME batch chaque pas (fitness appariee -> robuste au bruit de fitness, EDR 078), garde si
    acc_cand >= acc_inc. Reutilise run_bptt pour le forward (dW ignore). Meme budget (epochs) que train
    (BPTT) -> comparaison appariee. Renvoie l'accuracy sign-match finale (eval frais 512)."""
    np.random.seed(seed)
    W = np.random.randn(N, N) * 0.3
    for _ in range(epochs):
        cand = W + np.random.randn(N, N) * sigma
        bits = np.random.choice([-1.0, 1.0], size=(batch, K)).astype(np.float64)
        _, _, a_w = run_bptt(W, I, O, K, D, bits)
        _, _, a_c = run_bptt(cand, I, O, K, D, bits)
        if a_c >= a_w:
            W = cand
    bits = np.random.choice([-1.0, 1.0], size=(512, K)).astype(np.float64)
    _, _, acc = run_bptt(W, I, O, K, D, bits)
    return acc
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/sandbox/test_grad_mem_mutation.py -v`
Expected: PASS (3/3). `test_train_mutation_learns_trivial_recall` est un peu lent (600 pas x 2 forwards) mais court (petit reseau).

- [ ] **Step 5: Confirm non-regression of `grad_mem`**

Run: `python -c "import tools.grad_mem as g; print(hasattr(g,'train_mutation'), g.train.__defaults__ is not None)"`
Expected: `True True` (l'ajout n'a pas casse `train`/`main`).

- [ ] **Step 6: Commit**

```bash
git add tools/grad_mem.py tests/sandbox/test_grad_mem_mutation.py
git commit -m "feat(grad_mem): bras mutation (1+1)-ES same-batch sur le reseau simplifie (pour banc horizon de credit)"
```

---

### Task 2: banc frontiere (K,D) + verdict + report + entry point

**Files:**
- Create: `tools/memory_credit_horizon.py`
- Test: `tests/sandbox/test_memory_credit_horizon.py` (creer)

**Interfaces:**
- Consumes: `tools.grad_mem.train(N, I, O, K, D, epochs, batch, lr, seed)` et `tools.grad_mem.train_mutation(N, I, O, K, D, epochs, batch, sigma, seed)` (Task 1) ; `Harness` (`src.seed_ai.harness`) ; `np`.
- Produces:
  - `train_arm(arm, N=19, I=8, O=8, K=4, D=3, epochs=400, batch=64, seed=0) -> float`.
  - `frontier(arm, K=4, Ds=(1,3,6,10,16,24), seeds=(0,1,2), N=19, I=8, O=8, epochs=400, batch=64) -> dict` (`{D: mean_acc}`).
  - `_verdict_horizon(front_bptt, front_mut, gap_margin=0.20, hi=0.90, lo=0.65) -> str`.
  - `_report_horizon(h, K, front_bptt, front_mut, R, _return) -> dict|None`.
  - `main_credit_horizon(K=4, Ds=(1,3,6,10,16,24), R=3, epochs=400, seed=1167, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_memory_credit_horizon.py` :

```python
from tools.memory_credit_horizon import (train_arm, _verdict_horizon, main_credit_horizon)


def test_train_arm_dispatch_deterministic():
    a = train_arm("mutation", N=10, K=1, D=0, epochs=30, seed=5)
    b = train_arm("mutation", N=10, K=1, D=0, epochs=30, seed=5)
    assert a == b
    c = train_arm("bptt", N=12, K=1, D=0, epochs=30, seed=5)
    assert 0.0 <= c <= 1.0


def test_train_arm_rejects_unknown():
    import pytest
    with pytest.raises(ValueError):
        train_arm("nope", N=10, K=1, D=0, epochs=1, seed=0)


def test_verdict_horizon_branches():
    confirme = ({1: 0.95, 24: 0.95}, {1: 0.90, 24: 0.65})   # gap 0.05 -> 0.30 (delta 0.25) ; D=24 separe
    assert _verdict_horizon(*confirme) == "HORIZON CONFIRME"
    refute = ({1: 0.95, 24: 0.95}, {1: 0.90, 24: 0.85})      # gap 0.05 -> 0.10 (delta 0.05)
    assert _verdict_horizon(*refute) == "HORIZON REFUTE"
    assert _verdict_horizon({1: 0.9}, {}) == "INDETERMINE"


def test_main_credit_horizon_smoke():
    r = main_credit_horizon(K=1, Ds=(1, 6), R=1, epochs=20, seed=99167, _return=True)
    assert r["verdict"] in ("HORIZON CONFIRME", "HORIZON REFUTE", "INDETERMINE")
    assert len(r["table"]) == 2   # 2 valeurs de D
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_memory_credit_horizon.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.memory_credit_horizon'`.

- [ ] **Step 3: Implement `tools/memory_credit_horizon.py`**

Creer `tools/memory_credit_horizon.py` :

```python
"""tools/memory_credit_horizon.py — Banc « horizon de credit » (P1 audit memoire).

Fait VARIER le delai D d'une tache K-bit recall (reseau simplifie de grad_mem) et compare la frontiere
(acc vs D) entre BPTT et mutation. Question falsifiable : l'avantage du gradient s'ELARGIT-il quand le
delai croit (assignation de credit a travers le temps) ? Si oui -> HORIZON CONFIRME (aligne EDR 067 +
le verrou credit-assignment d'EDR 119/120) ; si la mutation suit BPTT a grand D -> HORIZON REFUTE.

Tooling pur (pas de src/, pas de make_population/torch/Biosphere). Usage : python -m tools.memory_credit_horizon
"""
import numpy as np

from src.seed_ai.harness import Harness
from tools.grad_mem import train, train_mutation


def train_arm(arm, N=19, I=8, O=8, K=4, D=3, epochs=400, batch=64, seed=0):
    """Entraine un bras sur le reseau simplifie. arm in {'bptt','mutation'}. Meme reseau/tache/budget
    -> comparaison appariee. Renvoie l'accuracy sign-match finale."""
    if arm == "bptt":
        return train(N, I, O, K, D, epochs, batch, seed=seed)
    if arm == "mutation":
        return train_mutation(N, I, O, K, D, epochs, batch, seed=seed)
    raise ValueError(f"arm inconnu: {arm!r}")


def frontier(arm, K=4, Ds=(1, 3, 6, 10, 16, 24), seeds=(0, 1, 2), N=19, I=8, O=8, epochs=400, batch=64):
    """Balaie le delai D a K fixe, R=len(seeds) seeds appaires. Renvoie {D: mean_acc}."""
    out = {}
    for D in Ds:
        accs = [train_arm(arm, N=N, I=I, O=O, K=K, D=D, epochs=epochs, batch=batch, seed=s) for s in seeds]
        out[D] = float(np.mean(accs))
    return out


def _verdict_horizon(front_bptt, front_mut, gap_margin=0.20, hi=0.90, lo=0.65):
    """HORIZON CONFIRME si le gap (bptt - mut) CROIT avec D (delta >= gap_margin) ET il existe un D ou
    BPTT tient (>=hi) la ou la mutation s'effondre (<=lo) ; HORIZON REFUTE sinon ; INDETERMINE si une
    frontiere est vide."""
    if not front_bptt or not front_mut:
        return "INDETERMINE"
    Ds = sorted(set(front_bptt) & set(front_mut))
    if not Ds:
        return "INDETERMINE"
    d_lo, d_hi = Ds[0], Ds[-1]
    gap_lo = front_bptt[d_lo] - front_mut[d_lo]
    gap_hi = front_bptt[d_hi] - front_mut[d_hi]
    grows = (gap_hi - gap_lo) >= gap_margin
    separated = any(front_bptt[d] >= hi and front_mut[d] <= lo for d in Ds)
    return "HORIZON CONFIRME" if (grows and separated) else "HORIZON REFUTE"


def _report_horizon(h, K, front_bptt, front_mut, R, _return):
    """Table ASCII (1 ligne/D : D, acc_bptt, acc_mut, gap) + D_max par bras + verdict. Save JSON."""
    verdict = _verdict_horizon(front_bptt, front_mut)
    Ds = sorted(set(front_bptt) & set(front_mut))
    print("\n=== Horizon de credit : frontiere (delai D) BPTT vs mutation ===")
    print("  D | acc_bptt acc_mut |   gap")
    for d in Ds:
        gb, gm = front_bptt[d], front_mut[d]
        print(f"  {d:2d} | {gb:8.3f} {gm:6.3f} | {gb - gm:+.3f}")

    def _dmax(front):
        ok = [d for d in Ds if front[d] >= 0.95]
        return max(ok) if ok else 0

    print(f"  D_max(acc>=0.95) : bptt={_dmax(front_bptt)} mutation={_dmax(front_mut)}")
    print("=== VERDICT (horizon de credit) ===")
    print(f"  -> {verdict}")
    table = [{"D": d, "acc_bptt": front_bptt[d], "acc_mut": front_mut[d], "gap": front_bptt[d] - front_mut[d]}
             for d in Ds]
    h.save({"K": K, "R": R, "verdict": verdict, "table": table})
    if _return:
        return {"verdict": verdict, "table": table, "K": K, "R": R}


def main_credit_horizon(K=4, Ds=(1, 3, 6, 10, 16, 24), R=3, epochs=400, seed=1167, _return=False):
    """Frontiere (K,D) appariee BPTT vs mutation sur le reseau simplifie. Quantifie si l'avantage du
    gradient s'elargit avec le delai (horizon de credit)."""
    with Harness(seed=seed, name="memory_credit_horizon", with_db=False) as h:
        base = h.seed
        seeds = [base + r for r in range(R)]
        print(f"Horizon de credit : K={K}, Ds={Ds}, R={R}, epochs={epochs}, seed={base}.")
        front_bptt = frontier("bptt", K=K, Ds=Ds, seeds=seeds, epochs=epochs)
        front_mut = frontier("mutation", K=K, Ds=Ds, seeds=seeds, epochs=epochs)
        return _report_horizon(h, K, front_bptt, front_mut, R, _return)


if __name__ == "__main__":
    main_credit_horizon()
```

- [ ] **Step 4: Run the full test file**

Run: `python -m pytest tests/sandbox/test_memory_credit_horizon.py -v`
Expected: PASS (4/4). Le smoke tourne 2 valeurs de D x 2 bras x R=1 a epochs=20 -> rapide.

- [ ] **Step 5: Commit**

```bash
git add tools/memory_credit_horizon.py tests/sandbox/test_memory_credit_horizon.py
git commit -m "feat(tooling): banc horizon de credit (frontiere K,D : BPTT vs mutation x delai) + verdict gele"
```

---

## Self-Review

**Spec coverage** : Task 1 = bras mutation (spec §2 correction + §4.1) ; Task 2 = `train_arm`/`frontier`/`_verdict_horizon`/`_report_horizon`/`main_credit_horizon` (spec §4) + verdict gele (§5) + provenance Harness (§6) + tests (§7). Le run reel + doc EDR (§9) sont hors-plan (executes par le controleur APRES revue, comme le chantier de-confond). Couvert.

**Placeholders** : aucun — code complet a chaque step.

**Type consistency** : `train_mutation` (Task 1) signature == celle consommee par `train_arm` (Task 2). `_verdict_horizon(front_bptt, front_mut)` ordre des args == usage dans les tests et `_report_horizon`. `frontier` renvoie `{D: float}` consomme par `_verdict_horizon`/`_report_horizon`. Coherent.
