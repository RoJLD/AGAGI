# Re-run 3-way avec preserve_dims — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Câbler un knob `CT_PRESERVE_DIMS` dans `target_competence_probe`, puis re-faire le 3-way (tabula/champion/mono_fresh) avec l'architecture du génome PRÉSERVÉE pour trancher le caveat d'EDR 102 (l'avantage apex du champion était-il masqué par l'aplatissement `from_genome` ?).

**Architecture:** Tâche 1 = ajouter `PRESERVE_DIMS = os.environ.get("CT_PRESERVE_DIMS","")=="1"` + passer `preserve_dims=PRESERVE_DIMS` aux 3 appels `from_genome` de `run_probe` (pattern identique à `MEC_/MCS_PRESERVE_DIMS`). Défaut OFF → comportement aplati inchangé. Tâche 2 = run 3-way avec le flag ON + EDR.

**Tech Stack:** Python 3.13, pytest. Réutilise la métrique vivante réparée, les modes `tabula`/`champion`/`mono_fresh`, la décompo apex/lance.

## Global Constraints

- **Pattern établi** : `PRESERVE_DIMS = os.environ.get("CT_PRESERVE_DIMS","")=="1"` (cf. `map_elites_compare.py:38`, `metabolic_cost_sweep.py:75`). `from_genome(genome, preserve_dims=False)` existe (`src/agents/mamba_agent.py:136`).
- **Défaut OFF** (chaîne vide) → comportement APLATI actuel STRICTEMENT inchangé (non-régressif ; les runs aplatis d'EDR 102 restent reproductibles sans le flag).
- **Risque** : `preserve_dims=True` peut échouer si les dims du génome sont incompatibles avec l'env → le smoke (mode champion, flag ON) le révèle (échec visible, pas silencieux).
- **Anti-théâtre** : décompo `frac_apex`/`frac_tool` par ère (déjà câblée), apparié par seed (même `SeedManager(i)`), 3-way. Rapporter aussi le RÉGIME absolu si `preserve_dims` change la perf des 3 bras (pas juste l'écart).
- **Tree partagé** : commits **pathspec-limités** `git commit <paths> -m`. Branche `feat/d1-prod-pairing`.
- **Fichiers** : `tools/target_competence_probe.py` (modif) ; `tests/sandbox/test_preserve_dims_probe.py` (nouveau).

---

## File Structure

- **Modify** `tools/target_competence_probe.py` — `PRESERVE_DIMS` en tête + `preserve_dims=PRESERVE_DIMS` aux 3 appels `from_genome` de `run_probe`.
- **Create** `tests/sandbox/test_preserve_dims_probe.py` — smoke `slow` (mode champion, flag ON, tourne sans erreur + décompo).

---

### Task 1: Câbler `CT_PRESERVE_DIMS`

**Files:**
- Modify: `tools/target_competence_probe.py` (constante en tête + 3 appels `from_genome` dans `run_probe`)
- Test: `tests/sandbox/test_preserve_dims_probe.py`

**Interfaces:**
- Consumes: `from_genome(genome, preserve_dims=False)` (`src/agents/mamba_agent.py:136`), `run_probe` (existant).
- Produces: `run_probe` honore `CT_PRESERVE_DIMS=1` → charge les génomes en préservant leur architecture aux 3 modes ; défaut OFF inchangé.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/sandbox/test_preserve_dims_probe.py
import pytest


@pytest.mark.slow
def test_probe_runs_with_preserve_dims(monkeypatch):
    """Garde-fou : mode champion avec CT_PRESERVE_DIMS=1 tourne SANS erreur (dims compatibles avec
    l'env) et sort la décompo. Valide le câblage ET le risque dims."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    monkeypatch.setenv("CT_PRESERVE_DIMS", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=20, max_ticks=80, shared_db=db, mode="champion")
    finally:
        async_logger.stop()
    assert res["mode"] == "champion" and res["per_era"]
    row = res["per_era"][0]
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
```

- [ ] **Step 2: Note sur la nature du test (smoke d'intégration / garde-fou risque)**

Ce test PASSERAIT déjà avant le câblage (le flag est lu mais ignoré → mode champion aplati, forme
valide). Son rôle réel : (a) après câblage, prouver que `preserve_dims=True` ne CASSE pas l'exécution
(risque dims incompatibles), et (b) garder la forme du retour. NE PAS forcer un faux « expected FAIL ».
Procéder au Step 3 puis Step 4 (le smoke doit PASSER, et il valide le non-crash sous preserve_dims).

- [ ] **Step 3: Ajouter la constante `PRESERVE_DIMS` en tête de `run_probe` ou du module**

Dans `tools/target_competence_probe.py`, repérer la fonction `run_probe` et, juste après la lecture de
`config.base_metabolism`/`config.forage_payoff` (les autres lectures d'env de la fonction), ajouter la
lecture du flag. Repérer le bloc actuel :

```python
    config.base_metabolism = float(os.environ.get("CT_METAB", "1.0"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "1.0"))
    champ_g = _champion_genome() if mode == "champion" else None
```

et le remplacer par (ajout d'UNE ligne `preserve_dims` après `forage_payoff`) :

```python
    config.base_metabolism = float(os.environ.get("CT_METAB", "1.0"))
    config.forage_payoff = float(os.environ.get("CT_PAYOFF", "1.0"))
    preserve_dims = os.environ.get("CT_PRESERVE_DIMS", "") == "1"   # NAS substrat : garde l'archi du genome (EDR 102 caveat)
    champ_g = _champion_genome() if mode == "champion" else None
```

- [ ] **Step 4: Passer `preserve_dims` aux 3 appels `from_genome`**

Dans `run_probe`, les 3 appels sont dans le bloc de peuplement. Remplacer chacun :

Site champion :
```python
                a.from_genome(champ_g)
```
par :
```python
                a.from_genome(champ_g, preserve_dims=preserve_dims)
```

Site mono_fresh :
```python
                a.from_genome(mono_g)
```
par :
```python
                a.from_genome(mono_g, preserve_dims=preserve_dims)
```

Site tabula :
```python
                a.from_genome(g)
```
par :
```python
                a.from_genome(g, preserve_dims=preserve_dims)
```

(NB : `preserve_dims` est la variable locale du Step 3, en minuscules — pas la constante module
`PRESERVE_DIMS` des autres tools. Cohérent, car elle est lue dans `run_probe`.)

- [ ] **Step 5: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_preserve_dims_probe.py -q -p no:cacheprovider`
Expected: PASS (~10-40 s). Si ÉCHEC avec une erreur de dimensions → `preserve_dims` est incompatible
avec l'env stoneage ; STOPPER et rapporter (le run réel serait impossible — finding en soi).

- [ ] **Step 6: Non-régression (défaut OFF inchangé)**

Run: `python -m pytest tests/sandbox/test_mono_fresh.py tests/sandbox/test_live_harvest.py -q -p no:cacheprovider`
Expected: PASS (sans le flag, `preserve_dims=False` → comportement aplati strictement inchangé).

- [ ] **Step 7: Commit**

```bash
git commit tools/target_competence_probe.py tests/sandbox/test_preserve_dims_probe.py -m "feat(probe): knob CT_PRESERVE_DIMS (garde l'archi du genome aux 3 modes, caveat EDR 102)"
```

---

### Task 2: Run 3-way préservé + EDR (pas de code)

**Files:** aucun (exécution + EDR).

- [ ] **Step 1: Lancer les 3 bras avec `CT_PRESERVE_DIMS=1` (même config qu'EDR 102)**

Lancer SUCCESSIVEMENT (chaque run écrase `results/target_competence_probe_0.json`, seed=0 — sauvegarder
entre chaque) :

```bash
AGISEED_QUIET_LOG=1 CT_PRESERVE_DIMS=1 CT_TARGET=stoneage CT_MODE=tabula CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py
# sauvegarder results/target_competence_probe_0.json -> P_tabula.json
AGISEED_QUIET_LOG=1 CT_PRESERVE_DIMS=1 CT_TARGET=stoneage CT_MODE=champion CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py
# sauvegarder -> P_champion.json
AGISEED_QUIET_LOG=1 CT_PRESERVE_DIMS=1 CT_TARGET=stoneage CT_MODE=mono_fresh CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py
# sauvegarder -> P_monofresh.json
```

Expected : 3 runs sans erreur, chacun `VERDICT=... median_C=...` + per-era `frac_apex`/`frac_tool`.

- [ ] **Step 2: Comparaison + verdict (apparié par seed/ère)**

Référence APLATIE EDR 102 : tabula apex 0.211 / C 0.313 ; champion apex 0.162 / C 0.256 ; mono_fresh
apex 0.158 / C 0.246. Comparer les bras PRÉSERVÉS :

- **champion préservé > mono_fresh ET > tabula** (apex et/ou median_C, contraste apparié par ère) →
  **ARCHITECTURALE** : l'archi évoluée du champion porte une compétence apex masquée par l'aplatissement
  → EDR 102 sous-estimait le génome (reframe).
- **champion préservé ≈ mono_fresh préservé** (sign_p élevé) → **MONOCULTURE robuste** même avec l'archi
  → EDR 102 confirmé/renforcé.
- **RÉGIME ABSOLU** : si `preserve_dims` change la perf des 3 bras (ex. tous montent/descendent vs
  EDR 102 aplati), le rapporter — c'est un changement de régime, pas seulement un contraste.

Rapporter la décompo apex/lance par ère des 3 bras + le contraste apparié (champion−mono_fresh,
champion−tabula). Jamais le scalaire nu. n=8.

- [ ] **Step 3: Écrire l'EDR** (numéro **103** — éviter 098-101 pris par l'arc Lewis/métabolisme et
  100/102 déjà pris) et committer (pathspec-limité). Lier à EDR 102 et au caveat `from_genome`.

---

## Self-Review

**Spec coverage :** câblage `CT_PRESERVE_DIMS` (constante + 3 sites) → Task 1 Steps 3-4 ; smoke /
garde-fou risque dims → Task 1 Step 1/5 ; non-régression défaut OFF → Step 6 ; run 3-way préservé +
verdict ARCHITECTURALE/MONOCULTURE + régime absolu → Task 2 ; EDR → Task 2 Step 3. Garde-fous : apparié,
décompo par ère, défaut OFF non-régressif. ✓

**Placeholder scan :** aucun TODO/TBD ; blocs à remplacer cités verbatim ; commandes de run exactes. La
note du Step 2 (smoke non-rouge) est une mise en garde honnête, pas un placeholder. ✓

**Type consistency :** `preserve_dims` (variable locale de `run_probe`, Step 3) passée à
`from_genome(genome, preserve_dims=...)` (signature existante mamba_agent.py:136) aux 3 sites (Step 4).
`run_probe(..., mode=...)` renvoie le même dict (`mode`, `median_competence`, `per_era` avec
`frac_apex`/`frac_tool`/`total_mammoth`/`total_spears`) consommé par le smoke. ✓
