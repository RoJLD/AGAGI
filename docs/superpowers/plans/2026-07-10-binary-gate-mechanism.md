# Gate de conditionnement sur action BINAIRE (cran 2, Brique A) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vérifier en isolation qu'un readout de H apprend à conditionner une action BINAIRE (throw) sur un contexte (did_craft) sous crédit épisodique — le mécanisme manquant pour gater l'action offensive biosphère.

**Architecture:** Harnais autonome (fichier neuf) : monde 2-pas binaire (S1 craft move, S2 throw binaire), pop torch pour l'état H, tête throw (`w_throw`/`b_throw`) gérée par le harnais, REINFORCE épisodique binaire + anti-saturation. A/B gate-binaire ON (lit H) vs OFF (marginal). KPI = `binding_gap`.

**Tech Stack:** Python, PyTorch, numpy, pytest. Réutilise `compositional_world_probe` (CRAFT, `_softmax_np`, `_MOVE`) et `substrate_ab` (`compute_ab_verdict`).

## Global Constraints

- **Fichiers NEUFS uniquement** : `tools/torch_binary_gate_probe.py` et `tests/sandbox/test_torch_binary_gate_probe.py`. NE PAS toucher `src/agents/backend_torch.py` (sessions // actives).
- **Commits PATH-SCOPED** : `git add` UNIQUEMENT ces 2 fichiers. JAMAIS `git add -A`.
- **W gelé (MVP)** : le gradient ne passe QUE par `w_throw`/`b_throw` (H détaché : `pop.H` est déjà détaché par `forward`). Isole l'effet au gate binaire, pas au substrat.
- **Style** : français, concis, pas d'emojis. Shell PowerShell (Windows). Tests via `python -m pytest ...`.
- **Faits vérifiés** : `CRAFT=0`, `_MOVE=8` (de compositional_world_probe) ; `pop.N=172`, `pop.I=59` ; `pop.H` (B,N) accessible après `pop.forward` (détaché) ; `make_population(agents, backend="torch")`.
- **Énergie** : `+1` si `throw & did_craft` ; sinon faim `−0.3`. **Anti-saturation** : pénalité `antisat * P(throw)²` (empêche le collapse always-throw). **binding_gap** = `P(throw|did_craft) − P(throw|¬did_craft)`.

---

### Task 1: Fonctions pures — énergie binaire + binding_gap

**Files:**
- Create: `tools/torch_binary_gate_probe.py` (imports + 2 fonctions pures)
- Create: `tests/sandbox/test_torch_binary_gate_probe.py`

**Interfaces produites:** `_energy_binary(throw: bool, did_craft: bool, hunger=-0.3) -> float` ; `_binding_gap(throws, did_crafts) -> float`.

- [ ] **Step 1: Écrire les tests des fonctions pures**

```python
# tests/sandbox/test_torch_binary_gate_probe.py
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def test_energy_binary():
    from tools.torch_binary_gate_probe import _energy_binary
    assert _energy_binary(True, True) == 1.0        # composition reussie
    assert _energy_binary(True, False) == -0.3      # throw sans craft -> faim
    assert _energy_binary(False, True) == -0.3      # craft sans throw -> faim
    assert _energy_binary(False, False) == -0.3     # abstention -> faim


def test_binding_gap():
    from tools.torch_binary_gate_probe import _binding_gap
    # throw parfaitement conditionne sur craft -> gap = 1
    throws = [1, 1, 0, 0]; craft = [True, True, False, False]
    assert abs(_binding_gap(throws, craft) - 1.0) < 1e-6
    # throw independant du craft -> gap = 0
    throws2 = [1, 0, 1, 0]; craft2 = [True, True, False, False]
    assert abs(_binding_gap(throws2, craft2) - 0.0) < 1e-6
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py -v`
Expected: FAIL (`ModuleNotFoundError` / `ImportError`).

- [ ] **Step 3: Écrire l'en-tête + les 2 fonctions pures**

```python
# tools/torch_binary_gate_probe.py
"""Gate de conditionnement sur action BINAIRE (cran 2, Brique A). Le gate livre (EDR-159/165) biaise une
politique CATEGORIELLE (8 moves) ; l'action "ends" biosphere = throw (logit 8, BINAIRE). Ce harnais teste
en ISOLATION si un readout de H apprend a conditionner throw sur did_craft sous credit episodique, avant
tout cablage biosphere. Monde 2-pas binaire ; ne touche NI backend_torch NI la biosphere.

Usage : python tools/torch_binary_gate_probe.py   (env: TBG_SEEDS, TBG_EPISODES, TBG_AGENTS)
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
from tools.compositional_world_probe import _softmax_np, CRAFT, _MOVE
from tools.substrate_ab import compute_ab_verdict


def _energy_binary(throw, did_craft, hunger=-0.3):
    """Energie/episode du monde 2-pas binaire. +1 SSI composition (throw ET craft) ; faim sinon
    (throw-sans-craft, craft-sans-throw, abstention) -> l'abstention COUTE, force l'engagement."""
    return 1.0 if (throw and did_craft) else hunger


def _binding_gap(throws, did_crafts):
    """Instrument de binding direct (EDR-126) : P(throw|did_craft) - P(throw|¬did_craft). >0 = throw
    conditionne sur le craft ; ~0 = throw independant du craft (pas de binding)."""
    throws = np.asarray(throws, dtype=np.float32)
    dc = np.asarray(did_crafts, dtype=bool)
    p_given = float(throws[dc].mean()) if dc.any() else 0.0
    p_notgiven = float(throws[~dc].mean()) if (~dc).any() else 0.0
    return p_given - p_notgiven
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit (PATH-SCOPED)**

```bash
git add tools/torch_binary_gate_probe.py tests/sandbox/test_torch_binary_gate_probe.py
git commit -m "feat(G1): fonctions pures monde binaire (energie + binding_gap) — cran 2 brique A"
```

---

### Task 2: `run_arm` — tête throw + REINFORCE binaire (cœur)

**Files:**
- Modify: `tools/torch_binary_gate_probe.py` (ajouter `run_arm`)
- Modify: `tests/sandbox/test_torch_binary_gate_probe.py` (ajouter un smoke)

**Interfaces:**
- Consumes: `_energy_binary`, `_binding_gap` (Task 1) ; `make_population`, `_softmax_np`, `CRAFT`, `_MOVE`.
- Produces: `run_arm(gate_on, episodes=800, n_agents=64, seed=0, lr=0.05, antisat=6.0) -> dict` avec clés `gate_on`, `seed`, `binding_gap`, `comp_rate`, `throw_rate`.

- [ ] **Step 1: Écrire le smoke test**

```python
def test_run_arm_smoke_on_and_off():
    from tools.torch_binary_gate_probe import run_arm
    r_on = run_arm(gate_on=True, episodes=60, n_agents=16, seed=0)
    r_off = run_arm(gate_on=False, episodes=60, n_agents=16, seed=0)
    for r in (r_on, r_off):
        assert set(["gate_on", "binding_gap", "comp_rate", "throw_rate"]).issubset(r)
        assert -1.0 <= r["binding_gap"] <= 1.0
        assert 0.0 <= r["throw_rate"] <= 1.0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py::test_run_arm_smoke_on_and_off -v`
Expected: FAIL (`ImportError: run_arm`).

- [ ] **Step 3: Écrire `run_arm`**

Ajouter à `tools/torch_binary_gate_probe.py` :

```python
def run_arm(gate_on, episodes=800, n_agents=64, seed=0, lr=0.05, antisat=6.0):
    """Entraine une tete throw BINAIRE sur le monde 2-pas. gate_on=True : logit_throw = H·w_throw + b
    (conditionne sur H -> peut decoder did_craft) ; gate_on=False : logit_throw = b seul (marginal, pas
    de lecture de H -> ne peut pas conditionner). Credit episodique REINFORCE binaire + anti-saturation
    (penalise P(throw) -> empeche le collapse always-throw). W gele (H detache) : isole la tete throw.
    Renvoie binding_gap (dernier quart) + comp_rate + throw_rate."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
    N, I = pop.N, pop.I
    w_throw = torch.zeros(N, requires_grad=True)
    b_throw = torch.zeros(1, requires_grad=True)
    params = [w_throw, b_throw] if gate_on else [b_throw]
    opt = torch.optim.Adam(params, lr=lr)
    rng = np.random.RandomState(seed + 1)
    obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)

    throw_hist, craft_hist = [], []
    for _ in range(episodes):
        pop.H = torch.zeros((n_agents, pop.N))
        with torch.no_grad():
            p1, _ = pop.forward(obs_a)
        move1 = _softmax_np(np.asarray(p1)[:, :_MOVE]).argmax(1)
        did_craft = (move1 == CRAFT)
        with torch.no_grad():
            pop.forward(obs_b)                                  # met a jour pop.H (S2)
        H_S2 = pop.H.detach()                                   # W gele : gradient seulement via w_throw
        if gate_on:
            z = H_S2 @ w_throw + b_throw                        # conditionne sur H
        else:
            z = b_throw.expand(n_agents)                       # marginal (aucune lecture de H)
        pthrow = torch.sigmoid(torch.clamp(z, -10.0, 10.0))
        throw = (pthrow.detach() > torch.rand(n_agents)).float()
        energy = np.array([_energy_binary(bool(throw[i]), bool(did_craft[i]))
                           for i in range(n_agents)], dtype=np.float32)
        ret = torch.tensor(energy - energy.mean())             # retour episodique baseline
        logp = throw * torch.log(pthrow + 1e-6) + (1 - throw) * torch.log(1 - pthrow + 1e-6)
        loss = -(ret * logp).mean() + antisat * pthrow.mean() ** 2   # REINFORCE + anti-saturation
        opt.zero_grad()
        loss.backward()
        opt.step()
        throw_hist.append(throw.detach().numpy())
        craft_hist.append(did_craft.copy())

    q = max(1, episodes // 4)
    th = np.concatenate(throw_hist[-q:])
    cr = np.concatenate(craft_hist[-q:])
    return {"gate_on": bool(gate_on), "seed": int(seed),
            "binding_gap": _binding_gap(th, cr),
            "comp_rate": float(np.mean(th * cr)),
            "throw_rate": float(np.mean(th))}
```

- [ ] **Step 4: Lancer TOUT le fichier, vérifier PASS**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit (PATH-SCOPED)**

```bash
git add tools/torch_binary_gate_probe.py tests/sandbox/test_torch_binary_gate_probe.py
git commit -m "feat(G1): run_arm tete throw binaire + REINFORCE episodique — cran 2 brique A"
```

---

### Task 3: `compare` + verdict + run powered (le livrable)

**Files:**
- Modify: `tools/torch_binary_gate_probe.py` (ajouter `compare` + `__main__`)
- Modify: `tests/sandbox/test_torch_binary_gate_probe.py` (test du verdict pur)

**Interfaces:**
- Consumes: `run_arm` (Task 2) ; `compute_ab_verdict(rows, band)`.
- Produces: `compare(seeds, episodes, n_agents) -> dict{rows, verdict}` (diff = binding_gap ON − OFF).

- [ ] **Step 1: Écrire le test du verdict pur**

```python
def test_verdict_pure_on_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.30}, {"diff": 0.25}, {"diff": 0.40}]   # gap_ON - gap_OFF > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
```

- [ ] **Step 2: Lancer, vérifier le succès (compute_ab_verdict existe déjà)**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py::test_verdict_pure_on_binds_more -v`
Expected: PASS.

- [ ] **Step 3: Écrire `compare` + `__main__`**

Ajouter à `tools/torch_binary_gate_probe.py` :

```python
def compare(seeds=(0, 1, 2, 3), episodes=800, n_agents=64):
    """A/B apparie gate-binaire ON vs OFF par seed -> verdict (diff = binding_gap ON - OFF)."""
    rows = []
    for s in seeds:
        on = run_arm(True, episodes=episodes, n_agents=n_agents, seed=s)
        off = run_arm(False, episodes=episodes, n_agents=n_agents, seed=s)
        rows.append({"seed": s, "on": on["binding_gap"], "off": off["binding_gap"],
                     "on_comp": on["comp_rate"], "diff": on["binding_gap"] - off["binding_gap"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TBG_SEEDS", "0,1,2,3").split(","))
    episodes = int(os.environ.get("TBG_EPISODES", "800"))
    agents = int(os.environ.get("TBG_AGENTS", "64"))
    out = compare(seeds=seeds, episodes=episodes, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_OFF={r['off']:+.3f} "
              f"diff={r['diff']:+.3f} (comp_ON={r['on_comp']:.3f})")
    print("VERDICT:", out["verdict"])
    _label = {"GRADIENT_GAGNE": "GATE_BINAIRE_BINDE", "HEBBIEN_GAGNE": "OFF_BINDE_PLUS", "NEUTRE": "NEUTRE"}
    print("INTERPRETATION:", _label.get(out["verdict"]["verdict"], out["verdict"]["verdict"]))
```

- [ ] **Step 4: Lancer TOUT le fichier de test**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_probe.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run powered (le livrable de mesure)**

Run (PowerShell): `$env:TBG_SEEDS="0,1,2,3"; $env:TBG_EPISODES="800"; python tools/torch_binary_gate_probe.py`
Expected: 4 lignes seed + `VERDICT` + `INTERPRETATION`. Reporte les chiffres (gap_ON/gap_OFF/diff par seed + verdict) : c'est le résultat scientifique (le gate binaire binde-t-il throw sur le craft ?). Le monde est synthétique → quelques minutes.

- [ ] **Step 6: Commit (PATH-SCOPED)**

```bash
git add tools/torch_binary_gate_probe.py tests/sandbox/test_torch_binary_gate_probe.py
git commit -m "feat(G1): compare gate-binaire ON/OFF + verdict — instrument cran 2 brique A"
```

---

## Self-Review

**Spec coverage :**
- Monde 2-pas binaire (S1 craft, S2 throw binaire, énergie) → Task 1 (`_energy_binary`) + Task 2 (boucle). ✓
- Tête throw (w_throw/b_throw readout de H) → Task 2. ✓
- Gate ON (lit H) vs OFF (marginal) → Task 2 (`params` + branche `z`). ✓
- REINFORCE binaire + anti-saturation → Task 2 (`logp` Bernoulli + `antisat*pthrow.mean()²`). ✓
- W gelé (H détaché) → Task 2 (`H_S2 = pop.H.detach()`, `with torch.no_grad()` sur forward). ✓
- KPI binding_gap → Task 1 (`_binding_gap`) + Task 2/3. ✓
- Verdict compute_ab_verdict → Task 3. ✓
- Fichiers neufs / path-scopé → Global Constraints. ✓

**Placeholder scan :** aucun TBD/TODO ; tout le code est explicite. ✓

**Type consistency :** `_energy_binary(throw, did_craft, hunger)->float` ↔ appelé Task 2 ; `_binding_gap(throws, did_crafts)->float` ↔ Task 2 ; `run_arm(gate_on, episodes, n_agents, seed, lr, antisat)->dict{gate_on,binding_gap,comp_rate,throw_rate,...}` ↔ Task 3 ; `compare(seeds, episodes, n_agents)->{rows,verdict}` ↔ `__main__`. Imports (`CRAFT`,`_softmax_np`,`_MOVE`,`compute_ab_verdict`) vérifiés présents. ✓

## Hors scope (Brique B, suivi)
Câblage du gate binaire dans `world_1_stoneage.py` (biais sur `logits[8]` avant `do_throw`) ; KPI biosphère (kills-avec-outil, rétention craft) ; W entraîné (dégeler) ; promotion dans backend_torch.
