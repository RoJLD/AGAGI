# EDR 099 — Décomposition du Drain Intrinsèque : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Instrumenter `world_1_stoneage.py:step()` (4 hooks opt-in) pour décomposer le drain énergétique par tick en 3 phases (brain / action / biologie), et étendre `tools/lewis_survival_sweep.py` pour mesurer et nommer le poste dominant du drain intrinsèque à `N_APEX=0`.

**Architecture:** Un champ config opt-in (`trace_energy_sinks`, défaut `False`) garde 4 captures d'énergie aux frontières de phase dans `step()` ; sans le flag, zéro changement de comportement. Le harnais (extension DRY du socle 093/094/098) active le flag, lit `agent["_e_phases"]`, agrège l'énergie/tick par phase, et mappe la phase dominante (>50%) vers un verdict.

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR099-Intrinsic-Drain-Decomposition-design.md`.

## Global Constraints

- **Mesure, pas de variable manipulée.** Condition gelée Lewis-vide : `N_APEX=0`, `forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`.
- **3 phases** : `brain = e0 − e_brain` ; `action = e_brain − e_prebio` ; `biologie = e_prebio − e_fin`. Elles télescopent vers le net `e0 − e_fin` (somme exacte). La phase **biologie peut être négative** (forage/approach-reward = source d'énergie) — ne PAS asserter la non-négativité.
- **Seuil de phase dominante : 50%** (gelé). Verdict ∈ `{"TARIF=THROW", "TARIF=BIOLOGIE", "TARIF=BRAIN", "DRAIN DIFFUS"}` (ASCII).
- **Hooks strictement gardés** par `getattr(self.config, "trace_energy_sinks", False)` (défaut `False`) → inertes pour 087-098 et sessions parallèles.
- **Non-régression** : les 11 tests existants (093/094/098) restent verts avec `trace_energy_sinks=False`.
- Reproductibilité : `_disable_kuzu()` ; `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ; `seed_at(s,0)` par ère.
- Normalisation : énergie/tick par agent = `_e_phases[phase] / age` (évite le biais survivants-longs).
- Commits path-scopés (2 fichiers prod partagés + harnais + tests) ; `git -C add` exact, jamais `git add -A` ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `src/environments/config.py` — +1 champ `trace_energy_sinks: bool = False`.
- **Modify:** `src/worlds/world_1_stoneage.py` — +4 hooks gardés dans `step()` (loop 1 brain, loop 2 biologie).
- **Modify:** `tools/lewis_survival_sweep.py` — +`_cfg` param, +`_verdict_drain`, +`_measure_drain`, +`_report_drain`, +`main_decompose`.
- **Modify:** `tests/sandbox/test_lewis_survival_sweep.py` — +tests harnais.
- **Create:** `tests/sandbox/test_energy_trace.py` — test des hooks world (inertie + traçage).

---

## Task 1: config flag + 4 hooks `step()` (instrumentation opt-in)

**Files:**
- Modify: `src/environments/config.py:55-57` (zone champs ttc)
- Modify: `src/worlds/world_1_stoneage.py` (loop 1 ~973-978, loop 2 ~1254-1255)
- Test: `tests/sandbox/test_energy_trace.py`

**Interfaces:**
- Produces : `WorldConfig.trace_energy_sinks: bool = False` ; quand `True`, chaque `agent` du monde porte après un `step()` un dict cumulatif `agent["_e_phases"] = {"brain": float, "action": float, "biologie": float}`.

- [ ] **Step 1: Write the failing test**

Créer `tests/sandbox/test_energy_trace.py` :

```python
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _mk_env(trace):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_energy_sinks = trace
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(4):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def test_trace_off_is_inert():
    env = _mk_env(trace=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool, "des agents doivent exister"
    assert all("_e_phases" not in ag for ag in pool)   # trace OFF -> aucun _e_phases


def test_trace_on_records_three_phases():
    env = _mk_env(trace=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_e_phases" in ag]
    assert traced, "des agents doivent porter _e_phases"
    for ag in traced:
        ph = ag["_e_phases"]
        assert set(ph) == {"brain", "action", "biologie"}
        assert all(np.isfinite(v) for v in ph.values())


def test_config_default_trace_off():
    assert WorldConfig().trace_energy_sinks is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_energy_trace.py -q`
Expected: FAIL (`AttributeError: ... 'trace_energy_sinks'` / pas de `_e_phases`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Dans `src/environments/config.py`, après la ligne `ttc_surprise_scale: float = 1.0` (l.57), ajouter :

```python
    trace_energy_sinks: bool = False   # EDR099 : decompose le drain par phase (opt-in, defaut OFF)
```

**3b.** Dans `src/worlds/world_1_stoneage.py`, **loop 1** (boucle `for i, agent in enumerate(self.agents):`, ~l.973). Remplacer :

```python
        for i, agent in enumerate(self.agents):
            surprise_val = float(agent["model"].surprise_momentum)
            surprise_scale = 1.0 + surprise_val * getattr(self.config, "ttc_surprise_scale", 1.0)
            
            brain_cost = base_cost * (1.0 + np.log2(1.0 + compute_spent[i])) * night_mult * surprise_scale
            agent["energy"] = max(0.0, agent["energy"] - float(brain_cost))
```

par (ajout de 2 captures gardées : `_e0` en entrée, `_e_brain` après le coût) :

```python
        for i, agent in enumerate(self.agents):
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e0"] = agent["energy"]                 # EDR099 : energie debut tick
            surprise_val = float(agent["model"].surprise_momentum)
            surprise_scale = 1.0 + surprise_val * getattr(self.config, "ttc_surprise_scale", 1.0)
            
            brain_cost = base_cost * (1.0 + np.log2(1.0 + compute_spent[i])) * night_mult * surprise_scale
            agent["energy"] = max(0.0, agent["energy"] - float(brain_cost))
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e_brain"] = agent["energy"]            # EDR099 : apres brain_cost
```

**3c.** Dans `src/worlds/world_1_stoneage.py`, **loop 2** au commentaire `# Biology` / `self._resolve_biology(agent, action, logits)` (~l.1254-1255). Remplacer :

```python
            # Biology
            self._resolve_biology(agent, action, logits)
```

par (capture `_e_prebio` avant, puis enregistrement cumulatif des 3 deltas après) :

```python
            # Biology
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e_prebio"] = agent["energy"]           # EDR099 : avant biologie
            self._resolve_biology(agent, action, logits)
            if getattr(self.config, "trace_energy_sinks", False):
                _e0 = agent.get("_e0", agent["energy"])
                _eb = agent.get("_e_brain", _e0)
                _ep = agent.get("_e_prebio", _eb)
                ph = agent.setdefault("_e_phases", {"brain": 0.0, "action": 0.0, "biologie": 0.0})
                ph["brain"] += _e0 - _eb                       # cout brain_cost
                ph["action"] += _eb - _ep                      # throw + signal + divers (loop2 avant biologie)
                ph["biologie"] += _ep - agent["energy"]        # metab+terrain+carry (peut etre <0 si forage)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_energy_trace.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
git -C "$WT" add src/environments/config.py src/worlds/world_1_stoneage.py tests/sandbox/test_energy_trace.py
git -C "$WT" commit -m "feat(EDR099): hooks opt-in decomposition energie par phase (trace_energy_sinks)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `_cfg(+trace)` + `_verdict_drain` + `_measure_drain`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_cfg` ~l.32-37 ; ajout fonctions)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `WorldConfig`, `_disable_kuzu`, `_setup_critical`, `_load_champions`, `_reproduce`, `seed_at`, `MutationConfig`, `Biosphere3D`, `MambaAgent`, `N_APEX/PREY_COUNT/NUM_AGENTS/MAX_TICKS`. La clé `agent["_e_phases"]` (Task 1).
- Produces : `_cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False) -> WorldConfig` ; `_verdict_drain(phases) -> str` ; `_measure_drain(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS) -> {"brain","action","biologie","net","n_agents"}` (moyennes énergie/tick).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_cfg_sets_trace_flag():
    assert lss._cfg(3, trace_energy_sinks=True).trace_energy_sinks is True
    assert lss._cfg(3).trace_energy_sinks is False


def test_verdict_drain_four_branches():
    # action > 50% du net -> throw
    assert lss._verdict_drain({"brain": 1, "action": 12, "biologie": 2, "net": 15}) == "TARIF=THROW"
    # biologie > 50% -> biologie
    assert lss._verdict_drain({"brain": 1, "action": 2, "biologie": 12, "net": 15}) == "TARIF=BIOLOGIE"
    # brain > 50% -> brain
    assert lss._verdict_drain({"brain": 12, "action": 2, "biologie": 1, "net": 15}) == "TARIF=BRAIN"
    # aucune > 50% -> diffus
    assert lss._verdict_drain({"brain": 5, "action": 6, "biologie": 4, "net": 15}) == "DRAIN DIFFUS"
    # net <= 0 -> diffus (garde)
    assert lss._verdict_drain({"brain": 0, "action": 0, "biologie": 0, "net": 0}) == "DRAIN DIFFUS"


def test_measure_drain_keys_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3, trace_energy_sinks=True)
    a = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    b = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert set(a) == {"brain", "action", "biologie", "net", "n_agents"}
    assert a["n_agents"] >= 1
    assert abs(a["net"] - (a["brain"] + a["action"] + a["biologie"])) < 1e-6   # net = somme (telescopage)
    assert a == b                                                              # seede -> reproductible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_trace_flag tests/sandbox/test_lewis_survival_sweep.py::test_verdict_drain_four_branches tests/sandbox/test_lewis_survival_sweep.py::test_measure_drain_keys_and_reproducible -q`
Expected: FAIL (`TypeError: _cfg() ... 'trace_energy_sinks'` puis `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

**3a.** Remplacer `_cfg` (l.32-37) — ajouter le param `trace_energy_sinks` (et conserver `ttc_surprise_scale` ajouté par 098) :

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

**3b.** Ajouter `_verdict_drain` (après `_verdict_surprise`) :

```python
def _verdict_drain(phases):
    """Mappe la decomposition (brain/action/biologie + net) -> 4 branches. La phase qui porte > 50% du
    drain net nomme le coupable ; aucune > 50% (ou net <= 0) -> drain diffus."""
    net = phases["net"]
    if net <= 0:
        return "DRAIN DIFFUS"
    shares = {k: phases[k] / net for k in ("brain", "action", "biologie")}
    top = max(shares, key=shares.get)
    if shares[top] <= 0.5:
        return "DRAIN DIFFUS"
    return {"action": "TARIF=THROW", "biologie": "TARIF=BIOLOGIE", "brain": "TARIF=BRAIN"}[top]
```

**3c.** Ajouter `_measure_drain` (après `_measure_survival`) :

```python
def _measure_drain(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
    """Decompose le drain energetique par phase (brain/action/biologie) a N_APEX=0. Lit agent['_e_phases']
    (pose par les hooks trace_energy_sinks) sur le pool, normalise par l'age (energie/tick), moyenne sur
    les agents. cfg DOIT avoir trace_energy_sinks=True."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)
    champs = _load_champions()
    brain, action, biologie = [], [], []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, 0.0, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
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
        for ag in pool:
            ph = ag.get("_e_phases")
            if not ph:
                continue
            age = max(1, int(ag.get("age", 1)))
            brain.append(ph["brain"] / age)
            action.append(ph["action"] / age)
            biologie.append(ph["biologie"] / age)
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    b, a_, bio = mean(brain), mean(action), mean(biologie)
    return {"brain": b, "action": a_, "biologie": bio, "net": b + a_ + bio, "n_agents": len(brain)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_trace_flag tests/sandbox/test_lewis_survival_sweep.py::test_verdict_drain_four_branches tests/sandbox/test_lewis_survival_sweep.py::test_measure_drain_keys_and_reproducible -q`
Expected: PASS (la mesure tourne une vraie sim réduite ~10-40 s).

- [ ] **Step 5: Run non-régression `_cfg` (093/098) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_payoff_metab_cap tests/sandbox/test_lewis_survival_sweep.py::test_cfg_sets_surprise_scale -q`
Expected: PASS (le nouveau param optionnel n'a pas cassé `_cfg`).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR099): _cfg +trace, _verdict_drain (4 branches), _measure_drain

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_report_drain` + `main_decompose`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajout `_report_drain`, `main_decompose`)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_measure_drain`, `_verdict_drain`, `Harness`, `_disable_kuzu`.
- Produces : `main_decompose(n_eval=8, R=4, seed=None, _return=False)`. Avec `_return=True`, renvoie `{"phases", "verdict", "R", "n_eval"}` où `phases = {"brain","action","biologie","net","n_agents"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_main_decompose_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    assert a["phases"] == b["phases"]                         # seede -> reproductible
    assert set(a["phases"]) == {"brain", "action", "biologie", "net", "n_agents"}
    assert a["verdict"] in {"TARIF=THROW", "TARIF=BIOLOGIE", "TARIF=BRAIN", "DRAIN DIFFUS"}
```

(NB : vraie simulation réduite ; ~30-90 s.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_decompose_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main_decompose'`).

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/lewis_survival_sweep.py` (après `main_surprise`, avant `if __name__`) :

```python
def _report_drain(h, agg, R, n_eval, _return):
    """Table des 3 phases (energie/tick + part %) + verdict + provenance. Tout ASCII (cp1252)."""
    verdict = _verdict_drain(agg)
    net = agg["net"]
    print(f"\n=== EDR099 decomposition drain a N_APEX=0 (energie/tick/agent) ===")
    for ph in ("brain", "action", "biologie"):
        pct = (100.0 * agg[ph] / net) if net else 0.0
        print(f"  {ph:<9} | {agg[ph]:7.2f}/tick | {pct:6.1f}% du net")
    print(f"  {'NET':<9} | {net:7.2f}/tick | n_agents={agg['n_agents']}")
    print("=== VERDICT (pre-enregistre, phase >50%) ===")
    print(f"  -> {verdict}")
    h.save({"phases": agg, "verdict": verdict, "R": R, "n_eval": n_eval})
    if _return:
        return {"phases": agg, "verdict": verdict, "R": R, "n_eval": n_eval}


def main_decompose(n_eval=8, R=4, seed=None, _return=False):
    """EDR 099 : decompose le drain intrinseque a N_APEX=0 (monde vide), forage_payoff=3, en 3 phases."""
    with Harness(seed=seed, name="lewis_drain_decompose", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR099 : decomposition drain N_APEX=0, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]
        agg = _measure_drain(_cfg(3, trace_energy_sinks=True), seeds, n_apex=0)
        return _report_drain(h, agg, R, n_eval, _return)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_decompose_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Run le fichier complet (non-régression 093/094/098) + smoke console + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py tests/sandbox/test_energy_trace.py -q`
Expected: PASS (11 de 093/094/098 + 6 de 099 = 17 tests). Le traçage est OFF partout sauf `_measure_drain`/`main_decompose`, donc 093/094/098 inchangés.

Smoke console (cp1252) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
python -c "from tools import lewis_survival_sweep as lss; lss.main_decompose(n_eval=2, R=1, seed=21)"
```
Expected : table 3 phases + verdict SANS `UnicodeEncodeError`.

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR099): _report_drain + main_decompose (table 3 phases + verdict)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Run direct (EXÉCUTION) — la mesure + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (réduit, ~1 min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print('SMOKE:', lss.main_decompose(n_eval=3, R=1, seed=21, _return=True)['verdict'])" 2>/dev/null
```
Expected : table 3 phases + verdict ∈ {TARIF=THROW, TARIF=BIOLOGIE, TARIF=BRAIN, DRAIN DIFFUS}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr099-drain-decompose"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main_decompose(seed=199)" 2>/dev/null
```
Expected : table brain/action/biologie (énergie/tick + %), net, verdict. Provenance `results/lewis_drain_decompose_199.json`.

**Sanity check à vérifier au run :** `net` doit être de l'ordre de ~10-16/tick (cohérent avec le drain qui tue au tick 5 depuis E=80). Si `net` est très petit, les hooks ne capturent pas le bon intervalle → investiguer avant de conclure.

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 099 selon la branche, et amorcer l'EDR 100 :
  - **TARIF=THROW** → le throw (−10/−5) est le poste dominant ; EDR 100 = paramétrer/baisser le coût throw, re-mesurer la survie.
  - **TARIF=BIOLOGIE** → métab/terrain/carry cumulés ; rééquilibrer le métabolisme de Lewis.
  - **TARIF=BRAIN** → contredit 098 ; ré-investiguer le `brain_cost`/compute (flag).
  - **DRAIN DIFFUS** → pas de poste unique > 50% ; lever exige plusieurs ajustements (lister les parts).

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 mesure à N_APEX=0, condition gelée → T1 (hooks), T2/T3 (`_measure_drain`/`main_decompose` à `_cfg(3, trace=True)`, `n_apex=0`). ✓
- §3 3 phases (brain/action/biologie, télescopage) → T1 (hooks calculent les deltas), T2 (`_measure_drain` agrège, test télescopage). ✓
- §3 verdict 4 branches seuil 50% → T2 (`_verdict_drain`), T3 (`_report_drain`). ✓
- §4 params gelés → `main_decompose` défauts R=4/n_eval=8, `n_apex=0`/`forage_payoff=3`/trace=True. ✓
- §5 config flag + 4 hooks + harnais DRY → T1 (config+world), T2/T3 (harnais). ✓
- §5 inertie défaut OFF → T1 (`test_trace_off_is_inert`), non-régression 11 tests (T2/T3 steps). ✓
- §6 tests (config, inertie, traçage, verdict, measure, main) → T1/T2/T3. ✓
- §7 run direct → T4. ✓
- §8 hooks gardés, N_APEX=0 correctif 094, seed_at, normalisation /age → T1 (gardes), T2 (`/age`). ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes (seul le seed du run T4 choisi à l'exécution). ✓

**3. Type consistency :** `_cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False)` (T2) appelé par `main_decompose` avec `trace_energy_sinks=True` (T3). `agent["_e_phases"]={"brain","action","biologie"}` (T1) lu par `_measure_drain` (T2). `_measure_drain -> {brain,action,biologie,net,n_agents}` (T2) consommé par `_verdict_drain` (T2) et `_report_drain` (T3). `main_decompose -> {phases,verdict,R,n_eval}` (T3) consommé par le test. Cohérent. ✓
