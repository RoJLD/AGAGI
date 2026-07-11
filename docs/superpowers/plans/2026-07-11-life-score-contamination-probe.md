# Probe d'impact de contamination `life_score` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer un probe qui mesure si les termes morts/inertes de `calculate_life_score` (`altars_solved·20`, `spears_crafted·300`) changent réellement le classement top-K de la sélection, sur une cohorte évoluée réaliste — sans jamais muter le cœur de sélection partagé.

**Architecture:** Un tool additif `tools/life_score_contamination_probe.py` structuré en 3 couches pures testables (métriques → variantes de poids → agrégation/verdict) + une couche harness qui réutilise l'évolution canonique de `competence_profile.py`. Un test sandbox par couche.

**Tech Stack:** Python, numpy, biosphère AGAGI (`Biosphere3D`, `MambaAgent`), réutilisation `tools.competence_profile._evolve_champions` + `tools.map_elites_compare.{_make_cfg,_reproduce,PRESERVE_DIMS}`. Zéro dépendance externe (Kendall tau manuel, pas de scipy).

## Global Constraints

- **Zéro modification `src/`** — additif pur. Seuls fichiers touchés : `tools/life_score_contamination_probe.py` (créer) et `tests/sandbox/test_life_score_contamination_probe.py` (créer).
- **Ne PAS muter `calculate_life_score`** ni aucun poids en prod. Les variantes sont des copies locales de dict.
- **Ne PAS semer** de spears/autels — taux naturels only.
- **Aucun verdict `METRIQUE_CONTAMINEE` sous K=12 seeds** (garde-fou anti-évaporation).
- **Régime = `_make_cfg()`** canonique (sweet 0.25/3.0), pas de knob de régime.
- **stdout cp1252-safe** dans `__main__` : `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
- **Tokens de verdict ASCII** : `METRIQUE_INERTE` / `METRIQUE_CONTAMINEE` / `AMBIGU` (pas d'accent dans les valeurs sérialisées).
- **Commits path-scopés** (`git add` explicite des 2 fichiers seulement) — tree partagé par des sessions //.

---

### Task 1: Couche métriques pures

**Files:**
- Create: `tools/life_score_contamination_probe.py`
- Test: `tests/sandbox/test_life_score_contamination_probe.py`

**Interfaces:**
- Produces: `score(components, weights) -> float`, `kendall_tau(a, b) -> float`, `_topk_indices(scores, k) -> set`, `topk_jaccard(scores_full, scores_var, k) -> float`, `term_mass_share(roster, weights) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_life_score_contamination_probe.py
import math
from tools.life_score_contamination_probe import (
    score, kendall_tau, _topk_indices, topk_jaccard, term_mass_share,
)

W = {"age": 0.1, "preys_eaten": 50.0, "altars_solved": 20.0,
     "spears_crafted": 300.0, "mammoth_kills": 400.0, "ref_distinction": 0.0}


def _c(age=0, preys=0, altars=0, spears=0, mammoth=0, ref=0.0):
    return {"age": age, "preys_eaten": preys, "altars_solved": altars,
            "spears_crafted": spears, "mammoth_kills": mammoth, "ref_distinction": ref}


def test_score_weighted_sum():
    assert score(_c(age=10, preys=2), W) == (10 * 0.1 + 2 * 50.0)
    assert score(_c(spears=1), W) == 300.0


def test_kendall_tau_identity():
    assert kendall_tau([3.0, 1.0, 2.0], [3.0, 1.0, 2.0]) == 1.0


def test_kendall_tau_reversed():
    assert kendall_tau([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == -1.0


def test_topk_indices_tie_broken_by_index():
    # scores egaux -> indices croissants
    assert _topk_indices([5.0, 5.0, 5.0], 2) == {0, 1}


def test_topk_jaccard_identical_is_one():
    s = [1.0, 2.0, 3.0, 4.0]
    assert topk_jaccard(s, s, 2) == 1.0


def test_topk_jaccard_disjoint_is_zero():
    # top-1 de full = idx3 ; top-1 de var = idx0 -> disjoint
    assert topk_jaccard([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0], 1) == 0.0


def test_term_mass_share_sums_to_one():
    roster = [_c(preys=2), _c(mammoth=1), _c(spears=1)]
    shares = term_mass_share(roster, W)
    assert abs(sum(shares.values()) - 1.0) < 1e-9
    assert shares["altars_solved"] == 0.0  # aucun autel


def test_term_mass_share_zero_total_safe():
    assert term_mass_share([_c()], W)["preys_eaten"] == 0.0  # pas de division par zero
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: FAIL (ModuleNotFoundError / cannot import name).

- [ ] **Step 3: Write minimal implementation (top of the tool file)**

```python
# tools/life_score_contamination_probe.py
"""EDR-WLD-002 : probe d'impact de contamination life_score. Mesure si les termes
morts/inertes de calculate_life_score (altars_solved.20, spears_crafted.300) changent
le classement top-K de la selection sur une cohorte EVOLUEE realiste (memes conditions
qu'EDR 125). NE MUTE JAMAIS la fitness de prod : les variantes sont des copies locales.
Verdict par variante : METRIQUE_INERTE / METRIQUE_CONTAMINEE / AMBIGU. Garde-fou K>=12.

Usage : python tools/life_score_contamination_probe.py
  (env: LSC_SEEDS, LSC_ERAS, LSC_AGENTS, LSC_TICKS)
"""
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def score(components, weights):
    """Somme ponderee des composants par le jeu de poids."""
    return sum(components[k] * weights[k] for k in weights)


def kendall_tau(a, b):
    """tau-b manuel (sans scipy) : corrige les ex-aequo -> kendall_tau(a, a) == 1.0 meme
    quand plusieurs elements partagent le meme score (cohorte de clones-champions).
    tau = (C - D) / sqrt((C+D+Tx)(C+D+Ty))."""
    n = len(a)
    if n < 2:
        return 1.0
    C = D = Tx = Ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = a[i] - a[j]
            db = b[i] - b[j]
            if da == 0 and db == 0:
                continue
            if da == 0:
                Ty += 1
            elif db == 0:
                Tx += 1
            elif da * db > 0:
                C += 1
            else:
                D += 1
    denom = math.sqrt((C + D + Tx) * (C + D + Ty))
    return (C - D) / denom if denom else 1.0

# Correction post-implementation : le plan specifiait initialement un tau-a qui echouait
# sur les ex-aequo (kendall_tau(a,a) < 1.0). Passe en tau-b. Regression couverte par
# test_kendall_tau_identity_with_ties. Comptes de tests du plan +1 par tache en aval.


def _topk_indices(scores, k):
    """Indices du top-k par score decroissant ; egalites departagees par indice croissant."""
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return set(order[:k])


def topk_jaccard(scores_full, scores_var, k):
    """Jaccard des ensembles top-k entre le classement full et le classement variante."""
    a = _topk_indices(scores_full, k)
    b = _topk_indices(scores_var, k)
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def term_mass_share(roster, weights):
    """Part de la masse totale de life_score venant de chaque terme (magnitude de contamination)."""
    terms = {k: sum(c[k] * weights[k] for c in roster) for k in weights}
    total = sum(terms.values())
    return {k: (terms[k] / total if total else 0.0) for k in terms}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/life_score_contamination_probe.py tests/sandbox/test_life_score_contamination_probe.py
git commit -m "feat(WLD): couche metriques pures du probe de contamination life_score"
```

---

### Task 2: Variantes de poids + analyse d'un roster

**Files:**
- Modify: `tools/life_score_contamination_probe.py`
- Test: `tests/sandbox/test_life_score_contamination_probe.py`

**Interfaces:**
- Consumes: `score`, `kendall_tau`, `topk_jaccard`, `term_mass_share` (Task 1)
- Produces: `WEIGHTS_FULL: dict`, `variants() -> dict[str, dict]`, `analyze_roster(roster, frac_topk=0.25) -> dict` avec structure `{"n_crafters", "n_altar_solvers", "term_mass_share", "variants": {nom: {"kendall_tau", "topk_jaccard"}}}`

- [ ] **Step 1: Write the failing tests (append)**

```python
from tools.life_score_contamination_probe import WEIGHTS_FULL, variants, analyze_roster


def test_variants_structure():
    v = variants()
    assert set(v) == {"full", "drop_altars", "drop_spears", "drop_both"}
    assert v["drop_altars"]["altars_solved"] == 0.0
    assert v["drop_altars"]["spears_crafted"] == 300.0
    assert v["drop_spears"]["spears_crafted"] == 0.0
    assert v["drop_both"]["altars_solved"] == 0.0 and v["drop_both"]["spears_crafted"] == 0.0
    # full ne modifie pas les poids de reference
    assert v["full"]["spears_crafted"] == WEIGHTS_FULL["spears_crafted"]


def test_drop_altars_is_identity_when_altars_dead():
    # altars_solved == 0 partout (dead code EDR 096) -> retirer altars = no-op EXACT
    roster = [_c(age=i, preys=i % 3) for i in range(20)]
    res = analyze_roster(roster)
    assert res["variants"]["drop_altars"]["kendall_tau"] == 1.0
    assert res["variants"]["drop_altars"]["topk_jaccard"] == 1.0
    assert res["n_altar_solvers"] == 0


def test_drop_spears_reorders_when_crafter_present():
    # 19 agents faibles + 1 crafteur qui, GRACE au terme spears.300, entre dans le top-k ;
    # le retirer doit l'en sortir -> jaccard < 1
    roster = [_c(age=1, preys=1) for _ in range(19)] + [_c(age=1, preys=1, spears=1)]
    res = analyze_roster(roster, frac_topk=0.25)
    assert res["n_crafters"] == 1
    assert res["variants"]["drop_spears"]["topk_jaccard"] < 1.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: FAIL (cannot import WEIGHTS_FULL / variants / analyze_roster).

- [ ] **Step 3: Write minimal implementation (append to tool)**

```python
from src.seed_ai.persistence import REF_FITNESS_WEIGHT

WEIGHTS_FULL = {
    "age": 0.1, "preys_eaten": 50.0, "altars_solved": 20.0,
    "spears_crafted": 300.0, "mammoth_kills": 400.0, "ref_distinction": REF_FITNESS_WEIGHT,
}


def variants():
    """full + une variante par terme suspect annule (copies locales, jamais la prod)."""
    v = {"full": dict(WEIGHTS_FULL)}
    for name, zeroed in (("drop_altars", ("altars_solved",)),
                         ("drop_spears", ("spears_crafted",)),
                         ("drop_both", ("altars_solved", "spears_crafted"))):
        w = dict(WEIGHTS_FULL)
        for key in zeroed:
            w[key] = 0.0
        v[name] = w
    return v


def analyze_roster(roster, frac_topk=0.25):
    """Compare chaque variante a full sur ce roster. Retourne metriques + comptes d'events."""
    W = variants()
    n = len(roster)
    full_scores = [score(c, W["full"]) for c in roster]
    k = max(1, math.ceil(frac_topk * n)) if n else 1
    out = {
        "n": n,
        "n_crafters": sum(1 for c in roster if c["spears_crafted"] > 0),
        "n_altar_solvers": sum(1 for c in roster if c["altars_solved"] > 0),
        "term_mass_share": term_mass_share(roster, W["full"]) if n else {},
        "variants": {},
    }
    for name, w in W.items():
        if name == "full":
            continue
        var_scores = [score(c, w) for c in roster]
        out["variants"][name] = {
            "kendall_tau": kendall_tau(full_scores, var_scores),
            "topk_jaccard": topk_jaccard(full_scores, var_scores, k),
        }
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/life_score_contamination_probe.py tests/sandbox/test_life_score_contamination_probe.py
git commit -m "feat(WLD): variantes de poids + analyse de roster (drop_altars/spears/both)"
```

---

### Task 3: Harness cohorte évoluée

**Files:**
- Modify: `tools/life_score_contamination_probe.py`
- Test: `tests/sandbox/test_life_score_contamination_probe.py`

**Interfaces:**
- Consumes: réutilise `tools.competence_profile._evolve_champions`, `tools.map_elites_compare.{_make_cfg, _reproduce, PRESERVE_DIMS}`, `src.worlds.world_1_stoneage.Biosphere3D`, `src.agents.mamba_agent.MambaAgent`
- Produces: `_components(agent) -> dict` (6 termes), `_measure_roster(cfg, genomes, max_ticks) -> list[dict]`, `run_arm(seed, eras=8, num_agents=30, max_ticks=300) -> list[dict]`

**Note (coupling):** ces symboles existent sur main (vérifié : `competence_profile.py:90`, `map_elites_compare.py:58`). Si une signature diffère, adapter et signaler.

- [ ] **Step 1: Write the failing tests (append)**

```python
from tools.life_score_contamination_probe import _components, run_arm


def test_components_extracts_six_terms():
    agent = {"age": 5, "preys_eaten": 3, "altars_solved": 0,
             "spears_crafted": 1, "mammoth_kills": 2, "_ref_distinction": 0.4}
    c = _components(agent)
    assert c == {"age": 5, "preys_eaten": 3, "altars_solved": 0,
                 "spears_crafted": 1, "mammoth_kills": 2, "ref_distinction": 0.4}


def test_components_defaults_missing_keys():
    c = _components({"age": 1, "preys_eaten": 0, "altars_solved": 0})
    assert c["spears_crafted"] == 0 and c["mammoth_kills"] == 0 and c["ref_distinction"] == 0.0


def test_run_arm_smoke_returns_roster():
    # run minuscule : evolue 1 ere de 4 agents 5 ticks, mesure -> liste de dicts a 6 cles
    roster = run_arm(seed=0, eras=1, num_agents=4, max_ticks=5)
    assert isinstance(roster, list) and len(roster) >= 1
    assert set(roster[0]) == {"age", "preys_eaten", "altars_solved",
                              "spears_crafted", "mammoth_kills", "ref_distinction"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: FAIL (cannot import `_components` / `run_arm`).

- [ ] **Step 3: Write minimal implementation (append)**

```python
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.competence_profile import _evolve_champions
from tools.map_elites_compare import _make_cfg, _reproduce, PRESERVE_DIMS


def _components(agent):
    """Extrait les 6 termes de life_score (dont altars_solved, pour MESURER qu'il est 0)."""
    return {"age": agent.get("age", 0), "preys_eaten": agent.get("preys_eaten", 0),
            "altars_solved": agent.get("altars_solved", 0),
            "spears_crafted": agent.get("spears_crafted", 0),
            "mammoth_kills": agent.get("mammoth_kills", 0),
            "ref_distinction": agent.get("_ref_distinction", 0.0)}


def _measure_roster(cfg, genomes, max_ticks):
    """Mesure sur COHORTE FIXE (benchmark_mode) ; roster = env.agents + dead_agents
    (mirror competence_profile._measure_profile : inclut les morts avec stats finales)."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    return [_components(a) for a in pool]


def run_arm(seed=0, eras=8, num_agents=30, max_ticks=300):
    """Evolue des champions (cliquet top-5, repro ON, regime sweet _make_cfg) puis mesure
    leur cohorte fixe. Retourne le roster (liste de composants). CRN via _evolve_champions."""
    champs = _evolve_champions(seed, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    if not champs:
        return []
    reps = (champs * (num_agents // len(champs) + 1))[:num_agents]
    return _measure_roster(_make_cfg(), reps, max_ticks)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: PASS (14 tests). Le smoke `test_run_arm_smoke_returns_roster` peut prendre quelques secondes (évolution minuscule).

- [ ] **Step 5: Commit**

```bash
git add tools/life_score_contamination_probe.py tests/sandbox/test_life_score_contamination_probe.py
git commit -m "feat(WLD): harness cohorte evoluee (reuse _evolve_champions, roster = pool+dead)"
```

---

### Task 4: Agrégation multi-seed + verdict

**Files:**
- Modify: `tools/life_score_contamination_probe.py`
- Test: `tests/sandbox/test_life_score_contamination_probe.py`

**Interfaces:**
- Consumes: la structure `analyze_roster` (Task 2) : `per_seed[i]["variants"][name]["topk_jaccard"|"kendall_tau"]`
- Produces: `_median(xs) -> float`, `aggregate(per_seed, k_seeds, effect_thresh=0.10) -> dict` avec `{"per_variant": {nom: {"median_jaccard","median_tau","n_changed","effect","verdict"}}, "global_verdict": str}`

- [ ] **Step 1: Write the failing tests (append)**

```python
from tools.life_score_contamination_probe import _median, aggregate


def _seed_result(jac_by_variant):
    # helper : construit un dict analyze_roster minimal avec les jaccard/tau donnes
    return {"variants": {name: {"topk_jaccard": j, "kendall_tau": (1.0 if j == 1.0 else 0.5)}
                         for name, j in jac_by_variant.items()}}


def test_median_odd_even():
    assert _median([3.0, 1.0, 2.0]) == 2.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_verdict_inerte_when_no_change():
    per_seed = [_seed_result({"drop_altars": 1.0}) for _ in range(12)]
    agg = aggregate(per_seed, k_seeds=12)
    assert agg["per_variant"]["drop_altars"]["verdict"] == "METRIQUE_INERTE"


def test_verdict_contaminee_needs_strong_effect_and_k12():
    # jaccard 0.5 partout (effect 0.5), 12 seeds tous changes -> CONTAMINEE
    per_seed = [_seed_result({"drop_spears": 0.5}) for _ in range(12)]
    agg = aggregate(per_seed, k_seeds=12)
    assert agg["per_variant"]["drop_spears"]["verdict"] == "METRIQUE_CONTAMINEE"


def test_guardrail_blocks_contaminee_under_12():
    # meme effet fort mais seulement 6 seeds -> jamais CONTAMINEE (garde-fou)
    per_seed = [_seed_result({"drop_spears": 0.5}) for _ in range(6)]
    agg = aggregate(per_seed, k_seeds=6)
    assert agg["per_variant"]["drop_spears"]["verdict"] == "AMBIGU"


def test_verdict_ambigu_weak_effect():
    # jaccard 0.95 partout -> mediane 0.95 (!= 1.0 donc pas INERTE), effect 0.05 < 0.10
    # donc pas CONTAMINEE -> AMBIGU
    per_seed = [_seed_result({"drop_spears": 0.95}) for _ in range(12)]
    agg = aggregate(per_seed, k_seeds=12)
    assert agg["per_variant"]["drop_spears"]["verdict"] == "AMBIGU"


def test_global_verdict_picks_most_actionable():
    per_seed = [_seed_result({"drop_altars": 1.0, "drop_spears": 0.5}) for _ in range(12)]
    agg = aggregate(per_seed, k_seeds=12)
    assert agg["global_verdict"] == "METRIQUE_CONTAMINEE"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: FAIL (cannot import `_median` / `aggregate`).

- [ ] **Step 3: Write minimal implementation (append)**

```python
def _median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


_RANK = {"METRIQUE_CONTAMINEE": 2, "AMBIGU": 1, "METRIQUE_INERTE": 0}


def aggregate(per_seed, k_seeds, effect_thresh=0.10):
    """Agrege les metriques par variante sur les seeds et rend un verdict. Garde-fou :
    aucun METRIQUE_CONTAMINEE sous k_seeds=12."""
    names = list(per_seed[0]["variants"]) if per_seed else []
    per_variant = {}
    for name in names:
        jac = [s["variants"][name]["topk_jaccard"] for s in per_seed]
        tau = [s["variants"][name]["kendall_tau"] for s in per_seed]
        med_j = _median(jac)
        med_t = _median(tau)
        n_changed = sum(1 for x in jac if x < 1.0)
        effect = 1.0 - med_j
        if med_j == 1.0 and med_t == 1.0:
            verdict = "METRIQUE_INERTE"
        elif k_seeds >= 12 and effect >= effect_thresh and n_changed >= math.ceil(k_seeds / 2):
            verdict = "METRIQUE_CONTAMINEE"
        else:
            verdict = "AMBIGU"
        per_variant[name] = {"median_jaccard": med_j, "median_tau": med_t,
                             "n_changed": n_changed, "effect": effect, "verdict": verdict}
    global_verdict = max((v["verdict"] for v in per_variant.values()),
                         key=lambda x: _RANK[x], default="METRIQUE_INERTE")
    return {"per_variant": per_variant, "global_verdict": global_verdict}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: PASS (20 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/life_score_contamination_probe.py tests/sandbox/test_life_score_contamination_probe.py
git commit -m "feat(WLD): agregation multi-seed + verdict INERTE/CONTAMINEE/AMBIGU (garde-fou K>=12)"
```

---

### Task 5: Corroborant HoF + compare + repro + `__main__`

**Files:**
- Modify: `tools/life_score_contamination_probe.py`
- Test: `tests/sandbox/test_life_score_contamination_probe.py`

**Interfaces:**
- Consumes: `run_arm` (T3), `analyze_roster` (T2), `aggregate` (T4), `term_mass_share`/`WEIGHTS_FULL` (T1/T2)
- Produces: `hof_decomposition() -> dict | None`, `compare(seeds, eras=8, num_agents=30, max_ticks=300, frac_topk=0.25) -> dict`, bloc `__main__`

- [ ] **Step 1: Write the failing tests (append)**

```python
from tools.life_score_contamination_probe import hof_decomposition, compare


def test_hof_decomposition_graceful_absent():
    # aucun HoF en prod -> None, jamais d'exception
    res = hof_decomposition()
    assert res is None or ("mean_share" in res and "n_champions" in res)


def test_compare_schema_and_repro():
    # 2 seeds, run minuscule ; verifie schema + que la garde repro ne leve pas
    out = compare(seeds=(0, 1), eras=1, num_agents=4, max_ticks=5)
    assert set(out) >= {"config", "per_seed", "per_variant", "global_verdict", "hof_decomposition"}
    assert len(out["per_seed"]) == 2
    assert out["global_verdict"] in {"METRIQUE_INERTE", "METRIQUE_CONTAMINEE", "AMBIGU"}
    assert out["per_variant"]["drop_altars"]["verdict"] == "METRIQUE_INERTE"  # altars dead
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: FAIL (cannot import `hof_decomposition` / `compare`).

- [ ] **Step 3: Write minimal implementation (append)**

```python
def hof_decomposition():
    """Corroborant non-bloquant : decompose le HoF de prod (si present) en part-de-masse
    par terme (moyenne sur les champions). Retourne None sur toute absence/erreur."""
    try:
        from src.seed_ai.persistence import load_hall_of_fame
        _version, hof = load_hall_of_fame()
        if not hof:
            return None
        shares = []
        for entry in hof:
            stats = getattr(entry, "stats", None)
            if stats is None and isinstance(entry, dict):
                stats = entry.get("stats")
            if not stats:
                continue
            comp = {"age": stats.get("age", 0), "preys_eaten": stats.get("preys_eaten", 0),
                    "altars_solved": stats.get("altars_solved", 0),
                    "spears_crafted": stats.get("spears_crafted", 0),
                    "mammoth_kills": stats.get("mammoth_kills", 0), "ref_distinction": 0.0}
            shares.append(term_mass_share([comp], WEIGHTS_FULL))
        if not shares:
            return None
        keys = list(shares[0])
        return {"n_champions": len(shares),
                "mean_share": {k: sum(s[k] for s in shares) / len(shares) for k in keys}}
    except Exception:
        return None


def compare(seeds=(0,), eras=8, num_agents=30, max_ticks=300, frac_topk=0.25):
    """Evolue+mesure chaque seed, analyse, agrege, verdict. Garde repro : re-run seed[0]
    et exige un roster byte-identique."""
    rosters = {}
    per_seed = []
    for s in seeds:
        roster = run_arm(seed=s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
        rosters[s] = roster
        per_seed.append(analyze_roster(roster, frac_topk=frac_topk))
    repro = run_arm(seed=seeds[0], eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    assert repro == rosters[seeds[0]], "repro cassee : deux passes seed[0] different"
    agg = aggregate(per_seed, k_seeds=len(seeds))
    return {"config": {"seeds": list(seeds), "eras": eras, "num_agents": num_agents,
                       "max_ticks": max_ticks, "frac_topk": frac_topk},
            "per_seed": per_seed, "per_variant": agg["per_variant"],
            "global_verdict": agg["global_verdict"], "hof_decomposition": hof_decomposition()}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import json
    seeds = tuple(int(x) for x in os.environ.get("LSC_SEEDS", ",".join(str(i) for i in range(12))).split(","))
    eras = int(os.environ.get("LSC_ERAS", "8"))
    n_agents = int(os.environ.get("LSC_AGENTS", "30"))
    ticks = int(os.environ.get("LSC_TICKS", "300"))
    out = compare(seeds=seeds, eras=eras, num_agents=n_agents, max_ticks=ticks)
    for i, ps in enumerate(out["per_seed"]):
        da = ps["variants"]["drop_altars"]
        ds = ps["variants"]["drop_spears"]
        print(f"seed={seeds[i]} n={ps['n']} crafters={ps['n_crafters']} altar={ps['n_altar_solvers']} "
              f"| drop_altars tau={da['kendall_tau']:+.3f} jac={da['topk_jaccard']:.3f} "
              f"| drop_spears tau={ds['kendall_tau']:+.3f} jac={ds['topk_jaccard']:.3f}")
    print("--- verdict par variante ---")
    for name, v in out["per_variant"].items():
        print(f"{name:12s} med_jac={v['median_jaccard']:.3f} med_tau={v['median_tau']:+.3f} "
              f"effect={v['effect']:.3f} n_changed={v['n_changed']} -> {v['verdict']}")
    print("VERDICT GLOBAL:", out["global_verdict"])
    if out["hof_decomposition"]:
        print("HoF mean_share:", out["hof_decomposition"]["mean_share"])
    os.makedirs("results", exist_ok=True)
    path = f"results/life_score_contamination_{seeds[0]}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("RESULT ->", path)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sandbox/test_life_score_contamination_probe.py -q`
Expected: PASS (22 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/life_score_contamination_probe.py tests/sandbox/test_life_score_contamination_probe.py
git commit -m "feat(WLD): corroborant HoF + compare + garde repro + __main__ (cp1252-safe)"
```

---

## Après le plan

Une fois les 5 tâches vertes + revue finale : lancer le run de recherche (K=12, `python tools/life_score_contamination_probe.py`, tâche de fond) puis rédiger **EDR-WLD-002** avec le verdict par variante. Prédiction : `drop_altars` = INERTE-exact (preuve empirique du dead-code EDR 096) ; `drop_spears` = l'inconnue (dépend de si les rares crafteurs entrent dans le top-K).
