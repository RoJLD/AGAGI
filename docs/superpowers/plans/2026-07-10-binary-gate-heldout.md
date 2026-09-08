# Gate binaire held-out sans confond (cran 2, Brique B1) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trancher si le gate binaire binde throw sur un contexte réellement présent (did_craft dans l'obs), généralise (held-out) et est spécifique (bat le shuffle) — sans le confond de mémorisation d'EDR-169.

**Architecture:** Harnais autonome (fichier neuf) : monde 2-pas à obs VARIABLES par épisode, S1 stochastique, did_craft encodé dans `obs_b[:,0]`. Phase TRAIN (readout entraîné) puis HELD-OUT TEST (readout gelé, obs fraîches). Bras ON-vrai vs SHUFFLE (label de récompense permuté). KPI = binding_gap held-out.

**Tech Stack:** Python, PyTorch, numpy, pytest. Réutilise `torch_binary_gate_probe` (`_energy_binary`, `_binding_gap`), `compositional_world_probe` (`_softmax_np`, `CRAFT`, `_MOVE`), `substrate_ab` (`compute_ab_verdict`).

## Global Constraints

- **Fichiers NEUFS uniquement** : `tools/torch_binary_gate_heldout_probe.py` et `tests/sandbox/test_torch_binary_gate_heldout_probe.py`. NE PAS toucher `backend_torch.py` (sessions //).
- **Commits PATH-SCOPED** : `git add` UNIQUEMENT ces 2 fichiers. JAMAIS `git add -A`.
- **W gelé** : `pop.H` détaché + `torch.no_grad()` sur les forward → gradient seulement via `w_throw`/`b_throw`.
- **Style** : français, concis, pas d'emojis. Shell PowerShell (Windows). Tests via `python -m pytest ...`.
- **Paramètres validés par smoke** : `train_ep=1200` (400 sous-entraîne : held-out gap 0.02 vs 0.74 à 1200), `test_ep=100`, `n_agents=128`, `signal_amp=3.0`, `lr=0.05`, `antisat=6.0`.
- **Les 3 corrections d'EDR-169** : obs re-tirées par épisode (RandomState qui avance) ; S1 échantillonné (`rng.choice`, pas argmax) ; `did_craft` encodé dans `obs_b[:,0] = did*signal_amp`.
- **Shuffle** = permute le LABEL DE RÉCOMPENSE (pas le contexte dans obs_b) ; held-out gap mesuré sur le VRAI did_craft. ON → récompense suit le contexte → gap élevé ; SHUFFLE → récompense décorrélée → gap ~0.

---

### Task 1: `run_arm` — train + held-out, ON/shuffle

**Files:**
- Create: `tools/torch_binary_gate_heldout_probe.py`
- Create: `tests/sandbox/test_torch_binary_gate_heldout_probe.py`

**Interfaces produites:** `run_arm(shuffle_reward=False, train_ep=1200, test_ep=100, n_agents=128, seed=0, lr=0.05, antisat=6.0, signal_amp=3.0) -> dict` avec clés `shuffle_reward`, `seed`, `binding_gap_heldout`, `comp_rate_heldout`, `throw_rate_heldout`.

- [ ] **Step 1: Écrire le smoke test**

```python
# tests/sandbox/test_torch_binary_gate_heldout_probe.py
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_arm_smoke_true_and_shuffle():
    from tools.torch_binary_gate_heldout_probe import run_arm
    r_true = run_arm(shuffle_reward=False, train_ep=80, test_ep=30, n_agents=32, seed=0)
    r_shuf = run_arm(shuffle_reward=True, train_ep=80, test_ep=30, n_agents=32, seed=0)
    for r in (r_true, r_shuf):
        assert set(["shuffle_reward", "binding_gap_heldout", "comp_rate_heldout", "throw_rate_heldout"]).issubset(r)
        assert -1.0 <= r["binding_gap_heldout"] <= 1.0
        assert 0.0 <= r["throw_rate_heldout"] <= 1.0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_heldout_probe.py -v`
Expected: FAIL (`ModuleNotFoundError` / `ImportError: run_arm`).

- [ ] **Step 3: Écrire l'en-tête + `run_arm`**

```python
# tools/torch_binary_gate_heldout_probe.py
"""Gate binaire, test HELD-OUT sans confond (cran 2, Brique B1). EDR-169 a montre que le harnais binaire
a obs FIXES confond binding et memorisation. Ici : obs VARIABLES par episode + S1 stochastique + did_craft
encode dans obs_b[:,0] (simule le spear-en-inventaire) + HELD-OUT (readout gele, obs fraiches). Le vrai
verdict = gap_heldout(ON) vs gap_heldout(SHUFFLE label de recompense). Ne touche NI backend_torch NI la
biosphere. Reutilise le monde/energie de torch_binary_gate_probe (DRY).

Usage : python tools/torch_binary_gate_heldout_probe.py   (env: TBH_SEEDS, TBH_TRAIN, TBH_TEST, TBH_AGENTS)
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
from tools.torch_binary_gate_probe import _energy_binary, _binding_gap
from tools.substrate_ab import compute_ab_verdict


def run_arm(shuffle_reward=False, train_ep=1200, test_ep=100, n_agents=128, seed=0,
            lr=0.05, antisat=6.0, signal_amp=3.0):
    """Monde 2-pas a obs VARIABLES. S1 stochastique -> did_craft ; obs_b[:,0]=did*signal_amp (contexte
    dans l'etat). TRAIN : readout w_throw/b_throw entraine par REINFORCE binaire + anti-sat ; le label de
    RECOMPENSE est le vrai did_craft (ON) ou une PERMUTATION FIXE (shuffle_reward -> decorrele du contexte).
    HELD-OUT : readout gele, obs FRAICHES, binding_gap mesure sur le VRAI did_craft. W gele (H detache).
    ON -> la recompense suit le contexte -> gap eleve ; SHUFFLE -> gap ~0 (rien a apprendre de generalisant)."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
    N, I = pop.N, pop.I
    w_throw = torch.zeros(N, requires_grad=True)
    b_throw = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w_throw, b_throw], lr=lr)
    rng = np.random.RandomState(seed + 1)
    perm = np.random.RandomState(seed + 7).permutation(n_agents)   # permutation FIXE du label de recompense

    def _episode(update):
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        pop.H = torch.zeros((n_agents, pop.N))
        with torch.no_grad():
            p1, _ = pop.forward(obs_a)
        probs = _softmax_np(np.asarray(p1)[:, :_MOVE])
        move1 = np.array([rng.choice(_MOVE, p=pi) for pi in probs])   # S1 STOCHASTIQUE
        did_craft = (move1 == CRAFT)
        obs_b[:, 0] = did_craft.astype(np.float32) * signal_amp        # contexte dans l'obs
        with torch.no_grad():
            pop.forward(obs_b)
        H_S2 = pop.H.detach()
        z = H_S2 @ w_throw + b_throw
        pthrow = torch.sigmoid(torch.clamp(z, -10.0, 10.0))
        throw = (pthrow.detach() > torch.rand(n_agents)).float()
        reward_label = did_craft[perm] if shuffle_reward else did_craft   # SHUFFLE = recompense decorrelee
        energy = np.array([_energy_binary(bool(throw[i]), bool(reward_label[i]))
                           for i in range(n_agents)], dtype=np.float32)
        if update:
            ret = torch.tensor(energy - energy.mean())
            logp = throw * torch.log(pthrow + 1e-6) + (1 - throw) * torch.log(1 - pthrow + 1e-6)
            loss = -(ret * logp).mean() + antisat * pthrow.mean() ** 2
            opt.zero_grad()
            loss.backward()
            opt.step()
        return throw.detach().numpy(), did_craft            # gap TOUJOURS sur le VRAI did_craft

    for _ in range(train_ep):
        _episode(update=True)
    th, cr = [], []
    for _ in range(test_ep):                                # HELD-OUT : readout gele, obs fraiches
        t, d = _episode(update=False)
        th.append(t)
        cr.append(d)
    th = np.concatenate(th)
    cr = np.concatenate(cr)
    return {"shuffle_reward": bool(shuffle_reward), "seed": int(seed),
            "binding_gap_heldout": _binding_gap(th, cr),
            "comp_rate_heldout": float(np.mean(th * cr)),
            "throw_rate_heldout": float(np.mean(th))}
```

- [ ] **Step 4: Lancer TOUT le fichier, vérifier PASS**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_heldout_probe.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit (PATH-SCOPED)**

```bash
git add tools/torch_binary_gate_heldout_probe.py tests/sandbox/test_torch_binary_gate_heldout_probe.py
git commit -m "feat(G1): run_arm gate binaire held-out (obs variables + did dans obs + train/test) — cran 2 B1"
```

---

### Task 2: `compare` + verdict + run powered (le livrable)

**Files:**
- Modify: `tools/torch_binary_gate_heldout_probe.py` (ajouter `compare` + `__main__`)
- Modify: `tests/sandbox/test_torch_binary_gate_heldout_probe.py` (test du verdict pur)

**Interfaces:**
- Consumes: `run_arm` (Task 1) ; `compute_ab_verdict(rows, band)`.
- Produces: `compare(seeds, train_ep, test_ep, n_agents) -> dict{rows, verdict}` (diff = gap_heldout ON − SHUFFLE).

- [ ] **Step 1: Écrire le test du verdict pur**

```python
def test_verdict_pure_true_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.60}, {"diff": 0.70}, {"diff": 0.55}]   # gap ON - gap SHUFFLE > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
```

- [ ] **Step 2: Lancer, vérifier le succès (compute_ab_verdict existe déjà)**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_heldout_probe.py::test_verdict_pure_true_binds_more -v`
Expected: PASS.

- [ ] **Step 3: Écrire `compare` + `__main__`**

```python
def compare(seeds=(0, 1, 2, 3), train_ep=1200, test_ep=100, n_agents=128):
    """A/B apparie held-out : gap(ON vrai) vs gap(SHUFFLE label de recompense) par seed -> verdict.
    diff>0 sur held-out = le gate binaire binde un contexte PRESENT, generalise, et est SPECIFIQUE
    (pas de memorisation, distinct du shuffle)."""
    rows = []
    for s in seeds:
        t = run_arm(False, train_ep=train_ep, test_ep=test_ep, n_agents=n_agents, seed=s)
        sh = run_arm(True, train_ep=train_ep, test_ep=test_ep, n_agents=n_agents, seed=s)
        rows.append({"seed": s, "on": t["binding_gap_heldout"], "shuffle": sh["binding_gap_heldout"],
                     "on_comp": t["comp_rate_heldout"], "diff": t["binding_gap_heldout"] - sh["binding_gap_heldout"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TBH_SEEDS", "0,1,2,3").split(","))
    train_ep = int(os.environ.get("TBH_TRAIN", "1200"))
    test_ep = int(os.environ.get("TBH_TEST", "100"))
    agents = int(os.environ.get("TBH_AGENTS", "128"))
    out = compare(seeds=seeds, train_ep=train_ep, test_ep=test_ep, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_SHUF={r['shuffle']:+.3f} "
              f"diff={r['diff']:+.3f} (comp_ON={r['on_comp']:.3f})")
    print("VERDICT:", out["verdict"])
    _label = {"GRADIENT_GAGNE": "BINDING_REEL_HELDOUT", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PAS_DE_BINDING_HELDOUT"}
    print("INTERPRETATION:", _label.get(out["verdict"]["verdict"], out["verdict"]["verdict"]))
```

- [ ] **Step 4: Lancer TOUT le fichier de test**

Run: `python -m pytest tests/sandbox/test_torch_binary_gate_heldout_probe.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit (PATH-SCOPED) — le run powered est lancé par le contrôleur**

```bash
git add tools/torch_binary_gate_heldout_probe.py tests/sandbox/test_torch_binary_gate_heldout_probe.py
git commit -m "feat(G1): compare held-out ON vs SHUFFLE + verdict — instrument cran 2 B1"
```

> NOTE exécutant : NE lance PAS le run powered (`python tools/torch_binary_gate_heldout_probe.py`) — le contrôleur le lance lui-même après (train_ep=1200 × 4 seeds × 2 bras ≈ plusieurs minutes). Fais Steps 1-5 uniquement.

---

## Self-Review

**Spec coverage :**
- Obs variables par épisode → Task 1 (`obs_a/obs_b` re-tirées dans `_episode`). ✓
- S1 stochastique → Task 1 (`rng.choice`, pas argmax). ✓
- did_craft dans obs_b → Task 1 (`obs_b[:,0] = did*signal_amp`). ✓
- Held-out (train puis test gelé, obs fraîches) → Task 1 (2 boucles, `update=False` en test). ✓
- Shuffle = label de récompense permuté, gap sur vrai did_craft → Task 1 (`reward_label`, `return ... did_craft`). ✓
- W gelé → Task 1 (`H_S2 = pop.H.detach()`, `no_grad` forward). ✓
- KPI binding_gap held-out + verdict → Task 1 + Task 2. ✓
- DRY (réutilise `_energy_binary`/`_binding_gap`) → import Task 1. ✓
- Fichiers neufs / path-scopé → Global Constraints. ✓

**Placeholder scan :** aucun TBD/TODO ; tout le code est explicite. ✓

**Type consistency :** `run_arm(shuffle_reward, train_ep, test_ep, n_agents, seed, lr, antisat, signal_amp)->dict{binding_gap_heldout,...}` (Task 1) ↔ consommé Task 2 ; `compare(seeds, train_ep, test_ep, n_agents)->{rows,verdict}` ↔ `__main__`. Imports vérifiés présents. ✓

## Hors scope (B2, suivi)
Câblage biosphère (`world_1_stoneage.py`, gate sur `logits[8]`, did_craft = spear en inventaire réel, KPI kills-avec-outil) ; contexte distribué via la vraie dynamique.
