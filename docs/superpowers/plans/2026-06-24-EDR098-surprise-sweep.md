# EDR 098 — Sweep `ttc_surprise_scale` : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre `tools/lewis_survival_sweep.py` (EDR 093/094, mergé) pour balayer `ttc_surprise_scale` à `N_APEX=0` et mesurer la survie + le `surprise_momentum`, afin de tester si le mur intrinsèque de Lewis est le `brain_cost` amplifié par la surprise.

**Architecture:** Extension DRY config-only du harnais 093/094 mergé. Trois ajouts rétro-compatibles dans le même fichier : (1) param `ttc_surprise_scale` à `_cfg` + `SURPRISE_LEVELS` + `_verdict_surprise` ; (2) flag `collect_surprise` à `_measure_survival` (instrumentation `surprise_momentum`) ; (3) colonne surprise conditionnelle dans `_report` + driver `main_surprise`. Les `main`/`main_apex` (093/094) restent fonctionnellement inchangés. **Zéro modif du code de production.**

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR098-Intrinsic-Drain-Surprise-Sweep-design.md`.

## Global Constraints

- **1 variable** : `ttc_surprise_scale` ∈ `(1.0, 0.5, 0.25, 0.0)`. Tout le reste fixe.
- Fixes gelés : `N_APEX=0` (monde vide), `forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`, gate survie `120`.
- **Pas d'évolution, pas de langage** ; champions répliqués via `_reproduce`.
- **Zéro modification du code de production** : `ttc_surprise_scale` est déjà un champ `WorldConfig`. Lecture `surprise_momentum` read-only. Seul `tools/lewis_survival_sweep.py` + son test changent.
- Reproductibilité : `_disable_kuzu()` avant tout monde ; `Harness(with_db=False)` ; `seed_at(seed, 0)` par ère ; mêmes seeds entre niveaux (appariement).
- Survie = **âge par agent** sur le pool (`env.agents + env.dead_agents`), médiane par niveau.
- Cause de mort : `energy <= 0` = famine ; `hp <= 0 and energy > 0` = combat.
- Verdict strings exactement (ASCII, cp1252) : `"TARIF=SURPRISE"`, `"OVERFLOW=RACINE"`, `"PAS LE BRAIN_COST"`.
- **Non-régression** : les 7 tests existants (093+094) restent verts.
- Commits path-scopés ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `tools/lewis_survival_sweep.py` — ajout `SURPRISE_LEVELS`, `_verdict_surprise`, param `ttc_surprise_scale` à `_cfg`, flag `collect_surprise` à `_measure_survival`, colonne surprise dans `_report`, `main_surprise`. Aucune suppression.
- **Modify:** `tests/sandbox/test_lewis_survival_sweep.py` — ajout de 3 tests. Les 7 existants restent.
- **Untouched:** tout le reste (code de prod inclus).

---

## Task 1: `_cfg(+ttc_surprise_scale)` + `SURPRISE_LEVELS` + `_verdict_surprise`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_cfg` lignes 32-37 ; ajout constante + fonction)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `WorldConfig`, `GATE` (déjà là).
- Produces : `_cfg(forage_payoff, ttc_surprise_scale=None) -> WorldConfig` ; `SURPRISE_LEVELS = (1.0, 0.5, 0.25, 0.0)` ; `_verdict_surprise(levels, medians, frac_nonfinite, gate=GATE) -> str`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_cfg_sets_surprise_scale():
    assert lss._cfg(3, ttc_surprise_scale=0.0).ttc_surprise_scale == 0.0
    assert lss._cfg(3, ttc_surprise_scale=0.5).ttc_surprise_scale == 0.5
    assert lss._cfg(3).ttc_surprise_scale == 1.0          # defaut config preserve (retro-compat)


def test_verdict_surprise_three_branches():
    levels = (1.0, 0.5, 0.25, 0.0)
    ff0 = [0.0, 0.0, 0.0, 0.0]
    # un scale<1 franchit (0.25 et 0.0) -> tarif = surprise
    assert lss._verdict_surprise(levels, [10, 50, 130, 200], ff0) == "TARIF=SURPRISE"
    # aucun ne franchit + une surprise non-finie -> overflow racine
    assert lss._verdict_surprise(levels, [5, 5, 5, 5], [0.0, 0.0, 0.0, 0.3]) == "OVERFLOW=RACINE"
    # aucun ne franchit + surprises finies -> pas le brain_cost
    assert lss._verdict_surprise(levels, [5, 5, 5, 5], ff0) == "PAS LE BRAIN_COST"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_surprise(levels, [5, 5, 5, 120], ff0) == "PAS LE BRAIN_COST"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_surprise_scale tests/sandbox/test_lewis_survival_sweep.py::test_verdict_surprise_three_branches -q`
Expected: FAIL (`TypeError: _cfg() got an unexpected keyword argument 'ttc_surprise_scale'` puis `AttributeError: _verdict_surprise`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Remplacer `_cfg` (lignes 32-37) :

```python
def _cfg(forage_payoff):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    return cfg
```

par :

```python
def _cfg(forage_payoff, ttc_surprise_scale=None):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098 ; sinon defaut config (1.0)
    return cfg
```

**3b.** Ajouter la constante près de `APEX_LEVELS` (après la ligne 29) :

```python
SURPRISE_LEVELS = (1.0, 0.5, 0.25, 0.0)   # ttc_surprise_scale : baseline 094 (1.0) -> brain_cost decouple (0.0)
```

**3c.** Ajouter `_verdict_surprise` après `_verdict_apex` :

```python
def _verdict_surprise(levels, medians, frac_nonfinite, gate=GATE):
    """Mappe (medianes, fractions non-finies de surprise par niveau) -> 3 branches pre-enregistrees.
    Un ttc_surprise_scale franchit le gate -> TARIF=SURPRISE (le brain_cost surprise-amplifie est le mur) ;
    aucun ne franchit + une surprise non-finie (overflow) -> OVERFLOW=RACINE ; aucun + surprises finies ->
    PAS LE BRAIN_COST (le drain est ailleurs, ex. throw)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if crossed:
        return "TARIF=SURPRISE"
    if any(f > 0 for f in frac_nonfinite):
        return "OVERFLOW=RACINE"
    return "PAS LE BRAIN_COST"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_surprise_scale tests/sandbox/test_lewis_survival_sweep.py::test_verdict_surprise_three_branches -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Run non-régression `_cfg` (093) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_payoff_metab_cap -q`
Expected: PASS (le param optionnel n'a pas cassé `_cfg(forage_payoff)`).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR098): _cfg +ttc_surprise_scale, SURPRISE_LEVELS, _verdict_surprise

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: flag `collect_surprise` dans `_measure_survival`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_measure_survival` lignes 40-73)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_disable_kuzu`, `np` (déjà là).
- Produces : `_measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS, collect_surprise=False)`. Quand `collect_surprise=True`, le dict retourné gagne une clé `"surprise"` = liste (une entrée/ère) de `{"mean_abs_finite", "max_finite", "frac_nonfinite"}`, lue sur `agent["model"].surprise_momentum` du pool. Défaut `False` → dict **identique** à 093/094.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_measure_survival_collect_surprise():
    lss._disable_kuzu()
    cfg = lss._cfg(3, ttc_surprise_scale=1.0)
    a = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30, collect_surprise=True)
    a2 = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30, collect_surprise=True)
    assert set(a) == {"ticks", "famine", "combat", "kills", "surprise"}
    assert len(a["surprise"]) == 2                          # une entree par ere (2 seeds)
    assert set(a["surprise"][0]) == {"mean_abs_finite", "max_finite", "frac_nonfinite"}
    assert all(0.0 <= s["frac_nonfinite"] <= 1.0 for s in a["surprise"])
    assert a == a2                                          # seede -> reproductible
    # defaut (sans collect) -> contrat 093/094 preserve
    b = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert set(b) == {"ticks", "famine", "combat", "kills"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_collect_surprise -q`
Expected: FAIL (`TypeError: ... unexpected keyword argument 'collect_surprise'`).

- [ ] **Step 3: Write minimal implementation**

Remplacer `_measure_survival` (lignes 40-73) par (signature étendue + collecte surprise + clé conditionnelle) :

```python
def _measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS,
                      max_ticks=MAX_TICKS, collect_surprise=False):
    """Mesure la survie des CHAMPIONS (repliques, pas d'evolution) en Lewis a letalite leurre_frac.
    Une ere par seed (appariement entre niveaux : meme seed -> meme monde initial). memory_retriever
    stoppe avant la boucle. Renvoie ages (pool), causes de mort (famine/combat), kills moyens/ere.
    Si collect_surprise : ajoute 'surprise' = stats de agent['model'].surprise_momentum par ere
    (mean_abs_finite, max_finite, frac_nonfinite) -> diagnostic du brain_cost (EDR098)."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)                  # graine fixe pour _load_champions (HoF vide -> fallback random)
    champs = _load_champions()
    ticks, famine, combat, kills, surprise = [], 0, 0, [], []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, leurre_frac, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()   # vide le cache timing-dependant -> reproductible
        env.use_ref_head = False
        env.decode_act = False
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        ticks.extend(int(ag.get("age", 0)) for ag in pool)
        famine += sum(1 for ag in pool if ag.get("energy", 1.0) <= 0)
        combat += sum(1 for ag in pool if ag.get("hp", 1.0) <= 0 and ag.get("energy", 1.0) > 0)
        kills.append(float(np.mean([ag.get("mammoth_kills", 0) for ag in pool])) if pool else 0.0)
        if collect_surprise:
            surprise.append(_surprise_stats(pool))
    result = {"ticks": ticks, "famine": famine, "combat": combat, "kills": kills}
    if collect_surprise:
        result["surprise"] = surprise
    return result


def _surprise_stats(pool):
    """Stats de surprise_momentum sur le pool (read-only) : moyenne des |finies|, max fini, fraction
    non-finie (inf/nan -> detecte l'overflow brain_cost)."""
    vals = []
    for ag in pool:
        m = ag.get("model")
        try:
            vals.append(float(getattr(m, "surprise_momentum", np.nan)))
        except (TypeError, ValueError):
            vals.append(np.nan)
    arr = np.array(vals, dtype=float)
    finite = arr[np.isfinite(arr)]
    return {"mean_abs_finite": float(np.mean(np.abs(finite))) if finite.size else 0.0,
            "max_finite": float(np.max(np.abs(finite))) if finite.size else 0.0,
            "frac_nonfinite": float(np.mean(~np.isfinite(arr))) if arr.size else 0.0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_collect_surprise -q`
Expected: PASS (simulation réduite ~10-40 s).

- [ ] **Step 5: Run non-régression (093/094 measure) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_keys_and_reproducible tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_n_apex_wired_and_reproducible -q`
Expected: PASS (le défaut `collect_surprise=False` préserve le contrat 093/094).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR098): collect_surprise dans _measure_survival (instrumentation surprise_momentum)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: colonne surprise dans `_report` + `main_surprise`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_report` lignes 97-119 ; ajout `main_surprise`)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_measure_survival` (avec `collect_surprise`), `_verdict_surprise`, `SURPRISE_LEVELS`, `st.jonckheere_terpstra`, `Harness`, `_disable_kuzu`.
- Produces : `_report(...)` détecte les groupes portant `"surprise"` → calcule `frac_nonfinite` par niveau, appelle `verdict_fn(levels, medians, frac_nf)`, et ajoute une colonne surprise à la table/impression. `main_surprise(levels=SURPRISE_LEVELS, n_eval=8, R=4, seed=None, _return=False)`. Avec `_return=True`, renvoie `{"levels","medians","jt","verdict","table"}` où `table[scale]` a au moins `{"median","famine","combat","mean_kills","n","mean_surprise","frac_nonfinite"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_main_surprise_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_surprise(levels=(1.0, 0.0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_surprise(levels=(1.0, 0.0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [1.0, 0.0]
    assert {"median", "famine", "combat", "mean_kills", "n",
            "mean_surprise", "frac_nonfinite"} <= set(a["table"][1.0])
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"TARIF=SURPRISE", "OVERFLOW=RACINE", "PAS LE BRAIN_COST"}
```

(NB : vraie simulation réduite ; ~30-90 s.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_surprise_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main_surprise'`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Remplacer `_report` (lignes 97-119) par (détection surprise + colonne conditionnelle ; appel verdict à 2 ou 3 args selon les groupes ; tout ASCII) :

```python
def _report(h, levels, groups, R, n_eval, _return, knob="forage_payoff", verdict_fn=_verdict):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance.
    knob = nom du parametre balaye ; verdict_fn = mapping medianes->verdict. Si les groupes portent une
    cle 'surprise' (EDR098), ajoute une colonne surprise et appelle verdict_fn(levels, medians, frac_nf)."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    has_surprise = all("surprise" in g for g in groups)
    if has_surprise:
        frac_nf = [float(np.mean([s["frac_nonfinite"] for s in g["surprise"]])) if g["surprise"] else 0.0
                   for g in groups]
        verdict = verdict_fn(levels, medians, frac_nf)
    else:
        verdict = verdict_fn(levels, medians)
    table = {}
    print(f"\n=== EDR sweep {knob} : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        row = {"median": med, "famine": g["famine"], "combat": g["combat"], "mean_kills": mk, "n": n}
        line = (f"  {knob}={lv:<4} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
                f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
        if has_surprise:
            ms = float(np.mean([s["mean_abs_finite"] for s in g["surprise"]])) if g["surprise"] else 0.0
            fnf = float(np.mean([s["frac_nonfinite"] for s in g["surprise"]])) if g["surprise"] else 0.0
            row["mean_surprise"] = ms
            row["frac_nonfinite"] = fnf
            line += f" | surprise~{ms:.1f} nonfini={fnf:.2f}"
        table[lv] = row
        print(line)
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": knob, "levels": list(levels), "R": R, "n_eval": n_eval, "medians": medians,
            "jt": jt, "verdict": verdict, "table": {str(k): v for k, v in table.items()}})
    if _return:
        return {"levels": list(levels), "medians": medians, "jt": jt,
                "verdict": verdict, "table": table}
```

**3b.** Ajouter `main_surprise` après `main_apex` (avant le bloc `if __name__`) :

```python
def main_surprise(levels=SURPRISE_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 098 : sweep ttc_surprise_scale a N_APEX=0 (monde vide), forage_payoff=3 fixe, Lewis letalite 0.
    Instrumente surprise_momentum -> teste si le brain_cost surprise-amplifie est le mur intrinseque."""
    with Harness(seed=seed, name="lewis_surprise_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR098 : sweep ttc_surprise_scale={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux ttc_surprise_scale")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3, ttc_surprise_scale=lv), seeds, n_apex=0,
                                            collect_surprise=True))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="surprise_scale",
                       verdict_fn=_verdict_surprise)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_surprise_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Run le fichier complet (non-régression 093/094) + smoke console + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: PASS (10 tests : 7 de 093/094 + 3 de 098). Le `_report` reste rétro-compatible (groupes 093/094 sans `"surprise"` → branche `has_surprise=False` → comportement original).

Smoke console (détecte le hasard cp1252 que pytest masque) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
python -c "from tools import lewis_survival_sweep as lss; lss.main_surprise(levels=(1.0,0.0), n_eval=2, R=1, seed=21)"
```
Expected : table + colonne surprise + verdict SANS `UnicodeEncodeError`.

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR098): colonne surprise dans _report + main_surprise

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Run direct (EXÉCUTION) — la mesure + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (bout-en-bout réduit, ~1 min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print('SMOKE:', lss.main_surprise(levels=(1.0,0.25,0.0), n_eval=3, R=1, seed=21, _return=True)['verdict'])" 2>/dev/null
```
Expected : table + verdict ∈ {TARIF=SURPRISE, OVERFLOW=RACINE, PAS LE BRAIN_COST}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr098-surprise-sweep"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main_surprise(seed=198)" 2>/dev/null
```
Expected : table survie × `ttc_surprise_scale` (4 niveaux, R=4, n_eval=8) + colonne surprise, JT, verdict. Provenance `results/lewis_surprise_sweep_198.json`.

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 098 selon la branche, et amorcer l'EDR 099 :
  - **TARIF=SURPRISE** → le brain_cost surprise-amplifié est le mur ; EDR 099 = clamper/réparer la surprise.
  - **OVERFLOW=RACINE** → `surprise_momentum` explose ; EDR 099 = fix numérique (clamp, écho 086).
  - **PAS LE BRAIN_COST** → drain ailleurs ; EDR 099 = décomposer le drain complet (suspect throw `:1122`).

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 variable `ttc_surprise_scale` (1.0..0.0), reste fixe → T1 (`_cfg` param, `SURPRISE_LEVELS`), T3 (`main_surprise` à `n_apex=0`/`_cfg(3)`). ✓
- §3 métrique survie médiane + JT + verdict 3 branches → T1 (`_verdict_surprise`), T3 (`_report` médianes+JT). ✓
- §3 instrumentation surprise (mean_abs_finite/max_finite/frac_nonfinite) → T2 (`_surprise_stats`, `collect_surprise`), T3 (colonne + frac vers verdict). ✓
- §4 params gelés → `SURPRISE_LEVELS`, `main_surprise` défauts R=4/n_eval=8, `n_apex=0`/`forage_payoff=3` fixes. ✓
- §5 extension DRY (`_cfg`+param, `collect_surprise`, `_verdict_surprise`, `main_surprise`, `_report`+colonne, `Harness("lewis_surprise_sweep")`) → T1/T2/T3. ✓
- §5 garde non-fini (frac_nonfinite → branche OVERFLOW) → T1 (`_verdict_surprise`), T2 (`_surprise_stats` np.isfinite). ✓
- §6 tests (cfg, verdict, measure collect, main) + non-régression 7 → T1/T2/T3 + steps non-régression. ✓
- §7 run direct → T4. ✓
- §8 `_disable_kuzu`, `seed_at` pairing, `n_apex=0` correctif 094, lecture read-only → T2/T3. ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes (seul le seed du run T4 est choisi à l'exécution, comme 093/094). ✓

**3. Type consistency :** `_cfg(forage_payoff, ttc_surprise_scale=None)` (T1) appelé par `main_surprise` avec `ttc_surprise_scale=lv` (T3). `_measure_survival(..., collect_surprise=False)` (T2) appelé par `main_surprise` avec `collect_surprise=True` (T3). `_surprise_stats(pool)->{mean_abs_finite,max_finite,frac_nonfinite}` (T2) consommé par `_report` (colonne) et agrégé en `frac_nf` passé à `_verdict_surprise(levels, medians, frac_nonfinite)` (T1). `main_surprise -> {levels,medians,jt,verdict,table}` (T3) consommé par le test. Cohérent. ✓
