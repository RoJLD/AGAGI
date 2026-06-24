# A2 MAP-Elites (archive QD) + comparaison vs HoF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Fournir une archive Quality-Diversity (MAP-Elites) réutilisable + un outil de comparaison appariée qui mesure si reproduire depuis des niches diverses bat le HoF top-10 mono-objectif. NE PAS câbler en prod (différé jusqu'au verdict).

**Architecture:** (1) `src/seed_ai/map_elites.py` : descripteur (taille×palier) + `MapElitesArchive` (pur, testable sans biosphère) + flag `WorldConfig.use_map_elites`. (2) `tools/map_elites_compare.py` : bras HoF (top-5 ratchet) vs bras QD (archive), appariés multi-seed, era-runner riche en stats, verdict via `compute_transfer_verdict` (réutilisé de curriculum_transfer).

**Tech Stack:** Python 3, NumPy, pytest.

**Spec:** [`../specs/2026-06-24-NAS-A2-MapElites-design.md`](../specs/2026-06-24-NAS-A2-MapElites-design.md)

## Global Constraints

- **Non-régression** : `WorldConfig.use_map_elites=False` par défaut ; **`main_biosphere` / `persistence.py` NON touchés** cette itération (câblage prod différé). A2 = archive + mesure uniquement.
- **Budget égal** entre bras (mêmes ères/agents/ticks ; banc sweet-spot `base_metabolism=0.25`, `forage_payoff=3.0`).
- **Appariement** : `SeedManager(seed).seed_boundary(0)` au départ de CHAQUE bras.
- **Imports tool** : injection `sys.path` (racine projet) AVANT les imports `src` (sinon ModuleNotFoundError en script — leçon D1).
- **Archive pure** : pas d'I/O ni de RNG caché dans `MapElitesArchive` (RNG = `np.random` global, seedé par seed_boundary).
- **Git** : commits PATH-SCOPED ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: `MapElitesArchive` (archive QD pure) + flag config

**Files:**
- Create: `src/seed_ai/map_elites.py`
- Modify: `src/environments/config.py` (après `kwta_keep_frac`)
- Test: `tests/sandbox/test_map_elites.py` (Create)

**Interfaces:**
- Produces: `descriptor(num_nodes:int, stats:dict) -> (int,int)` ; `MapElitesArchive` (`upsert`, `elites`, `sample`, `coverage`, `best_score`) ; `WorldConfig.use_map_elites: bool = False`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_map_elites.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.seed_ai.map_elites import descriptor, MapElitesArchive


class _G:
    def __init__(self, n):
        self.num_nodes = n


def test_descriptor_bins():
    assert descriptor(172, {"mammoth_kills": 1}) == (1, 3)
    assert descriptor(150, {}) == (0, 0)
    assert descriptor(400, {})[0] == 7          # size clampé haut
    assert descriptor(172, {"preys_eaten": 2}) == (1, 1)
    assert descriptor(172, {"spears_crafted": 1}) == (1, 2)
    assert descriptor(100, {})[0] == 0          # size clampé bas


def test_upsert_keeps_max_per_cell():
    a = MapElitesArchive()
    assert a.upsert(10.0, _G(172), {"preys_eaten": 1}) is True
    assert a.upsert(5.0, _G(172), {"preys_eaten": 1}) is False   # même cellule, plus bas
    assert a.best_score() == 10.0
    assert a.upsert(20.0, _G(172), {"preys_eaten": 1}) is True   # plus haut -> remplace
    assert a.best_score() == 20.0
    assert a.coverage() == 1


def test_distinct_cells_coexist():
    a = MapElitesArchive()
    a.upsert(10.0, _G(172), {"preys_eaten": 1})    # (1,1)
    a.upsert(8.0, _G(172), {"mammoth_kills": 1})   # (1,3)
    a.upsert(7.0, _G(220), {"preys_eaten": 1})     # (4,1)
    assert a.coverage() == 3


def test_sample_and_empty():
    a = MapElitesArchive()
    assert a.sample(3) == []
    a.upsert(10.0, _G(172), {"preys_eaten": 1})
    a.upsert(9.0, _G(200), {"mammoth_kills": 1})
    np.random.seed(0)
    s = a.sample(4)
    assert len(s) == 4
    assert all(hasattr(g, "num_nodes") for g in s)
```

- [ ] **Step 2: Run tests — verify fail**

Run: `python -m pytest tests/sandbox/test_map_elites.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.seed_ai.map_elites'`).

- [ ] **Step 3: Create `src/seed_ai/map_elites.py`**

```python
"""MAP-Elites (Quality-Diversity) — NAS Axe A-2. Archive de niches comportementales : chaque cellule
garde l'élite de plus haut life_score de sa niche. Reproduire depuis des niches diverses (vs HoF
mono-objectif) pour échapper au plateau de bruit de fitness. Spec : docs/superpowers/specs/2026-06-24-NAS-A2-MapElites-design.md"""
from typing import Dict, Tuple, List
import numpy as np

SIZE_BIN_LO = 150     # num_nodes en dessous -> bin 0
SIZE_BIN_W = 15       # largeur d'un bin de taille
SIZE_BINS = 8         # nb de bins de taille (clamp)


def descriptor(num_nodes: int, stats: dict) -> Tuple[int, int]:
    """(size_bin, tier) — taille réseau × palier moyens→ends (0 survit /1 forage /2 crafte /3 chasse apex)."""
    size_bin = (int(num_nodes) - SIZE_BIN_LO) // SIZE_BIN_W
    size_bin = max(0, min(size_bin, SIZE_BINS - 1))
    if stats.get("mammoth_kills", 0) > 0:
        tier = 3
    elif stats.get("spears_crafted", 0) > 0:
        tier = 2
    elif stats.get("preys_eaten", 0) > 0:
        tier = 1
    else:
        tier = 0
    return (size_bin, tier)


class MapElitesArchive:
    """cells: (size_bin, tier) -> (score, genome, stats). Garde le max par cellule."""

    def __init__(self):
        self.cells: Dict[Tuple[int, int], Tuple[float, object, dict]] = {}

    def upsert(self, score: float, genome, stats: dict) -> bool:
        cell = descriptor(genome.num_nodes, stats)
        cur = self.cells.get(cell)
        if cur is None or score > cur[0]:
            self.cells[cell] = (float(score), genome, dict(stats))
            return True
        return False

    def elites(self) -> List[Tuple[float, object, dict]]:
        return list(self.cells.values())

    def sample(self, n: int) -> List:
        """n génomes tirés (avec remise) uniformément parmi les élites (RNG global np.random, seedé)."""
        elites = self.elites()
        if not elites:
            return []
        idxs = np.random.randint(0, len(elites), size=n)
        return [elites[int(i)][1] for i in idxs]

    def coverage(self) -> int:
        return len(self.cells)

    def best_score(self) -> float:
        return max((c[0] for c in self.cells.values()), default=0.0)
```

- [ ] **Step 4: Add config flag**

Dans `src/environments/config.py`, après `kwta_keep_frac: float = 1.0` :

```python
    # NAS Axe A-2 : sélection MAP-Elites (archive QD) au lieu du HoF top-10. False = HoF legacy
    # (non-régression). Câblage prod différé jusqu'au verdict de la mesure (tools/map_elites_compare.py).
    use_map_elites: bool = False
```

- [ ] **Step 5: Run tests — verify pass**

Run: `python -m pytest tests/sandbox/test_map_elites.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Config default test + commit**

Ajouter au fichier de test :
```python
def test_config_use_map_elites_default_false():
    from src.environments.config import WorldConfig
    assert WorldConfig().use_map_elites is False
```
Run: `python -m pytest tests/sandbox/test_map_elites.py -v` (5 tests PASS), puis :
```bash
git add src/seed_ai/map_elites.py src/environments/config.py tests/sandbox/test_map_elites.py
git commit -m "feat(NAS-A2): MapElitesArchive (descripteur taille x palier) + flag use_map_elites"
```

---

### Task 2: `tools/map_elites_compare.py` (bras HoF vs QD, apparié) + tests

**Files:**
- Create: `tools/map_elites_compare.py`
- Test: `tests/sandbox/test_map_elites_compare.py` (Create)

**Interfaces:**
- Consumes: `MapElitesArchive` (Task 1) ; `compute_transfer_verdict`/`_sign_test_p` (`tools.curriculum_transfer`) ; `SeedManager`, `WorldConfig`, `build_population`, `MambaAgent`, `Biosphere3D`, `calculate_life_score`, `Harness`, `async_logger`.
- Produces: `_qd_label`, `run_era_pool`, `run_lineage_hof`, `run_lineage_qd`, `compare`, `main`. Era-runner contract: `run_era_fn(cfg, genomes, max_ticks) -> (pool, metrics)` où `pool=[(score, genome, stats), ...]`, `metrics={"score","ticks"}`.

- [ ] **Step 1: Write the failing tests (faux runner, sans biosphère)**

```python
# tests/sandbox/test_map_elites_compare.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from tools.map_elites_compare import _qd_label, run_lineage_hof, run_lineage_qd, compare


def test_qd_label_mapping():
    assert _qd_label("TRANSFERE") == "QD_GAGNE"
    assert _qd_label("NUIT") == "QD_PERD"
    assert _qd_label("NEUTRE") == "NEUTRE"


def _fake_pool_runner(cfg, genomes, max_ticks):
    # score déterministe qui varie par génome (taille) -> reproductibilité testable.
    pool = [(40.0 + float(g.num_nodes % 20), g,
             {"num_nodes": g.num_nodes, "preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0})
            for g in genomes]
    best = max(p[0] for p in pool)
    return pool, {"score": best, "ticks": 200.0}


def test_arms_run_and_reproducible():
    a = run_lineage_hof(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    b = run_lineage_hof(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert a == b                                   # apparié reproductible
    c_qd, cov = run_lineage_qd(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert isinstance(c_qd, float) and cov >= 1     # archive peuplée


def test_compare_structure_and_verdict():
    out = compare(seeds=[0, 1], eras=2, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert "per_seed" in out and "verdict" in out and out["config"]["seeds"] == [0, 1]
    assert out["verdict"] in ("QD_GAGNE", "QD_PERD", "NEUTRE")
    assert all("ratio" in p and "C_hof" in p and "C_qd" in p for p in out["per_seed"])
```

- [ ] **Step 2: Run tests — verify fail**

Run: `python -m pytest tests/sandbox/test_map_elites_compare.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.map_elites_compare'`).

- [ ] **Step 3: Create `tools/map_elites_compare.py`**

```python
"""tools/map_elites_compare.py — A2 : MAP-Elites bat-il le HoF mono-objectif ? Deux bras évolutifs
appariés par seed à BUDGET ÉGAL (HoF top-5 ratchet vs archive QD), verdict + provenance.
Spec : docs/superpowers/specs/2026-06-24-NAS-A2-MapElites-design.md
Usage : MEC_SEEDS=0,1,2 MEC_ERAS=15 python tools/map_elites_compare.py"""
import os
import sys
import copy
import logging
from typing import List, Dict, Optional, Callable

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.seed_ai.map_elites import MapElitesArchive
from src.seed_ai.mutation import apply_mutations, MutationConfig
from src.seed_ai.repopulation import build_population
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.seed_ai.persistence import calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.curriculum_transfer import compute_transfer_verdict

SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0
log = logging.getLogger("AGIseed.MapElitesCompare")


def _qd_label(v: str) -> str:
    return {"TRANSFERE": "QD_GAGNE", "NUIT": "QD_PERD", "NEUTRE": "NEUTRE"}.get(v, v)


def _make_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    return cfg


def _reproduce(champ_genomes, num_agents):
    mc = MutationConfig(weight_init_std=2.0)
    heavy = copy.deepcopy(mc)
    heavy.weight_mutate_rate = min(1.0, mc.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mc.weight_mutate_power * 1.5
    return build_population(champ_genomes, num_agents, mc, apply_mutations,
                           heavy_config=heavy, heavy_frac=0.3)


def run_era_pool(cfg, genomes, max_ticks=400):
    """Mirror run_era_metab mais renvoie le POOL COMPLET avec stats (pour MAP-Elites)."""
    env = Biosphere3D(cfg)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool_agents = env.agents + list(getattr(env, "dead_agents", []))
    pool = []
    for ag in pool_agents:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is None:
            continue
        score = float(calculate_life_score(ag))
        stats = {"num_nodes": g.num_nodes, "preys_eaten": ag.get("preys_eaten", 0),
                 "spears_crafted": ag.get("spears_crafted", 0), "mammoth_kills": ag.get("mammoth_kills", 0)}
        pool.append((score, g, stats))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    best = max((p[0] for p in pool), default=0.0)
    return pool, {"score": best, "ticks": float(t)}


def _competence(window):
    tail = window[-5:] if len(window) >= 5 else window
    return float(np.mean([m["score"] for m in tail])) if tail else 0.0


def run_lineage_hof(seed, eras=15, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras HoF : cliquet top-5 (comme evolve_competence)."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    best_ever = [(0.0, g) for g in [MambaAgent().genome for _ in range(5)]]
    window = []
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, m = run_era_fn(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
        window.append(m)
    return _competence(window)


def run_lineage_qd(seed, eras=15, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras QD : archive MAP-Elites, reproduit depuis des niches diverses."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    archive = MapElitesArchive()
    genomes = [MambaAgent().genome for _ in range(num_agents)]
    window = []
    for _ in range(eras):
        pool, m = run_era_fn(cfg, genomes, max_ticks)
        for s, g, st in pool:
            archive.upsert(s, g, st)
        champ = archive.sample(5)
        genomes = _reproduce(champ, num_agents) if champ else [MambaAgent().genome for _ in range(num_agents)]
        window.append(m)
    return _competence(window), archive.coverage()


def compare(seeds, eras=15, num_agents=30, max_ticks=400, run_era_fn=None) -> Dict:
    per_seed = []
    for seed in seeds:
        c_hof = run_lineage_hof(seed, eras, num_agents, max_ticks, run_era_fn)
        c_qd, cov = run_lineage_qd(seed, eras, num_agents, max_ticks, run_era_fn)
        ratio = c_qd / max(c_hof, 1e-6)
        per_seed.append({"seed": int(seed), "C_hof": c_hof, "C_qd": c_qd, "coverage": cov, "ratio": ratio})
        log.info("seed=%s C_hof=%.2f C_qd=%.2f cov=%d ratio=%.3f", seed, c_hof, c_qd, cov, ratio)
    verdict = compute_transfer_verdict([p["ratio"] for p in per_seed])
    return {**verdict, "verdict": _qd_label(verdict["verdict"]), "per_seed": per_seed,
            "config": {"seeds": [int(s) for s in seeds], "eras": eras,
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main():
    seeds = [int(s) for s in os.environ.get("MEC_SEEDS", "0,1,2").split(",") if s.strip()]
    eras = int(os.environ.get("MEC_ERAS", "15"))
    num_agents = int(os.environ.get("MEC_NUM_AGENTS", "30"))
    max_ticks = int(os.environ.get("MEC_TICKS", "400"))
    log.info("MapElitesCompare : seeds=%s eras=%d (2 bras/seed)", seeds, eras)
    async_logger.start()
    try:
        result = compare(seeds, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    finally:
        async_logger.stop()
    h = Harness(seed=min(seeds) if seeds else 0, name="map_elites_compare", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_ratio=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_ratio"], result["n_favorable"], result["n"],
             result["sign_p"], path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 4: Run tests — verify pass**

Run: `python -m pytest tests/sandbox/test_map_elites_compare.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Smoke opt-in (vraie biosphère, 2 bras)**

Ajouter au test :
```python
import pytest
@pytest.mark.skipif(os.environ.get("MEC_SMOKE") != "1", reason="smoke lourd — set MEC_SMOKE=1")
def test_compare_smoke_real():
    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        out = compare(seeds=[0], eras=2, num_agents=6, max_ticks=30)
    finally:
        async_logger.stop()
    assert out["verdict"] in ("QD_GAGNE", "QD_PERD", "NEUTRE")
    assert out["per_seed"][0]["coverage"] >= 1
```
Run réel : `MEC_SMOKE=1 python -m pytest tests/sandbox/test_map_elites_compare.py::test_compare_smoke_real -v`
Expected: PASS (1) — les deux bras tournent sur la vraie biosphère.

- [ ] **Step 6: Run full file (smoke skipped by default) + commit**

Run: `python -m pytest tests/sandbox/test_map_elites_compare.py -v` (3 passed, 1 skipped), puis :
```bash
git add tools/map_elites_compare.py tests/sandbox/test_map_elites_compare.py
git commit -m "feat(NAS-A2): map_elites_compare (bras HoF vs QD apparie, verdict)"
```

---

## Self-Review

**1. Spec coverage :** descripteur taille×palier + Archive (upsert/sample/coverage) → Task 1 ; flag config → Task 1 ; comparaison HoF vs QD appariée + era-runner riche + verdict relabelé → Task 2 ; budget égal (mêmes eras/agents/ticks, sweet-spot) → `_make_cfg` + signatures ; non-régression (use_map_elites=False, main_biosphere non touché) → Task 1 flag + aucun edit prod. ✓

**2. Placeholder scan :** aucun ; code complet.

**3. Type consistency :** `run_era_fn(cfg,genomes,max_ticks)->(pool,metrics)` identique faux runner ↔ `run_era_pool` ↔ usage dans les deux bras ; `pool=[(score,genome,stats)]` cohérent ; `descriptor`/`upsert` signatures Task 1 ↔ usage Task 2 ; `compute_transfer_verdict` réutilisé (clé `verdict` relabelée par `_qd_label`). ✓

## Validation finale (post-impl)
```bash
python -m pytest tests/sandbox/test_map_elites.py tests/sandbox/test_map_elites_compare.py -v
MEC_SMOKE=1 python -m pytest tests/sandbox/test_map_elites_compare.py::test_compare_smoke_real -v
```
Puis (hors plan, compute) : `MEC_SEEDS=0,1,2,3,4,5,6,7 MEC_ERAS=15 python tools/map_elites_compare.py` → verdict QD_GAGNE/NEUTRE/QD_PERD. Si QD_GAGNE → câbler `main_biosphere` (itération suivante).
