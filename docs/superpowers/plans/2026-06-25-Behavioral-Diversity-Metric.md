# Métrique de diversité comportementale — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une métrique de diversité COMPORTEMENTALE par ère à `tools/evolve_ceiling_probe.py` (descripteurs stratégiques normalisés + décompo par conduite), puis re-run l'A/B elitist vs diverse pour trancher si le bras `diverse` préserve réellement plus de diversité — closant le caveat ouvert d'EDR 108.

**Architecture:** Un seul ajout au `row` par ère dans `run_evolution`, réutilisant `stats = _agent_stats(all_agents)` déjà calculé. Normalisation par max d'ère (évite que `age` domine), `pstdev` inter-agents par descripteur, moyenne = scalaire `behavioral_diversity` + décompo `bdiv_*`. `genome_diversity` (grossier) reste pour comparaison.

**Tech Stack:** Python 3.13, `statistics` (déjà importé), pytest (marqueur `slow`), env `EVP_*`/`CT_*`/`EXPERIMENT_SEED`.

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu.
- **Quiet-log** : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- **Sweet spot** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0`.
- **Non-régressif** : ajouter une clé au `row` ne change ni les modes, ni les verdicts, ni `genome_diversity` (conservé). Les smokes existants restent verts.
- **Normalisation par dimension OBLIGATOIRE** : diviser chaque descripteur par son max d'ère (sinon `age` ~0-300 domine `mammoth_kills` ~0-2 → on re-mesurerait la survie, pas la stratégie).
- **Détection de succès du run par EXIT CODE python** (PAS grep sur log redirigé — piège EDR 108 : `2>/dev/null` avale `TRAJ` → grep échoue → JSON non copié).
- **Anti-théâtre** : vérifier la SENSIBILITÉ de la métrique (pas au plancher) AVANT le verdict ; décompo stratégie (preys/mammoth/spears) vs survie (age) ; apex DOIT reproduire EDR 108 (cohérence).

---

### Task 1: métrique `behavioral_diversity` par ère

**Files:**
- Modify: `tools/evolve_ceiling_probe.py` (insérer le calcul après `genome_diversity` `:97`, avant le dict `row` `:98` ; ajouter 5 clés au `row` `:98-109`)
- Test: `tests/sandbox/test_behavioral_diversity.py` (créer)

**Interfaces:**
- Consumes : `stats = _agent_stats(all_agents)` (liste de dicts avec clés `age`, `preys_eaten`, `mammoth_kills`, `spears_crafted`, etc., déjà calculée dans `run_evolution` avant le `row`) ; `statistics.pstdev`/`statistics.mean` (importés).
- Produces : chaque `per_era[i]` du dict retourné par `run_evolution` gagne 5 clés : `behavioral_diversity` (float ∈ [0,1]), `bdiv_preys`, `bdiv_mammoth`, `bdiv_spears`, `bdiv_age` (floats ∈ [0,1]).

- [ ] **Step 1: Write the failing smoke test**

Créer `tests/sandbox/test_behavioral_diversity.py` :

```python
# tests/sandbox/test_behavioral_diversity.py
import pytest


@pytest.mark.slow
def test_behavioral_diversity_present_and_decomposed(monkeypatch):
    """Chaque ère rapporte behavioral_diversity + la décompo par descripteur, tous dans [0,1]."""
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
    assert len(res["per_era"]) == 2
    for row in res["per_era"]:
        for k in ("behavioral_diversity", "bdiv_preys", "bdiv_mammoth", "bdiv_spears", "bdiv_age"):
            assert k in row, f"clé manquante : {k}"
            assert 0.0 <= row[k] <= 1.0, f"{k}={row[k]} hors [0,1]"
    assert 0.0 <= res["per_era"][0]["median_competence"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_behavioral_diversity.py -v -m slow`
Expected : FAIL — `AssertionError: clé manquante : behavioral_diversity` (la clé n'existe pas encore dans le `row`).

- [ ] **Step 3: Insert the behavioral diversity computation**

Dans `tools/evolve_ceiling_probe.py`, juste APRÈS la ligne `genome_diversity = round(float(statistics.pstdev(w_means)), 4) if len(w_means) > 1 else 0.0` (`:97`) et AVANT `row = {` (`:98`), insérer :

```python
        # Diversité COMPORTEMENTALE (EDR 109) : std inter-agents de descripteurs NORMALISÉS par dimension
        # (sinon age ~0-300 domine mammoth ~0-2). Décompo -> stratégie (preys/mammoth/spears) vs survie (age).
        DESCRIPTORS = ("preys_eaten", "mammoth_kills", "spears_crafted", "age")
        bdiv = {}
        for d in DESCRIPTORS:
            vals = [s[d] for s in stats]
            vmax = max(vals) if vals else 0
            norm = [v / vmax for v in vals] if vmax > 0 else [0.0 for _ in vals]
            bdiv[d] = statistics.pstdev(norm) if len(norm) > 1 else 0.0
        behavioral_diversity = round(statistics.mean(bdiv.values()), 4) if bdiv else 0.0
```

- [ ] **Step 4: Add the 5 keys to the `row` dict**

Dans le dict `row` (`:98-109`), ajouter après la ligne `"genome_diversity": genome_diversity,` (`:108`) :

```python
            "behavioral_diversity": behavioral_diversity,
            "bdiv_preys": round(bdiv["preys_eaten"], 4),
            "bdiv_mammoth": round(bdiv["mammoth_kills"], 4),
            "bdiv_spears": round(bdiv["spears_crafted"], 4),
            "bdiv_age": round(bdiv["age"], 4),
```

- [ ] **Step 5: Add behavioral_diversity to the log line**

Remplacer la ligne `log.info(...)` (`:111-113`) pour inclure `bdiv` :

```python
        log.info("  era=%d apex=%.3f C=%.3f mean_nodes=%.1f n=%d t=%d gdiv=%.4f bdiv=%.4f",
                 era, row["frac_apex"], row["median_competence"], row["mean_nodes"],
                 row["n"], t, row["genome_diversity"], row["behavioral_diversity"])
```

- [ ] **Step 6: Run the smoke test to verify it passes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_behavioral_diversity.py -v -m slow`
Expected : PASS — 2 ères, les 5 clés présentes et ∈ [0,1], `median_competence ∈ [0,1]`.

- [ ] **Step 7: Run non-regression**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diverse_selection.py tests/sandbox/test_evolve_ceiling_probe.py -v -m slow`
Expected : PASS (les 4) — l'ajout d'une clé au `row` n'altère ni les modes, ni `genome_diversity`, ni les verdicts.

- [ ] **Step 8: Commit (path-scoped)**

```bash
git add tools/evolve_ceiling_probe.py tests/sandbox/test_behavioral_diversity.py
git commit -m "feat(probe): metrique diversite comportementale par ere (descripteurs normalises + decompo)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Re-run A/B + EDR 109 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/NNN_*.md` (vérifier le numéro libre — 108 pris par moi, 107 réservé Lewis → viser 109)

**Interfaces:**
- Consumes : `main()` de la Task 1 (mêmes env qu'EDR 108 + la nouvelle métrique dans le JSON) ; sortie `results/evolve_ceiling_probe_0.json` (s'écrase).
- Produces : EDR documentant `behavioral_diversity(era)` (+ décompo) par bras, et le verdict (issue 1 / 2).

- [ ] **Step 1: Run elitist, seeds 0/1/2 (détection succès par exit code)**

```bash
SCRATCH="C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/eb814eca-e9fe-4f79-b0f7-d5d509e03b7b/scratchpad"
for s in 0 1 2; do
  if timeout 480 env AGISEED_QUIET_LOG=1 EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage \
      EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 \
      CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=$s \
      python -u tools/evolve_ceiling_probe.py > "$SCRATCH/bdiv_E_s${s}.log" 2>&1; then
    cp results/evolve_ceiling_probe_0.json "$SCRATCH/bdiv_E_s${s}.json"; echo "OK E_s$s"
  else echo "FAIL E_s$s (exit $?)"; fi
done
```
**Détection de succès = exit code de python** (via `if timeout ... python ...; then`), PAS un grep sur la sortie (piège EDR 108).

- [ ] **Step 2: Run diverse, seeds 0/1/2**

Idem avec `EVP_SELECT=diverse`, sauver `bdiv_D_s${s}.json`.

- [ ] **Step 3: VÉRIFIER LA SENSIBILITÉ + le contraste de la métrique**

Moyenner `behavioral_diversity(era)` par bras (3 seeds). Vérifier :
- **Sensibilité** : `behavioral_diversity` est > plancher (pas ~0 comme `genome_diversity`) — sinon issue 3 (re-spécifier).
- **Contraste** : `behavioral_diversity` est-elle PLUS HAUTE sous `diverse` que `elitist` ?
- **Décompo** : quelle conduite diversifie ? `bdiv_mammoth`/`bdiv_preys`/`bdiv_spears` (stratégie) vs `bdiv_age` (survie). Rapporter les 4 par bras.

- [ ] **Step 4: Contrôle de cohérence apex + verdict**

- **Cohérence** : `frac_apex(era)` DOIT reproduire EDR 108 (mêmes seeds/params : elitist 0.228→0.082, diverse →0.097). Si écart → signaler (non-repro).
- **Verdict** :
  - Issue 1 : `diverse` PLUS divers comportementalement (stratégie) ET apex plat → **répertoire-monde CLOSE net, sélection innocentée**.
  - Issue 2 : `diverse` PAS plus divers → le tournoi ne maintient pas la diversité comportementale → sélection = levier insuffisant.

- [ ] **Step 5: Vérifier le prochain numéro EDR libre**

Run : `git fetch origin main --quiet; { ls docs/EDR/; git show origin/main:docs/EDR | tail -n +3; } | grep -oE "^1[01][0-9]" | sort -u` — confirmer 109 libre (107 réservé Lewis, 108 = moi).

- [ ] **Step 6: Écrire l'EDR 109**

Créer `docs/EDR/109_<verdict>.md` : contexte (EDR 108 caveat : `genome_diversity` trop grossier), table `behavioral_diversity(era)` + décompo par descripteur par bras, sensibilité confirmée, contraste diverse/elitist, contrôle cohérence apex (= EDR 108), verdict (issue 1 / 2), liens `[[coop-competence-is-population-property]]`/`[[nas-bottleneck-is-substrate-not-search]]` + EDR 108, statut + suite (piste 2 répertoire-monde si issue 1).

- [ ] **Step 7: Commit (path-scoped)**

```bash
git add docs/EDR/109_*.md
git commit -m "docs(EDR109): diversite comportementale -> clot issue1/2 EDR108 (selection vs repertoire-monde)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- `behavioral_diversity` (descripteurs normalisés par max d'ère, pstdev, moyenne) (spec Unité 1) → Task 1 Step 3. ✅
- Décompo `bdiv_*` par descripteur + ajout au row (spec) → Task 1 Steps 3-4. ✅
- `genome_diversity` conservé (spec) → Task 1 (non touché, row :108 reste). ✅
- Smoke (5 clés ∈ [0,1]) + non-rég (spec Tests) → Task 1 Steps 1, 6, 7. ✅
- Re-run A/B mêmes params, détection par exit code (spec Unité 2 + leçon EDR 108) → Task 2 Steps 1-2. ✅
- Vérifier sensibilité + contraste + décompo AVANT verdict (spec anti-théâtre) → Task 2 Step 3. ✅
- Cohérence apex = EDR 108 (spec) → Task 2 Step 4. ✅
- Verdict issue 1 / 2 (spec) → Task 2 Step 4. ✅
- EDR numéro libre 109 (spec) → Task 2 Steps 5-6. ✅

**2. Placeholder scan :** Aucun TBD/TODO ; code complet. `<verdict>`/`NNN` résolus en Task 2 Steps 4-5 (intentionnel).

**3. Type consistency :** `bdiv` (dict descripteur→float), `behavioral_diversity` (float), clés `row` (`behavioral_diversity`, `bdiv_preys`, `bdiv_mammoth`, `bdiv_spears`, `bdiv_age`) cohérentes entre Step 3/4 (def) et asserts du test (Step 1). `DESCRIPTORS` clés (`preys_eaten`/`mammoth_kills`/`spears_crafted`/`age`) conformes aux clés produites par `_agent_stats` (`evolve_ceiling_probe.py:38-44`). `statistics.pstdev`/`mean` déjà importés (`:19`). `stats` déjà calculé avant le row (réutilisé, pas recalculé).
