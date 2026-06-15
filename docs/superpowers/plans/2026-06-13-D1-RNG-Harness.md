# D1 — RNG appariement + BaseHarness — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre les comparaisons d'expériences appariées et reproductibles via un `SeedManager` (seed global déterministe aux frontières) et un objet `Harness` de composition, puis brancher seed + provenance dans la prod (`robust_hof`, `main_biosphere`) et le pilote `robust_eval`.

**Architecture:** Nouveau module `src/seed_ai/harness.py` = `SeedManager` (seed aux frontières + `default_rng` exposé) + `Harness` (context manager : seed, cycle async_logger, Progress, éval robuste **appariée**, I/O résultats). `eval_harness.py` (stat) reste inchangé, devient collaborateur. La prod et les tools sont seedés sans réécrire les 168 sites `np.random.X`.

**Tech Stack:** Python 3.13, numpy (seed global + `default_rng`), pytest. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-13-D1-RNG-Harness-design.md`

---

## File Structure

- **Create** `src/seed_ai/harness.py` — `SeedManager`, `Harness`, `_git_short_commit`.
- **Create** `tests/sandbox/test_harness.py` — tests unitaires rapides (sans biosphère ni KuzuDB) + 1 test d'intégration `robust_hof`.
- **Modify** `src/seed_ai/robust_hof.py` — kwarg `seed` dans `robust_evaluate`.
- **Modify** `src/environments/config.py` — champ `experiment_seed: Optional[int] = None`.
- **Modify** `main_biosphere.py` — seed boot + log de provenance après création du `config`.
- **Modify** `tools/robust_eval.py` — pilote : appariement BRUITÉE vs ROBUSTE via `Harness`/seed.
- **Recipe + checklist** (Tasks 8-9) — vague comparative puis reste des tools (migration par tool, lue à l'exécution).

Convention tests : `tests/sandbox/`, lancés par `python -m pytest`. Commits : un par tâche atomique.

---

### Task 1: `SeedManager` (déterminisme aux frontières)

**Files:**
- Create: `src/seed_ai/harness.py`
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_harness.py
import numpy as np
from src.seed_ai.harness import SeedManager


def test_resolve_returns_given_int():
    assert SeedManager.resolve(123) == 123


def test_resolve_draws_valid_int_when_none():
    s = SeedManager.resolve(None)
    assert isinstance(s, int) and 0 <= s < 2 ** 32


def test_seed_boundary_is_reproducible():
    SeedManager(42).seed_boundary(0)
    a = np.random.rand()
    SeedManager(42).seed_boundary(0)
    b = np.random.rand()
    assert a == b


def test_seed_boundary_independent_across_eras():
    sm = SeedManager(100)
    sm.seed_boundary(0)
    a = np.random.rand()
    sm.seed_boundary(1)
    b = np.random.rand()
    assert a != b


def test_rng_generator_is_seeded():
    assert SeedManager(7).rng.random() == SeedManager(7).rng.random()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.seed_ai.harness'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/seed_ai/harness.py
"""
src/seed_ai/harness.py — Socle de validité D1 (scan global, item Dev D1).

SeedManager : pose le déterminisme aux FRONTIÈRES (boot/ère/répétition) via le RNG global numpy.
Garantit l'APPARIEMENT (deux conditions au même seed partent du même monde initial) sans réécrire
les 168 sites np.random.X. Expose aussi un Generator default_rng pour le code NEUF qui veut
l'isolation par tirage. Détail : docs/superpowers/specs/2026-06-13-D1-RNG-Harness-design.md.
"""
import numpy as np


class SeedManager:
    def __init__(self, base_seed):
        self.base_seed = int(base_seed)
        self.rng = np.random.default_rng(self.base_seed)

    def seed_boundary(self, i=0):
        """Pose np.random.seed(base_seed + i) (déterministe). Renvoie la graine effective."""
        s = self.base_seed + int(i)
        np.random.seed(s)
        return s

    @staticmethod
    def resolve(seed=None):
        """seed fourni -> int(seed) ; None -> graine d'entropie (run rejouable a posteriori)."""
        if seed is not None:
            return int(seed)
        return int(np.random.SeedSequence().entropy % (2 ** 32))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/harness.py tests/sandbox/test_harness.py
git commit -m "feat(harness): SeedManager — seed deterministe aux frontieres (D1)"
```

---

### Task 2: `Harness` context manager (seed boot + cycle async_logger)

**Files:**
- Modify: `src/seed_ai/harness.py`
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_harness.py
from src.seed_ai.harness import Harness


def test_harness_resolves_and_exposes_seed():
    with Harness(seed=1, name="t", with_db=False) as h:
        assert h.seed == 1
        assert h.db is None            # with_db=False -> pas de DB, pas de crash


def test_harness_seeds_boot_deterministically():
    with Harness(seed=99, name="t", with_db=False):
        a = np.random.rand()
    with Harness(seed=99, name="t", with_db=False):
        b = np.random.rand()
    assert a == b


def test_harness_none_seed_is_logged_int():
    with Harness(seed=None, name="t", with_db=False) as h:
        assert isinstance(h.seed, int) and 0 <= h.seed < 2 ** 32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py -k harness -v`
Expected: FAIL — `ImportError: cannot import name 'Harness'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/seed_ai/harness.py (après SeedManager)
import os
import json
import time
import logging

log = logging.getLogger("AGIseed.Harness")


def _git_short_commit():
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


class Harness:
    """Objet de composition (context manager) : seed + cycle async_logger + Progress + éval robuste
    appariée + I/O résultats. Absorbe le boilerplate des tools/ ; ne porte pas leur logique métier.

        with Harness(seed=0, name="robust_eval") as h:
            score = h.eval_robust(cfg, genome, run_era_fn=run_era, K=4)
            h.save({"score": score})
    """
    def __init__(self, seed=None, name="exp", robust_K=3, num_agents=20, with_db=True, db_wait=5.0):
        self.seed = SeedManager.resolve(seed)
        self.seeds = SeedManager(self.seed)
        self.name = name
        self.robust_K = int(robust_K)
        self.num_agents = int(num_agents)
        self.with_db = with_db
        self.db_wait = float(db_wait)
        self.db = None
        self._logger_started = False

    def __enter__(self):
        self.seeds.seed_boundary(0)
        log.info(f"[HARNESS] {self.name} seed={self.seed}  (rejouer : seed={self.seed})")
        if self.with_db:
            from src.graph_rag.async_logger import logger as async_logger
            async_logger.start()
            self._logger_started = True
            deadline = time.time() + self.db_wait
            while time.time() < deadline:
                self.db = async_logger.get_db()
                if self.db is not None:
                    break
                time.sleep(0.1)
            if self.db is None:
                log.warning(f"[HARNESS] {self.name}: KuzuDB indisponible -> degradation gracieuse")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._logger_started:
            from src.graph_rag.async_logger import logger as async_logger
            async_logger.stop()
            self._logger_started = False
        return False  # ne masque jamais une exception
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/harness.py tests/sandbox/test_harness.py
git commit -m "feat(harness): Harness context manager (seed boot + cycle async_logger, with_db gracieux)"
```

---

### Task 3: `Harness.eval_robust` (appariement) + `.powered` / `.progress` / `.save`

**Files:**
- Modify: `src/seed_ai/harness.py`
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_harness.py

def test_eval_robust_is_reproducible():
    def fake_run_era(cfg, genomes):
        return None, {"score": float(np.random.rand())}
    s1 = Harness(seed=42, with_db=False).eval_robust(None, "g", fake_run_era, K=3, num_agents=1)
    s2 = Harness(seed=42, with_db=False).eval_robust(None, "g", fake_run_era, K=3, num_agents=1)
    assert s1 == s2


def test_eval_robust_pairs_conditions_on_seed():
    # Chaque ère re-seede sa frontière -> le 1er tirage ("monde initial") est identique pour
    # deux conditions au même seed, MÊME si elles consomment ensuite le flux differemment.
    worlds_a, worlds_b = [], []

    def run_era_a(cfg, genomes):
        worlds_a.append(float(np.random.rand()))  # monde
        np.random.rand()                          # condition A consomme
        return None, {"score": 0.0}

    def run_era_b(cfg, genomes):
        worlds_b.append(float(np.random.rand()))  # monde (même seed -> même valeur)
        np.random.rand(); np.random.rand()        # condition B consomme PLUS
        return None, {"score": 0.0}

    Harness(seed=7, with_db=False).eval_robust(None, "ga", run_era_a, K=3, num_agents=1)
    Harness(seed=7, with_db=False).eval_robust(None, "gb", run_era_b, K=3, num_agents=1)
    assert worlds_a == worlds_b   # mondes initiaux APPARIÉS


def test_save_writes_seed_and_commit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h = Harness(seed=5, name="demo", with_db=False)
    path = h.save({"metric": 1.0})
    import json as _json
    with open(path, encoding="utf-8") as f:
        out = _json.load(f)
    assert out["seed"] == 5 and out["name"] == "demo" and "commit" in out
    assert out["data"]["metric"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py -k "eval_robust or save" -v`
Expected: FAIL — `AttributeError: 'Harness' object has no attribute 'eval_robust'`

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter ces méthodes DANS la classe Harness
    def eval_robust(self, config, genome, run_era_fn, K=None, num_agents=None):
        """Compétence robuste APPARIÉE : moyenne du metrics['score'] sur K ères seedées base+i.
        run_era_fn(config, genomes) -> (scored, metrics). Deux conditions au même seed Harness
        voient les mêmes mondes initiaux (block-pairing) -> variance entre-conditions effondrée."""
        K = self.robust_K if K is None else int(K)
        n = self.num_agents if num_agents is None else int(num_agents)
        scores = []
        for i in range(max(1, K)):
            self.seeds.seed_boundary(i)
            _scored, metrics = run_era_fn(config, [genome] * n)
            scores.append(float(metrics["score"]))
        return float(np.mean(scores)) if scores else 0.0

    def powered(self, conditions, run_seed_fn, seeds=(0, 1, 2)):
        """Wrap eval_harness.powered_eval en injectant le seed Harness comme base (base+s)."""
        from src.seed_ai.eval_harness import powered_eval
        base = self.seed

        def seeded_fn(cfg, s):
            np.random.seed(base + int(s))
            return run_seed_fn(cfg, s)

        return powered_eval(conditions, seeded_fn, seeds=seeds)

    def progress(self, total, label=""):
        from tools.progress import Progress
        return Progress(total, label=label or self.name)

    def save(self, data):
        """Écrit results/<name>_<seed>.json (seed + commit court + données) -> provenance."""
        os.makedirs("results", exist_ok=True)
        out = {"name": self.name, "seed": self.seed, "commit": _git_short_commit(), "data": data}
        path = os.path.join("results", f"{self.name}_{self.seed}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=float)
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/harness.py tests/sandbox/test_harness.py
git commit -m "feat(harness): eval_robust apparie + powered/progress/save (provenance)"
```

---

### Task 4: Seed dans `robust_hof.robust_evaluate` (prod)

**Files:**
- Modify: `src/seed_ai/robust_hof.py:14-38`
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test** (intégration légère — lance une vraie mini-ère, ~secondes)

```python
# Ajouter à tests/sandbox/test_harness.py

def test_robust_evaluate_reproducible_with_seed():
    from src.environments.config import WorldConfig
    from src.seed_ai.robust_hof import robust_evaluate
    from src.agents.mamba_agent import MambaAgent
    cfg = WorldConfig()
    cfg.size = 6
    g = MambaAgent().genome
    a = robust_evaluate(cfg, g, K=2, num_agents=2, max_ticks=3, seed=2026)
    b = robust_evaluate(cfg, g, K=2, num_agents=2, max_ticks=3, seed=2026)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py::test_robust_evaluate_reproducible_with_seed -v`
Expected: FAIL — `TypeError: robust_evaluate() got an unexpected keyword argument 'seed'`

- [ ] **Step 3: Write minimal implementation**

Dans `src/seed_ai/robust_hof.py`, modifier la signature et seeder par ère :

```python
def robust_evaluate(config, genome, K=3, num_agents=20, max_ticks=400, seed=None):
    """Compétence robuste d'un génome : moyenne du meilleur life_score sur K ères de clones.
    De-bruite la sélection HoF. seed fourni -> ères seedées base+i (reproductible + apparié).
    Renvoie 0.0 si aucune ère scorable."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score

    scores = []
    for i in range(max(1, int(K))):
        if seed is not None:
            np.random.seed(int(seed) + i)
        env = Biosphere3D(config)
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        if pool:
            scores.append(max(calculate_life_score(a) for a in pool))
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    return float(np.mean(scores)) if scores else 0.0
```

(Le `robust_rank` ci-dessous accepte déjà `config` ; lui passer un `seed` est différé à la vague comparative — il n'apparie pas encore. Aucun changement de `robust_rank` ici : non-régression.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py::test_robust_evaluate_reproducible_with_seed -v`
Expected: PASS (si l'environnement charge ; sinon marquer `@pytest.mark.slow`)

- [ ] **Step 5: Run full suite (non-régression)**

Run: `python -m pytest tests/sandbox/test_harness.py -v`
Expected: PASS (12 tests)

- [ ] **Step 6: Commit**

```bash
git add src/seed_ai/robust_hof.py tests/sandbox/test_harness.py
git commit -m "feat(robust_hof): kwarg seed -> evaluation HoF reproductible/appariee (prod)"
```

---

### Task 5: `experiment_seed` dans la config + seed boot dans `main_biosphere`

**Files:**
- Modify: `src/environments/config.py:2` (import `Optional`), `:62-63` (champ)
- Modify: `main_biosphere.py:162-165` (seed boot + log provenance)
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_harness.py

def test_config_has_experiment_seed_default_none():
    from src.environments.config import WorldConfig
    assert WorldConfig().experiment_seed is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py::test_config_has_experiment_seed_default_none -v`
Expected: FAIL — `AttributeError: 'WorldConfig' object has no attribute 'experiment_seed'`

- [ ] **Step 3: Write minimal implementation**

Dans `src/environments/config.py`, ligne 2, étendre l'import typing :

```python
from typing import Dict, Any, List, Optional
```

Dans `WorldConfig`, juste après `robust_hof_K: int = 0` (ligne 62) :

```python
    # Reproductibilité / provenance (D1) : None -> graine tirée et LOGGÉE au boot (run rejouable
    # a posteriori) ; int fixe -> run pleinement reproductible. Défaut None = comportement historique.
    experiment_seed: Optional[int] = None
```

Dans `main_biosphere.py`, remplacer le bloc lignes 162-165 :

```python
    config = WorldConfig()
    config.robust_hof_K = 4   # EDR 080 (reco) : sélection HoF ROBUSTE pour les vraies runs (+~45% compétence,
                              # résultat + fiable). Défaut WorldConfig reste 0 (tests/outils inchangés).
    os.environ["ACTIVE_EXP_VARIABLE"] = config.active_exp_variable
```

par :

```python
    config = WorldConfig()
    config.robust_hof_K = 4   # EDR 080 (reco) : sélection HoF ROBUSTE pour les vraies runs (+~45% compétence,
                              # résultat + fiable). Défaut WorldConfig reste 0 (tests/outils inchangés).

    # D1 — provenance : seed le RNG global au boot et LOGGE la graine (rejouable via EXPERIMENT_SEED).
    from src.seed_ai.harness import SeedManager
    _env_seed = os.getenv("EXPERIMENT_SEED")
    config.experiment_seed = SeedManager.resolve(int(_env_seed) if _env_seed else None)
    SeedManager(config.experiment_seed).seed_boundary(0)
    logger.info(f"[SEED] experiment_seed={config.experiment_seed}  (rejouer : EXPERIMENT_SEED={config.experiment_seed})")

    os.environ["ACTIVE_EXP_VARIABLE"] = config.active_exp_variable
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py::test_config_has_experiment_seed_default_none -v`
Expected: PASS

- [ ] **Step 5: Smoke import (main_biosphere se charge sans erreur)**

Run: `python -c "import main_biosphere; from src.environments.config import WorldConfig; assert WorldConfig().experiment_seed is None; print('OK')"`
Expected: `OK` (pas de traceback à l'import)

- [ ] **Step 6: Commit**

```bash
git add src/environments/config.py main_biosphere.py tests/sandbox/test_harness.py
git commit -m "feat(seed): experiment_seed config + seed boot logge dans main_biosphere (provenance D1)"
```

---

### Task 6: Pilote — migrer `tools/robust_eval.py` (appariement BRUITÉE vs ROBUSTE)

**But :** prouver le pattern sur le tool qui compare deux régimes. Aujourd'hui `_robust_score`/`_true_competence` ne seedent pas → BRUITÉE vs ROBUSTE comparent des mondes différents. On apparie via le seed.

**Files:**
- Modify: `tools/robust_eval.py:40-51` (seed dans `_robust_score`/`_true_competence`), `:69-99` (boot via seed + provenance)

- [ ] **Step 1: Modifier `_robust_score` et `_true_competence` pour seeder par ère**

```python
def _robust_score(cfg, g, K, num_agents, seed=None):
    """Compétence robuste d'un génome : moyenne du life_score sur K ères de clones (de-bruite)."""
    vals = []
    for i in range(K):
        if seed is not None:
            np.random.seed(int(seed) + i)
        _, m = run_era(cfg, [g] * num_agents)
        vals.append(m["score"])
    return float(np.mean(vals))


def _true_competence(cfg, g, n, num_agents, seed=None):
    """Compétence VRAIE (mesure propre) : survie moyenne sur n ères indépendantes (seedées si fourni)."""
    vals = []
    for i in range(n):
        if seed is not None:
            np.random.seed(int(seed) + 1000 + i)   # plage disjointe de _robust_score
        vals.append(run_era(cfg, [g] * num_agents)[1]["ticks"])
    return float(np.mean(vals))
```

- [ ] **Step 2: Câbler `evolve` pour propager le seed**

Modifier `evolve(...)` pour accepter `seed=None` et le passer à `_robust_score` :

```python
def evolve(cfg, robust_K, eras, num_agents, mc, prog, seed=None):
    champions = _load_champions()
    best_ever = [(0.0, g) for g in champions]
    for e in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents, mc)
        if seed is not None:
            np.random.seed(int(seed) + e)               # ère seedée -> appariement entre régimes
        scored, _ = run_era(cfg, genomes)
        if scored:
            if robust_K > 1:
                top_g = scored[0][1]
                scored[0] = (_robust_score(cfg, top_g, robust_K, num_agents, seed=seed), top_g)
            best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return best_ever[0][1]
```

- [ ] **Step 3: Remplacer le boot manuel de `main()` par `Harness` (seed + cycle logger + provenance)**

Remplacer le corps de `main(...)` (lignes 70-99) par :

```python
def main(eras=15, num_agents=30, robust_K=3, n_final=15, seed=None):
    from src.seed_ai.harness import Harness
    with Harness(seed=seed, name="robust_eval", with_db=True) as h:
        s = h.seed
        cfg = WorldConfig()
        mc = MutationConfig(weight_init_std=2.0)
        print(f"VALIDATION BIOSPHERE d'EDR 078 : BRUITEE (K=1) vs ROBUSTE (K={robust_K}). {eras} eres. seed={s}.")

        pn = h.progress(eras, label="BRUITEE (K=1)")
        champ_noisy = evolve(cfg, 1, eras, num_agents, mc, pn, seed=s)            # même seed -> mondes appariés
        pr = h.progress(eras, label=f"ROBUSTE (K={robust_K})")
        champ_robust = evolve(cfg, robust_K, eras, num_agents, mc, pr, seed=s)

        pf = h.progress(2, label="mesure competence vraie")
        tn = _true_competence(cfg, champ_noisy, n_final, num_agents, seed=s); pf.update()
        tr = _true_competence(cfg, champ_robust, n_final, num_agents, seed=s); pf.update()

        print(f"\n=== COMPETENCE VRAIE du champion (survie moyenne / {n_final} eres propres) ===")
        print(f"  selection BRUITEE  (K=1)        : {tn:5.1f} ticks")
        print(f"  selection ROBUSTE  (K={robust_K})        : {tr:5.1f} ticks")
        print("\n=== VERDICT ===")
        if tr > tn * 1.15:
            print(f"  -> l'evaluation ROBUSTE leve le plateau : {tn:.0f} -> {tr:.0f} ticks (+{(tr/tn-1)*100:.0f}%).")
            print(f"     EDR 078 valide sur le VIVANT : de-bruiter la fitness forge une vraie competence.")
        elif tr > tn:
            print(f"  -> robuste > bruitee ({tr:.0f} vs {tn:.0f}) ; effet present, a amplifier (K plus grand).")
        else:
            print(f"  -> pas d'effet net sur le vivant ({tr:.0f} vs {tn:.0f}) : la fitness de GROUPE domine le bruit.")
        h.save({"true_noisy": tn, "true_robust": tr, "eras": eras, "robust_K": robust_K})
```

Supprimer en tête de `main` l'ancien `async_logger.start()` + boucle d'attente + `async_logger.stop()` (désormais gérés par `Harness`). Garder l'import `async_logger` seulement s'il sert ailleurs (sinon le retirer).

- [ ] **Step 4: Smoke (run court, vérifier déterminisme + provenance)**

Run: `HEADLESS=1 python -m tools.robust_eval` *(ou un wrapper court `main(eras=2, num_agents=6, robust_K=2, n_final=2, seed=1)`)*
Expected: s'exécute sans crash, imprime `seed=1`, écrit `results/robust_eval_1.json`. Relancer avec `seed=1` → mêmes `true_noisy`/`true_robust`.

- [ ] **Step 5: Commit**

```bash
git add tools/robust_eval.py
git commit -m "refactor(tools): robust_eval pilote — appariement BRUITEE/ROBUSTE via Harness+seed (D1)"
```

---

### Task 7: Vague comparative — recette de migration + 1ʳ tool

**But :** migrer les tools qui **comparent des conditions** (l'appariement y paye le plus). Chaque tool est lu à l'exécution puis migré selon la **recette** ci-dessous (le pilote Task 6 = implémentation de référence). Un commit atomique par tool.

**Recette (à appliquer par tool) :**
1. Envelopper le corps de `main()` dans `with Harness(seed=seed, name="<tool>") as h:` ; supprimer le `async_logger.start()`/attente/`stop()` manuel.
2. Comparaisons multi-conditions → passer par `h.powered(conditions, run_seed_fn, seeds)` (les conditions partagent `base+s` → **appariées**). Sinon, seeder chaque ère via `np.random.seed(base+i)` avant `run_era`.
3. Remplacer les `Progress(...)` par `h.progress(...)`.
4. Terminer par `h.save({...})` pour la provenance.
5. Vérifier : relancer 2× au même `seed` → résultats identiques.

**Tools de la vague (checklist) :**
- [ ] `tools/func_benefit.py` (FIABLE vs SOLO — bénéfice fonctionnel langage)
- [ ] `tools/lang_on_competent.py`
- [ ] `tools/coevolve_language.py`
- [ ] `tools/refgame_bio.py`
- [ ] `tools/fiabiliser.py`
- [ ] `tools/aligned_selection.py`

Pour CHAQUE : lire le tool → appliquer la recette → smoke court (2× même seed = identique) → commit `refactor(tools): <tool> appariement via Harness+seed (D1)`.

---

### Task 8: Reste des tools (mécanique) + cohérence finale

**But :** migrer les ~50 tools restants (boilerplate seed + cycle logger). Mécanique, faible risque. Un tool peut être laissé tel quel s'il n'a ni `async_logger` ni comparaison (noter dans le commit).

- [ ] **Step 1: Lister les tools restants à seeder**

Run: `python -m pytest -q` *(baseline verte avant la vague)* puis recenser :
Run: `git grep -l "async_logger.start\|np.random" tools/ | sort`
Expected: liste des tools ; cocher au fur et à mesure.

- [ ] **Step 2: Appliquer la recette de Task 7 à chaque tool restant**

Par lots de 3-5, chacun : recette → smoke → commit atomique `refactor(tools): <tool> seed+Harness (D1)`.

- [ ] **Step 3: Non-régression globale**

Run: `python -m pytest -q`
Expected: suite verte (≥ 146 tests + nouveaux tests harness), aucune régression.

- [ ] **Step 4: Commit final de clôture (doc)**

Mettre à jour `roadmap.md` §🛠️ Dev (item 1 RNG/BaseHarness → ✅ livré) + pointer le spec/plan.

```bash
git add roadmap.md
git commit -m "docs(roadmap): D1 RNG appariement + Harness livre (socle de validite)"
```

---

## Self-Review (effectuée)

- **Spec coverage :** SeedManager (T1) ✓ · Harness composition (T2-T3) ✓ · appariement/eval_robust (T3) ✓ · seed-défaut provenance (T5) ✓ · robust_hof prod (T4) ✓ · main_biosphere boot (T5) ✓ · pilotes robust_eval (T6) + vague comparative (T7) + reste (T8) ✓ · tests repro/appariement/indépendance/cycle-logger/non-régression (T1-T8) ✓. Frontières YAGNI (pas de rewrite 168 sites, pas de versioning complet, pas de Bonferroni) respectées.
- **Placeholders :** aucun dans les tâches à code déterminable (T1-T6). T7-T8 = recette explicite + checklist (code par-tool non fabriqué car fichiers lus à l'exécution — choix honnête, pas un placeholder).
- **Cohérence des types :** `SeedManager(base_seed)`, `.seed_boundary(i)`, `.resolve(seed)`, `.rng` ; `Harness(seed,name,robust_K,num_agents,with_db,db_wait)`, `.eval_robust(config,genome,run_era_fn,K,num_agents)`, `.powered(conditions,run_seed_fn,seeds)`, `.progress(total,label)`, `.save(data)` — noms cohérents T1→T8. `robust_evaluate(...,seed=None)` cohérent T4↔usages.
