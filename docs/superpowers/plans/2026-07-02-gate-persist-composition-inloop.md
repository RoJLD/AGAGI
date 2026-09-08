# Persistance du gate au rebuild + binding in-loop — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vérifier que porter le gate appris à travers un rebuild de pop (mortalité) maintient le binding, via un A/B PERSIST vs RESET sur le monde compositionnel d'EDR-161.

**Architecture:** Deux unités, TOUTES EN FICHIERS NEUFS (aucun fichier partagé/en-vol touché). Unité A = helper `inherit_gate(new_pop, old_pop)` (copie le gate public entre deux pops). Unité B = harnais `tools/torch_gate_persist_ab.py` qui fait tourner un pop torch persistant sur le monde 2-pas d'EDR-161 avec rebuilds périodiques, et compare PERSIST (inherit_gate) vs RESET (gate neuf) sur `comp_rate`.

**Tech Stack:** Python, PyTorch, numpy, pytest. Réutilise `tools/compositional_world_probe.py` (EDR-161) et `tools/substrate_ab.py`.

## Global Constraints

- **Fichiers NEUFS uniquement** : `tools/torch_gate_persist_ab.py` et `tests/sandbox/test_torch_gate_persist_ab.py`. NE PAS modifier `src/agents/backend_torch.py` (travail EDR-160 // non-commité → un commit path-scopé y est impossible sans `git add -p`). Le helper `inherit_gate` vit DANS le harnais.
- **Commits PATH-SCOPED** : `git add` UNIQUEMENT les 2 fichiers neufs ci-dessus. JAMAIS `git add -A` (tree partagé, sessions //).
- **Additif / non-régressif** : rien ne touche le chemin prod ; le harnais pose les class-vars du gate en `try/finally` (restaure, motif d'EDR-161).
- **DRY** : réutiliser `_energy`, `CRAFT`, `USE`, `FREE`, `_softmax_np`, `_MOVE` de `compositional_world_probe` par import (ne pas recopier le monde).
- **Style projet** : français, concis, pas d'emojis. Tests dans `tests/sandbox/`.
- **Shell PowerShell (Windows)** ; tests via `python -m pytest ...`.
- **Le gate** : `pop.w_gate` (tensor taille N, requires_grad), `pop.b_gate` (taille 1). Créés si class-vars `CONDITION_GATE=True` et `GATE_TARGET is not None`. `GATE_TARGET=USE` route l'action « ends ».
- **Rebuild = W survit, gate perdu** : `TorchPopulationModel(mêmes_agents)` relit `genome.W` (mis à jour par `_write_back` dans `learn_episode`) → W survit ; `w_gate`/`b_gate` neufs → gate perdu sauf `inherit_gate`.

---

### Task 1: Helper `inherit_gate` (Unité A)

**Files:**
- Create: `tools/torch_gate_persist_ab.py` (début du fichier : imports + helper)
- Create: `tests/sandbox/test_torch_gate_persist_ab.py`

**Interfaces:**
- Consumes: `TorchPopulationModel` (attributs publics `w_gate`, `b_gate`) ; `make_population(agents, backend="torch")`.
- Produces: `inherit_gate(new_pop, old_pop) -> bool` (True si copie effectuée, False si no-op).

- [ ] **Step 1: Écrire les tests du helper**

```python
# tests/sandbox/test_torch_gate_persist_ab.py
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def _gated_pop(n=4, seed=0):
    np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGET = 4        # USE
    try:
        pop = make_population([MambaAgent() for _ in range(n)], backend="torch")
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved
    return pop


def test_inherit_gate_copies_values():
    import torch
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    with torch.no_grad():
        old.w_gate += 3.0                        # rend le gate distinct de l'init
        old.b_gate -= 1.5
    new = _gated_pop(seed=1)
    ok = inherit_gate(new, old)
    assert ok is True
    assert torch.allclose(new.w_gate.data, old.w_gate.data)
    assert torch.allclose(new.b_gate.data, old.b_gate.data)


def test_inherit_gate_noop_when_gate_absent():
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    plain = make_population([MambaAgent() for _ in range(4)], backend="torch")  # gate OFF -> w_gate None
    assert inherit_gate(plain, old) is False     # cible sans gate -> no-op
    assert inherit_gate(old, plain) is False      # source sans gate -> no-op
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py -v`
Expected: FAIL (`ModuleNotFoundError` / `ImportError: inherit_gate`).

- [ ] **Step 3: Écrire l'en-tête du harnais + le helper**

```python
# tools/torch_gate_persist_ab.py
"""A/B PERSIST vs RESET du gate au rebuild du pop (cran 2, prerequis EDR-163). Le gate porte le binding
means->ends (EDR-158/159) mais est population-partage, PAS dans le genome -> perdu au rebuild sur
mortalite. Ce banc teste si le porter (inherit_gate) maintient le CAPABILITY_PAYS d'EDR-161 a travers
les rebuilds. Reutilise le monde 2-pas craft->USE de compositional_world_probe (EDR-161).

Usage : python tools/torch_gate_persist_ab.py   (env: TGP_SEEDS, TGP_EPISODES, TGP_REBUILD_EVERY, TGP_DEMAND)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel
from tools.compositional_world_probe import _energy, _softmax_np, CRAFT, USE, _MOVE
from tools.substrate_ab import compute_ab_verdict


def inherit_gate(new_pop, old_pop) -> bool:
    """Porte le gate appris (w_gate/b_gate) de old_pop vers new_pop a travers un rebuild. Le gate est
    population-partage, hors genome -> perdu au rebuild sauf carry-over explicite. No-op (False) si un
    gate est absent ou si les dimensions different. N'affecte PAS W (survit via genome)."""
    if getattr(new_pop, "w_gate", None) is None or getattr(old_pop, "w_gate", None) is None:
        return False
    if new_pop.w_gate.shape != old_pop.w_gate.shape or new_pop.b_gate.shape != old_pop.b_gate.shape:
        return False
    with torch.no_grad():
        new_pop.w_gate.data.copy_(old_pop.w_gate.data)
        new_pop.b_gate.data.copy_(old_pop.b_gate.data)
    return True
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit (PATH-SCOPED)**

```bash
git add tools/torch_gate_persist_ab.py tests/sandbox/test_torch_gate_persist_ab.py
git commit -m "feat(G1): helper inherit_gate — porte le gate au rebuild (prerequis cran 2)"
```

---

### Task 2: `run_arm` avec rebuilds (Unité B, cœur)

**Files:**
- Modify: `tools/torch_gate_persist_ab.py` (ajouter `run_arm`)
- Modify: `tests/sandbox/test_torch_gate_persist_ab.py` (ajouter un smoke)

**Interfaces:**
- Consumes: `inherit_gate` (Task 1) ; `_energy`, `_softmax_np`, `CRAFT`, `USE`, `_MOVE` (compositional_world_probe) ; boucle 2-pas d'EDR-161.
- Produces: `run_arm(persist, demand=1.0, episodes=800, rebuild_every=200, n_agents=64, seed=0, lr=0.05, antisat=6.0) -> dict` avec clés `persist`, `demand`, `seed`, `comp_rate`, `n_rebuilds`.

- [ ] **Step 1: Écrire le smoke test**

```python
def test_run_arm_smoke_persist_and_reset():
    from tools.torch_gate_persist_ab import run_arm
    r_p = run_arm(persist=True, episodes=40, rebuild_every=20, n_agents=16, seed=0)
    r_r = run_arm(persist=False, episodes=40, rebuild_every=20, n_agents=16, seed=0)
    for r in (r_p, r_r):
        assert set(["persist", "comp_rate", "n_rebuilds"]).issubset(r)
        assert 0.0 <= r["comp_rate"] <= 1.0
    assert r_p["n_rebuilds"] == r_r["n_rebuilds"] == 1     # 40/20 - 1 rebuild a l'episode 20
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py::test_run_arm_smoke_persist_and_reset -v`
Expected: FAIL (`ImportError: run_arm`).

- [ ] **Step 3: Écrire `run_arm`**

Ajouter à `tools/torch_gate_persist_ab.py` :

```python
def _new_gated_pop(agents, lr):
    """Construit un pop torch gate-ON depuis des agents (W relu de leur genome) + opt Adam."""
    pop = make_population(agents, backend="torch")
    pop.opt = torch.optim.Adam([p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
    pop._gate_runtime = True
    return pop


def run_arm(persist, demand=1.0, episodes=800, rebuild_every=200, n_agents=64,
            seed=0, lr=0.05, antisat=6.0):
    """Pop torch PERSISTANT sur le monde 2-pas craft->USE (EDR-161) avec rebuilds tous les
    `rebuild_every` episodes. Au rebuild : nouveau pop depuis les MEMES agents (W survit via genome) ;
    persist=True -> inherit_gate (le gate survit), persist=False -> gate neuf (bug actuel). Renvoie le
    comp_rate du dernier quart. Isole PERSIST vs RESET (1 variable = le sort du gate au rebuild)."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
             TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.ANTISAT = antisat
    TorchPopulationModel.GATE_TARGET = USE
    try:
        agents = [MambaAgent() for _ in range(n_agents)]
        pop = _new_gated_pop(agents, lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        comp_hist, n_rebuilds = [], 0
        for ep in range(episodes):
            if ep > 0 and ep % rebuild_every == 0:
                old = pop
                pop = _new_gated_pop(agents, lr)          # W survit (genome) ; gate neuf
                if persist:
                    inherit_gate(pop, old)                # ... sauf carry-over explicite
                n_rebuilds += 1
            pop.H = torch.zeros((n_agents, pop.N))
            preds1, _ = pop.forward(obs_a)
            move1 = _sample(preds1)
            did_x = (move1 == CRAFT)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            preds2, _ = pop.forward(obs_b)
            move2 = _sample(preds2)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            energy = np.array([_energy(int(move2[i]), bool(did_x[i]), demand)
                               for i in range(n_agents)], dtype=np.float32)
            pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(),
                              gate_last_only=False)
            comp_hist.append((move2 == USE) & did_x)
        q = max(1, episodes // 4)
        comp_rate = float(np.mean(np.concatenate(comp_hist[-q:])))
        return {"persist": bool(persist), "demand": float(demand), "seed": int(seed),
                "comp_rate": comp_rate, "n_rebuilds": n_rebuilds}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET) = saved
```

- [ ] **Step 4: Lancer le smoke, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit (PATH-SCOPED)**

```bash
git add tools/torch_gate_persist_ab.py tests/sandbox/test_torch_gate_persist_ab.py
git commit -m "feat(G1): run_arm PERSIST/RESET — pop persistant + rebuilds sur monde compositionnel"
```

---

### Task 3: `compare` + verdict + run powered (le livrable)

**Files:**
- Modify: `tools/torch_gate_persist_ab.py` (ajouter `compare` + `__main__`)
- Modify: `tests/sandbox/test_torch_gate_persist_ab.py` (test du verdict pur)

**Interfaces:**
- Consumes: `run_arm` (Task 2) ; `compute_ab_verdict(rows, band)` (substrate_ab, pur).
- Produces: `compare(seeds, demand, episodes, rebuild_every, n_agents) -> dict` (rows appariés + verdict).

- [ ] **Step 1: Écrire le test du verdict pur**

```python
def test_verdict_pure_persist_better():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.10}, {"diff": 0.08}, {"diff": 0.12}]   # persist - reset > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
```

- [ ] **Step 2: Lancer, vérifier le succès (compute_ab_verdict existe déjà)**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py::test_verdict_pure_persist_better -v`
Expected: PASS (réutilise `compute_ab_verdict`).

- [ ] **Step 3: Écrire `compare` + `__main__`**

Ajouter à `tools/torch_gate_persist_ab.py` :

```python
def compare(seeds=(0, 1, 2, 3), demand=1.0, episodes=800, rebuild_every=200, n_agents=64):
    """A/B apparie PERSIST vs RESET par seed -> verdict (diff = comp_rate persist - reset)."""
    rows = []
    for s in seeds:
        p = run_arm(True, demand, episodes, rebuild_every, n_agents, seed=s)
        r = run_arm(False, demand, episodes, rebuild_every, n_agents, seed=s)
        rows.append({"seed": s, "persist": p["comp_rate"], "reset": r["comp_rate"],
                     "diff": p["comp_rate"] - r["comp_rate"], "n_rebuilds": p["n_rebuilds"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TGP_SEEDS", "0,1,2,3").split(","))
    episodes = int(os.environ.get("TGP_EPISODES", "800"))
    rebuild_every = int(os.environ.get("TGP_REBUILD_EVERY", "200"))
    demand = float(os.environ.get("TGP_DEMAND", "1.0"))
    out = compare(seeds=seeds, demand=demand, episodes=episodes, rebuild_every=rebuild_every)
    for r in out["rows"]:
        print(f"seed={r['seed']} persist={r['persist']:.3f} reset={r['reset']:.3f} "
              f"diff={r['diff']:+.3f} (rebuilds={r['n_rebuilds']})")
    print("VERDICT:", out["verdict"])
```

- [ ] **Step 4: Lancer TOUT le fichier de test**

Run: `python -m pytest tests/sandbox/test_torch_gate_persist_ab.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run powered (le livrable de mesure)**

Run (PowerShell): `$env:TGP_SEEDS="0,1,2,3"; $env:TGP_EPISODES="800"; $env:TGP_REBUILD_EVERY="200"; python tools/torch_gate_persist_ab.py`
Expected: 4 lignes seed + un `VERDICT`. Reporte le verdict (PERSIST maintient-il le binding vs RESET ?) — c'est le résultat scientifique.

- [ ] **Step 6: Commit (PATH-SCOPED)**

```bash
git add tools/torch_gate_persist_ab.py tests/sandbox/test_torch_gate_persist_ab.py
git commit -m "feat(G1): compare PERSIST/RESET + verdict — instrument prerequis cran 2"
```

---

## Self-Review

**Spec coverage :**
- Unité A (`inherit_gate`) → Task 1 (helper dans le harnais, PAS méthode backend_torch — déviation path-scoping justifiée §Insight). ✓
- Unité B (harnais in-loop, rebuilds, PERSIST/RESET) → Task 2. ✓
- Asymétrie rebuild (W survit via génome, gate perdu) → Task 2 `_new_gated_pop` reconstruit depuis les mêmes agents. ✓
- KPI comp_rate + verdict compute_ab_verdict → Task 3. ✓
- Réutilise monde EDR-161 par import (DRY) → Global Constraints + Task 2. ✓
- Bornes N stable / synthétique → héritées d'EDR-161 (mêmes agents, dims homogènes). ✓
- Non-régression (try/finally class-vars) → Task 2. ✓

**Placeholder scan :** aucun TBD/TODO ; tous les steps ont code ou commande réelle. La déviation méthode→helper est explicite et motivée. ✓

**Type consistency :** `inherit_gate(new_pop, old_pop)->bool` (Task 1) ↔ appelé Task 2 ; `run_arm(persist, demand, episodes, rebuild_every, n_agents, seed, lr, antisat)->dict{persist,comp_rate,n_rebuilds,...}` (Task 2) ↔ consommé Task 3 ; `compare(...)->{rows,verdict}` ↔ `__main__`. `_energy/_softmax_np/CRAFT/USE/_MOVE` importés de compositional_world_probe (vérifiés présents). ✓

## Hors scope (plan de suivi)
Promotion d'`inherit_gate` en méthode de `TorchPopulationModel` (quand le cran 2 réel biosphère en a besoin) ; intégration du gate dans `world_1_stoneage.py` ; N variable au rebuild ; gate hérité dans le génome.
