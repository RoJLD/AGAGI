# Évolvabilité du stockage dans FamineWorld — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer causalement si le substrat ÉVOLUE la gratification différée (le stockage) quand on évolue une population *dans* FamineWorld, via une ablation du cache (ON vs OFF) + un contrôle stoneage.

**Architecture:** Un seam d'ablation `cache_enabled` dans `FamineWorld`, puis un outil dédié `tools/famine_storage_probe.py` qui (1) évolue une population tabula-rasa dans famine en retenant le génome du champion en mémoire, (2) mesure sa survie médiane cache ON vs OFF, (3) refait l'ablation sur le champion stoneage (contrôle), (4) calcule un verdict d'émergence sur le delta d'ablation apparié par seed. Réutilise la machinerie d'ères/sélection existante et les helpers de test de signe.

**Tech Stack:** Python 3.11, numpy, pytest. Lancement Windows : `py -3`, `PYTHONIOENCODING=utf-8`.

## Global Constraints

- **Héritage moteur** : pas de réécriture ; `FamineWorld(Biosphere3D)`, I/O 59/108 partagé. (spec §3)
- **Seam d'ablation défaut `True`** → comportement EDR-118/G0 byte-inchangé (non-régressif). (spec §3.1, §6.5)
- **Évoluer pour la SURVIE, jamais récompenser le stockage** — sinon on enseigne au lieu de tester l'émergence. (spec §6.1)
- **Ablation = inférence causale** ; le contrôle stoneage neutralise « le cache aide tout le monde ». (spec §6.2)
- **Repro** : `deterministic=True` (mémoire ambiante `memory_retriever.stop()` AVANT toute boucle sim). (spec §6.3)
- **n≥8 seeds pour un verdict powered** (leçon EDR-116) ; smoke 1-2 seeds d'abord. (spec §4)
- **Régime nuit OFF** dans évolution ET mesure (cohérent avec le harnais S2 d'EDR-118 ; isole la pression de pénurie — la nuit ×2.5 rend le stockage non-mesurable, cf. fix Task 3 FamineWorld). À consigner comme choix de régime.
- **Sessions parallèles / tree partagé** : commits PATH-SCOPED (liste explicite), jamais `git add -A`.
- **Tests** : `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest <fichier> -q`.
- **⚠️ Contention KuzuDB** (machine multi-sessions) : tout test qui tourne la biosphère doit `memory_retriever.stop()` et rester MINIMAL (peu d'agents/ticks). Si un test pend >2min → ne tuer aucun process, rapporter BLOCKED.

---

### Task 1: Seam d'ablation `cache_enabled` dans FamineWorld

**Files:**
- Modify: `src/worlds/world_famine.py` (`__init__` après `starve_threshold` ; les 2 appels `_auto_consume_cache` dans `step()`)
- Test: `tests/test_world_famine.py` (append)

**Interfaces:**
- Produces: attribut `self.cache_enabled: bool` (défaut `True`) sur `FamineWorld`. Quand `False`, la passe d'auto-consommation du cache (pré-step ET post-step) est sautée → les fruits stockés ne rendent plus d'énergie (le coût de portage reste facturé par le moteur).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_world_famine.py` :
```python
def test_cache_enabled_false_disables_auto_consume():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cache_enabled = False
    w.cycle_abundance, w.cycle_famine = 0, 100   # famine permanente
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # cache OFF : le fruit n'est PAS consommé -> reste en inventaire, pas de gain FOOD_VALUE
    assert any(it.get("type") == "Fruit" for it in a["inventory"])
    assert a["energy"] <= e0    # aucune remontée d'énergie (drain seul)


def test_cache_enabled_default_true_consumes():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    assert w.cache_enabled is True   # défaut non-régressif
    w.cycle_abundance, w.cycle_famine = 0, 100
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # cache ON (défaut) : fruit consommé, énergie remontée (comportement EDR-118)
    assert all(it.get("type") != "Fruit" for it in a["inventory"])
    assert a["energy"] > e0 - 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -k "cache_enabled" -q`
Expected: FAIL — `test_cache_enabled_false_disables_auto_consume` échoue (le cache se consomme quand même, car le flag n'existe pas / n'est pas respecté).

- [ ] **Step 3: Write minimal implementation**

Dans `src/worlds/world_famine.py`, `__init__`, après `self.starve_threshold = 25.0` :
```python
        # Seam d'ablation (probe d'évolvabilité) : à False, l'auto-consommation du cache est
        # désactivée -> les fruits stockés deviennent du poids mort (le coût de portage reste).
        # Défaut True = comportement EDR-118 / distinctness inchangé (non-régressif).
        self.cache_enabled = True
```
Puis dans `step()`, gater les DEUX appels `_auto_consume_cache`. La passe pré-step :
```python
        if self.cache_enabled:
            for a in self.agents:
                self._auto_consume_cache(a)
```
Et la passe post-step (dans la boucle de démasquage existante), conditionner l'appel :
```python
            if self.cache_enabled:
                self._auto_consume_cache(a)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: PASS (10 tests : les 8 existants + 2 nouveaux ; le défaut True préserve les 8).

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_famine.py tests/test_world_famine.py
git commit -m "feat(world): seam cache_enabled dans FamineWorld (ablation du stockage, defaut True non-regressif)"
```

---

### Task 2: Primitive de mesure `measure_genome` (survie + fruits portés, ablation)

**Files:**
- Create: `tools/famine_storage_probe.py`
- Test: `tests/test_famine_storage_probe.py`

**Interfaces:**
- Consumes: `FamineWorld`, `self.cache_enabled` (Task 1), `MambaAgent`, `Genome`.
- Produces:
  - `count_reserves(agent: dict) -> int` : nombre de fruits/réserves dans `agent["inventory"]` (compte `type in {"Fruit","_FruitReserve"}`).
  - `measure_genome(genome, seed, cache_enabled=True, num_agents=10, max_ticks=300, cycle_abundance=60, cycle_famine=40) -> dict` : clone le génome dans une `FamineWorld` (cohorte fixe `benchmark_mode=True`, `night_enabled=False`, `cache_enabled` posé), boucle jusqu'à extinction/max_ticks, renvoie `{"median_survival": float, "fruits_at_transition": float}`. `fruits_at_transition` = moyenne (sur agents vivants) du nombre de fruits portés au 1ᵉʳ tick de famine (première bascule `is_famine()` False→True) ; 0.0 si aucune transition atteinte.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_famine_storage_probe.py` :
```python
import numpy as np
from tools.famine_storage_probe import count_reserves, measure_genome
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.environments.config import WorldConfig


def test_count_reserves_counts_fruits_and_masked():
    agent = {"inventory": [
        {"type": "Fruit", "weight": 0.5},
        {"type": "_FruitReserve", "weight": 0.5},
        {"type": "Spear", "weight": 1.0},
        "not_a_dict",
    ]}
    assert count_reserves(agent) == 2


def test_measure_genome_returns_survival_and_fruits():
    # un génome frais (petit run) ; on vérifie la FORME du retour, pas une valeur précise.
    genomes, _ = init_primordial_soup(num_agents=2, config=WorldConfig())
    g = genomes[0]
    out = measure_genome(g, seed=1, cache_enabled=True, num_agents=4, max_ticks=40,
                         cycle_abundance=10, cycle_famine=10)
    assert set(out) == {"median_survival", "fruits_at_transition"}
    assert out["median_survival"] >= 0.0
    assert out["fruits_at_transition"] >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.famine_storage_probe'`.

- [ ] **Step 3: Write minimal implementation**

Créer `tools/famine_storage_probe.py` :
```python
"""Probe d'évolvabilité du stockage dans FamineWorld (spec 2026-06-30-Famine-Storage-Evolvability).

Évolue une population tabula-rasa DANS famine, puis teste causalement si le stockage a émergé :
ablation du cache (ON vs OFF) sur le champion évolué vs le champion stoneage (contrôle). Si la survie
s'effondre cache OFF pour l'évolué mais pas pour le stoneage -> la gratification différée est ÉVOLUÉE.
On évolue pour la SURVIE, jamais en récompensant le stockage (test d'émergence, pas d'enseignement)."""
import os
import sys
import math
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_famine import FamineWorld
from src.environments.config import WorldConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.harness import SeedManager


def count_reserves(agent: dict) -> int:
    """Nombre de fruits portés (frais ou masqués en réserve) dans l'inventaire d'un agent-dict."""
    inv = agent.get("inventory", [])
    return sum(1 for it in inv
               if isinstance(it, dict) and it.get("type") in ("Fruit", "_FruitReserve"))


def _genome_to_agent(g) -> MambaAgent:
    a = MambaAgent(g.num_inputs, g.num_outputs, g.num_nodes)
    a.from_genome(g)
    return a


def _new_famine(cache_enabled: bool, cycle_abundance: int, cycle_famine: int) -> FamineWorld:
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()       # repro + anti-contention KuzuDB
        w.memory_retriever.clear()
    w.benchmark_mode = True             # cohorte fixe (pas de repro/mutation pendant la mesure)
    w.night_enabled = False             # régime cohérent EDR-118 (isole la pénurie)
    w.cache_enabled = cache_enabled
    w.cycle_abundance, w.cycle_famine = cycle_abundance, cycle_famine
    return w


def measure_genome(genome, seed, cache_enabled=True, num_agents=10, max_ticks=300,
                   cycle_abundance=60, cycle_famine=40) -> Dict:
    """Survie médiane d'une cohorte de clones du génome, + fruits portés à la 1ʳᵉ transition famine."""
    SeedManager(seed).seed_boundary(0)
    w = _new_famine(cache_enabled, cycle_abundance, cycle_famine)
    for _ in range(num_agents):
        w.add_agent(_genome_to_agent(genome), energy=80.0)
    fruits_at_transition = None
    was_famine = w.is_famine()
    t = 0
    while w.agents and t < max_ticks:
        w.step()
        t += 1
        now_famine = w.is_famine()
        if fruits_at_transition is None and now_famine and not was_famine and w.agents:
            fruits_at_transition = float(np.mean([count_reserves(a) for a in w.agents]))
        was_famine = now_famine
    all_agents = w.agents + getattr(w, "dead_agents", [])
    ages = [int(a["age"]) for a in all_agents]
    return {"median_survival": float(np.median(ages)) if ages else 0.0,
            "fruits_at_transition": fruits_at_transition if fruits_at_transition is not None else 0.0}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -q`
Expected: PASS (2 tests). Si le 2ᵉ pend >2min = contention KuzuDB → BLOCKED (rapporter).

- [ ] **Step 5: Commit**

```bash
git add tools/famine_storage_probe.py tests/test_famine_storage_probe.py
git commit -m "feat(probe): measure_genome (survie + fruits portes, ablation cache) pour l'evolvabilite du stockage"
```

---

### Task 3: Primitive d'évolution `evolve_in_famine` (GA autonome, génome en mémoire)

**Files:**
- Modify: `tools/famine_storage_probe.py`
- Test: `tests/test_famine_storage_probe.py` (append)

**Interfaces:**
- Consumes: `init_primordial_soup` (population fraîche), `build_population` (reseed muté), `calculate_life_score`, `MambaAgent`, `FamineWorld`.
- Produces: `evolve_in_famine(seed, eras=15, num_agents=20, max_ticks=300, cycle_abundance=60, cycle_famine=40) -> Genome` : boucle GA — ère 0 = population fraîche (`init_primordial_soup`), chaque ère crée une `FamineWorld` fraîche (cache ON, nuit OFF, déterministe), boucle jusqu'à extinction/max_ticks, sélectionne le champion (`max(env.agents+env.dead_agents, key=calculate_life_score)`), reseed via `build_population([champion_genome], num_agents, ...)`. Renvoie le génome du champion final. On évolue pour la survie (sélection par life_score), JAMAIS en récompensant le stockage.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_famine_storage_probe.py` :
```python
from tools.famine_storage_probe import evolve_in_famine
from src.seed_ai.mutation import Genome


def test_evolve_in_famine_returns_genome():
    # smoke minimal : 2 ères, peu d'agents/ticks -> renvoie un Genome aux bonnes dims.
    g = evolve_in_famine(seed=3, eras=2, num_agents=4, max_ticks=30,
                         cycle_abundance=10, cycle_famine=10)
    assert isinstance(g, Genome)
    assert g.num_inputs == 59 and g.num_outputs == 108


def test_evolve_in_famine_deterministic():
    # même seed -> même champion (W identique). Repro (verrou Dev #3).
    g1 = evolve_in_famine(seed=5, eras=2, num_agents=4, max_ticks=30,
                          cycle_abundance=10, cycle_famine=10)
    g2 = evolve_in_famine(seed=5, eras=2, num_agents=4, max_ticks=30,
                          cycle_abundance=10, cycle_famine=10)
    assert np.array_equal(g1.W, g2.W)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -k "evolve" -q`
Expected: FAIL — `ImportError: cannot import name 'evolve_in_famine'`.

- [ ] **Step 3: Write minimal implementation**

Dans `tools/famine_storage_probe.py`, ajouter les imports en tête :
```python
from main_biosphere import init_primordial_soup
from src.seed_ai.repopulation import build_population
from src.seed_ai.mutation import apply_mutations, MutationConfig
```
Puis la fonction :
```python
def evolve_in_famine(seed, eras=15, num_agents=20, max_ticks=300,
                     cycle_abundance=60, cycle_famine=40):
    """Évolue une population tabula-rasa DANS famine (sélection par survie) -> génome du champion final.
    GA autonome (génome en mémoire, pas de KuzuDB) : population fraîche puis reseed muté du champion."""
    SeedManager(seed).seed_boundary(0)
    genomes, _ = init_primordial_soup(num_agents=num_agents, config=WorldConfig())
    mut_config = MutationConfig(weight_init_std=2.0, add_node_rate=0.0)  # topo fixe (batching stable)
    champion_genome = genomes[0]
    for _era in range(max(1, eras)):
        w = _new_famine(cache_enabled=True, cycle_abundance=cycle_abundance, cycle_famine=cycle_famine)
        for g in genomes:
            w.add_agent(_genome_to_agent(g), energy=50.0)
        t = 0
        while w.agents and t < max_ticks:
            w.step()
            t += 1
        all_agents = w.agents + getattr(w, "dead_agents", [])
        if not all_agents:
            break
        champion_genome = max(all_agents, key=calculate_life_score)["model"].genome
        genomes = build_population([champion_genome], num_agents, mut_config, apply_mutations)
    return champion_genome
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -q`
Expected: PASS (4 tests). Si un test evolve pend >2min = contention KuzuDB → BLOCKED.

- [ ] **Step 5: Commit**

```bash
git add tools/famine_storage_probe.py tests/test_famine_storage_probe.py
git commit -m "feat(probe): evolve_in_famine (GA autonome, selection par survie, genome en memoire)"
```

---

### Task 4: Verdict d'émergence + orchestration `run_storage_probe`

**Files:**
- Modify: `tools/famine_storage_probe.py`
- Test: `tests/test_famine_storage_probe.py` (append)

**Interfaces:**
- Consumes: `evolve_in_famine` (T3), `measure_genome` (T2), `load_champion_genome` (s2_demand, contrôle stoneage), `_sign_test_p` (curriculum_transfer).
- Produces:
  - `compute_emergence_verdict(deltas_famine: List[float], deltas_stoneage: List[float], min_effect: float = 5.0) -> dict` : PUR. Apparié par seed, `paired = [df - ds for df, ds in zip(...)]`. Renvoie `{"n", "median_delta_famine", "median_delta_stoneage", "median_paired", "n_favorable", "sign_p", "verdict"}`. `verdict` = **EMERGE** si `median_paired > min_effect` ET `2*n_favorable > n` ET `sign_p < 0.05` ; **N_EMERGE_PAS** si `median_paired <= min_effect` (ou non significatif) ; (le cas négatif profond reste N_EMERGE_PAS — l'absence d'émergence est le résultat, pas un troisième label).
  - `run_storage_probe(seeds, eras=15, num_agents=20, max_ticks=300, cycle_abundance=60, cycle_famine=40) -> dict` : pour chaque seed, évolue en famine, mesure `Δ_famine = measure(champion_famine, ON) - measure(champion_famine, OFF)` (survie), idem `Δ_stoneage` sur `load_champion_genome()`, capture les fruits portés. Renvoie le verdict + le détail par seed.

- [ ] **Step 1: Write the failing test (verdict pur)**

Ajouter à `tests/test_famine_storage_probe.py` :
```python
from tools.famine_storage_probe import compute_emergence_verdict


def test_verdict_emerge_when_famine_delta_dominates():
    # l'évolué dépend du cache (gros delta), le stoneage non (delta ~0) -> EMERGE
    df = [40.0, 35.0, 50.0, 45.0, 38.0, 42.0, 47.0, 39.0]
    ds = [2.0, 1.0, 3.0, 0.0, 1.0, 2.0, 1.0, 0.0]
    v = compute_emergence_verdict(df, ds)
    assert v["verdict"] == "EMERGE"
    assert v["n"] == 8 and v["n_favorable"] == 8
    assert v["sign_p"] < 0.05


def test_verdict_n_emerge_pas_when_deltas_match():
    # aucun avantage cache spécifique à l'évolué -> N_EMERGE_PAS (finding substrat)
    df = [3.0, 2.0, 1.0, 4.0, 2.0, 3.0, 1.0, 2.0]
    ds = [2.0, 3.0, 2.0, 1.0, 3.0, 2.0, 2.0, 1.0]
    v = compute_emergence_verdict(df, ds)
    assert v["verdict"] == "N_EMERGE_PAS"


def test_verdict_empty():
    v = compute_emergence_verdict([], [])
    assert v["verdict"] == "N_EMERGE_PAS" and v["n"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -k "verdict" -q`
Expected: FAIL — `ImportError: cannot import name 'compute_emergence_verdict'`.

- [ ] **Step 3: Write minimal implementation**

Dans `tools/famine_storage_probe.py`, ajouter l'import du test de signe :
```python
from tools.curriculum_transfer import _sign_test_p
from tools.s2_demand import load_champion_genome
```
Puis :
```python
def compute_emergence_verdict(deltas_famine: List[float], deltas_stoneage: List[float],
                              min_effect: float = 5.0) -> Dict:
    """PUR. Delta d'ablation apparié (famine - stoneage) par seed -> verdict d'émergence du stockage."""
    n = min(len(deltas_famine), len(deltas_stoneage))
    if n == 0:
        return {"n": 0, "median_delta_famine": 0.0, "median_delta_stoneage": 0.0,
                "median_paired": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "N_EMERGE_PAS"}
    paired = [deltas_famine[i] - deltas_stoneage[i] for i in range(n)]
    med_pair = float(statistics.median(paired))
    n_fav = sum(1 for p in paired if p > 0.0)
    effective = [p for p in paired if p != 0.0]
    sign_p = _sign_test_p(sum(1 for p in effective if p > 0.0), len(effective))
    emerge = (med_pair > min_effect) and (2 * n_fav > n) and (sign_p < 0.05)
    return {"n": n,
            "median_delta_famine": float(statistics.median(deltas_famine[:n])),
            "median_delta_stoneage": float(statistics.median(deltas_stoneage[:n])),
            "median_paired": med_pair, "n_favorable": n_fav, "sign_p": sign_p,
            "verdict": "EMERGE" if emerge else "N_EMERGE_PAS"}


def run_storage_probe(seeds, eras=15, num_agents=20, max_ticks=300,
                      cycle_abundance=60, cycle_famine=40) -> Dict:
    """Orchestration : par seed, évolue en famine + ablation A/B (évolué) + contrôle stoneage."""
    stoneage_genome = load_champion_genome()
    per_seed, df, ds = [], [], []
    for seed in seeds:
        champ = evolve_in_famine(seed, eras, num_agents, max_ticks, cycle_abundance, cycle_famine)
        f_on = measure_genome(champ, seed, True, num_agents, max_ticks, cycle_abundance, cycle_famine)
        f_off = measure_genome(champ, seed, False, num_agents, max_ticks, cycle_abundance, cycle_famine)
        s_on = measure_genome(stoneage_genome, seed, True, num_agents, max_ticks, cycle_abundance, cycle_famine)
        s_off = measure_genome(stoneage_genome, seed, False, num_agents, max_ticks, cycle_abundance, cycle_famine)
        d_f = f_on["median_survival"] - f_off["median_survival"]
        d_s = s_on["median_survival"] - s_off["median_survival"]
        df.append(d_f); ds.append(d_s)
        per_seed.append({"seed": int(seed), "delta_famine": d_f, "delta_stoneage": d_s,
                         "fruits_famine": f_on["fruits_at_transition"],
                         "fruits_stoneage": s_on["fruits_at_transition"],
                         "f_on": f_on["median_survival"], "f_off": f_off["median_survival"],
                         "s_on": s_on["median_survival"], "s_off": s_off["median_survival"]})
    verdict = compute_emergence_verdict(df, ds)
    return {**verdict, "per_seed": per_seed,
            "config": {"seeds": [int(s) for s in seeds], "eras": eras, "num_agents": num_agents,
                       "max_ticks": max_ticks, "cycle_abundance": cycle_abundance,
                       "cycle_famine": cycle_famine}}


def main():
    import json
    seeds = [int(s) for s in os.environ.get("FSP_SEEDS", "0,1").split(",") if s.strip()]
    eras = int(os.environ.get("FSP_ERAS", "15"))
    num_agents = int(os.environ.get("FSP_NUM_AGENTS", "20"))
    max_ticks = int(os.environ.get("FSP_MAX_TICKS", "300"))
    r = run_storage_probe(seeds, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    print("FSP_RESULT", json.dumps(r))
    return r


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_famine_storage_probe.py -q`
Expected: PASS (7 tests : count + measure + 2 evolve + 3 verdict).

- [ ] **Step 5: Commit**

```bash
git add tools/famine_storage_probe.py tests/test_famine_storage_probe.py
git commit -m "feat(probe): compute_emergence_verdict (pur) + run_storage_probe (orchestration ablation + controle stoneage)"
```

---

### Task 5: Run (smoke → power) + EDR (exécution + science, INLINE)

**Files:**
- Create: `docs/EDR/NNN_Storage_Evolvability_In_Famine.md` (NNN = max EDR + 1, vérifier `ls docs/EDR/`)
- Modify: `docs/SDR/G1_competence_generalizes.md` (lier l'EDR)

**Interfaces:**
- Consumes: `tools/famine_storage_probe.run_storage_probe`. Exécution, pas de nouveau code.

- [ ] **Step 1: Smoke**

```bash
PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -c "from tools.famine_storage_probe import run_storage_probe; import json; print('SMOKE', json.dumps(run_storage_probe([0], eras=15, num_agents=12, max_ticks=200)))"
```
Vérifie : le pipeline tourne (évolution → ablation → verdict), `delta_famine`/`delta_stoneage`/`fruits_*` plausibles. Si crash/contention → diagnostiquer avant de monter en puissance. Régler `eras`/cycle si la survie est au plancher (variable d'expérience, spec §4).

- [ ] **Step 2: Power**

```bash
PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -c "from tools.famine_storage_probe import run_storage_probe; import json; print('POWER', json.dumps(run_storage_probe([0,1,2,3,4,5,6,7], eras=15, num_agents=20, max_ticks=300)))"
```
(n=8 seeds appariés). Noter `verdict`, `median_paired`, `median_delta_famine` vs `median_delta_stoneage`, `sign_p`, et les fruits portés (corroboration comportementale).

- [ ] **Step 3: Consigner l'EDR**

Rédiger `docs/EDR/NNN_*.md` avec frontmatter (`id: EDR-NNN`, `type: EDR`, `gate: G1`, `tests: [SDR-G1]`, `verdict: <EMERGE|N_EMERGE_PAS>`), le protocole (évolution famine + ablation + contrôle stoneage), les chiffres (Δ_famine vs Δ_stoneage appariés, sign_p, fruits portés), et l'interprétation (spec §9 : ÉMERGE = débloque G1 ; N'ÉMERGE PAS = finding substrat, convergence EDR 105/108/110/113/116/117). Caveats : régime nuit OFF (cohérent EDR-118), benchmark_mode pour la mesure, contention KuzuDB = logging seul, échelle. Puis :
```bash
PYTHONIOENCODING=utf-8 py -3 tools/consolidate_records.py
```
Expected: `problemes=0`, l'EDR apparaît lié à SDR-G1.

- [ ] **Step 4: Commit**

```bash
git add docs/EDR/NNN_Storage_Evolvability_In_Famine.md docs/SDR/G1_competence_generalizes.md
git commit -m "feat(G1): EDR NNN — evolvabilite du stockage dans FamineWorld (verdict <...>)"
```

---

## Self-Review

**1. Spec coverage** (spec §2-§10) :
- Seam d'ablation `cache_enabled` (§3.1) → Task 1. ✅
- Probe : mesure survie + fruits (§3.2.2/§3.2.4) → Task 2 ; évolution famine + extraction génome (§3.2.1) → Task 3 ; verdict + contrôle stoneage (§3.2.3/§3.3) → Task 4. ✅
- Détection ablation + comportement (§2) → Task 2 (fruits) + Task 4 (deltas appariés). ✅
- Évoluer pour la survie, jamais récompenser le stockage (§6.1) → Task 3 (sélection par `calculate_life_score`, aucun reward de stockage). ✅
- Repro deterministic (§6.3) → `SeedManager` + `memory_retriever.stop()` dans `_new_famine`/`evolve_in_famine` ; test de déterminisme Task 3. ✅
- n≥8, smoke→power (§4) → Task 5. ✅
- Régime nuit OFF (Global Constraints) → `_new_famine` pose `night_enabled=False`. ✅
- Non-régression seam défaut True (§6.5) → Task 1 (8 tests famine restent verts). ✅
- EDR + interprétation des deux verdicts (§9) → Task 5 Step 3. ✅
- **Hors périmètre (spec §8)** : re-mesure G1 transfert = sous-chantier suivant. Noté, pas un gap.

**2. Placeholder scan** : `NNN` (Task 5) = numéro EDR résolu au commit (sessions parallèles créent des EDR). Pas de TODO/TBD ailleurs ; tout le code est complet.

**3. Type consistency** : `cache_enabled` (bool) cohérent Task 1↔2↔3 ; `measure_genome(...) -> {"median_survival","fruits_at_transition"}` cohérent Task 2↔4 ; `evolve_in_famine(...) -> Genome` cohérent Task 3↔4 ; `compute_emergence_verdict(deltas_famine, deltas_stoneage)` cohérent Task 4↔tests ; `count_reserves(agent) -> int` cohérent Task 2↔4. `_genome_to_agent`/`_new_famine` partagés (définis Task 2, réutilisés Task 3).
