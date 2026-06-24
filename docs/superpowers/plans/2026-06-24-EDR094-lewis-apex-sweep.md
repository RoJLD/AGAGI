# EDR 094 — Sweep Densité d'Apex : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Généraliser `tools/lewis_survival_sweep.py` (EDR 093, mergé) pour balayer `N_APEX` (densité d'apex) et mesurer la survie médiane des champions stoneage en Lewis à létalité 0 — localiser (ou réfuter) un barreau survivable par la densité, en isolant le déclencheur de la dépense.

**Architecture:** Extension DRY du harnais 093 mergé. Trois ajouts rétro-compatibles dans le même fichier : (1) `_verdict_apex` + `APEX_LEVELS` ; (2) un paramètre `n_apex` à `_measure_survival` ; (3) `_report` paramétré par `(knob, verdict_fn)` + un driver `main_apex`. Le `main` de 093 (sweep forage) reste fonctionnellement inchangé (non-régression).

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR094-Lewis-Apex-Density-Sweep-design.md`.

## Global Constraints

- **1 variable** : `N_APEX` ∈ `(12, 9, 6, 3, 0)`. Tout le reste fixe.
- Fixes gelés : `forage_payoff=3` (inerte par 093), `base_metabolism=0.25`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`, gate survie `120`, `max_population=150` (défensif).
- **Pas d'évolution, pas de langage** (`use_ref_head=False`, `decode_act=False`, champions répliqués via `_reproduce`).
- **Zéro modification du code de production** : `N_APEX` est déjà un paramètre de `_setup_critical(env, leurre_frac, n_apex=...)`. Seul `tools/lewis_survival_sweep.py` + son test changent.
- Reproductibilité : `_disable_kuzu()` avant toute création de monde ; `Harness(with_db=False)` ; `seed_at(seed, 0)` par ère ; mêmes seeds entre niveaux (appariement).
- Survie = **âge par agent** (`agent["age"]`) sur le pool (`env.agents + env.dead_agents`), médiane par niveau.
- Cause de mort : `energy <= 0` = famine ; `hp <= 0 and energy > 0` = combat.
- **Non-régression** : les 4 tests de 093 (`test_lewis_survival_sweep.py`) restent verts.
- Commits path-scopés (sessions parallèles) ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `tools/lewis_survival_sweep.py` — ajout de `APEX_LEVELS`, `_verdict_apex`, param `n_apex` à `_measure_survival`, généralisation de `_report`, ajout de `main_apex`. Aucune suppression ; `_cfg`, `_verdict`, `main` conservés.
- **Modify:** `tests/sandbox/test_lewis_survival_sweep.py` — ajout de 3 tests (verdict_apex, measure n_apex câblé, main_apex). Les 4 tests existants restent.
- **Untouched:** tout le reste (code de prod inclus).

---

## Task 1: `APEX_LEVELS` + `_verdict_apex` (helper pur)

**Files:**
- Modify: `tools/lewis_survival_sweep.py`
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `GATE` (déjà défini, `120.0`).
- Produces : `APEX_LEVELS = (12, 9, 6, 3, 0)` ; `_verdict_apex(levels, medians, gate=GATE) -> str` (∈ `{"BARREAU TROUVE", "RUNG DEGENERE", "MUR INTRINSEQUE"}`).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_verdict_apex_three_branches():
    levels = (12, 9, 6, 3, 0)
    # survie franchie a un N_APEX > 0 (ici 6 et 3) -> barreau trouve
    assert lss._verdict_apex(levels, [10, 20, 130, 200, 260]) == "BARREAU TROUVE"
    # survie franchie SEULEMENT a N_APEX = 0 -> rung degenere
    assert lss._verdict_apex(levels, [10, 20, 40, 90, 150]) == "RUNG DEGENERE"
    # aucun niveau ne franchit (meme 0) -> mur intrinseque
    assert lss._verdict_apex(levels, [5, 8, 10, 30, 60]) == "MUR INTRINSEQUE"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_apex(levels, [5, 8, 10, 30, 120]) == "MUR INTRINSEQUE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_verdict_apex_three_branches -q`
Expected: FAIL (`AttributeError: ... '_verdict_apex'`).

- [ ] **Step 3: Write minimal implementation**

Dans `tools/lewis_survival_sweep.py`, ajouter `APEX_LEVELS` près des autres constantes (après la ligne `CHEAP_MAX = 24`) :

```python
APEX_LEVELS = (12, 9, 6, 3, 0)     # N_APEX balaye : de la densite 093 (12) au Lewis vide (0)
```

Et ajouter la fonction `_verdict_apex` (après `_verdict`) :

```python
def _verdict_apex(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau de densite d'apex) -> 3 branches pre-enregistrees.
    Un N_APEX > 0 franchit le gate -> barreau trouve (densite reduite survivable) ; seul N_APEX=0
    franchit -> rung degenere (survie uniquement dans un Lewis vide) ; aucun -> mur intrinseque
    (le drain n'est pas l'environnement)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "MUR INTRINSEQUE"
    return "BARREAU TROUVE" if max(crossed) > 0 else "RUNG DEGENERE"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_verdict_apex_three_branches -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR094): APEX_LEVELS + _verdict_apex (3 branches densite)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: paramètre `n_apex` dans `_measure_survival`

**Files:**
- Modify: `tools/lewis_survival_sweep.py:39-72` (`_measure_survival`)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_disable_kuzu` (déjà importés/définis), `_setup_critical` (déjà importé).
- Produces : `_measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS) -> {"ticks", "famine", "combat", "kills"}`. Le `n_apex` est threadé dans `_setup_critical(env, leurre_frac, n_apex=n_apex)`. **Rétro-compatible** : le défaut `N_APEX` reproduit le comportement actuel.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_measure_survival_n_apex_wired_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3)
    a = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    a2 = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert set(a) == {"ticks", "famine", "combat", "kills"}
    assert a == a2                              # seede -> reproductible
    # n_apex=0 -> AUCUN apex instancie -> impossible de tuer un Mammouth -> kills tous nuls.
    # Assertion science-independante (ne depend PAS de l'issue de survie) : prouve le cablage de n_apex.
    assert sum(a["kills"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_n_apex_wired_and_reproducible -q`
Expected: FAIL (`TypeError: _measure_survival() got an unexpected keyword argument 'n_apex'`).

- [ ] **Step 3: Write minimal implementation**

Modifier la signature et l'appel à `_setup_critical` dans `_measure_survival`.

Remplacer la ligne 39 (signature) :

```python
def _measure_survival(cfg, seeds, leurre_frac=0.0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
```

par :

```python
def _measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
```

Et remplacer la ligne 51 (l'appel) :

```python
        _setup_critical(env, leurre_frac, n_apex=N_APEX)
```

par :

```python
        _setup_critical(env, leurre_frac, n_apex=n_apex)
```

(Aucune autre ligne ne change. Le reste de la fonction est inchangé.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_n_apex_wired_and_reproducible -q`
Expected: PASS (la simulation réduite tourne ~10-40 s).

- [ ] **Step 5: Run non-regression (093 measure test) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_keys_and_reproducible -q`
Expected: PASS (le défaut `n_apex=N_APEX` préserve le comportement 093).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR094): parametre n_apex dans _measure_survival (retro-compatible)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_report` paramétré + `main_apex`

**Files:**
- Modify: `tools/lewis_survival_sweep.py:85-120` (`_report`, `main`) + ajout `main_apex`
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_measure_survival` (avec `n_apex`), `_verdict`, `_verdict_apex`, `APEX_LEVELS`, `st.jonckheere_terpstra`, `Harness`, `_disable_kuzu`.
- Produces : `_report(h, levels, groups, R, n_eval, _return, knob="forage_payoff", verdict_fn=_verdict)` (généralisé) ; `main_apex(levels=APEX_LEVELS, n_eval=8, R=4, seed=None, _return=False)`. Avec `_return=True`, `main_apex` renvoie `{"levels", "medians", "jt", "verdict", "table"}` où `table[N_APEX]` a les clés `{"median","famine","combat","mean_kills","n"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_main_apex_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_apex(levels=(12, 0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_apex(levels=(12, 0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [12, 0]
    assert set(a["table"][12]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"BARREAU TROUVE", "RUNG DEGENERE", "MUR INTRINSEQUE"}
    # le niveau N_APEX=0 ne peut produire aucun kill (aucun apex)
    assert a["table"][0]["mean_kills"] == 0
```

(NB : tourne une vraie simulation réduite ; ~30-90 s.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_apex_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main_apex'`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Généraliser `_report`. Remplacer la définition actuelle (lignes 85-106) :

```python
def _report(h, levels, groups, R, n_eval, _return):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    verdict = _verdict(levels, medians)
    table = {}
    print(f"\n=== EDR093 sweep forage_payoff : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        table[lv] = {"median": med, "famine": g["famine"], "combat": g["combat"],
                     "mean_kills": mk, "n": n}
        print(f"  payoff={lv:<3} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
              f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"levels": list(levels), "R": R, "n_eval": n_eval, "medians": medians,
            "jt": jt, "verdict": verdict, "table": {str(k): v for k, v in table.items()}})
    if _return:
        return {"levels": list(levels), "medians": medians, "jt": jt,
                "verdict": verdict, "table": table}
```

par (ajout des paramètres `knob` et `verdict_fn`, utilisés dans l'impression et le verdict ; tout ASCII pour cp1252) :

```python
def _report(h, levels, groups, R, n_eval, _return, knob="forage_payoff", verdict_fn=_verdict):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance.
    knob = nom du parametre balaye (impression/provenance) ; verdict_fn = mapping medianes->verdict."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    verdict = verdict_fn(levels, medians)
    table = {}
    print(f"\n=== EDR sweep {knob} : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        table[lv] = {"median": med, "famine": g["famine"], "combat": g["combat"],
                     "mean_kills": mk, "n": n}
        print(f"  {knob}={lv:<3} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
              f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": knob, "levels": list(levels), "R": R, "n_eval": n_eval, "medians": medians,
            "jt": jt, "verdict": verdict, "table": {str(k): v for k, v in table.items()}})
    if _return:
        return {"levels": list(levels), "medians": medians, "jt": jt,
                "verdict": verdict, "table": table}
```

(Le `main` de 093 appelle `_report(h, levels, groups, R, n_eval, _return)` sans nommer `knob`/`verdict_fn` → défauts `"forage_payoff"`/`_verdict` → comportement préservé. Le dict retourné est **identique** ; seuls le label console et un champ `knob` ajouté à la provenance changent — sans incidence sur les tests 093.)

**3b.** Ajouter `main_apex` (après `main`, avant le bloc `if __name__`) :

```python
def main_apex(levels=APEX_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 094 : sweep N_APEX (densite d'apex) a forage_payoff=3 fixe, Lewis letalite 0."""
    with Harness(seed=seed, name="lewis_apex_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR094 : sweep N_APEX={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux N_APEX")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3), seeds, n_apex=lv))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="N_APEX", verdict_fn=_verdict_apex)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_apex_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Run the FULL file (non-régression 093) + smoke console + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: PASS (7 tests : 4 de 093 + 3 de 094).

Smoke console (détecte le hasard cp1252 que pytest masque) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
python -c "from tools import lewis_survival_sweep as lss; lss.main_apex(levels=(12,0), n_eval=2, R=1, seed=21)"
```
Expected : imprime la table + verdict SANS `UnicodeEncodeError`.

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR094): _report parametre (knob, verdict_fn) + main_apex

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Run direct (EXÉCUTION) — la mesure + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (bout-en-bout réduit, ~1 min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print('SMOKE:', lss.main_apex(levels=(12,6,0), n_eval=3, R=1, seed=21, _return=True)['verdict'])" 2>/dev/null
```
Expected : table + verdict ∈ {BARREAU TROUVE, RUNG DEGENERE, MUR INTRINSEQUE}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr094-apex-sweep"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main_apex(seed=194)" 2>/dev/null
```
Expected : table survie × `N_APEX` (5 niveaux, R=4, n_eval=8), JT, verdict. Provenance `results/lewis_apex_sweep_194.json`.

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 094 selon la branche :
  - **BARREAU TROUVE** → rung survivable à `N_APEX=X>0` ; base d'un curriculum de densité (ramper vers 12).
  - **RUNG DEGENERE** → survie seulement à `N_APEX=0` ; les apex sont un mur absolu.
  - **MUR INTRINSEQUE** → famine même sans apex ; pivot vers coût d'action (−10) / métabolisme.

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 variable `N_APEX` (12..0), reste fixe → T1 (`APEX_LEVELS`), T2 (`n_apex` câblé), T3 (`main_apex` à `_cfg(3)` fixe). ✓
- §3 métrique survie médiane + JT + verdict 3 branches → T1 (`_verdict_apex`), T3 (`_report` médianes+JT). ✓
- §3 sous-produits famine/combat + kills + signal `kills=0` à N_APEX bas → T2 (assertion `sum(kills)==0` à 0), T3 (table + assertion `mean_kills==0` à 0). ✓
- §4 params gelés → constantes (`APEX_LEVELS`, `GATE`), `main_apex` défauts R=4/n_eval=8, `forage_payoff=3` fixe. ✓
- §5 généralisation DRY (param `n_apex`, `_report(knob, verdict_fn)`, `main_apex`, `Harness("lewis_apex_sweep")`) → T2/T3. ✓
- §5 pairing seeds entre niveaux → T3 (`seeds` indépendant du niveau). ✓
- §6 tests (verdict_apex, measure n_apex câblé, main_apex, non-régression 093) → T1/T2/T3 + steps non-régression. ✓
- §7 run direct → T4. ✓
- §8 `N_APEX=0` valide (forage pur), `_disable_kuzu` avant monde → T2/T3 (déjà dans `_measure_survival`/`main_apex`). ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes (seul le seed du run T4 est choisi à l'exécution, comme 093). ✓

**3. Type consistency :** `_measure_survival(..., n_apex=N_APEX, ...)` (T2) appelé par `main_apex` avec `n_apex=lv` (T3). `_verdict_apex(levels, medians)` (T1) passé comme `verdict_fn` à `_report` (T3). `_report(..., knob, verdict_fn)` (T3) appelé par `main` (défauts) et `main_apex` (`knob="N_APEX"`, `verdict_fn=_verdict_apex`). `main_apex -> {levels, medians, jt, verdict, table}` (T3) consommé par le test. Cohérent. ✓
