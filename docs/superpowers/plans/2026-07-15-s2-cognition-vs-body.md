# S2 — Cognition ou Corps ? Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Décomposer causalement l'edge de survie 4× du champion HoF via un 2×2 GÉNOME × POLITIQUE (`verdict_cognition_body` + étude `cognition_body_study`), pour trancher : la survie vient-elle de la COGNITION (politique) ou du CORPS (génome/métabolisme) ?

**Architecture:** Additif. `verdict_cognition_body` (APPEND à `src/seed_ai/s2_stats.py`) réutilise `_compare`. `cognition_body_study` (nouveau `tools/s2_cognition_body.py`) déroule les 4 cellules via `run_condition` (réutilisé de `s2_demand`) — la seule cellule nouvelle est `champion_body` = génome champion + `RandomActionBatchModel`. NE modifie PAS `CONDITIONS` ni le verdict between-subject de `s2_demand`.

**Tech Stack:** Python, numpy, pytest. Worktree `.worktrees/s2-cogbody` (branche `chantier/s2-cognition-body`, off origin/main).

## Global Constraints

- **Additif** : APPEND à `src/seed_ai/s2_stats.py` ; CREATE `tools/s2_cognition_body.py`. NE touche PAS `mamba_agent.py`/`backend_torch.py`/`world_1_stoneage.py` ni `CONDITIONS` de `s2_demand`.
- **`verdict_cognition_body`** réutilise `_compare, ALPHA(0.05), CLIFF_THRESH(0.33)` existants. Seuils GELÉS. Verdict ∈ `{COGNITION, BODY, BOTH, NEITHER}`, non préjugé.
- **Les 4 cellules** : `champion`=(None,fresh=False) ; `champion_body`=(`RandomActionBatchModel`,fresh=False) ; `random_genome`=(None,fresh=True) ; `random_action`=(`RandomActionBatchModel`,fresh=True).
- **Injectable pour tests** : `cognition_body_study(..., run_fn=None, champion_genome=None)` → défauts `run_condition`/`load_champion_genome()` ; les tests passent un `run_fn` stub + `champion_genome` factice pour éviter la biosphère.
- **Run décisif** (hors tâches) : 5 mondes, K=12, max_ticks=200, num_agents=20, RAG-off (`_disable_kuzu`) — étape contrôleur.
- **Tree** : chemins ABSOLUS worktree pour handoffs sous-agent ; commits path-scopés ; pytest/git préfixés `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && …`.

## File Structure

- `src/seed_ai/s2_stats.py` — APPEND : `verdict_cognition_body` (T1).
- `tools/s2_cognition_body.py` — CREATE : `CELLS`, `cognition_body_study`, `_report_cogbody`, `__main__` (T2).
- `tests/sandbox/test_s2_cognition_body.py` — CREATE : verdict synthétique (T1) ; contrat de l'étude (T2).

Deux tâches : **T1** = verdict ; **T2** = étude + CLI.

---

### Task 1: `verdict_cognition_body` (décomposition 2×2)

**Files:**
- Modify: `src/seed_ai/s2_stats.py` (APPEND)
- Test: `tests/sandbox/test_s2_cognition_body.py` (CREATE)

**Interfaces:**
- Consumes : `_compare, ALPHA, CLIFF_THRESH` (déjà dans `s2_stats`).
- Produces : `verdict_cognition_body(champion, champion_body, random_genome, random_action, alpha=ALPHA, cliff_thresh=CLIFF_THRESH) -> {"verdict","policy_cmp","body_cmp","inter_cmp","policy_sig","body_sig"}`. Args = dicts de `run_condition` (`survival` poolée + `era_survival` par ère).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/sandbox/test_s2_cognition_body.py` :

```python
import numpy as np

from src.seed_ai.s2_stats import verdict_cognition_body


def _cond(center, n=12, spread=4.0):
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era}


def test_verdict_cognition():
    # C(45) >> B(12) ; B(12) ~ R(12) -> la POLITIQUE porte la survie -> COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12))
    assert r["verdict"] == "COGNITION"
    assert r["policy_sig"] and not r["body_sig"]


def test_verdict_body():
    # C(45) ~ B(44) ; B(44) >> R(12) -> le CORPS/genome porte la survie -> BODY
    r = verdict_cognition_body(_cond(45), _cond(44), _cond(20), _cond(12))
    assert r["verdict"] == "BODY"
    assert r["body_sig"] and not r["policy_sig"]


def test_verdict_both():
    # C(45) >> B(28) >> R(12) -> corps ET politique -> BOTH
    r = verdict_cognition_body(_cond(45), _cond(28), _cond(20), _cond(12))
    assert r["verdict"] == "BOTH"
    assert r["policy_sig"] and r["body_sig"]


def test_verdict_neither():
    # C(20) ~ B(20) ~ R(20) -> aucun -> NEITHER
    r = verdict_cognition_body(_cond(20), _cond(20), _cond(20), _cond(20))
    assert r["verdict"] == "NEITHER"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && python -m pytest tests/sandbox/test_s2_cognition_body.py -q`
Expected: FAIL — `ImportError: cannot import name 'verdict_cognition_body'`.

- [ ] **Step 3: Écrire le verdict**

Ajouter à `src/seed_ai/s2_stats.py` (après `verdict_from_survival_cmps` ou `verdict_within_subject`) :

```python
def verdict_cognition_body(champion, champion_body, random_genome, random_action,
                           alpha=ALPHA, cliff_thresh=CLIFF_THRESH):
    """Décompose l'edge de survie du champion : COGNITION (politique) vs CORPS (génome/métabolisme).
    2x2 GÉNOME × POLITIQUE. Réutilise `_compare` (Cliff δ + p apparié par ère).

    - `policy` = _compare(champion, champion_body) : sur le génome CHAMPION, la politique Mamba bat-elle
      les actions random ? (la survie vient-elle du FAIRE ?)
    - `body`   = _compare(champion_body, random_action) : le génome champion + actions random bat-il le
      floor random ? (la survie vient-elle de l'ÊTRE — traits corps/métabolisme ?)
    - `inter`  = _compare(random_genome, random_action) : effet politique sur génome RANDOM (corroborant
      d'interaction : si la politique aide plus avec le génome champion qu'avec un génome random -> synergie).
    Verdict (seuils gelés) : BOTH / COGNITION (politique seule) / BODY (corps seul) / NEITHER (dégénéré)."""
    policy = _compare(champion, champion_body, "survival")
    body = _compare(champion_body, random_action, "survival")
    inter = _compare(random_genome, random_action, "survival")
    policy_sig = bool((policy["p"] < alpha) and (policy["cliff"] >= cliff_thresh))
    body_sig = bool((body["p"] < alpha) and (body["cliff"] >= cliff_thresh))
    if policy_sig and body_sig:
        verdict = "BOTH"
    elif policy_sig:
        verdict = "COGNITION"
    elif body_sig:
        verdict = "BODY"
    else:
        verdict = "NEITHER"
    return {"verdict": verdict, "policy_cmp": policy, "body_cmp": body, "inter_cmp": inter,
            "policy_sig": policy_sig, "body_sig": body_sig}
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && python -m pytest tests/sandbox/test_s2_cognition_body.py -q`
Expected: PASS — 4 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody"
git add -- src/seed_ai/s2_stats.py tests/sandbox/test_s2_cognition_body.py
git commit -m "feat(S2): verdict_cognition_body — decomposition 2x2 genome x politique (T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `cognition_body_study` (étude 4 cellules + CLI)

**Files:**
- Create: `tools/s2_cognition_body.py`
- Test: `tests/sandbox/test_s2_cognition_body.py` (APPEND)

**Interfaces:**
- Consumes : `verdict_cognition_body` (T1) ; `run_condition, load_champion_genome, WORLDS` (de `tools.s2_demand`) ; `RandomActionBatchModel` (de `src.agents.baseline_models`) ; `holm` (de `src.seed_ai.s2_stats`) ; `Harness` (de `src.seed_ai.harness`) ; `_disable_kuzu` (de `tools.lethality_curriculum`).
- Produces : `CELLS` (dict des 4 cellules) ; `cognition_body_study(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=200, run_fn=None, champion_genome=None) -> report` ; `_report_cogbody(report)`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_s2_cognition_body.py` :

```python
from tools.s2_cognition_body import cognition_body_study, CELLS


def test_cells_registered():
    assert set(CELLS) == {"champion", "champion_body", "random_genome", "random_action"}
    assert CELLS["champion"]["fresh_genome"] is False
    assert CELLS["champion_body"]["fresh_genome"] is False           # MÊME génome champion
    from src.agents.baseline_models import RandomActionBatchModel
    assert CELLS["champion_body"]["batch_model_cls"] is RandomActionBatchModel
    assert CELLS["champion"]["batch_model_cls"] is None              # moteur normal


def test_study_contract_with_stub():
    # stub run_fn : evite la biosphere. Rend une survie par cellule -> verdict structurel.
    surv = {"champion": _cond(45), "champion_body": _cond(12),
            "random_genome": _cond(20), "random_action": _cond(12)}
    def stub_run(world_cls, batch_model_cls, genome, seed, num_agents, max_ticks, n_eras):
        # associe la cellule par (batch_model_cls, genome is None)
        from src.agents.baseline_models import RandomActionBatchModel
        rnd = batch_model_cls is RandomActionBatchModel
        champ = genome is not None
        key = ("champion" if (champ and not rnd) else "champion_body" if (champ and rnd)
               else "random_genome" if (not champ and not rnd) else "random_action")
        return surv[key]
    rep = cognition_body_study(worlds=["stoneage"], seed=1, K=2, num_agents=4, max_ticks=10,
                               run_fn=stub_run, champion_genome="dummy")
    w = rep["worlds"]["stoneage"]
    assert w["verdict"] in {"COGNITION", "BODY", "BOTH", "NEITHER"}
    assert w["verdict"] == "COGNITION"                              # C(45)>>B(12), B(12)~R(12)
    assert set(w["survivals"]) == set(CELLS)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && python -m pytest tests/sandbox/test_s2_cognition_body.py -k "cells_registered or study_contract" -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.s2_cognition_body'`.

- [ ] **Step 3: Écrire l'étude + le rapport + la CLI**

Créer `tools/s2_cognition_body.py` :

```python
"""tools/s2_cognition_body.py — S2 : Cognition ou Corps ?

Décompose l'edge de survie 4x du champion HoF via un 2x2 GÉNOME × POLITIQUE. La perception ayant été
écartée (S2-ablation : le champion survit sans que la perception soit causale), on tranche : la survie
vient-elle de la COGNITION (politique/ce que l'agent FAIT) ou du CORPS (génome/métabolisme/ce que l'agent
EST) ? La seule cellule nouvelle = `champion_body` (génome champion + actions RANDOM). Additif, réutilise
`run_condition` de s2_demand ; ne modifie pas CONDITIONS. RAG-off. Usage : python -m tools.s2_cognition_body
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.baseline_models import RandomActionBatchModel
from src.seed_ai.harness import Harness
from src.seed_ai.s2_stats import verdict_cognition_body, holm
from tools.s2_demand import run_condition, load_champion_genome, WORLDS

# 2x2 GÉNOME × POLITIQUE. (batch_model_cls, fresh_genome) :
#  champion       = génome champion + moteur normal (Mamba)          -> réel (~4x)
#  champion_body  = génome champion + actions RANDOM                 -> le CORPS seul (politique détruite)
#  random_genome  = génome frais    + moteur normal (Mamba)          -> politique sur corps random
#  random_action  = génome frais    + actions RANDOM                 -> floor
CELLS = {
    "champion":      {"batch_model_cls": None,                   "fresh_genome": False},
    "champion_body": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": False},
    "random_genome": {"batch_model_cls": None,                   "fresh_genome": True},
    "random_action": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": True},
}


def cognition_body_study(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=200,
                         run_fn=None, champion_genome=None):
    """Déroule les 4 cellules du 2x2 par monde et rend `verdict_cognition_body`. run_fn/champion_genome
    injectables (tests). Holm sur les p de l'effet POLITIQUE (famille des mondes). RAG-off = appelant."""
    run_fn = run_fn or run_condition
    worlds = worlds or list(WORLDS)
    champion = champion_genome if champion_genome is not None else load_champion_genome()
    report = {"seed": seed, "K": K, "worlds": {}}
    with Harness(seed=seed, name="s2_cogbody", with_db=False):
        for w in worlds:
            wcls = WORLDS[w]
            conds = {}
            for name, spec in CELLS.items():
                genome = None if spec["fresh_genome"] else champion
                conds[name] = run_fn(wcls, spec["batch_model_cls"], genome, seed,
                                     num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
            v = verdict_cognition_body(conds["champion"], conds["champion_body"],
                                       conds["random_genome"], conds["random_action"])
            v["survivals"] = {k: (float(np.median(conds[k]["survival"])) if conds[k]["survival"] else 0.0)
                              for k in CELLS}
            report["worlds"][w] = v
    decided = [w for w in worlds if report["worlds"][w].get("policy_cmp")]
    if decided:
        adj = holm([report["worlds"][w]["policy_cmp"]["p"] for w in decided])
        for w, pa in zip(decided, adj):
            report["worlds"][w]["policy_p_holm"] = float(pa)
    _report_cogbody(report)
    return report


def _report_cogbody(report):
    print("\n=== S2 — Cognition ou Corps ? 2x2 GÉNOME × POLITIQUE (seed=%s, K=%s) ===" % (report["seed"], report["K"]))
    for w, v in report["worlds"].items():
        s = v["survivals"]
        pc, bc, ic = v["policy_cmp"], v["body_cmp"], v["inter_cmp"]
        print("  %-12s : %-9s | survies champ=%.1f champ_body=%.1f rnd_genome=%.1f rnd_action=%.1f"
              % (w, v["verdict"], s["champion"], s["champion_body"], s["random_genome"], s["random_action"]))
        print("      politique (champ vs champ_body): Cliff d=%+.2f p=%.4f | corps (champ_body vs random): Cliff d=%+.2f p=%.4f"
              " | interaction (rnd_genome vs random): Cliff d=%+.2f"
              % (pc["cliff"], v.get("policy_p_holm", pc["p"]), bc["cliff"], bc["p"], ic["cliff"]))
    print("  -> COGNITION = la survie vient du FAIRE (politique) ; BODY = de l'ÊTRE (corps/génome).")


if __name__ == "__main__":
    from tools.lethality_curriculum import _disable_kuzu
    _disable_kuzu()
    cognition_body_study()
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && python -m pytest tests/sandbox/test_s2_cognition_body.py -q`
Expected: PASS — 6 tests verts (4 T1 + 2 T2).

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody"
git add -- tools/s2_cognition_body.py tests/sandbox/test_s2_cognition_body.py
git commit -m "feat(S2): cognition_body_study — etude 2x2 4 cellules + CLI (T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Run décisif (contrôleur, hors tâches TDD — après revue finale)

1. **Vérifier le champion HoF** : `HOF_PATH=".../data/hall_of_fame.pkl"` préfixé en env (setdefault trop tardif échoue).
2. **Run** (arrière-plan, ~1 h) : `cd "c:/Users/robla/VScode_Project/AGAGI/.worktrees/s2-cogbody" && HOF_PATH="c:/Users/robla/VScode_Project/AGAGI/data/hall_of_fame.pkl" python -m tools.s2_cognition_body`.
3. **Lire le verdict par monde** :
   - **BODY** (champ ≈ champ_body ≫ random) → le biosphère récompense l'ENDURANCE/corps, pas la cognition → **finding foundational** : le benchmark d'intelligence est questionnable.
   - **COGNITION** (champ ≫ champ_body ≈ random) → la survie vient de la POLITIQUE obs-indépendante → l'intelligence compte (canal non-perceptif).
   - **BOTH / interaction** (regarder `interaction Cliff` : politique plus utile sur génome champ que random → synergie).
   - Signal à investiguer : `champ_body` survivant PIRE que `random_action` (cerveau champ = poids mort sans sa politique) = signal fort de COGNITION.
4. Comparer les verdicts entre les 5 mondes (unanime ? divergent ?).
