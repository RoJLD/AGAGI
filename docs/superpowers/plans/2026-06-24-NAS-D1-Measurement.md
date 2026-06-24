# Mesure X2 de D1 (coût métabolique) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/metabolic_cost_sweep.py` qui mesure si le coût métabolique d'activation (D1) sélectionne des connectomes plus efficients sans effondrer la compétence, par trajectoires évolutives appariées multi-seed.

**Architecture:** Trois couches, calquées sur `tools/curriculum_transfer.py` : (1) verdict PUR testable sans biosphère ; (2) trajectoire évolutive `run_lineage`/`run_sweep` avec `run_era_fn` injectable (testable avec un faux runner) ; (3) ère réelle instrumentée `run_era_metab` (accumule `mean_active`, aucun changement du cœur) + `main()` paramétré par env + `Harness.save`.

**Tech Stack:** Python 3, NumPy, pytest. Aucune nouvelle dépendance.

**Spec:** [`../specs/2026-06-24-NAS-D1-Measurement-design.md`](../specs/2026-06-24-NAS-D1-Measurement-design.md)

## Global Constraints

- **Instrumentation 100 % tool-local** : NE modifier AUCUN fichier sous `src/`. Tout vit dans `tools/metabolic_cost_sweep.py` + son test.
- **Banc survivable** : `WorldConfig` avec `base_metabolism=0.25`, `forage_payoff=3.0` (sweet-spot EDR 085). `metabolic_cost_coef` = la variable balayée.
- **Appariement** : `SeedManager(seed).seed_boundary(0)` au début de CHAQUE lignée → même seed pour tous les coefs d'un seed donné.
- **Testabilité** : `run_lineage`/`run_sweep` acceptent `run_era_fn` injectable ; les tests unitaires N'INSTANCIENT PAS de biosphère (faux runner déterministe). Seul un smoke opt-in (`MCS_SMOKE=1`) touche le vrai moteur.
- **Verdict pur** : `compute_sweep_verdict` est une fonction PURE (pas d'I/O, pas de RNG).
- **Git** : commits PATH-SCOPED (`git add <paths>`), jamais `-A`/`.`. Trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Couche verdict pure (`_sign_test_p` + `compute_sweep_verdict`)

**Files:**
- Create: `tools/metabolic_cost_sweep.py`
- Test: `tests/sandbox/test_metabolic_cost_sweep.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `_sign_test_p(k: int, n: int) -> float`
  - `compute_sweep_verdict(per_coef: list[dict], eff_band=0.05, collapse_frac=0.90) -> dict`
    où chaque `per_coef[i]` = `{"coef": float, "eff_ratios": list[float], "surv_ratios": list[float]}`,
    retour = `{"per_coef": [{"coef","median_eff","n","n_favorable","sign_p","collapsed","verdict"}...]}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_metabolic_cost_sweep.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.metabolic_cost_sweep import _sign_test_p, compute_sweep_verdict


def test_sign_test_p_bounds():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1     # tous favorables sur 5 -> significatif
    assert _sign_test_p(2, 4) == 1.0    # 2/4 -> bilatéral = 1.0


def test_verdict_efficace():
    per_coef = [{"coef": 0.01,
                 "eff_ratios": [1.2, 1.3, 1.15],   # efficacité en hausse
                 "surv_ratios": [0.98, 1.0, 0.95]}] # survie OK
    out = compute_sweep_verdict(per_coef)["per_coef"][0]
    assert out["verdict"] == "EFFICACE"
    assert out["median_eff"] > 1.05


def test_verdict_nuit_on_collapse():
    per_coef = [{"coef": 0.05,
                 "eff_ratios": [1.5, 1.6, 1.4],    # efficacité haute MAIS...
                 "surv_ratios": [0.5, 0.4, 0.6]}]  # survie effondrée
    out = compute_sweep_verdict(per_coef)["per_coef"][0]
    assert out["collapsed"] is True
    assert out["verdict"] == "NUIT"


def test_verdict_neutre():
    per_coef = [{"coef": 0.001,
                 "eff_ratios": [1.0, 0.99, 1.01],
                 "surv_ratios": [1.0, 1.0, 1.0]}]
    assert compute_sweep_verdict(per_coef)["per_coef"][0]["verdict"] == "NEUTRE"


def test_verdict_empty():
    assert compute_sweep_verdict([])["per_coef"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'tools.metabolic_cost_sweep'`

- [ ] **Step 3: Create the file with the pure verdict layer**

```python
# tools/metabolic_cost_sweep.py
"""tools/metabolic_cost_sweep.py — Mesure X2 de D1 (coût métabolique d'activation, NAS Axe D-1).
Le coût métabolique sélectionne-t-il des connectomes efficients sans effondrer la compétence ?
Trajectoires évolutives appariées multi-seed, banc stoneage survivable (sweet-spot EDR 085).
Spec : docs/superpowers/specs/2026-06-24-NAS-D1-Measurement-design.md
Usage : MCS_SEEDS=0,1,2 MCS_SWEEP=0,0.001,0.01 python tools/metabolic_cost_sweep.py"""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

log = logging.getLogger("AGIseed.MetabolicCostSweep")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_sweep_verdict(per_coef: List[Dict], eff_band: float = 0.05,
                          collapse_frac: float = 0.90) -> Dict:
    """per_coef[i] = {coef, eff_ratios:[par seed], surv_ratios:[par seed]} -> verdict par coef. PUR."""
    out = []
    for entry in per_coef:
        eff = list(entry.get("eff_ratios", []))
        surv = list(entry.get("surv_ratios", []))
        n = len(eff)
        if n == 0:
            out.append({"coef": entry.get("coef"), "median_eff": 0.0, "n": 0,
                        "n_favorable": 0, "sign_p": 1.0, "collapsed": False, "verdict": "NEUTRE"})
            continue
        median_eff = float(statistics.median(eff))
        n_fav = sum(1 for r in eff if r > 1.0)
        effective = [r for r in eff if r != 1.0]
        sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
        collapsed = bool(surv) and statistics.median(surv) < collapse_frac
        if collapsed:
            verdict = "NUIT"
        elif median_eff > 1.0 + eff_band and 2 * n_fav > n:
            verdict = "EFFICACE"
        else:
            verdict = "NEUTRE"
        out.append({"coef": entry.get("coef"), "median_eff": median_eff, "n": n,
                    "n_favorable": n_fav, "sign_p": sign_p, "collapsed": collapsed, "verdict": verdict})
    return {"per_coef": out}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/metabolic_cost_sweep.py tests/sandbox/test_metabolic_cost_sweep.py
git commit -m "feat(NAS-D1-measure): couche verdict pure (sign test + compute_sweep_verdict)"
```

---

### Task 2: Trajectoire évolutive appariée (`run_lineage` + `run_sweep`, runner injectable)

**Files:**
- Modify: `tools/metabolic_cost_sweep.py`
- Test: `tests/sandbox/test_metabolic_cost_sweep.py`

**Interfaces:**
- Consumes: `compute_sweep_verdict` (Task 1) ; `SeedManager` (`src.seed_ai.harness`).
- Produces:
  - `run_lineage(seed, coef, eras, num_agents, max_ticks, run_era_fn) -> dict` retour
    `{seed, coef, competence, survival, mean_active, efficiency}`.
  - `run_sweep(seeds, coefs, eras, num_agents, max_ticks, run_era_fn) -> dict` retour
    `{**compute_sweep_verdict(...), "per_lineage": [...], "config": {...}}`.
  - Le `run_era_fn` a la signature `run_era_fn(cfg, genomes, max_ticks) -> (scored, metrics)` où
    `scored = [(score, genome), ...]` et `metrics = {"ticks", "score", "mean_active"}`.

- [ ] **Step 1: Write the failing tests (faux runner déterministe, sans biosphère)**

Ajouter dans `tests/sandbox/test_metabolic_cost_sweep.py` :

```python
import numpy as np
from tools.metabolic_cost_sweep import run_lineage, run_sweep


class _FakeGenome:
    def clone(self):
        return _FakeGenome()


def _fake_run_era_fn(cfg, genomes, max_ticks):
    # Déterministe : plus le coef est haut, plus mean_active baisse (cerveaux sparses sélectionnés)
    # et plus l'efficacité monte ; survie quasi constante. competence fixe.
    coef = getattr(cfg, "metabolic_cost_coef", 0.0)
    mean_active = max(1.0, 100.0 - coef * 2000.0)   # coef=0 ->100 ; 0.01 ->80
    metrics = {"ticks": 200.0, "score": 50.0, "mean_active": mean_active}
    scored = [(50.0, _FakeGenome()) for _ in range(5)]
    return scored, metrics


def test_run_lineage_efficiency_rises_with_coef():
    base = run_lineage(seed=0, coef=0.0, eras=3, num_agents=6, max_ticks=50,
                       run_era_fn=_fake_run_era_fn)
    hi = run_lineage(seed=0, coef=0.01, eras=3, num_agents=6, max_ticks=50,
                     run_era_fn=_fake_run_era_fn)
    assert hi["efficiency"] > base["efficiency"]      # moins de noeuds actifs -> efficacité ↑
    assert hi["mean_active"] < base["mean_active"]


def test_run_lineage_paired_reproducible():
    a = run_lineage(seed=7, coef=0.005, eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    b = run_lineage(seed=7, coef=0.005, eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    assert a["efficiency"] == b["efficiency"]


def test_run_sweep_structure_and_verdict():
    out = run_sweep(seeds=[0, 1], coefs=[0.0, 0.01], eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    assert "per_coef" in out and "per_lineage" in out
    coef_entry = [c for c in out["per_coef"] if abs(c["coef"] - 0.01) < 1e-9][0]
    assert coef_entry["verdict"] == "EFFICACE"        # efficacité ↑, survie constante
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -k "lineage or sweep_structure" -v`
Expected: FAIL avec `ImportError: cannot import name 'run_lineage'`

- [ ] **Step 3: Implement `run_lineage` + `run_sweep`**

Ajouter dans `tools/metabolic_cost_sweep.py` (après `compute_sweep_verdict`) :

```python
import copy
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager

SWEET_METAB = 0.25      # sweet-spot EDR 085 (survie ×4)
SWEET_PAYOFF = 3.0


def _make_cfg(coef: float):
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    cfg.metabolic_cost_coef = coef
    return cfg


def _reproduce(champ_genomes, num_agents):
    """ÉLITE intacte + enfants mutés + fraction heavy (EDR 024), comme evolve_competence."""
    from src.seed_ai.mutation import apply_mutations, MutationConfig
    from src.seed_ai.repopulation import build_population
    mc = MutationConfig(weight_init_std=2.0)
    heavy = copy.deepcopy(mc)
    heavy.weight_mutate_rate = min(1.0, mc.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mc.weight_mutate_power * 1.5
    return build_population(champ_genomes, num_agents, mc, apply_mutations,
                           heavy_config=heavy, heavy_frac=0.3)


def run_lineage(seed: int, coef: float, eras: int = 15, num_agents: int = 30,
                max_ticks: int = 400, run_era_fn: Optional[Callable] = None) -> Dict:
    """Une trajectoire évolutive (E ères + cliquet) à coef fixe, seed apparié. KPIs sur 5 dernières ères."""
    if run_era_fn is None:
        run_era_fn = run_era_metab
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg(coef)
    from src.agents.mamba_agent import MambaAgent
    champions = [MambaAgent().genome for _ in range(5)]
    best_ever = [(0.0, g) for g in champions]
    window: List[Dict] = []
    for _era in range(1, eras + 1):
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents)
        scored, m = run_era_fn(cfg, genomes, max_ticks)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        window.append(m)
    tail = window[-5:] if len(window) >= 5 else window
    competence = float(np.mean([m["score"] for m in tail]))
    survival = float(np.mean([m["ticks"] for m in tail]))
    mean_active = float(np.mean([m["mean_active"] for m in tail]))
    efficiency = competence / max(mean_active, 1e-6)
    return {"seed": int(seed), "coef": float(coef), "competence": competence,
            "survival": survival, "mean_active": mean_active, "efficiency": efficiency}


def run_sweep(seeds, coefs, eras: int = 15, num_agents: int = 30, max_ticks: int = 400,
              run_era_fn: Optional[Callable] = None) -> Dict:
    """Sweep apparié : pour chaque seed, chaque coef -> run_lineage. Ratios vs coef=0 -> verdict."""
    coefs = list(coefs)
    if 0.0 not in coefs:
        coefs = [0.0] + coefs
    per_lineage = []
    by_seed: Dict[int, Dict[float, Dict]] = {}
    for seed in seeds:
        by_seed[seed] = {}
        for coef in coefs:
            r = run_lineage(seed, coef, eras, num_agents, max_ticks, run_era_fn)
            by_seed[seed][coef] = r
            per_lineage.append(r)
    per_coef = []
    for coef in coefs:
        if coef == 0.0:
            continue
        eff_ratios, surv_ratios = [], []
        for seed in seeds:
            base, cur = by_seed[seed][0.0], by_seed[seed][coef]
            eff_ratios.append(cur["efficiency"] / max(base["efficiency"], 1e-6))
            surv_ratios.append(cur["survival"] / max(base["survival"], 1e-6))
        per_coef.append({"coef": coef, "eff_ratios": eff_ratios, "surv_ratios": surv_ratios})
    verdict = compute_sweep_verdict(per_coef)
    return {**verdict, "per_lineage": per_lineage,
            "config": {"seeds": [int(s) for s in seeds], "coefs": coefs, "eras": eras,
                       "num_agents": num_agents, "max_ticks": max_ticks}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -k "lineage or sweep_structure" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run full test file (Task 1 + Task 2)**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/metabolic_cost_sweep.py tests/sandbox/test_metabolic_cost_sweep.py
git commit -m "feat(NAS-D1-measure): run_lineage + run_sweep apparies (runner injectable)"
```

---

### Task 3: Ère réelle instrumentée (`run_era_metab`) + `main()` + smoke opt-in

**Files:**
- Modify: `tools/metabolic_cost_sweep.py`
- Test: `tests/sandbox/test_metabolic_cost_sweep.py`

**Interfaces:**
- Consumes: `run_sweep` (Task 2) ; `Biosphere3D`, `MambaAgent`, `calculate_life_score`, `WorldConfig`, `Harness`, `async_logger`.
- Produces:
  - `run_era_metab(cfg, genomes, max_ticks=400) -> (scored, metrics)` — défaut runner de `run_lineage`.
  - `main()` — params par env, lance `run_sweep`, `Harness.save`, log verdict.

- [ ] **Step 1: Write the smoke test (opt-in, ne tourne pas en CI normale)**

Ajouter dans `tests/sandbox/test_metabolic_cost_sweep.py` :

```python
import pytest


@pytest.mark.skipif(os.environ.get("MCS_SMOKE") != "1",
                    reason="smoke lourd (vraie biosphère) — set MCS_SMOKE=1 pour lancer")
def test_run_era_metab_smoke():
    from tools.metabolic_cost_sweep import run_era_metab, _make_cfg
    from src.agents.mamba_agent import MambaAgent
    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        cfg = _make_cfg(0.0)
        genomes = [MambaAgent().genome for _ in range(6)]
        scored, m = run_era_metab(cfg, genomes, max_ticks=30)
        assert m["mean_active"] >= 0.0
        assert m["ticks"] >= 1
        assert isinstance(scored, list)
    finally:
        async_logger.stop()
```

- [ ] **Step 2: Run it to confirm it SKIPS by default**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py::test_run_era_metab_smoke -v`
Expected: SKIPPED (reason: smoke lourd)

- [ ] **Step 3: Implement `run_era_metab` + `main`**

Ajouter dans `tools/metabolic_cost_sweep.py` :

```python
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger


def run_era_metab(cfg, genomes, max_ticks: int = 400):
    """Mirror de evolve_competence.run_era + accumulation de mean_active (tool-local, 0 changement cœur)."""
    env = Biosphere3D(cfg)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    active_sum = 0.0
    agent_ticks = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
        active_sum += sum(float(getattr(a["model"], "last_activation_cost", 0)) for a in env.agents)
        agent_ticks += len(env.agents)
    mean_active = active_sum / max(agent_ticks, 1)
    pool = env.agents + list(getattr(env, "dead_agents", []))
    ranked = sorted(pool, key=calculate_life_score, reverse=True)
    best_score = float(calculate_life_score(ranked[0])) if ranked else 0.0
    scored = []
    for ag in ranked[:5]:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is not None:
            scored.append((float(calculate_life_score(ag)), g))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return scored, {"ticks": float(t), "score": best_score, "mean_active": mean_active}


def main():
    seeds = [int(s) for s in os.environ.get("MCS_SEEDS", "0,1,2").split(",") if s.strip()]
    coefs = [float(c) for c in os.environ.get("MCS_SWEEP", "0,0.001,0.003,0.01").split(",") if c.strip()]
    eras = int(os.environ.get("MCS_ERAS", "15"))
    num_agents = int(os.environ.get("MCS_NUM_AGENTS", "30"))
    max_ticks = int(os.environ.get("MCS_TICKS", "400"))
    log.info("MetabolicCostSweep : seeds=%s coefs=%s eras=%d (cout estime ~%d lignees)",
             seeds, coefs, eras, len(seeds) * len(set([0.0] + coefs)))
    async_logger.start()
    try:
        result = run_sweep(seeds, coefs, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    finally:
        async_logger.stop()
    h = Harness(seed=min(seeds) if seeds else 0, name="metabolic_cost_sweep",
                with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    for c in result["per_coef"]:
        log.info("coef=%.4g -> %s (median_eff=%.3f, n_fav=%d/%d, sign_p=%.3f, collapsed=%s)",
                 c["coef"], c["verdict"], c["median_eff"], c["n_favorable"], c["n"],
                 c["sign_p"], c["collapsed"])
    log.info("saved -> %s", path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 4: Run the smoke test for real (proves the real engine path works)**

Run: `MCS_SMOKE=1 python -m pytest tests/sandbox/test_metabolic_cost_sweep.py::test_run_era_metab_smoke -v`
Expected: PASS (1 test) — confirme que `run_era_metab` tourne sur la vraie biosphère et que `mean_active` est calculé.

- [ ] **Step 5: Run full test file (default, smoke skipped)**

Run: `python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -v`
Expected: 8 passed, 1 skipped

- [ ] **Step 6: Commit**

```bash
git add tools/metabolic_cost_sweep.py tests/sandbox/test_metabolic_cost_sweep.py
git commit -m "feat(NAS-D1-measure): run_era_metab instrumente + main (env params + Harness.save)"
```

---

## Self-Review

**1. Spec coverage :**
- Spec §3.1 verdict pur → Task 1. ✓
- Spec §3.2 `run_lineage` + §3.4 `run_sweep` (runner injectable) → Task 2. ✓
- Spec §3.3 `run_era_metab` (accumulation mean_active, stop memory_retriever) + §3.4 `main` (env, Harness.save) → Task 3. ✓
- Spec §2 banc sweet-spot (0.25/3.0) → `_make_cfg` (Task 2). ✓
- Spec §4 KPIs (competence=life_score, survival=ticks, mean_active, efficiency) → `run_era_metab` + `run_lineage`. ✓
- Spec §5 params env + log coût → `main` (Task 3). ✓
- Spec §6 tests 1-4 (purs + injectés) → Task 1+2 ; test 5 (smoke opt-in) → Task 3. ✓
- Spec Global "0 changement cœur" → toutes les tâches ne touchent que `tools/` + `tests/`. ✓

**2. Placeholder scan :** aucun TBD ; tout le code est complet.

**3. Type consistency :** `run_era_fn(cfg, genomes, max_ticks) -> (scored, metrics{"ticks","score","mean_active"})` identique entre le faux runner (Task 2 test), `run_lineage` (Task 2), et `run_era_metab` (Task 3). `compute_sweep_verdict` entrée/sortie identiques Task 1 ↔ usage Task 2. `_make_cfg` défini Task 2, réutilisé Task 3 (smoke). ✓

## Validation finale (post-implémentation)
```bash
python -m pytest tests/sandbox/test_metabolic_cost_sweep.py -v          # 8 passed, 1 skipped
MCS_SMOKE=1 python -m pytest tests/sandbox/test_metabolic_cost_sweep.py::test_run_era_metab_smoke -v   # 1 passed
```
Puis (hors plan, compute) : lancer `MCS_SEEDS=... MCS_ERAS=... python tools/metabolic_cost_sweep.py` à l'échelle → verdict EFFICACE/NEUTRE/NUIT par coef → EDR de conclusion sur D1.
