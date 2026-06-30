# γ-sweep attribution de crédit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exposer le facteur d'escompte γ de l'Actor-Critic TD en knob (`MambaBatchModel.TD_GAMMA` via `EVP_GAMMA`), puis sweeper γ ∈ {0.9, 0.99, 0.999} pour trancher si l'horizon d'attribution de crédit étrangle l'émergence de la stratégie craft→apex.

**Architecture:** Un attribut de classe `MambaBatchModel.TD_GAMMA` (défaut 0.9 = non-régressif, même patron que `PLAN_BIAS`), lu dans `compute_policy_gradient` à la place du γ hardcodé, et posé par `tools/evolve_ceiling_probe.py` depuis `EVP_GAMMA`. Puis sweep × 3 seeds, lecture `frac_tool`/`frac_apex` + garde-fou santé d'apprentissage (`median_competence`/`n`).

**Tech Stack:** Python 3.13, NumPy, pytest (marqueur `slow`), env `EVP_*`/`CT_*`/`EXPERIMENT_SEED`.

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu. NE PAS stager `data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` (artefacts runtime concurrents).
- **Quiet-log** : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- **Sweet spot** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0`.
- **Non-régressif** : `TD_GAMMA` défaut **0.9** = `compute_policy_gradient` byte-identique ; `lr_actor=0.04`/`lr_critic=0.05` INCHANGÉS ; `EVP_GAMMA` absent → 0.9. Smokes existants verts.
- **Détection de succès du run par EXIT CODE python** (PAS grep sur log redirigé — piège EDR 108 : `2>/dev/null` avale `TRAJ`).
- **Anti-théâtre** : garde-fou santé d'apprentissage (un null à γ élevé doit distinguer « horizon pas le verrou » de « γ a cassé l'apprentissage ») ; le bras contrôle γ=0.9 DOIT reproduire l'apex 108/109/111 (ère0 ≈ 0.228, late ≈ 0.082) ; dose-réponse par ère.

---

### Task 1 : knob `TD_GAMMA` (modèle + probe)

**Files:**
- Modify: `src/agents/mamba_agent.py` (attribut de classe `TD_GAMMA` après `PLAN_LR` `:312` ; lecture dans `compute_policy_gradient` `:783`)
- Modify: `tools/evolve_ceiling_probe.py` (import `MambaBatchModel` `:32` ; pose `EVP_GAMMA` dans `run_evolution` après `:58`)
- Test: `tests/sandbox/test_credit_assignment_gamma.py` (créer)

**Interfaces:**
- Produces : `MambaBatchModel.TD_GAMMA: float` (attribut de classe, défaut 0.9) ; lu par `compute_policy_gradient` comme γ de `td_error` ; posé par `run_evolution` depuis `EVP_GAMMA` (défaut "0.9").

- [ ] **Step 1 : Write the failing tests**

Créer `tests/sandbox/test_credit_assignment_gamma.py` :

```python
# tests/sandbox/test_credit_assignment_gamma.py
import pytest


def test_td_gamma_default_is_09():
    """Non-régression : le défaut reste 0.9 (Actor-Critic TD historique)."""
    from src.agents.mamba_agent import MambaBatchModel
    assert MambaBatchModel.TD_GAMMA == 0.9


@pytest.mark.slow
def test_evp_gamma_propagates_to_td_update(monkeypatch):
    """EVP_GAMMA → MambaBatchModel.TD_GAMMA → γ effectivement reçu par td_error dans la boucle."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    monkeypatch.setenv("EVP_GAMMA", "0.99")
    import src.agents.mamba_agent as ma
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db

    seen = []
    real = ma.td_error

    def spy(reward, value, next_value, gamma=0.9):
        seen.append(gamma)
        return real(reward, value, next_value, gamma)

    monkeypatch.setattr(ma, "td_error", spy)
    async_logger.start()
    captured = None
    try:
        db = _acquire_shared_db()
        run_evolution("stoneage", k_eras=1, num_agents=8, max_ticks=40,
                      shared_db=db, preserve_dims=True, node_cap=512,
                      experiment_seed=0, select="elitist", n_carry=6,
                      tournament_size=3, pop_cap=40)
        captured = ma.MambaBatchModel.TD_GAMMA
    finally:
        async_logger.stop()
        ma.MambaBatchModel.TD_GAMMA = 0.9   # restaurer (attribut de classe GLOBAL)

    assert captured == 0.99                 # run_evolution a posé le knob depuis EVP_GAMMA
    assert seen, "td_error jamais appelé (l'update Actor-Critic différé n'a pas tourné)"
    assert all(g == 0.99 for g in seen), f"gamma non propagé : {sorted(set(seen))}"
```

- [ ] **Step 2 : Run tests to verify they fail**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_credit_assignment_gamma.py -v -m "slow or not slow"`
Expected : FAIL — `test_td_gamma_default_is_09` lève `AttributeError: type object 'MambaBatchModel' has no attribute 'TD_GAMMA'`.

- [ ] **Step 3 : Add the `TD_GAMMA` class attribute**

Dans `src/agents/mamba_agent.py`, juste APRÈS la ligne `PLAN_LR = 0.05    # taux d'apprentissage en ligne de g` (`:312`), ajouter :

```python
    TD_GAMMA = 0.9    # EDR 112 : facteur d'escompte du crédit temporel (Actor-Critic TD). Défaut 0.9
                      # = comportement historique ; relevé (0.99/0.999) étend l'horizon craft->apex.
```

- [ ] **Step 4 : Read the class attribute in compute_policy_gradient**

Dans `src/agents/mamba_agent.py`, `compute_policy_gradient`, remplacer la ligne (`:783`) :

```python
        lr_actor, lr_critic, gamma = 0.04, 0.05, 0.9
```

par :

```python
        lr_actor, lr_critic = 0.04, 0.05
        gamma = MambaBatchModel.TD_GAMMA          # EDR 112 : horizon de crédit (knob, défaut 0.9)
```

- [ ] **Step 5 : Wire `EVP_GAMMA` into the probe**

Dans `tools/evolve_ceiling_probe.py`, remplacer la ligne d'import (`:32`) :

```python
from src.agents.mamba_agent import MambaAgent
```

par :

```python
from src.agents.mamba_agent import MambaAgent, MambaBatchModel
```

Puis dans `run_evolution`, juste APRÈS la ligne `config.mammoth_hp = float(os.environ.get("EVP_MAMMOTH_HP", "100"))   # tool-gate EDR 111 (100 = contrôle)` (`:58`), ajouter :

```python
    MambaBatchModel.TD_GAMMA = float(os.environ.get("EVP_GAMMA", "0.9"))   # EDR 112 horizon crédit (0.9 = contrôle)
```

- [ ] **Step 6 : Run the tests to verify they pass**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_credit_assignment_gamma.py -v -m "slow or not slow"`
Expected : PASS — défaut 0.9 ; le spy voit `gamma==0.99` partout, `captured==0.99`.

- [ ] **Step 7 : Run non-regression**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py tests/sandbox/test_diverse_selection.py tests/sandbox/test_policy_gradient.py -v -m "slow or not slow"`
Expected : PASS — `EVP_GAMMA` absent → 0.9 → `compute_policy_gradient` inchangé ; les tests purs de `td_error` restent verts.

> Note : `test_evp_gamma_propagates...` restaure `TD_GAMMA=0.9` dans son `finally`, mais l'ordre des tests pourrait laisser la valeur modifiée si un run échoue. Les tests de non-régression ci-dessus tournent dans un PROCESSUS pytest séparé (commande distincte) → état de classe frais. Si lancés ensemble, le `finally` garantit le reset.

- [ ] **Step 8 : Commit (path-scoped)**

```bash
git add src/agents/mamba_agent.py tools/evolve_ceiling_probe.py tests/sandbox/test_credit_assignment_gamma.py
git commit -m "feat(agent): knob TD_GAMMA (horizon credit Actor-Critic, EDR112) via EVP_GAMMA, defaut 0.9 non-regressif

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2 : sweep γ ∈ {0.9, 0.99, 0.999} + EDR 112 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/112_<verdict>.md`

**Interfaces:**
- Consumes : Task 1 (`EVP_GAMMA` → `MambaBatchModel.TD_GAMMA`) ; sortie `results/evolve_ceiling_probe_0.json` (s'écrase).
- Produces : EDR documentant `frac_tool(ère)` + `frac_apex(ère)` + santé (`median_competence`/`n`) par valeur de γ, et le verdict (issue 1 horizon=verrou / issue 2 éliminé / issue 3 instable).

- [ ] **Step 1 : Run γ=0.9 (contrôle), seeds 0/1/2 (détection succès par exit code)**

```bash
SCRATCH="C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/eb814eca-e9fe-4f79-b0f7-d5d509e03b7b/scratchpad"
for s in 0 1 2; do
  if timeout 480 env AGISEED_QUIET_LOG=1 EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage \
      EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 \
      EVP_GAMMA=0.9 CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=$s \
      python -u tools/evolve_ceiling_probe.py > "$SCRATCH/ga_090_s${s}.log" 2>&1; then
    cp results/evolve_ceiling_probe_0.json "$SCRATCH/ga_090_s${s}.json"; echo "OK 090_s$s"
  else echo "FAIL 090_s$s (exit $?)"; fi
done
```
**Détection de succès = exit code de python** (via `if timeout ... python ...; then`), PAS un grep sur la sortie (piège EDR 108).

- [ ] **Step 2 : Run γ=0.99 puis γ=0.999, seeds 0/1/2**

Idem Step 1 avec `EVP_GAMMA=0.99` (sauver `ga_099_s${s}.json`) puis `EVP_GAMMA=0.999` (sauver `ga_0999_s${s}.json`).

- [ ] **Step 3 : Contrôle de cohérence (le bras γ=0.9 reproduit 108/109/111)**

Moyenner `frac_apex(ère)` du bras γ=0.9 (3 seeds). VÉRIFIER qu'il reproduit l'apex 108/109/111 : ère0 ≈ 0.228, ères tardives (6-11) ≈ 0.082. Si écart → signaler (non-repro). Contrôle de validité du harnais AVANT toute lecture du sweep.

- [ ] **Step 4 : Garde-fou santé d'apprentissage + lecture du sweep + verdict**

Moyenner par valeur de γ (3 seeds), trajectoire par ère :
- **Santé d'apprentissage** : `median_competence` (inclut `frac_hunt` pondéré 0.4) et `n` (population/survie) restent-ils sains à γ=0.99/0.999 ? Si la chasse de base s'effondre → INSTABILITÉ (issue 3), un null serait confondu → rapporter, NE PAS conclure « horizon pas le verrou ».
- **Dose-réponse** : `frac_tool` (le craft émerge-t-il quand l'horizon s'étend ?) ET `frac_apex` (monte-t-il avec γ ?). Forme de la courbe vs γ (monotone ? seuil vers 0.99 = horizon ~100 ticks ?).
- **Verdict** :
  - **Issue 1 (horizon = verrou RÉPARABLE)** : `frac_tool` ET `frac_apex` montent à γ élevé ET santé OK → le crédit temporel était le verrou → 1er levier qui lève l'apex.
  - **Issue 2 (horizon éliminé)** : γ↑ no-op ET santé OK → pivot connectivité (piste A) ou TD(λ).
  - **Issue 3 (instable)** : γ↑ casse la chasse → résultat confondu, rapporter l'instabilité (pas une réfutation).

- [ ] **Step 5 : Vérifier le prochain numéro EDR libre**

Run : `git fetch origin main --quiet; { ls docs/EDR/; git show origin/main:docs/EDR | tail -n +3; } | grep -oE "^11[0-9]" | sort -u | tail` — confirmer **112** libre (109 diversité comportementale, 110 capacity-nav Lewis mergé, 111 tool-gate apex).

- [ ] **Step 6 : Écrire l'EDR 112**

Créer `docs/EDR/112_<verdict>.md` : contexte (EDR 111 : substrat ne pivote pas ; hypothèse horizon de crédit, γ=0.9 → ~10 ticks ≪ chaîne craft→apex 100-300 ticks ; puzzle scaffold-déjà-actif) ; **manipulation** (knob `TD_GAMMA` 0.9→0.99→0.999, patron `PLAN_BIAS`) ; **garde-fou santé d'apprentissage** (median_competence/n par γ) ; table `frac_tool(ère)` + `frac_apex(ère)` + santé par γ ; dose-réponse vs horizon ; contrôle de cohérence (γ=0.9 = 108/109/111) ; verdict (issue 1/2/3, borné) ; liens `[[coop-competence-is-population-property]]` / `[[nas-bottleneck-is-substrate-not-search]]` + EDR 111 ; statut + suite (câbler γ prod si issue 1 ; pivot connectivité/TD(λ) si issue 2).

- [ ] **Step 7 : Commit (path-scoped)**

```bash
git add docs/EDR/112_*.md
git commit -m "docs(EDR112): gamma-sweep horizon de credit -> craft->apex emerge (horizon=verrou) ou non (substrat plus profond)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- Attribut `MambaBatchModel.TD_GAMMA` défaut 0.9, patron PLAN_BIAS (spec Unité 1) → Task 1 Step 3. ✅
- Lecture dans `compute_policy_gradient`, lr inchangés (spec Unité 1) → Task 1 Step 4. ✅
- `EVP_GAMMA` → `MambaBatchModel.TD_GAMMA` dans le probe (spec Unité 2) → Task 1 Step 5. ✅
- Sweep {0.9, 0.99, 0.999} × 3 seeds, détection par exit code (spec Unité 3) → Task 2 Steps 1-2. ✅
- Garde-fou santé d'apprentissage AVANT verdict (spec anti-théâtre) → Task 2 Step 4. ✅
- frac_tool + frac_apex dose-réponse, verdict issue 1/2/3 (spec Instrument) → Task 2 Step 4. ✅
- Cohérence contrôle γ=0.9 = 108/109/111 (spec Contrôles) → Task 2 Step 3. ✅
- Non-régression défaut 0.9 byte-identique (spec Tests) → Task 1 Steps 1, 7. ✅
- Smoke propagation du knob (spec Tests) → Task 1 Steps 1, 6. ✅
- EDR 112 (spec Variables) → Task 2 Steps 5-6. ✅

**2. Placeholder scan :** `<verdict>` (Task 2 nom de fichier) résolu en Step 4-6 (intentionnel). Pas de TBD/TODO ; code complet pour chaque step de code.

**3. Type consistency :** `TD_GAMMA` (float, attribut de CLASSE de `MambaBatchModel`) cohérent : déclaration (Step 3), lecture `gamma = MambaBatchModel.TD_GAMMA` (Step 4), pose `MambaBatchModel.TD_GAMMA = float(os.environ.get("EVP_GAMMA", "0.9"))` (Step 5), et le test (`ma.MambaBatchModel.TD_GAMMA`, spy sur `ma.td_error`). `td_error(reward, value, next_value, gamma)` signature inchangée (déjà paramétrée). Import `MambaBatchModel` ajouté à la ligne 32 du probe avant son usage Step 5. `EVP_GAMMA` défaut "0.9" cohérent avec le défaut de classe 0.9.
