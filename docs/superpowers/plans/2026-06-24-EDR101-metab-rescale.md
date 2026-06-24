# EDR 101 — Rescale `base_metabolism` : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre `tools/lewis_survival_sweep.py` pour balayer `base_metabolism` (0.25→0) à `N_APEX=0` et mesurer la survie médiane des champions, afin de tester si le mur métabolique de Lewis (EDR 100) est supprimable par config.

**Architecture:** Extension DRY config-only du harnais (calque le pattern `main_apex` d'EDR 094). `_cfg` gagne un paramètre `base_metabolism` ; un `_verdict_metab` (même forme que `_verdict_apex`) et un driver `main_metab` réutilisent `_measure_survival` (093) et `_report` (paramétré `knob`/`verdict_fn` depuis 094). Aucune modification du code de production.

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR101-Metabolism-Rescale-design.md`.

## Global Constraints

- **1 variable** : `base_metabolism` ∈ `(0.25, 0.1, 0.05, 0.025, 0.0)`. Tout le reste fixe.
- Fixes gelés : `N_APEX=0`, `forage_payoff=3`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`, gate survie `120`.
- **Pas d'évolution, pas de langage** ; champions répliqués via `_reproduce`.
- **Config-only** : seul `tools/lewis_survival_sweep.py` + son test changent. Aucune modif du code de prod.
- Reproductibilité : `_disable_kuzu()` ; `Harness(with_db=False)` ; `seed_at(s,0)` par ère ; mêmes seeds entre niveaux (appariement).
- Verdict strings exactement (ASCII) : `"RESCALE SUFFIT"`, `"RESCALE EXTREME"`, `"PAS LE METABOLISME SEUL"`.
- **Non-régression** : les tests existants (093/094/098/099/100) restent verts (`_cfg` rétro-compatible : défaut `base_metabolism=METAB`).
- Commits path-scopés ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `tools/lewis_survival_sweep.py` — `_cfg` (+param `base_metabolism`), +`METAB_LEVELS`, +`_verdict_metab`, +`main_metab`.
- **Modify:** `tests/sandbox/test_lewis_survival_sweep.py` — +tests.

---

## Task 1: `_cfg(+base_metabolism)` + `METAB_LEVELS` + `_verdict_metab`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_cfg` ; ajout constante + fonction)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `METAB` (constante existante, `0.25`), `GATE` (`120.0`).
- Produces : `_cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB) -> WorldConfig` ; `METAB_LEVELS = (0.25, 0.1, 0.05, 0.025, 0.0)` ; `_verdict_metab(levels, medians, gate=GATE) -> str`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_cfg_sets_base_metabolism():
    assert lss._cfg(3, base_metabolism=0.05).base_metabolism == 0.05
    assert lss._cfg(3, base_metabolism=0.0).base_metabolism == 0.0
    assert lss._cfg(3).base_metabolism == lss.METAB          # defaut 0.25 (retro-compat)


def test_verdict_metab_three_branches():
    levels = (0.25, 0.1, 0.05, 0.025, 0.0)
    # un base_metabolism > 0 franchit (ici 0.05) -> rescale suffit
    assert lss._verdict_metab(levels, [10, 50, 130, 200, 260]) == "RESCALE SUFFIT"
    # franchit SEULEMENT a base_metabolism = 0 -> rescale extreme
    assert lss._verdict_metab(levels, [10, 20, 40, 90, 150]) == "RESCALE EXTREME"
    # aucun ne franchit -> pas le metabolisme seul
    assert lss._verdict_metab(levels, [5, 8, 10, 30, 60]) == "PAS LE METABOLISME SEUL"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_metab(levels, [5, 8, 10, 30, 120]) == "PAS LE METABOLISME SEUL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_base_metabolism tests/sandbox/test_lewis_survival_sweep.py::test_verdict_metab_three_branches -q`
Expected: FAIL (`TypeError: _cfg() ... 'base_metabolism'` puis `AttributeError: _verdict_metab`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Remplacer `_cfg` (la définition actuelle) :

```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098
    cfg.trace_energy_sinks = bool(trace_energy_sinks)         # EDR099
    return cfg
```

par (ajout du param `base_metabolism`, défaut `METAB`) :

```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB):
    cfg = WorldConfig()
    cfg.base_metabolism = float(base_metabolism)             # EDR101 : sweepable (defaut METAB=0.25)
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098
    cfg.trace_energy_sinks = bool(trace_energy_sinks)         # EDR099
    return cfg
```

**3b.** Ajouter la constante près des autres `*_LEVELS` (par ex. après `APEX_LEVELS`) :

```python
METAB_LEVELS = (0.25, 0.1, 0.05, 0.025, 0.0)   # base_metabolism balaye : de 085 (0.25) vers 0
```

**3c.** Ajouter `_verdict_metab` (après `_verdict_apex`) — même forme que `_verdict_apex` :

```python
def _verdict_metab(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau de base_metabolism) -> 3 branches pre-enregistrees. Un
    base_metabolism > 0 franchit le gate -> rescale suffit (mur supprimable par config) ; seul 0 franchit ->
    rescale extreme (metabolisme nul requis) ; aucun -> pas le metabolisme seul (la suppression ne sauve pas)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "PAS LE METABOLISME SEUL"
    return "RESCALE SUFFIT" if max(crossed) > 0 else "RESCALE EXTREME"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_base_metabolism tests/sandbox/test_lewis_survival_sweep.py::test_verdict_metab_three_branches -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Run non-régression `_cfg` (093) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_payoff_metab_cap -q`
Expected: PASS (le nouveau param par défaut `METAB` préserve `cfg.base_metabolism == 0.25`).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr101-metab-rescale"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR101): _cfg +base_metabolism, METAB_LEVELS, _verdict_metab

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `main_metab` (sweep `base_metabolism`)

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajout `main_metab`)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg` (avec `base_metabolism`), `_measure_survival` (093), `_verdict_metab`, `METAB_LEVELS`, `_report`, `Harness`, `_disable_kuzu`.
- Produces : `main_metab(levels=METAB_LEVELS, n_eval=8, R=4, seed=None, _return=False)`. Avec `_return=True`, renvoie `{"levels","medians","jt","verdict","table"}` où `table[base_metabolism]` a les clés `{"median","famine","combat","mean_kills","n"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_main_metab_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_metab(levels=(0.25, 0.0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_metab(levels=(0.25, 0.0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [0.25, 0.0]
    assert set(a["table"][0.25]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"RESCALE SUFFIT", "RESCALE EXTREME", "PAS LE METABOLISME SEUL"}
```

(NB : vraie simulation réduite ; ~30-90 s.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_metab_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main_metab'`).

- [ ] **Step 3: Write minimal implementation**

Ajouter `main_metab` (après `main_apex`, avant `main_decompose` ou `if __name__`) :

```python
def main_metab(levels=METAB_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 101 : sweep base_metabolism a N_APEX=0 (monde vide), forage_payoff=3 fixe, Lewis letalite 0.
    1ere intervention : teste si reduire le multiplicateur de metabolisme debloque la survie."""
    with Harness(seed=seed, name="lewis_metab_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR101 : sweep base_metabolism={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux base_metabolism")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3, base_metabolism=lv), seeds, n_apex=0))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="base_metab", verdict_fn=_verdict_metab)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_metab_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Run le fichier complet (non-régression) + smoke console + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py tests/sandbox/test_energy_trace.py -q`
Expected: PASS (tous les tests existants 093/094/098/099/100 + les 3 de 101).

Smoke console (cp1252) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr101-metab-rescale"
python -c "from tools import lewis_survival_sweep as lss; lss.main_metab(levels=(0.25,0.0), n_eval=2, R=1, seed=21)"
```
Expected : table survie × `base_metabolism` + verdict SANS `UnicodeEncodeError`.

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr101-metab-rescale"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR101): main_metab (sweep base_metabolism, reutilise _measure_survival + _report)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Run direct (EXÉCUTION) — la mesure + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (réduit, ~1 min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr101-metab-rescale"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print('SMOKE:', lss.main_metab(levels=(0.25,0.05,0.0), n_eval=3, R=1, seed=21, _return=True)['verdict'])" 2>/dev/null
```
Expected : table + verdict ∈ {RESCALE SUFFIT, RESCALE EXTREME, PAS LE METABOLISME SEUL}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr101-metab-rescale"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main_metab(seed=101)" 2>/dev/null
```
Expected : table survie × `base_metabolism` (5 niveaux, R=4, n_eval=8), JT, verdict. Provenance `results/lewis_metab_sweep_101.json`.

**Sanity check à vérifier au run :** à `base_metabolism=0`, la survie devrait au minimum **augmenter vs 0.25** (le drain métabolique disparaît). Si la survie reste plate à 5 ticks même à 0 → PAS LE METABOLISME SEUL (vérifier alors les causes : famine encore dominante ?).

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 101 selon la branche, et amorcer la suite :
  - **RESCALE SUFFIT** → premier barreau survivable à `base_metabolism = X > 0` ; base d'un curriculum corrigé (re-test 090). EDR 102 = vérifier `from_genome` (le trait est-il un artefact ?) reste utile pour la généralisation.
  - **RESCALE EXTREME** → métabolisme nul requis ; le trait `phenotype_energy_drain` est trop lourd → EDR 102 (vérification `from_genome` : artefact d'aplatissement ?) devient prioritaire.
  - **PAS LE METABOLISME SEUL** → supprimer le métabolisme ne sauve pas ; pivot forage/comportement (mesurer pourquoi les champions ne foragent pas assez).

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 variable `base_metabolism` (0.25..0), reste fixe → T1 (`_cfg` param, `METAB_LEVELS`), T2 (`main_metab` à `n_apex=0`/`_cfg(3)`). ✓
- §3 métrique survie médiane + JT + verdict 3 branches → T1 (`_verdict_metab`), T2 (`main_metab` via `_report`). ✓
- §3 sous-produits famine/combat + kills → réutilise `_measure_survival` (093) + `_report` (table). ✓
- §4 params gelés → `METAB_LEVELS`, `main_metab` défauts R=4/n_eval=8, `n_apex=0`/`forage_payoff=3` fixes. ✓
- §5 extension DRY (`_cfg`+param, `_verdict_metab`, `main_metab`, `Harness("lewis_metab_sweep")`, `_report` réutilisé) → T1/T2. ✓
- §5 pairing seeds entre niveaux → T2 (`seeds` indépendant du niveau). ✓
- §6 tests (cfg, verdict, main) + non-régression → T1/T2. ✓
- §7 run direct → T3. ✓
- §8 `_disable_kuzu`, `seed_at`, `n_apex=0` correctif 094 → T2 (`main_metab` + `_measure_survival`). ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes (seul le seed du run T3 = `101` fixé ici). ✓

**3. Type consistency :** `_cfg(forage_payoff, ..., base_metabolism=METAB)` (T1) appelé par `main_metab` avec `base_metabolism=lv` (T2). `_verdict_metab(levels, medians)` (T1) passé comme `verdict_fn` à `_report` (T2). `main_metab -> {levels,medians,jt,verdict,table}` (T2) consommé par le test. Cohérent avec le contrat `_report`/`_measure_survival` existant. ✓
