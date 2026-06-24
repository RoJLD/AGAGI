# S2 — « Le monde EXIGE-t-il l'intelligence ? » — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Benchmark falsifiable, monde par monde, qui mesure si un champion HoF bat 3 baselines bêtes (action-aléatoire, nouveau-né, réflexe) sur la **survie individuelle** — pour trancher si le monde *exige* l'intelligence (cause-racine B, EDR 010).

**Architecture:** Un module stats pur-numpy pré-enregistré (`s2_stats.py`), un seam d'injection 2-lignes (`batch_model_cls`) + un `benchmark_mode` dans `Biosphere3D`, deux `BaselineBatchModel` drop-in, et un runner (`tools/s2_demand.py`) qui orchestre champion + baselines × 4 mondes, calcule survie individuelle censurée + `life_score` (cohérence), fixe K par power analysis, applique IUT+Holm et rend un verdict 3-issues. Bâti sur le `Harness` D1 (appariement seedé + provenance).

**Tech Stack:** Python 3.13, numpy (pas de scipy — Wilcoxon par approximation normale, valide à K≥12), pytest. `math.erf` pour la CDF normale.

**Spec (pré-enregistrement) :** `docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md`

---

## File Structure

- **Create** `src/seed_ai/s2_stats.py` — stats pré-enregistrées : `cliffs_delta`, `median_ratio`, `wilcoxon_signed_rank`, `bootstrap_ci`, `holm`, `iut_pvalue`, `s2_verdict`.
- **Create** `tests/sandbox/test_s2_stats.py` — tests unitaires (valeurs connues).
- **Create** `src/agents/baseline_models.py` — `BaselineBatchModel` (base), `RandomActionBatchModel`, `ReflexBatchModel`.
- **Create** `tests/sandbox/test_baseline_models.py` — forme des logits, `surprise=0`, comportement de poursuite.
- **Modify** `src/worlds/world_1_stoneage.py` — seam `batch_model_cls` (`__init__` + l.945) + `benchmark_mode` (`__init__` + gate reproduction l.1276 + gate HGT).
- **Create** `tests/sandbox/test_benchmark_mode.py` — seam d'injection + cohorte fixe.
- **Create** `tools/s2_demand.py` — runner (run_condition, provisioning, pilote/power, grille, verdict, save, EDR).
- **Create** `tests/sandbox/test_s2_demand.py` — run_condition reproductible + survie individuelle.

Convention : tests dans `tests/sandbox/`, lancés par `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: Stats — `cliffs_delta` + `median_ratio`

**Files:**
- Create: `src/seed_ai/s2_stats.py`
- Test: `tests/sandbox/test_s2_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_s2_stats.py
import numpy as np
from src.seed_ai.s2_stats import cliffs_delta, median_ratio


def test_cliffs_delta_full_dominance():
    # tous les a > tous les b -> delta = +1
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0


def test_cliffs_delta_full_dominance_negative():
    assert cliffs_delta([1, 2, 3], [5, 6, 7]) == -1.0


def test_cliffs_delta_no_difference():
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_median_ratio_basic():
    assert median_ratio([20, 40, 60], [10, 20, 30]) == 2.0


def test_median_ratio_zero_denominator_returns_inf():
    assert median_ratio([5, 5, 5], [0, 0, 0]) == float("inf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k "cliffs or median" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.seed_ai.s2_stats'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/seed_ai/s2_stats.py
"""
src/seed_ai/s2_stats.py — Stats PRÉ-ENREGISTRÉES du benchmark S2 (le monde exige-t-il l'intelligence ?).

Survie = distribution asymétrique/censurée -> effets NON-paramétriques (Cliff's delta, ratio de
médianes) + test APPARIÉ sur les différences (Wilcoxon signed-rank, approx. normale valide à K>=12).
Pas de scipy (hors dépendances) : tout en numpy + math.erf. Aucune hypothèse de normalité.
Détail : docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md (§8).
"""
import math
import numpy as np


def cliffs_delta(a, b):
    """Dominance stochastique de a sur b dans [-1, 1] : P(a>b) - P(a<b). Robuste, sans échelle."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return 0.0
    diff = a[:, None] - b[None, :]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / (a.size * b.size))


def median_ratio(a, b):
    """Ratio des médianes med(a)/med(b). inf si med(b)=0 et med(a)>0 ; 1.0 si les deux sont 0."""
    ma, mb = float(np.median(a)), float(np.median(b))
    if mb == 0.0:
        return float("inf") if ma > 0.0 else 1.0
    return ma / mb
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k "cliffs or median" -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/s2_stats.py tests/sandbox/test_s2_stats.py
git commit -m "feat(s2_stats): Cliff's delta + ratio de medianes (effets non-parametriques, S2)"
```

---

### Task 2: Stats — `wilcoxon_signed_rank` (test apparié + p-value)

**Files:**
- Modify: `src/seed_ai/s2_stats.py`
- Test: `tests/sandbox/test_s2_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_stats.py
from src.seed_ai.s2_stats import wilcoxon_signed_rank


def test_wilcoxon_all_positive_is_significant():
    # 15 différences toutes positives -> p très petit
    d = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    w, p = wilcoxon_signed_rank(d)
    assert p < 0.01


def test_wilcoxon_symmetric_not_significant():
    d = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0]
    w, p = wilcoxon_signed_rank(d)
    assert p > 0.5


def test_wilcoxon_drops_zeros_and_handles_empty():
    assert wilcoxon_signed_rank([0.0, 0.0])[1] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k wilcoxon -v`
Expected: FAIL — `ImportError: cannot import name 'wilcoxon_signed_rank'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/seed_ai/s2_stats.py

def _phi(z):
    """CDF de la loi normale centrée réduite (sans scipy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _average_ranks(values):
    """Rangs moyens (gère les ex aequo) — valeurs >= 0 (abs des différences)."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # rangs 1-indexés, moyenne sur les ex aequo
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon_signed_rank(d):
    """Test de Wilcoxon signé sur les différences appariées d (champion - baseline).
    Approximation normale avec correction de continuité (valide à n>=12, plancher S2).
    Renvoie (W_plus, p_bilatéral). Les zéros sont retirés (convention). p=1.0 si n=0."""
    d = np.asarray(d, dtype=float)
    d = d[d != 0.0]
    n = d.size
    if n == 0:
        return 0.0, 1.0
    ranks = _average_ranks(np.abs(d))
    w_plus = float(np.sum(ranks[d > 0]))
    mean = n * (n + 1) / 4.0
    var = n * (n + 1) * (2 * n + 1) / 24.0
    if var == 0.0:
        return w_plus, 1.0
    cc = 0.5 * np.sign(w_plus - mean)            # correction de continuité
    z = (w_plus - mean - cc) / math.sqrt(var)
    p = 2.0 * (1.0 - _phi(abs(z)))
    return w_plus, float(min(1.0, max(0.0, p)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k wilcoxon -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/s2_stats.py tests/sandbox/test_s2_stats.py
git commit -m "feat(s2_stats): Wilcoxon signed-rank apparie + p-value (approx normale, S2)"
```

---

### Task 3: Stats — `bootstrap_ci` (IC apparié)

**Files:**
- Modify: `src/seed_ai/s2_stats.py`
- Test: `tests/sandbox/test_s2_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_stats.py
from src.seed_ai.s2_stats import bootstrap_ci, median_ratio as _mr


def test_bootstrap_ci_brackets_point_estimate():
    a = [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42]
    b = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    lo, hi = bootstrap_ci(_mr, a, b, n_boot=500, alpha=0.05, seed=1)
    assert lo <= 2.0 <= hi          # ratio vrai ~2
    assert lo < hi


def test_bootstrap_ci_is_deterministic_with_seed():
    a, b = [3, 4, 5, 6], [1, 2, 3, 4]
    assert bootstrap_ci(_mr, a, b, n_boot=200, seed=7) == bootstrap_ci(_mr, a, b, n_boot=200, seed=7)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k bootstrap -v`
Expected: FAIL — `ImportError: cannot import name 'bootstrap_ci'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/seed_ai/s2_stats.py

def bootstrap_ci(stat_fn, *arrays, n_boot=2000, alpha=0.05, seed=0):
    """IC percentile bootstrap d'une statistique. APPARIÉ : tous les arrays sont rééchantillonnés
    avec les MÊMES indices (préserve l'appariement seed-à-seed champion/baseline). stat_fn reçoit
    les arrays rééchantillonnés. Déterministe au seed."""
    arrays = [np.asarray(x, dtype=float) for x in arrays]
    n = len(arrays[0])
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot, dtype=float)
    for k in range(n_boot):
        idx = rng.integers(0, n, n)
        stats[k] = stat_fn(*[x[idx] for x in arrays])
    finite = stats[np.isfinite(stats)]
    if finite.size == 0:
        return float("nan"), float("nan")
    lo = float(np.percentile(finite, 100.0 * alpha / 2.0))
    hi = float(np.percentile(finite, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k bootstrap -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/s2_stats.py tests/sandbox/test_s2_stats.py
git commit -m "feat(s2_stats): bootstrap_ci apparie (IC du ratio de medianes, S2)"
```

---

### Task 4: Stats — `holm` + `iut_pvalue`

**Files:**
- Modify: `src/seed_ai/s2_stats.py`
- Test: `tests/sandbox/test_s2_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_stats.py
from src.seed_ai.s2_stats import holm, iut_pvalue


def test_holm_known_values():
    # Holm step-down : p triés [.01,.02,.04] * [3,2,1] = [.03,.04,.04] (monotone)
    adj = holm([0.04, 0.01, 0.02])
    assert abs(adj[1] - 0.03) < 1e-9     # le .01 -> .03
    assert adj[0] >= adj[2]              # monotonie après tri


def test_holm_caps_at_one():
    assert all(p <= 1.0 for p in holm([0.9, 0.8, 0.7]))


def test_iut_pvalue_is_max():
    # Intersection-Union : on ne rejette que si TOUTES rejettent -> p = max
    assert iut_pvalue([0.01, 0.2, 0.03]) == 0.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k "holm or iut" -v`
Expected: FAIL — `ImportError: cannot import name 'holm'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/seed_ai/s2_stats.py

def holm(pvals):
    """Correction Holm-Bonferroni (step-down) du FWER. Renvoie les p-values ajustées (monotones,
    bornées à 1). Famille S2 = les 4 verdicts-monde (m=4), PAS les 12 comparaisons baseline."""
    pvals = np.asarray(pvals, dtype=float)
    m = pvals.size
    order = np.argsort(pvals)
    adj = np.empty(m, dtype=float)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])   # monotonie step-down
        adj[i] = min(1.0, running)
    return adj


def iut_pvalue(pvals):
    """Intersection-Union Test : pour conclure que le champion bat les 3 baselines (critère
    CONJONCTIF), la p-value du monde = MAX des p-values. Contrôle déjà le type-I à alpha, SANS
    correction (propriété IUT). C'est le bon outil pour un min-test, pas Holm."""
    return float(np.max(np.asarray(pvals, dtype=float)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k "holm or iut" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/s2_stats.py tests/sandbox/test_s2_stats.py
git commit -m "feat(s2_stats): Holm (FWER 4 mondes) + IUT min-test (critere conjonctif, S2)"
```

---

### Task 5: Stats — `s2_verdict` (table de décision 3 issues + cohérence)

**Files:**
- Modify: `src/seed_ai/s2_stats.py`
- Test: `tests/sandbox/test_s2_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_stats.py
import numpy as np
from src.seed_ai.s2_stats import s2_verdict


def _rng_arr(seed, lo, hi, n=14):
    return list(np.random.default_rng(seed).uniform(lo, hi, n))


def test_verdict_exige_when_champion_dominates():
    surv_champ = _rng_arr(1, 200, 260)
    surv_base = {"random": _rng_arr(2, 10, 30), "newborn": _rng_arr(3, 20, 40), "reflex": _rng_arr(4, 40, 70)}
    life_champ = _rng_arr(5, 2000, 3000)
    life_base = {"random": _rng_arr(6, 0, 50), "newborn": _rng_arr(7, 0, 80), "reflex": _rng_arr(8, 50, 200)}
    v = s2_verdict(surv_champ, surv_base, life_champ, life_base)
    assert v["verdict"] == "EXIGE"
    assert v["coherence_ok"] is True


def test_verdict_void_when_champion_fails_coherence():
    # champion ne bat PAS les baselines sur sa propre fitness (life_score) -> VOID
    surv_champ = _rng_arr(1, 200, 260)
    surv_base = {"reflex": _rng_arr(4, 40, 70)}
    life_champ = _rng_arr(9, 0, 10)              # life_score champion FAIBLE
    life_base = {"reflex": _rng_arr(10, 100, 300)}
    v = s2_verdict(surv_champ, surv_base, life_champ, life_base)
    assert v["verdict"] == "VOID"


def test_verdict_nexige_pas_when_champion_equiv_reflex():
    surv_champ = _rng_arr(1, 40, 70)
    surv_base = {"random": _rng_arr(2, 10, 30), "reflex": _rng_arr(4, 40, 70)}
    life_champ = _rng_arr(5, 500, 800)
    life_base = {"random": _rng_arr(6, 0, 50), "reflex": _rng_arr(8, 50, 200)}
    v = s2_verdict(surv_champ, surv_base, life_champ, life_base)
    assert v["verdict"] == "N'EXIGE PAS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -k verdict -v`
Expected: FAIL — `ImportError: cannot import name 's2_verdict'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/seed_ai/s2_stats.py

# Seuils PRÉ-ENREGISTRÉS (spec §8). Modifiables UNIQUEMENT via l'addendum post-pilote daté.
ALPHA = 0.05
CLIFF_THRESH = 0.33        # "large" (Romano) — effet principal
RATIO_LO_THRESH = 1.3      # borne_inf de l'IC bootstrap du ratio de médianes (corroborant)
EQUIV_MARGIN = 0.147       # |Cliff| < 0.147 = "negligible" (Romano) -> équivalence (placeholder pilote)


def _compare(champ, base):
    """Une comparaison appariée champion-vs-baseline -> dict de stats."""
    champ = np.asarray(champ, dtype=float)
    base = np.asarray(base, dtype=float)
    d = champ - base
    _w, p = wilcoxon_signed_rank(d)
    delta = cliffs_delta(champ, base)
    ratio = median_ratio(champ, base)
    ratio_lo, ratio_hi = bootstrap_ci(median_ratio, champ, base, n_boot=2000, alpha=ALPHA, seed=0)
    return {"p": p, "cliff": delta, "ratio": ratio, "ratio_lo": ratio_lo, "ratio_hi": ratio_hi}


def s2_verdict(surv_champ, surv_baselines, life_champ, life_baselines,
               alpha=ALPHA, cliff_thresh=CLIFF_THRESH, ratio_lo_thresh=RATIO_LO_THRESH,
               equiv_margin=EQUIV_MARGIN):
    """Verdict S2 d'UN monde (table de décision §10). surv_baselines / life_baselines : dict
    {nom: liste de survies/life appariées par seed}. Renvoie un dict complet (verdict + stats).

    - Cohérence (§6) : le champion doit battre le MEILLEUR baseline sur le life_score (sa fitness
      d'entraînement) -> sinon VOID (le champion ne se comporte pas en champion dans ce régime).
    - Survie : IUT min-test (p_monde = max des p) ; effet sur le baseline le plus FORT (réflexe).
    - Issues : EXIGE / N'EXIGE PAS (équivalence) / ANTI-CORRÉLÉ / AMBIGU."""
    # --- Test de cohérence sur life_score (IUT) ---
    life_cmps = {k: _compare(life_champ, life_baselines[k]) for k in life_baselines}
    life_p = iut_pvalue([c["p"] for c in life_cmps.values()])
    life_best_cliff = min(c["cliff"] for c in life_cmps.values())   # pire baseline sur la cohérence
    coherence_ok = (life_p < alpha) and (life_best_cliff > 0.0)
    if not coherence_ok:
        return {"verdict": "VOID", "coherence_ok": False, "life_p": life_p,
                "survival": {k: _compare(surv_champ, surv_baselines[k]) for k in surv_baselines}}

    # --- Survie ---
    cmps = {k: _compare(surv_champ, surv_baselines[k]) for k in surv_baselines}
    p_monde = iut_pvalue([c["p"] for c in cmps.values()])
    # baseline le plus FORT = plus haute survie médiane (le plus dur à battre, attendu = réflexe)
    strongest = max(surv_baselines, key=lambda k: np.median(surv_baselines[k]))
    s = cmps[strongest]

    if p_monde < alpha and s["cliff"] >= cliff_thresh and s["ratio_lo"] >= ratio_lo_thresh:
        verdict = "EXIGE"
    elif s["cliff"] < -cliff_thresh and p_monde < alpha:
        verdict = "ANTI-CORRELE"
    elif abs(s["cliff"]) < equiv_margin:
        verdict = "N'EXIGE PAS"
    else:
        verdict = "AMBIGU"

    return {"verdict": verdict, "coherence_ok": True, "life_p": life_p,
            "p_monde": p_monde, "strongest_baseline": strongest,
            "survival": cmps}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_stats.py -v`
Expected: PASS (toute la suite s2_stats, ~16 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/s2_stats.py tests/sandbox/test_s2_stats.py
git commit -m "feat(s2_stats): s2_verdict — table 3 issues + test de coherence life_score (S2)"
```

---

### Task 6: Seam d'injection — `batch_model_cls` dans `Biosphere3D`

**But :** permettre au runner d'injecter un `BaselineBatchModel` sans forker le monde. 2 lignes, rétro-compatible.

**Files:**
- Modify: `src/worlds/world_1_stoneage.py:38` (zone `__init__`), `:945` (instanciation)
- Test: `tests/sandbox/test_benchmark_mode.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_benchmark_mode.py
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaBatchModel


def test_default_batch_model_cls_is_mamba():
    env = Biosphere3D(WorldConfig())
    assert env.batch_model_cls is MambaBatchModel
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_benchmark_mode.py::test_default_batch_model_cls_is_mamba -v`
Expected: FAIL — `AttributeError: 'Biosphere3D' object has no attribute 'batch_model_cls'`

- [ ] **Step 3: Write minimal implementation**

Dans `src/worlds/world_1_stoneage.py`, juste après `self.world_model = WorldModel(...)` (l.38) :

```python
        # Seam d'injection (S2) : classe du batch model lue à l'inférence. Défaut = MambaBatchModel
        # (inchangé). Le runner S2 le remplace par un BaselineBatchModel (RandomAction/Reflex) APRÈS
        # construction du monde -> baselines sans connectome, zéro fork. Spec §11.
        self.batch_model_cls = MambaBatchModel
```

À la ligne 945, remplacer :

```python
        batch_model = MambaBatchModel(models, world_model=self.world_model)
```

par :

```python
        batch_model = self.batch_model_cls(models, world_model=self.world_model)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_benchmark_mode.py::test_default_batch_model_cls_is_mamba -v`
Expected: PASS

- [ ] **Step 5: Non-régression (le monde tourne toujours)**

Run: `python -m pytest tests/sandbox/test_crafting.py tests/sandbox/test_evolution.py -q`
Expected: PASS (aucune régression du moteur)

- [ ] **Step 6: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_benchmark_mode.py
git commit -m "feat(world): seam batch_model_cls (injection baselines S2, retro-compatible)"
```

---

### Task 7: `benchmark_mode` — cohorte fixe (reproduction + HGT OFF)

**But :** désactiver reproduction/mutation/HGT pendant la mesure (sinon la lignée ne s'éteint jamais → survie plafonnée à 400, blocker du panel). L'apprentissage intra-vie reste ON (spec §4). Scaffolds/nuit gérés par le runner (`current_era` haut, `night_enabled=False`).

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`__init__` ; reproduction l.1276 ; appel HGT)
- Test: `tests/sandbox/test_benchmark_mode.py`

- [ ] **Step 1: Localiser l'appel HGT à gater**

Run: `grep -n "horizontal_gene_transfer\|HorizontalGeneTransfer\|hgt\.\|\.transfer(" src/worlds/world_1_stoneage.py`
Expected: une ligne d'appel HGT (proche de la l.860-878, méthode qui émet `HGT_FAILED`). Noter son numéro de ligne `<HGT_LINE>`.

- [ ] **Step 2: Write the failing test**

```python
# Ajouter à tests/sandbox/test_benchmark_mode.py
import numpy as np
from src.agents.mamba_agent import MambaAgent


def test_benchmark_mode_freezes_cohort_size():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000              # scaffolds OFF
    for _ in range(8):
        a = MambaAgent()
        env.add_agent(a, energy=99.0)     # quasi reproduction -> doit être bloquée
    n0 = len(env.agents)
    for _ in range(15):
        env.step()
    # cohorte fixe : la population ne CROÎT jamais (peut décroître par mort)
    assert len(env.agents) + len(getattr(env, "dead_agents", [])) <= n0


def test_default_mode_allows_reproduction_attr():
    env = Biosphere3D(WorldConfig())
    assert env.benchmark_mode is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_benchmark_mode.py -k benchmark_mode -v`
Expected: FAIL — `AttributeError: 'Biosphere3D' object has no attribute 'benchmark_mode'`

- [ ] **Step 4: Write minimal implementation**

Dans `__init__` (juste après le seam de Task 6) :

```python
        # Mode benchmark (S2) : cohorte FIXE -> désactive reproduction/mutation/HGT pendant la
        # mesure (sinon la lignée est immortelle et la survie sature au cap, blocker panel). Défaut
        # False = comportement historique. L'apprentissage intra-vie reste actif. Spec §4.
        self.benchmark_mode = False
```

À la ligne 1276, modifier la garde de reproduction :

```python
                if agent["energy"] >= self.config.agent.energy_max and not self.benchmark_mode:
```

À la ligne `<HGT_LINE>` repérée au Step 1, envelopper l'appel HGT :

```python
        if not getattr(self, "benchmark_mode", False):
            # ... (l'appel HGT existant, ré-indenté d'un niveau)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_benchmark_mode.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Non-régression**

Run: `python -m pytest tests/sandbox/test_evolution.py -q`
Expected: PASS (la reproduction par défaut est inchangée)

- [ ] **Step 7: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_benchmark_mode.py
git commit -m "feat(world): benchmark_mode — cohorte fixe (repro/mutation/HGT off, S2)"
```

---

### Task 8: `BaselineBatchModel` base + `RandomActionBatchModel`

**But :** drop-in du `MambaBatchModel` : même interface (`forward` → `(logits, compute_spent)`, `compute_policy_gradient` no-op), écrit `surprise=0` sur les agents (sinon coût cérébral/curiosité gelés, blocker panel).

**Files:**
- Create: `src/agents/baseline_models.py`
- Test: `tests/sandbox/test_baseline_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_baseline_models.py
import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.baseline_models import RandomActionBatchModel


def _agents(n=4):
    out = []
    for _ in range(n):
        a = MambaAgent()
        a.surprise = 9.9            # valeur "sale" à écraser
        a.surprise_momentum = 9.9
        out.append(a)
    return out


def test_random_action_forward_shape_matches_outputs():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    O = max(a.genome.num_outputs for a in agents)
    logits, spent = bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert logits.shape == (len(agents), O)
    assert spent.shape == (len(agents),)
    assert np.all(spent == 0.0)         # pas de rêve


def test_random_action_writes_zero_surprise():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert all(a.surprise == 0.0 and a.surprise_momentum == 0.0 for a in agents)


def test_random_action_compute_policy_gradient_is_noop():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.compute_policy_gradient(np.zeros(len(agents)), None)     # ne lève pas


def test_random_action_is_seeded():
    agents = _agents()
    obs = np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32)
    np.random.seed(123); a1, _ = RandomActionBatchModel(agents).forward(obs)
    np.random.seed(123); a2, _ = RandomActionBatchModel(agents).forward(obs)
    assert np.allclose(a1, a2)          # tire du flux global seedé (appariement)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_baseline_models.py -k random_action -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agents.baseline_models'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/baseline_models.py
"""
src/agents/baseline_models.py — Baselines "bêtes" du benchmark S2, drop-in de MambaBatchModel.

Même interface que MambaBatchModel (forward -> (logits, compute_spent) ; compute_policy_gradient
no-op), injectés via env.batch_model_cls (seam, world_1:945). Écrivent surprise=0 sur les agents
(sinon step() relit des valeurs gelées -> coût cérébral/curiosité = artefacts, blocker panel).
RandomGenome n'est PAS ici : c'est un MambaAgent à poids aléatoires qui passe par MambaBatchModel.
Spec §5/§11.
"""
import numpy as np


class BaselineBatchModel:
    """Base : interface minimale du batch model. Les sous-classes fournissent _logits(batch_obs)."""

    def __init__(self, agents, world_model=None):
        self.agents = agents
        self.B = len(agents)
        self.O = max((a.genome.num_outputs for a in agents), default=0)
        self.world_model = world_model      # ignoré (pas de surprise) — accepté pour l'interface

    def _logits(self, batch_obs):
        raise NotImplementedError

    def forward(self, batch_obs, env_surprise_batch=None):
        if self.B == 0:
            return np.array([]), np.array([])
        logits = self._logits(batch_obs)
        # Contrôle propre : pas de World Model -> surprise = 0 (sinon valeurs gelées relues par step()).
        for a in self.agents:
            a.surprise = 0.0
            a.surprise_momentum = 0.0
        compute_spent = np.zeros(self.B, dtype=np.float32)      # aucun rêve
        return logits, compute_spent

    def compute_policy_gradient(self, rewards_batch, actions_batch=None):
        return                                                  # no-op : poids figés


class RandomActionBatchModel(BaselineBatchModel):
    """Zéro politique : logits aléatoires à chaque tick, tirés du flux global np.random (déjà seedé
    aux frontières par le Harness -> appariement préservé, JAMAIS un RNG privé)."""

    def _logits(self, batch_obs):
        return np.random.randn(self.B, self.O).astype(np.float32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_baseline_models.py -k random_action -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/baseline_models.py tests/sandbox/test_baseline_models.py
git commit -m "feat(baselines): BaselineBatchModel + RandomAction (surprise=0, seede, S2)"
```

---

### Task 9: `ReflexBatchModel` — poursuite (naïf)

**But :** réflexe de poursuite exécutable depuis l'obs réelle. L'obs commence par `[dn, ds, de, dw]` (colonnes 0-3, `world_1:505`) et le monde décode `action 0,1,2,3 → N,S,E,W` (`world_1:1246-1249`) : le mapping est **direct**. Grab = `logits[24]`.

**Files:**
- Modify: `src/agents/baseline_models.py`
- Test: `tests/sandbox/test_baseline_models.py`

- [ ] **Step 1: Write the failing test (comportement, pas indices)**

```python
# Ajouter à tests/sandbox/test_baseline_models.py
from src.agents.baseline_models import ReflexBatchModel
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def test_reflex_logits_point_toward_prey_direction():
    # obs col 0..3 = dn,ds,de,dw. Proie à l'EST -> de (col 2) dominant -> argmax(logits[:8]) == 2.
    agents = [MambaAgent() for _ in range(1)]
    bm = ReflexBatchModel(agents)
    obs = np.zeros((1, agents[0].genome.num_inputs), dtype=np.float32)
    obs[0, 2] = 0.9          # de : proie à l'est
    logits, _ = bm.forward(obs)
    assert int(np.argmax(logits[0, :8])) == 2     # action East (world_1:1248)


def test_reflex_always_attempts_grab():
    agents = [MambaAgent() for _ in range(1)]
    bm = ReflexBatchModel(agents)
    logits, _ = bm.forward(np.zeros((1, agents[0].genome.num_inputs), dtype=np.float32))
    assert logits[0, 24] > 0.0                    # do_grab (world_1:1205)


def test_reflex_pursues_in_real_world():
    # intégration : un agent réflexe finit par bouger (x ou y change) en présence de proies.
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000
    env.batch_model_cls = ReflexBatchModel
    a = MambaAgent()
    env.add_agent(a, energy=80.0)
    start = (env.agents[0]["x"], env.agents[0]["y"])
    moved = False
    for _ in range(20):
        env.step()
        if not env.agents:
            break
        if (env.agents[0]["x"], env.agents[0]["y"]) != start:
            moved = True
            break
    assert moved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_baseline_models.py -k reflex -v`
Expected: FAIL — `ImportError: cannot import name 'ReflexBatchModel'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/agents/baseline_models.py

# Indices d'observation (world_1.get_batch_observations, l.505) et d'action (world_1 step, l.1246-1249).
OBS_DIR = slice(0, 4)        # [dn, ds, de, dw] -> proie au Nord/Sud/Est/Ouest
MOVE_SLOT = [0, 1, 2, 3]     # action 0=N(ny-1) 1=S(ny+1) 2=E(nx+1) 3=W(nx-1)
GRAB_LOGIT = 24              # do_grab = logits[24]


class ReflexBatchModel(BaselineBatchModel):
    """Poursuite : va vers la proie la plus proche (direction lue dans l'obs), tente de grab chaque
    tick. Heuristique non-cognitive = borne basse "réflexe". prudent=True -> variante (Task 10)."""

    def __init__(self, agents, world_model=None, prudent=False):
        super().__init__(agents, world_model)
        self.prudent = prudent

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        dirs = batch_obs[:, OBS_DIR]                     # (B, 4) = dn,ds,de,dw
        best = np.argmax(dirs, axis=1)                   # 0..3 -> N,S,E,W
        for i in range(self.B):
            logits[i, MOVE_SLOT[best[i]]] = 1.0          # argmax(logits[:8]) = direction vers la proie
            logits[i, GRAB_LOGIT] = 1.0                  # toujours tenter de ramasser
        return logits
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_baseline_models.py -k reflex -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/baseline_models.py tests/sandbox/test_baseline_models.py
git commit -m "feat(baselines): ReflexBatchModel poursuite naive (S2)"
```

---

### Task 10: `ReflexBatchModel` — variante prudente (évite l'apex hostile)

**But :** la spec §5 demande 2 variantes (naïf/prudent) et de prendre le **meilleur** comme borne réflexe — un réflexe qui fonce sur un apex qui riposte sous-estimerait la barre. Le prudent **fuit** si adjacent à un apex hostile (`on_apex_type < 0`, le Leurre). Son index d'obs n'est pas connu a priori → on le localise puis on pin le comportement par un test.

**Files:**
- Modify: `src/agents/baseline_models.py`
- Test: `tests/sandbox/test_baseline_models.py`

- [ ] **Step 1: Localiser la colonne `on_apex_type` dans l'obs**

Run: `grep -n "on_apex_type\|np.column_stack\|np.concatenate\|np.stack\|batch_obs =\|return np" src/worlds/world_1_stoneage.py | head -40`
Lire la zone d'assemblage de `get_batch_observations` (l.500-560) et compter la position de `on_apex_type` dans le vecteur final. Noter l'index `<APEX_IDX>`. (S'il n'est pas dans l'obs assemblée, le prudent est sans objet → marquer la variante inutile et conserver uniquement le naïf, documenter dans l'EDR.)

- [ ] **Step 2: Write the failing test**

```python
# Ajouter à tests/sandbox/test_baseline_models.py
def test_prudent_reflex_flees_hostile_apex():
    # apex hostile adjacent (on_apex_type < 0) ET proie au Nord (dn) -> le prudent NE fonce PAS au Nord.
    APEX_IDX = 4   # <APEX_IDX> confirmé au Step 1 ; ajuster si différent
    agents = [MambaAgent() for _ in range(1)]
    bm = ReflexBatchModel(agents, prudent=True)
    obs = np.zeros((1, agents[0].genome.num_inputs), dtype=np.float32)
    obs[0, 0] = 0.9            # dn : proie au Nord (action 0)
    obs[0, APEX_IDX] = -1.0    # apex hostile adjacent
    logits, _ = bm.forward(obs)
    assert int(np.argmax(logits[0, :8])) != 0     # ne fonce pas vers l'apex/la proie
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_baseline_models.py::test_prudent_reflex_flees_hostile_apex -v`
Expected: FAIL — le prudent fonce encore (assert violé) car la logique n'existe pas.

- [ ] **Step 4: Write minimal implementation**

Dans `baseline_models.py`, ajouter la constante puis la branche prudente :

```python
APEX_IDX = 4                 # on_apex_type dans l'obs (confirmé Task 10 Step 1)
```

```python
    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        dirs = batch_obs[:, OBS_DIR]
        best = np.argmax(dirs, axis=1)
        hostile = batch_obs[:, APEX_IDX] < 0.0 if batch_obs.shape[1] > APEX_IDX else np.zeros(self.B, bool)
        for i in range(self.B):
            move = MOVE_SLOT[best[i]]
            if self.prudent and hostile[i]:
                move = MOVE_SLOT[(int(best[i]) + 1) % 4]     # tourne -> s'éloigne de l'apex hostile
            logits[i, move] = 1.0
            logits[i, GRAB_LOGIT] = 1.0
        return logits
```

(Remplace le `_logits` de Task 9 : la branche naïve = `prudent=False` → comportement identique.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_baseline_models.py -v`
Expected: PASS (toute la suite baselines)

- [ ] **Step 6: Commit**

```bash
git add src/agents/baseline_models.py tests/sandbox/test_baseline_models.py
git commit -m "feat(baselines): variante prudente du reflexe (fuit l'apex hostile, S2)"
```

---

### Task 11: Runner — `run_condition` (survie individuelle censurée + life_score)

**But :** exécuter K ères seedées d'un monde sous une condition (champion ou baseline) et renvoyer la survie **individuelle** (âge à la mort) + `life_score`, avec les survivants de fin marqués censurés.

**Files:**
- Create: `tools/s2_demand.py`
- Test: `tests/sandbox/test_s2_demand.py`

- [ ] **Step 1: Confirmer les classes de mondes**

Run: `grep -n "^class " src/worlds/world_0_soup.py src/worlds/world_2_agricultural.py src/worlds/world_3_industrial.py`
Noter les noms exacts (ex. `SoupWorld`, `AgriculturalWorld`, `IndustrialWorld`) pour le dict `WORLDS`. Ajuster les imports du Step 3 si besoin.

- [ ] **Step 2: Write the failing test**

```python
# tests/sandbox/test_s2_demand.py
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.baseline_models import RandomActionBatchModel
from tools.s2_demand import run_condition


def test_run_condition_returns_individual_survival():
    cfg = WorldConfig()
    out = run_condition(Biosphere3D, RandomActionBatchModel, genome=None,
                        seed=2026, num_agents=4, max_ticks=8, n_eras=2)
    assert "survival" in out and "life_score" in out
    assert len(out["survival"]) >= 4 * 2          # un âge PAR agent PAR ère (pas l'extinction-cohorte)
    assert all(s >= 0 for s in out["survival"])
    assert "censored_frac" in out


def test_run_condition_is_reproducible():
    cfg = WorldConfig()
    a = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    b = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    assert a["survival"] == b["survival"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_demand.py::test_run_condition_returns_individual_survival -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.s2_demand'`

- [ ] **Step 4: Write minimal implementation**

```python
# tools/s2_demand.py
"""
tools/s2_demand.py — Benchmark S2 : "Le monde EXIGE-t-il l'intelligence ?" (cause-racine B).
Champion HoF + 3 baselines (RandomAction, RandomGenome, Reflex) x 4 mondes, survie INDIVIDUELLE
censurée + life_score (cohérence), appariement seedé (Harness D1), verdict IUT+Holm 3 issues.
Pré-enregistrement : docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md.
"""
import numpy as np
from src.seed_ai.harness import seed_at
from src.seed_ai.persistence import calculate_life_score


def run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1):
    """K=n_eras ères seedées base+i d'UN monde sous UNE condition. batch_model_cls=None -> moteur
    normal (MambaBatchModel, pour champion/RandomGenome) ; sinon baseline injecté (RandomAction/Reflex).
    genome=None -> agents frais (RandomGenome) ; sinon clones du génome (champion). Renvoie la survie
    INDIVIDUELLE (âge de chaque agent, mort OU survivant-censuré) + life_score, agrégée sur les ères."""
    from src.agents.mamba_agent import MambaAgent
    survival, life, censored = [], [], 0
    for i in range(max(1, int(n_eras))):
        seed_at(seed, i)
        env = world_cls()
        env.benchmark_mode = True              # cohorte fixe (pas de reproduction/mutation/HGT)
        env.night_enabled = False              # nuit OFF (irrésoluble dans Soup)
        env.current_era = 10_000               # scaffolds OFF (anneal -> 0)
        if batch_model_cls is not None:
            env.batch_model_cls = batch_model_cls
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        survivors = list(env.agents)           # encore vivants à max_ticks -> CENSURÉS
        dead = list(getattr(env, "dead_agents", []))
        for a in survivors + dead:
            survival.append(int(a["age"]))
            life.append(float(calculate_life_score(a)))
        censored += len(survivors)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    n = max(1, len(survival))
    return {"survival": survival, "life_score": life, "censored_frac": censored / n}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_demand.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/s2_demand.py tests/sandbox/test_s2_demand.py
git commit -m "feat(s2): run_condition — survie individuelle censuree + life_score, seede (S2)"
```

---

### Task 12: Runner — provisioning champion + baselines par monde

**But :** charger le champion HoF (corriger le `except: pass` silencieux → erreur si HoF vide) et définir les 4 conditions par monde (champion, RandomAction, RandomGenome, Reflex naïf, Reflex prudent).

**Files:**
- Modify: `tools/s2_demand.py`
- Test: `tests/sandbox/test_s2_demand.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_demand.py
from tools.s2_demand import load_champion_genome, CONDITIONS


def test_conditions_cover_the_ladder():
    keys = set(CONDITIONS)
    assert {"champion", "random_action", "random_genome", "reflex_naive", "reflex_prudent"} <= keys


def test_load_champion_raises_on_empty_hof(monkeypatch):
    import tools.s2_demand as s2
    monkeypatch.setattr(s2, "load_hall_of_fame", lambda: (2, []))
    try:
        load_champion_genome()
        assert False, "doit lever si HoF vide"
    except RuntimeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_demand.py -k "conditions or champion" -v`
Expected: FAIL — `ImportError: cannot import name 'load_champion_genome'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/s2_demand.py (imports en tête)
from src.seed_ai.persistence import load_hall_of_fame
from src.agents.baseline_models import RandomActionBatchModel, ReflexBatchModel


def load_champion_genome():
    """Génome du #1 du HoF. Lève si le HoF est vide (pas de `except: pass` silencieux, blocker panel)."""
    _version, entries = load_hall_of_fame()
    if not entries:
        raise RuntimeError("HoF vide : impossible de lancer S2 sans champion. Évoluer d'abord (main_biosphere).")
    return entries[0].genome


# Les 5 conditions par monde. (batch_model_cls, genome_kind) :
#  - champion / random_genome -> moteur normal (None) ; genome fourni ou frais.
#  - random_action / reflex -> baseline injecté.
def _reflex_prudent(agents, world_model=None):
    return ReflexBatchModel(agents, world_model, prudent=True)


CONDITIONS = {
    "champion":        {"batch_model_cls": None,                    "fresh_genome": False},
    "random_genome":   {"batch_model_cls": None,                    "fresh_genome": True},
    "random_action":   {"batch_model_cls": RandomActionBatchModel,  "fresh_genome": True},
    "reflex_naive":    {"batch_model_cls": ReflexBatchModel,        "fresh_genome": True},
    "reflex_prudent":  {"batch_model_cls": _reflex_prudent,         "fresh_genome": True},
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_demand.py -k "conditions or champion" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/s2_demand.py tests/sandbox/test_s2_demand.py
git commit -m "feat(s2): provisioning champion (HoF, raise si vide) + 5 conditions (S2)"
```

---

### Task 13: Runner — pilote + power analysis → K

**But :** estimer `std` des différences appariées (champion − réflexe) sur ~5 seeds par monde, puis calculer le K requis (puissance 0.8) et le plancher à 12 (spec §9). Pas de K=3 deviné.

**Files:**
- Modify: `tools/s2_demand.py`
- Test: `tests/sandbox/test_s2_demand.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_demand.py
from tools.s2_demand import required_k


def test_required_k_floor_is_12():
    # effet énorme, variance faible -> K calculé petit, mais plancher = 12 (réf EDR 087)
    assert required_k(mean_diff=100.0, std_diff=5.0) == 12


def test_required_k_grows_with_noise():
    k_low = required_k(mean_diff=10.0, std_diff=5.0)
    k_high = required_k(mean_diff=10.0, std_diff=40.0)
    assert k_high > k_low >= 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_demand.py -k required_k -v`
Expected: FAIL — `ImportError: cannot import name 'required_k'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/s2_demand.py
import math

K_FLOOR = 12                 # plancher pré-enregistré (réf EDR 087), spec §9
Z_ALPHA = 1.96               # alpha=0.05 bilatéral
Z_POWER = 0.84               # puissance 0.80


def required_k(mean_diff, std_diff, floor=K_FLOOR):
    """K requis pour détecter un effet apparié (t apparié) à puissance 0.80, alpha 0.05.
    K = ((z_alpha + z_power) / d)^2, d = |mean_diff|/std_diff. Planché à K_FLOOR."""
    if mean_diff == 0.0 or std_diff <= 0.0:
        return floor
    d = abs(mean_diff) / std_diff
    k = math.ceil(((Z_ALPHA + Z_POWER) / d) ** 2)
    return max(floor, int(k))


def pilot_required_k(world_cls, champion_genome, seed, k_pilot=5):
    """Pilote : survie champion vs réflexe naïf sur k_pilot ères, -> K requis (par monde)."""
    champ = run_condition(world_cls, None, champion_genome, seed, n_eras=k_pilot)["survival"]
    refl = run_condition(world_cls, ReflexBatchModel, None, seed, n_eras=k_pilot)["survival"]
    m = min(len(champ), len(refl))
    diff = np.array(champ[:m], dtype=float) - np.array(refl[:m], dtype=float)
    return required_k(float(np.mean(diff)), float(np.std(diff) + 1e-9))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_demand.py -k required_k -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/s2_demand.py tests/sandbox/test_s2_demand.py
git commit -m "feat(s2): power analysis -> K (plancher 12) + pilote par monde (S2)"
```

---

### Task 14: Runner — grille complète + verdict + provenance + EDR 088

**But :** orchestrer les 4 mondes × 5 conditions, appliquer `s2_verdict` + Holm sur les 4 mondes, sauver avec provenance étendue (via `Harness`), imprimer la table et amorcer l'EDR 088.

**Files:**
- Modify: `tools/s2_demand.py`
- Test: `tests/sandbox/test_s2_demand.py`

- [ ] **Step 1: Write the failing test (run minimal, K=2, mondes réduits)**

```python
# Ajouter à tests/sandbox/test_s2_demand.py
from tools.s2_demand import run_s2


def test_run_s2_smoke_one_world(monkeypatch):
    # Smoke : 1 monde, K=2, peu d'agents/ticks -> structure du rapport correcte, sans crash.
    import tools.s2_demand as s2
    monkeypatch.setattr(s2, "load_champion_genome", lambda: __import__(
        "src.agents.mamba_agent", fromlist=["MambaAgent"]).MambaAgent().genome)
    rep = run_s2(worlds=["stoneage"], seed=2026, K=2, num_agents=3, max_ticks=6, with_db=False)
    assert "stoneage" in rep["worlds"]
    w = rep["worlds"]["stoneage"]
    assert "verdict" in w and "survival" in w
    assert rep["seed"] == 2026 and "commit" in rep
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_demand.py::test_run_s2_smoke_one_world -v`
Expected: FAIL — `ImportError: cannot import name 'run_s2'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/s2_demand.py
from src.seed_ai.harness import Harness, _git_short_commit
from src.seed_ai.s2_stats import s2_verdict, holm
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_0_soup import SoupWorld            # noms confirmés Task 11 Step 1
from src.worlds.world_2_agricultural import AgriculturalWorld
from src.worlds.world_3_industrial import IndustrialWorld

WORLDS = {"soup": SoupWorld, "stoneage": Biosphere3D,
          "agricultural": AgriculturalWorld, "industrial": IndustrialWorld}
BASELINE_KEYS = ("random_action", "random_genome", "reflex_naive", "reflex_prudent")


def _run_all_conditions(world_cls, champion_genome, seed, K, num_agents, max_ticks):
    """Toutes les conditions d'UN monde -> {cond: {survival, life_score, censored_frac}}."""
    out = {}
    for name, spec in CONDITIONS.items():
        genome = None if spec["fresh_genome"] else champion_genome
        out[name] = run_condition(world_cls, spec["batch_model_cls"], genome,
                                  seed, num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    return out


def run_s2(worlds=None, seed=2026, K=None, num_agents=20, max_ticks=400, with_db=False):
    """Grille S2 complète. K=None -> pilote par monde (power analysis). Renvoie le rapport + le sauve."""
    worlds = worlds or list(WORLDS)
    champion = load_champion_genome()
    report = {"seed": seed, "commit": _git_short_commit(), "K": {}, "worlds": {}}

    with Harness(seed=seed, name="s2_demand", with_db=with_db) as h:
        # Réflexe = MEILLEUR des 2 variantes (borne réflexe, spec §5) ; baselines = naïf/prudent fusionnés.
        for w in worlds:
            wcls = WORLDS[w]
            k_w = K if K is not None else pilot_required_k(wcls, champion, seed)
            report["K"][w] = k_w
            conds = _run_all_conditions(wcls, champion, seed, k_w, num_agents, max_ticks)

            # survie : réflexe = la variante à plus haute survie médiane (borne haute du réflexe)
            refl = max((conds["reflex_naive"], conds["reflex_prudent"]),
                       key=lambda c: np.median(c["survival"]) if c["survival"] else 0.0)
            surv_base = {"random_action": conds["random_action"]["survival"],
                         "random_genome": conds["random_genome"]["survival"],
                         "reflex": refl["survival"]}
            life_base = {"random_action": conds["random_action"]["life_score"],
                         "random_genome": conds["random_genome"]["life_score"],
                         "reflex": refl["life_score"]}
            # appariement : tronquer à la longueur commune (même K, même num_agents -> aligné)
            n = min(len(conds["champion"]["survival"]), *(len(v) for v in surv_base.values()))
            v = s2_verdict(conds["champion"]["survival"][:n],
                           {k: surv_base[k][:n] for k in surv_base},
                           conds["champion"]["life_score"][:n],
                           {k: life_base[k][:n] for k in life_base})
            v["censored_frac_champion"] = conds["champion"]["censored_frac"]
            report["worlds"][w] = v

        # FWER global : Holm sur les p_monde des mondes au verdict non-VOID
        decided = [w for w in worlds if report["worlds"][w].get("p_monde") is not None]
        if decided:
            adj = holm([report["worlds"][w]["p_monde"] for w in decided])
            for w, pa in zip(decided, adj):
                report["worlds"][w]["p_monde_holm"] = float(pa)

        h.save(report)

    _print_table(report)
    return report


def _print_table(report):
    print(f"\n=== S2 — Le monde exige-t-il l'intelligence ? (seed={report['seed']}, commit={report['commit']}) ===")
    for w, v in report["worlds"].items():
        if v["verdict"] == "VOID":
            print(f"  {w:12s} : VOID (cohérence life_score échouée, life_p={v['life_p']:.3f})")
            continue
        s = v["survival"][v["strongest_baseline"]]
        print(f"  {w:12s} : {v['verdict']:12s} | p_monde={v.get('p_monde_holm', v['p_monde']):.3f} "
              f"| vs {v['strongest_baseline']}: Cliff δ={s['cliff']:+.2f}, ratio[{s['ratio_lo']:.2f},{s['ratio_hi']:.2f}] "
              f"| censuré={v['censored_frac_champion']*100:.0f}%")
    print("  -> Rédiger EDR 088 à partir de ce verdict. Si censuré>5% quelque part : augmenter max_ticks.")


if __name__ == "__main__":
    import os
    run_s2(seed=int(os.getenv("EXPERIMENT_SEED", "2026")), with_db=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_demand.py::test_run_s2_smoke_one_world -v`
Expected: PASS (la structure du rapport est correcte ; si les classes de mondes diffèrent, corriger les imports d'après Task 11 Step 1)

- [ ] **Step 5: Suite complète + non-régression**

Run: `python -m pytest tests/sandbox/test_s2_stats.py tests/sandbox/test_baseline_models.py tests/sandbox/test_benchmark_mode.py tests/sandbox/test_s2_demand.py -q`
Expected: PASS (toute la suite S2)

- [ ] **Step 6: Pilote réel + addendum K (avant la grille de prod)**

Run: `python -c "from tools.s2_demand import run_s2; r = run_s2(worlds=['stoneage'], seed=2026, K=None, num_agents=20, max_ticks=400); print(r['K'])"`
Action : reporter le K calculé + la marge d'équivalence observée dans un **addendum daté** du spec (`docs/superpowers/specs/2026-06-14-S2-...-design.md`, §9/§10), vérifier `censored_frac < 0.05` (sinon augmenter `max_ticks`), PUIS lancer la grille complète.

- [ ] **Step 7: Commit**

```bash
git add tools/s2_demand.py tests/sandbox/test_s2_demand.py
git commit -m "feat(s2): grille 4 mondes x 5 conditions + verdict IUT+Holm + provenance (S2)"
```

- [ ] **Step 8: Documenter (roadmap + EDR 088)**

Mettre à jour `roadmap.md` (S2 : levier #2 → en cours/livré) et rédiger `docs/EDR/088_*.md` à partir du verdict. Commit `docs(s2): EDR 088 + roadmap (verdict S2)`.

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §3 métrique survie individuelle censurée → Task 11 (`run_condition` lit `a["age"]`, marque survivants censurés). ✓
- §4 mode benchmark déparasité → Task 7 (`benchmark_mode`) + Task 11 (scaffolds via `current_era`, nuit via `night_enabled`). ✓
- §5 baselines (3 + 2 variantes réflexe) → Tasks 8/9/10 + Task 12 (CONDITIONS) + Task 14 (réflexe = max des 2 variantes). ✓
- §6 champion HoF + cohérence life_score → Task 12 (`load_champion_genome`) + Task 5 (`s2_verdict` VOID si cohérence échoue). ✓
- §7 4 mondes contrôles → Task 14 (`WORLDS`). ✓
- §8 stats (Wilcoxon apparié, Cliff+IC, ratio+IC, IUT, Holm-4) → Tasks 1-5 + Task 14 (Holm sur 4 mondes). ✓
- §9 K par power analysis (plancher 12) → Task 13. ✓
- §10 table 3 issues + VOID → Task 5. ✓
- §11 seam + surprise=0 → Task 6 + Task 8 (`BaselineBatchModel.forward`). ✓
- §13 provenance (seed+commit) → Task 14 (`Harness.save` + report). ✓
- §14 erreurs (HoF vide raise, smoke 1-seed) → Task 12 + Task 14 Step 1/4. ✓

**2. Placeholder scan :** `<HGT_LINE>` (Task 7) et `<APEX_IDX>` (Task 10) sont des **valeurs à confirmer par grep** avec une étape de localisation explicite + test de comportement qui les pin — pas des placeholders de code (choix honnête : ces indices internes sont lus à l'exécution, le test échoue si faux). Les noms de classes de mondes (Task 11 Step 1) idem. Aucun « TODO/à compléter » dans le code à écrire.

**3. Type consistency :** `run_condition(world_cls, batch_model_cls, genome, seed, num_agents, max_ticks, n_eras) -> {survival, life_score, censored_frac}` cohérent Tasks 11→14. `BaselineBatchModel(agents, world_model=None)` / `.forward(batch_obs, env_surprise_batch=None) -> (logits, compute_spent)` cohérent Tasks 8→11 et avec `world_1:952`. `s2_verdict(surv_champ, surv_baselines:dict, life_champ, life_baselines:dict)` cohérent Task 5↔14. `cliffs_delta/median_ratio/wilcoxon_signed_rank/bootstrap_ci/holm/iut_pvalue` signatures stables Tasks 1-5. `batch_model_cls` / `benchmark_mode` attributs cohérents Tasks 6/7↔11.
