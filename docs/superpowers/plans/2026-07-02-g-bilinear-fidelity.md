# EDR 193 — g bilinéaire : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une sonde qui fitte offline un g BILINÉAIRE (`ΔH = H·W_a`) sur les transitions latentes réelles d'un rollout env-grille et mesure s'il est G_FIDÈLE là où le g linéaire d'EDR 135 était NEUTRE.

**Architecture:** Nouveau fichier `tools/g_bilinear_probe.py`. Deux couches : (1) machinerie offline PURE NUMPY (split, fits ridge/linéaire, ratios, verdict) — testable sans le modèle ; (2) collecte des triplets latents via un rollout env-grille (import read-only de `g_fidelity_probe`) + orchestration. Réutilise `transition_error` et `fidelity_verdict` d'EDR 135.

**Tech Stack:** Python, NumPy (fit ridge `np.linalg.solve`, déterministe). Modèle legacy `MambaAgent` (import read-only). PAS de torch, PAS de Biosphere/HoF/KuzuDB.

## Global Constraints

- **TOOLING ADDITIF** : créer SEULEMENT `tools/g_bilinear_probe.py` et `tests/sandbox/test_g_bilinear_probe.py`. NE modifier AUCUN autre fichier — ni `tools/g_fidelity_probe.py` (mergé EDR-135), ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : toute chaîne passée à `print()` strictement ASCII (`->` en tirets OK, pas d'accent ni flèche unicode). Accents seulement dans les docstrings.
- **Déterminisme** : rollout `np.random.seed(seed)` + ridge `np.linalg.solve` (numpy pur). Flags `PLAN_BIAS`/`PLAN_A`/`PLAN_LR` restaurés en `finally`. Run réel = 2 passes byte-identiques.
- **Imports minimaux (pas d'import mort)** : n'importer QUE ce qui est utilisé.
- **Verdict gelé** : `BILINEAR_FIDELE` si `fidelity_verdict(ratios_bilin)` == `G_FIDELE` ET `median(bilin) < median(learned)` ; `BILINEAR_NEUTRAL` si `fidelity_verdict(ratios_bilin).verdict` ∈ {`NEUTRE`, `G_INUTILE`} ; sinon `PARTIAL`. λ ridge = 1.0. Ne PAS ajuster après le run.
- **Convention ridge** : prédiction en convention LIGNE `ΔH_pred = H_prev @ W_a` ; fit `W_a = solve(X^T X + λI, X^T ΔY)` avec `X`=(m,N) empilement des `H_prev` train, `ΔY`=(m,N) empilement des `H_next−H_prev` train.

---

## Fichiers

- Créer : `tools/g_bilinear_probe.py`.
- Créer : `tests/sandbox/test_g_bilinear_probe.py`.

Imports disponibles (vérifiés dans `tools/g_fidelity_probe.py`, EDR-135) :
- `MambaAgent, MambaBatchModel` (ré-exportés depuis `g_fidelity_probe`, qui les importe de `src.agents.mamba_agent`).
- `transition_error(H_prev, g_delta, H_next) -> (g_err, base_err)`.
- `fidelity_verdict(ratios) -> {"median_ratio","n_favorable","n","sign_p","verdict"}` (verdict ∈ {`G_FIDELE`,`G_INUTILE`,`NEUTRE`}).
- Constantes env : `_GRID_L (=7), _N_MOVES (=3), _OBS_DIM (=14), _T_WARN_PERIOD (=6)`, helper `_obs_bench(pos, danger_cell) -> np.ndarray`.
- `numpy as np`.

---

## Task 1 : machinerie offline pure-numpy (split + fits + ratios + verdict)

**Files:**
- Create: `tools/g_bilinear_probe.py`
- Test: `tests/sandbox/test_g_bilinear_probe.py`

**Interfaces:**
- Consumes : `fidelity_verdict` (de `g_fidelity_probe`) ; `numpy as np`.
- Produces : `_split_temporal(triples, n_moves, frac=0.7) -> (train, test)` ; `_fit_bilinear(train, n_moves, N, lam) -> dict` ; `_fit_linear_offline(train, n_moves, N) -> dict` ; `_ratios_for_predictor(test, predictor_fn, base_thresh=1e-4) -> list[float]` ; `_verdict_bilinear(ratios_bilin, ratios_learned) -> str`.
- Un triplet = `dict` `{"H_prev": np.ndarray(N,), "move": int, "H_next": np.ndarray(N,), "g_learned": np.ndarray(N,)}`.

- [ ] **Step 1 : écrire les tests qui échouent**

Créer `tests/sandbox/test_g_bilinear_probe.py` :

```python
import numpy as np

from tools.g_bilinear_probe import (
    _split_temporal, _fit_bilinear, _fit_linear_offline, _ratios_for_predictor, _verdict_bilinear,
)


def _toy_triples(n, N, M, seed, move=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        h = rng.standard_normal(N).astype(np.float64)
        dh = h @ M                      # transition VRAIMENT bilineaire (etat-dependante)
        out.append({"H_prev": h, "move": move, "H_next": h + dh,
                    "g_learned": np.zeros(N, dtype=np.float64)})
    return out


def test_split_temporal_proportions():
    tr = [{"move": 0} for _ in range(10)] + [{"move": 1} for _ in range(10)]
    train, test = _split_temporal(tr, 2, frac=0.7)
    assert len(train) == 14 and len(test) == 6


def test_bilinear_fits_state_dependent_map():
    N = 6
    rng = np.random.default_rng(0)
    M = rng.standard_normal((N, N)) * 0.2
    triples = _toy_triples(120, N, M, seed=1)
    train, test = _split_temporal(triples, 1, frac=0.7)
    W = _fit_bilinear(train, 1, N, lam=1e-3)
    ratios = _ratios_for_predictor(test, lambda tr: tr["H_prev"] @ W[tr["move"]])
    # transition purement bilineaire -> le fit doit ecraser la baseline
    assert float(np.median(ratios)) < 0.5


def test_linear_offline_recovers_constant_delta():
    N = 4
    c = np.array([1.0, -2.0, 0.5, 3.0])
    triples = [{"H_prev": np.zeros(N), "move": 0, "H_next": c.copy(),
                "g_learned": np.zeros(N)} for _ in range(10)]
    C = _fit_linear_offline(triples, 1, N)
    assert np.allclose(C[0], c)


def test_verdict_bilinear_fidele():
    # bilineaire fidele (ratios<1) ET bat le learned (median plus bas)
    assert _verdict_bilinear([0.4, 0.5, 0.3, 0.45, 0.5], [1.0, 1.0, 0.98, 1.02, 1.0]) == "BILINEAR_FIDELE"


def test_verdict_bilinear_neutral():
    assert _verdict_bilinear([1.0, 1.01, 0.99, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]) == "BILINEAR_NEUTRAL"


def test_verdict_bilinear_partial():
    # fidele mais NE bat PAS le learned (learned median plus bas)
    assert _verdict_bilinear([0.4, 0.5, 0.3, 0.45, 0.5], [0.1, 0.1, 0.1, 0.1, 0.1]) == "PARTIAL"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -v`
Expected : FAIL (ImportError sur `tools.g_bilinear_probe`).

- [ ] **Step 3 : implémenter (créer le fichier, EXACTEMENT ce code)**

Créer `tools/g_bilinear_probe.py` :

```python
"""tools/g_bilinear_probe.py — Sonde de fidelite d'un g BILINEAIRE (EDR 193, extension d'EDR 135).

EDR 135 : le g LINEAIRE du modele (delta constant par action, independant de H) est NEUTRE sur obs riches. Dernier
levier G4 non teste = un g BILINEAIRE (etat-dependant) : ΔH = H . W_a (une matrice par action). Le modele n'apprenant
qu'un g lineaire, on fitte le bilineaire OFFLINE par ridge sur les vraies transitions latentes d'un rollout env-grille
(a trajectoire FIXE) et on compare les fidelites a la baseline 'pas de changement' + au g lineaire appris (reference
135). Auto-contenu (numpy pur pour le fit ; MambaAgent en import read-only), ne modifie rien.

Usage : python -m tools.g_bilinear_probe
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.g_fidelity_probe import fidelity_verdict


def _split_temporal(triples, n_moves, frac=0.7):
    """Split TEMPOREL par action : les premiers frac% des triplets d'une action = train, le reste = test.
    Preserve l'ordre (generalisation temporelle, pas memorisation)."""
    train, test = [], []
    for mv in range(n_moves):
        grp = [tr for tr in triples if tr["move"] == mv]
        k = int(len(grp) * frac)
        train.extend(grp[:k])
        test.extend(grp[k:])
    return train, test


def _fit_linear_offline(train, n_moves, N):
    """Delta CONSTANT par action : c_a = moyenne des (H_next - H_prev) du train pour l'action a. Controle 'lineaire
    re-estime offline'. Renvoie dict move -> vecteur (N,)."""
    out = {}
    for mv in range(n_moves):
        deltas = [np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                  for tr in train if tr["move"] == mv]
        out[mv] = np.mean(deltas, axis=0) if deltas else np.zeros(N, dtype=np.float64)
    return out


def _fit_bilinear(train, n_moves, N, lam):
    """g BILINEAIRE par ridge, une matrice W_a (N,N) par action. Convention LIGNE : ΔH_pred = H_prev @ W_a.
    W_a = solve(X^T X + lam*I, X^T ΔY), X=(m,N) empilement H_prev train, ΔY=(m,N) empilement (H_next-H_prev) train."""
    out = {}
    eye = np.eye(N, dtype=np.float64)
    for mv in range(n_moves):
        grp = [tr for tr in train if tr["move"] == mv]
        if len(grp) < 2:
            out[mv] = np.zeros((N, N), dtype=np.float64)
            continue
        X = np.stack([np.asarray(tr["H_prev"], dtype=np.float64) for tr in grp])
        DY = np.stack([np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                       for tr in grp])
        A = X.T @ X + lam * eye
        B = X.T @ DY
        out[mv] = np.linalg.solve(A, B)
    return out


def _ratios_for_predictor(test, predictor_fn, base_thresh=1e-4):
    """ratio = pred_err/base_err par triplet test (filtre base_err > base_thresh). predictor_fn(tr) -> ΔH_pred (N,)."""
    ratios = []
    for tr in test:
        H_prev = np.asarray(tr["H_prev"], dtype=np.float64)
        H_next = np.asarray(tr["H_next"], dtype=np.float64)
        delta_pred = np.asarray(predictor_fn(tr), dtype=np.float64)
        pred_err = float(np.mean((H_prev + delta_pred - H_next) ** 2))
        base_err = float(np.mean((H_prev - H_next) ** 2))
        if base_err > base_thresh:
            ratios.append(pred_err / base_err)
    return ratios


def _verdict_bilinear(ratios_bilin, ratios_learned):
    """GELE. BILINEAR_FIDELE si fidelity_verdict(bilin)=G_FIDELE ET median(bilin)<median(learned) ;
    BILINEAR_NEUTRAL si verdict bilin in {NEUTRE, G_INUTILE} ; sinon PARTIAL."""
    vb = fidelity_verdict(ratios_bilin)
    vl = fidelity_verdict(ratios_learned)
    if vb["verdict"] == "G_FIDELE" and vb["median_ratio"] < vl["median_ratio"]:
        return "BILINEAR_FIDELE"
    if vb["verdict"] in ("NEUTRE", "G_INUTILE"):
        return "BILINEAR_NEUTRAL"
    return "PARTIAL"
```

- [ ] **Step 4 : lancer les tests, vérifier PASS**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -v`
Expected : PASS (6 tests). `test_bilinear_fits_state_dependent_map` prouve que le fit récupère une carte bilinéaire vraie (ratio < 0.5).

- [ ] **Step 5 : vérifier zéro modif fichiers existants**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && git status --short`
Expected : seuls `tools/g_bilinear_probe.py` et `tests/sandbox/test_g_bilinear_probe.py`.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear"
git add tools/g_bilinear_probe.py tests/sandbox/test_g_bilinear_probe.py
git commit -m "feat(gbilinear): machinerie offline (split + ridge fit + ratios + verdict gele)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : collecte des triplets (rollout env-grille) + main + report + smoke

**Files:**
- Modify: `tools/g_bilinear_probe.py` (AJOUTER après `_verdict_bilinear`)
- Test: `tests/sandbox/test_g_bilinear_probe.py` (AJOUTER à la fin)

**Interfaces:**
- Consumes : `_split_temporal, _fit_bilinear, _fit_linear_offline, _ratios_for_predictor, _verdict_bilinear` (Task 1) ; `fidelity_verdict, np` (déjà importés en tête) ; NOUVEAUX imports de `g_fidelity_probe` : `MambaAgent, MambaBatchModel, _obs_bench, _GRID_L, _N_MOVES, _T_WARN_PERIOD, _OBS_DIM`.
- Produces : `_collect_transitions_env(seed, warmup, measure) -> list[dict]` ; `main_bilinear_check(seeds=(0,1,2,3,4,5,6,7), warmup=300, measure=600, lam=1.0, _return=False) -> dict|None` retournant `{verdict, median_bilin, median_learned, median_linoff, n}`.

- [ ] **Step 1 : ajouter le test smoke qui échoue**

Ajouter à la fin de `tests/sandbox/test_g_bilinear_probe.py` :

```python
from tools.g_bilinear_probe import main_bilinear_check


def test_smoke_bilinear_returns_verdict():
    res = main_bilinear_check(seeds=(0,), warmup=30, measure=60, _return=True)
    assert res["verdict"] in {"BILINEAR_FIDELE", "BILINEAR_NEUTRAL", "PARTIAL", "NO_DATA"}
    assert "median_bilin" in res
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -k smoke -v`
Expected : FAIL (ImportError sur `main_bilinear_check`).

- [ ] **Step 3 : mettre à jour l'import de tête ET ajouter le code (EXACTEMENT)**

D'abord, REMPLACER la ligne d'import existante `from tools.g_fidelity_probe import fidelity_verdict` par :

```python
from tools.g_fidelity_probe import (
    fidelity_verdict, MambaAgent, MambaBatchModel, _obs_bench, _GRID_L, _N_MOVES, _T_WARN_PERIOD, _OBS_DIM,
)
```

Puis AJOUTER après `_verdict_bilinear` :

```python
def _collect_transitions_env(seed, warmup, measure):
    """Rollout env-grille 1-D deterministe (miroir de collect_ratios_env, EDR 135). Capture les triplets latents
    (H_prev, move, H_next, g_learned) apres warmup. g_learned = colonne g LINEAIRE apprise par le modele (reference).
    Restaure les flags PLAN_* en finally."""
    np.random.seed(seed)
    a = MambaAgent(num_inputs=_OBS_DIM, num_outputs=108, num_nodes=172)
    a.genome.organ_genes = np.array([True, False])
    prev_bias, prev_plan_a, prev_plan_lr = (MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_A = _N_MOVES
    MambaBatchModel.PLAN_LR = 0.1
    triples = []
    try:
        m = MambaBatchModel([a])
        map_idx = m.mappings[0]
        pos = _GRID_L // 2
        pending_danger = None
        prev_hrec = None
        prev_move = None
        for t in range(warmup + measure):
            strike_cell = pending_danger
            pending_danger = None
            if strike_cell is not None and pos == strike_cell:
                pos = _GRID_L // 2
            warn = (t % _T_WARN_PERIOD == 0)
            telegraph = pos if warn else None
            obs = _obs_bench(pos, telegraph)[None, :]
            m.forward(obs)
            move = int(t % _N_MOVES)
            cur_hrec = m.H_rec_batch[0, map_idx].copy()
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_learned = m.G_batch[0][:, map_idx][prev_move].copy()
                triples.append({"H_prev": np.asarray(prev_hrec, dtype=np.float64),
                                "move": int(prev_move),
                                "H_next": np.asarray(cur_hrec, dtype=np.float64),
                                "g_learned": np.asarray(g_learned, dtype=np.float64)})
            reward = 0.1 if (strike_cell is None or pos != strike_cell) else -1.0
            m.compute_policy_gradient(np.array([reward], dtype=np.float32),
                                      [{"move": move, "grab": 0, "rub": 0}])
            new_pos = min(_GRID_L - 1, max(0, pos + (move - 1)))
            if warn:
                pending_danger = pos
            pos = new_pos
            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR = prev_bias, prev_plan_a, prev_plan_lr
    return triples


def _median(ratios):
    return float(fidelity_verdict(ratios)["median_ratio"])


def main_bilinear_check(seeds=(0, 1, 2, 3, 4, 5, 6, 7), warmup=300, measure=600, lam=1.0, _return=False):
    all_bilin, all_learned, all_linoff = [], [], []
    for s in seeds:
        triples = _collect_transitions_env(int(s), warmup, measure)
        if not triples:
            continue
        N = len(triples[0]["H_prev"])
        train, test = _split_temporal(triples, _N_MOVES, 0.7)
        if not train or not test:
            continue
        W = _fit_bilinear(train, _N_MOVES, N, lam)
        C = _fit_linear_offline(train, _N_MOVES, N)
        all_bilin.extend(_ratios_for_predictor(test, lambda tr: tr["H_prev"] @ W[tr["move"]]))
        all_learned.extend(_ratios_for_predictor(test, lambda tr: tr["g_learned"]))
        all_linoff.extend(_ratios_for_predictor(test, lambda tr: C[tr["move"]]))
    if not all_bilin:
        print("Aucune transition collectee -> NO_DATA.")
        res = {"verdict": "NO_DATA", "median_bilin": 1.0, "median_learned": 1.0, "median_linoff": 1.0, "n": 0}
        return res if _return else None
    verdict = _verdict_bilinear(all_bilin, all_learned)
    mb, ml, mo = _median(all_bilin), _median(all_learned), _median(all_linoff)
    print("\n=== g bilineaire vs lineaire (env-grille, ratios test-set) ===")
    print("  median ratio (pred_err/base_err) : bilin=%.3f  learned-lin=%.3f  offline-lin=%.3f  (n=%d)"
          % (mb, ml, mo, len(all_bilin)))
    print("=== VERDICT ===")
    print("  -> %s (FIDELE si bilin G_FIDELE ET bilin<learned ; NEUTRAL si bilin ratio>=0.95)" % verdict)
    res = {"verdict": verdict, "median_bilin": mb, "median_learned": ml, "median_linoff": mo, "n": len(all_bilin)}
    return res if _return else None


if __name__ == "__main__":
    main_bilinear_check()
```

- [ ] **Step 4 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -v`
Expected : PASS (7 tests). Le smoke lance 1 rollout réduit (90 ticks) + fit → quelques secondes, laisse finir.

- [ ] **Step 5 : vérifier zéro modif fichiers existants + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && git status --short`
Expected : seuls les 2 fichiers du chantier. Vérifier que les `print` de `main_bilinear_check` sont strictement ASCII.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear"
git add tools/g_bilinear_probe.py tests/sandbox/test_g_bilinear_probe.py
git commit -m "feat(gbilinear): rollout env-grille (triplets) + main_bilinear_check + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 substrat env-grille → `_collect_transitions_env` (T2). §3 triplets (H_prev/move/H_next/g_learned) → structure T1+T2. §4 prédicteurs (baseline implicite, learned, linéaire-offline, bilinéaire ridge) → `_fit_bilinear`/`_fit_linear_offline`/`_ratios_for_predictor` (T1) + orchestration (T2). §5 verdict gelé → `_verdict_bilinear` (T1). §9 interfaces → T1 (split/fits/ratios/verdict) + T2 (collecte/main). §8 périmètre additif + ASCII + déterminisme → Global Constraints + steps de vérif. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; code complet et exécutable.

**3. Type consistency :** triplet dict `{H_prev, move, H_next, g_learned}` cohérent T1↔T2. `_fit_bilinear` renvoie `dict move->W (N,N)`, consommé en `tr["H_prev"] @ W[tr["move"]]` (convention ligne, cohérent). `_fit_linear_offline` renvoie `dict move->c (N,)`, consommé `C[tr["move"]]`. `_verdict_bilinear` seuils via `fidelity_verdict` (G_FIDELE/NEUTRE/G_INUTILE). `main_bilinear_check` clés retour (`verdict/median_bilin/median_learned/median_linoff/n`) cohérentes report + smoke assert. Le remplacement de l'import de tête (T2 step 3) rend `MambaAgent/_obs_bench/...` disponibles pour `_collect_transitions_env`.
