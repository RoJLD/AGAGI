# EDR 193 (REFORMULÉ) — g-fidélité décomposée FULL vs CACHÉS : Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reworker la sonde pour décomposer la g-fidélité (linéaire-appris + bilinéaire ridge) en ratio FULL (172 dims) vs HIDDEN (nœuds cachés [14,64)), et trancher si le G_FIDELE d'EDR 135 sur env-grille est un artefact de ré-encodage d'entrée ou une vraie anticipation latente.

**Architecture:** Réécriture COMPLÈTE de `tools/g_bilinear_probe.py` (branche non mergée) : conserve collecte + fits ridge, ajoute un masque de nœuds au ratio + un verdict de décomposition + rework de `main`. Réécriture complète du test associé.

**Tech Stack:** Python, NumPy (fit ridge déterministe). `MambaAgent` legacy en import read-only. PAS de torch/Biosphere/HoF/KuzuDB.

## Global Constraints

- **TOOLING ADDITIF** : modifier SEULEMENT `tools/g_bilinear_probe.py` et `tests/sandbox/test_g_bilinear_probe.py`. NE modifier AUCUN autre fichier — ni `tools/g_fidelity_probe.py` (mergé), ni `src/`, ni torch substrat.
- **Prints ASCII-only** (cp1252) ; accents seulement dans docstrings.
- **Déterminisme** : rollout `np.random.seed(seed)` + ridge `np.linalg.solve` ; flags `PLAN_*` restaurés en `finally` ; 2 passes byte-identiques.
- **Verdict gelé** (spec §6) : `ENCODING_ARTIFACT` / `LATENT_BILINEAR` / `LATENT_LINEAR` / `PARTIAL`. λ=1.0. Masque cachés = `[n_in, N - n_out)` avec `n_in=14 (_OBS_DIM)`, `n_out=108`. Ne PAS ajuster après le run.
- **Convention ridge** (inchangée) : `ΔH_pred = H_prev @ W_a`, `W_a = solve(X^T X + λI, X^T ΔY)`.

---

## Task 1 (unique) : rework décomposition FULL/HIDDEN + verdict + main + tests

**Files:**
- Overwrite: `tools/g_bilinear_probe.py`
- Overwrite: `tests/sandbox/test_g_bilinear_probe.py`

**Interfaces produites :** `_split_temporal`, `_fit_linear_offline`, `_fit_bilinear` (inchangés) ; `_ratios_for_predictor(test, predictor_fn, idx=None, base_thresh=1e-4)` (signature étendue) ; `_hidden_idx(N, n_in, n_out)` (nouveau) ; `_verdict_decomposition(learned_full, bilin_full, learned_hidden, bilin_hidden)` (remplace `_verdict_bilinear`) ; `_collect_transitions_env`, `_median` (inchangés) ; `main_bilinear_check(...)` (reworké).

- [ ] **Step 1 : écrire/écraser les tests qui échouent**

Écraser INTÉGRALEMENT `tests/sandbox/test_g_bilinear_probe.py` par EXACTEMENT :

```python
import numpy as np

from tools.g_bilinear_probe import (
    _split_temporal, _fit_bilinear, _fit_linear_offline, _ratios_for_predictor,
    _hidden_idx, _verdict_decomposition,
)


def _toy_triples(n, N, M, seed, move=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        h = rng.standard_normal(N).astype(np.float64)
        dh = h @ M
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
    assert float(np.median(ratios)) < 0.5


def test_linear_offline_recovers_constant_delta():
    N = 4
    c = np.array([1.0, -2.0, 0.5, 3.0])
    triples = [{"H_prev": np.zeros(N), "move": 0, "H_next": c.copy(),
                "g_learned": np.zeros(N)} for _ in range(10)]
    C = _fit_linear_offline(triples, 1, N)
    assert np.allclose(C[0], c)


def test_hidden_idx():
    idx = _hidden_idx(172, 14, 108)
    assert idx[0] == 14 and idx[-1] == 63 and len(idx) == 50


def test_ratios_masked_isolates_dims():
    # dim 0 parfaitement predite (delta connu), dim 1 = pur bruit non predit.
    # FULL melange les deux ; masque sur dim 1 seule -> ratio ~1 (aucune prediction utile).
    test = [{"H_prev": np.array([1.0, 1.0]), "move": 0, "H_next": np.array([2.0, 5.0]),
             "g_learned": np.zeros(2)}]
    pred = lambda tr: np.array([1.0, 0.0])   # predit exactement dim0 (delta=+1), rien sur dim1
    r_full = _ratios_for_predictor(test, pred)                 # (0 + 16)/(1+16) ~ 0.94
    r_hid = _ratios_for_predictor(test, pred, idx=np.array([1]))  # 16/16 = 1.0
    assert r_hid[0] == 1.0 and r_full[0] < 1.0


def test_verdict_encoding_artifact():
    # FULL fidele (both), HIDDEN neutre (both >=0.95) -> ARTIFACT
    fid = [0.4, 0.5, 0.3, 0.45, 0.5]
    neu = [1.0, 1.01, 0.99, 1.0, 1.0]
    assert _verdict_decomposition(fid, fid, neu, neu) == "ENCODING_ARTIFACT"


def test_verdict_latent_bilinear():
    # HIDDEN : bilin fidele ET bat learned -> LATENT_BILINEAR
    learned_h = [0.9, 0.85, 0.92, 0.88, 0.9]
    bilin_h = [0.4, 0.5, 0.3, 0.45, 0.5]
    fid = [0.5, 0.5, 0.5, 0.5, 0.5]
    assert _verdict_decomposition(fid, fid, learned_h, bilin_h) == "LATENT_BILINEAR"


def test_verdict_latent_linear():
    # HIDDEN : learned fidele, bilin NE bat PAS -> LATENT_LINEAR
    learned_h = [0.4, 0.5, 0.3, 0.45, 0.5]
    bilin_h = [0.6, 0.65, 0.55, 0.6, 0.6]
    fid = [0.5, 0.5, 0.5, 0.5, 0.5]
    assert _verdict_decomposition(fid, fid, learned_h, bilin_h) == "LATENT_LINEAR"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -v`
Expected : FAIL (ImportError sur `_hidden_idx`/`_verdict_decomposition`, ou AttributeError).

- [ ] **Step 3 : écraser INTÉGRALEMENT `tools/g_bilinear_probe.py` par EXACTEMENT ce code**

```python
"""tools/g_bilinear_probe.py — g-fidelite decomposee FULL vs CACHES (EDR 193, re-examine EDR 135).

EDR 135 : g LINEAIRE du modele = delta constant par action. Sur env-grille (obs riches causal) il est G_FIDELE
(median ~0.75), PAS neutre (le neutre = mode synthetique). Mais la position est un one-hot dans les noeuds d'ENTREE,
pos_t = clip(pos_{t-1}+move-1) = decalage deterministe par action -> une fidelite FULL peut n'etre QUE ce re-encodage,
sans anticipation latente. On decompose : ratio sur dims PLEINES (172) vs dims CACHEES [n_in, N-n_out) = [14,64). Si la
fidelite s'effondre sur les caches -> artefact d'encodage (corrige EDR 135). Sinon on demande si le bilineaire (fit
offline par ridge) capte le latent cache mieux que le lineaire. Auto-contenu (numpy pur ; MambaAgent read-only).

Usage : python -m tools.g_bilinear_probe
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.g_fidelity_probe import (
    fidelity_verdict, MambaAgent, MambaBatchModel, _obs_bench, _GRID_L, _N_MOVES, _T_WARN_PERIOD, _OBS_DIM,
)


def _split_temporal(triples, n_moves, frac=0.7):
    """Split TEMPOREL par action : premiers frac% train, reste test. Preserve l'ordre."""
    train, test = [], []
    for mv in range(n_moves):
        grp = [tr for tr in triples if tr["move"] == mv]
        k = int(len(grp) * frac)
        train.extend(grp[:k])
        test.extend(grp[k:])
    return train, test


def _fit_linear_offline(train, n_moves, N):
    """Delta CONSTANT par action : c_a = moyenne train de (H_next - H_prev). Renvoie dict move -> (N,)."""
    out = {}
    for mv in range(n_moves):
        deltas = [np.asarray(tr["H_next"], dtype=np.float64) - np.asarray(tr["H_prev"], dtype=np.float64)
                  for tr in train if tr["move"] == mv]
        out[mv] = np.mean(deltas, axis=0) if deltas else np.zeros(N, dtype=np.float64)
    return out


def _fit_bilinear(train, n_moves, N, lam):
    """g BILINEAIRE par ridge, W_a (N,N) par action. Convention LIGNE : ΔH_pred = H_prev @ W_a.
    W_a = solve(X^T X + lam*I, X^T ΔY), X=(m,N) H_prev train, ΔY=(m,N) (H_next-H_prev) train."""
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


def _ratios_for_predictor(test, predictor_fn, idx=None, base_thresh=1e-4):
    """ratio = pred_err/base_err par triplet test (filtre base_err > base_thresh). predictor_fn(tr) -> ΔH_pred (N,).
    idx=None -> dims pleines ; idx (array) -> erreur restreinte a ces dims (controle FULL vs CACHES)."""
    ratios = []
    for tr in test:
        H_prev = np.asarray(tr["H_prev"], dtype=np.float64)
        H_next = np.asarray(tr["H_next"], dtype=np.float64)
        delta_pred = np.asarray(predictor_fn(tr), dtype=np.float64)
        resid = H_prev + delta_pred - H_next
        base = H_prev - H_next
        if idx is not None:
            resid = resid[idx]
            base = base[idx]
        pred_err = float(np.mean(resid ** 2))
        base_err = float(np.mean(base ** 2))
        if base_err > base_thresh:
            ratios.append(pred_err / base_err)
    return ratios


def _hidden_idx(N, n_in, n_out):
    """Indices des noeuds CACHES [n_in, N - n_out) (hors blocs one-hot entree/sortie ; cf. mamba_agent map_idx)."""
    return np.arange(n_in, N - n_out)


def _verdict_decomposition(learned_full, bilin_full, learned_hidden, bilin_hidden):
    """GELE (spec S6). Decompose FULL vs HIDDEN pour learned + bilin.
    ENCODING_ARTIFACT : FULL fidele (les 2) MAIS HIDDEN non-fidele (les 2, median>=0.95) -> corrige EDR 135.
    LATENT_BILINEAR : bilin-HIDDEN fidele ET median(bilin-hidden) < median(learned-hidden).
    LATENT_LINEAR : learned-HIDDEN fidele ET bilin ne bat pas. Sinon PARTIAL."""
    lf, bf = fidelity_verdict(learned_full), fidelity_verdict(bilin_full)
    lh, bh = fidelity_verdict(learned_hidden), fidelity_verdict(bilin_hidden)
    full_fidele = (lf["verdict"] == "G_FIDELE" and bf["verdict"] == "G_FIDELE")
    hidden_dead = (lh["verdict"] != "G_FIDELE" and bh["verdict"] != "G_FIDELE"
                   and lh["median_ratio"] >= 0.95 and bh["median_ratio"] >= 0.95)
    if full_fidele and hidden_dead:
        return "ENCODING_ARTIFACT"
    if bh["verdict"] == "G_FIDELE" and bh["median_ratio"] < lh["median_ratio"]:
        return "LATENT_BILINEAR"
    if lh["verdict"] == "G_FIDELE" and bh["median_ratio"] >= lh["median_ratio"]:
        return "LATENT_LINEAR"
    return "PARTIAL"


def _collect_transitions_env(seed, warmup, measure):
    """Rollout env-grille 1-D deterministe (miroir de collect_ratios_env, EDR 135). Capture les triplets latents
    (H_prev, move, H_next, g_learned) apres warmup. g_learned = colonne g LINEAIRE apprise (reference EDR 135).
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


def main_bilinear_check(seeds=(0, 1, 2, 3, 4, 5, 6, 7), warmup=300, measure=600, lam=1.0,
                        n_in=_OBS_DIM, n_out=108, _return=False):
    lf, bf, lh, bh = [], [], [], []
    for s in seeds:
        triples = _collect_transitions_env(int(s), warmup, measure)
        if not triples:
            continue
        N = len(triples[0]["H_prev"])
        hid = _hidden_idx(N, n_in, n_out)
        train, test = _split_temporal(triples, _N_MOVES, 0.7)
        if not train or not test:
            continue
        W = _fit_bilinear(train, _N_MOVES, N, lam)
        learned_fn = lambda tr: tr["g_learned"]
        bilin_fn = lambda tr: tr["H_prev"] @ W[tr["move"]]
        lf.extend(_ratios_for_predictor(test, learned_fn))
        bf.extend(_ratios_for_predictor(test, bilin_fn))
        lh.extend(_ratios_for_predictor(test, learned_fn, idx=hid))
        bh.extend(_ratios_for_predictor(test, bilin_fn, idx=hid))
    if not lf:
        print("Aucune transition collectee -> NO_DATA.")
        res = {"verdict": "NO_DATA", "med_learned_full": 1.0, "med_bilin_full": 1.0,
               "med_learned_hidden": 1.0, "med_bilin_hidden": 1.0, "n": 0}
        return res if _return else None
    verdict = _verdict_decomposition(lf, bf, lh, bh)
    mlf, mbf, mlh, mbh = _median(lf), _median(bf), _median(lh), _median(bh)
    print("\n=== g-fidelite decomposee FULL vs CACHES (env-grille, ratios test-set) ===")
    print("  FULL   : learned-lin=%.3f  bilin=%.3f" % (mlf, mbf))
    print("  HIDDEN : learned-lin=%.3f  bilin=%.3f  (n=%d)" % (mlh, mbh, len(lh)))
    print("=== VERDICT ===")
    print("  -> %s (ARTIFACT si FULL fidele mais HIDDEN neutre ; LATENT_BILINEAR si bilin-hidden fidele et < learned)"
          % verdict)
    res = {"verdict": verdict, "med_learned_full": mlf, "med_bilin_full": mbf,
           "med_learned_hidden": mlh, "med_bilin_hidden": mbh, "n": len(lh)}
    return res if _return else None


if __name__ == "__main__":
    main_bilinear_check()
```

- [ ] **Step 4 : ajouter le test smoke qui exerce le pipeline complet**

Ajouter à la FIN de `tests/sandbox/test_g_bilinear_probe.py` :

```python
from tools.g_bilinear_probe import main_bilinear_check


def test_smoke_decomposition_returns_verdict():
    res = main_bilinear_check(seeds=(0,), warmup=30, measure=90, _return=True)
    assert res["verdict"] in {"ENCODING_ARTIFACT", "LATENT_BILINEAR", "LATENT_LINEAR", "PARTIAL", "NO_DATA"}
    assert "med_learned_hidden" in res and "med_bilin_hidden" in res
```

- [ ] **Step 5 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && python -m pytest tests/sandbox/test_g_bilinear_probe.py -v`
Expected : PASS (9 tests — 3 fits/split + hidden_idx + masked + 3 verdict + smoke). Le smoke lance 1 rollout réduit (120 ticks) → quelques secondes.

- [ ] **Step 6 : vérifier zéro modif hors périmètre + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear" && git status --short`
Expected : seuls `tools/g_bilinear_probe.py` et `tests/sandbox/test_g_bilinear_probe.py`. Vérifier que les `print` de `main_bilinear_check` sont strictement ASCII.

- [ ] **Step 7 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/g-bilinear"
git add tools/g_bilinear_probe.py tests/sandbox/test_g_bilinear_probe.py
git commit -m "feat(gbilinear): rework decomposition FULL vs CACHES + verdict artefact/latent (reformulation post-opus)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 layout nœuds → `_hidden_idx` (14/64). §3 collecte → `_collect_transitions_env` (inchangé). §4 prédicteurs → fits (inchangés) + `learned_fn`/`bilin_fn`. §5 métrique décomposée → `_ratios_for_predictor(idx=)` FULL+HIDDEN dans `main`. §6 verdict gelé → `_verdict_decomposition`. §10 delta interfaces → tous couverts. Périmètre/ASCII/déterminisme → Global Constraints + steps. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; code complet.

**3. Type consistency :** `_ratios_for_predictor` `idx=None` par défaut → rétrocompatible avec `test_bilinear_fits_state_dependent_map`. `_verdict_decomposition(4 listes)` cohérent avec l'appel `main` (lf/bf/lh/bh). Clés retour `main` (`med_learned_full/med_bilin_full/med_learned_hidden/med_bilin_hidden/n`) cohérentes report + smoke assert. `_hidden_idx(172,14,108)` → [14,64), 50 dims (test). Lambdas `learned_fn`/`bilin_fn` appelées immédiatement (pas de late-binding).
