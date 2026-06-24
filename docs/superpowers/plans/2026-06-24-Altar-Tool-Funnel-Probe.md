# Sonde funnel autel/outil (barreau 0 EDR 014) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnostiquer le goulot couche-2 (EDR 014) sur stoneage au sweet spot : confirmer empiriquement que l'autel est mort + mesurer le funnel outil (craft→usage mammouth) sur tous les agents → deux verdicts décomposés.

**Architecture:** Sonde pure-lecture `tools/altar_tool_funnel_probe.py` (AUCUNE modif de `src/`). Moule des sondes précédentes : helper PUR `funnel_verdict` + era-runner `run_era_funnel` (modelé sur `run_era_organ` SANS semis d'organe) + `main` provenance.

**Tech Stack:** Python 3.13, numpy non requis, pytest. Réutilise `WorldConfig`, `SeedManager`, `Harness`, `async_logger`, `MambaAgent`, `init_primordial_soup`, `_prepare_world`, `_acquire_shared_db`.

## Global Constraints

- **AUCUNE modification de `src/`** : sonde pure-lecture.
- **Tous les agents** (vivants + morts, `env.agents + env.dead_agents`, EDR 092) — la population s'éteint à 100 %.
- **Fractions, pas médianes** (craft/mammouth = événements rares, EDR 094).
- **Champs d'agent réels** (`world_1_stoneage.py:336-339`) : `preys_eaten`, `mammoth_kills`, `altars_solved` (jamais incrémenté), `spears_crafted`. Les agents stoneage sont des **dicts** → `a.get("spears_crafted", 0)`.
- **Sweet spot fixe** : `metab=0.25`, `payoff=3.0`.
- **Quiet-log** : `os.environ["AGISEED_QUIET_LOG"]="1"` dans `main()` AVANT `async_logger.start()`. Pour le run réel : passer `AGISEED_QUIET_LOG=1` AUSSI dans le shell (le singleton `async_logger` lit la variable à l'import — leçon de vitesse).
- **Fuite d'env (EDR 093)** : test de provenance → `monkeypatch.setenv("AGISEED_QUIET_LOG","0")` AVANT `main()`.
- **Tree partagé** : commits **pathspec-limités** `git commit <paths> -m "..."` (jamais `git add -A`/`.`/`git commit -m` sans pathspec). Branche `feat/d1-prod-pairing`.
- **Fichiers** : `tools/altar_tool_funnel_probe.py` + `tests/sandbox/test_altar_tool_funnel_probe.py`.

---

## File Structure

- **Create** `tools/altar_tool_funnel_probe.py` — sonde (imports + `funnel_verdict` + `run_era_funnel` + `main`).
- **Create** `tests/sandbox/test_altar_tool_funnel_probe.py` — tests (verdict pur + smoke slow + provenance).

---

### Task 1: Helper pur `funnel_verdict`

**Files:**
- Create: `tools/altar_tool_funnel_probe.py`
- Test: `tests/sandbox/test_altar_tool_funnel_probe.py`

**Interfaces:**
- Produces: `funnel_verdict(per_seed_agents: dict, eps: float = 0.02) -> dict` avec clés
  `verdict_autel` ∈ {`AUTEL_MORT`,`AUTEL_VIVANT`}, `verdict_funnel` ∈ {`GAP_ACQUISITION`,`GAP_USAGE`,`PATHWAY_VIVANT`},
  `frac_hunt`, `frac_craft`, `frac_apex`, `total_spears`, `total_mammoth_kills`, `altars_solved_max`,
  `n_agents`, `par_seed`. `per_seed_agents` = `{seed: [ {preys_eaten, spears_crafted, mammoth_kills, altars_solved, age}, ... ]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_altar_tool_funnel_probe.py
from tools.altar_tool_funnel_probe import funnel_verdict


def _ag(preys=0, spears=0, mammoth=0, altars=0, age=10):
    return {"preys_eaten": preys, "spears_crafted": spears, "mammoth_kills": mammoth,
            "altars_solved": altars, "age": age}


def test_funnel_gap_acquisition_when_no_craft():
    # 5 agents chassent mais aucun ne crafte -> frac_craft=0 < eps
    per_seed = {0: [_ag(preys=3) for _ in range(5)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "GAP_ACQUISITION"
    assert v["verdict_autel"] == "AUTEL_MORT"
    assert v["frac_hunt"] == 1.0 and v["frac_craft"] == 0.0 and v["frac_apex"] == 0.0


def test_funnel_gap_usage_when_craft_but_no_mammoth():
    # 5 agents craftent (frac_craft=1.0) mais aucun ne tue le mammouth
    per_seed = {0: [_ag(preys=3, spears=2) for _ in range(5)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "GAP_USAGE"
    assert v["frac_craft"] == 1.0 and v["frac_apex"] == 0.0
    assert v["total_spears"] == 10


def test_funnel_pathway_vivant_when_mammoth_killed():
    # au moins un agent tue le mammouth -> frac_apex > eps
    per_seed = {0: [_ag(preys=3, spears=2, mammoth=1)] + [_ag(preys=1) for _ in range(4)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "PATHWAY_VIVANT"
    assert v["frac_apex"] == 0.2 and v["total_mammoth_kills"] == 1


def test_autel_vivant_when_any_solved():
    per_seed = {0: [_ag(altars=1)] + [_ag() for _ in range(4)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_autel"] == "AUTEL_VIVANT" and v["altars_solved_max"] == 1


def test_funnel_empty_no_crash():
    v = funnel_verdict({})
    assert v["n_agents"] == 0 and v["verdict_autel"] == "AUTEL_MORT"
    assert v["verdict_funnel"] == "GAP_ACQUISITION" and v["par_seed"] == {}


def test_par_seed_carries_decomposition():
    per_seed = {0: [_ag(preys=2, spears=1)], 1: [_ag(preys=2, mammoth=1, spears=1)]}
    v = funnel_verdict(per_seed)
    assert set(v["par_seed"]) == {"0", "1"}
    assert v["par_seed"]["1"]["frac_apex"] == 1.0 and v["par_seed"]["0"]["frac_apex"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_altar_tool_funnel_probe.py -q -p no:cacheprovider`
Expected: FAIL (cannot import `funnel_verdict`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/altar_tool_funnel_probe.py
"""Sonde funnel autel/outil (barreau 0 de l'EDR 014). Au sweet spot sur stoneage : l'autel est-il
structurellement mort (altars_solved jamais >0) et où les agents décrochent-ils dans le pathway outil
(craft -> usage mammouth) ? Observationnel, pure-lecture des champs d'agent (vivants+morts, EDR 092).
Spec : docs/superpowers/specs/2026-06-24-Altar-Tool-Funnel-Probe-design.md."""
import os
import sys
import logging
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.AltarToolFunnel")


def _frac(agents: List[Dict], key: str) -> float:
    """Fraction des agents avec champ `key` >= 1 (rare-event-aware). Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if a.get(key, 0) >= 1) / len(agents)


def _seed_summary(agents: List[Dict]) -> Dict:
    return {"n": len(agents),
            "frac_hunt": _frac(agents, "preys_eaten"),
            "frac_craft": _frac(agents, "spears_crafted"),
            "frac_apex": _frac(agents, "mammoth_kills"),
            "total_spears": sum(a.get("spears_crafted", 0) for a in agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in agents),
            "altars_solved_max": max((a.get("altars_solved", 0) for a in agents), default=0)}


def funnel_verdict(per_seed_agents: Dict, eps: float = 0.02) -> Dict:
    """Verdicts décomposés (autel + funnel outil) sur TOUS les agents poolés, fractions (pas médianes).
    Le verdict funnel localise le 1er étage qui s'effondre sous eps. par_seed = courbe complète."""
    all_agents = [a for agents in per_seed_agents.values() for a in agents]
    frac_hunt = _frac(all_agents, "preys_eaten")
    frac_craft = _frac(all_agents, "spears_crafted")
    frac_apex = _frac(all_agents, "mammoth_kills")
    altars_solved_max = max((a.get("altars_solved", 0) for a in all_agents), default=0)
    verdict_autel = "AUTEL_MORT" if altars_solved_max == 0 else "AUTEL_VIVANT"
    if frac_craft < eps:
        verdict_funnel = "GAP_ACQUISITION"
    elif frac_apex < eps:
        verdict_funnel = "GAP_USAGE"
    else:
        verdict_funnel = "PATHWAY_VIVANT"
    return {"verdict_autel": verdict_autel, "verdict_funnel": verdict_funnel,
            "frac_hunt": frac_hunt, "frac_craft": frac_craft, "frac_apex": frac_apex,
            "total_spears": sum(a.get("spears_crafted", 0) for a in all_agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in all_agents),
            "altars_solved_max": altars_solved_max, "n_agents": len(all_agents),
            "par_seed": {str(s): _seed_summary(agents) for s, agents in per_seed_agents.items()}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_altar_tool_funnel_probe.py -q -p no:cacheprovider`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git commit tools/altar_tool_funnel_probe.py tests/sandbox/test_altar_tool_funnel_probe.py -m "feat(funnel): funnel_verdict pur (autel mort + funnel outil decompose, EDR 014)"
```

---

### Task 2: Era-runner `run_era_funnel`

**Files:**
- Modify: `tools/altar_tool_funnel_probe.py`
- Test: `tests/sandbox/test_altar_tool_funnel_probe.py` (smoke, `slow`)

**Interfaces:**
- Consumes: `WorldConfig`, `SeedManager`, `MambaAgent`, `init_primordial_soup`, `_prepare_world` (déjà importés Task 1).
- Produces: `run_era_funnel(seed, metab, payoff, num_agents, max_ticks, shared_db) -> List[Dict]` renvoyant par agent `{age, preys_eaten, spears_crafted, mammoth_kills, altars_solved}` (vivants + morts).

- [ ] **Step 1: Write the implementation (append au module, après `funnel_verdict`)**

```python
def run_era_funnel(seed, metab, payoff, num_agents, max_ticks, shared_db) -> List[Dict]:
    """UNE ère stoneage (sweet spot). Renvoie par agent TOUS (vivants + morts, env.agents +
    env.dead_agents, EDR 092) : {age, preys_eaten, spears_crafted, mammoth_kills, altars_solved}.
    Modelé sur run_era_organ (tools/dreaming_probe.py) mais SANS semis d'organe. Déterministe."""
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world("stoneage", config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=50.0)

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    all_agents = list(env.agents) + list(getattr(env, "dead_agents", []))
    out = [{"age": a.get("age", 0), "preys_eaten": a.get("preys_eaten", 0),
            "spears_crafted": a.get("spears_crafted", 0), "mammoth_kills": a.get("mammoth_kills", 0),
            "altars_solved": a.get("altars_solved", 0)} for a in all_agents]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out
```

- [ ] **Step 2: Write the smoke test (append au fichier de test)**

```python
import pytest


@pytest.mark.slow
def test_run_era_funnel_smoke_all_agents_altar_dead(monkeypatch):
    """Smoke biosphère : 1 seed, ticks courts. Vérifie les 5 champs, la couverture vivants+morts,
    ET que l'autel est mort en conditions réelles (altars_solved jamais >0)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.altar_tool_funnel_probe import run_era_funnel
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        agents = run_era_funnel(0, 0.25, 3.0, num_agents=20, max_ticks=40, shared_db=db)
    finally:
        async_logger.stop()
    assert len(agents) >= 1
    a0 = agents[0]
    assert set(a0) == {"age", "preys_eaten", "spears_crafted", "mammoth_kills", "altars_solved"}
    assert max(a["altars_solved"] for a in agents) == 0   # autel mort, confirmé empiriquement
```

- [ ] **Step 3: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_altar_tool_funnel_probe.py::test_run_era_funnel_smoke_all_agents_altar_dead -q -p no:cacheprovider`
Expected: PASS (~10-40 s).

- [ ] **Step 4: Commit**

```bash
git commit tools/altar_tool_funnel_probe.py tests/sandbox/test_altar_tool_funnel_probe.py -m "feat(funnel): run_era_funnel (ere stoneage, tous agents, sans organe)"
```

---

### Task 3: `main()` + provenance

**Files:**
- Modify: `tools/altar_tool_funnel_probe.py`
- Test: `tests/sandbox/test_altar_tool_funnel_probe.py` (provenance via monkeypatch)

**Interfaces:**
- Consumes: `run_era_funnel`, `funnel_verdict`, `Harness`, `async_logger`, `_acquire_shared_db`, `WorldConfig`.
- Produces: `main() -> Dict`.

- [ ] **Step 1: Write the implementation (append au module)**

```python
def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse, AVANT start()
    seeds = [int(s) for s in os.environ.get("AF_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("AF_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("AF_MAX_TICKS", "300"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde funnel autel/outil : seeds=%s agents=%d ticks=%d (sweet 0.25/3.0) ===",
                 seeds, num_agents, max_ticks)
        per_seed = {seed: run_era_funnel(seed, 0.25, 3.0, num_agents, max_ticks, shared_db)
                    for seed in seeds}
        result = funnel_verdict(per_seed)
    finally:
        async_logger.stop()

    result["config"] = {"seeds": [int(s) for s in seeds], "num_agents": num_agents,
                        "max_ticks": max_ticks, "metab": 0.25, "payoff": 3.0}
    h = Harness(seed=min(seeds) if seeds else 0, name="altar_tool_funnel", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT autel=%s funnel=%s | hunt=%.3f craft=%.3f apex=%.3f | spears=%d mammoth=%d altar_max=%d -> %s",
             result["verdict_autel"], result["verdict_funnel"], result["frac_hunt"],
             result["frac_craft"], result["frac_apex"], result["total_spears"],
             result["total_mammoth_kills"], result["altars_solved_max"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 2: Write the provenance test (append au fichier de test, sans biosphère)**

```python
import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.altar_tool_funnel_probe as af
    monkeypatch.setattr(af, "run_era_funnel",
                        lambda *a, **k: [{"age": 12, "preys_eaten": 2, "spears_crafted": 1,
                                          "mammoth_kills": 0, "altars_solved": 0}])
    monkeypatch.setattr(af.async_logger, "start", lambda: None)
    monkeypatch.setattr(af.async_logger, "stop", lambda: None)
    monkeypatch.setattr(af, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("AF_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = af.main()
    assert result["verdict_funnel"] == "GAP_USAGE"      # craft=1.0, apex=0.0
    assert result["verdict_autel"] == "AUTEL_MORT"
    files = glob.glob(str(tmp_path / "results" / "altar_tool_funnel_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict_funnel"] == "GAP_USAGE"
    assert "commit" in data and "git_dirty" in data
```

- [ ] **Step 3: Run all non-slow tests + anti-fuite combiné**

Run: `python -m pytest tests/sandbox/test_altar_tool_funnel_probe.py tests/sandbox/test_async_logger.py -q -p no:cacheprovider -m "not slow"`
Expected: PASS (funnel_verdict x6 + provenance + tests async_logger ; `test_quiet_mode_off_by_default` ne doit PAS échouer → preuve d'isolation de la fuite d'env).

- [ ] **Step 4: Commit**

```bash
git commit tools/altar_tool_funnel_probe.py tests/sandbox/test_altar_tool_funnel_probe.py -m "feat(funnel): main + provenance (sonde funnel complete)"
```

---

### Task 4: Run réel + interprétation (pas de code)

**Files:** aucun (exécution + lecture).

- [ ] **Step 1: Lancer la sonde (stoneage, sweet spot, 8 seeds)**

Run: `AGISEED_QUIET_LOG=1 AF_SEEDS=0,1,2,3,4,5,6,7 AF_NUM_AGENTS=40 AF_MAX_TICKS=300 python -u tools/altar_tool_funnel_probe.py`
Expected: une ligne `VERDICT autel=... funnel=... | hunt=... craft=... apex=...` + un JSON dans `results/altar_tool_funnel_0.json`.
(NB : `AGISEED_QUIET_LOG=1` dans le shell AUSSI — le singleton async_logger lit la variable à l'import ; sans ça le run est ~10× plus lent.)

- [ ] **Step 2: Lire les deux verdicts + la courbe par seed et conclure**

- **`AUTEL_MORT`** (attendu) → acter l'**artefact métrique** : `stoneage_competence` pondère `altars_solved` (≡0) à 0.6 (`src/curriculum/competence.py:45-58`) → la couche-2 mesure du vide. Décider : implémenter la résolution d'autel sur stoneage, OU re-pondérer la couche-2 sur un signal vivant (`spears_crafted`/`mammoth_kills`).
- **`GAP_ACQUISITION`** (frac_craft≈0) → le mur est en amont du craft (récolte rock+stick / action `do_rub`) → levier nouveauté ou scaffold de craft.
- **`GAP_USAGE`** (craft OK, frac_apex≈0) → barreau 1 = intervention gated « force-spear » pour trancher can't-use vs won't-use.
- **`PATHWAY_VIVANT`** (frac_apex>0) → la couche-2 outil n'est PAS le goulot ; le mur EDR 014 est l'autel (structurel) → pivot implémentation/repondération.

Rapporter la **décomposition par seed complète** (`par_seed`), JAMAIS le label nu. Signaler `n_agents` et la rareté (fractions).

- [ ] **Step 3: Écrire l'EDR du résultat** (numéro libre suivant, ex. 096) et committer (pathspec-limité).

---

## Self-Review

**Spec coverage :** `funnel_verdict` (2 verdicts, fractions, par_seed, eps) → Task 1. `run_era_funnel`
(tous agents, sans organe, sweet spot) → Task 2. `main` (knobs AF_*, quiet-log avant start, provenance)
→ Task 3. Confirmation empirique autel mort → Task 2 smoke (`altars_solved_max==0`). Run réel +
interprétation décomposée → Task 4. Garde-fous : tous agents (Task 2), fractions (Task 1), fuite d'env
isolée (Task 3 Step 2), décomposition par_seed rapportée (Task 1/3). ✓

**Placeholder scan :** aucun TODO/TBD ; provenance test utilise `with open(...)` propre. ✓

**Type consistency :** `run_era_funnel` → `list[{age,preys_eaten,spears_crafted,mammoth_kills,altars_solved}]`
→ `funnel_verdict` consomme via `_frac`/`_seed_summary` (clés `preys_eaten`/`spears_crafted`/`mammoth_kills`/`altars_solved`)
✓. `main` construit `per_seed={seed:[agents]}` → `funnel_verdict` ✓. `funnel_verdict` produit
`{verdict_autel,verdict_funnel,frac_*,total_*,altars_solved_max,n_agents,par_seed}` → `main` lit
`verdict_autel/verdict_funnel/frac_*/total_*/altars_solved_max` ✓.
