# S2 — bras d'ablation-perception WITHIN-SUBJECT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Câbler un bras d'ablation-perception within-subject dans `s2_demand` (condition `champion_obs_ablated` = même champion, obs row-shufflée par tick) + un verdict CAUSAL apparié, pour rendre le verdict S2 « le monde EXIGE l'intelligence » **causal** (pas seulement between-subject).

**Architecture:** Additif. `ObsAblatedMambaBatchModel` (nouveau fichier `src/agents/ablation_models.py`) enveloppe le vrai `MambaBatchModel` et permute les lignes de `batch_obs` avant le forward. `verdict_within_subject` (ajout à `src/seed_ai/s2_stats.py`) réutilise `_compare`. `s2_demand` gagne la condition + un bloc `within` dans le rapport. **NE TOUCHE PAS** `mamba_agent.py`/`backend_torch.py`/`world_1_stoneage.py`.

**Tech Stack:** Python, numpy, pytest. Worktree `.worktrees/s2-ablation` (branche `chantier/s2-ablation`, off origin/main).

## Global Constraints

- **Additif** : CREATE `src/agents/ablation_models.py` ; APPEND à `src/seed_ai/s2_stats.py` et `tools/s2_demand.py`. AUCUNE modif de `mamba_agent.py`/`backend_torch.py`/`world_1_stoneage.py`.
- **Ablation = row-shuffle par tick** via le flux `np.random` SEEDÉ global (JAMAIS un RNG privé — comme `RandomActionBatchModel`, préserve appariement/déterminisme).
- **Le wrapper NE zéro-fixe PAS `surprise`** (contrairement aux baselines) : il délègue TOUT au forward interne → le pipeline perceptif réel du champion tourne, nourri d'obs décorrélée.
- **Seuils GELÉS** = ceux de `s2_stats` : `ALPHA=0.05`, `CLIFF_THRESH=0.33`, `EQUIV_MARGIN=0.147`. Verdict ∈ `{CAUSAL-FULL, CAUSAL-PARTIEL, NON-CAUSAL}`, non préjugé.
- **Déterminisme** : `np.random` seedé ; 2 forwards au même état RNG → même permutation.
- **Run décisif** (hors tâches) : stoneage, K=12, max_ticks=200, num_agents=20, RAG-off — étape contrôleur après revue.
- **Tree** : chemins ABSOLUS worktree pour handoffs sous-agent ; commits path-scopés ; pytest/git préfixés `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && …`.

## File Structure

- `src/agents/ablation_models.py` — CREATE : `ObsAblatedMambaBatchModel` (T1).
- `src/seed_ai/s2_stats.py` — APPEND : `verdict_within_subject` (T2).
- `tools/s2_demand.py` — APPEND : import + condition `champion_obs_ablated` + `_within_block` + intégration `run_s2`/`_print_table` (T3).
- `tests/sandbox/test_s2_ablation.py` — CREATE : wrapper (T1), verdict (T2), contrat d'intégration (T3).

Trois tâches : **T1** = wrapper d'ablation ; **T2** = verdict within-subject ; **T3** = câblage `s2_demand`.

---

### Task 1: `ObsAblatedMambaBatchModel` (wrapper d'ablation-perception)

**Files:**
- Create: `src/agents/ablation_models.py`
- Test: `tests/sandbox/test_s2_ablation.py`

**Interfaces:**
- Produces : `ObsAblatedMambaBatchModel(agents, world_model=None)` avec `.forward(batch_obs, env_surprise_batch=None) -> (logits, compute_spent)` (délègue à un `MambaBatchModel` interne après row-shuffle de `batch_obs`) et `.compute_policy_gradient(*a, **k)` (délègue).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/sandbox/test_s2_ablation.py` :

```python
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent
from src.agents.ablation_models import ObsAblatedMambaBatchModel


class _RecordingInner:
    """Stub du MambaBatchModel interne : enregistre l'obs reçue, renvoie des sorties factices."""
    def __init__(self):
        self.seen = None
    def forward(self, batch_obs, env_surprise_batch=None):
        self.seen = np.asarray(batch_obs).copy()
        B = batch_obs.shape[0]
        return np.zeros((B, 2), dtype=np.float32), np.zeros(B, dtype=np.float32)
    def compute_policy_gradient(self, *a, **k):
        self.grad_called = True
        return


def test_ablation_shuffles_rows_decorrelates():
    agents = [MambaAgent() for _ in range(8)]
    w = ObsAblatedMambaBatchModel(agents)
    w._inner = _RecordingInner()                         # intercepte l'obs vue par le champion
    obs = (np.arange(8)[:, None] * np.ones((1, 3))).astype(np.float64)   # ligne i = [i,i,i] distinctes
    non_identity = False
    for _ in range(5):
        np.random.seed(1 + _)
        w.forward(obs)
        seen = w._inner.seen
        assert seen.shape == obs.shape
        assert sorted(seen[:, 0].tolist()) == sorted(obs[:, 0].tolist())   # PERMUTATION (mêmes lignes)
        if not np.array_equal(seen, obs):
            non_identity = True
    assert non_identity                                  # le shuffle décorrèle bien (pas un no-op)


def test_ablation_determinism():
    agents = [MambaAgent() for _ in range(6)]
    obs = (np.arange(6)[:, None] * np.ones((1, 3))).astype(np.float64)
    w1 = ObsAblatedMambaBatchModel(agents); w1._inner = _RecordingInner()
    w2 = ObsAblatedMambaBatchModel(agents); w2._inner = _RecordingInner()
    np.random.seed(42); w1.forward(obs); s1 = w1._inner.seen
    np.random.seed(42); w2.forward(obs); s2 = w2._inner.seen
    assert np.array_equal(s1, s2)


def test_ablation_empty_batch():
    w = ObsAblatedMambaBatchModel([])
    w._inner = _RecordingInner()
    logits, comp = w.forward(np.zeros((0, 3), dtype=np.float64))
    assert logits.shape[0] == 0 and comp.shape[0] == 0


def test_ablation_delegates_grad():
    agents = [MambaAgent() for _ in range(4)]
    w = ObsAblatedMambaBatchModel(agents); w._inner = _RecordingInner()
    w.compute_policy_gradient(np.zeros(4))
    assert getattr(w._inner, "grad_called", False)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agents.ablation_models'`.

- [ ] **Step 3: Écrire le wrapper**

Créer `src/agents/ablation_models.py` :

```python
"""src/agents/ablation_models.py — ablation within-subject pour le benchmark S2.

ObsAblatedMambaBatchModel : drop-in de MambaBatchModel (injecté via env.batch_model_cls) qui déroule
le VRAI champion (même génome, même moteur) mais sur une obs DÉCORRÉLÉE de l'état propre (row-shuffle
par tick). C'est le témoin CAUSAL within-subject de « le monde exige la perception » (S2-001) : si la
survie du champion s'effondre à obs ablée, la perception est causalement porteuse. Additif, ne touche
pas mamba_agent/backend_torch/world_1.
"""
import numpy as np

from src.agents.mamba_agent import MambaBatchModel


class ObsAblatedMambaBatchModel:
    """Enveloppe un MambaBatchModel réel ; permute les lignes de batch_obs (agent i reçoit l'obs RÉELLE
    d'un autre) AVANT le forward -> décorrèle perception↔état propre en préservant EXACTEMENT la
    distribution marginale. Shuffle tiré du flux np.random SEEDÉ global (comme les baselines : appariement
    et déterminisme préservés, jamais un RNG privé). NE zéro-fixe PAS surprise : tout le pipeline perceptif
    réel du champion tourne, simplement nourri d'obs décorrélée."""

    def __init__(self, agents, world_model=None):
        self._inner = MambaBatchModel(agents, world_model=world_model)
        self.agents = agents

    def forward(self, batch_obs, env_surprise_batch=None):
        B = batch_obs.shape[0]
        if B == 0:
            return self._inner.forward(batch_obs, env_surprise_batch)
        perm = np.random.permutation(B)                  # décorrèle obs↔agent (flux seedé global)
        return self._inner.forward(batch_obs[perm], env_surprise_batch)

    def compute_policy_gradient(self, *args, **kwargs):
        return self._inner.compute_policy_gradient(*args, **kwargs)   # champion figé -> no-op délégué
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -q`
Expected: PASS — 4 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation"
git add -- src/agents/ablation_models.py tests/sandbox/test_s2_ablation.py
git commit -m "feat(S2): ObsAblatedMambaBatchModel — ablation-perception within-subject (T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `verdict_within_subject` (verdict CAUSAL apparié)

**Files:**
- Modify: `src/seed_ai/s2_stats.py` (APPEND)
- Test: `tests/sandbox/test_s2_ablation.py` (APPEND)

**Interfaces:**
- Consumes : `_compare, ALPHA, CLIFF_THRESH, EQUIV_MARGIN` (déjà dans `s2_stats`).
- Produces : `verdict_within_subject(champion, champion_ablated, random_action, alpha=ALPHA, cliff_thresh=CLIFF_THRESH, equiv_margin=EQUIV_MARGIN) -> {"verdict", "causal_cmp", "residual_cmp", "is_causal", "edge_fully_perceptual"}`. `champion`/`champion_ablated`/`random_action` = dicts de `run_condition` (clés `survival` poolée + `era_survival` par ère).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_s2_ablation.py` :

```python
from src.seed_ai.s2_stats import verdict_within_subject


def _cond(center, n=12, spread=4.0):
    """Condition synthétique : survie centrée sur `center` (era = n médianes, pooled = 4n individus)."""
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era}


def test_within_verdict_causal_full():
    # champion (45) >> ablaté (15) ; ablaté ~ random (14) -> perception explique TOUT -> CAUSAL-FULL
    r = verdict_within_subject(_cond(45), _cond(15), _cond(14))
    assert r["verdict"] == "CAUSAL-FULL"
    assert r["is_causal"] and r["edge_fully_perceptual"]


def test_within_verdict_causal_partiel():
    # champion (45) >> ablaté (25) ; ablaté (25) >> random (10) -> perception explique une PART -> PARTIEL
    r = verdict_within_subject(_cond(45), _cond(25), _cond(10))
    assert r["verdict"] == "CAUSAL-PARTIEL"
    assert r["is_causal"] and not r["edge_fully_perceptual"]


def test_within_verdict_non_causal():
    # champion (45) ~ ablaté (44) -> ablater la perception NE nuit PAS -> NON-CAUSAL
    r = verdict_within_subject(_cond(45), _cond(44), _cond(10))
    assert r["verdict"] == "NON-CAUSAL"
    assert not r["is_causal"]
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -k within_verdict -q`
Expected: FAIL — `ImportError: cannot import name 'verdict_within_subject'`.

- [ ] **Step 3: Écrire le verdict**

Ajouter à `src/seed_ai/s2_stats.py` (après `verdict_from_survival_cmps`) :

```python
def verdict_within_subject(champion, champion_ablated, random_action,
                           alpha=ALPHA, cliff_thresh=CLIFF_THRESH, equiv_margin=EQUIV_MARGIN):
    """Verdict CAUSAL within-subject de « le monde exige la PERCEPTION » (S2-001). Réutilise `_compare`
    (Cliff δ + p apparié par ère). Ablater la perception du MÊME champion (obs décorrélée) doit effondrer
    la survie SI la perception est causalement porteuse.

    - `causal`   = _compare(champion, champion_ablated) : le champion bat-il sa version obs-ablée ?
    - `residual` = _compare(champion_ablated, random_action) : l'ablé garde-t-il un edge sur l'aléatoire ?
    Décision (seuils gelés) :
      NON-CAUSAL     : ablater la perception NE nuit PAS (p≥α OU Cliff<thresh) -> l'edge n'était pas perceptif.
      CAUSAL-FULL    : champion≫ablé ET ablé≈random (|Cliff résiduel|<equiv_margin) -> la perception explique TOUT.
      CAUSAL-PARTIEL : champion≫ablé mais ablé garde un edge résiduel sur l'aléatoire -> la perception explique une PART.
    On ne préjuge PAS : NON-CAUSAL est un résultat falsifiable (l'edge survie viendrait d'un autre facteur)."""
    causal = _compare(champion, champion_ablated, "survival")
    residual = _compare(champion_ablated, random_action, "survival")
    is_causal = (causal["p"] < alpha) and (causal["cliff"] >= cliff_thresh)
    edge_fully_perceptual = bool(abs(residual["cliff"]) < equiv_margin)
    if not is_causal:
        verdict = "NON-CAUSAL"
    elif edge_fully_perceptual:
        verdict = "CAUSAL-FULL"
    else:
        verdict = "CAUSAL-PARTIEL"
    return {"verdict": verdict, "causal_cmp": causal, "residual_cmp": residual,
            "is_causal": bool(is_causal), "edge_fully_perceptual": edge_fully_perceptual}
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -k within_verdict -q`
Expected: PASS — 3 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation"
git add -- src/seed_ai/s2_stats.py tests/sandbox/test_s2_ablation.py
git commit -m "feat(S2): verdict_within_subject — verdict CAUSAL apparie (T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Câblage `champion_obs_ablated` + bloc `within` dans `s2_demand`

**Files:**
- Modify: `tools/s2_demand.py` (APPEND/EDIT)
- Test: `tests/sandbox/test_s2_ablation.py` (APPEND)

**Interfaces:**
- Consumes : `ObsAblatedMambaBatchModel` (T1), `verdict_within_subject` (T2), `CONDITIONS`/`run_s2`/`_print_table` (existants).
- Produces : condition `champion_obs_ablated` dans `CONDITIONS` ; `_within_block(conds) -> dict` (verdict within depuis les conditions d'un monde) ; `run_s2` ajoute `report["worlds"][w]["within"]` ; `_print_table` affiche la ligne within.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_s2_ablation.py` :

```python
from tools.s2_demand import CONDITIONS as S2_CONDITIONS, _within_block


def test_condition_registered():
    assert "champion_obs_ablated" in S2_CONDITIONS
    spec = S2_CONDITIONS["champion_obs_ablated"]
    assert spec["fresh_genome"] is False              # MÊME génome champion
    assert spec["batch_model_cls"] is ObsAblatedMambaBatchModel


def test_within_block_from_conds():
    # _within_block extrait champion / champion_obs_ablated / random_action et rend le verdict
    conds = {"champion": _cond(45), "champion_obs_ablated": _cond(15), "random_action": _cond(14)}
    r = _within_block(conds)
    assert r["verdict"] in {"CAUSAL-FULL", "CAUSAL-PARTIEL", "NON-CAUSAL"}
    assert r["verdict"] == "CAUSAL-FULL"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -k "condition_registered or within_block" -q`
Expected: FAIL — `ImportError: cannot import name '_within_block'` (ou KeyError sur la condition).

- [ ] **Step 3: Câbler la condition + le bloc within**

Dans `tools/s2_demand.py` :

(a) Ajouter aux imports (près des autres imports `src.agents`/`src.seed_ai`) :

```python
from src.agents.ablation_models import ObsAblatedMambaBatchModel
from src.seed_ai.s2_stats import verdict_within_subject
```

(b) Ajouter la condition à `CONDITIONS` (après `"reflex_prudent"`) :

```python
    "champion_obs_ablated": {"batch_model_cls": ObsAblatedMambaBatchModel, "fresh_genome": False},
```

(c) Ajouter le helper `_within_block` (avant `run_s2`) :

```python
def _within_block(conds):
    """Verdict CAUSAL within-subject d'UN monde depuis ses conditions : ablation-perception du champion.
    champion vs champion_obs_ablated (l'ablation effondre-t-elle la survie ?), corroboré par
    champion_obs_ablated vs random_action (l'ablé retombe-t-il au niveau aléatoire ?)."""
    return verdict_within_subject(conds["champion"], conds["champion_obs_ablated"], conds["random_action"])
```

(d) Dans `run_s2`, après la ligne `report["worlds"][w] = sv`, ajouter :

```python
            report["worlds"][w]["within"] = _within_block(conds)
```

(e) Dans `_print_table`, la boucle est `for w, v in report["worlds"].items():` (`v` = dict du monde ; les mondes `VOID` font `continue` plus haut → la ligne within ne s'affiche que pour les mondes non-VOID, ce qui est correct : le within n'a de sens que si le champion est un survivant cohérent). Ajouter, JUSTE APRÈS la ligne `print(f"  {w:12s} : {v['verdict']:12s} | ...")` du cas non-VOID (dernière instruction du corps de boucle) :

```python
        wi = v.get("within")
        if wi is not None:
            cc = wi["causal_cmp"]; rc = wi["residual_cmp"]
            print(f"      within (ablation-perception): {wi['verdict']:14s} "
                  f"| champion vs ablaté: Cliff d={cc['cliff']:+.2f} p={cc['p']:.4f} "
                  f"| ablaté vs random: Cliff d={rc['cliff']:+.2f}")
```

Ne rien changer d'autre dans `_print_table`.

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -m pytest tests/sandbox/test_s2_ablation.py -q`
Expected: PASS — 9 tests verts (4 T1 + 3 T2 + 2 T3).

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation"
git add -- tools/s2_demand.py tests/sandbox/test_s2_ablation.py
git commit -m "feat(S2): condition champion_obs_ablated + bloc within dans run_s2/_print_table (T3)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Run décisif (contrôleur, hors tâches TDD — après revue finale)

1. **Vérifier le champion HoF** dans le worktree : `python -c "from src.seed_ai.hall_of_fame import load_hall_of_fame; print(len(load_hall_of_fame()[1]))"` (>0 requis ; sinon localiser/pointer `HOF_PATH` vers un `hall_of_fame.pkl` peuplé).
2. **Run** (arrière-plan, ~dizaines de min) : `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-ablation" && python -c "from tools.s2_demand import run_s2; run_s2(worlds=['stoneage'], seed=2026, K=12, num_agents=20, max_ticks=200, with_db=False)"`.
3. **Lire le bloc `within`** :
   - **CAUSAL-FULL / CAUSAL-PARTIEL** → ablater la perception effondre la survie → **EXIGE devient CAUSAL in-world**, ferme le caveat « survivant ≠ marqueur », consolide EDR 124.
   - **NON-CAUSAL** → l'avantage survie du champion ne vient PAS de la perception (corps/génome/politique fixe) → finding fort à investiguer AVANT conclusion (vérifier que le champion n'est pas dégénéré ; que l'obs stoneage est bien informative).
4. Étendre aux autres mondes/seeds si CAUSAL confirmé sur stoneage.
