# Sonde de Signature de Détresse du Dreaming (Phase 1-A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/dream_distress_probe.py` — un diagnostic corrélationnel qui mesure si les rêves se concentrent chez les agents proches de la mort (signature de détresse), pour orienter (pas trancher) le paradoxe Q2a d'EDR 093.

**Architecture:** Sonde déterministe appariée seedée (moule de `tools/dreaming_probe.py`). Helpers PURS (`dream_rate`, `distress_split`, `distress_verdict`) testables sans biosphère ; orchestration `run_distress` qui RÉUTILISE `run_era_organ` (livrée, EDR 092) avec `organ_fraction=1.0`. Aucune modification de `src/`.

**Tech Stack:** Python 3.13, numpy, pytest. Réutilise `run_era_organ` (`tools.dreaming_probe`), `_sign_test_p` (`tools.curriculum_transfer`), `Harness` (provenance), `async_logger` (+ `AGISEED_QUIET_LOG`).

## Global Constraints

- **Diagnostic seul** : AUCUNE modification de `src/` (le moteur). La sonde réutilise `run_era_organ`.
- **Corrélationnel, ORIENTANT, pas définitif** : le verdict `DETRESSE` motive la Phase 2 (causale), ne prouve pas que le rêve nuit.
- **Headless** : `os.environ["AGISEED_QUIET_LOG"]="1"` posé dans `main()` AVANT `async_logger.start()` (anti-segfault KuzuDB + vitesse, EDR 091/092).
- **Fuite d'env (leçon EDR 093)** : le test de provenance appelle `main()` qui pose `AGISEED_QUIET_LOG` en dur → faire `monkeypatch.setenv("AGISEED_QUIET_LOG","0")` AVANT `main()` pour que monkeypatch restaure la clé au teardown (sinon pollution inter-tests).
- **Accès substrat** : `run_era_organ(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db)` renvoie une liste de `{"age": int, "total_dreams": int, "has_organ": bool}` (tous les agents, vivants + morts). Sweet spot = `metab=0.25, payoff=3.0`.
- **Fichiers** : tout dans `tools/dream_distress_probe.py` + tests `tests/sandbox/test_dream_distress_probe.py`.

---

## File Structure

- **Create** `tools/dream_distress_probe.py` — sonde complète (helpers purs + orchestration + main).
- **Create** `tests/sandbox/test_dream_distress_probe.py` — tests des helpers purs + provenance.

---

### Task 1: Helper pur `dream_rate`

**Files:**
- Create: `tools/dream_distress_probe.py`
- Test: `tests/sandbox/test_dream_distress_probe.py`

**Interfaces:**
- Produces: `dream_rate(agent: dict) -> float` = `total_dreams / max(age, 1)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_dream_distress_probe.py
from tools.dream_distress_probe import dream_rate


def test_dream_rate_known_values():
    assert dream_rate({"age": 10, "total_dreams": 5}) == 0.5
    assert dream_rate({"age": 200, "total_dreams": 10}) == 0.05
    assert dream_rate({"age": 0, "total_dreams": 0}) == 0.0      # max(age,1) -> pas de div par zero
    assert dream_rate({"age": 0, "total_dreams": 3}) == 3.0      # age 0 -> denominateur 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py -q -p no:cacheprovider`
Expected: FAIL (cannot import `dream_rate`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/dream_distress_probe.py
"""Sonde de signature de détresse du dreaming (Phase 1-A, corrélationnel). Les rêves se concentrent-
ils chez les agents proches de la mort ? Spec : docs/superpowers/specs/2026-06-24-Dream-Distress-
Signature-design.md. ORIENTANT, pas définitif (la Phase 2 causale tranche). Diagnostic seul."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def dream_rate(agent: Dict) -> float:
    """Taux de rêve ajusté à l'exposition : total_dreams / max(age, 1) (age 0 -> dénominateur 1)."""
    return agent.get("total_dreams", 0) / max(agent.get("age", 0), 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py -q -p no:cacheprovider`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add tools/dream_distress_probe.py tests/sandbox/test_dream_distress_probe.py
git commit -m "feat(dream-distress): helper pur dream_rate (Phase 1-A)"
```

---

### Task 2: Helper pur `distress_split`

**Files:**
- Modify: `tools/dream_distress_probe.py`
- Test: `tests/sandbox/test_dream_distress_probe.py`

**Interfaces:**
- Consumes: `dream_rate`.
- Produces: `distress_split(stats: list[dict], age_floor: int = 10) -> dict` avec clés
  `rate_short`, `rate_long`, `delta`, `n_short`, `n_long`. `delta = rate_short - rate_long`.

- [ ] **Step 1: Write the failing test**

```python
# (append to tests/sandbox/test_dream_distress_probe.py)
from tools.dream_distress_probe import distress_split


def test_distress_split_short_dream_more():
    """Court-vivants rêvent plus (taux haut) -> delta > 0 = signature de détresse."""
    stats = [
        {"age": 20, "total_dreams": 10},   # court (sous mediane), taux 0.5
        {"age": 25, "total_dreams": 12},   # court, taux 0.48
        {"age": 100, "total_dreams": 5},   # long, taux 0.05
        {"age": 120, "total_dreams": 6},   # long, taux 0.05
    ]
    out = distress_split(stats)
    assert out["n_short"] == 2 and out["n_long"] == 2
    assert out["rate_short"] > out["rate_long"]
    assert out["delta"] > 0


def test_distress_split_age_floor_excludes_tiny():
    """Le filtre age_floor écarte l'artefact petit-âge (mort à 2 ticks avec 1 rêve = taux 0.5)."""
    stats = [
        {"age": 2, "total_dreams": 1},     # ECARTE (age < 10)
        {"age": 50, "total_dreams": 5},
        {"age": 150, "total_dreams": 3},
    ]
    out = distress_split(stats, age_floor=10)
    assert out["n_short"] + out["n_long"] == 2     # l'agent age 2 est exclu


def test_distress_split_empty_no_crash():
    out = distress_split([], age_floor=10)
    assert out["rate_short"] == 0.0 and out["rate_long"] == 0.0 and out["delta"] == 0.0
    assert out["n_short"] == 0 and out["n_long"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py::test_distress_split_short_dream_more -q -p no:cacheprovider`
Expected: FAIL (cannot import `distress_split`).

- [ ] **Step 3: Write minimal implementation**

```python
# (append to tools/dream_distress_probe.py, after dream_rate)
def distress_split(stats: List[Dict], age_floor: int = 10) -> Dict:
    """Filtre age >= age_floor (écarte l'artefact petit-âge), split par âge médian, compare le taux
    de rêve médian des court-vivants vs long-vivants. delta = rate_short - rate_long (>0 = détresse)."""
    kept = [s for s in stats if s.get("age", 0) >= age_floor]
    if not kept:
        return {"rate_short": 0.0, "rate_long": 0.0, "delta": 0.0, "n_short": 0, "n_long": 0}
    med_age = statistics.median([s["age"] for s in kept])
    short = [s for s in kept if s["age"] < med_age]
    long = [s for s in kept if s["age"] >= med_age]
    r_short = float(statistics.median([dream_rate(s) for s in short])) if short else 0.0
    r_long = float(statistics.median([dream_rate(s) for s in long])) if long else 0.0
    return {"rate_short": r_short, "rate_long": r_long, "delta": r_short - r_long,
            "n_short": len(short), "n_long": len(long)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py -q -p no:cacheprovider`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dream_distress_probe.py tests/sandbox/test_dream_distress_probe.py
git commit -m "feat(dream-distress): distress_split (taux de reve court vs long-vivants)"
```

---

### Task 3: Verdict pur 3-cas `distress_verdict`

**Files:**
- Modify: `tools/dream_distress_probe.py`
- Test: `tests/sandbox/test_dream_distress_probe.py`

**Interfaces:**
- Consumes: `_sign_test_p` (de `tools.curriculum_transfer`).
- Produces: `distress_verdict(deltas: list[float], delta_eps: float = 0.0) -> dict` avec clés
  `median_delta`, `n_favorable`, `sign_p`, `verdict` ∈ {`DETRESSE`, `BENEFIQUE`, `NEUTRE`}.

- [ ] **Step 1: Write the failing test**

```python
# (append to tests/sandbox/test_dream_distress_probe.py)
from tools.dream_distress_probe import distress_verdict


def test_distress_verdict_three_cases():
    # court-vivants revent nettement plus, tous du meme cote -> DETRESSE (sign_p bas)
    assert distress_verdict([0.3, 0.4, 0.35, 0.3])["verdict"] == "DETRESSE"
    # long-vivants revent plus -> BENEFIQUE
    assert distress_verdict([-0.3, -0.4, -0.35, -0.3])["verdict"] == "BENEFIQUE"
    # mixte / centre sur 0 -> NEUTRE
    assert distress_verdict([0.1, -0.1, 0.05, -0.05])["verdict"] == "NEUTRE"
    assert distress_verdict([])["verdict"] == "NEUTRE"


def test_distress_verdict_reports_fields():
    v = distress_verdict([0.3, 0.4, 0.35, 0.3])
    assert v["n_favorable"] == 4 and "sign_p" in v and v["median_delta"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py::test_distress_verdict_three_cases -q -p no:cacheprovider`
Expected: FAIL (cannot import `distress_verdict`).

- [ ] **Step 3: Write minimal implementation**

```python
# (append to tools/dream_distress_probe.py, after distress_split)
from tools.curriculum_transfer import _sign_test_p


def distress_verdict(deltas: List[float], delta_eps: float = 0.0) -> Dict:
    """Agrège les delta par seed. DETRESSE = court-vivants rêvent plus (median > eps ET sign_p<0.1) ;
    BENEFIQUE = long-vivants rêvent plus (median < -eps ET sign_p<0.1) ; NEUTRE sinon. sign_p calculé
    sur les deltas EFFECTIFS (≠0) -> évite k>n (pattern compute_transfer_verdict)."""
    if not deltas:
        return {"median_delta": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(deltas))
    n_fav = sum(1 for d in deltas if d > 0.0)
    effective = [d for d in deltas if d != 0.0]
    sign_p = _sign_test_p(sum(1 for d in effective if d > 0.0), len(effective))
    if med > delta_eps and sign_p < 0.1:
        verdict = "DETRESSE"
    elif med < -delta_eps and sign_p < 0.1:
        verdict = "BENEFIQUE"
    else:
        verdict = "NEUTRE"
    return {"median_delta": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py -q -p no:cacheprovider`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dream_distress_probe.py tests/sandbox/test_dream_distress_probe.py
git commit -m "feat(dream-distress): verdict 3-cas (DETRESSE/BENEFIQUE/NEUTRE)"
```

---

### Task 4: `run_distress`, `main()` + provenance

**Files:**
- Modify: `tools/dream_distress_probe.py`
- Test: `tests/sandbox/test_dream_distress_probe.py` (provenance via monkeypatch)

**Interfaces:**
- Consumes: `run_era_organ` (`tools.dreaming_probe`), `distress_split`, `distress_verdict`,
  `Harness`, `async_logger`, `_acquire_shared_db`, `WorldConfig`.
- Produces: `run_distress(seeds, target, num_agents, max_ticks, shared_db) -> dict` ; `main() -> dict`.

- [ ] **Step 1: Write the implementation**

```python
# (append to tools/dream_distress_probe.py)
from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db
from tools.dreaming_probe import run_era_organ

log = logging.getLogger("AGIseed.DreamDistress")


def run_distress(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Par seed : une ère organe-ON (organ_fraction=1.0) au sweet spot -> distress_split -> delta.
    Agrège en verdict. Le signal : les court-vivants rêvent-ils plus (détresse) ?"""
    per_seed = []
    for seed in seeds:
        stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        split = distress_split(stats)
        per_seed.append({"seed": int(seed), **split})
        log.info("  seed=%s rate_short=%.3f rate_long=%.3f delta=%.3f (n_short=%d n_long=%d)",
                 seed, split["rate_short"], split["rate_long"], split["delta"],
                 split["n_short"], split["n_long"])
    verdict = distress_verdict([p["delta"] for p in per_seed])
    return {**verdict, "per_seed": per_seed,
            "config": {"target": target, "seeds": [int(s) for s in seeds],
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091/092), AVANT start()
    target = os.environ.get("DD_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DD_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DD_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DD_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde detresse : cible=%s seeds=%s agents=%d ticks=%d ===",
                 target, seeds, num_agents, max_ticks)
        result = run_distress(seeds, target, num_agents, max_ticks, shared_db)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_distress", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_delta=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_delta"], result["n_favorable"],
             len(result["per_seed"]), result["sign_p"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 2: Write the provenance test (monkeypatch, sans biosphère)**

```python
# (append to tests/sandbox/test_dream_distress_probe.py)
import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dream_distress_probe as dd
    monkeypatch.setattr(dd, "run_distress", lambda *a, **k: {
        "median_delta": 0.3, "n_favorable": 3, "sign_p": 0.05, "verdict": "DETRESSE",
        "per_seed": [{"seed": 0, "rate_short": 0.5, "rate_long": 0.2, "delta": 0.3,
                      "n_short": 5, "n_long": 5}],
        "config": {"target": "stoneage", "seeds": [0]}})
    monkeypatch.setattr(dd.async_logger, "start", lambda: None)
    monkeypatch.setattr(dd.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dd, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DD_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests de la session, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dd.main()
    assert result["verdict"] == "DETRESSE"
    files = glob.glob(str(tmp_path / "results" / "dream_distress_*.json"))
    assert files, "provenance non écrite"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "DETRESSE"
    assert "commit" in data and "git_dirty" in data
```

- [ ] **Step 3: Run all pure + provenance tests**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py -q -p no:cacheprovider`
Expected: PASS (7 tests : dream_rate, distress_split x3, distress_verdict x2, provenance).

- [ ] **Step 4: Vérifier l'absence de fuite d'env (run combiné)**

Run: `python -m pytest tests/sandbox/test_dream_distress_probe.py tests/sandbox/test_async_logger.py -q -p no:cacheprovider -m "not slow"`
Expected: PASS (toutes) — `test_async_logger::test_quiet_mode_off_by_default` ne doit PAS échouer (preuve que la fuite d'env est isolée).

- [ ] **Step 5: Commit**

```bash
git add tools/dream_distress_probe.py tests/sandbox/test_dream_distress_probe.py
git commit -m "feat(dream-distress): run_distress + main + provenance (Phase 1-A complet)"
```

---

### Task 5: Run réel + interprétation (pas de code)

**Files:** aucun (exécution + lecture).

- [ ] **Step 1: Lancer la sonde (stoneage, 5 seeds pour un peu de puissance)**

Run: `DD_TARGET=stoneage DD_SEEDS=0,1,2,3,4 DD_NUM_AGENTS=40 DD_MAX_TICKS=400 python tools/dream_distress_probe.py`
Expected: une ligne `VERDICT=... median_delta=...` + un JSON dans `results/dream_distress_0.json`.

- [ ] **Step 2: Lire le verdict et décider la suite**

- `DETRESSE` (court-vivants rêvent plus) → hypothèse « corrélat de détresse » plausible → **la Phase 2 (intervention causale `force_dream`) est justifiée** pour confirmer.
- `BENEFIQUE` (long-vivants rêvent plus) → le dreaming n'est PAS un signal de détresse → le paradoxe Q2a a une autre source ; reconsidérer.
- `NEUTRE` → corrélationnel non concluant → envisager la Phase 1-B (hook moteur, énergie-au-rêve) avant la Phase 2.

Rapporter la décomposition (rate_short/long, n, per-seed), JAMAIS le label nu. Signaler la
sous-puissance (sign_p).

- [ ] **Step 3: Écrire l'EDR du résultat** (numéro libre suivant, ex. 094) et committer.

---

## Self-Review

**Spec coverage :** `dream_rate` → Task 1. `distress_split` (filtre age_floor, split âge médian) →
Task 2. `distress_verdict` (3-cas, sign_p effectif) → Task 3. `run_distress` (réutilise
`run_era_organ` organ_fraction=1.0) + `main` (quiet-log avant start, provenance Harness) → Task 4.
Garde-fous (décomposition rapportée, confondants, sous-puissance) → Tasks 2/3/4 + Task 5 interprétation.
Leçon fuite d'env → Task 4 Step 2 (monkeypatch.setenv) + Step 4 (run combiné le prouve). ✓

**Placeholder scan :** aucun TODO/TBD ; tout le code est complet. ✓

**Type consistency :** `run_era_organ` renvoie `{age, total_dreams, has_organ}` → `dream_rate`/
`distress_split` consomment `{age, total_dreams}` ✓. `distress_split` produit
`{rate_short, rate_long, delta, n_short, n_long}` → `run_distress` lit `delta` (+ rapporte le reste)
✓. `distress_verdict(deltas)` ↔ `run_distress` passe `[p["delta"] for p in per_seed]` ✓.
`main` lit `median_delta`/`n_favorable`/`sign_p`/`verdict`/`per_seed` produits par `distress_verdict`
+ `run_distress` ✓.
