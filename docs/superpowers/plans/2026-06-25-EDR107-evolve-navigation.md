# EDR 107 — Ré-évoluer la navigation en Lewis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire tourner l'évolution à cliquet EN Lewis (N_APEX=0, metab=0) sur la fitness de prod `calculate_life_score` et mesurer si `p_reach` (atteinte de proies) monte au fil des générations.

**Architecture:** Réemploi de la machinerie d'évolution (`_reproduce`, cliquet best-ever) et de l'instrument `trace_forage` (EDR 105). Trois fonctions nouvelles dans `tools/lewis_survival_sweep.py` : un runner par génération, un verdict de trajectoire, une orchestration. Aucune modification du monde/du connectome.

**Tech Stack:** Python, numpy, `tools/lewis_survival_sweep.py`, `tools/evolve_competence._reproduce`, `tools/lewis_critical._setup_critical`, `src/seed_ai/persistence.calculate_life_score`, pytest.

## Global Constraints

- **Commandement 15 (1 variable)** : la « variable » est le temps évolutif (numéro de génération). Tout le reste gelé : `N_APEX=0`, `base_metabolism=0`, `forage_payoff=3`, sélection sur `calculate_life_score`, cliquet best-ever top-5.
- **Sélection sur la fitness de PROD** : `calculate_life_score` (PAS de fitness navigation custom).
- **`trace_forage=True`** (instrument inerte d'EDR 105) pour mesurer `p_reach` ; PAS besoin de `trace_energy_sinks` (pas de `drain_t` ici).
- **Scaffold chaud par construction** : chaque génération = ère fraîche `current_era=1` → `anneal(1,30)=0.967`.
- **ASCII only** dans tout `print`/littéral exécuté (cp1252 ; `->` OK).
- **Reproductibilité** : `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par génération ; `memory_retriever.stop()+clear()`.
- **Run réduit d'emblée** (évolution lourde) : `generations=20, num_agents=24, max_ticks=80`.
- **Verdict gelé** : NAVIGATION EVOLUE si `median(p_reach[-5:]) >= median(p_reach[:5]) + 0.15`, sinon SUBSTRAT BLOQUE.

---

## File Structure

- `tools/lewis_survival_sweep.py` — import `calculate_life_score` ; `_p_reach_of_pool` ; `_verdict_evolve_nav` ; `_evolve_nav_gen` ; `_report_evolve_nav` ; `main_evolve_nav`.
- `tests/sandbox/test_edr107_evolve_nav.py` — tests (calqués sur les tests EDR existants).

Constantes existantes réutilisées (déjà dans le module) : `PREY_COUNT=15`, `MutationConfig`, `Biosphere3D`, `MambaAgent`, `_reproduce`, `_setup_critical`, `_load_champions`, `_disable_kuzu`, `Harness`, `seed_at`, `_cfg`.

---

## Task 1: Helpers purs — `_p_reach_of_pool` + `_verdict_evolve_nav`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (import + 2 fonctions, près des `_verdict_*`)
- Test: `tests/sandbox/test_edr107_evolve_nav.py`

**Interfaces:**
- Consumes: rien (fonctions pures).
- Produces:
  - `_p_reach_of_pool(pool)` → float : fraction des agents (dicts) avec `_forage_min_dist <= 0` ; pool vide → 0.0.
  - `_verdict_evolve_nav(traj)` → `"NAVIGATION EVOLUE"` si `median(traj[-k:]) >= median(traj[:k]) + 0.15` (k=5 si ≥10 générations, sinon `max(1, n//2)`), sinon `"SUBSTRAT BLOQUE"` ; traj vide → `"SUBSTRAT BLOQUE"`.

- [ ] **Step 1: Write the failing tests**

Créer `tests/sandbox/test_edr107_evolve_nav.py` :

```python
import numpy as np
from tools.lewis_survival_sweep import _p_reach_of_pool, _verdict_evolve_nav


def test_p_reach_of_pool_fraction():
    pool = [{"_forage_min_dist": 0.0}, {"_forage_min_dist": 3.0},
            {"_forage_min_dist": 0.0}, {"_forage_min_dist": 9999.0}]
    assert _p_reach_of_pool(pool) == 0.5   # 2 sur 4 atteignent (md<=0)


def test_p_reach_of_pool_absent_key_is_unreached():
    pool = [{}, {"_forage_min_dist": 0.0}]   # cle absente -> defaut 9999 -> non atteint
    assert _p_reach_of_pool(pool) == 0.5


def test_p_reach_of_pool_empty():
    assert _p_reach_of_pool([]) == 0.0


def test_verdict_evolve_nav_evolue():
    # premieres ~0.18, dernieres ~0.40 -> delta 0.22 >= 0.15
    traj = [0.18, 0.17, 0.19, 0.18, 0.20] + [0.30, 0.35, 0.38, 0.40, 0.42]
    assert _verdict_evolve_nav(traj) == "NAVIGATION EVOLUE"


def test_verdict_evolve_nav_bloque():
    # plat ~0.18 partout -> delta ~0
    traj = [0.18, 0.17, 0.19, 0.18, 0.20] + [0.19, 0.18, 0.20, 0.17, 0.19]
    assert _verdict_evolve_nav(traj) == "SUBSTRAT BLOQUE"


def test_verdict_evolve_nav_boundary():
    # first median=0.20, last median=0.35 -> delta 0.15 (>= 0.15 -> EVOLUE)
    traj = [0.20] * 5 + [0.35] * 5
    assert _verdict_evolve_nav(traj) == "NAVIGATION EVOLUE"


def test_verdict_evolve_nav_empty():
    assert _verdict_evolve_nav([]) == "SUBSTRAT BLOQUE"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -v`
Expected: FAIL (`ImportError` : `_p_reach_of_pool`/`_verdict_evolve_nav` n'existent pas).

- [ ] **Step 3: Add the import**

Dans `tools/lewis_survival_sweep.py`, après la ligne `from tools.lethality_curriculum import _disable_kuzu`, ajouter :

```python
from src.seed_ai.persistence import calculate_life_score
```

- [ ] **Step 4: Add `_p_reach_of_pool` and `_verdict_evolve_nav`**

Ajouter dans `tools/lewis_survival_sweep.py` (zone des `_verdict_*`, p.ex. après `_verdict_approach`) :

```python
def _p_reach_of_pool(pool):
    """EDR107 : fraction des agents du pool ayant atteint une cellule-proie (_forage_min_dist<=0).
    Pool vide -> 0.0. Necessite trace_forage=True (sinon cle absente -> defaut 9999 -> non atteint)."""
    if not pool:
        return 0.0
    reached = sum(1 for ag in pool if float(ag.get("_forage_min_dist", 9999.0)) <= 0)
    return reached / len(pool)


def _verdict_evolve_nav(traj):
    """EDR107 : verdict sur la trajectoire p_reach par generation. NAVIGATION EVOLUE si la mediane des
    k dernieres generations depasse celle des k premieres de >= 0.15 (ancre sur l'effet +0.05 d'EDR106) ;
    sinon SUBSTRAT BLOQUE. k=5 si >=10 generations, sinon max(1, n//2). traj vide -> SUBSTRAT BLOQUE."""
    if not traj:
        return "SUBSTRAT BLOQUE"
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    first = float(np.median(traj[:k]))
    last = float(np.median(traj[-k:]))
    return "NAVIGATION EVOLUE" if last >= first + 0.15 else "SUBSTRAT BLOQUE"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -v`
Expected: les 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr107_evolve_nav.py
git commit -m "feat(EDR107): helpers _p_reach_of_pool + _verdict_evolve_nav"
```

---

## Task 2: Runner par génération — `_evolve_nav_gen`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (1 fonction)
- Test: `tests/sandbox/test_edr107_evolve_nav.py`

**Interfaces:**
- Consumes: `_p_reach_of_pool` (Task 1), `calculate_life_score`, `_setup_critical`, `PREY_COUNT`, `Biosphere3D`, `MambaAgent`.
- Produces: `_evolve_nav_gen(cfg, genomes, max_ticks=80)` → `(scored, p_reach, stats)` où `scored` = liste de ≤5 tuples `(life_score: float, genome)` triés décroissant (pour le cliquet), `p_reach` = float, `stats` = `{"ticks": int, "eaten": int, "p_reach": float}`. `cfg` doit avoir `trace_forage=True`.

- [ ] **Step 1: Write the failing test (smoke génération)**

Ajouter à `tests/sandbox/test_edr107_evolve_nav.py` :

```python
from tools.lewis_survival_sweep import _evolve_nav_gen, _cfg, _reproduce
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent


def test_evolve_nav_gen_smoke():
    seed_at(107, 0)
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
    mc = MutationConfig(weight_init_std=2.0)
    genomes = _reproduce([MambaAgent().genome for _ in range(3)], 6, mc)
    scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=15)
    assert 0.0 <= p_reach <= 1.0
    assert isinstance(scored, list) and len(scored) >= 1
    s0, g0 = scored[0]
    assert isinstance(s0, float)
    assert g0 is not None
    assert set(stats) == {"ticks", "eaten", "p_reach"}
    assert np.isfinite(stats["ticks"]) and stats["p_reach"] == p_reach
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -k evolve_nav_gen_smoke -v`
Expected: FAIL (`_evolve_nav_gen` n'existe pas).

- [ ] **Step 3: Add `_evolve_nav_gen`**

Ajouter dans `tools/lewis_survival_sweep.py` (après `_measure_forage` ou près des runners) :

```python
def _evolve_nav_gen(cfg, genomes, max_ticks=80):
    """EDR107 : lance UNE generation (ere fraiche, current_era=1 -> scaffold chaud) en Lewis vide d'apex.
    cfg DOIT avoir trace_forage=True. Renvoie (scored, p_reach, stats) : scored = top-5 (life_score, genome)
    pour le cliquet best-ever ; p_reach = _p_reach_of_pool(pool) ; stats = {ticks, eaten, p_reach}.
    Calque run_era d'evolve_competence + setup Lewis de _measure_forage."""
    env = Biosphere3D(cfg)
    _setup_critical(env, 0.0, n_apex=0)
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
    ranked = sorted(pool, key=calculate_life_score, reverse=True)
    scored = []
    for ag in ranked[:5]:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is not None:
            scored.append((float(calculate_life_score(ag)), g))
    p_reach = _p_reach_of_pool(pool)
    eaten = int(sum(ag.get("preys_eaten", 0) for ag in pool))
    return scored, p_reach, {"ticks": t, "eaten": eaten, "p_reach": p_reach}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -k evolve_nav_gen_smoke -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr107_evolve_nav.py
git commit -m "feat(EDR107): _evolve_nav_gen (une generation en Lewis, p_reach + cliquet)"
```

---

## Task 3: Orchestration — `_report_evolve_nav` + `main_evolve_nav`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (2 fonctions, avant le `if __name__`)
- Test: `tests/sandbox/test_edr107_evolve_nav.py`

**Interfaces:**
- Consumes: `_evolve_nav_gen`, `_verdict_evolve_nav`, `_reproduce`, `_load_champions`, `_cfg`, `Harness`, `_disable_kuzu`, `seed_at`, `MutationConfig`.
- Produces:
  - `_report_evolve_nav(h, traj, stats_hist, generations, num_agents, max_ticks, _return)` : imprime la trajectoire + first/last médianes + pente + verdict ; sauve via `h.save` ; renvoie un dict si `_return`.
  - `main_evolve_nav(generations=20, num_agents=24, max_ticks=80, seed=None, _return=False)` : boucle cliquet best-ever, enregistre `p_reach[]`, appelle `_report_evolve_nav`.

- [ ] **Step 1: Write the failing tests**

Ajouter à `tests/sandbox/test_edr107_evolve_nav.py` :

```python
from tools.lewis_survival_sweep import _report_evolve_nav, main_evolve_nav


class _FakeHarness:
    """Capture h.save sans DB."""
    def __init__(self):
        self.saved = None
    def save(self, d):
        self.saved = d


def test_report_evolve_nav_verdict_and_save():
    traj = [0.18, 0.17, 0.19, 0.18, 0.20, 0.30, 0.35, 0.38, 0.40, 0.42]
    stats = [{"ticks": 20, "eaten": 3, "p_reach": p} for p in traj]
    h = _FakeHarness()
    out = _report_evolve_nav(h, traj, stats, 10, 24, 80, _return=True)
    assert out["verdict"] == "NAVIGATION EVOLUE"
    assert h.saved is not None and h.saved["verdict"] == "NAVIGATION EVOLUE"
    assert h.saved["traj"] == traj


def test_main_evolve_nav_smoke():
    out = main_evolve_nav(generations=2, num_agents=6, max_ticks=12, seed=107, _return=True)
    assert "verdict" in out
    assert len(out["traj"]) == 2
    assert out["verdict"] in ("NAVIGATION EVOLUE", "SUBSTRAT BLOQUE")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -k "report_evolve_nav or main_evolve_nav_smoke" -v`
Expected: FAIL (`_report_evolve_nav`/`main_evolve_nav` n'existent pas).

- [ ] **Step 3: Add `_report_evolve_nav` and `main_evolve_nav`**

Ajouter dans `tools/lewis_survival_sweep.py` (après `main_approach`, avant le `if __name__`) :

```python
def _report_evolve_nav(h, traj, stats_hist, generations, num_agents, max_ticks, _return):
    """Trajectoire p_reach par generation + first/last medianes + pente lineaire + verdict + provenance.
    Tout ASCII (cp1252)."""
    verdict = _verdict_evolve_nav(traj)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    first = float(np.median(traj[:k]))
    last = float(np.median(traj[-k:]))
    slope = float(np.polyfit(range(1, n + 1), traj, 1)[0]) if n >= 2 else 0.0
    print("\n=== EDR107 evolution navigation Lewis : trajectoire p_reach ===")
    print("  gen | p_reach | ticks eaten")
    for i, (p, sd) in enumerate(zip(traj, stats_hist), 1):
        print(f"  {i:3d} | {p:7.3f} | {sd['ticks']:5d} {sd['eaten']:5d}")
    print(f"  first-{k} median={first:.3f}  last-{k} median={last:.3f}  delta={last - first:+.3f} (gate +0.15)")
    print(f"  pente lineaire p_reach/gen = {slope:+.4f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "generation", "generations": generations, "num_agents": num_agents,
            "max_ticks": max_ticks, "traj": traj, "first_median": first, "last_median": last,
            "slope": slope, "verdict": verdict, "stats": stats_hist})
    if _return:
        return {"verdict": verdict, "traj": traj, "first_median": first, "last_median": last,
                "slope": slope}


def main_evolve_nav(generations=20, num_agents=24, max_ticks=80, seed=None, _return=False):
    """EDR 107 : re-evolue la navigation EN Lewis (N_APEX=0, metab=0, forage_payoff=3) sur la fitness de
    prod calculate_life_score. Cliquet best-ever (top-5 global). Mesure p_reach par generation -> verdict
    NAVIGATION EVOLUE (last>=first+0.15) vs SUBSTRAT BLOQUE."""
    with Harness(seed=seed, name="lewis_evolve_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR107 : evolution navigation Lewis, gen={generations}, pop={num_agents}, "
              f"max_ticks={max_ticks}, seed={base}.")
        mc = MutationConfig(weight_init_std=2.0)
        seed_at(base, 0)
        champs = _load_champions()
        best_ever = [(0.0, g) for g in champs]
        cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
        traj, stats_hist = [], []
        prog = h.progress(generations, label="generations")
        for gen in range(1, generations + 1):
            seed_at(base + gen, 0)
            champ_genomes = [g for (_s, g) in best_ever]
            genomes = _reproduce(champ_genomes, num_agents, mc)
            scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
            best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
            traj.append(p_reach)
            stats_hist.append(stats)
            prog.update()
        return _report_evolve_nav(h, traj, stats_hist, generations, num_agents, max_ticks, _return)
```

- [ ] **Step 4: Run the full test file to verify everything passes**

Run: `python -m pytest tests/sandbox/test_edr107_evolve_nav.py -v`
Expected: tous les tests PASS (helpers + smoke génération + report + smoke main).

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr107_evolve_nav.py
git commit -m "feat(EDR107): _report_evolve_nav + main_evolve_nav (boucle cliquet, trajectoire p_reach)"
```

---

## Task 4: Run réduit + provenance (exécution, pas TDD)

**Files:**
- Lecture seule ; écrit `results/lewis_evolve_nav_107.json` (via `h.save`).

**Interfaces:**
- Consumes: `main_evolve_nav` (Task 3).
- Produces: la trajectoire `p_reach` sur 20 générations + le verdict + le JSON de provenance.

- [ ] **Step 1: Run réduit d'emblée**

Run (depuis le worktree) :
`python -c "from tools.lewis_survival_sweep import main_evolve_nav; main_evolve_nav(generations=20, num_agents=24, max_ticks=80, seed=107)"`

Expected: une table de 20 lignes (p_reach par génération) + first/last médianes + pente + VERDICT (`NAVIGATION EVOLUE` ou `SUBSTRAT BLOQUE`).

- [ ] **Step 2: Si trop lent (> ~20 min)**

Réduire et relancer (documenter comme surdéterminé) :
`python -c "from tools.lewis_survival_sweep import main_evolve_nav; main_evolve_nav(generations=14, num_agents=18, max_ticks=60, seed=107)"`
(14 générations restent suffisantes pour first-5 vs last-5 ; `max_ticks=60 > survie ~27` ticks d'EDR 101.)

- [ ] **Step 3: Vérifier la provenance**

Run: `python -c "import json; d=json.load(open('results/lewis_evolve_nav_107.json'))['data']; print(d['verdict']); print('first/last:', round(d['first_median'],3), round(d['last_median'],3), 'slope:', round(d['slope'],4)); print('traj:', [round(x,3) for x in d['traj']])"`
Expected: imprime le verdict, first/last médianes, pente, et la trajectoire complète.

---

## Notes de réalisation

- Le doc de résultat `docs/EDR/107_*.md` et la MAJ mémoire `lewis-energy-economy-wall.md` sont écrits **après** le run, une fois le verdict connu.
- `results/` est gitignoré (artefacts régénérables) ; provenance citée par chemin + `seed=107` + commit.
- Le smoke `test_main_evolve_nav_smoke` lance une mini-évolution (2 gén × 6 agents × 12 ticks) — quelques dizaines de secondes, acceptable (précédent EDR 105/106).
- Le scaffold reste chaud automatiquement (`current_era=1` à chaque génération) ; ne PAS incrémenter `current_era` entre générations.
