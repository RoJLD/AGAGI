# ToM comportementale (coordination vs indépendance) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un banc tooling read-only `tools/tom_coordination.py` qui mesure si la chasse coop au mammouth est COORDONNÉE (l'agent conditionne son attaque à la présence d'autres) ou INDÉPENDANTE.

**Architecture:** Un seul bras (coop = comportement par défaut). Champions évolués, mesurés sur cohorte fixe ; pour chaque agent proche d'un mammouth frais, on enregistre {attaque?, nb d'autres proches} ; on compare P(attaque|autres) vs P(attaque|seul). Réutilise par imports — zéro `src/`.

**Tech Stack:** Python 3, numpy. Réutilise `tools/competence_profile.py` (`_evolve_champions`) + `tools/map_elites_compare.py` (`_make_cfg`, `PRESERVE_DIMS`) + lecture `Biosphere3D`.

## Global Constraints

- TOOLING pur READ-ONLY : `git diff <merge-base> HEAD -- src/` VIDE. Ne modifie NI `src/` NI substrate_ab/torch/famine/gate-mlp/cross_world_transfer (session //).
- Tout `print` exécuté est **ASCII-only** (cp1252). Accents seulement dans docstrings/commentaires.
- Réutilise par IMPORT (zéro modif) : `_evolve_champions` (competence_profile) ; `_make_cfg`, `PRESERVE_DIMS` (map_elites_compare).
- Verdict gelé : `COORDINATED` si `delta >= 0.10` ; `INDETERMINE` si `n_with < 20` ou `n_alone < 20` ; sinon `INDEPENDENT`. Seuils NON modifiables.
- Pairing/mesure : attaque = `manhattan(agent, mammouth) == 0` ; proche = `<= 2` ; mammouth FRAIS = `hp >= 0.5*mammoth_hp`.
- Seed réel 1300, smoke 99300. Tests `tests/sandbox/test_tom_coordination.py`. Run réel avec `MEC_PRESERVE_DIMS=1`. AUCUN test relancé après le run (EDR 107).

---

### Task 1: Squelette + logique pure (samples + signal + verdict)

**Files:**
- Create: `tools/tom_coordination.py`
- Test: `tests/sandbox/test_tom_coordination.py`

**Interfaces:**
- Produces: `_manhattan(a, m) -> int` ; `_hunt_samples_from_state(agents, preys, mammoth_hp) -> list[dict]` (chaque sample = `{"attacking": bool, "others_near": int}`) ; `_recruitment_signal(samples) -> dict` (`p_with/p_alone/delta/n_with/n_alone`) ; `_verdict_coordination(sig) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_tom_coordination.py
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.tom_coordination import (
    _hunt_samples_from_state,
    _recruitment_signal,
    _verdict_coordination,
)


def test_hunt_samples_fresh_mammoth_only_near_agents():
    preys = [
        {"type": "Mammouth", "x": 5, "y": 5, "hp": 80.0},   # frais (>= 50)
        {"type": "Mammouth", "x": 0, "y": 0, "hp": 10.0},   # agonie -> ignore
        {"type": "Lapin", "x": 5, "y": 5, "hp": 1.0},        # pas mammouth -> ignore
    ]
    agents = [
        {"x": 5, "y": 5},    # A sur le mammouth frais (attacking)
        {"x": 5, "y": 6},    # B a dist 1
        {"x": 15, "y": 15},  # C loin -> exclu
        {"x": 0, "y": 0},    # D sur l'agonie -> mammouth ignore
    ]
    samples = _hunt_samples_from_state(agents, preys, mammoth_hp=100.0)
    assert len(samples) == 2
    assert sorted(s["attacking"] for s in samples) == [False, True]
    assert all(s["others_near"] == 1 for s in samples)


def test_recruitment_signal_rates():
    samples = [
        {"attacking": True, "others_near": 2},
        {"attacking": False, "others_near": 1},
        {"attacking": True, "others_near": 0},
        {"attacking": False, "others_near": 0},
    ]
    sig = _recruitment_signal(samples)
    assert sig["n_with"] == 2 and sig["n_alone"] == 2
    assert sig["p_with"] == 0.5 and sig["p_alone"] == 0.5
    assert sig["delta"] == 0.0


def test_recruitment_signal_empty_buckets():
    sig = _recruitment_signal([{"attacking": True, "others_near": 3}])
    assert sig["p_alone"] == 0.0 and sig["n_alone"] == 0
    assert sig["p_with"] == 1.0 and sig["n_with"] == 1


def test_verdict_coordination_three_branches():
    assert _verdict_coordination({"delta": 0.15, "n_with": 30, "n_alone": 30}) == "COORDINATED"
    assert _verdict_coordination({"delta": 0.02, "n_with": 30, "n_alone": 30}) == "INDEPENDENT"
    assert _verdict_coordination({"delta": 0.15, "n_with": 5, "n_alone": 30}) == "INDETERMINE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_tom_coordination.py -v`
Expected: FAIL (`ModuleNotFoundError: tools.tom_coordination`).

- [ ] **Step 3: Create the module skeleton + pure functions**

```python
# tools/tom_coordination.py
"""tools/tom_coordination.py — ToM comportementale : la chasse coop est-elle COORDONNEE ? (P4 audit memoire, #2).

Tranche le caveat #2 d'EDR 132 (decode latent = contexte partage vs modelisation). Mecanique (EDR 028) :
attaquer = etre sur la cellule d'une proie (world_1_stoneage:692) ; le mammouth (hp 100) meurt des degats
cumules du pack. Question : parmi les agents proches d'un mammouth FRAIS, la proba d'attaquer est-elle plus
haute quand d'AUTRES agents sont proches (recrutement) ou inchangee (convergence fortuite) ?

Tooling pur READ-ONLY (pas de src/ modifie ; competence_profile/map_elites_compare importes).
Usage : MEC_PRESERVE_DIMS=1 python -m tools.tom_coordination
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS
from tools.competence_profile import _evolve_champions


def _manhattan(a, m):
    return abs(a["x"] - m["x"]) + abs(a["y"] - m["y"])


def _hunt_samples_from_state(agents, preys, mammoth_hp):
    """Pour chaque mammouth FRAIS (hp >= 0.5*mammoth_hp), pour chaque agent a distance Manhattan <= 2 :
    {attacking: dist==0, others_near: nb d'AUTRES agents a <= 2 du mammouth}."""
    samples = []
    thresh = 0.5 * mammoth_hp
    for m in preys:
        if m.get("type") != "Mammouth" or m.get("hp", 0.0) < thresh:
            continue
        near = [a for a in agents if _manhattan(a, m) <= 2]
        for a in near:
            samples.append({"attacking": _manhattan(a, m) == 0, "others_near": len(near) - 1})
    return samples


def _recruitment_signal(samples):
    """p_with = P(attaque | others_near>=1), p_alone = P(attaque | others_near==0), delta = with - alone."""
    with_ = [s for s in samples if s["others_near"] >= 1]
    alone = [s for s in samples if s["others_near"] == 0]

    def _rate(xs):
        return float(np.mean([1.0 if s["attacking"] else 0.0 for s in xs])) if xs else 0.0

    p_with, p_alone = _rate(with_), _rate(alone)
    return {"p_with": p_with, "p_alone": p_alone, "delta": p_with - p_alone,
            "n_with": len(with_), "n_alone": len(alone)}


def _verdict_coordination(sig):
    """INDETERMINE si trop peu d'obs ; COORDINATED si delta >= 0.10 (recrutement) ; sinon INDEPENDENT."""
    if sig["n_with"] < 20 or sig["n_alone"] < 20:
        return "INDETERMINE"
    if sig["delta"] >= 0.10:
        return "COORDINATED"
    return "INDEPENDENT"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_tom_coordination.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Verify zero src/ change**

Run: `git status --short src/` (attendu VIDE) puis `git add tools/tom_coordination.py tests/sandbox/test_tom_coordination.py`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(tom-coord): squelette + samples/signal/verdict recrutement (logique pure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Collecte (env) + report + main

**Files:**
- Modify: `tools/tom_coordination.py` (ajoute fonctions APRÈS `_verdict_coordination`)
- Test: `tests/sandbox/test_tom_coordination.py` (ajoute 1 test smoke)

**Interfaces:**
- Consumes: `_evolve_champions(seed, eras, num_agents, max_ticks) -> list[Genome]` ; `Biosphere3D` (`.benchmark_mode`, `.memory_retriever`, `.add_agent`, `.current_era`, `.step`, `.agents`, `.preys`) ; `MambaAgent().from_genome(g, preserve_dims=PRESERVE_DIMS)` ; `_make_cfg` (`.mammoth_hp`) ; `_hunt_samples_from_state`, `_recruitment_signal`, `_verdict_coordination` (Task 1).
- Produces: `_collect_hunt_decisions(cfg, genomes, max_ticks) -> list[dict]` ; `_report_coordination(h, per_seed, R, _return)` ; `main_tom_coordination(R, eras, num_agents, max_ticks, seed, _return) -> dict|None`.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter a tests/sandbox/test_tom_coordination.py
from tools.tom_coordination import main_tom_coordination


def test_smoke_main_tom_coordination_returns_verdict():
    res = main_tom_coordination(R=1, eras=2, num_agents=16, max_ticks=120, seed=99300, _return=True)
    assert res["verdict"] in {"COORDINATED", "INDEPENDENT", "INDETERMINE"}
    assert len(res["per_seed"]) == 1
    assert set(res["per_seed"][0].keys()) >= {"seed", "delta", "n_with", "n_alone"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_tom_coordination.py -k smoke -v`
Expected: FAIL (ImportError sur `main_tom_coordination`).

- [ ] **Step 3: Implement collection + report + main**

```python
# Ajouter a tools/tom_coordination.py apres _verdict_coordination

def _collect_hunt_decisions(cfg, genomes, max_ticks=400):
    """Cohorte fixe (benchmark_mode + memory neutralisee AVANT boucle, lecons 114b/P0). A chaque tick,
    collecte les samples de chasse (mammouths frais, agents proches). Renvoie tous les samples."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    mammoth_hp = getattr(cfg, "mammoth_hp", 100.0)
    samples = []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        samples += _hunt_samples_from_state(env.agents, env.preys, mammoth_hp)
        t += 1
    return samples


def _report_coordination(h, per_seed, R, _return):
    """Table ASCII (par seed : p_with, p_alone, delta, nW, nA) + moyenne + verdict (delta moyen, garde min n)."""
    delta = float(np.mean([p["delta"] for p in per_seed]))
    p_with = float(np.mean([p["p_with"] for p in per_seed]))
    p_alone = float(np.mean([p["p_alone"] for p in per_seed]))
    n_with = int(min(p["n_with"] for p in per_seed))
    n_alone = int(min(p["n_alone"] for p in per_seed))
    verdict = _verdict_coordination({"delta": delta, "n_with": n_with, "n_alone": n_alone})
    print("\n=== ToM comportementale : chasse coop coordonnee ? (cohorte fixe) ===")
    print("  seed | p_with p_alone  delta   nW    nA")
    for p in per_seed:
        print(f"  {p['seed']:4d} | {p['p_with']:.3f}  {p['p_alone']:.3f}  {p['delta']:+.3f} {p['n_with']:5d} {p['n_alone']:5d}")
    print(f"  MOYEN| {p_with:.3f}  {p_alone:.3f}  {delta:+.3f}")
    print("=== VERDICT (recrutement) ===")
    print(f"  -> {verdict}  (garde min nW={n_with} nA={n_alone})")
    h.save({"R": R, "verdict": verdict, "delta": delta, "p_with": p_with, "p_alone": p_alone,
            "n_with_min": n_with, "n_alone_min": n_alone, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "delta": delta, "p_with": p_with, "p_alone": p_alone,
                "n_with_min": n_with, "n_alone_min": n_alone, "per_seed": per_seed, "R": R}


def main_tom_coordination(R=3, eras=12, num_agents=30, max_ticks=400, seed=1300, _return=False):
    """Par seed base+r : evolue des champions (coop par defaut), mesure les decisions de chasse sur cohorte
    fixe, agrege R seeds, verdict recrutement."""
    base = seed
    h = Harness(seed=base, name="tom_coordination", with_db=False, config=WorldConfig())
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
            samples = _collect_hunt_decisions(_make_cfg(), reps, max_ticks=max_ticks)
            per_seed.append({**_recruitment_signal(samples), "seed": int(s)})
    finally:
        async_logger.stop()
    return _report_coordination(h, per_seed, R, _return)


if __name__ == "__main__":
    main_tom_coordination()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_tom_coordination.py -v`
Expected: PASS (5 tests). Le smoke lance une évolution réelle (R=1, eras=2) → quelques dizaines de secondes.

- [ ] **Step 5: Verify zero src/ change**

Run: `git diff --stat <task1-head> HEAD -- src/` (attendu VIDE).

- [ ] **Step 6: Commit**

```bash
git add tools/tom_coordination.py tests/sandbox/test_tom_coordination.py
git commit -m "feat(tom-coord): collecte decisions de chasse (cohorte fixe) + report + main

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage** : §4.1 `_hunt_samples_from_state` → T1. §4.3 `_recruitment_signal` → T1. §4.4 `_verdict_coordination` → T1. §4.2 `_collect_hunt_decisions` → T2. §4.5 `_report_coordination` → T2. §4.6 `main_tom_coordination` → T2. §8 tests 1-4 → T1 (samples/signal/verdict) + T2 (smoke). Couvert.
- **Placeholders** : aucun ; code complet à chaque step.
- **Type consistency** : `sample = {"attacking": bool, "others_near": int}` cohérent (produit par `_hunt_samples_from_state`, consommé par `_recruitment_signal`). `sig = {p_with,p_alone,delta,n_with,n_alone}` cohérent (produit par `_recruitment_signal`, consommé par `_verdict_coordination`/`_report_coordination`). `per_seed[i]` = `{**sig, seed}` ; `_report_coordination` moyenne `delta/p_with/p_alone` et prend min `n_with/n_alone`. Cohérent.
- **Run réel** (hors plan, après revue) : `MEC_PRESERVE_DIMS=1 python -m tools.tom_coordination` (seed 1300, R=3), 2 passes byte-identiques, puis EDR 135 + mémoire + PR.
