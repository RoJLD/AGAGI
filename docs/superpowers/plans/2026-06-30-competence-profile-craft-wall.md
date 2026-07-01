# Profil de competence par tier (« mur du craft ») Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer la competence stoneage ventilee par tier {forage/craft/apex} sur une cohorte fixe et trancher un verdict gele « mur du craft » (echelle inversee : apex >= craft), au lieu d'ecraser sur le scalaire `life_score`.

**Architecture:** Tooling pur. Nouveau `tools/competence_profile.py` qui REUTILISE (imports) les helpers stoneage de `tools/map_elites_compare.py` (`_make_cfg`/`_seed_genome`/`_reproduce`/`run_era_pool`/`PRESERVE_DIMS`) et `_frac_reaching` de `src/curriculum/competence.py`. Deux phases : evoluer des champions (repro ON) puis mesurer leur profil par tier sur cohorte FIXE (`benchmark_mode=True`). Aucun `src/` modifie.

**Tech Stack:** Python, numpy. Reutilise `Biosphere3D` (stoneage), `Harness`/`SeedManager`, `async_logger`.

## Global Constraints

- **Zero fichier partage** : SEULS `tools/competence_profile.py` (nouveau) + tests + doc sont crees. AUCUN `src/` modifie, AUCUN fichier de la session // (`world_famine.py`, `backend_torch.py`, `torch_batch_model.py`, `substrate_ab*.py`). `map_elites_compare.py` et `competence.py` sont IMPORTES seulement. `git diff src/` doit rester VIDE.
- **Cohorte fixe (EDR 114b)** : la mesure du profil pose `env.benchmark_mode = True` -> pas de reproduction -> pool = cohorte initiale, pas de dilution par nouveau-nes tardifs.
- **Repro memory (P0)** : `_measure_profile` fait `stop()` + `clear()` du `memory_retriever` AVANT la boucle sim (pas apres, contrairement a `run_era_pool`).
- **ASCII-only dans tout `print` execute** (Windows cp1252) : `->` ASCII OK, pas de fleche/accent unicode.
- **Provenance** : `Harness(name="competence_profile")` -> JSON distinct ; seed reel 1240, smoke 99240 distinct. Run reel APRES revue ; AUCUN test relance apres.
- **Verdict gele** : `INDETERMINE` si `frac_forage < 0.10` ; sinon `CRAFT_WALL CONFIRME` si `frac_craft < frac_forage` ET `frac_apex >= frac_craft` ET `frac_craft <= 0.10` ; sinon `ECHELLE MONOTONE`. Fractions = `_frac_reaching` (binaire par agent, seuil >=1).

---

### Task 1: logique pure — fractions par tier + verdict + report

**Files:**
- Create: `tools/competence_profile.py` (entete + imports + fonctions pures)
- Test: `tests/sandbox/test_competence_profile.py` (creer)

**Interfaces:**
- Consumes: `_frac_reaching(agent_stats, key, threshold=1.0)` (`src/curriculum/competence.py:22`) ; `Harness` (`src.seed_ai.harness`) ; `WorldConfig` ; `np`.
- Produces:
  - `_tier_fractions(stats_list) -> dict` (cles `frac_forage`, `frac_craft`, `frac_apex`, `n`).
  - `_verdict_craft_wall(fracs) -> str`.
  - `_report_profile(h, per_seed, R, _return) -> dict|None`.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_competence_profile.py` :

```python
from tools.competence_profile import _tier_fractions, _verdict_craft_wall


def test_tier_fractions_binary_per_agent():
    stats = [
        {"preys_eaten": 3, "spears_crafted": 0, "mammoth_kills": 1},
        {"preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0},
        {"preys_eaten": 0, "spears_crafted": 1, "mammoth_kills": 0},
        {"preys_eaten": 0, "spears_crafted": 0, "mammoth_kills": 0},
    ]
    f = _tier_fractions(stats)
    assert f["frac_forage"] == 0.5   # 2/4 ont preys_eaten >= 1
    assert f["frac_craft"] == 0.25   # 1/4
    assert f["frac_apex"] == 0.25    # 1/4
    assert f["n"] == 4


def test_verdict_craft_wall_branches():
    confirme = {"frac_forage": 0.80, "frac_craft": 0.02, "frac_apex": 0.22}
    assert _verdict_craft_wall(confirme) == "CRAFT_WALL CONFIRME"
    monotone = {"frac_forage": 0.80, "frac_craft": 0.30, "frac_apex": 0.10}  # apex < craft
    assert _verdict_craft_wall(monotone) == "ECHELLE MONOTONE"
    indet = {"frac_forage": 0.05, "frac_craft": 0.0, "frac_apex": 0.0}
    assert _verdict_craft_wall(indet) == "INDETERMINE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_competence_profile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.competence_profile'`.

- [ ] **Step 3: Create `tools/competence_profile.py` with header, imports, and pure functions**

Creer `tools/competence_profile.py` :

```python
"""tools/competence_profile.py — Profil de competence par tier (P3a audit memoire).

Mesure la competence stoneage ventilee par tier {forage/craft/apex} sur une COHORTE FIXE (benchmark_mode,
EDR 114b) au lieu d'ecraser sur le scalaire life_score. Tranche le verdict gele « mur du craft » :
l'echelle moyens->ends {survie<forage<craft<apex} s'inverse-t-elle au craft (apex atteint PLUS que la
lance -> pathway outil quasi-mort, poids spears de life_score inerte) ? Indices code (competence.py:66 :
apex 21.7% / lance 1.6%) ; ici on le MESURE proprement et on PRE-ENREGISTRE le verdict.

Tooling pur (pas de src/ modifie ; map_elites_compare/competence importes). Usage : python -m tools.competence_profile
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.curriculum.competence import _frac_reaching
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool, PRESERVE_DIMS


def _tier_fractions(stats_list):
    """Fractions « a deja atteint » par tier (binaire par agent, _frac_reaching seuil >=1)."""
    return {"frac_forage": _frac_reaching(stats_list, "preys_eaten"),
            "frac_craft": _frac_reaching(stats_list, "spears_crafted"),
            "frac_apex": _frac_reaching(stats_list, "mammoth_kills"),
            "n": len(stats_list)}


def _verdict_craft_wall(fracs):
    """INDETERMINE si forage < 0.10 (cohorte trop incompetente) ; CRAFT_WALL CONFIRME si craft < forage
    ET apex >= craft (echelle inversee) ET craft <= 0.10 (quasi-mort) ; sinon ECHELLE MONOTONE."""
    ff, fc, fa = fracs["frac_forage"], fracs["frac_craft"], fracs["frac_apex"]
    if ff < 0.10:
        return "INDETERMINE"
    if fc < ff and fa >= fc and fc <= 0.10:
        return "CRAFT_WALL CONFIRME"
    return "ECHELLE MONOTONE"


def _report_profile(h, per_seed, R, _return):
    """Table ASCII (1 ligne/seed : forage, craft, apex, n) + moyenne + verdict. Save JSON."""
    keys = ("frac_forage", "frac_craft", "frac_apex")
    fracs = {k: float(np.mean([p[k] for p in per_seed])) for k in keys}
    verdict = _verdict_craft_wall(fracs)
    print("\n=== Profil de competence par tier (cohorte fixe) ===")
    print("  seed | forage  craft   apex  |   n")
    for p in per_seed:
        print(f"  {p['seed']:4d} | {p['frac_forage']:6.3f} {p['frac_craft']:6.3f} {p['frac_apex']:6.3f} | {p['n']:4d}")
    print(f"  MOYEN| {fracs['frac_forage']:6.3f} {fracs['frac_craft']:6.3f} {fracs['frac_apex']:6.3f}")
    print("=== VERDICT (mur du craft) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed, "R": R}
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/sandbox/test_competence_profile.py -v`
Expected: PASS (2/2).

- [ ] **Step 5: Commit**

```bash
git add tools/competence_profile.py tests/sandbox/test_competence_profile.py
git commit -m "feat(tooling): profil competence par tier -- fractions + verdict mur du craft (logique pure)"
```

---

### Task 2: mesure cohorte fixe + evolution + entry point

**Files:**
- Modify: `tools/competence_profile.py` (ajouter 3 fonctions apres `_report_profile`)
- Test: `tests/sandbox/test_competence_profile.py` (ajouter 2 tests)

**Interfaces:**
- Consumes: `_make_cfg`/`_seed_genome`/`_reproduce`/`run_era_pool`/`PRESERVE_DIMS` (`tools/map_elites_compare.py`) ; `_tier_fractions`/`_report_profile` (Task 1) ; `Biosphere3D`, `MambaAgent`, `SeedManager`, `Harness`, `WorldConfig`, `async_logger`.
- Produces:
  - `_measure_profile(cfg, genomes, max_ticks=400, disable_repro=True) -> list[dict]`.
  - `_evolve_champions(seed, eras=12, num_agents=30, max_ticks=400) -> list` (genomes top-5).
  - `main_competence_profile(R=3, eras=12, num_agents=30, max_ticks=400, seed=1240, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_competence_profile.py` :

```python
def test_measure_profile_fixed_cohort_no_repro():
    # benchmark_mode -> pas de reproduction -> pool = cohorte initiale (pas d'explosion) + cles presentes.
    from tools.competence_profile import _measure_profile
    from tools.map_elites_compare import _make_cfg
    from src.agents.mamba_agent import MambaAgent
    genomes = [MambaAgent().genome for _ in range(3)]
    stats = _measure_profile(_make_cfg(), genomes, max_ticks=40, disable_repro=True)
    assert len(stats) == 3, "cohorte fixe : pas de naissances (pool = genomes initiaux)"
    assert all(k in stats[0] for k in ("age", "preys_eaten", "spears_crafted", "mammoth_kills"))


def test_main_competence_profile_smoke():
    from tools.competence_profile import main_competence_profile
    r = main_competence_profile(R=1, eras=2, num_agents=10, max_ticks=80, seed=99240, _return=True)
    assert r["verdict"] in ("CRAFT_WALL CONFIRME", "ECHELLE MONOTONE", "INDETERMINE")
    assert len(r["per_seed"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_competence_profile.py -v`
Expected: FAIL — `ImportError: cannot import name '_measure_profile'` / `main_competence_profile`.

- [ ] **Step 3: Add the sim-touching functions to `tools/competence_profile.py`**

Ajouter APRES `_report_profile` dans `tools/competence_profile.py` :

```python
def _measure_profile(cfg, genomes, max_ticks=400, disable_repro=True):
    """Mesure profil sur COHORTE FIXE. Mirror run_era_pool MAIS : benchmark_mode si disable_repro (pas
    de repro -> pas de dilution pooling, EDR 114b) ; memory_retriever stop()+clear() AVANT la boucle
    (repro, P0) ; renvoie la liste des stats par agent {age, preys_eaten, spears_crafted, mammoth_kills}."""
    env = Biosphere3D(cfg)
    if disable_repro:
        env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool_agents = env.agents + list(getattr(env, "dead_agents", []))
    return [{"age": ag.get("age", 0), "preys_eaten": ag.get("preys_eaten", 0),
             "spears_crafted": ag.get("spears_crafted", 0), "mammoth_kills": ag.get("mammoth_kills", 0)}
            for ag in pool_agents]


def _evolve_champions(seed, eras=12, num_agents=30, max_ticks=400):
    """Cliquet top-5 (boucle de run_lineage_hof, repro ON) -> renvoie les genomes best_ever (top-5)."""
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    best_ever = [(0.0, g) for g in [_seed_genome(i) for i in range(5)]]
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, _m = run_era_pool(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
    return [g for _s, g in best_ever]


def main_competence_profile(R=3, eras=12, num_agents=30, max_ticks=400, seed=1240, _return=False):
    """Pour chaque seed base+r : evolue des champions stoneage (repro ON) puis mesure leur profil par
    tier sur cohorte fixe (benchmark_mode). Agrege R seeds, verdict mur du craft."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
            stats = _measure_profile(_make_cfg(), reps, max_ticks=max_ticks, disable_repro=True)
            per_seed.append({**_tier_fractions(stats), "seed": int(s)})
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="competence_profile", with_db=False, config=WorldConfig())
    return _report_profile(h, per_seed, R, _return)


if __name__ == "__main__":
    main_competence_profile()
```

- [ ] **Step 4: Run the full test file**

Run: `python -m pytest tests/sandbox/test_competence_profile.py -v`
Expected: PASS (4/4). Les 2 tests sim (`_measure_profile`, smoke) tournent de vrais episodes stoneage courts -> un peu lents mais courts.

- [ ] **Step 5: Confirm zero src/ change**

Run: `git status --short src/`
Expected: vide (aucun fichier src/ modifie).

- [ ] **Step 6: Commit**

```bash
git add tools/competence_profile.py tests/sandbox/test_competence_profile.py
git commit -m "feat(tooling): mesure cohorte fixe + evolution champions + main_competence_profile (mur du craft)"
```

---

## Self-Review

**Spec coverage** : Task 1 = `_tier_fractions`/`_verdict_craft_wall`/`_report_profile` (spec §4.3-4.5 + verdict §4.4) ; Task 2 = `_measure_profile` (§4.2, cohorte fixe + P0) / `_evolve_champions` (§4.1) / `main_competence_profile` (§4.6) + smoke (§7.4). Le run reel + doc EDR (§9) sont hors-plan (controleur APRES revue, comme P1). Couvert.

**Placeholders** : aucun — code complet a chaque step.

**Type consistency** : `_tier_fractions` renvoie `{frac_forage, frac_craft, frac_apex, n}` consomme par `_verdict_craft_wall` (lit frac_forage/craft/apex) et `_report_profile` (moyenne sur ces 3 cles). `_measure_profile` renvoie une liste de dicts avec `preys_eaten/spears_crafted/mammoth_kills` consommee par `_tier_fractions` via `_frac_reaching`. `main_competence_profile` ajoute `seed` a chaque entree per_seed, lu par `_report_profile`. Coherent.
