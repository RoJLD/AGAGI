# EDR 100 — Sous-décomposition de la phase biologie : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sous-décomposer la phase biologie du drain de Lewis (90% du drain, EDR 099) en `metab/terrain/carry/autres` via 6 sous-captures opt-in dans `_resolve_biology`, et étendre `tools/lewis_survival_sweep.py` pour nommer le sous-poste dominant.

**Architecture:** Extension de l'instrumentation opt-in 099 (`trace_energy_sinks`). 6 sous-captures gardées dans `_resolve_biology` accumulent `agent["_e_bio"] = {metab, terrain, carry, autres}` (télescopant vers le delta biologie). Le harnais (extension DRY) lit `_e_bio`, agrège, et mappe le sous-poste dominant (>50% du drain biologie) vers un verdict.

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR100-Biology-Subdecomposition-design.md`.

## Global Constraints

- **Mesure, pas de variable manipulée.** Condition gelée Lewis-vide : `N_APEX=0`, `forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`.
- **4 sous-postes biologie** : `metab = s0−s1` (l.637) ; `terrain = s1−s2` (l.640) ; `carry = s3−s4` (l.651) ; `autres = (s2−s3)+(s4−s5)` (gains approach/forage + jump/heal/hunt). Ils télescopent vers `s0−s5` = delta biologie. `autres`/`carry` peuvent être négatifs (gains) → pas d'assertion de non-négativité.
- **Seuil de sous-poste dominant : 50% du drain biologie** (gelé). `bio_verdict` ∈ `{"TARIF=METABOLISME", "TARIF=TERRAIN", "TARIF=CARRY", "DRAIN BIO DIFFUS"}` (ASCII).
- **Réutilise le flag `trace_energy_sinks`** (099) — aucun nouveau champ config. Sous-captures **strictement gardées** par `getattr(self.config, "trace_energy_sinks", False)` → inertes par défaut.
- **Non-régression** : les 18 tests existants (093/094/098/099) restent verts avec `trace=False`.
- **Cohérence** : `sum(_e_bio.values()) == _e_phases["biologie"]` par agent (télescopage exact).
- Reproductibilité : `_disable_kuzu()` ; `Harness(with_db=False)` ; `seed_at(s,0)` ; lecture read-only ; normalisation par âge.
- Commits path-scopés (fichier prod partagé + harnais + tests) ; `git -C add` exact, jamais `git add -A` ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `src/worlds/world_1_stoneage.py` — +6 sous-captures gardées dans `_resolve_biology` (614-751).
- **Modify:** `tools/lewis_survival_sweep.py` — `_measure_drain` (+agrégation `_e_bio`), +`_verdict_bio`, `_report_drain` (+sous-table biologie).
- **Modify:** `tests/sandbox/test_energy_trace.py` — +test sous-postes + cohérence.
- **Modify:** `tests/sandbox/test_lewis_survival_sweep.py` — +tests harnais.

---

## Task 1: 6 sous-captures `_e_bio` dans `_resolve_biology`

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`_resolve_biology`, 614-751)
- Test: `tests/sandbox/test_energy_trace.py`

**Interfaces:**
- Produces : quand `trace_energy_sinks=True`, chaque `agent` porte après un `step()` un dict cumulatif `agent["_e_bio"] = {"metab": float, "terrain": float, "carry": float, "autres": float}`, dont la somme égale `agent["_e_phases"]["biologie"]` (cohérence télescopage).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_energy_trace.py` :

```python
def test_trace_off_is_inert_bio():
    env = _mk_env(trace=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool
    assert all("_e_bio" not in ag for ag in pool)            # trace OFF -> aucun _e_bio


def test_trace_on_records_bio_subphases_and_coheres():
    env = _mk_env(trace=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_e_bio" in ag]
    assert traced, "des agents doivent porter _e_bio"
    for ag in traced:
        bio = ag["_e_bio"]
        assert set(bio) == {"metab", "terrain", "carry", "autres"}
        # coherence : somme des sous-postes = phase biologie d'EDR 099 (telescopage s0-s5)
        if "_e_phases" in ag:
            assert abs(sum(bio.values()) - ag["_e_phases"]["biologie"]) < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_energy_trace.py::test_trace_off_is_inert_bio tests/sandbox/test_energy_trace.py::test_trace_on_records_bio_subphases_and_coheres -q`
Expected: FAIL (pas de `_e_bio`).

- [ ] **Step 3: Write minimal implementation**

Dans `src/worlds/world_1_stoneage.py`, `_resolve_biology`. Insérer **6 blocs gardés**. (Toutes les ancres sont des lignes existantes ; insérer immédiatement avant/après comme indiqué.)

**3a. s0 — entrée.** Tout en haut du corps de `_resolve_biology`, juste après la signature `def _resolve_biology(self, agent, action, logits):` (l.614) et avant le commentaire `# Base drain` :

```python
    def _resolve_biology(self, agent, action, logits):
        if getattr(self.config, "trace_energy_sinks", False):
            agent["_s0_bio"] = agent["energy"]               # EDR100 : entree biologie
        # Base drain (métabolisme). EDR 084 ...
```

**3b. s1 — après le métabolisme.** Juste après la ligne `agent["energy"] -= drain` (l.637) :

```python
        agent["energy"] -= drain
        if getattr(self.config, "trace_energy_sinks", False):
            agent["_s1_bio"] = agent["energy"]               # EDR100 : apres metabolisme
```

**3c. s2 — après le terrain.** Juste après la ligne du drain de terrain (l.640, `agent["energy"] -= [self.config.biome...][terrain]`) :

```python
        agent["energy"] -= [self.config.biome.plains_drain, self.config.biome.forest_drain, self.config.biome.water_drain, self.config.biome.desert_drain][terrain]
        if getattr(self.config, "trace_energy_sinks", False):
            agent["_s2_bio"] = agent["energy"]               # EDR100 : apres terrain
```

**3d. s3/s4 — autour du carry.** Le carry est `agent["energy"] -= carry_weight * 0.5` (l.651), précédé du calcul `carry_weight = ...` (l.650). Capturer `s3` avant le calcul du poids et `s4` après la soustraction :

```python
        if getattr(self.config, "trace_energy_sinks", False):
            agent["_s3_bio"] = agent["energy"]               # EDR100 : avant carry
        carry_weight = sum(i.get("weight", 1.0) if isinstance(i, dict) else 1.0 for i in agent["inventory"])
        agent["energy"] -= carry_weight * 0.5
        if getattr(self.config, "trace_energy_sinks", False):
            agent["_s4_bio"] = agent["energy"]               # EDR100 : apres carry
```

**3e. s5 + accumulation — fin de `_resolve_biology`.** Tout à la fin de la méthode (après le bloc trésor, l.748-751, AVANT la ligne `def _resolve_social(self):` l.753) :

```python
        if agent["x"] == self.treasure_x and agent["y"] == self.treasure_y and agent.get("z", 0) == self.treasure_z and float(logits[14]) > 0:
            agent["energy"] += self.config.treasure_reward
            logger.emit("TREASURE_FOUND", {"agent_id": agent["id"]})
            self._spawn_treasure()
        if getattr(self.config, "trace_energy_sinks", False):
            _s0 = agent.get("_s0_bio", agent["energy"])
            _s1 = agent.get("_s1_bio", _s0)
            _s2 = agent.get("_s2_bio", _s1)
            _s3 = agent.get("_s3_bio", _s2)
            _s4 = agent.get("_s4_bio", _s3)
            bio = agent.setdefault("_e_bio", {"metab": 0.0, "terrain": 0.0, "carry": 0.0, "autres": 0.0})
            bio["metab"] += _s0 - _s1
            bio["terrain"] += _s1 - _s2
            bio["carry"] += _s3 - _s4
            bio["autres"] += (_s2 - _s3) + (_s4 - agent["energy"])   # gains approach/forage + jump/heal/hunt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_energy_trace.py::test_trace_off_is_inert_bio tests/sandbox/test_energy_trace.py::test_trace_on_records_bio_subphases_and_coheres -q`
Expected: PASS (sim réduite ~5-20 s). La cohérence `sum(_e_bio) == _e_phases["biologie"]` valide que `s0≈_e_prebio` et `s5≈_e_postbio` (les bornes 099).

- [ ] **Step 5: Run non-régression (énergie + harnais) + commit**

Run: `python -m pytest tests/sandbox/test_energy_trace.py tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: PASS (tous : les sous-captures sont inertes avec `trace=False`).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
git -C "$WT" add src/worlds/world_1_stoneage.py tests/sandbox/test_energy_trace.py
git -C "$WT" commit -m "feat(EDR100): 6 sous-captures _e_bio dans _resolve_biology (metab/terrain/carry/autres)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `_measure_drain` agrège `_e_bio` + `_verdict_bio`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_measure_drain` ~88-129 ; ajout `_verdict_bio`)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `agent["_e_bio"]` (Task 1).
- Produces : `_measure_drain` renvoie EN PLUS `{"bio_metab","bio_terrain","bio_carry","bio_autres"}` (moyennes énergie/tick, normalisées par âge). `_verdict_bio(agg) -> str` (4 branches) lit ces clés.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_verdict_bio_four_branches():
    base = {"bio_metab": 0, "bio_terrain": 0, "bio_carry": 0, "bio_autres": 0}
    assert lss._verdict_bio({**base, "bio_metab": 9, "bio_terrain": 1, "bio_carry": 1}) == "TARIF=METABOLISME"
    assert lss._verdict_bio({**base, "bio_terrain": 9, "bio_metab": 1, "bio_carry": 1}) == "TARIF=TERRAIN"
    assert lss._verdict_bio({**base, "bio_carry": 9, "bio_metab": 1, "bio_terrain": 1}) == "TARIF=CARRY"
    assert lss._verdict_bio({**base, "bio_metab": 4, "bio_terrain": 4, "bio_carry": 3}) == "DRAIN BIO DIFFUS"
    assert lss._verdict_bio(base) == "DRAIN BIO DIFFUS"        # bio_net <= 0 -> diffus


def test_measure_drain_has_bio_keys():
    lss._disable_kuzu()
    cfg = lss._cfg(3, trace_energy_sinks=True)
    a = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    a2 = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    for k in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        assert k in a
    # coherence agregat : somme des sous-postes ~ phase biologie
    assert abs((a["bio_metab"] + a["bio_terrain"] + a["bio_carry"] + a["bio_autres"]) - a["biologie"]) < 1e-6
    assert a == a2                                            # reproductible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_verdict_bio_four_branches tests/sandbox/test_lewis_survival_sweep.py::test_measure_drain_has_bio_keys -q`
Expected: FAIL (`AttributeError: _verdict_bio` puis clés `bio_*` manquantes).

- [ ] **Step 3: Write minimal implementation**

**3a.** Dans `_measure_drain`, ajouter la collecte `_e_bio`. Remplacer le bloc d'agrégation (lignes ~95-129) :

```python
    brain, action, biologie, mouvement = [], [], [], []
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
            mouvement.append(ph["mouvement"] / age)
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    b, a_, bio, mv = mean(brain), mean(action), mean(biologie), mean(mouvement)
    return {"brain": b, "action": a_, "biologie": bio, "mouvement": mv,
            "net": b + a_ + bio + mv, "n_agents": len(brain)}
```

par (ajout des listes `bio_*`, collecte de `_e_bio`, clés de retour) :

```python
    brain, action, biologie, mouvement = [], [], [], []
    bmetab, bterrain, bcarry, bautres = [], [], [], []
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
            mouvement.append(ph["mouvement"] / age)
            bio = ag.get("_e_bio")
            if bio:
                bmetab.append(bio["metab"] / age)
                bterrain.append(bio["terrain"] / age)
                bcarry.append(bio["carry"] / age)
                bautres.append(bio["autres"] / age)
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    b, a_, bio, mv = mean(brain), mean(action), mean(biologie), mean(mouvement)
    return {"brain": b, "action": a_, "biologie": bio, "mouvement": mv,
            "net": b + a_ + bio + mv, "n_agents": len(brain),
            "bio_metab": mean(bmetab), "bio_terrain": mean(bterrain),
            "bio_carry": mean(bcarry), "bio_autres": mean(bautres)}
```

**3b.** Ajouter `_verdict_bio` (après `_verdict_drain`) :

```python
def _verdict_bio(agg):
    """Mappe les sous-postes biologie (bio_metab/terrain/carry/autres) -> 4 branches. Le sous-poste (parmi
    metab/terrain/carry) qui porte > 50% du drain biologie nomme le coupable ; aucun (ou bio_net<=0) ->
    drain bio diffus. 'autres' (gains) n'est pas une cible de tarif."""
    bio_net = agg["bio_metab"] + agg["bio_terrain"] + agg["bio_carry"] + agg["bio_autres"]
    if bio_net <= 0:
        return "DRAIN BIO DIFFUS"
    keys = ("bio_metab", "bio_terrain", "bio_carry")
    shares = {k: agg[k] / bio_net for k in keys}
    top = max(shares, key=shares.get)
    if shares[top] <= 0.5:
        return "DRAIN BIO DIFFUS"
    return {"bio_metab": "TARIF=METABOLISME", "bio_terrain": "TARIF=TERRAIN",
            "bio_carry": "TARIF=CARRY"}[top]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_verdict_bio_four_branches tests/sandbox/test_lewis_survival_sweep.py::test_measure_drain_has_bio_keys -q`
Expected: PASS.

- [ ] **Step 5: Run non-régression (099 measure) + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_drain_keys_and_reproducible -q`
Expected: PASS (les clés 099 `{brain,action,biologie,mouvement,net,n_agents}` restent présentes ; les clés `bio_*` sont en plus).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR100): _measure_drain agrege _e_bio (bio_*) + _verdict_bio (4 branches)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_report_drain` sous-table biologie + `bio_verdict`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (`_report_drain` ~284-297)
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_measure_drain` (clés `bio_*`), `_verdict_bio`.
- Produces : `_report_drain` ajoute une sous-table biologie + `bio_verdict` au dict sauvé/retourné. `main_decompose(... _return=True)` renvoie désormais `{"phases","verdict","bio_verdict","R","n_eval"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_lewis_survival_sweep.py` :

```python
def test_main_decompose_has_bio_verdict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    assert a["phases"] == b["phases"]                         # reproductible
    assert "bio_verdict" in a
    assert a["bio_verdict"] in {"TARIF=METABOLISME", "TARIF=TERRAIN", "TARIF=CARRY", "DRAIN BIO DIFFUS"}
    for k in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        assert k in a["phases"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_decompose_has_bio_verdict -q`
Expected: FAIL (`KeyError/assert` : pas de `bio_verdict`).

- [ ] **Step 3: Write minimal implementation**

Remplacer `_report_drain` (lignes ~284-297) :

```python
def _report_drain(h, agg, R, n_eval, _return):
    """Table des 4 phases (energie/tick + part %) + verdict + provenance. Tout ASCII (cp1252)."""
    verdict = _verdict_drain(agg)
    net = agg["net"]
    print(f"\n=== EDR099 decomposition drain a N_APEX=0 (energie/tick/agent) ===")
    for ph in ("brain", "action", "biologie", "mouvement"):
        pct = (100.0 * agg[ph] / net) if net else 0.0
        print(f"  {ph:<9} | {agg[ph]:7.2f}/tick | {pct:6.1f}% du net")
    print(f"  {'NET':<9} | {net:7.2f}/tick | n_agents={agg['n_agents']}")
    print("=== VERDICT (pre-enregistre, phase >50%) ===")
    print(f"  -> {verdict}")
    h.save({"phases": agg, "verdict": verdict, "R": R, "n_eval": n_eval})
    if _return:
        return {"phases": agg, "verdict": verdict, "R": R, "n_eval": n_eval}
```

par (ajout de la sous-table biologie + `bio_verdict` ; tout ASCII) :

```python
def _report_drain(h, agg, R, n_eval, _return):
    """Table des 4 phases + sous-table biologie (EDR100) + verdicts + provenance. Tout ASCII (cp1252)."""
    verdict = _verdict_drain(agg)
    bio_verdict = _verdict_bio(agg)
    net = agg["net"]
    print(f"\n=== EDR099 decomposition drain a N_APEX=0 (energie/tick/agent) ===")
    for ph in ("brain", "action", "biologie", "mouvement"):
        pct = (100.0 * agg[ph] / net) if net else 0.0
        print(f"  {ph:<9} | {agg[ph]:7.2f}/tick | {pct:6.1f}% du net")
    print(f"  {'NET':<9} | {net:7.2f}/tick | n_agents={agg['n_agents']}")
    bio_net = agg["bio_metab"] + agg["bio_terrain"] + agg["bio_carry"] + agg["bio_autres"]
    print("=== EDR100 sous-decomposition de la phase biologie ===")
    for sp in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        pct = (100.0 * agg[sp] / bio_net) if bio_net else 0.0
        print(f"  {sp:<11} | {agg[sp]:7.2f}/tick | {pct:6.1f}% du drain bio")
    print("=== VERDICT (pre-enregistre, >50%) ===")
    print(f"  -> phases : {verdict}")
    print(f"  -> biologie : {bio_verdict}")
    h.save({"phases": agg, "verdict": verdict, "bio_verdict": bio_verdict, "R": R, "n_eval": n_eval})
    if _return:
        return {"phases": agg, "verdict": verdict, "bio_verdict": bio_verdict, "R": R, "n_eval": n_eval}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_decompose_has_bio_verdict -q`
Expected: PASS.

- [ ] **Step 5: Run le fichier complet (non-régression) + smoke console + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py tests/sandbox/test_energy_trace.py -q`
Expected: PASS (18 de 093/094/098/099 + 5 de 100 = 23 tests).

Smoke console (cp1252) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
python -c "from tools import lewis_survival_sweep as lss; lss.main_decompose(n_eval=2, R=1, seed=21)"
```
Expected : 4 phases + sous-table biologie + 2 verdicts SANS `UnicodeEncodeError`.

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR100): _report_drain sous-table biologie + bio_verdict

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Run direct (EXÉCUTION) — la sous-décomposition + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (réduit, ~1 min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print('SMOKE:', lss.main_decompose(n_eval=3, R=1, seed=21, _return=True)['bio_verdict'])" 2>/dev/null
```
Expected : 4 phases + sous-table biologie + `bio_verdict` ∈ {TARIF=METABOLISME, TARIF=TERRAIN, TARIF=CARRY, DRAIN BIO DIFFUS}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr100-biology-decompose"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main_decompose(seed=100)" 2>/dev/null
```
Expected : 4 phases + sous-table biologie (metab/terrain/carry/autres + %) + `bio_verdict`. Provenance `results/lewis_drain_decompose_100.json`.

**Sanity check à vérifier au run :** `bio_metab+terrain+carry+autres ≈ biologie` (~10.8/tick d'EDR 099). Sinon les sous-captures ratent un poste → investiguer avant de conclure.

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 100 selon la branche, et amorcer l'EDR 101 :
  - **TARIF=METABOLISME** → `base_metabolism × phenotype_energy_drain` ; EDR 101 = `phenotype_energy_drain` est-il un trait évolué inadapté ? (mesurer sa distribution dans les champions) ou rééquilibrer `base_metabolism` pour Lewis.
  - **TARIF=TERRAIN** → drains de biome ; rééquilibrer la géographie de Lewis.
  - **TARIF=CARRY** → poids d'inventaire ; pourquoi les champions accumulent-ils ?
  - **DRAIN BIO DIFFUS** → réparti ; lister les parts.

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 mesure à N_APEX=0, condition gelée → T1 (sous-hooks), T2/T3 (`_measure_drain`/`main_decompose` à `_cfg(3, trace=True)`). ✓
- §3 4 sous-postes (metab/terrain/carry/autres, télescopage) → T1 (hooks calculent les deltas), T2 (`_measure_drain` agrège, test cohérence). ✓
- §3 verdict 4 branches seuil 50% du drain bio → T2 (`_verdict_bio`), T3 (`_report_drain`). ✓
- §5 réutilise `trace_energy_sinks` (pas de nouveau champ) + sous-table → T1 (gardes), T3 (sous-table). ✓
- §5 inertie défaut OFF → T1 (`test_trace_off_is_inert_bio`), non-régression (T1/T2/T3 steps). ✓
- §6 tests (inertie, sous-postes+cohérence, verdict, measure, main) → T1/T2/T3. ✓
- §7 run direct → T4. ✓
- §8 sous-captures gardées, cohérence somme bio ≈ phase biologie, normalisation /age → T1 (gardes + test cohérence), T2 (`/age`). ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes (seul le seed du run T4 est `100` fixé ici). ✓

**3. Type consistency :** `_e_bio = {metab,terrain,carry,autres}` (T1) lu par `_measure_drain` qui produit `bio_metab/terrain/carry/autres` (T2), consommés par `_verdict_bio` (T2) et `_report_drain` (T3). `main_decompose -> {phases (avec bio_*), verdict, bio_verdict, R, n_eval}` (T3) consommé par le test. Cohérent. ✓
