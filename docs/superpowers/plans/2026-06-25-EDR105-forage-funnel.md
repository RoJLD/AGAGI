# EDR 105 — Décomposition de l'entonnoir de forage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Instrumenter et mesurer l'entonnoir de forage (APPROCHE → CAPTURE → REVENU) des champions stoneage en Lewis vidé d'apex, pour localiser l'étage où l'acquisition casse.

**Architecture:** Trois hooks opt-in `trace_forage` (inertes quand off) posent des compteurs d'entonnoir sur l'agent dans `world_1_stoneage.py`. Une fonction de mesure `_measure_forage` lit ces compteurs + les buckets de drain de l'instrument `trace_energy_sinks` co-activé (pour un `drain_t` forage-indépendant, anti-circularité) et agrège par agent. Un verdict cascade nomme le premier étage cassé.

**Tech Stack:** Python, numpy, `src/seed_ai/exp_stats.py`, harnais `tools/lewis_survival_sweep.py`, pytest.

## Global Constraints

- **Commandement 15 (1 variable)** : la seule variable balayée est `base_metabolism ∈ {0.0, 0.25}`. `trace_forage` et `trace_energy_sinks` sont des **instruments inertes**, pas des variables.
- **Inertie stricte** : `trace_forage=False` (défaut) → comportement **byte-identique** à l'actuel (aucune clé `_forage_*` posée). Protège les sessions parallèles.
- **ASCII only** dans tout `print`/littéral exécuté (Windows cp1252 : pas de `−`, `→`, `×`, accents dans les chaînes imprimées).
- **Reproductibilité** : `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; `memory_retriever.stop()+clear()` ; mêmes seeds appariés entre niveaux.
- **N_APEX=0**, `forage_payoff=3`, `PREY_COUNT=15`, `NUM_AGENTS=24`, `max_ticks=150`.
- **Verdict porté par metab=0** ; metab=0.25 rapporté en contraste seulement.

---

## File Structure

- `src/environments/config.py` — ajoute le champ `trace_forage: bool = False`.
- `src/worlds/world_1_stoneage.py` — 3 hooks `trace_forage` (min_dist, contacts, income) dans `_resolve_biology` et la résolution d'attaque.
- `tools/lewis_survival_sweep.py` — param `_cfg(trace_forage=…)` ; `_measure_forage` ; `_verdict_forage` ; `_report_forage` ; `main_forage`.
- `tests/sandbox/test_edr105_forage_funnel.py` — tests (calqués sur `tests/sandbox/test_energy_trace.py`, même répertoire que les tests EDR existants).

---

## Task 1: Hooks `trace_forage` inertes (instrumentation de l'entonnoir)

**Files:**
- Modify: `src/environments/config.py:58`
- Modify: `src/worlds/world_1_stoneage.py` (3 insertions : ~l.653, ~l.686, ~l.745)
- Test: `tests/sandbox/test_edr105_forage_funnel.py`

**Interfaces:**
- Consumes: rien (premier task).
- Produces: quand `cfg.trace_forage=True`, chaque agent vivant porte après quelques `env.step()` :
  - `agent["_forage_min_dist"]` (float, distance Manhattan min jamais atteinte vers la proie la plus proche),
  - `agent["_forage_contacts"]` (int, nb d'attaques co-localisées),
  - `agent["_forage_income"]` (float, énergie brute extraite des proies régulières).
  Quand `trace_forage=False` : aucune de ces clés n'est posée.

- [ ] **Step 1: Write the failing test (config default + inertie)**

Créer `tests/sandbox/test_edr105_forage_funnel.py` :

```python
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _mk_env(trace_forage):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_forage = trace_forage
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(4):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def test_config_default_trace_forage_off():
    assert WorldConfig().trace_forage is False


def test_trace_forage_off_is_inert():
    env = _mk_env(trace_forage=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool, "des agents doivent exister"
    for ag in pool:
        assert "_forage_min_dist" not in ag
        assert "_forage_contacts" not in ag
        assert "_forage_income" not in ag


def test_trace_forage_on_records_min_dist():
    env = _mk_env(trace_forage=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_forage_min_dist" in ag]
    assert traced, "des agents doivent porter _forage_min_dist (proies presentes)"
    for ag in traced:
        assert np.isfinite(ag["_forage_min_dist"])
        assert ag["_forage_min_dist"] >= 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -v`
Expected: `test_config_default_trace_forage_off` FAILS (`AttributeError: 'WorldConfig' object has no attribute 'trace_forage'`) ; `test_trace_forage_on_records_min_dist` FAILS (aucun `_forage_min_dist`).

- [ ] **Step 3: Add the config field**

Dans `src/environments/config.py`, après la ligne 58 (`trace_energy_sinks: bool = False ...`), ajouter :

```python
    trace_forage: bool = False         # EDR105 : decompose l'entonnoir de forage (opt-in, defaut OFF)
```

- [ ] **Step 4: Add hook A (min_dist) in `_resolve_biology`**

Dans `src/worlds/world_1_stoneage.py`, localiser dans `_resolve_biology` (~l.653) :

```python
            agent["energy"] += approach_reward(agent.get("last_prey_dist", d), d, self.scaffold_eps, lam)
            agent["last_prey_dist"] = d
```

Insérer juste après `agent["last_prey_dist"] = d` (même indentation, dans le bloc `if self.preys:`) :

```python
            if getattr(self.config, "trace_forage", False):
                agent["_forage_min_dist"] = min(agent.get("_forage_min_dist", d), d)
```

- [ ] **Step 5: Add hook B (contacts) at the attack resolution**

Localiser (~l.685) :

```python
        attacked_prey = next((p for p in self.preys if agent["x"] == p["x"] and agent["y"] == p["y"]), None)
        if attacked_prey:
            cfg_atk = self.config.preys.get(attacked_prey["type"], None)
```

Insérer entre `if attacked_prey:` et `cfg_atk = ...` :

```python
        if attacked_prey:
            if getattr(self.config, "trace_forage", False):
                agent["_forage_contacts"] = agent.get("_forage_contacts", 0) + 1
            cfg_atk = self.config.preys.get(attacked_prey["type"], None)
```

- [ ] **Step 6: Add hook C (income) in the regular-prey reward branch**

Localiser le `else` de la récompense régulière (~l.743) — c'est la branche NON-apex/NON-leurre :

```python
                else:
                    agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + reward)
                    agent["preys_eaten"] += 1
                self.preys.remove(attacked_prey)
```

Insérer après `agent["preys_eaten"] += 1` (dans le `else`, avant `self.preys.remove`) :

```python
                else:
                    agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + reward)
                    agent["preys_eaten"] += 1
                    if getattr(self.config, "trace_forage", False):
                        agent["_forage_income"] = agent.get("_forage_income", 0.0) + reward
                self.preys.remove(attacked_prey)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -v`
Expected: les 3 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tests/sandbox/test_edr105_forage_funnel.py
git commit -m "feat(EDR105): hooks trace_forage inertes (min_dist/contacts/income)"
```

---

## Task 2: `_cfg(trace_forage)` + `_measure_forage`

**Files:**
- Modify: `tools/lewis_survival_sweep.py:34-42` (signature `_cfg`)
- Modify: `tools/lewis_survival_sweep.py` (nouvelle fonction `_measure_forage` après `_measure_drain`)
- Test: `tests/sandbox/test_edr105_forage_funnel.py`

**Interfaces:**
- Consumes: les compteurs `_forage_*` du Task 1 ; les buckets `_e_phases` (`brain`/`action`/`biologie`/`mouvement`) et `_e_bio` (`metab`/`terrain`/`carry`/`autres`) de l'instrument `trace_energy_sinks` existant.
- Produces: `_measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150)` renvoyant un dict :
  `{"p_reach": float, "p_cap": float, "income_t": float, "drain_t": float, "mean_captures": float, "mean_contacts": float, "mean_min_dist": float, "n_agents": int}`.
  `drain_t` = médiane sur agents de `(bio_metab+bio_terrain+bio_carry+brain+action+mouvement)/age` (coût structurel forage-indépendant, le revenu vit dans `bio_autres` et n'est jamais sommé). `income_t` = médiane de `_forage_income/age`.

- [ ] **Step 1: Write the failing test (smoke de mesure)**

Ajouter à `tests/sandbox/test_edr105_forage_funnel.py` :

```python
from tools.lewis_survival_sweep import _cfg, _measure_forage


def test_cfg_trace_forage_param():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    assert cfg.trace_forage is True
    assert cfg.trace_energy_sinks is True
    assert cfg.base_metabolism == 0.0


def test_measure_forage_smoke():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    agg = _measure_forage(cfg, [105, 106], n_apex=0, max_ticks=20)
    assert agg["n_agents"] > 0
    assert 0.0 <= agg["p_reach"] <= 1.0
    assert 0.0 <= agg["p_cap"] <= 1.0
    assert agg["income_t"] >= 0.0
    assert agg["drain_t"] >= 0.0
    assert np.isfinite(agg["mean_min_dist"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -k "trace_forage_param or measure_forage_smoke" -v`
Expected: FAIL (`_cfg` n'accepte pas `trace_forage` ; `_measure_forage` n'existe pas).

- [ ] **Step 3: Add the `trace_forage` param to `_cfg`**

Dans `tools/lewis_survival_sweep.py`, modifier la signature et le corps de `_cfg` (l.34-42) :

```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB,
         trace_forage=False):
    cfg = WorldConfig()
    cfg.base_metabolism = float(base_metabolism)             # EDR101 : sweepable (defaut METAB=0.25)
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098
    cfg.trace_energy_sinks = bool(trace_energy_sinks)         # EDR099
    cfg.trace_forage = bool(trace_forage)                     # EDR105
    return cfg
```

- [ ] **Step 4: Add `_measure_forage`**

Ajouter dans `tools/lewis_survival_sweep.py` juste après la fonction `_measure_drain` (après sa ligne `return {...}`) :

```python
def _measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150):
    """EDR105 : decompose l'entonnoir de forage a N_APEX=0. Lit les compteurs _forage_* (poses par
    trace_forage) + preys_eaten + les buckets de pure depense _e_phases/_e_bio (trace_energy_sinks
    co-active) sur le pool, agrege par agent. cfg DOIT avoir trace_forage=True ET trace_energy_sinks=True.
    drain_t = cout structurel FORAGE-INDEPENDANT/tick (le revenu vit dans _e_bio['autres'], jamais somme
    ici) -> la comparaison income_t<drain_t est non circulaire (cf. spec EDR105)."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)
    champs = _load_champions()
    reached, captured_if_reached = [], []
    income_t, drain_t, captures, contacts, min_dists = [], [], [], [], []
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
            bio = ag.get("_e_bio")
            if not ph or not bio:
                continue
            age = max(1, int(ag.get("age", 1)))
            md = float(ag.get("_forage_min_dist", 9999.0))
            inc = float(ag.get("_forage_income", 0.0))
            structural = (bio["metab"] + bio["terrain"] + bio["carry"]
                          + ph["brain"] + ph["action"] + ph["mouvement"])
            is_reached = md <= 0
            reached.append(1.0 if is_reached else 0.0)
            if is_reached:
                captured_if_reached.append(1.0 if int(ag.get("preys_eaten", 0)) >= 1 else 0.0)
            income_t.append(inc / age)
            drain_t.append(structural / age)
            captures.append(float(ag.get("preys_eaten", 0)))
            contacts.append(float(ag.get("_forage_contacts", 0)))
            min_dists.append(md)
    med = lambda xs: float(np.median(xs)) if xs else 0.0
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    return {"p_reach": mean(reached),
            "p_cap": mean(captured_if_reached),
            "income_t": med(income_t),
            "drain_t": med(drain_t),
            "mean_captures": mean(captures),
            "mean_contacts": mean(contacts),
            "mean_min_dist": mean(min_dists),
            "n_agents": len(income_t)}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -k "trace_forage_param or measure_forage_smoke" -v`
Expected: les 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr105_forage_funnel.py
git commit -m "feat(EDR105): _cfg(trace_forage) + _measure_forage (entonnoir, drain structurel)"
```

---

## Task 3: `_verdict_forage` + `_report_forage` + `main_forage`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (3 fonctions après `_measure_forage` / dans la zone des `_report`/`main`)
- Test: `tests/sandbox/test_edr105_forage_funnel.py`

**Interfaces:**
- Consumes: le dict de `_measure_forage` (Task 2).
- Produces:
  - `_verdict_forage(agg)` → une des 4 chaînes : `"GOULOT=APPROCHE"`, `"GOULOT=CAPTURE"`, `"GOULOT=REVENU"`, `"FORAGE SUFFISANT"`.
  - `_report_forage(h, aggs, R, n_eval, _return)` où `aggs` est une liste de `(metab_level, agg)` ; imprime la table ASCII, applique `_verdict_forage` sur l'agg de `metab==0.0`, sauve via `h.save`.
  - `main_forage(metab_levels=(0.0, 0.25), n_eval=8, R=4, seed=None, _return=False)`.

- [ ] **Step 1: Write the failing test (4 branches du verdict)**

Ajouter à `tests/sandbox/test_edr105_forage_funnel.py` :

```python
from tools.lewis_survival_sweep import _verdict_forage


def _agg(p_reach, p_cap, income_t, drain_t):
    return {"p_reach": p_reach, "p_cap": p_cap, "income_t": income_t, "drain_t": drain_t}


def test_verdict_forage_approche():
    assert _verdict_forage(_agg(0.3, 1.0, 5.0, 1.0)) == "GOULOT=APPROCHE"


def test_verdict_forage_capture():
    assert _verdict_forage(_agg(0.9, 0.3, 5.0, 1.0)) == "GOULOT=CAPTURE"


def test_verdict_forage_revenu():
    assert _verdict_forage(_agg(0.9, 0.9, 0.5, 1.0)) == "GOULOT=REVENU"


def test_verdict_forage_suffisant():
    assert _verdict_forage(_agg(0.9, 0.9, 2.0, 1.0)) == "FORAGE SUFFISANT"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -k verdict_forage -v`
Expected: FAIL (`_verdict_forage` n'existe pas).

- [ ] **Step 3: Add `_verdict_forage`**

Ajouter dans `tools/lewis_survival_sweep.py` (zone des `_verdict_*`, p.ex. après `_verdict_bio`) :

```python
def _verdict_forage(agg):
    """Cascade 'premier etage casse' de l'entonnoir de forage (seuils geles, cf. spec EDR105). Evalue
    sur l'agg de metab=0. p_reach<0.5 -> APPROCHE (navigation) ; sinon p_cap<0.5 -> CAPTURE (atteint
    mais ne tue pas) ; sinon income_t<drain_t -> REVENU (tue mais ne couvre pas le cout structurel) ;
    sinon FORAGE SUFFISANT (l'entonnoir tient, le mur est ailleurs)."""
    if agg["p_reach"] < 0.5:
        return "GOULOT=APPROCHE"
    if agg["p_cap"] < 0.5:
        return "GOULOT=CAPTURE"
    if agg["income_t"] < agg["drain_t"]:
        return "GOULOT=REVENU"
    return "FORAGE SUFFISANT"
```

- [ ] **Step 4: Run the verdict tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -k verdict_forage -v`
Expected: les 4 tests PASS.

- [ ] **Step 5: Add `_report_forage` and `main_forage`**

Ajouter dans `tools/lewis_survival_sweep.py` (après `main_decompose`, avant le `if __name__`) :

```python
def _report_forage(h, aggs, R, n_eval, _return):
    """Table entonnoir (1 ligne/niveau de metab) + verdict (porte par metab=0) + provenance.
    Tout ASCII (cp1252). aggs = liste de (metab_level, agg)."""
    agg0 = next((a for lv, a in aggs if lv == 0.0), aggs[0][1])
    verdict = _verdict_forage(agg0)
    print("\n=== EDR105 entonnoir de forage a N_APEX=0 (verdict sur metab=0) ===")
    print("  metab | p_reach p_cap | income/t drain/t | captures contacts min_dist | n")
    for lv, a in aggs:
        print(f"  {lv:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['income_t']:8.3f} {a['drain_t']:7.3f} | "
              f"{a['mean_captures']:8.2f} {a['mean_contacts']:8.2f} {a['mean_min_dist']:8.2f} | "
              f"{a['n_agents']}")
    print("=== VERDICT (pre-enregistre, cascade premier etage casse) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "base_metab", "metab_levels": [lv for lv, _ in aggs], "R": R, "n_eval": n_eval,
            "verdict": verdict, "table": {str(lv): a for lv, a in aggs}})
    if _return:
        return {"verdict": verdict, "table": {lv: a for lv, a in aggs}, "R": R, "n_eval": n_eval}


def main_forage(metab_levels=(0.0, 0.25), n_eval=8, R=4, seed=None, _return=False):
    """EDR 105 : decompose l'entonnoir de forage (APPROCHE/CAPTURE/REVENU) a N_APEX=0, forage_payoff=3.
    Variable = base_metabolism ; metab=0 porte le verdict (acquisition isolee), 0.25 en contraste.
    Co-active trace_forage ET trace_energy_sinks (instruments inertes, pas des variables)."""
    with Harness(seed=seed, name="lewis_forage_funnel", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR105 : entonnoir forage metab={metab_levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(metab_levels), label="niveaux base_metab")
        aggs = []
        for lv in metab_levels:
            cfg = _cfg(3, base_metabolism=lv, trace_energy_sinks=True, trace_forage=True)
            aggs.append((lv, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
            prog.update()
        return _report_forage(h, aggs, R, n_eval, _return)
```

- [ ] **Step 6: Run the full test file to verify everything passes**

Run: `python -m pytest tests/sandbox/test_edr105_forage_funnel.py -v`
Expected: tous les tests PASS (config, inertie, min_dist, cfg param, measure smoke, 4 verdicts).

- [ ] **Step 7: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr105_forage_funnel.py
git commit -m "feat(EDR105): _verdict_forage cascade + _report_forage + main_forage"
```

---

## Task 4: Run gelé + provenance (exécution, pas TDD)

**Files:**
- Lecture seule du code ci-dessus ; écrit `results/lewis_forage_funnel_105.json` (via `h.save`).

**Interfaces:**
- Consumes: `main_forage` (Task 3).
- Produces: la table d'entonnoir aux deux niveaux de metab + le verdict + le JSON de provenance.

- [ ] **Step 1: Run gelé**

Run (depuis le worktree) :
`python -c "from tools.lewis_survival_sweep import main_forage; main_forage(seed=105)"`

Expected: une table à 2 lignes (metab=0.0 et 0.25) + une ligne VERDICT. metab=0.25 doit montrer `p_reach≈0` (mort au tick ~5, entonnoir vide) ; metab=0.0 porte le verdict.

- [ ] **Step 2: Si le run gelé est impraticablement lent (precedent EDR 101)**

Si le run dépasse ~15 min (à metab=0 les agents survivent + se reproduisent → pop au cap → ères lourdes), l'interrompre et lancer un run réduit **fidèle** (l'entonnoir se mesure sur ~27 ticks ≪ 150) :

```python
from tools.lewis_survival_sweep import main_forage
main_forage(metab_levels=(0.0, 0.25), n_eval=3, R=1, seed=105)
```

Documenter la réduction comme **surdéterminée** dans le doc EDR (l'entonnoir est une propriété par-agent, robuste à n_eval ; précédent EDR 101).

- [ ] **Step 3: Vérifier la provenance**

Run: `python -c "import json; d=json.load(open('results/lewis_forage_funnel_105.json')); print(d['verdict']); print(list(d['table']))"`
Expected: imprime le verdict + les clés de niveaux (`0.0`, `0.25`).

- [ ] **Step 4: Commit la provenance**

```bash
git add results/lewis_forage_funnel_105.json
git commit -m "data(EDR105): run gele entonnoir forage (provenance)"
```

---

## Notes de réalisation

- Le doc de résultat `docs/EDR/105_*.md` et la MAJ mémoire `lewis-energy-economy-wall.md` sont écrits **après** le run (hors de ce plan d'implémentation), une fois le verdict connu.
- La phase `_e_phases["biologie"]` n'est **pas** utilisée pour `drain_t` (elle nette le revenu de forage via `autres`) ; on somme les sous-buckets purs `bio_metab/terrain/carry` + `brain/action/mouvement` — c'est le cœur de l'anti-circularité.
