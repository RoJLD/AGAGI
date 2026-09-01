# Diagnostic retain+compose Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trancher par un diagnostic CHEAP si le mur retain+compose (retenir key PUIS composer avec q) est la RÉTENTION apprise (H1) ou la lecture d'un état porté (H2), via 3 conditions bilinéaire+supervisé : same_tick (baseline), oracle (key injecté en état caché), learned (2-tick).

**Architecture:** Une sonde torch self-contained qui réutilise le substrat bilinéaire (`BILINEAR=True`, livré) et entraîne `(q+key)%K` en supervisé (cross-entropy) via un appel DIRECT à `agent._step` (grad-enabled), sur 3 conditions différant par OÙ vit le key à l'instant de la composition (entrée co-présente / état caché oracle / état porté appris). Le verdict compare les 3 médianes vs bar. Aucun nouveau mécanisme substrat.

**Tech Stack:** Python 3, torch (CPU), numpy, pytest. Réutilise `MambaAgent`, `make_population(backend="torch")`, `TorchPopulationModel.BILINEAR`, `_step`. Le validateur/graphe ne change pas (pas d'arête).

## Global Constraints

- **Réutilise le substrat bilinéaire (verbatim)** : `TorchPopulationModel.BILINEAR=True` + `BILINEAR_RANK=16` dans un `try/finally` qui RESTAURE les flags (+ `CONDITION_GATE=False`, `GATE_TARGET=None`). L'optimiseur inclut les params bilinéaires : `Adam([agent.W, agent.U, agent.V, agent.W_bl], lr=lr)`.
- **Entraînement supervisé DIRECT (verbatim)** : `agent.forward` est `no_grad` (inférence) → INUTILISABLE pour entraîner. Appeler `agent._step(obs_tensor, H)` DIRECTEMENT (grad-enabled), lire les logits `H_new[:, N-O:N][:, :K]`, `F.cross_entropy` vs la cible `(q+key)%K`, `opt.zero_grad(); loss.backward(); opt.step()`. Pour `learned` (2-tick), enchaîner deux `_step` SANS `.detach()` entre eux (BPTT flue le gradient à travers le tick de rétention).
- **Layout d'entrée + mem_slots (verbatim)** : key one-hot @slots `[0:K]`, q one-hot @slots `[K:2K]` (entrée, ⊂ `[0:I]`). ORACLE : injecter le key dans des nœuds d'ÉTAT non-entrée, non-readout : `mem_start = (N-O) + K`, `mem_slots = [mem_start : mem_start+K]` (région output après les K nœuds de readout ; VÉRIFIER `O >= 2K` — sinon placer ailleurs en état non-readout). Ces nœuds portent l'état récurrent, ne sont pas écrasés par l'injection d'obs du `_step` (indices ≥ I), et ne sont pas le readout `[N-O:N-O+K]`.
- **Les 3 conditions** : `same_tick` (key+q co-présents en entrée, 1 pas) ; `oracle` (reset H, `H[:, mem_slots]=key`, 1 pas avec q en entrée) ; `learned` (2 pas : encode(key) puis use(q)). Cible TOUJOURS `(q+key)%K` sur le VRAI key. Éval miroir de l'entraînement (même construction).
- **Calibration générateur A** : POSITIF = `same_tick` > bar (le bilinéaire compose) ; NÉGATIF = `oracle_decorrelated` (key ALÉATOIRE dans mem_slots, décorrélé de la cible calculée sur le vrai key) ≤ bar (l'état retenu ne porte pas la bonne info → plancher). Prouve que l'oracle mesure la LECTURE de l'état, pas un artefact.
- **Verdict** : bar=`1/K+0.15`≈0.317. `RETENTION` si `same_tick>bar ET oracle>bar ET learned≤bar` (le bilinéaire compose un état retenu → gap = rétention apprise) ; `REPRESENTATION` si `same_tick>bar ET oracle≤bar` (ne compose pas un état porté) ; sinon `INCONCLUSIVE`. n≥12 seeds.
- **Nommage cliquet** : `run_retain_compose_diagnostic_probe` (motif `run_*probe`) → `CALIBRATED`. Helpers privés préfixe `_`.
- **Bornage** : pur torch CPU, aucun bail `kuzu`, aucun monde. Pré-vol `declare_design`. SMOKE d'abord ; run-verdict n=12 **FOREGROUND** borné (< ~9 min). Persister accuracies + `_params`. Provenance : fonction calibrée réelle.
- **Ne modifier AUCUN fichier existant** (probes, `backend_torch.py`, validateur). Commits path-scoped (JAMAIS `-A`), arbre partagé, stash-contingency, jamais `--no-verify`. Branche `feat/d1-prod-pairing`.

## File Structure

- `tools/retain_compose_diagnostic_probe.py` (NOUVEAU) — la sonde 3-conditions.
- `tests/test_retain_compose_diagnostic_probe.py` (NOUVEAU) — smoke unitaire.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — CALIBRATED + positif/négatif.
- `results/retain_compose_diagnostic.json` (NOUVEAU, Task 2).
- `docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md` (NOUVEAU, Task 2).

---

### Task 1: Sonde diagnostique + calibration (FUSIONNÉS) + smoke

**Files:**
- Create: `tools/retain_compose_diagnostic_probe.py`
- Create: `tests/test_retain_compose_diagnostic_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py`

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `TorchPopulationModel.{BILINEAR,BILINEAR_RANK,_step}`, `agent.{W,U,V,W_bl,I,N,O}`.
- Produces: `run_retain_compose_diagnostic_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02, conditions=("same_tick","oracle","learned")) -> dict` renvoyant `{"<cond>_median": float, ..., "gap_verdict": str, "per_seed": {cond: [...]}, "n": int}`.

- [ ] **Step 1: Écrire le smoke unitaire (qui échoue)**

Create `tests/test_retain_compose_diagnostic_probe.py`:

```python
import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4)
    assert set(r) >= {"same_tick_median", "oracle_median", "learned_median", "gap_verdict"}
    assert r["n"] == 2 and len(r["per_seed"]["oracle"]) == 2
    assert r["gap_verdict"] in ("RETENTION", "REPRESENTATION", "INCONCLUSIVE")
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_retain_compose_diagnostic_probe.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/retain_compose_diagnostic_probe.py` (VÉRIFIER les interfaces substrat en implémentant) :

```python
"""Diagnostic : le mur retain+compose est-il la RÉTENTION apprise (H1) ou la lecture d'un état porté (H2) ?

3 conditions bilinéaire (BILINEAR=True) + supervisé (cross-entropy via _step direct, grad) sur (q+key)%K :
 same_tick : key+q CO-PRÉSENTS en entrée (baseline, connu ~0.93) ;
 oracle    : key injecté PAR FIAT dans des nœuds d'ÉTAT (mem_slots), q en entrée -> rétention PARFAITE ;
 learned   : 2 pas encode(key)->use(q), rétention APPRISE (le cas qui échoue ~0.18).
oracle APPREND -> gap = rétention apprise (H1) ; oracle ÉCHOUE (same_tick OK) -> gap = lecture d'état (H2).
Calibré : same_tick (positif, le bilinéaire compose) + oracle_decorrelated (négatif, key aléatoire -> plancher).
Pur torch CPU, aucun bail. Usage : python tools/retain_compose_diagnostic_probe.py
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


def _mem_start(N, O, K):
    ms = (N - O) + K                     # après les K nœuds de readout, dans l'état non-readout
    assert ms + K <= N, f"mem_slots débordent (N={N},O={O},K={K}) — placer ailleurs"
    return ms


def _cond_logits(agent, key, q, condition, K, I, N, O, n, rng_dec):
    """Un forward grad-enabled (via _step DIRECT, pas agent.forward qui est no_grad) selon la condition.
    Renvoie les logits (n, K) au pas RÉPONSE."""
    import torch
    H = torch.zeros((n, N))
    if condition == "same_tick":
        obs = _slot(key, K, 0, I, n) + _slot(q, K, K, I, n)          # key@[0:K] + q@[K:2K]
        H = agent._step(torch.tensor(obs), H)
    elif condition in ("oracle", "oracle_decorrelated"):
        held = key if condition == "oracle" else rng_dec.randint(0, K, size=n)  # vrai vs aléatoire
        ms = _mem_start(N, O, K)
        H = H.clone()
        H[np.arange(n), ms + (held % K)] = 1.0                       # key injecté en état (mem_slots)
        H = agent._step(torch.tensor(_slot(q, K, K, I, n)), H)       # q en entrée
    else:                                                            # learned (2 pas, BPTT)
        H = agent._step(torch.tensor(_slot(key, K, 0, I, n)), H)     # encode(key)
        H = agent._step(torch.tensor(_slot(q, K, K, I, n)), H)       # use(q)
    return H[:, N - O:N][:, :K]


def _train_eval_condition(seed, condition, episodes, n_agents, K, lr, eval_batches=40):
    import torch
    import torch.nn.functional as F
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel as TPM

    np.random.seed(seed); torch.manual_seed(seed)
    saved = (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR, TPM.BILINEAR_RANK)
    TPM.CONDITION_GATE = False; TPM.GATE_TARGET = None
    TPM.BILINEAR = True; TPM.BILINEAR_RANK = 16
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I, N, O = agent.I, agent.N, agent.O
        rng = np.random.RandomState(seed + 1); rng_dec = np.random.RandomState(seed + 7)
        agent.opt = torch.optim.Adam([agent.W, agent.U, agent.V, agent.W_bl], lr=lr)

        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
            logits = _cond_logits(agent, key, q, condition, K, I, N, O, n_agents, rng_dec)
            tgt = torch.tensor(((q + key) % K).astype(np.int64))
            loss = F.cross_entropy(logits, tgt)
            agent.opt.zero_grad(); loss.backward(); agent.opt.step()

        hits = []
        with torch.no_grad():
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
                logits = _cond_logits(agent, key, q, condition, K, I, N, O, n_agents, rng_dec)
                g = logits.argmax(dim=1).cpu().numpy()
                hits.append((g == ((q + key) % K)).astype(np.float32))
        return float(np.mean(np.concatenate(hits)))
    finally:
        (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR, TPM.BILINEAR_RANK) = saved


def run_retain_compose_diagnostic_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02,
                                        conditions=("same_tick", "oracle", "learned")):
    """Entraîne (q+key)%K sur chaque condition, par seed ; renvoie médianes + gap_verdict."""
    per = {c: [] for c in conditions}
    for s in seeds:
        for c in conditions:
            per[c].append(_train_eval_condition(s, c, episodes, n_agents, K, lr))
    bar = 1.0 / K + 0.15
    med = {c: float(np.median(per[c])) for c in conditions}
    st, oc, ln = med.get("same_tick"), med.get("oracle"), med.get("learned")
    if st is not None and oc is not None and ln is not None:
        if st > bar and oc > bar and ln <= bar:
            verdict = "RETENTION"
        elif st > bar and oc <= bar:
            verdict = "REPRESENTATION"
        else:
            verdict = "INCONCLUSIVE"
    else:
        verdict = "INCONCLUSIVE"
    out = {f"{c}_median": med[c] for c in conditions}
    out.update({"gap_verdict": verdict, "per_seed": per, "n": len(seeds), "bar": bar})
    return out


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("RC_SEEDS", "12"))))
    r = run_retain_compose_diagnostic_probe(seeds, episodes=int(os.environ.get("RC_EPISODES", "1500")))
    print(json.dumps({k: v for k, v in r.items() if k != "per_seed"}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Lancer le smoke unitaire**

Run: `python -m pytest tests/test_retain_compose_diagnostic_probe.py -v`
Expected: PASS (forme + gap_verdict présent, n=2). Si échec d'interface (`_step` grad, `agent.O`, mem_slots), corriger d'après le code réel et re-signaler. VÉRIFIER surtout que `same_tick` monte au smoke (le bilinéaire doit composer — sinon le pipeline est cassé).

- [ ] **Step 5: Déclarer calibré + calibration (positif same_tick / négatif oracle décorrélé)**

In `tests/sandbox/test_instrument_calibration.py`, add to `CALIBRATED`:

```python
    # Diagnostic retain+compose. Positif = same_tick (le bilinéaire compose 2 entrées co-présentes -> >bar) ;
    # négatif = oracle DÉCORRÉLÉ (key aléatoire en état -> ne porte pas la bonne info -> plancher). Générateur A.
    "run_retain_compose_diagnostic_probe": ["*"],
```

Append:

```python
def test_retain_compose_same_tick_composes():
    """POSITIF (générateur A) : le bilinéaire compose key+q CO-PRÉSENTS -> same_tick > bar. Prouve que
    l'instrument PEUT montrer la composition (sinon un oracle<=bar serait ininterprétable)."""
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=list(range(4)), episodes=400, n_agents=16, K=6,
                                            conditions=("same_tick",))
    assert r["same_tick_median"] > 1/6 + 0.15, r


def test_retain_compose_decorrelated_oracle_is_floor():
    """NÉGATIF : un key ALÉATOIRE injecté en état (décorrélé de la cible) ne permet PAS (q+key)%K -> plancher.
    Prouve que l'oracle mesure la LECTURE de l'état retenu, pas un artefact d'injection."""
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=list(range(4)), episodes=400, n_agents=16, K=6,
                                            conditions=("oracle_decorrelated",))
    assert r["oracle_decorrelated_median"] <= 1/6 + 0.15, r
```

Note : ces cas ENTRAÎNENT → bornés (4 seeds, 400 ep). Si > ~2-3 min/cas, réduire au strict nécessaire pour trancher le seuil. Documenter le budget.

- [ ] **Step 6: Lancer calibration + cliquet**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k "retain_compose" -v`
Expected: PASS (same_tick > bar ; oracle décorrélé ≤ bar).
Run: `python tools/check_instrument_calibration.py` → `OK`.

- [ ] **Step 7: Commit (FUSIONNÉ)**

```bash
git add tools/retain_compose_diagnostic_probe.py tests/test_retain_compose_diagnostic_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # UNIQUEMENT ces trois chemins
git commit -m "feat(RETAIN-COMPOSE): sonde diagnostique 3-conditions (same_tick/oracle/learned) + calibration (cliquet)"
```

Si le hook bloque sur un instrument étranger : stash path-scoped, commit, pop, vérifier — jamais `--no-verify`.

---

### Task 2: Run-verdict (n=12, FOREGROUND) + record

**Files:**
- Create: `results/retain_compose_diagnostic.json`
- Create: `docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md`

**Interfaces:**
- Consumes: `run_retain_compose_diagnostic_probe` (Task 1).
- Produces: le verdict persisté + le record nommant le gap.

- [ ] **Step 1: Pré-vol + SMOKE (mécanisme + débit)**

Run: `python -c "import time,json; from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe as R; t=time.time(); r=R(seeds=[0,1,2], episodes=600, n_agents=16, K=6); print('dt_s=%.1f' % (time.time()-t)); print('same_tick', round(r['same_tick_median'],3), 'oracle', round(r['oracle_median'],3), 'learned', round(r['learned_median'],3), 'verdict', r['gap_verdict'])"`

Attendu : `dt_s` (débit), `same_tick` tend > 0.32 (contrôle positif), `oracle` et `learned` = la mesure. ⚠️ n<12 ne tranche pas.

**Décision de bornage** : si n=12 projette > ~9 min, réduire `episodes`/`n_agents`. VÉRIFIER que `same_tick` monte (sinon diagnostic ininterprétable — augmenter episodes). `learned` doit reproduire ~nul (sinon re-vérifier le pipeline 2-tick).

- [ ] **Step 2: Run-verdict n=12 (FOREGROUND, borné) + persister**

⚠️ FOREGROUND. Si promu en bg, bloquer dessus, ne pas dupliquer.

Run (ajuster d'après le smoke) :
`python -c "import json; from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe as R; r=R(seeds=list(range(12)), episodes=1500, n_agents=16, K=6); r['_params']={'episodes':1500,'n_agents':16,'K':6,'lr':0.02,'seeds':12}; json.dump(r, open('results/retain_compose_diagnostic.json','w'), indent=2); print('same_tick', round(r['same_tick_median'],3), 'oracle', round(r['oracle_median'],3), 'learned', round(r['learned_median'],3)); print('VERDICT', r['gap_verdict']); [print(c, sorted(r['per_seed'][c])) for c in ('same_tick','oracle','learned')]"`

Attendu : les 3 médianes + `gap_verdict`. Le contrôle positif `same_tick` DOIT être > bar (sinon ininterprétable). `oracle`/`learned` donnent la réponse. Persisté dans `results/retain_compose_diagnostic.json`.

**Interprétation** : `RETENTION` (oracle apprend, learned échoue) → le bilinéaire compose un état retenu → gap = rétention apprise. `REPRESENTATION` (oracle échoue) → gap = lecture d'état. `INCONCLUSIVE` (p.ex. same_tick raté) → le noter honnêtement, ne pas forcer.

- [ ] **Step 3: Écrire le record**

Create `docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md` (valeurs réelles) :

```markdown
---
id: EDR-RETAIN-COMPOSE
type: EDR
title: "OÙ est le mur retain+compose : diagnostic par oracle de rétention (RÉTENTION_APPRISE / LECTURE_D_ÉTAT)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question
BILINEAR a débloqué la composition à opérandes CO-PRÉSENTS mais le 2-tick (retenir key PUIS composer) reste
nul — même sous BPTT non-tronqué (pas le gradient). La rétention seule marche (MEM-PERCEPTION), la composition
seule marche (BILINEAR). OÙ est le gap de la COMBINAISON ?

## Méthode
3 conditions bilinéaire+supervisé (cross-entropy via `_step` direct, grad) sur (q+key)%K, n=12 : `same_tick`
(key+q co-présents en entrée, contrôle positif), `oracle` (key injecté PAR FIAT dans des nœuds d'état
`mem_slots`, rétention PARFAITE), `learned` (2-tick, rétention apprise). Calibré : same_tick compose (positif),
oracle décorrélé -> plancher (négatif).

## Résultat
same_tick M_ST (>bar, le bilinéaire compose) ; oracle M_OC ; learned M_LN. **Verdict : V_REEL.**
[Si RETENTION] oracle APPREND (le bilinéaire compose un état RETENU propre) alors que learned échoue -> le gap
n'est PAS la composition d'un état porté mais la RÉTENTION APPRISE (holder le key en apprenant à composer).
[Si REPRESENTATION] oracle échoue malgré une rétention parfaite -> le bilinéaire ne compose un opérande que
s'il est en ENTRÉE, pas porté en état -> gap représentationnel.

## Portée (bornée)
Diagnostic sous ORACLE parfait (isole la variable), pas l'émergence. Un seul rang/budget. mem_slots = nœuds
d'état non-readout (le key porté y est lisible par le bilinéaire par construction).

## Ce que ça débloque
Nomme le prochain levier : [RETENTION] un mécanisme de rétention apprise (porte d'oubli / registre) + le
bilinéaire ; [REPRESENTATION] une refonte de la lecture d'état par la composition. Cf.
`docs/superpowers/specs/2026-08-04-retain-compose-diagnostic-design.md`.
```

Remplacer `M_ST`/`M_OC`/`M_LN`/`V_REEL` et garder SEULEMENT la branche d'interprétation correspondant au verdict.

- [ ] **Step 4: Valider**

Run: `python tools/check_record_links.py` (EDR-RETAIN-COMPOSE non-orphelin)
Run: `python -m pytest tests/test_retain_compose_diagnostic_probe.py -q` (vert)
Run: `python tools/check_instrument_calibration.py` (OK)
Run: `python tools/check_agi_taxonomy.py` (2 arêtes inchangées — pas d'arête ajoutée)

- [ ] **Step 5: Commit**

```bash
git add results/retain_compose_diagnostic.json docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md
git status --short   # UNIQUEMENT ces deux chemins
git commit -m "feat(RETAIN-COMPOSE): verdict n=12 -- ou est le mur retain+compose (diagnostic oracle) + record"
```

Si `results/` gitignored : `git add -f`. Stash-contingency fichier étranger si besoin.

---

## Self-Review

**Spec coverage :**
- §2 3 conditions (same_tick/oracle/learned) bilinéaire+supervisé → Task 1 `_cond_logits`/`_train_eval_condition`. ✓
- §2 note oracle = boucle custom (_step direct, pas imitate) → implémenté via `_step` + CE + backward. ✓
- §3 verdict (RETENTION/REPRESENTATION/INCONCLUSIVE, seuils) → `run_..._probe` gap_verdict. ✓
- §4 calibration (positif same_tick / négatif oracle décorrélé, générateur A) → Task 1 Step 5 (2 cas + CALIBRATED). ✓
- §5 bornage (smoke, FOREGROUND borné, persister _params, provenance) → Task 2. ✓
- §6 livrable (sonde + record nommant le gap, pas d'arête ni mécanisme) → Task 1-2. ✓

**Placeholder scan :** valeurs à mesurer (M_ST/M_OC/M_LN/V_REEL) marquées explicitement, remplies au run. Aucun TODO code.

**Type consistency :** `run_retain_compose_diagnostic_probe(seeds, episodes, n_agents, K, lr, conditions)` renvoie `{<cond>_median, gap_verdict, per_seed, n, bar}` — utilisé identiquement en Task 1 (tests, avec `conditions=(...)` restreint pour la calibration) et Task 2 (run complet 3 conditions). Le substrat `BILINEAR`/`_step`/`U/V/W_bl` (livré) consommé sans modification. Helpers `_slot/_mem_start/_cond_logits/_train_eval_condition` privés — aucun ne matche un motif cliquet. ✓
