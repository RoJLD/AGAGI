# Sonde de Dreaming (réveil de l'organe par l'énergie) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/dreaming_probe.py` — un diagnostic qui mesure si l'organe de planification (MCTS/dreaming) survit à la sélection (Q1, sweet vs létal) et s'il paye quand il est présent (Q2), pour décider le prochain barreau de l'attaque du goulot d'exploration (EDR 014).

**Architecture:** Sonde déterministe appariée seedée (pattern de `tools/target_competence_probe.py`). Helpers PURS (prévalence d'organe, split rêveurs/non-rêveurs, verdict 4-cas) testables sans biosphère ; une couche d'orchestration biosphère (seed l'organe à fraction connue, tourne une ère, lit `organ_genes`/`total_dreams`/`age`). Diagnostic SEUL : observe, ne répare pas le moteur.

**Tech Stack:** Python 3.13, numpy, pytest. Réutilise `SeedManager`, `Harness` (provenance), `async_logger` (+ `AGISEED_QUIET_LOG`), `_prepare_world(deterministic=True)`, `init_primordial_soup`, `MambaAgent`, `survival_competence`, `WorldConfig` (knobs `base_metabolism`/`forage_payoff`).

## Global Constraints

- **Diagnostic seul** : aucune modification de `src/` (moteur). La sonde force `organ_genes` sur des génomes LOCAUX uniquement, jamais un changement de prod.
- **Repro** : `_prepare_world(..., deterministic=True)` (memory_retriever stop+clear) sur chaque ère ; `SeedManager(seed).seed_boundary(0)` avant chaque ère.
- **Headless** : `os.environ["AGISEED_QUIET_LOG"]="1"` posé dans `main()` AVANT `async_logger.start()` (anti-segfault + vitesse, cf. EDR 091).
- **Accès substrat** (verbatim) : organe = `agent["model"].genome.organ_genes[0]` (np.array bool) ; rêves = `agent.get("total_dreams", 0)` ; âge = `agent.get("age", 0)`. Énergie sweet spot = `config.base_metabolism=0.25`, `config.forage_payoff=3.0` ; létal = `1.0`/`1.0`.
- **Fichiers** : tout dans `tools/dreaming_probe.py` + tests `tests/sandbox/test_dreaming_probe.py`.

---

## File Structure

- **Create** `tools/dreaming_probe.py` — sonde complète (helpers purs + orchestration + main).
- **Create** `tests/sandbox/test_dreaming_probe.py` — tests des helpers purs + provenance.

---

### Task 1: Helper pur `organ_prevalence`

**Files:**
- Create: `tools/dreaming_probe.py`
- Test: `tests/sandbox/test_dreaming_probe.py`

**Interfaces:**
- Produces: `_has_organ(agent: dict) -> bool` ; `organ_prevalence(agents: list[dict]) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_dreaming_probe.py
import numpy as np
from types import SimpleNamespace
from tools.dreaming_probe import organ_prevalence, _has_organ


def _agent(organ_on):
    g = SimpleNamespace(organ_genes=np.array([organ_on, False], dtype=bool))
    return {"model": SimpleNamespace(genome=g)}


def test_organ_prevalence_known_fractions():
    assert organ_prevalence([]) == 0.0
    assert organ_prevalence([_agent(True), _agent(True)]) == 1.0
    assert organ_prevalence([_agent(False), _agent(False)]) == 0.0
    assert organ_prevalence([_agent(True), _agent(False)]) == 0.5


def test_has_organ_robust_to_missing():
    assert _has_organ({"model": SimpleNamespace(genome=SimpleNamespace(organ_genes=None))}) is False
    assert _has_organ({"model": None}) is False
    assert _has_organ(_agent(True)) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py -q -p no:cacheprovider`
Expected: FAIL (ModuleNotFoundError / cannot import `organ_prevalence`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/dreaming_probe.py
"""Sonde de Dreaming (barreau 0, attaque du goulot d'exploration EDR 014, approche A).
L'organe MCTS (+0.5 drain) est-il (Q1) survivable au sweet spot vs létal, et (Q2) payant quand
présent ? Spec : docs/superpowers/specs/2026-06-23-Dreaming-Organ-Revival-design.md.
Diagnostic SEUL : observe, ne répare pas le moteur."""
import os
import sys
import logging
import statistics
from typing import List, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _has_organ(agent: Dict) -> bool:
    """True si l'agent porte l'organe MCTS (organ_genes[0]). Robuste aux champs manquants."""
    model = agent.get("model")
    genome = getattr(model, "genome", None)
    og = getattr(genome, "organ_genes", None)
    return bool(og is not None and len(og) > 0 and og[0])


def organ_prevalence(agents: List[Dict]) -> float:
    """Fraction des agents portant l'organe MCTS. Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if _has_organ(a)) / len(agents)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py -q -p no:cacheprovider`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dreaming_probe.py tests/sandbox/test_dreaming_probe.py
git commit -m "feat(dreaming-probe): helper pur organ_prevalence (barreau 0, EDR 014)"
```

---

### Task 2: Helper pur `q2_split` (rêveurs vs non-rêveurs)

**Files:**
- Modify: `tools/dreaming_probe.py`
- Test: `tests/sandbox/test_dreaming_probe.py`

**Interfaces:**
- Consumes: `survival_competence` (de `src.curriculum.competence`).
- Produces: `q2_split(stats: list[dict]) -> dict` avec clés `dreamers_competence`, `nondreamers_competence`, `delta`, `n_dreamers`, `n_nondreamers`. Un `stat` = `{"age": int, "total_dreams": int}`.

- [ ] **Step 1: Write the failing test**

```python
# (append to tests/sandbox/test_dreaming_probe.py)
from tools.dreaming_probe import q2_split
from src.curriculum.competence import AGE_REF


def test_q2_split_separates_dreamers():
    stats = [
        {"age": int(AGE_REF), "total_dreams": 3},      # rêveur, compétence haute
        {"age": int(AGE_REF), "total_dreams": 1},      # rêveur
        {"age": 10, "total_dreams": 0},                # non-rêveur, basse
        {"age": 10, "total_dreams": 0},                # non-rêveur
    ]
    out = q2_split(stats)
    assert out["n_dreamers"] == 2 and out["n_nondreamers"] == 2
    assert out["dreamers_competence"] == 1.0           # médiane âge = AGE_REF
    assert out["delta"] > 0                             # rêveurs > non-rêveurs


def test_q2_split_handles_zero_dreamers():
    out = q2_split([{"age": 10, "total_dreams": 0}])
    assert out["n_dreamers"] == 0
    assert out["dreamers_competence"] == 0.0            # groupe vide -> 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py::test_q2_split_separates_dreamers -q -p no:cacheprovider`
Expected: FAIL (cannot import `q2_split`).

- [ ] **Step 3: Write minimal implementation**

```python
# (append to tools/dreaming_probe.py, after organ_prevalence)
from src.curriculum.competence import survival_competence


def q2_split(stats: List[Dict]) -> Dict:
    """Sépare les agents par rêve (total_dreams>0) et compare leur compétence-survie.
    Groupe vide -> compétence 0.0 (convention survival_competence)."""
    dreamers = [s for s in stats if s.get("total_dreams", 0) > 0]
    nondreamers = [s for s in stats if s.get("total_dreams", 0) == 0]
    c_d = survival_competence(dreamers)
    c_n = survival_competence(nondreamers)
    return {"dreamers_competence": c_d, "nondreamers_competence": c_n,
            "delta": c_d - c_n, "n_dreamers": len(dreamers), "n_nondreamers": len(nondreamers)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py -q -p no:cacheprovider`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dreaming_probe.py tests/sandbox/test_dreaming_probe.py
git commit -m "feat(dreaming-probe): q2_split (compétence reveurs vs non-reveurs)"
```

---

### Task 3: Verdict pur 4-cas (gate de l'échelle)

**Files:**
- Modify: `tools/dreaming_probe.py`
- Test: `tests/sandbox/test_dreaming_probe.py`

**Interfaces:**
- Produces: `dreaming_verdict(delta_prev_sweet, delta_prev_lethal, q2a_delta, q2b_ratio, surv_eps=0.05, pay_eps=0.02) -> str` ∈ {`SURVIT_ET_PAYE`, `SURVIT_PAS_PAYE`, `PAYE_PAS_SURVIT`, `MORT`}.

- [ ] **Step 1: Write the failing test**

```python
# (append to tests/sandbox/test_dreaming_probe.py)
from tools.dreaming_probe import dreaming_verdict


def test_verdict_four_cases():
    # survit (sweet toléré ET pression>0) ET paye (q2a delta>pay_eps OU q2b ratio>1+pay_eps)
    assert dreaming_verdict(0.0, -0.3, 0.10, 1.20) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(0.0, -0.3, 0.00, 1.00) == "SURVIT_PAS_PAYE"
    # ne survit pas (sweet purgé) mais paye
    assert dreaming_verdict(-0.4, -0.45, 0.10, 1.20) == "PAYE_PAS_SURVIT"
    assert dreaming_verdict(-0.4, -0.45, 0.00, 1.00) == "MORT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py::test_verdict_four_cases -q -p no:cacheprovider`
Expected: FAIL (cannot import `dreaming_verdict`).

- [ ] **Step 3: Write minimal implementation**

```python
# (append to tools/dreaming_probe.py, after q2_split)
def dreaming_verdict(delta_prev_sweet: float, delta_prev_lethal: float,
                     q2a_delta: float, q2b_ratio: float,
                     surv_eps: float = 0.05, pay_eps: float = 0.02) -> str:
    """Gate 4-cas. SURVIT = organe toléré au sweet spot (Δprev > -eps) ET moins purgé qu'au létal
    (pression nette > 0). PAYE = bénéfice intra-pop (q2a_delta > pay_eps) OU population on>off
    (q2b_ratio > 1+pay_eps)."""
    survives = (delta_prev_sweet > -surv_eps) and ((delta_prev_sweet - delta_prev_lethal) > 0)
    pays = (q2a_delta > pay_eps) or (q2b_ratio > 1.0 + pay_eps)
    if survives and pays:
        return "SURVIT_ET_PAYE"
    if survives and not pays:
        return "SURVIT_PAS_PAYE"
    if (not survives) and pays:
        return "PAYE_PAS_SURVIT"
    return "MORT"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py -q -p no:cacheprovider`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dreaming_probe.py tests/sandbox/test_dreaming_probe.py
git commit -m "feat(dreaming-probe): verdict 4-cas (gate de l'echelle EDR 014)"
```

---

### Task 4: Orchestration biosphère — une ère avec organe semé

**Files:**
- Modify: `tools/dreaming_probe.py`
- Test: `tests/sandbox/test_dreaming_probe.py` (smoke, marqué lent)

**Interfaces:**
- Consumes: `_prepare_world`, `init_primordial_soup`, `MambaAgent`, `WorldConfig`, `SeedManager`.
- Produces: `_set_organ(genome, on: bool)` ; `run_era_organ(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db) -> list[dict]` où chaque dict = `{"age", "total_dreams", "has_organ"}`.

- [ ] **Step 1: Write the implementation (orchestration — testée par smoke)**

```python
# (append to tools/dreaming_probe.py)
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.DreamingProbe")


def _set_organ(genome, on: bool) -> None:
    """Force organ_genes[0] (MCTS) sur un génome LOCAL. Préserve les autres organes."""
    og = np.array(genome.organ_genes, dtype=bool) if getattr(genome, "organ_genes", None) is not None \
        else np.array([False, False], dtype=bool)
    og[0] = bool(on)
    genome.organ_genes = og


def run_era_organ(target: str, seed: int, organ_fraction: float, metab: float, payoff: float,
                  num_agents: int, max_ticks: int, shared_db) -> List[Dict]:
    """UNE ère sur `target`, avec une fraction `organ_fraction` de la population portant l'organe
    MCTS (les `int(organ_fraction*num_agents)` premiers). Renvoie par agent vivant à la fin :
    {age, total_dreams, has_organ}. Déterministe (memory_retriever neutralisé)."""
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world(target, config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    n_on = int(round(organ_fraction * len(genomes)))
    for i, g in enumerate(genomes):
        _set_organ(g, i < n_on)
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=50.0)

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    survivors = list(env.agents)        # vivants à la fin -> signal de mortalité différentielle (Q1)
    out = [{"age": a.get("age", 0), "total_dreams": a.get("total_dreams", 0),
            "has_organ": _has_organ(a)} for a in survivors]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out
```

- [ ] **Step 2: Write the smoke test**

```python
# (append to tests/sandbox/test_dreaming_probe.py)
import os
import pytest


@pytest.mark.slow
def test_run_era_organ_smoke_seeds_organ():
    """Smoke biosphère : une ère courte, ~50% organe semé -> renvoie des stats avec has_organ booléen."""
    os.environ["AGISEED_QUIET_LOG"] = "1"
    from src.graph_rag.async_logger import logger as async_logger
    from tools.dreaming_probe import run_era_organ, _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        stats = run_era_organ("stoneage", seed=0, organ_fraction=0.5, metab=0.25, payoff=3.0,
                              num_agents=20, max_ticks=40, shared_db=db)
    finally:
        async_logger.stop()
    assert isinstance(stats, list)
    for s in stats:
        assert set(s) == {"age", "total_dreams", "has_organ"}
        assert isinstance(s["has_organ"], bool)
```

- [ ] **Step 3: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py::test_run_era_organ_smoke_seeds_organ -q -p no:cacheprovider`
Expected: PASS (peut prendre ~10-30 s).

- [ ] **Step 4: Commit**

```bash
git add tools/dreaming_probe.py tests/sandbox/test_dreaming_probe.py
git commit -m "feat(dreaming-probe): orchestration une ere avec organe seme (Q1/Q2 substrate)"
```

---

### Task 5: `run_q1`, `run_q2`, `main()` + provenance + verdict

**Files:**
- Modify: `tools/dreaming_probe.py`
- Test: `tests/sandbox/test_dreaming_probe.py` (provenance via monkeypatch)

**Interfaces:**
- Consumes: `run_era_organ`, `organ_prevalence` (via stats `has_organ`), `q2_split`, `dreaming_verdict`, `_sign_test_p` (de `tools.curriculum_transfer`), `Harness`.
- Produces: `run_q1(seeds, ...) -> dict`, `run_q2(seeds, ...) -> dict`, `main() -> dict`.

- [ ] **Step 1: Write the implementation**

```python
# (append to tools/dreaming_probe.py)
from tools.curriculum_transfer import _sign_test_p


def _prevalence_from_stats(stats: List[Dict]) -> float:
    """Prévalence d'organe à partir des stats run_era_organ (clé has_organ)."""
    if not stats:
        return 0.0
    return sum(1 for s in stats if s["has_organ"]) / len(stats)


def run_q1(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q1 : organe semé à 50%, prévalence des survivants sweet vs létal -> pression de sélection."""
    sweet, lethal = [], []
    for seed in seeds:
        s = run_era_organ(target, seed, 0.5, 0.25, 3.0, num_agents, max_ticks, shared_db)
        l = run_era_organ(target, seed, 0.5, 1.0, 1.0, num_agents, max_ticks, shared_db)
        sweet.append(_prevalence_from_stats(s) - 0.5)
        lethal.append(_prevalence_from_stats(l) - 0.5)
    dps = float(statistics.median(sweet)) if sweet else 0.0
    dpl = float(statistics.median(lethal)) if lethal else 0.0
    return {"delta_prev_sweet": dps, "delta_prev_lethal": dpl, "pressure": dps - dpl,
            "per_seed_sweet": sweet, "per_seed_lethal": lethal}


def run_q2(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q2 : forcé-ON au sweet spot. (a) rêveurs vs non-rêveurs ; (b) apparié ON vs OFF (ratio survie)."""
    deltas, ratios, dreams_seen = [], [], 0
    for seed in seeds:
        on = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        off = run_era_organ(target, seed, 0.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        split = q2_split(on)
        deltas.append(split["delta"])
        dreams_seen += sum(s["total_dreams"] for s in on)
        c_on, c_off = survival_competence(on), survival_competence(off)
        ratios.append(c_on / max(c_off, 1e-6))
    q2a_delta = float(statistics.median(deltas)) if deltas else 0.0
    q2b_ratio = float(statistics.median(ratios)) if ratios else 1.0
    n_fav = sum(1 for r in ratios if r > 1.0)
    sign_p = _sign_test_p(n_fav, len([r for r in ratios if r != 1.0]))
    return {"q2a_delta": q2a_delta, "q2b_ratio": q2b_ratio, "n_favorable": n_fav,
            "n": len(ratios), "sign_p": sign_p, "total_dreams_seen": dreams_seen,
            "per_seed_delta": deltas, "per_seed_ratio": ratios}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091), AVANT start()
    target = os.environ.get("DP_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DP_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DP_MAX_TICKS", "400"))
    mode = os.environ.get("DP_MODE", "both")

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        q1 = run_q1(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q1", "both") else {}
        q2 = run_q2(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q2", "both") else {}
    finally:
        async_logger.stop()

    verdict = dreaming_verdict(q1.get("delta_prev_sweet", -1.0), q1.get("delta_prev_lethal", -1.0),
                               q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0)) if mode == "both" \
        else "PARTIEL"
    result = {"verdict": verdict, "q1": q1, "q2": q2,
              "config": {"target": target, "seeds": seeds, "num_agents": num_agents,
                         "max_ticks": max_ticks, "mode": mode}}
    h = Harness(seed=min(seeds) if seeds else 0, name="dreaming_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s | Q1 pressure=%.3f (sweet=%.3f letal=%.3f) | Q2 q2a=%.3f q2b=%.3f dreams=%d -> %s",
             verdict, q1.get("pressure", 0.0), q1.get("delta_prev_sweet", 0.0),
             q1.get("delta_prev_lethal", 0.0), q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0),
             q2.get("total_dreams_seen", 0), path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 2: Write the provenance test (monkeypatch — pas de biosphère)**

```python
# (append to tests/sandbox/test_dreaming_probe.py)
import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dreaming_probe as dp
    monkeypatch.setattr(dp, "run_q1", lambda *a, **k: {
        "delta_prev_sweet": 0.0, "delta_prev_lethal": -0.3, "pressure": 0.3,
        "per_seed_sweet": [0.0], "per_seed_lethal": [-0.3]})
    monkeypatch.setattr(dp, "run_q2", lambda *a, **k: {
        "q2a_delta": 0.10, "q2b_ratio": 1.20, "n_favorable": 1, "n": 1, "sign_p": 1.0,
        "total_dreams_seen": 12, "per_seed_delta": [0.10], "per_seed_ratio": [1.20]})
    monkeypatch.setattr(dp.async_logger, "start", lambda: None)
    monkeypatch.setattr(dp.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dp, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DP_SEEDS", "0")
    monkeypatch.setenv("DP_MODE", "both")

    result = dp.main()
    assert result["verdict"] == "SURVIT_ET_PAYE"
    files = glob.glob(str(tmp_path / "results" / "dreaming_probe_*.json"))
    assert files, "provenance non écrite"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "SURVIT_ET_PAYE"
    assert "commit" in data and "git_dirty" in data
```

- [ ] **Step 3: Run all pure + provenance tests**

Run: `python -m pytest tests/sandbox/test_dreaming_probe.py -q -p no:cacheprovider -m "not slow"`
Expected: PASS (organ_prevalence, has_organ, q2_split x2, verdict, provenance — 6 tests ; le smoke `slow` est désélectionné).

- [ ] **Step 4: Commit**

```bash
git add tools/dreaming_probe.py tests/sandbox/test_dreaming_probe.py
git commit -m "feat(dreaming-probe): run_q1/run_q2/main + provenance + verdict (barreau 0 complet)"
```

---

### Task 6: Premier run réel + interprétation (pas de code)

**Files:** aucun (exécution + lecture).

- [ ] **Step 1: Lancer la sonde (stoneage, le barreau fondateur)**

Run: `DP_TARGET=stoneage DP_SEEDS=0,1,2 DP_NUM_AGENTS=40 DP_MAX_TICKS=400 python tools/dreaming_probe.py`
Expected: une ligne `VERDICT=... | Q1 pressure=... | Q2 ...` + un JSON dans `results/dreaming_probe_0.json`.

- [ ] **Step 2: Lire le verdict et décider le barreau suivant**

Selon la table de gate (spec §Logique de gate) :
- `SURVIT_ET_PAYE` → concevoir le barreau 1 (le dreaming ravivé fait-il monter les autels ?).
- `SURVIT_PAS_PAYE` → l'organe est inutile → diagnostiquer l'aval (do_dream_logit / surprise).
- `PAYE_PAS_SURVIT` → scaffold de sélection.
- `MORT` → escalade levier I (nouveauté) ou II (auto-craft).

Si `total_dreams_seen == 0` même en Q2 forcé-ON : le dreaming est bloqué EN AVAL de l'organe (logit/surprise), résultat distinct à rapporter (le réveil de l'organe ne suffit pas).

- [ ] **Step 3: Écrire l'EDR du résultat** (numéro libre suivant, ex. 092) et committer.

---

## Self-Review

**Spec coverage :** Q1 (survie, sweet vs létal, prévalence survivants) → Task 4+5 (`run_era_organ` + `run_q1`). Q2 (forcé-ON, rêveurs/non-rêveurs + apparié ON/OFF) → Task 2 + Task 5 (`q2_split` + `run_q2`). Verdict 4-cas → Task 3. Provenance/repro/quiet-log → Task 5 (`main`). Helpers purs testables → Tasks 1-3. Garde-fous (décomposition rapportée, total_dreams_seen, sous-puissance sign_p) → Task 5. ✓

**Placeholder scan :** aucun TODO/TBD ; tout le code est complet. ✓

**Type consistency :** `run_era_organ` renvoie `{age, total_dreams, has_organ}` ; `q2_split` consomme `{age, total_dreams}` ; `_prevalence_from_stats` consomme `has_organ` ; `dreaming_verdict(delta_prev_sweet, delta_prev_lethal, q2a_delta, q2b_ratio)` ↔ clés produites par `run_q1`/`run_q2`. Cohérent. ✓
