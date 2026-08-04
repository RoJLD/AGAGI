# Substrat bilinéaire — débloquer la composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un terme d'interaction BILINÉAIRE flag-gated au substrat `TorchPopulationModel._step` et PROUVER par calibration qu'il débloque la composition `(q+key)%K` (nulle sur le substrat plain), sans régression quand le flag est off.

**Architecture:** Le flag de classe `BILINEAR` (défaut False → bit-identique à l'actuel) suit le patron exact de `CONDITION_GATE` : params low-rank `U,V,W_bl` créés SEULEMENT si on, ajoutés à l'optimiseur, et un terme `((H·U)⊙(H·V))·W_bl` ajouté à l'excitation du `_step`. Une sonde de calibration entraîne `(q+key)%K` avec BILINEAR on/off et vérifie : positif (bilinéaire apprend), no-op (pur-rappel non régressé), régression (off bit-identique). Coût borné : smoke → run n=12 FOREGROUND.

**Tech Stack:** Python 3, torch (CPU), numpy, pytest. Modifie `src/agents/backend_torch.py` (CORE). Réutilise `MambaAgent`, `make_population`, `learn_episode`, `tools/demand_marker.ablation_verdict`.

## Global Constraints

- **Backward-compat NON-NÉGOCIABLE (verbatim)** : `BILINEAR=False` (défaut) → `TorchPopulationModel` BIT-IDENTIQUE à l'actuel : aucun param `U/V/W_bl` créé (restent `None`), `_step` ne calcule AUCUN terme bilinéaire. Prouver : (a) un test de RÉGRESSION qui compare un forward `BILINEAR=False` à la formule de référence `(1-δ)H+δtanh(H·W_off)` bit-à-bit ; (b) la suite substrat existante VERTE avant/après (`tests/` touchant `backend_torch`/`MambaAgent`/torch — repérer et lancer).
- **Flag de classe** : `BILINEAR = False`, `BILINEAR_RANK = 16` — comme `CONDITION_GATE`/`GATE_TARGET` (activable par un banc via `TorchPopulationModel.BILINEAR = True`, off partout ailleurs). Toujours restaurer dans un `try/finally` côté sonde.
- **Forme low-rank (verbatim)** : `U,V` de `(B,N,r)`, `W_bl` de `(B,r,N)` ; `bilinear(H) = ((H·U)⊙(H·V))·W_bl` → `(B,N)` ajouté à l'excitation DANS le tanh. Init les TROIS en petit-aléatoire (`~0.1·randn`) — PAS `W_bl=0` (gèlerait le gradient de U/V). Params créés dans `__init__` seulement si `BILINEAR`, ajoutés à `params` avant `self.opt`.
- **Optimiseur côté sonde** : quand `BILINEAR`, la sonde DOIT inclure les params bilinéaires : `Adam([agent.W, agent.U, agent.V, agent.W_bl], lr=lr)` (sinon ils n'apprennent pas). Vérifier que `learn_episode`/`forward` restent différentiables via les nouveaux params (le gradient circule par `_step`).
- **Étalon = composition `(q+key)%K`** (le finding LANG-MEMORY : plain nul 0.15-0.33). No-op = pur-rappel (plain apprend ~0.88). floor=1/K, seuil d'émergence `1/K+0.15`≈0.32 (K=6).
- **Nommage cliquet** : `run_bilinear_composition_probe` (motif `run_*probe`) → `CALIBRATED`. Helpers privés préfixe `_`.
- **Bornage** : pur torch CPU, aucun bail `kuzu`, aucun monde. Pré-vol `declare_design`. SMOKE d'abord ; run-verdict n=12 **FOREGROUND** borné (< ~9 min ; leçons SP-2/MEM-PERCEPTION). Persister accuracies + `_params`. Provenance : fonction calibrée réelle.
- **Commits path-scoped** (JAMAIS `-A`), arbre partagé, stash-contingency, jamais `--no-verify`. Branche `feat/d1-prod-pairing`.

## File Structure

- `src/agents/backend_torch.py` (MODIFIÉ, Task 1) — flag `BILINEAR` + params + terme `_step`. CORE.
- `tests/test_bilinear_substrate.py` (NOUVEAU, Task 1) — régression bit-identique off + présence params on.
- `tools/bilinear_composition_probe.py` (NOUVEAU, Task 2) — sonde de calibration.
- `tests/test_bilinear_composition_probe.py` (NOUVEAU, Task 2) — smoke unitaire.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ, Task 2) — CALIBRATED + cas positif/no-op.
- `results/bilinear_composition.json` (NOUVEAU, Task 3).
- `docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md` (NOUVEAU, Task 3).

---

### Task 1: Terme bilinéaire flag-gated dans le substrat (CORE) + backward-compat

**Files:**
- Modify: `src/agents/backend_torch.py`
- Create: `tests/test_bilinear_substrate.py`

**Interfaces:**
- Consumes: `TorchPopulationModel.__init__` (crée `self.W` (B,N,N), gate params, `self.opt`), `_step(obs_t, H_in)` (excitation `torch.bmm(H.unsqueeze(1), W_off).squeeze(1)`).
- Produces: flag `BILINEAR`/`BILINEAR_RANK` ; attributs `self.U/V/W_bl` (None si off) ; terme bilinéaire dans `_step`.

- [ ] **Step 1: Écrire le test de régression + présence params (qui échoue)**

Create `tests/test_bilinear_substrate.py`:

```python
import pytest

pytest.importorskip("torch")
import numpy as np
import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def _pop(n=4, seed=0):
    np.random.seed(seed); torch.manual_seed(seed)
    return make_population([MambaAgent() for _ in range(n)], backend="torch")


def test_bilinear_off_is_bit_identical_reference():
    """BILINEAR=False (défaut) : _step == formule de référence (1-δ)H+δtanh(H·W_off), bit-à-bit."""
    assert TorchPopulationModel.BILINEAR is False   # défaut off
    m = _pop()
    assert m.U is None and m.V is None and m.W_bl is None
    H = torch.randn(m.B, m.N)
    obs = torch.randn(m.B, m.I)
    got = m._step(obs, H)
    # référence explicite
    Href = H.clone(); Href[:, :m.I] = obs
    diag = torch.diagonal(m.W, dim1=1, dim2=2)
    delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
    W_off = m.W * (1.0 - m._eye)
    exc = torch.bmm(Href.unsqueeze(1), W_off).squeeze(1)
    ref = (1.0 - delta) * Href + delta * torch.tanh(exc)
    assert torch.equal(got, ref), "BILINEAR=False doit être bit-identique à la référence"


def test_bilinear_on_creates_params_and_changes_step():
    """BILINEAR=True : params U/V/W_bl créés (bonnes formes), et _step diffère de la référence linéaire."""
    saved = TorchPopulationModel.BILINEAR
    TorchPopulationModel.BILINEAR = True
    try:
        m = _pop()
        r = TorchPopulationModel.BILINEAR_RANK
        assert m.U.shape == (m.B, m.N, r) and m.V.shape == (m.B, m.N, r) and m.W_bl.shape == (m.B, r, m.N)
        assert all(p.requires_grad for p in (m.U, m.V, m.W_bl))
        assert any(p is m.U for p in m.opt.param_groups[0]["params"])   # dans l'optimiseur par défaut
        H = torch.randn(m.B, m.N); obs = torch.randn(m.B, m.I)
        got = m._step(obs, H)
        Href = H.clone(); Href[:, :m.I] = obs
        diag = torch.diagonal(m.W, dim1=1, dim2=2); delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
        exc = torch.bmm(Href.unsqueeze(1), (m.W * (1.0 - m._eye))).squeeze(1)
        lin_ref = (1.0 - delta) * Href + delta * torch.tanh(exc)
        assert not torch.equal(got, lin_ref), "BILINEAR=True doit ajouter un terme (≠ linéaire)"
    finally:
        TorchPopulationModel.BILINEAR = saved
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_bilinear_substrate.py -v`
Expected: FAIL (`AttributeError: ... 'U'` / `BILINEAR` absent).

- [ ] **Step 3: Ajouter le flag + params (backend_torch.py)**

In `src/agents/backend_torch.py`, add class flags near `CONDITION_GATE` (après `GATE_SCALE`) :

```python
    BILINEAR = False         # terme d'interaction bilinéaire low-rank dans _step (débloque la composition).
    BILINEAR_RANK = 16       # rang r du bilinéaire ((H·U)⊙(H·V))·W_bl ; params créés SEULEMENT si BILINEAR.
```

In `__init__`, AFTER the gate params block (après le `self.opt = ...`? NON — AVANT, pour inclure dans `params`). Insérer JUSTE avant `self.opt = torch.optim.SGD(params, lr=lr)` :

```python
        # Terme bilinéaire low-rank (flag BILINEAR) : params créés seulement si activé, sinon None (chemin
        # prod bit-identique). Init petit-aléatoire pour les TROIS (W_bl=0 gèlerait le gradient de U,V).
        self.U = self.V = self.W_bl = None
        if type(self).BILINEAR:
            r = int(type(self).BILINEAR_RANK)
            self.U = (0.1 * torch.randn(self.B, self.N, r, device=self.device)).detach().requires_grad_(True)
            self.V = (0.1 * torch.randn(self.B, self.N, r, device=self.device)).detach().requires_grad_(True)
            self.W_bl = (0.1 * torch.randn(self.B, r, self.N, device=self.device)).detach().requires_grad_(True)
            params += [self.U, self.V, self.W_bl]
```

(Note : mettre `self.U = self.V = self.W_bl = None` AUSSI dans le early-return `if self.B == 0:` — ligne ~67 — pour que l'attribut existe toujours.)

- [ ] **Step 4: Ajouter le terme dans `_step`**

In `_step`, REPLACE the excitation line + return:

```python
        excitation = torch.bmm(H.unsqueeze(1), W_off).squeeze(1)   # (B,N) = H · W_off
        if type(self).BILINEAR and self.W_bl is not None:
            hu = torch.bmm(H.unsqueeze(1), self.U).squeeze(1)      # (B,r)
            hv = torch.bmm(H.unsqueeze(1), self.V).squeeze(1)      # (B,r)
            excitation = excitation + torch.bmm((hu * hv).unsqueeze(1), self.W_bl).squeeze(1)  # (B,N)
        return (1.0 - delta) * H + delta * torch.tanh(excitation)
```

- [ ] **Step 5: Lancer le test + la suite substrat existante (backward-compat)**

Run: `python -m pytest tests/test_bilinear_substrate.py -v`
Expected: PASS (off bit-identique, on crée params + change _step).

Run: repérer et lancer la suite substrat existante — p.ex. `python -m pytest tests/ -k "torch or backend or mamba or substrate" -q` (ajuster au repo). Expected: VERTE (le flag off ne change RIEN). Si un test casse, le flag off n'est pas bit-identique → corriger avant de continuer.

- [ ] **Step 6: Commit**

```bash
git add src/agents/backend_torch.py tests/test_bilinear_substrate.py
git status --short   # UNIQUEMENT ces deux chemins
git commit -m "feat(BILINEAR): terme d'interaction bilineaire low-rank flag-gated dans _step (off=bit-identique)"
```

---

### Task 2: Sonde de calibration (plain vs bilinéaire sur la composition) + smoke

**Files:**
- Create: `tools/bilinear_composition_probe.py`
- Create: `tests/test_bilinear_composition_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py`

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `learn_episode`, `TorchPopulationModel.BILINEAR`.
- Produces: `run_bilinear_composition_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02, rank=16, task="composition") -> dict` renvoyant `{"plain_median": float, "bilinear_median": float, "unlocked": bool, "per_seed": {"plain": [...], "bilinear": [...]}, "task": str, "n": int}`.

- [ ] **Step 1: Écrire le smoke unitaire (qui échoue)**

Create `tests/test_bilinear_composition_probe.py`:

```python
import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, rank=8)
    assert set(r) >= {"plain_median", "bilinear_median", "unlocked", "per_seed"}
    assert r["n"] == 2 and len(r["per_seed"]["plain"]) == 2 and len(r["per_seed"]["bilinear"]) == 2
    assert isinstance(r["unlocked"], bool)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_bilinear_composition_probe.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implémenter la sonde**

Create `tools/bilinear_composition_probe.py` (VÉRIFIER les interfaces substrat en implémentant) :

```python
"""Calibration : le terme BILINÉAIRE du substrat débloque-t-il la composition (q+key)%K ?

Étalon connu (finding LANG-MEMORY) : le substrat PLAIN est NUL sur (q+key)%K (0.15-0.33). On entraîne la MÊME
tâche avec TorchPopulationModel.BILINEAR off puis on, et on compare : `unlocked` ssi plain nul ET bilinéaire
apprend. Contrôle NO-OP : task='recall' (pur-rappel, que le plain apprend) doit ENCORE marcher en bilinéaire
(pas de régression). Le nom run_*probe trippe le cliquet -> calibré. Pur torch CPU, aucun bail.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def _slot(idx, K, offset, I, n):
    m = np.zeros((n, I), dtype=np.float32)
    m[np.arange(n), offset + (idx % K)] = 1.0
    return m


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True); e = np.exp(z); return e / e.sum(axis=1, keepdims=True)


def _sample(preds, K, rng, n):
    p = _softmax(np.asarray(preds)[:, :K]); return np.array([rng.choice(K, p=pi) for pi in p])


def _train_eval_one(seed, bilinear, task, episodes, n_agents, K, lr, rank, eval_batches=40):
    """Entraîne la tâche (composition (q+key)%K OU recall=key) avec BILINEAR on/off ; renvoie l'accuracy éval."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed); torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = bool(bilinear)
    TorchPopulationModel.BILINEAR_RANK = int(rank)
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        params = [agent.W]
        if bilinear:
            params += [agent.U, agent.V, agent.W_bl]           # inclure les params bilinéaires
        agent.opt = torch.optim.Adam(params, lr=lr)

        def _target(key, q):
            return (q + key) % K if task == "composition" else key   # recall = key seul (no-op)

        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
            enc = _slot(key, K, 0, I, n_agents)
            use = _slot(q, K, K, I, n_agents) if task == "composition" else np.zeros((n_agents, I), np.float32)
            seq = [enc, use]                                   # encode(key) puis usage(query) ; 1 pas de portage
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in seq:
                logits, _ = agent.forward(x)
            guess = _sample(logits, K, rng, n_agents)
            tgt = _target(key, q)
            adv = (guess == tgt).astype(np.float32); adv = adv - adv.mean()
            acts = [[{"move": 0} for _ in range(n_agents)], [{"move": int(g)} for g in guess]]
            agent.learn_episode(seq, acts, adv, gate_last_only=True)

        hits = []
        for _ in range(eval_batches):
            key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
            enc = _slot(key, K, 0, I, n_agents)
            use = _slot(q, K, K, I, n_agents) if task == "composition" else np.zeros((n_agents, I), np.float32)
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in (enc, use):
                logits, _ = agent.forward(x)
            g = np.asarray(logits)[:, :K].argmax(axis=1)
            hits.append((g == _target(key, q)).astype(np.float32))
        return float(np.mean(np.concatenate(hits)))
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK) = saved


def run_bilinear_composition_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02, rank=16, task="composition"):
    """Compare le substrat PLAIN vs BILINÉAIRE sur la tâche. `unlocked` ssi plain nul ET bilinéaire apprend."""
    plain, bil = [], []
    for s in seeds:
        plain.append(_train_eval_one(s, False, task, episodes, n_agents, K, lr, rank))
        bil.append(_train_eval_one(s, True, task, episodes, n_agents, K, lr, rank))
    bar = 1.0 / K + 0.15
    pm, bm = float(np.median(plain)), float(np.median(bil))
    unlocked = (pm <= bar) and (bm > bar)
    return {"plain_median": pm, "bilinear_median": bm, "unlocked": unlocked,
            "per_seed": {"plain": plain, "bilinear": bil}, "task": task, "n": len(seeds)}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("BL_SEEDS", "12"))))
    r = run_bilinear_composition_probe(seeds, episodes=int(os.environ.get("BL_EPISODES", "1500")))
    print(json.dumps({k: v for k, v in r.items() if k != "per_seed"}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Lancer le smoke unitaire**

Run: `python -m pytest tests/test_bilinear_composition_probe.py -v`
Expected: PASS (forme, n=2). Si échec d'interface (params bilinéaires dans l'opt, forward différentiable), corriger d'après le code réel et re-signaler.

- [ ] **Step 5: Déclarer calibré + calibration (positif + no-op)**

In `tests/sandbox/test_instrument_calibration.py`, add to `CALIBRATED`:

```python
    # Le terme BILINÉAIRE débloque-t-il la composition ? Positif = (q+key)%K passe de NUL (plain) à APPRIS
    # (bilinéaire) ; no-op = pur-rappel non régressé en bilinéaire. Générateur A (le levier produit les 2 issues).
    "run_bilinear_composition_probe": ["*"],
```

Append:

```python
def test_bilinear_unlocks_composition():
    """POSITIF (générateur A) : sur (q+key)%K, plain NUL et bilinéaire APPREND -> unlocked. n=12."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=list(range(12)), episodes=1500, n_agents=16, K=6, task="composition")
    assert r["plain_median"] <= 1/6 + 0.15, r          # plain reste nul (reproduit le finding)
    assert r["bilinear_median"] > 1/6 + 0.15 and r["unlocked"], r


def test_bilinear_noop_on_recall():
    """NO-OP : le pur-rappel (que le plain apprend déjà) reste appris en bilinéaire (pas de régression)."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=list(range(12)), episodes=1500, n_agents=16, K=6, task="recall")
    assert r["bilinear_median"] > 1/6 + 0.15, r        # bilinéaire n'abîme pas le rappel
```

Note : ces cas ENTRAÎNENT (pas de bypass agent) → plus lents que les autres calibrations. Si > ~3 min/cas, réduire `episodes`/`n_agents` DANS le test au strict nécessaire pour trancher (le positif a besoin que le bilinéaire dépasse le seuil, pas d'un score parfait). Documenter le budget choisi.

- [ ] **Step 6: Lancer calibration + cliquet**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k "bilinear_unlocks or bilinear_noop" -v`
Expected: PASS (positif : unlocked ; no-op : rappel non régressé).
Run: `python tools/check_instrument_calibration.py` → `OK`.

- [ ] **Step 7: Commit (FUSIONNÉ)**

```bash
git add tools/bilinear_composition_probe.py tests/test_bilinear_composition_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # UNIQUEMENT ces trois chemins
git commit -m "feat(BILINEAR): sonde calibration composition (plain nul vs bilineaire appris) + no-op recall (cliquet)"
```

Si le hook bloque sur un instrument étranger : stash path-scoped, commit, pop, vérifier — jamais `--no-verify`.

---

### Task 3: Run-verdict (n=12, FOREGROUND) + record

**Files:**
- Create: `results/bilinear_composition.json`
- Create: `docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md`

**Interfaces:**
- Consumes: `run_bilinear_composition_probe` (Task 2).
- Produces: le verdict persisté + le record (positif si unlocked, négatif sinon).

- [ ] **Step 1: Pré-vol + SMOKE (mécanisme + débit)**

Run: `python -c "import time,json; from tools.bilinear_composition_probe import run_bilinear_composition_probe as R; t=time.time(); r=R(seeds=[0,1,2], episodes=600, n_agents=16, K=6, rank=16); print('dt_s=%.1f' % (time.time()-t)); print('plain_med', round(r['plain_median'],3), 'bilinear_med', round(r['bilinear_median'],3), 'unlocked', r['unlocked'])"`

Attendu (smoke, 3 seeds) : `dt_s` (débit), `plain_med` ≤ 0.32 (reste nul), `bilinear_med` tend > 0.32. ⚠️ n<12 ne tranche pas.

**Décision de bornage** : si n=12 projette > ~9 min, réduire `episodes`/`n_agents`. Si le bilinéaire n'apprend PAS au smoke, augmenter `episodes`/`rank` (tuner) — mais si robustement ≤ 0.32, c'est un VRAI nul (le low-rank ne suffit pas), à graver honnêtement (ne pas gonfler `rank` sans borne).

- [ ] **Step 2: Run-verdict n=12 (FOREGROUND, borné) + persister**

⚠️ FOREGROUND. Si promu en bg, bloquer dessus, ne pas dupliquer.

Run (ajuster d'après le smoke) :
`python -c "import json; from tools.bilinear_composition_probe import run_bilinear_composition_probe as R; r=R(seeds=list(range(12)), episodes=1500, n_agents=16, K=6, rank=16); r['_params']={'episodes':1500,'n_agents':16,'K':6,'lr':0.02,'rank':16,'seeds':12}; json.dump(r, open('results/bilinear_composition.json','w'), indent=2); print('plain_med', round(r['plain_median'],3), 'bilinear_med', round(r['bilinear_median'],3), 'unlocked', r['unlocked']); print('plain_seeds', sorted(r['per_seed']['plain'])); print('bilinear_seeds', sorted(r['per_seed']['bilinear']))"`

Attendu : `unlocked True` (plain ≤ 0.32, bilinéaire > 0.32 avec marge + séparation par-seed). Persisté dans `results/bilinear_composition.json`.

**Si `unlocked` False** (bilinéaire ≤ 0.32 robuste) : VRAI nul → record NÉGATIF honnête (le bilinéaire low-rank de ce design ne suffit pas ; le mur est plus profond, ou rang/budget insuffisant). Ne pas forcer.

- [ ] **Step 3: Écrire le record**

Create `docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md` (valeurs réelles) :

```markdown
---
id: EDR-BILINEAR
type: EDR
title: "Le terme d'interaction BILINÉAIRE débloque la composition (q+key)%K que le substrat affine ne pouvait pas apprendre — attaque directe du verrou dominant (SOTA-gap)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question
Le finding LANG-MEMORY a établi que la composition (q+key)%K N'ÉMERGE PAS sur le substrat affine
(H_new=(1-δ)H+δtanh(H·W_off)) — mur de composition/binding, verrou DOMINANT (SOTA-gap). Un terme
d'interaction BILINÉAIRE low-rank suffit-il à le débloquer ?

## Méthode
Terme `((H·U)⊙(H·V))·W_bl` (rang r=RANG) ajouté à l'excitation du `_step`, flag-gated (`BILINEAR`, off =
bit-identique, prouvé par régression). Sonde calibrée : MÊME tâche (q+key)%K entraînée avec BILINEAR off vs on,
n=12 seeds. No-op : pur-rappel non régressé. Étalon connu (plain nul, finding LANG-MEMORY).

## Résultat
PLAIN : nul (médiane P_REEL ≤ 1/K+0.15, reproduit le finding). BILINÉAIRE : APPREND (médiane B_REEL > seuil,
marge + séparation par-seed). No-op rappel : non régressé. Régression off : bit-identique. Donc **le terme
bilinéaire débloque la composition** — la classe de fonctions manquante était les PRODUITS d'unités, comme le
prédisait le précédent planner-depth1 (compo affine échouait jusqu'à un terme bilinéaire).

## Portée (bornée)
Montre la CAPACITÉ (entraînement direct par crédit épisodique), PAS l'émergence évolutive in-world (le NAS
active-t-il le bilinéaire ? hors scope). Proxy (q+key)%K, ce rang, ces budgets. Le substrat bilinéaire est
flag-gated (off partout ailleurs — chemin prod intact).

## Ce que ça débloque
Le verrou DOMINANT (composition) cède à un terme bilinéaire. Rouvre `language→memory` (l'antécédent langage
peut maintenant émerger) et la vraie généralisation (application de règle) — sous-projets suivants.
Cf. `docs/superpowers/specs/2026-08-03-bilinear-substrate-composition-design.md`.
```

Remplacer `RANG`/`P_REEL`/`B_REEL`. **Si nul** : record NÉGATIF (le bilinéaire low-rank ne débloque pas ; ne pas graver un positif).

- [ ] **Step 4: Valider**

Run: `python tools/check_record_links.py` (EDR-BILINEAR non-orphelin)
Run: `python -m pytest tests/test_bilinear_substrate.py tests/test_bilinear_composition_probe.py -q` (verts)
Run: `python tools/check_instrument_calibration.py` (OK)
Run: `python tools/check_agi_taxonomy.py` (2 arêtes inchangées — ce sous-projet n'en ajoute pas)

- [ ] **Step 5: Commit**

```bash
git add results/bilinear_composition.json docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md
git status --short   # UNIQUEMENT ces deux chemins
git commit -m "feat(BILINEAR): verdict n=12 -- le bilineaire debloque la composition (q+key)%K + record"
```

Si `results/` gitignored : `git add -f`. Stash-contingency fichier étranger si besoin.

---

## Self-Review

**Spec coverage :**
- §3 modif substrat (flag BILINEAR + params low-rank conditionnels + terme _step) → Task 1. ✓ (init petit-aléatoire les 3, pas W_bl=0 — raffinement noté : W_bl=0 gèle U/V.)
- §4 calibration (positif composition + no-op rappel, générateur A) → Task 2 (2 cas + CALIBRATED). ✓
- §5 backward-compat (off bit-identique + suite existante) → Task 1 Step 1 (régression) + Step 5 (suite). ✓
- §6 verdict (unlocked, n=12) + finding négatif → Task 3 Steps 2-3. ✓
- §7 bornage (smoke, FOREGROUND borné, persister _params, provenance) → Task 3. ✓
- §8 livrable (substrat + sonde + record, PAS d'arête) → Tasks 1-3. ✓

**Placeholder scan :** valeurs à mesurer (RANG/P_REEL/B_REEL) marquées explicitement, remplies au run. Aucun TODO code.

**Type consistency :** `run_bilinear_composition_probe(seeds, episodes, n_agents, K, lr, rank, task)` renvoie `{plain_median, bilinear_median, unlocked, per_seed:{plain,bilinear}, task, n}` — identique en Task 2 (tests) et Task 3 (run). Le flag `BILINEAR`/params `U/V/W_bl` de Task 1 sont consommés par la sonde de Task 2 (opt inclut U/V/W_bl si bilinéaire). Helpers privés `_slot/_softmax/_sample/_train_eval_one` — aucun ne matche un motif cliquet. ✓
