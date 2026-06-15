# EDR 088 — Lewis Critical Content : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le tool de sweep dose-réponse `tools/lewis_critical.py` (+ son module stats `src/seed_ai/exp_stats.py`) qui teste si le CONTENU référentiel paye quand la fraction de Leurres-pièges croît, selon le pré-enregistrement EDR 088.

**Architecture:** Module stats numpy-pur (Wilcoxon apparié, Jonckheere-Terpstra, bootstrap, OLS) testé d'abord ; puis `_setup_critical` (compose les apex au ratio voulu) + un moteur 3-bras apparié (copié/adapté de `relang_sweet.py` pour la métrique nette, **sans toucher l'artefact 087**) + `Harness` D1 (provenance) ; enfin pilote → power → grille.

**Tech Stack:** Python 3.13, numpy (stats pur, `math.erfc` pour la loi normale), `src/seed_ai/harness.py` (D1), biosphère `world_1_stoneage`, `referential_head`. **Pas de scipy** (non déclaré ; le projet l'évite). scipy n'est utilisé que comme *oracle de validation* dans les tests, via `pytest.importorskip`.

**Spec / pré-enregistrement:** `docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md`

---

## File Structure

- **Create** `src/seed_ai/exp_stats.py` — stats appariées/tendance, numpy pur. Une responsabilité : tests statistiques pré-enregistrés.
- **Create** `tests/sandbox/test_exp_stats.py` — tests unitaires (cas textbook + cross-check scipy `importorskip`).
- **Create** `tools/lewis_critical.py` — `_setup_critical`, `_run_era` (métrique nette), `evolve`, `main` (sweep), `Harness`.
- **Create** `tests/sandbox/test_lewis_critical.py` — test de composition d'apex + repro.
- **Append (addendum)** au spec : K final post-pilote (daté).
- **Create** `docs/EDR/088_*.md` — rédigé après le run (verdict).

Convention : tests dans `tests/sandbox/`, lancés par `python -m pytest`. Worktree isolé `worktree-edr088-lewis-critical` (base main). Commits **path-scoped** (`git commit -m msg -- <fichiers>`, index partagé par 4 sessions).

---

### Task 1 : `exp_stats` — Wilcoxon signed-rank apparié + paired_summary

**Files:**
- Create: `src/seed_ai/exp_stats.py`
- Test: `tests/sandbox/test_exp_stats.py`

- [ ] **Step 1 : test qui échoue**

```python
# tests/sandbox/test_exp_stats.py
import numpy as np
import pytest
from src.seed_ai import exp_stats as st


def test_wilcoxon_all_positive_is_significant():
    # 10 diffs toutes positives -> très significatif, p petit
    r = st.wilcoxon_signed_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert r["n"] == 10
    assert r["p"] < 0.01
    assert r["stat"] == 0.0  # W = min(W+, W-) = W- = 0


def test_wilcoxon_symmetric_is_not_significant():
    r = st.wilcoxon_signed_rank([1, -1, 2, -2, 3, -3, 4, -4])
    assert r["p"] > 0.5


def test_wilcoxon_drops_zeros():
    r = st.wilcoxon_signed_rank([0, 0, 1, 2, 3])
    assert r["n"] == 3


def test_wilcoxon_matches_scipy():
    scipy_stats = pytest.importorskip("scipy.stats")
    d = [0.5, -1.2, 2.3, 1.1, -0.4, 3.0, 0.9, -0.2, 1.5, 2.2, -1.0, 0.7]
    mine = st.wilcoxon_signed_rank(d)
    ref = scipy_stats.wilcoxon(d, correction=True, mode="approx")
    assert abs(mine["stat"] - float(ref.statistic)) < 1e-9
    assert abs(mine["p"] - float(ref.pvalue)) < 0.02   # approx normale ~ scipy approx


def test_paired_summary_fields():
    s = st.paired_summary([1.0, 2.0, -0.5, 3.0])
    assert set(s) >= {"mean", "se", "win_rate", "wilcoxon_p", "n"}
    assert s["n"] == 4
    assert 0.0 <= s["win_rate"] <= 1.0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -k "wilcoxon or paired" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.seed_ai.exp_stats'`

- [ ] **Step 3 : implémentation**

```python
# src/seed_ai/exp_stats.py
"""
src/seed_ai/exp_stats.py — Tests statistiques pré-enregistrés (EDR 088), numpy PUR (pas de scipy).

Appariés (Wilcoxon signed-rank), tendance ordonnée (Jonckheere-Terpstra), bootstrap IC, OLS.
Loi normale via math.erfc (stdlib). Validé contre scipy dans les tests (oracle), mais sans
dépendance scipy à l'exécution.
"""
import math
import numpy as np


def _norm_sf(x):
    """Survie de la loi normale standard : P(Z > x)."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def _average_ranks(a):
    """Rangs 1..n avec moyenne des rangs sur les ex-aequo."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    sa = a[order]
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j < len(a) and sa[j] == sa[i]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0   # moyenne des rangs (1-based) i+1..j
        i = j
    return ranks


def wilcoxon_signed_rank(d):
    """Wilcoxon signed-rank apparié (vs 0), approx normale + correction de continuité.
    Zéros écartés ; ex-aequo en rangs moyens + correction de variance. -> {stat, z, p, n}."""
    d = np.asarray(d, dtype=float)
    d = d[d != 0.0]
    n = len(d)
    if n == 0:
        return {"stat": 0.0, "z": 0.0, "p": 1.0, "n": 0}
    absd = np.abs(d)
    ranks = _average_ranks(absd)
    w_plus = float(ranks[d > 0].sum())
    w_minus = float(ranks[d < 0].sum())
    w = min(w_plus, w_minus)
    mean_w = n * (n + 1) / 4.0
    _, counts = np.unique(absd, return_counts=True)
    tie = float(((counts ** 3) - counts).sum())
    var_w = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    if var_w <= 0:
        return {"stat": w, "z": 0.0, "p": 1.0, "n": n}
    cc = 0.5 * np.sign(mean_w - w)          # continuité vers la moyenne
    z = (w - mean_w + cc) / math.sqrt(var_w)
    p = min(1.0, 2.0 * _norm_sf(abs(z)))    # bilatéral
    return {"stat": w, "z": float(z), "p": float(p), "n": n}


def paired_summary(d):
    """Résumé d'une diff appariée : moyenne, SE, win-rate (P(d>0)), p de Wilcoxon."""
    a = np.asarray(d, dtype=float)
    se = a.std(ddof=1) / math.sqrt(len(a)) if len(a) > 1 else float("inf")
    return {
        "mean": float(a.mean()),
        "se": float(se),
        "win_rate": float(np.mean(a > 0)),
        "wilcoxon_p": wilcoxon_signed_rank(a)["p"],
        "n": int(len(a)),
    }
```

- [ ] **Step 4 : lancer, vérifier le passage**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -k "wilcoxon or paired" -v`
Expected: PASS (5 tests ; `test_wilcoxon_matches_scipy` passe car scipy installé localement)

- [ ] **Step 5 : commit**

```bash
git add src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
git commit -m "feat(exp_stats): Wilcoxon signed-rank apparie + paired_summary (numpy pur, EDR088)" -- src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
```

---

### Task 2 : `exp_stats` — Jonckheere-Terpstra (test de tendance)

**Files:**
- Modify: `src/seed_ai/exp_stats.py`
- Test: `tests/sandbox/test_exp_stats.py`

- [ ] **Step 1 : test qui échoue (APPEND)**

```python
def test_jt_increasing_trend_significant():
    groups = [[1, 2, 1.5], [3, 4, 3.5], [5, 6, 5.5], [7, 8, 7.5]]  # médianes croissantes
    r = st.jonckheere_terpstra(groups)
    assert r["z"] > 0
    assert r["p_one_sided"] < 0.01


def test_jt_flat_not_significant():
    groups = [[2, 3, 4], [2, 3, 4], [2, 3, 4], [2, 3, 4]]
    r = st.jonckheere_terpstra(groups)
    assert r["p_one_sided"] > 0.3


def test_jt_decreasing_negative_z():
    groups = [[7, 8], [5, 6], [3, 4], [1, 2]]
    r = st.jonckheere_terpstra(groups)
    assert r["z"] < 0
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -k jt -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'jonckheere_terpstra'`

- [ ] **Step 3 : implémentation (APPEND à exp_stats.py)**

```python
def jonckheere_terpstra(groups):
    """Test de tendance ordonnée de Jonckheere-Terpstra (groupes pré-ordonnés).
    H1 (one-sided) : les médianes croissent avec l'ordre des groupes.
    Stat J = somme sur i<j de #{(x in g_i, y in g_j) : y>x} (+0.5 par ex-aequo).
    Approx normale (sans correction d'ex-aequo — noté). -> {stat, z, p_one_sided, p_two_sided}."""
    gs = [np.asarray(g, dtype=float) for g in groups]
    k = len(gs)
    J = 0.0
    for i in range(k):
        for j in range(i + 1, k):
            for x in gs[i]:
                J += float(np.sum(gs[j] > x) + 0.5 * np.sum(gs[j] == x))
    N = sum(len(g) for g in gs)
    sum_ni2 = sum(len(g) ** 2 for g in gs)
    mean_J = (N ** 2 - sum_ni2) / 4.0
    var_J = (N ** 2 * (2 * N + 3) - sum(len(g) ** 2 * (2 * len(g) + 3) for g in gs)) / 72.0
    z = (J - mean_J) / math.sqrt(var_J) if var_J > 0 else 0.0
    return {
        "stat": float(J),
        "z": float(z),
        "p_one_sided": float(_norm_sf(z)),
        "p_two_sided": float(min(1.0, 2.0 * _norm_sf(abs(z)))),
    }
```

- [ ] **Step 4 : passage**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -k jt -v`
Expected: PASS (3 tests)

- [ ] **Step 5 : commit**

```bash
git add src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
git commit -m "feat(exp_stats): Jonckheere-Terpstra (test de tendance dose-reponse, EDR088)" -- src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
```

---

### Task 3 : `exp_stats` — bootstrap_ci + ols_slope

**Files:**
- Modify: `src/seed_ai/exp_stats.py`
- Test: `tests/sandbox/test_exp_stats.py`

- [ ] **Step 1 : test qui échoue (APPEND)**

```python
def test_bootstrap_ci_brackets_mean():
    data = list(range(1, 21))  # 1..20, moyenne 10.5
    lo, hi = st.bootstrap_ci(data, np.mean, n_boot=2000, alpha=0.05, seed=0)
    assert lo < 10.5 < hi
    assert hi - lo < 6.0


def test_bootstrap_ci_reproducible():
    data = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
    a = st.bootstrap_ci(data, np.mean, n_boot=1000, alpha=0.05, seed=42)
    b = st.bootstrap_ci(data, np.mean, n_boot=1000, alpha=0.05, seed=42)
    assert a == b


def test_ols_slope_positive():
    x = [0.33, 0.50, 0.67, 0.83]
    y = [0.1, 1.0, 2.1, 3.0]   # croissant
    s = st.ols_slope(x, y)
    assert s > 0
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -k "bootstrap or ols" -v`
Expected: FAIL — `AttributeError: ... 'bootstrap_ci'`

- [ ] **Step 3 : implémentation (APPEND)**

```python
def bootstrap_ci(data, statistic_fn, n_boot=2000, alpha=0.05, seed=0):
    """IC percentile bootstrap (ré-échantillonnage avec remise). Seedé -> reproductible."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    rng = np.random.default_rng(int(seed))
    stats = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        stats[b] = statistic_fn(data[rng.integers(0, n, n)])
    lo = float(np.percentile(stats, 100 * alpha / 2.0))
    hi = float(np.percentile(stats, 100 * (1.0 - alpha / 2.0)))
    return lo, hi


def ols_slope(x, y):
    """Pente OLS (moindres carrés) de y sur x."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.polyfit(x, y, 1)[0])
```

- [ ] **Step 4 : passage**

Run: `python -m pytest tests/sandbox/test_exp_stats.py -v`
Expected: PASS (tous : 11 tests)

- [ ] **Step 5 : commit**

```bash
git add src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
git commit -m "feat(exp_stats): bootstrap_ci + ols_slope (EDR088) -- module stats complet+teste" -- src/seed_ai/exp_stats.py tests/sandbox/test_exp_stats.py
```

---

### Task 4 : `lewis_critical._setup_critical` — composition d'apex au ratio voulu

**Files:**
- Create: `tools/lewis_critical.py`
- Test: `tests/sandbox/test_lewis_critical.py`

**Contexte** : `relang_sweet._setup_balanced` (lu) configure le monde langage (nuit OFF, ajoute Leurre/Ours, spawn 3× chaque) via `env.config.preys[...]` + `env._spawn_prey_instance(ref)`. On veut une version paramétrée par `leurre_frac` qui fixe le total d'apex et le ratio.

- [ ] **Step 1 : test qui échoue**

```python
# tests/sandbox/test_lewis_critical.py
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from tools import lewis_critical as lc


def _apex_counts(env):
    by = {"Mammouth": 0, "Ours": 0, "Leurre": 0}
    for p in env.preys:
        t = p.get("type") if isinstance(p, dict) else getattr(p, "type", None)
        if t in by:
            by[t] += 1
    return by


def test_setup_critical_leurre_fraction():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    lc._setup_critical(env, leurre_frac=0.5, n_apex=12)
    c = _apex_counts(env)
    assert c["Leurre"] == 6                       # 0.5 * 12
    assert c["Mammouth"] + c["Ours"] == 6         # le reste = positifs
    assert env.night_enabled is False             # hérité du correctif 086


def test_setup_critical_high_fraction():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    lc._setup_critical(env, leurre_frac=0.83, n_apex=12)
    c = _apex_counts(env)
    assert c["Leurre"] == 10                       # round(0.83*12)=10
    assert c["Mammouth"] + c["Ours"] == 2
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_lewis_critical.py -k setup -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.lewis_critical'`
(NB : vérifie d'abord la clé `type` exposée par `env.preys` ; si la structure diffère, adapte `_apex_counts` ET le spawn — lire `world_1:285 _spawn_prey_instance` et la forme de `env.preys`.)

- [ ] **Step 3 : implémentation**

```python
# tools/lewis_critical.py
"""tools/lewis_critical.py — EDR 088 : le CONTENU paye-t-il quand la distinction devient décisive ?

Sweep dose-réponse de la fraction de Leurres-pièges (le levier explicite d'EDR 087). Réutilise les
briques feuilles de relang_sweet/referential_head MAIS écrit son propre moteur 3-bras (métrique NETTE
kills-leurre_hits) pour NE PAS altérer l'artefact 087. Pré-enregistrement :
docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md
"""
import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions

METAB, PAYOFF = 0.25, 3.0          # sweet spot (EDR 085)
LEURRE_FRACS = (0.33, 0.50, 0.67, 0.83)
N_APEX = 12


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _setup_critical(env, leurre_frac, n_apex=N_APEX):
    """Monde de Lewis à criticalité réglable : n_apex apex au total, dont round(leurre_frac*n_apex)
    Leurres-pièges ; le reste réparti Mammouth/Ours (positifs). Nuit OFF (correctif audit 086)."""
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.night_enabled = False
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    env.config.preys["Ours"] = PreyConfig(hp=60.0, damage=30.0, moves_per_tick=0.3)
    n_leurre = int(round(leurre_frac * n_apex))
    n_pos = n_apex - n_leurre
    positifs = [("Mammouth" if i % 2 == 0 else "Ours") for i in range(n_pos)]  # alterne les 2 food
    for ref in positifs:
        env._spawn_prey_instance(ref)
    for _ in range(n_leurre):
        env._spawn_prey_instance("Leurre")
```

- [ ] **Step 4 : passage**

Run: `python -m pytest tests/sandbox/test_lewis_critical.py -k setup -v`
Expected: PASS (2 tests). Si la forme de `env.preys` diffère, ajuster `_apex_counts`/le spawn (lire `world_1` d'abord) — NE PAS truquer l'assert.

- [ ] **Step 5 : commit**

```bash
git add tools/lewis_critical.py tests/sandbox/test_lewis_critical.py
git commit -m "feat(lewis_critical): _setup_critical -- composition d'apex au ratio Leurre voulu (EDR088)" -- tools/lewis_critical.py tests/sandbox/test_lewis_critical.py
```

---

### Task 5 : `lewis_critical` — moteur 3-bras (métrique nette) + sweep `main` + Harness

**Files:**
- Modify: `tools/lewis_critical.py`
- Test: `tests/sandbox/test_lewis_critical.py`

- [ ] **Step 1 : test qui échoue (APPEND) — reproductibilité du run d'un bras**

```python
def test_run_arm_reproducible():
    cfg = lc._sweet_cfg()
    g = lc._load_champions()[0]
    a = lc._run_arm(cfg, [g] * 4, 0.5, use_head=False, decode_act=False, scramble=False,
                    heads=None, world_seed=3, max_ticks=25)
    b = lc._run_arm(cfg, [g] * 4, 0.5, use_head=False, decode_act=False, scramble=False,
                    heads=None, world_seed=3, max_ticks=25)
    assert a["net"] == b["net"] and a["kills"] == b["kills"] and a["leurre_hits"] == b["leurre_hits"]
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_lewis_critical.py -k run_arm -v`
Expected: FAIL — `AttributeError: ... '_run_arm'`

- [ ] **Step 3 : implémentation (APPEND à lewis_critical.py)**

```python
def _run_arm(cfg, genomes, leurre_frac, use_head, decode_act, scramble, heads,
             world_seed, max_ticks=300):
    """Un bras apparié : seed la frontière (monde identique entre bras du même world_seed), construit
    le monde critique, ajoute les agents (têtes optionnelles), simule, renvoie la métrique NETTE."""
    seed_at(world_seed, 0)                       # APPARIEMENT (D1) : même monde entre bras
    env = Biosphere3D(cfg)
    _setup_critical(env, leurre_frac)
    env.use_ref_head = use_head
    env.decode_act = decode_act
    env.scramble_signal = scramble
    env.decode_act_fires = 0
    for k, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        if heads is not None:
            a.ref_head = heads[k]
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    kills = int(sum(ag.get("mammoth_kills", 0) for ag in pool))
    hits = int(getattr(env, "leurre_hits", 0))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return {"net": kills - hits, "kills": kills, "leurre_hits": hits, "ticks": t,
            "fires": int(getattr(env, "decode_act_fires", 0))}


def _evolve(cfg, mc, gens, num_agents, prog):
    """Évolue des champions dans le monde critique médian (0.5) pour un substrat compétent commun."""
    best = [(0.0, g) for g in _load_champions()]
    for gi in range(gens):
        seed_at(7000 + gi, 0)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        r = _run_arm(cfg, genomes, 0.5, False, False, False, None, world_seed=gi, max_ticks=300)
        pool_scores = r  # _run_arm ne renvoie pas les génomes ; on garde best courant + mutate
        best = sorted(best, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return [g for _s, g in best]


def main(gens=8, num_agents=24, K=12, seeds=range(12), levels=LEURRE_FRACS, max_ticks=300, seed=None):
    with Harness(seed=seed, name="lewis_critical", with_db=False) as h:
        base = h.seed
        cfg = _sweet_cfg()
        mc = MutationConfig(weight_init_std=2.0)
        seeds = list(seeds)
        champions = _load_champions()           # substrat HoF (cohérent avec 087 ; pas de ré-évolution)
        print(f"EDR088 sweep criticalite : seed={base}, niveaux={levels}, {len(seeds)} seeds apparies.")

        table = {}                              # niveau -> {dc:[...], fia:[...], scr:[...], solo:[...], fires:[...]}
        prog = h.progress(len(levels) * len(seeds) * 3, label="sweep FIABLE/BROUILLE/SOLO")
        for lf in levels:
            dc, fia, scr, solo, fires, hitsF, hitsS = [], [], [], [], [], [], []
            for s in seeds:
                ws = base + int(round(lf * 1000)) * 100 + s    # frontière disjointe par (niveau, seed)
                seed_at(ws, 0)
                genomes = _reproduce(champions, num_agents, mc)
                rng = np.random.RandomState(s)
                heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
                train_population(heads, steps=5000, seed=s)
                rf = _run_arm(cfg, genomes, lf, True, True, False, heads, ws, max_ticks); prog.update()
                rs = _run_arm(cfg, genomes, lf, True, True, True, heads, ws, max_ticks); prog.update()
                ro = _run_arm(cfg, genomes, lf, True, False, False, heads, ws, max_ticks); prog.update()
                dc.append(rf["net"] - rs["net"])               # CONTENU : FIABLE - BROUILLE (net)
                fia.append(rf["net"]); scr.append(rs["net"]); solo.append(ro["net"])
                fires.append(rf["fires"]); hitsF.append(rf["leurre_hits"]); hitsS.append(rs["leurre_hits"])
            table[lf] = {"dc": dc, "fia": fia, "scr": scr, "solo": solo, "fires": fires,
                         "summary": st.paired_summary(dc)}
            sm = table[lf]["summary"]
            print(f"  Leurre={lf:.2f} : FIABLE-BROUILLE(net) = {sm['mean']:+.2f} +/- {sm['se']:.2f} SE "
                  f"(win {sm['win_rate']*100:.0f}%, Wilcoxon p={sm['wilcoxon_p']:.3f}, fires~{np.mean(fires):.0f})")

        # Test de tendance (le verdict primaire)
        groups = [table[lf]["dc"] for lf in levels]
        jt = st.jonckheere_terpstra(groups)
        slope = st.ols_slope([lf for lf in levels for _ in table[lf]["dc"]],
                             [d for lf in levels for d in table[lf]["dc"]])
        print(f"\n=== TENDANCE (le contenu paye-t-il PLUS quand la distinction devient critique ?) ===")
        print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f} ; pente OLS={slope:+.3f}")
        hi = table[levels[-1]]["summary"]
        print("=== VERDICT (pre-enregistre) ===")
        if jt["p_one_sided"] < 0.05 and hi["mean"] > 0 and hi["wilcoxon_p"] < 0.05:
            print(f"  -> ARC 4 CLOS : le CONTENU paye quand la distinction est decisive (tendance +, "
                  f"FIABLE-BROUILLE={hi['mean']:+.1f} a {levels[-1]:.2f} pieges, p={hi['wilcoxon_p']:.3f}).")
        elif jt["p_one_sided"] >= 0.05 and abs(hi["mean"]) < hi["se"]:
            print(f"  -> NEGATIF PROFOND : pas de tendance, FIABLE~BROUILLE meme a {levels[-1]:.2f} pieges. "
                  f"Les agents n'exploitent pas le contenu meme decisif.")
        else:
            print(f"  -> PARTIEL/GATE : tendance/effet sous-puissant ou niveaux VOID. Reporter + re-regler.")
        h.save({"levels": list(levels), "seeds": seeds, "jt": jt, "slope": slope,
                "table": {f"{lf:.2f}": {k: v for k, v in table[lf].items() if k != "dc"} | {"dc": table[lf]["dc"]}
                          for lf in levels}})


if __name__ == "__main__":
    main()
```

> NOTE D'IMPLÉMENTATION (à résoudre par l'implémenteur) : `_evolve` ci-dessus est un **stub** —
> `_run_arm` ne renvoie pas les génomes scorés (contrairement à `relang_sweet._run_era` mode non-measure).
> Choix le plus simple, retenu : **réutiliser directement les champions HoF** (`_load_champions`) comme
> substrat (cohérent avec le pré-enregistrement §6 qui s'aligne sur 087 « HoF réutilisé »), et **supprimer
> `_evolve`** de `main` (déjà fait : `main` utilise `champions = _load_champions()`). Retirer le stub
> `_evolve` ou le compléter seulement si une ré-évolution dans le monde critique est jugée nécessaire
> (hors périmètre pré-enregistré). Garder le code minimal.

- [ ] **Step 4 : passage du test de repro**

Run: `python -m pytest tests/sandbox/test_lewis_critical.py -k run_arm -v`
Expected: PASS

- [ ] **Step 5 : SMOKE de bout en bout (court, vérifie repro du verdict)**

```bash
python -c "from tools.lewis_critical import main; main(num_agents=6, K=2, seeds=range(2), levels=(0.33,0.83), max_ticks=25, seed=1)"
```
Expected : s'exécute sans crash, imprime une ligne par niveau + la tendance + un verdict ; écrit `results/lewis_critical_1.json`. Relancer avec `seed=1` → **mêmes** nombres (appariement/repro). Si non-déterministe, DONE_WITH_CONCERNS + diagnostic (source d'aléa hors `np.random`).

- [ ] **Step 6 : commit**

```bash
git add tools/lewis_critical.py tests/sandbox/test_lewis_critical.py
git commit -m "feat(lewis_critical): moteur 3-bras net + sweep main + Harness/provenance (EDR088)" -- tools/lewis_critical.py tests/sandbox/test_lewis_critical.py
```

---

### Task 6 : PILOTE → power analysis → K (addendum daté)

**But** : estimer `std(d_s)` par niveau (K≈5) pour figer le K final (puissance ≥ 0.8), comme le pré-enregistrement l'exige (§5). **Pas de TDD** — exécution + analyse.

- [ ] **Step 1 : lancer le pilote** (K=5, niveaux complets, seeds réduits)

```bash
HEADLESS=1 python -c "from tools.lewis_critical import main; main(num_agents=24, seeds=range(5), seed=88)"
```
(Surveiller le wall-time ; si > ~20 min, réduire `max_ticks`/`num_agents` et noter.)

- [ ] **Step 2 : calculer le K requis par niveau**

Lire `results/lewis_critical_88.json` → pour chaque niveau, `sd = std(dc, ddof=1)`. Effet visé = pré-enregistré
(prendre l'effet observé au niveau haut comme proxy, OU une cible Cohen d=0.8). K requis (test apparié,
puissance 0.8, α=0.05 bilatéral) ≈ `((1.96 + 0.84) * sd / effet)^2`. Prendre `K = max` sur les 4 niveaux,
**plancher 12**.

```python
import json, numpy as np
d = json.load(open("results/lewis_critical_88.json"))["data"]
for lf, t in d["table"].items():
    sd = np.std(t["dc"], ddof=1)
    print(lf, "sd=", round(sd,2), "mean=", round(np.mean(t["dc"]),2))
```

- [ ] **Step 3 : écrire l'addendum daté dans le spec**

Ajouter à la fin de `docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md` :
```markdown
## Addendum post-pilote (2026-06-15) — K figé
Pilote K=5 (seed 88). std(d_s) par niveau : 0.33→<x>, 0.50→<x>, 0.67→<x>, 0.83→<x>.
K requis (puissance 0.8, effet <e>) = <K> ; **K final figé = max(<K>, 12) = <K_final>** seeds.
```

- [ ] **Step 4 : commit (path-scoped)**

```bash
git add docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md
git commit -m "docs(EDR088): addendum post-pilote -- K fige par power analysis" -- docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md
```

---

### Task 7 : GRILLE COMPLÈTE → résultats + EDR 088

**But** : run final au K figé → verdict pré-enregistré → EDR 088. Exécution + rédaction.

- [ ] **Step 1 : run final** (K_final seeds, niveaux complets)

```bash
HEADLESS=1 python -c "from tools.lewis_critical import main; main(num_agents=24, seeds=range(<K_final>), seed=2026)"
```
(Multiprocess si dispo / cap wall-time. Vérifier les **gates** par niveau : si `fires<5` ou survie indicative basse → niveau VOID, noté.)

- [ ] **Step 2 : repro**

Relancer `seed=2026` → table identique (provenance D1). Confirmer.

- [ ] **Step 3 : rédiger `docs/EDR/088_*.md`**

Selon l'issue (§6 du spec) : table niveau×bras (net, kills, leurre_hits, fires), FIABLE−BROUILLÉ ± SE +
Wilcoxon p par niveau, Jonckheere-Terpstra (verdict tendance), pente OLS + IC bootstrap, **le verdict**
(1 des 3 issues), honnêteté (gates, limites d'appariement), variables d'expérience. Pointer le JSON.

- [ ] **Step 4 : commit (path-scoped)**

```bash
git add "docs/EDR/088_Language_Content_Pays_When_Distinction_Is_Critical.md"
git commit -m "EDR 088 : <verdict en une ligne> (sweep criticalite, pre-enregistre)" -- "docs/EDR/088_Language_Content_Pays_When_Distinction_Is_Critical.md"
```

---

## Self-Review

- **Spec coverage** : §1 hypothèse → Task 7 verdict ; §2 sweep/manipulation → Task 4 `_setup_critical` (niveaux, N_APEX fixe) ; §3 bras/net → Task 5 `_run_arm` (net=kills−hits, 3 bras appariés via `seed_at`) ; §4 stats (Wilcoxon, JT, bootstrap, OLS) → Tasks 1-3 ; §5 K/power/gates → Task 6 ; §6 table de décision → Task 5 `main` (verdict pré-enregistré) ; §7 archi (tool neuf, sans toucher 087/world_1, Harness) → Tasks 4-5 ; §8 compute → Tasks 6-7 ; §9 provenance/EDR → Tasks 6-7. **Couvert.**
- **Placeholders** : le `<x>/<K>/<verdict>` des Tasks 6-7 sont des **valeurs de run** (inconnues avant exécution, par nature) — pas des placeholders de code. `_evolve` est explicitement signalé comme stub à retirer (note d'implémentation), `main` ne l'utilise pas.
- **Cohérence des types** : `_run_arm(cfg, genomes, leurre_frac, use_head, decode_act, scramble, heads, world_seed, max_ticks) -> {net,kills,leurre_hits,ticks,fires}` cohérent Task 5↔tests ; `_setup_critical(env, leurre_frac, n_apex)` cohérent Task 4↔5 ; `st.wilcoxon_signed_rank/jonckheere_terpstra/bootstrap_ci/ols_slope/paired_summary` cohérents Tasks 1-3↔5.
- **Risque connu** : la forme exacte de `env.preys` (dict vs objet) + l'API `_spawn_prey_instance` — Task 4 step 2/4 demande de **vérifier dans `world_1` avant d'asserter** (ne pas truquer). Le `train_population(steps=5000)` rend le smoke non-instantané (~secondes/bras) — params réduits au smoke.
