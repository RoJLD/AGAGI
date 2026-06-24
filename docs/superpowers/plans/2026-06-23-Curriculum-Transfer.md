# Harnais Ratio de Transfert — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Écrire l'expérience falsifiable « le curriculum développemental transfère-t-il mieux que tabula-rasa ? » : deux bras (curriculum complet vs cible seule, **budget compute égal**), apparié multi-seed, verdict {TRANSFERE/NEUTRE/NUIT} + provenance ledger.

**Architecture:** Réutilise la machinerie existante (`make_run_era_fn`, `CurriculumRunner`, `competence_for`, `Harness`). Le bras tabula-rasa = un `CurriculumRunner` à un seul stage qui ne diplôme jamais (`c_floor=1.1`) et tourne exactement T ères. `run_era_fn` **injectable** → orchestration testable sans biosphère.

**Tech Stack:** Python 3.13, stdlib (`math`/`statistics`), pytest. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-23-Curriculum-Transfer-design.md`

---

## File Structure

- **Create** `tools/curriculum_transfer.py` — `_sign_test_p`, `compute_transfer_verdict`, `run_transfer_experiment`, `main`.
- **Create** `tests/sandbox/test_curriculum_transfer.py` — verdict (pur) + orchestration (fake run_era_fn) + provenance (monkeypatch).
- **Modify** `roadmap.md` — Dev #3 : mesure de transfert livrée.

Convention : tests via `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: `compute_transfer_verdict` + `_sign_test_p` (pur)

**Files:**
- Create: `tools/curriculum_transfer.py`
- Test: `tests/sandbox/test_curriculum_transfer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_curriculum_transfer.py
from tools.curriculum_transfer import compute_transfer_verdict, _sign_test_p


def test_sign_test_p_extremes():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1          # tous du même côté -> significatif
    assert _sign_test_p(3, 6) == 1.0         # 50/50 -> p=1
    assert 0.0 <= _sign_test_p(4, 5) <= 1.0


def test_verdict_transfere_when_ratios_above_one():
    v = compute_transfer_verdict([1.5, 1.4, 1.6, 1.3, 1.5])
    assert v["verdict"] == "TRANSFERE"
    assert v["n_favorable"] == 5 and v["n"] == 5
    assert v["median_ratio"] > 1.0


def test_verdict_nuit_when_ratios_below_one():
    v = compute_transfer_verdict([0.5, 0.6, 0.4, 0.5])
    assert v["verdict"] == "NUIT"


def test_verdict_neutre_in_band_or_mixed():
    assert compute_transfer_verdict([1.01, 0.99, 1.02, 0.98])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["sign_p"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py -k "sign_test or verdict" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.curriculum_transfer'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/curriculum_transfer.py
"""Harnais Ratio de Transfert (Dev #3, mesure). Le curriculum développemental transfère-t-il mieux
que tabula-rasa ? Expérience appariée multi-seed à BUDGET COMPUTE ÉGAL, verdict + provenance ledger.
Spec : docs/superpowers/specs/2026-06-23-Curriculum-Transfer-design.md"""
import os
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

log = logging.getLogger("AGIseed.CurriculumTransfer")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe). Sans dépendance (math.comb)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_transfer_verdict(ratios: List[float], neutral_band: float = 0.05) -> Dict:
    """ratio par seed -> {n, median_ratio, n_favorable, sign_p, verdict}. PUR (testable sans biosphère)."""
    n = len(ratios)
    if n == 0:
        return {"n": 0, "median_ratio": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(ratios))
    n_fav = sum(1 for r in ratios if r > 1.0)
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    if med > 1.0 + neutral_band and 2 * n_fav > n:
        verdict = "TRANSFERE"
    elif med < 1.0 - neutral_band and 2 * n_fav < n:
        verdict = "NUIT"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_ratio": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py -k "sign_test or verdict" -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/curriculum_transfer.py tests/sandbox/test_curriculum_transfer.py
git commit -m "feat(curriculum): compute_transfer_verdict + test de signe (mesure de transfert, pur) (Dev3)"
```

---

### Task 2: `run_transfer_experiment` (deux bras, budget égal, `run_era_fn` injectable)

**Files:**
- Modify: `tools/curriculum_transfer.py`
- Test: `tests/sandbox/test_curriculum_transfer.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_curriculum_transfer.py
from src.curriculum.runner import EraResult, GraduationConfig
from tools.curriculum_transfer import run_transfer_experiment


def test_two_arms_equal_budget_and_pairing():
    """fake run_era_fn : compétence haute SI un ancêtre est hérité (bras curriculum atteint la cible
    avec transfert), basse sinon (bras tabula-rasa part de zéro). -> ratio > 1, TRANSFERE."""
    seen = []

    def fake(world_type, import_id, keep_mem):
        seen.append((world_type, import_id))
        comp = 0.8 if import_id is not None else 0.4
        return EraResult(competence=comp, champion_agent_id="champ1234")

    res = run_transfer_experiment(
        [0], ladder=["w_easy", "w_target"], target="w_target",
        grad_cfg=GraduationConfig(max_eras=2), run_era_fn=fake, manage_logger=False,
    )
    row = res["per_seed"][0]
    assert row["seed"] == 0
    assert row["C_curr"] == 0.8 and row["C_tabula"] == 0.4
    assert row["ratio"] == 0.8 / 0.4
    # budget égal : le bras tabula-rasa a tourné EXACTEMENT total_eras ères sur la cible
    tabula_calls = [w for (w, imp) in seen if imp is None]
    assert len(tabula_calls) == row["total_eras"]
    assert all(w == "w_target" for w in tabula_calls)
    assert res["verdict"] == "TRANSFERE"


def test_experiment_handles_zero_tabula_competence():
    def fake(world_type, import_id, keep_mem):
        comp = 0.5 if import_id is not None else 0.0   # tabula -> 0 -> pas de div par zéro
        return EraResult(competence=comp, champion_agent_id="c")
    res = run_transfer_experiment([7], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1), run_era_fn=fake,
                                  manage_logger=False)
    assert res["per_seed"][0]["ratio"] < 1e9   # borné (max(C_tabula, 1e-6))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py -k "two_arms or zero_tabula" -v`
Expected: FAIL — `ImportError: cannot import name 'run_transfer_experiment'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/curriculum_transfer.py` (imports en tête, puis la fonction) :

```python
from src.curriculum.runner import CurriculumRunner, WorldStage, GraduationConfig
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import make_run_era_fn, _acquire_shared_db, DEFAULT_LADDER


def _competence_on_target(transcript) -> float:
    return float(transcript[-1]["final_competence"]) if transcript else 0.0


def run_transfer_experiment(seeds, ladder: Optional[List[str]] = None, target: Optional[str] = None,
                            num_agents: int = 40, max_ticks: int = 300,
                            grad_cfg: Optional[GraduationConfig] = None,
                            run_era_fn: Optional[Callable] = None, manage_logger: bool = True) -> Dict:
    """Deux bras par seed (curriculum vs cible seule à BUDGET ÉGAL), apparié, -> verdict.
    run_era_fn injecté -> orchestration testable sans biosphère (sinon construit via make_run_era_fn)."""
    ladder = list(ladder) if ladder else list(DEFAULT_LADDER)
    target = target or ladder[-1]
    grad_cfg = grad_cfg or GraduationConfig(max_eras=12)

    owns_engine = run_era_fn is None
    if owns_engine and manage_logger:
        async_logger.start()
    try:
        if owns_engine:
            shared_db = _acquire_shared_db()
            run_era_fn = make_run_era_fn(shared_db, WorldConfig(), num_agents=num_agents, max_ticks=max_ticks)

        per_seed = []
        for seed in seeds:
            SeedManager(seed).seed_boundary(0)                              # bras curriculum
            tc = CurriculumRunner([WorldStage(w) for w in ladder], run_era_fn, grad_cfg).run()
            c_curr = _competence_on_target(tc)
            total_eras = sum(int(row["eras"]) for row in tc)

            SeedManager(seed).seed_boundary(0)                              # bras tabula-rasa (même seed)
            no_grad = GraduationConfig(window=grad_cfg.window, eps_plateau=grad_cfg.eps_plateau,
                                       c_floor=1.1, patience=grad_cfg.patience,
                                       max_eras=max(1, total_eras))         # ne diplôme jamais -> T ères
            tt = CurriculumRunner([WorldStage(target)], run_era_fn, no_grad).run()
            c_tabula = _competence_on_target(tt)

            ratio = c_curr / max(c_tabula, 1e-6)
            per_seed.append({"seed": int(seed), "C_curr": c_curr, "C_tabula": c_tabula,
                             "total_eras": total_eras, "ratio": ratio})
            log.info("seed=%s C_curr=%.3f C_tabula=%.3f T=%d ratio=%.3f",
                     seed, c_curr, c_tabula, total_eras, ratio)

        verdict = compute_transfer_verdict([p["ratio"] for p in per_seed])
        return {**verdict, "per_seed": per_seed,
                "config": {"ladder": ladder, "target": target, "seeds": [int(s) for s in seeds],
                           "num_agents": num_agents, "max_ticks": max_ticks, "max_eras": grad_cfg.max_eras}}
    finally:
        if owns_engine and manage_logger:
            async_logger.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py -k "two_arms or zero_tabula" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/curriculum_transfer.py tests/sandbox/test_curriculum_transfer.py
git commit -m "feat(curriculum): run_transfer_experiment (2 bras, budget egal, run_era_fn injectable) (Dev3)"
```

---

### Task 3: `main()` + provenance (`Harness.save` → ledger)

**Files:**
- Modify: `tools/curriculum_transfer.py`
- Test: `tests/sandbox/test_curriculum_transfer.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_curriculum_transfer.py
import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.curriculum_transfer as ct
    monkeypatch.setattr(ct, "run_transfer_experiment", lambda *a, **k: {
        "n": 1, "median_ratio": 2.0, "n_favorable": 1, "sign_p": 1.0, "verdict": "TRANSFERE",
        "per_seed": [{"seed": 0, "C_curr": 0.8, "C_tabula": 0.4, "total_eras": 2, "ratio": 2.0}],
        "config": {"ladder": ["a", "b"], "target": "b"}})
    monkeypatch.setenv("CT_SEEDS", "0")
    ct.main()
    files = glob.glob(str(tmp_path / "results" / "curriculum_transfer_*.json"))
    assert files, "fichier de provenance non écrit"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "TRANSFERE"          # le résultat est sous data["data"]
    assert "commit" in data and "git_dirty" in data        # provenance ledger (Harness.save)
    assert data["seed"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py::test_main_writes_provenance -v`
Expected: FAIL — `AttributeError: module 'tools.curriculum_transfer' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/curriculum_transfer.py` l'import `Harness` (compléter la ligne `from src.seed_ai.harness import SeedManager`) :

```python
from src.seed_ai.harness import SeedManager, Harness
```

et la fonction `main` + le garde `__main__` :

```python
def main():
    seeds = [int(s) for s in os.environ.get("CT_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    ladder = [w for w in os.environ.get("CT_LADDER", ",".join(DEFAULT_LADDER)).split(",") if w.strip()]
    target = os.environ.get("CT_TARGET") or (ladder[-1] if ladder else None)
    num_agents = int(os.environ.get("CT_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("CT_MAX_TICKS", "300"))
    grad_cfg = GraduationConfig(max_eras=int(os.environ.get("CT_MAX_ERAS", "12")))

    result = run_transfer_experiment(seeds, ladder=ladder, target=target,
                                     num_agents=num_agents, max_ticks=max_ticks, grad_cfg=grad_cfg)

    meta_seed = min(seeds) if seeds else 0
    h = Harness(seed=meta_seed, name="curriculum_transfer", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_ratio=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_ratio"], result["n_favorable"], result["n"],
             result["sign_p"], path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py::test_main_writes_provenance -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/curriculum_transfer.py tests/sandbox/test_curriculum_transfer.py
git commit -m "feat(curriculum): main() + provenance Harness.save (verdict au dashboard via ledger C1) (Dev3)"
```

---

### Task 4: Intégration & non-régression + roadmap

**Files:** `roadmap.md`

- [ ] **Step 1: Suite complète du harnais + non-régression curriculum**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py tests/sandbox/test_curriculum_runner.py tests/sandbox/test_harness.py -q`
Expected: PASS

- [ ] **Step 2: Smoke import (le module charge, machinerie câblée)**

Run: `python -c "import tools.curriculum_transfer as ct; print('OK', ct.compute_transfer_verdict([1.2,1.3])['verdict'])"`
Expected: `OK TRANSFERE`

- [ ] **Step 3: Mettre à jour la roadmap (Dev #3 mesure livrée)**

Modifier `roadmap.md` (item Dev #3) : noter que la **mesure de transfert est livrée** (`tools/curriculum_transfer.py`, verdict TRANSFERE/NEUTRE/NUIT apparié multi-seed à budget égal, provenance ledger). Reste : *lancer* l'expérience à l'échelle (compute), puis l'opt-in main_biosphere (optionnel).

```bash
git add roadmap.md
git commit -m "docs(roadmap): Dev #3 mesure de transfert livree (harnais Ratio de Transfert) (Dev3)"
```

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §4 deux bras / budget égal (tabula-rasa = single-stage `c_floor=1.1` max_eras=T) → Task 2. ✓
- §5 `compute_transfer_verdict` + `_sign_test_p` (band neutre, p de signe) → Task 1. ✓
- §6 provenance `Harness.save` → Task 3. ✓
- §8 erreurs (div par zéro bornée, `[]`→NEUTRE, logger une fois try/finally) → Tasks 1/2. ✓
- §9 tests (verdict pur, orchestration via fake run_era_fn, provenance via monkeypatch) → Tasks 1/2/3. ✓
- §9 « l'expérience réelle se lance à la main » → pas de run biosphère lourd en test (tests rapides). ✓

**2. Placeholder scan :** aucun TODO/TBD ; code complet (API `CurriculumRunner`/`make_run_era_fn`/`SeedManager`/
`Harness` lues). `run_era_fn` injectable = orchestration testable sans biosphère (la décision clé).

**3. Type consistency :** `run_transfer_experiment(..., run_era_fn=None, manage_logger=True)` cohérent
Task 2↔3. `compute_transfer_verdict` clés (`verdict`/`median_ratio`/`sign_p`/`n_favorable`/`n`) cohérentes
Tasks 1↔2↔3. `EraResult(competence, champion_agent_id)` cohérent avec le fake de test. `Harness(seed,name,
with_db,config)`/`save(data,config)` cohérent avec C1/D1.
