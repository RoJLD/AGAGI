# Phase A — Sonde de fidélité de `g` (go/no-go) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si le modèle de transition `g(H,a)→H'` (déjà dans `main`) prédit les transitions latentes action-conditionnées mieux qu'une baseline naïve — go/no-go AVANT de bâtir la machinerie Dyna (spec `2026-06-25-dream-offline-training-design.md`, composant A).

**Architecture:** Un outil autonome `tools/g_fidelity_probe.py` qui (1) déroule une boucle pilotée minimale où `g` apprend en ligne (`PLAN_BIAS>0` → `update_transition` se déclenche), (2) enregistre des transitions latentes réelles `(H_rec_t, action, H_rec_{t+1})` en ordre nœud, (3) compare l'erreur de prédiction de `g` vs la baseline « pas de changement », et rend un verdict apparié multi-seed. AUCUN changement du code cœur.

**Tech Stack:** Python 3.13, NumPy. Substrat `src/agents/mamba_agent.py` (`MambaBatchModel` : `G_batch`, `H_rec_batch`, `PLAN_BIAS`/`PLAN_A`, `mappings`). Tests pytest (`tests/sandbox/`).

## Global Constraints

- **Aucun changement du code de production** : la sonde lit `m.G_batch` / `m.H_rec_batch` / `m.mappings` et règle les flags de classe (`PLAN_BIAS`, `PLAN_A`, `PLAN_LR`) en les **restaurant en `finally`**. Le défaut OFF reste intact.
- **Ordre NŒUD** pour toute comparaison : `G` per-agent = `m.G_batch[i][:, map_idx]` (A, N_i) ; `H_rec` per-agent = `m.H_rec_batch[i, map_idx]` (N_i,). `map_idx = m.mappings[i]`.
- **Isoler l'effet action** : obs constante (zéros) pendant la sonde → la seule source de changement latent est la récurrence + l'action, ce que `g` est censé modéliser.
- `A = MambaBatchModel.PLAN_A = 8` (move 0..7) ; action exécutée = `int(argmax(preds[:8]))`.
- Déterministe par seed (`np.random.seed`), sans graph_rag (reproductible).
- Verdict apparié + test de signe (binomial bilatéral), comme les autres outils NAS.
- Commits **path-scopés** (`git add <chemins>` explicites, jamais `-A`). Message terminé par `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Fonctions pures de la sonde (erreurs + verdict)

**Files:**
- Create: `tools/g_fidelity_probe.py`
- Test: `tests/sandbox/test_g_fidelity_probe.py`

**Interfaces:**
- Produces:
  - `transition_error(H_prev, g_delta, H_next) -> tuple[float, float]` — renvoie `(g_err, base_err)` où `g_err = mean((H_prev + g_delta − H_next)²)` (prédiction de `g`) et `base_err = mean((H_prev − H_next)²)` (baseline « pas de changement »). Tous vecteurs `(N,)`.
  - `fidelity_verdict(ratios: list[float]) -> dict` — `ratios[i] = g_err/base_err` par transition. Renvoie `{"median_ratio", "n_favorable" (ratio<1), "n", "sign_p", "verdict"}` avec verdict `"G_FIDELE"` si `median_ratio < 0.95` ET majorité favorable, `"G_INUTILE"` si `median_ratio > 1.05`, sinon `"NEUTRE"`. (g utile = `g_err < base_err` = ratio < 1.)

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_g_fidelity_probe.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from tools.g_fidelity_probe import transition_error, fidelity_verdict


def test_transition_error_perfect_g_beats_baseline():
    H_prev = np.array([0.0, 0.0], dtype=np.float32)
    H_next = np.array([1.0, 0.0], dtype=np.float32)
    g_delta = np.array([1.0, 0.0], dtype=np.float32)        # g prédit exactement le changement
    g_err, base_err = transition_error(H_prev, g_delta, H_next)
    assert np.isclose(g_err, 0.0)                            # prédiction parfaite
    assert base_err > 0.0                                    # baseline se trompe
    assert g_err < base_err


def test_transition_error_zero_g_equals_baseline():
    H_prev = np.array([0.0, 0.0], dtype=np.float32)
    H_next = np.array([1.0, 0.0], dtype=np.float32)
    g_delta = np.zeros(2, dtype=np.float32)                  # g=0 -> identique à la baseline
    g_err, base_err = transition_error(H_prev, g_delta, H_next)
    assert np.isclose(g_err, base_err)


def test_fidelity_verdict_faithful():
    out = fidelity_verdict([0.3, 0.4, 0.2, 0.5, 0.35])       # g bat nettement la baseline
    assert out["verdict"] == "G_FIDELE"
    assert out["n_favorable"] == 5 and out["n"] == 5


def test_fidelity_verdict_useless():
    out = fidelity_verdict([1.3, 1.2, 1.5, 1.1])
    assert out["verdict"] == "G_INUTILE"


def test_fidelity_verdict_neutral_and_no_nan():
    out = fidelity_verdict([1.0, 1.0])                        # égalités -> NEUTRE, pas de NaN
    assert out["verdict"] == "NEUTRE"
    assert np.isfinite(out["sign_p"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_g_fidelity_probe.py -q`
Expected: FAIL (ModuleNotFoundError: tools.g_fidelity_probe).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/g_fidelity_probe.py
"""tools/g_fidelity_probe.py — Sonde de fidélité de g (NAS Axe 3, spec dream-offline, composant A).
go/no-go : g(H,a)→H' prédit-il les transitions latentes mieux que la baseline « pas de changement » ?
Si NON -> escalader vers g bilinéaire avant de bâtir Dyna. AUCUN changement du code cœur.
Usage : GFP_SEEDS=0,1,2 python tools/g_fidelity_probe.py"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def transition_error(H_prev, g_delta, H_next):
    """(g_err, base_err) pour une transition latente. g_err = prédiction de g ; base_err = baseline."""
    H_prev = np.asarray(H_prev, dtype=np.float32)
    g_delta = np.asarray(g_delta, dtype=np.float32)
    H_next = np.asarray(H_next, dtype=np.float32)
    g_err = float(np.mean((H_prev + g_delta - H_next) ** 2))
    base_err = float(np.mean((H_prev - H_next) ** 2))
    return g_err, base_err


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def fidelity_verdict(ratios) -> dict:
    """ratios[i] = g_err/base_err par transition. g UTILE = ratio < 1 (g bat la baseline)."""
    ratios = [float(r) for r in ratios]
    n = len(ratios)
    if n == 0:
        return {"median_ratio": 1.0, "n_favorable": 0, "n": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = st.median(ratios)
    n_fav = sum(1 for r in ratios if r < 1.0)            # favorable = g meilleur
    eff = [r for r in ratios if r != 1.0]
    sign_p = _sign_p(sum(1 for r in eff if r < 1.0), len(eff))
    if med < 0.95 and 2 * n_fav > n:
        verdict = "G_FIDELE"
    elif med > 1.05:
        verdict = "G_INUTILE"
    else:
        verdict = "NEUTRE"
    return {"median_ratio": float(med), "n_favorable": int(n_fav), "n": int(n),
            "sign_p": float(sign_p), "verdict": verdict}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_g_fidelity_probe.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/g_fidelity_probe.py tests/sandbox/test_g_fidelity_probe.py
git commit -m "feat(probe): fonctions pures sonde de fidelite de g (transition_error + verdict)"
```

---

### Task 2: Runner de la sonde + mesure décisive

**Files:**
- Modify: `tools/g_fidelity_probe.py`
- Test: `tests/sandbox/test_g_fidelity_probe.py`

**Interfaces:**
- Consumes: `transition_error`, `fidelity_verdict` (Task 1).
- Produces:
  - `collect_ratios(seed: int, warmup: int = 300, measure: int = 300) -> list[float]` — déroule une boucle pilotée (1 agent, obs zéro, organe planificateur actif, `PLAN_BIAS>0` pour que `g` apprenne), laisse `g` apprendre `warmup` ticks, puis sur `measure` ticks enregistre `g_err/base_err` par transition (ordre nœud).
  - `run_probe(seeds, warmup=300, measure=300) -> dict` — agrège les ratios de tous les seeds → `fidelity_verdict`.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_g_fidelity_probe.py
from tools.g_fidelity_probe import collect_ratios, run_probe


def test_collect_ratios_returns_finite_positive():
    ratios = collect_ratios(seed=0, warmup=20, measure=20)
    assert len(ratios) > 0
    assert all(np.isfinite(r) and r >= 0.0 for r in ratios)


def test_run_probe_structure():
    out = run_probe(seeds=[0, 1], warmup=20, measure=20)
    assert set(["median_ratio", "n_favorable", "n", "sign_p", "verdict"]).issubset(out)
    assert out["verdict"] in ("G_FIDELE", "G_INUTILE", "NEUTRE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_g_fidelity_probe.py -q`
Expected: FAIL (ImportError: cannot import name 'collect_ratios').

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/g_fidelity_probe.py` (après les imports, on importe le substrat ; respecter l'ordre `_ROOT` sur le path AVANT les imports `src`) :

```python
import numpy as np  # déjà importé en tête
from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def collect_ratios(seed: int, warmup: int = 300, measure: int = 300):
    """Boucle pilotée minimale : obs zéro (isole l'effet action), g apprend en ligne (PLAN_BIAS>0),
    puis on enregistre g_err/base_err par transition (ordre nœud). Restaure les flags en finally."""
    np.random.seed(seed)
    a = MambaAgent()
    a.genome.organ_genes = np.array([True, False])          # organe planificateur actif (g se met à jour)
    prev_bias, prev_a, prev_lr = (MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_LR = 0.1
    ratios = []
    try:
        m = MambaBatchModel([a])
        n_in = a.genome.num_inputs
        obs = np.zeros((1, n_in), dtype=np.float32)         # obs constante -> seule l'action change le latent
        map_idx = m.mappings[0]
        prev_hrec = None
        prev_move = None
        for t in range(warmup + measure):
            preds, _ = m.forward(obs)
            move = int(np.argmax(preds[0, :MambaBatchModel.PLAN_A]))
            # H_rec courant en ordre nœud (capturé par forward, avant le rêve)
            cur_hrec = m.H_rec_batch[0, map_idx].copy()
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_delta = m.G_batch[0][:, map_idx][prev_move]    # (N_i,) effet appris de l'action jouée
                g_err, base_err = transition_error(prev_hrec, g_delta, cur_hrec)
                if base_err > 1e-9:                              # ignorer les transitions nulles
                    ratios.append(g_err / base_err)
            # apprentissage en ligne de g (transition différée) : nécessite compute_policy_gradient
            m.compute_policy_gradient(np.array([0.1], dtype=np.float32),
                                      [{"move": move, "grab": 0, "rub": 0}])
            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR = prev_bias, prev_a, prev_lr
    return ratios


def run_probe(seeds, warmup: int = 300, measure: int = 300) -> dict:
    all_ratios = []
    for s in seeds:
        all_ratios.extend(collect_ratios(int(s), warmup, measure))
    return fidelity_verdict(all_ratios)


def main():
    seeds = [int(s) for s in os.environ.get("GFP_SEEDS", "0,1,2,3,4,5,6,7").split(",") if s.strip()]
    warmup = int(os.environ.get("GFP_WARMUP", "300"))
    measure = int(os.environ.get("GFP_MEASURE", "300"))
    out = run_probe(seeds, warmup, measure)
    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    return out


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_g_fidelity_probe.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/g_fidelity_probe.py tests/sandbox/test_g_fidelity_probe.py
git commit -m "feat(probe): runner sonde de fidelite de g + verdict apparie"
```

- [ ] **Step 6: Mesure décisive (go/no-go)**

Run: `GFP_SEEDS=0,1,2,3,4,5,6,7 python tools/g_fidelity_probe.py`
Expected: une ligne `VERDICT=... median_ratio=... sign_p=...`. **Rapporter le verdict tel quel.**
- `G_FIDELE` → `g` est exploitable en model-based → **écrire le plan Phase B-E** (reward head + buffer + Dyna).
- `G_INUTILE` / `NEUTRE` → `g` linéaire trop faible → **STOP Dyna ; escalader vers `g` bilinéaire** (backlog NAS §4) avant tout build offline. Résultat scientifique valide, pas un échec.

---

## Self-Review (auteur)

**Couverture spec :** composant A (sonde de fidélité de `g`, go/no-go) entièrement couvert (Tasks 1-2). Les composants B-E (reward head, buffer, Dyna, gate) sont **volontairement hors de ce plan** — conditionnels au verdict de la sonde (de-risquage : ne pas bâtir sur un `g` non validé). Plan Phase B-E à écrire seulement si `G_FIDELE`.

**Types cohérents :** `transition_error(H_prev, g_delta, H_next)→(float,float)` ; `fidelity_verdict(list)→dict` ; `collect_ratios(seed,warmup,measure)→list` ; `run_probe(seeds,...)→dict`. `g_delta` = `G_batch[0][:, map_idx][move]` shape `(N_i,)`, aligné avec `H_rec` ordre nœud `(N_i,)`. `A=PLAN_A=8`.

**Placeholders :** code complet pour fonctions pures + runner + tests. Aucun « TODO » fonctionnel.

**Risque :** la sonde lit `m.H_rec_batch` (attribut posé dans `forward` par le travail planificateur déjà dans `main`) — si absent, l'implémenteur doit rapporter NEEDS_CONTEXT (mais il est dans `main`, PR #66).
