# Sélection diversité-préservante (apex) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre `tools/evolve_ceiling_probe.py` d'un knob de sélection (`elitist` vs `diverse`=tournoi), d'un cap de population, et d'une métrique de diversité par ère — pour tester si une sélection diversité-préservante stoppe le déclin d'apex (EDR 105) ou si l'apex plafonne quand même (→ répertoire-monde = verrou).

**Architecture:** Extension DRY du harnais évolutif existant. Trois ajouts à `run_evolution` : (1) param `select` qui remplace le carry top-3 par un tirage par tournoi sur toute la population ; (2) `config.max_population = pop_cap` (mécanisme du monde déjà existant) ; (3) `genome_diversity` par ère (garde-fou : vérifie que `diverse` mord). Défauts non-régressifs (`select="elitist"`, `pop_cap=None`).

**Tech Stack:** Python 3.13, pytest (marqueur `slow`), env `EVP_*`/`CT_*`/`EXPERIMENT_SEED`, `tournament_selection` (`src/seed_ai/evolution.py`), `config.max_population` (`world_1_stoneage.py:1552`).

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu.
- **Quiet-log** : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- **Sweet spot** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0`.
- **Défauts non-régressifs** : `select="elitist"` (carry top-3 actuel), `pop_cap=None` (pas de cap) → le comportement EDR 105 reste STRICTEMENT inchangé sans les nouveaux knobs.
- **`preserve_dims` fixé True au run** (moot apex per EDR 105, évite l'explosion qu'avait False).
- **Anti-théâtre** : `genome_diversity(era)` VÉRIFIE le mécanisme (diverse plus divers ?) AVANT tout verdict apex ; trajectoire par ère ; A/B apparié par seed ; cap pop rapporté.

---

### Task 1: knob `select` + cap population + métrique diversité

**Files:**
- Modify: `tools/evolve_ceiling_probe.py` (import `tournament_selection` ; param `select`/`n_carry`/`tournament_size`/`pop_cap` à `run_evolution` ; branche carry diverse ; `config.max_population` ; `genome_diversity` dans `row` ; `main()` lit les nouveaux env)
- Test: `tests/sandbox/test_diverse_selection.py` (créer)

**Interfaces:**
- Consumes : `tournament_selection(population, fitnesses, tournament_size=3)` → int index (`src/seed_ai/evolution.py:153`) ; `calculate_life_score(agent_dict)` → float ; `config.max_population` (int|None, consommé par `world_1_stoneage.py:1552`) ; `run_evolution` actuel (`tools/evolve_ceiling_probe.py:47`).
- Produces : `run_evolution(target, k_eras, num_agents, max_ticks, shared_db, preserve_dims, node_cap, experiment_seed=0, select="elitist", n_carry=12, tournament_size=3, pop_cap=None)` → dict avec `select`, `n_carry`, `pop_cap` en plus, et chaque `per_era[i]` avec une clé `genome_diversity`.

- [ ] **Step 1: Write the failing smoke test (diverse)**

Créer `tests/sandbox/test_diverse_selection.py` :

```python
# tests/sandbox/test_diverse_selection.py
import pytest


@pytest.mark.slow
def test_diverse_selection_runs_and_reports_diversity(monkeypatch):
    """select='diverse' (tournoi) tourne 2 ères, le carry tournoi ère0->1 ne crashe pas,
    et chaque ère rapporte genome_diversity (garde-fou mécanisme)."""
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
                            shared_db=db, preserve_dims=True, node_cap=512,
                            experiment_seed=0, select="diverse", n_carry=6,
                            tournament_size=3, pop_cap=40)
    finally:
        async_logger.stop()
    assert res["select"] == "diverse"
    assert res["n_carry"] == 6 and res["pop_cap"] == 40
    assert len(res["per_era"]) == 2
    for row in res["per_era"]:
        assert "genome_diversity" in row
        assert row["genome_diversity"] >= 0.0
    assert 0.0 <= res["per_era"][0]["median_competence"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diverse_selection.py -v -m slow`
Expected : FAIL — `run_evolution()` got an unexpected keyword argument `select` (la signature n'a pas encore ces params).

- [ ] **Step 3: Add the import**

Dans `tools/evolve_ceiling_probe.py`, après la ligne `from src.seed_ai.repopulation import build_population` (:30), ajouter :

```python
from src.seed_ai.evolution import tournament_selection
```

- [ ] **Step 4: Extend `run_evolution` signature + config cap**

Remplacer la signature (`:47-48`) et l'init config (`:52-54`) :

```python
def run_evolution(target, k_eras, num_agents, max_ticks, shared_db,
                  preserve_dims, node_cap, experiment_seed=0,
                  select="elitist", n_carry=12, tournament_size=3, pop_cap=None):
    """K ères en `target`, carry des champions EN MÉMOIRE entre ères. preserve_dims appliqué au
    ré-import inter-ère. select='elitist' (top-3) | 'diverse' (tournoi sur toute la population, EDR 105
    corollaire). pop_cap borne la repro intra-ère (config.max_population). Retourne la trajectoire."""
    comp_fn = competence_for(target)
    config = WorldConfig()
    config.base_metabolism = float(os.environ.get("CT_METAB", "0.25"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "3.0"))
    config.max_population = pop_cap     # None = pas de cap (historique) ; sinon borne le runaway (EDR 105)
```

- [ ] **Step 5: Replace the carry step with the select branch**

Remplacer le bloc carry (`:108-110`) :

```python
        # Sélection -> carry. elitist=top-3 (EDR 105 baseline) ; diverse=tournoi sur TOUTE la pop.
        pool = [a for a in all_agents if a.get("model") is not None]
        if select == "diverse" and pool:
            fits = [calculate_life_score(a) for a in pool]
            genomes_pool = [a["model"].genome for a in pool]
            idxs = [tournament_selection(genomes_pool, fits, tournament_size) for _ in range(n_carry)]
            carried = [copy.deepcopy(genomes_pool[i]) for i in idxs]
        else:
            top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]
            carried = [copy.deepcopy(a["model"].genome) for a in top if a.get("model") is not None]
```

- [ ] **Step 6: Add `genome_diversity` to the per-era row**

Dans la construction de `row` (`:92-102`), ajouter la clé `genome_diversity` (après `cap_hits`). Juste AVANT le dict `row`, calculer :

```python
        w_means = [a["model"].genome.W.mean() for a in all_agents if a.get("model") is not None]
        genome_diversity = round(float(statistics.pstdev(w_means)), 4) if len(w_means) > 1 else 0.0
```

Puis ajouter dans le dict `row` la ligne :

```python
            "genome_diversity": genome_diversity,
```

- [ ] **Step 7: Extend the return dict**

Remplacer le `return` (`:115-116`) :

```python
    return {"target": target, "preserve_dims": preserve_dims, "k_eras": k_eras,
            "node_cap": node_cap, "select": select, "n_carry": n_carry, "pop_cap": pop_cap,
            "per_era": per_era}
```

- [ ] **Step 8: Wire `main()` to read the new env vars**

Dans `main()`, après la ligne `experiment_seed = int(os.environ.get("EXPERIMENT_SEED", "0"))` (:126), ajouter :

```python
    select = os.environ.get("EVP_SELECT", "elitist")
    n_carry = int(os.environ.get("EVP_N_CARRY", "12"))
    tournament_size = int(os.environ.get("EVP_TOURNAMENT", "3"))
    _cap_env = os.environ.get("EVP_POP_CAP", "")
    pop_cap = int(_cap_env) if _cap_env else None
```

Et passer ces params à `run_evolution` (remplacer l'appel `:135-137`) :

```python
        result = run_evolution(target, k, num_agents, max_ticks, shared_db,
                               preserve_dims=preserve_dims, node_cap=node_cap,
                               experiment_seed=experiment_seed, select=select,
                               n_carry=n_carry, tournament_size=tournament_size, pop_cap=pop_cap)
```

Mettre à jour la ligne de log d'en-tête (`:132-134`) pour inclure `select` et `pop_cap` :

```python
        log.info("=== Evolve ceiling : cible=%s preserve=%s K=%d agents=%d ticks=%d cap=%d seed=%d "
                 "select=%s n_carry=%d pop_cap=%s metab=%s payoff=%s ===", target, preserve_dims, k,
                 num_agents, max_ticks, node_cap, experiment_seed, select, n_carry, pop_cap,
                 os.environ.get("CT_METAB", "0.25"), os.environ.get("CT_PAYOFF", "3.0"))
```

- [ ] **Step 9: Run the diverse smoke test to verify it passes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diverse_selection.py -v -m slow`
Expected : PASS — `select=="diverse"`, `n_carry==6`, `pop_cap==40`, 2 ères, `genome_diversity` présent, `median_competence ∈ [0,1]`.

- [ ] **Step 10: Add the elitist control smoke test**

Ajouter à `tests/sandbox/test_diverse_selection.py` :

```python
@pytest.mark.slow
def test_elitist_default_unchanged_with_diversity_metric(monkeypatch):
    """Le défaut select='elitist' tourne (carry top-3 EDR105) et rapporte aussi genome_diversity."""
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
    assert res["select"] == "elitist"        # défaut non-régressif
    assert res["pop_cap"] is None
    assert "genome_diversity" in res["per_era"][0]
```

- [ ] **Step 11: Run the elitist smoke + non-regression**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diverse_selection.py tests/sandbox/test_evolve_ceiling_probe.py -v -m slow`
Expected : PASS (les 4) — 2 nouveaux smokes + les 2 smokes EDR 105 existants (défaut `select="elitist"`, `pop_cap=None` → comportement inchangé).

- [ ] **Step 12: Commit (path-scoped)**

```bash
git add tools/evolve_ceiling_probe.py tests/sandbox/test_diverse_selection.py
git commit -m "feat(probe): selection diverse (tournoi) + cap pop + metrique diversite (evolve_ceiling)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Run A/B elitist vs diverse + EDR 108 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/NNN_*.md` (vérifier le numéro libre avant — 104/105 pris par moi, 106 pris, 107 réservé Lewis → viser 108)

**Interfaces:**
- Consumes : `run_evolution` / `main()` de la Task 1 (`EVP_SELECT`/`EVP_N_CARRY`/`EVP_TOURNAMENT`/`EVP_POP_CAP`) ; sortie JSON via `Harness.save` (`results/evolve_ceiling_probe_0.json`, s'écrase).
- Produces : EDR documentant `genome_diversity(era)` (mécanisme) + `frac_apex(era)` (verdict) par bras.

- [ ] **Step 1: Run elitist, seeds 0/1/2 (baseline EDR 105)**

Pour chaque `s ∈ {0,1,2}` :
```bash
AGISEED_QUIET_LOG=1 EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 \
  EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 CT_METAB=0.25 CT_PAYOFF=3.0 \
  EXPERIMENT_SEED=$s python -u tools/evolve_ceiling_probe.py
```
Sauver chaque JSON en scratchpad sous `divsel_E_s${s}.json`.

- [ ] **Step 2: Run diverse, seeds 0/1/2**

Idem avec `EVP_SELECT=diverse EVP_N_CARRY=12 EVP_TOURNAMENT=3`. Sauver `divsel_D_s${s}.json`.

- [ ] **Step 3: VÉRIFIER LE MÉCANISME D'ABORD — genome_diversity**

Moyenner `genome_diversity(era)` par bras sur les 3 seeds. **Le bras `diverse` doit être PLUS DIVERS que `elitist`** (sinon issue 3 : knob inerte → STOP, re-designer avant tout verdict apex). Rapporter la trajectoire de diversité par bras.

- [ ] **Step 4: Trancher l'apex (seulement si le mécanisme mord)**

Si `diverse` est bien plus divers : comparer `frac_apex(era)` par bras (contraste apparié par seed/ère, sign-test) ET le déclin (ère0 → ères6-11) :
- Issue 1 : `diverse` STOPPE le déclin / lève l'apex (vs elitist 0.228→0.082) → sélection était le coupable, plafond partiellement artefact → reframe.
- Issue 2 : `diverse` décline/plateau quand même → sélection innocentée → **répertoire-monde confirmé**.
Contrôle de cohérence : le bras `elitist` doit reproduire le déclin d'EDR 105 (≈0.228→0.082).

- [ ] **Step 5: Vérifier le prochain numéro EDR libre**

Run : `git fetch origin main --quiet; { ls docs/EDR/; git show origin/main:docs/EDR | tail -n +3; } | grep -oE "^1[01][0-9]" | sort -u` — confirmer 108 libre (107 réservé Lewis).

- [ ] **Step 6: Écrire l'EDR 108**

Créer `docs/EDR/108_<verdict>.md` : contexte (EDR 105 corollaire : élitisme érode la diversité → apex décline), table `genome_diversity(era)` (mécanisme vérifié) + `frac_apex(era)` par bras, verdict (issue tranchée), signification, liens `[[coop-competence-is-population-property]]`/`[[nas-bottleneck-is-substrate-not-search]]` + EDR 105, statut + suite (si issue 2 → enrichissement monde ; si issue 1 → sélection diverse en prod).

- [ ] **Step 7: Commit (path-scoped)**

```bash
git add docs/EDR/108_*.md
git commit -m "docs(EDR108): selection diverse vs elitiste -> apex (verdict mecanisme+issue)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- Knob `select` (elitist/diverse=tournoi) (spec Unité 1) → Task 1 Steps 4-5. ✅
- Tournoi sur `all_agents` via `tournament_selection` (spec) → Task 1 Step 5 (`pool`/`fits`/`genomes_pool`/`idxs`). ✅
- Cap population `config.max_population = pop_cap` (spec Unité 2, réutilise l'existant) → Task 1 Step 4. ✅
- `genome_diversity` par ère (spec Unité 3, garde-fou) → Task 1 Step 6. ✅
- `main()` lit EVP_SELECT/N_CARRY/TOURNAMENT/POP_CAP + result inclut select/n_carry/pop_cap (spec) → Task 1 Steps 7-8. ✅
- Smoke diverse + smoke elitist + non-rég (spec Tests) → Task 1 Steps 1, 10, 11. ✅
- A/B 2 bras × 3 seeds, preserve=1, K=12/40/300, pop_cap=200, sweet spot (spec Unité 4) → Task 2 Steps 1-2. ✅
- VÉRIFIER diversité AVANT apex (spec anti-théâtre, issue 3) → Task 2 Steps 3-4. ✅
- Contrôle cohérence elitist=EDR105 (spec) → Task 2 Step 4. ✅
- EDR numéro libre 108 (spec) → Task 2 Steps 5-6. ✅

**2. Placeholder scan :** Aucun TBD/TODO ; code complet. `<verdict>`/`NNN` résolus en Task 2 Steps 4-5 (intentionnel).

**3. Type consistency :** `run_evolution(..., select="elitist", n_carry=12, tournament_size=3, pop_cap=None)` cohérent entre Step 4 (def), Steps 1/10 (tests, appels nommés), Step 8 (main). `tournament_selection(genomes_pool, fits, tournament_size)` → int conforme à `evolution.py:153`. `config.max_population` int|None conforme à `config.py:46`. `genome.W.mean()` (numpy) cohérent avec `main_biosphere:334`. Clés `per_era` (ajout `genome_diversity`) cohérentes entre Step 6 et asserts des tests. `pstdev` de `statistics` (déjà importé `:19`).
