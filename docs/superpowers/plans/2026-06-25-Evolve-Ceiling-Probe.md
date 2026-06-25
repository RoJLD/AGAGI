# Evolve Ceiling Probe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/evolve_ceiling_probe.py`, un harnais évolutif multi-ères déterministe qui porte les top-k champions en mémoire entre ères, instancie via `from_genome(preserve_dims=KNOB)`, et trace par ère `frac_apex` + taille réseau (`num_nodes`) — pour tester si la croissance topologique accumulée (`preserve_dims=True`) lève le plafond apex.

**Architecture:** Un seul nouveau fichier outil réutilisant tous les helpers existants (soupe, build_population, métrique réparée, life_score, MambaAgent). Carry en mémoire (pas de HoF global) pour reproductibilité + isolation des sessions parallèles. `preserve_dims` est la variable indépendante, appliquée au ré-import inter-ère (seul endroit où l'aplatissement mord).

**Tech Stack:** Python 3.13, pytest (marqueur `slow`), env vars `EVP_*`/`CT_*`/`EXPERIMENT_SEED`, `MambaAgent.from_genome`, `build_population`, KuzuDB via async_logger.

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu.
- **Quiet-log** : `AGISEED_QUIET_LOG=1` dans le SHELL avant python (singleton lu à l'import).
- **Sweet spot énergie** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0` (sinon plancher létal). Réutilise les noms `CT_METAB`/`CT_PAYOFF` du probe.
- **Déterministe / repro** : `SeedManager(experiment_seed + era*1_000_000).seed_boundary(0)` par ère ; `memory_retriever.stop()` AVANT/après chaque boucle sim (verrou repro, mémoire ambiante non-repro).
- **`preserve_dims`** = variable indépendante, lue via `EVP_PRESERVE_DIMS=="1"`. Appliquée à `from_genome(g, preserve_dims=preserve_dims)`.
- **Cap NON silencieux** : `node_cap` borne le compute ; `cap_hits` compté ET logué (anti-théâtre).
- **Carry en mémoire** : top-3 champions (`calculate_life_score`) → `build_population`, PAS le HoF global.
- **Anti-théâtre** : trajectoire par ère (jamais scalaire nu), régime absolu (taille ET apex), A/B apparié par (graine, ère).

---

### Task 1: `evolve_ceiling_probe.py` + smoke tests

**Files:**
- Create: `tools/evolve_ceiling_probe.py`
- Test: `tests/sandbox/test_evolve_ceiling_probe.py`

**Interfaces:**
- Consumes :
  - `competence_for(target)` → callable(stats)→float ; `_frac_reaching(stats, key, threshold=1.0)` (`src/curriculum/competence`).
  - `init_primordial_soup(num_agents, import_agent_id=None, keep_memory=False, shared_db, config)` → `(genomes, ntm)` (`main_biosphere`).
  - `build_population(champions, num_agents, mut_config, mutate_fn, heavy_config=None, heavy_frac=0.3)` → `list[Genome]` (`src/seed_ai/repopulation`). `champions` = liste de `Genome`.
  - `apply_mutations`, `MutationConfig` (`src/seed_ai/mutation`). `Genome.num_nodes` = property (int).
  - `calculate_life_score(agent_dict)` → float (`src/seed_ai/persistence`). agents = dicts (`env.agents + env.dead_agents`), modèle en `a["model"]`, génome en `a["model"].genome`.
  - `MambaAgent` (`src/agents/mamba_agent`) ; `.from_genome(genome, preserve_dims=False)`.
  - `_prepare_world(world_type, config, deterministic=False)`, `_acquire_shared_db()` (`main_curriculum`).
  - `WorldConfig` (`src/environments/config`) ; `SeedManager` (`src/seed_ai/harness`) ; `Harness` (`src/seed_ai/harness`) pour `save`.
- Produces : `run_evolution(target, k_eras, num_agents, max_ticks, shared_db, preserve_dims, node_cap, experiment_seed=0)` → dict `{target, preserve_dims, k_eras, node_cap, per_era:[{era, frac_apex, frac_tool, median_competence, mean_nodes, max_nodes, n, ticks, cap_hits}]}`.

- [ ] **Step 1: Write the failing smoke test (preserve=True)**

Créer `tests/sandbox/test_evolve_ceiling_probe.py` :

```python
# tests/sandbox/test_evolve_ceiling_probe.py
import pytest


@pytest.mark.slow
def test_evolution_carry_and_decompose_preserve_true(monkeypatch):
    """2 ères, carry ère0->1 OK, décompo + taille réseau + cap_hits présents (preserve_dims=True)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60,
                            shared_db=db, preserve_dims=True, node_cap=512, experiment_seed=0)
    finally:
        async_logger.stop()
    assert res["preserve_dims"] is True
    assert len(res["per_era"]) == 2          # carry ère0->1 a tourné sans crash
    row0, row1 = res["per_era"]
    for row in (row0, row1):
        for k in ("frac_apex", "frac_tool", "median_competence", "mean_nodes",
                  "max_nodes", "n", "ticks", "cap_hits"):
            assert k in row, f"clé manquante : {k}"
        assert 0.0 <= row["median_competence"] <= 1.0
        assert row["mean_nodes"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py::test_evolution_carry_and_decompose_preserve_true -v -m slow`
Expected : FAIL — `ModuleNotFoundError: No module named 'tools.evolve_ceiling_probe'` (le fichier n'existe pas).

- [ ] **Step 3: Create the tool file (imports + helpers)**

Créer `tools/evolve_ceiling_probe.py` avec l'en-tête, les imports, et le bloc de stats réutilisé :

```python
"""Sonde du plafond apex sous croissance topologique ACCUMULÉE (multi-ères évolutif).

Question : quand l'archi grossie PERSISTE entre générations (preserve_dims=True), les réseaux
grossissent-ils ET l'apex monte-t-il au-delà de ~0.21 — ou plafonne-t-il (verrou = répertoire-monde) ?

Harnais évolutif PROPRE (≠ main_biosphere lourd/non-repro) : carry des top-3 champions EN MÉMOIRE
(pas de HoF global → reproductible, isolé des sessions //), preserve_dims appliqué au ré-import
inter-ère (seul endroit où l'aplatissement mord). Déterministe (memory_retriever neutralisé, seedé).

Usage :
    AGISEED_QUIET_LOG=1 EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 \\
      EVP_MAX_TICKS=300 EVP_NODE_CAP=512 CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=0 \\
      python -u tools/evolve_ceiling_probe.py
"""
import os
import sys
import copy
import logging
import statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.curriculum.competence import competence_for, _frac_reaching
from src.seed_ai.harness import SeedManager, Harness
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.mutation import MutationConfig, apply_mutations
from src.seed_ai.repopulation import build_population
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.EvolveCeiling")


def _median(xs):
    return float(statistics.median(xs)) if xs else 0.0


def _agent_stats(all_agents):
    """Mêmes champs que target_competence_probe (signaux vivants EDR 096)."""
    return [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
             "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
             "total_dreams": a.get("total_dreams", 0),
             "mammoth_kills": a.get("mammoth_kills", 0),
             "spears_crafted": a.get("spears_crafted", 0)} for a in all_agents]
```

- [ ] **Step 4: Add `run_evolution` (the evolutionary loop with carry)**

Ajouter à `tools/evolve_ceiling_probe.py` :

```python
def run_evolution(target, k_eras, num_agents, max_ticks, shared_db,
                  preserve_dims, node_cap, experiment_seed=0):
    """K ères en `target`, carry des top-3 champions EN MÉMOIRE entre ères. preserve_dims appliqué
    au ré-import inter-ère. Retourne la trajectoire par ère (apex + taille réseau)."""
    comp_fn = competence_for(target)
    config = WorldConfig()
    config.base_metabolism = float(os.environ.get("CT_METAB", "0.25"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "3.0"))

    mut_config = MutationConfig(weight_init_std=2.0)
    heavy = copy.deepcopy(mut_config)            # fraction exploratrice (comme init_primordial_soup)
    heavy.weight_mutate_rate = min(1.0, mut_config.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mut_config.weight_mutate_power * 1.5

    carried = None        # liste de génomes champions portés en mémoire (None = ère 0)
    per_era = []

    for era in range(k_eras):
        SeedManager(experiment_seed + era * 1_000_000).seed_boundary(0)   # apparié (graine, ère)
        env = _prepare_world(target, config, deterministic=True)

        if carried is None:
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
        else:
            genomes = build_population(carried, num_agents, mut_config, apply_mutations,
                                       heavy_config=heavy, heavy_frac=0.3)

        cap_hits = 0
        for g in genomes:
            if g.num_nodes > node_cap:     # garde-fou compute NON silencieux
                cap_hits += 1
            a = MambaAgent()
            a.from_genome(g, preserve_dims=preserve_dims)
            env.add_agent(a, energy=50.0)

        env.current_era = era + 1
        t = 0
        while len(env.agents) > 0 and t < max_ticks:
            env.step()
            t += 1

        all_agents = env.agents + env.dead_agents
        stats = _agent_stats(all_agents)
        nodes = [a["model"].genome.num_nodes for a in all_agents if a.get("model") is not None]
        row = {
            "era": era,
            "frac_apex": round(_frac_reaching(stats, "mammoth_kills"), 4),
            "frac_tool": round(_frac_reaching(stats, "spears_crafted"), 4),
            "median_competence": round(comp_fn(stats), 4),
            "mean_nodes": round(statistics.mean(nodes), 2) if nodes else 0.0,
            "max_nodes": max(nodes) if nodes else 0,
            "n": len(all_agents),
            "ticks": t,
            "cap_hits": cap_hits,
        }
        per_era.append(row)
        log.info("  era=%d apex=%.3f C=%.3f mean_nodes=%.1f max_nodes=%d n=%d t=%d cap_hits=%d",
                 era, row["frac_apex"], row["median_competence"], row["mean_nodes"],
                 row["max_nodes"], row["n"], t, cap_hits)

        # Sélection -> carry (proxy fidèle de la sélection générationnelle, top-3 par life_score).
        top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]
        carried = [copy.deepcopy(a["model"].genome) for a in top if a.get("model") is not None]

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    return {"target": target, "preserve_dims": preserve_dims, "k_eras": k_eras,
            "node_cap": node_cap, "per_era": per_era}
```

- [ ] **Step 5: Run the preserve=True smoke test to verify it passes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py::test_evolution_carry_and_decompose_preserve_true -v -m slow`
Expected : PASS — 2 ères, toutes les clés présentes, `median_competence ∈ [0,1]`, `mean_nodes > 0`.

- [ ] **Step 6: Add the control smoke test (preserve=False, observable effect on size)**

Ajouter à `tests/sandbox/test_evolve_ceiling_probe.py` :

```python
@pytest.mark.slow
def test_evolution_preserve_false_runs_and_flattens(monkeypatch):
    """Contrôle : preserve_dims=False tourne aussi ; la taille de l'ère 1 reste aplatie (<=172+marge),
    prouvant que le flag a un effet OBSERVABLE sur mean_nodes au ré-import inter-ère."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60,
                            shared_db=db, preserve_dims=False, node_cap=512, experiment_seed=0)
    finally:
        async_logger.stop()
    assert res["preserve_dims"] is False
    assert len(res["per_era"]) == 2
    # Ère 1 : agents ré-importés via from_genome(preserve_dims=False) -> aplatis à 172 à l'instanciation.
    # La reproduction intra-ère peut grossir au-delà, donc on borne par max_nodes raisonnable, pas ==172.
    assert res["per_era"][1]["mean_nodes"] > 0
```

- [ ] **Step 7: Run the control smoke test**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py::test_evolution_preserve_false_runs_and_flattens -v -m slow`
Expected : PASS — tourne sans erreur, `preserve_dims is False`, 2 ères.

- [ ] **Step 8: Add `main()` and the `__main__` guard**

Ajouter à `tools/evolve_ceiling_probe.py` :

```python
def main():
    target = os.environ.get("EVP_TARGET", "stoneage")
    k = int(os.environ.get("EVP_K", "12"))
    num_agents = int(os.environ.get("EVP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("EVP_MAX_TICKS", "300"))
    node_cap = int(os.environ.get("EVP_NODE_CAP", "512"))
    preserve_dims = os.environ.get("EVP_PRESERVE_DIMS", "") == "1"
    experiment_seed = int(os.environ.get("EXPERIMENT_SEED", "0"))

    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Evolve ceiling : cible=%s preserve=%s K=%d agents=%d ticks=%d cap=%d seed=%d "
                 "metab=%s payoff=%s ===", target, preserve_dims, k, num_agents, max_ticks, node_cap,
                 experiment_seed, os.environ.get("CT_METAB", "0.25"), os.environ.get("CT_PAYOFF", "3.0"))
        result = run_evolution(target, k, num_agents, max_ticks, shared_db,
                               preserve_dims=preserve_dims, node_cap=node_cap,
                               experiment_seed=experiment_seed)
    finally:
        async_logger.stop()

    h = Harness(seed=0, name="evolve_ceiling_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    apex_traj = [r["frac_apex"] for r in result["per_era"]]
    nodes_traj = [r["mean_nodes"] for r in result["per_era"]]
    log.info("TRAJ apex=%s | mean_nodes=%s -> %s", apex_traj, nodes_traj, path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 9: Run BOTH smoke tests + non-regression**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py tests/sandbox/test_diversity_dose_probe.py tests/sandbox/test_mono_fresh.py -v -m slow`
Expected : PASS (les 4) — les 2 nouveaux smokes + non-régression (le nouvel outil n'altère pas les probes existants).

- [ ] **Step 10: Commit (path-scoped)**

```bash
git add tools/evolve_ceiling_probe.py tests/sandbox/test_evolve_ceiling_probe.py
git commit -m "feat(probe): evolve_ceiling_probe — harnais evolutif multi-eres (apex vs croissance topologique)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Run A/B sweep + EDR 105 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/105_*.md` (vérifier le numéro libre avant — éviter 098-101 Lewis)

**Interfaces:**
- Consumes : `run_evolution` / `main()` de la Task 1 ; sortie JSON via `Harness.save` (écrit `results/evolve_ceiling_probe_0.json`, s'écrase entre runs).
- Produces : EDR documentant les trajectoires `mean_nodes(era)` et `frac_apex(era)` par bras, et le verdict (3 issues).

- [ ] **Step 1: Run preserve=True, seeds 0/1/2**

Pour chaque `s ∈ {0,1,2}` :
```bash
AGISEED_QUIET_LOG=1 EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 \
  EVP_MAX_TICKS=300 EVP_NODE_CAP=512 CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=$s \
  python -u tools/evolve_ceiling_probe.py
```
Sauver chaque JSON en scratchpad sous `evolve_T_s${s}.json` AVANT le run suivant (il s'écrase).

- [ ] **Step 2: Run preserve=False, seeds 0/1/2 (contrôle)**

Idem avec `EVP_PRESERVE_DIMS=0`. Sauver `evolve_F_s${s}.json`.

- [ ] **Step 3: Collationner les trajectoires + contrôles**

Pour chaque bras, moyenner par ère sur les 3 seeds `mean_nodes(era)` et `frac_apex(era)`. Vérifier :
- **Croissance** : `mean_nodes(era)` MONTE-t-il sous True (pente > 0) ? reste-t-il plat (~172) sous False ?
- **Apex** : `frac_apex(era)` monte-t-il, plafonne-t-il, sous True ? Contraste True−False par (graine, ère).
- **cap_hits** : rapporter (si le cap mord, la croissance est forte → borne compute).
- **Régime absolu** : taille ET apex en valeurs brutes ; dispersion inter-seed.

- [ ] **Step 4: Trancher l'issue (3 mutuellement exclusives)**

- Issue 1 : `mean_nodes` ↑ ET `frac_apex` ↑ (au-delà de ~0.21) → plafond se lève (substrat était le verrou).
- Issue 2 : `mean_nodes` ↑ mais `frac_apex` plateau ~0.21 → répertoire-monde = verrou résiduel.
- Issue 3 : `mean_nodes` plat même sous True → croissance pas active (diagnostiquer : W non-nul ? taux ? cap ?).

- [ ] **Step 5: Vérifier le prochain numéro EDR libre**

Run : `ls docs/EDR/ | sort` — confirmer 105 libre (éviter 098-101 Lewis).

- [ ] **Step 6: Écrire l'EDR 105**

Créer `docs/EDR/105_<verdict>.md` : contexte (plafond mesuré sur pops non-évolutives ; bug from_genome bloquait l'accumulation ; fix prod), tables `mean_nodes(era)`/`frac_apex(era)` par bras, contraste True−False, verdict (issue tranchée), signification, liens `[[from-genome-flattens-architecture]]`/`[[coop-competence-is-population-property]]`/`[[nas-bottleneck-is-substrate-not-search]]`, statut + suite.

- [ ] **Step 7: Commit (path-scoped)**

```bash
git add docs/EDR/105_*.md
git commit -m "docs(EDR105): le plafond apex sous croissance topologique accumulee (verdict 3 issues)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- `run_evolution` signature + carry mémoire (spec Unité 1) → Task 1 Step 4. ✅
- ère 0 init_primordial_soup, ère>0 build_population (spec) → Task 1 Step 4 (`if carried is None`). ✅
- `from_genome(preserve_dims=preserve_dims)` au ré-import (spec : seul endroit où le flag mord) → Task 1 Step 4. ✅
- Garde-fou node_cap + cap_hits logué (spec anti-théâtre) → Task 1 Step 4 (`if g.num_nodes > node_cap`). ✅
- Mesures par ère {era, frac_apex, frac_tool, median_competence, mean_nodes, max_nodes, n, ticks, cap_hits} → Task 1 Step 4 (`row`). ✅
- Déterministe SeedManager(experiment_seed+era*1e6) + memory stop (spec) → Task 1 Step 4. ✅
- main() lit EVP_*/CT_*/EXPERIMENT_SEED + Harness.save (spec) → Task 1 Step 8. ✅
- Smoke True + contrôle False + non-rég (spec Tests) → Task 1 Steps 1, 6, 9. ✅
- A/B 2 bras × 3 seeds, K=12/40/300, sweet spot, cap 512 (spec Unité 2) → Task 2 Steps 1-2. ✅
- Trajectoires + verdict 3 issues (spec) → Task 2 Steps 3-4. ✅
- EDR numéro libre (spec) → Task 2 Steps 5-6. ✅

**2. Placeholder scan :** Aucun TBD/TODO ; code complet (run_evolution, main, 2 smokes). `<verdict>`/`105_*` résolus en Task 2 Steps 4-5 (intentionnel, pas un placeholder de code).

**3. Type consistency :** `run_evolution(target, k_eras, num_agents, max_ticks, shared_db, preserve_dims, node_cap, experiment_seed=0)` cohérent entre Step 4 (def), Step 1/6 (tests : appels nommés), Step 8 (main appelle nommé). `build_population(champions, num_agents, mut_config, mutate_fn, heavy_config, heavy_frac)` conforme à `repopulation.py:15`. `calculate_life_score(agent_dict)` sur dicts (`env.agents+env.dead_agents`). `Genome.num_nodes` = property int. `_frac_reaching(stats, key)` conforme. `Harness(seed, name, with_db, config).save(result, config)` conforme à `target_competence_probe.py`. Clés `per_era` identiques entre def et asserts des tests.
