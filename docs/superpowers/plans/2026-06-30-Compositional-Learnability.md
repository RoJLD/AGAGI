# Learnabilité compositionnelle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si un substrat torch (autograd) apprend une contingence COMPOSITIONNELLE means→ends (proxy de l'apex craft→chasse) qu'un substrat legacy (hebbien/Actor-Critic TD numpy, ~5 cachés) NE peut pas — porte de décision avant le gros chantier torch-en-prod.

**Architecture:** Un nouveau banc `tools/substrate_ab_compositional.py` qui RÉUTILISE le backend abstrait livré (`make_population(backend=)`) et `compute_ab_verdict` de `substrate_ab.py`, SANS les modifier. Tâche 2-étapes (S1: action X, récompense 0 → S2: action Y récompensée SSI X fait en S1, X mémorisé par la récurrence). A/B apparié legacy vs torch.

**Tech Stack:** Python 3.13, NumPy, PyTorch 2.6 (déjà dans l'env), pytest (`slow` + `importorskip`).

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu. NE PAS stager `data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` (artefacts runtime concurrents).
- **NE PAS modifier** `src/agents/backend.py`, `src/agents/backend_torch.py`, `tools/substrate_ab.py` (propriété session // ; on IMPORTE seulement `make_population`, `compute_ab_verdict`, `_MOVE`).
- **Déterminisme** : `np.random.seed(seed)` + `torch.manual_seed(seed)` par run ; A/B apparié par seed.
- **Anti-théâtre** : le legacy DOIT échouer la tâche compositionnelle (sinon elle ne teste pas la composition — issue 3) ; contraste avec `substrate_ab` mono-étape (que le legacy réussit) ; verdict BORNÉ = porte de décision, PAS preuve de transfert apex en prod.
- **Runs légers** : micro-tâche, env/monde NON requis, pas de KuzuDB → pas de risque de contention/DB.

---

### Task 1 : banc `substrate_ab_compositional.py` + tests

**Files:**
- Create: `tools/substrate_ab_compositional.py`
- Test: `tests/sandbox/test_substrate_ab_compositional.py`

**Interfaces:**
- Consumes : `make_population(agents, backend)` (`src/agents/backend.py`) ; `compute_ab_verdict(rows, band=0.02)` + `_MOVE` (`tools/substrate_ab.py`) ; `MambaAgent` (`src/agents/mamba_agent.py`).
- Produces : `compositional_reward(move2:int, target_y:int, did_x:bool) -> float` (PURE) ; `run_compositional(backend:str, seed:int, trials:int, n_agents:int, target_x:int, target_y:int) -> dict` (clés `backend/seed/trials/n_agents/hit_start/hit_end/delta`) ; `compare(seeds, trials, n_agents) -> dict` (verdict + `per_seed`).

- [ ] **Step 1 : Write the failing tests**

Créer `tests/sandbox/test_substrate_ab_compositional.py` :

```python
# tests/sandbox/test_substrate_ab_compositional.py
import pytest

from tools.substrate_ab_compositional import compositional_reward


def test_compositional_reward_truth_table():
    """Récompense étape 2 = +1 SSI (Y correct ET X fait en S1), −1 sinon (les 4 cas)."""
    assert compositional_reward(move2=4, target_y=4, did_x=True) == 1.0    # X✓ Y✓
    assert compositional_reward(move2=4, target_y=4, did_x=False) == -1.0  # X✗ Y✓ : Y seul ne paie pas
    assert compositional_reward(move2=2, target_y=4, did_x=True) == -1.0   # X✓ Y✗
    assert compositional_reward(move2=2, target_y=4, did_x=False) == -1.0  # X✗ Y✗


@pytest.mark.slow
def test_compositional_ab_smoke():
    """Le banc A/B tourne pour les deux backends et renvoie un verdict structuré."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare
    res = compare(seeds=(0,), trials=30, n_agents=4)
    assert res["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy_delta", "torch_delta", "diff"):
        assert k in row
```

- [ ] **Step 2 : Run tests to verify they fail**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v -m "slow or not slow"`
Expected : FAIL — `ModuleNotFoundError: No module named 'tools.substrate_ab_compositional'`.

- [ ] **Step 3 : Create the bench module**

Créer `tools/substrate_ab_compositional.py` :

```python
"""A/B de learnabilité COMPOSITIONNELLE du substrat (means→ends) — porte de décision torch-prod.

Question : un substrat `torch` (autograd) apprend-il une contingence 2-étapes — faire X en S1
(récompense IMMÉDIATE nulle) puis Y en S2 récompensé SEULEMENT si X a été fait — que le substrat
`legacy` (hebbien/Actor-Critic TD numpy, ~5 cachés) NE peut pas ? C'est l'apex craft→chasse en
miniature. `obs_B` n'encode PAS `did_X` -> l'agent doit le MÉMORISER (récurrence) = vraie composition.

Réutilise le backend abstrait (`make_population`, ADR-003) + `compute_ab_verdict` de `substrate_ab`
SANS les modifier. PORTÉE : micro-tâche, PAS une preuve de transfert apex en prod.

Usage : python tools/substrate_ab_compositional.py   (env: SABC_SEEDS, SABC_TRIALS, SABC_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from tools.substrate_ab import compute_ab_verdict, _MOVE


def compositional_reward(move2: int, target_y: int, did_x: bool) -> float:
    """Récompense d'étape 2 : +1 SSI l'action Y est correcte ET X a été fait en S1, sinon −1.
    PURE et testable. C'est ce qui rend la tâche COMPOSITIONNELLE (Y ne paie que via X)."""
    return 1.0 if (move2 == target_y and did_x) else -1.0


def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4) -> dict:
    """Entraîne une pop sur la tâche 2-étapes. Renvoie le taux d'essais PLEINEMENT corrects
    (X-puis-Y) début vs fin (delta = apprentissage compositionnel)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = [MambaAgent() for _ in range(n_agents)]
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S1 (motif fixe)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S2 (motif distinct)
    zeros = np.zeros(n_agents, dtype=np.float32)

    full = []
    for _ in range(trials):
        # Étape 1 (S1) : émettre X, récompense différée (0). La récurrence retient l'état.
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.learn(zeros, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        # Étape 2 (S2) : émettre Y, récompensé SSI X fait en S1 (obs_b n'encode pas did_x).
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        full.append(float(np.mean((move2 == target_y) & did_x)))   # essai pleinement correct

    q = max(1, trials // 4)
    hit_start, hit_end = float(np.mean(full[:q])), float(np.mean(full[-q:]))
    return {"backend": backend, "seed": int(seed), "trials": trials, "n_agents": n_agents,
            "hit_start": hit_start, "hit_end": hit_end, "delta": hit_end - hit_start}


def compare(seeds=(0, 1, 2, 3, 4), trials: int = 100, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch par seed -> verdict de learnabilité compositionnelle."""
    rows = []
    for s in seeds:
        leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents)
        tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
    return {**compute_ab_verdict(rows), "per_seed": rows}


def main():
    seeds = [int(s) for s in os.environ.get("SABC_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    trials = int(os.environ.get("SABC_TRIALS", "150"))
    n_agents = int(os.environ.get("SABC_AGENTS", "8"))
    res = compare(seeds=seeds, trials=trials, n_agents=n_agents)
    print(f"VERDICT={res['verdict']} median_diff={res['median_diff']:+.3f} "
          f"(grad_fav={res['n_gradient_favorable']}/{res['n']}, sign_p={res['sign_p']:.3f})")
    for r in res["per_seed"]:
        print(f"  seed={r['seed']} legacy d={r['legacy_delta']:+.3f}  torch d={r['torch_delta']:+.3f}  "
              f"diff={r['diff']:+.3f}  (legacy end={r['legacy']['hit_end']:.3f} torch end={r['torch']['hit_end']:.3f})")
    return res


if __name__ == "__main__":
    main()
```

> Note d'ancrage : `pop.forward(obs)` renvoie `(preds, _)` ; `np.asarray(preds)[:, :_MOVE].argmax(axis=1)` = move choisi (exactement le motif de `substrate_ab.run_substrate_ab`). La récurrence du backend (H_prev/état LTC) persiste ENTRE les deux `forward` consécutifs sur la même `pop` → c'est le canal mémoire pour `did_x`. `pop.learn(rewards, actions)` accepte un array de récompenses (0 à l'étape 1).

- [ ] **Step 4 : Run the tests to verify they pass**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v -m "slow or not slow"`
Expected : PASS — table de vérité (4 cas) verte ; smoke A/B renvoie un verdict ∈ {GRADIENT_GAGNE, HEBBIEN_GAGNE, NEUTRE} + `per_seed` non vide avec les clés delta.

- [ ] **Step 5 : Commit (path-scoped)**

```bash
git add tools/substrate_ab_compositional.py tests/sandbox/test_substrate_ab_compositional.py
git commit -m "feat(substrate): banc A/B de learnabilite COMPOSITIONNELLE means->ends (legacy vs torch, EDR115)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2 : Run A/B + contrôle anti-théâtre + EDR 115 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/115_<verdict>.md`

**Interfaces:**
- Consumes : Task 1 (`compare`, `run_compositional`, le script `main`) ; `tools/substrate_ab.py` (la mono-étape, pour le contrôle de dureté).
- Produces : EDR documentant `delta` compositionnel par bras (legacy/torch) + le contrôle (legacy réussit mono-étape mais échoue compositionnelle) + verdict issue 1/2/3.

- [ ] **Step 1 : Run l'A/B compositionnel (≥5 seeds)**

```bash
AGISEED_QUIET_LOG=1 SABC_SEEDS=0,1,2,3,4 SABC_TRIALS=150 SABC_AGENTS=8 \
  python -u tools/substrate_ab_compositional.py 2>&1 | tee \
  "C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/eb814eca-e9fe-4f79-b0f7-d5d509e03b7b/scratchpad/sabc_main.log"
```
Capturer le VERDICT + la table par-seed (legacy_delta, torch_delta, hit_end par bras). Runs légers (micro-tâche, pas de DB/env) → secondes, pas de risque de contention.

- [ ] **Step 2 : Contrôle anti-théâtre — la tâche compositionnelle est-elle PLUS DURE que la mono-étape ?**

Lancer la mono-étape de référence (legacy doit RÉUSSIR) :
```bash
AGISEED_QUIET_LOG=1 SAB_SEEDS=0,1,2,3,4 SAB_TICKS=300 SAB_AGENTS=8 \
  python -u tools/substrate_ab.py 2>&1 | tee \
  "C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/eb814eca-e9fe-4f79-b0f7-d5d509e03b7b/scratchpad/sab_mono.log"
```
VÉRIFIER : le legacy a un `delta` POSITIF sur la mono-étape (il apprend la contingence simple) MAIS un `delta` faible/nul sur la compositionnelle (Step 1). Si le legacy réussit AUSSI la compositionnelle → la tâche ne teste pas la composition (issue 3, re-spécifier). Rapporter les deux deltas legacy (mono vs compo) côte à côte.

- [ ] **Step 3 : Verdict**

- **Issue 1 (GRADIENT_GAGNE)** : `torch_delta` > `legacy_delta` (median_diff > band, sign_p bas) ET legacy échoue la compositionnelle → la RÈGLE D'APPRENTISSAGE est le verrou → **porte torch-prod OUVERTE**. Raffine EDR 113 (le legacy ne sait pas EXPLOITER l'horizon de crédit, pas « l'horizon est inutile »).
- **Issue 2 (NEUTRE, les DEUX deltas bas)** : torch n'y arrive pas non plus à ~5 cachés → taille/représentation aussi requise → ajouter un facteur taille avant l'investissement prod.
- **Issue 3 (les DEUX deltas hauts)** : tâche trop facile (legacy la réussit) → garde-fou déclenché, re-spécifier (crédit plus différé / k>2 étapes).
- Rapporter `hit_start`/`hit_end`/`delta` par bras et par seed (jamais le scalaire nu).

- [ ] **Step 4 : Vérifier le prochain numéro EDR libre**

Run : `git fetch origin main --quiet; { ls docs/EDR/; git show origin/main:docs/EDR | tail -n +3; } | grep -oE "^11[0-9]" | sort -u | tail` — confirmer **115** libre (113/114 pris par sessions //).

- [ ] **Step 5 : Écrire l'EDR 115**

Créer `docs/EDR/115_<verdict>.md` : contexte (convergence 104-113 substrat ; audit SOTA `[[sota-gap-substrate]]` ~5 cachés numpy sans gradient ; barreau-0 backend livré ; `substrate_ab` mono-étape torch>legacy ; l'apex est COMPOSITIONNEL) ; **manipulation** (tâche 2-étapes X-gate-Y, mémoire récurrente obligatoire) ; **contrôle de dureté** (legacy réussit mono mais échoue compo) ; table `delta` legacy/torch par seed ; verdict issue 1/2/3 ; **lien EDR 113** (isole POURQUOI le γ-sweep n'a pas marché : règle d'apprentissage vs « horizon inutile ») ; liens `[[sota-gap-substrate]]` / `[[nas-bottleneck-is-substrate-not-search]]` / `[[coop-competence-is-population-property]]` ; statut + suite (porte torch-prod si issue 1). Bornage : micro-tâche, PORTE DE DÉCISION pas preuve de transfert.

- [ ] **Step 6 : Commit (path-scoped)**

```bash
git add docs/EDR/115_*.md
git commit -m "docs(EDR115): learnabilite compositionnelle -> gradient craque le means->ends que l'hebbien ne peut pas (ou non)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- Banc `substrate_ab_compositional.py` réutilisant `make_population`/`compute_ab_verdict` sans modifier les sessions // (spec Architecture) → Task 1 Step 3. ✅
- Tâche 2-étapes X-gate-Y, mémoire récurrente (spec Architecture) → Task 1 Step 3 (`run_compositional` + note d'ancrage). ✅
- `compositional_reward` pur + 4 cas (spec Tests) → Task 1 Steps 1, 3. ✅
- Smoke A/B avec `importorskip torch` (spec Tests) → Task 1 Step 1. ✅
- A/B ≥5 seeds, verdict issue 1/2/3 (spec Instrument) → Task 2 Steps 1, 3. ✅
- Contrôle anti-théâtre (legacy réussit mono mais échoue compo) (spec Garde-fous) → Task 2 Step 2. ✅
- Verdict borné = porte de décision (spec Garde-fous) → Task 2 Steps 3, 5. ✅
- EDR 115 + lien EDR 113 (spec) → Task 2 Steps 4-6. ✅

**2. Placeholder scan :** `<verdict>` (Task 2 nom de fichier) résolu en Step 3-5 (intentionnel). Pas de TBD/TODO ; code complet à chaque step de code.

**3. Type consistency :** `compositional_reward(move2:int, target_y:int, did_x:bool) -> float` cohérent entre def (Step 3) et asserts (Step 1). `run_compositional(...) -> dict` clés `delta`/`hit_end` cohérentes avec `compare` (qui lit `leg["delta"]`/`tor["delta"]`) et le smoke (`legacy_delta`/`torch_delta`/`diff`). `compute_ab_verdict`/`_MOVE` importés de `substrate_ab` (signatures réelles vérifiées). `pop.forward → (preds,_)`, `pop.learn(rewards, actions)` conformes au backend livré. `n_in = num_inputs` (motif `substrate_ab`).
