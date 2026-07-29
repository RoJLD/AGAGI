# SP-2 — Première arête mesurée (« coordination demande perception ») Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raffiner le validateur SP-1 (n/a + specificity_control), puis MESURER et graver la première arête capacité→capacité du graphe — « language demande perception » — sur le jeu référentiel de Lewis, écrite dans `demands.json` et validée.

**Architecture:** Une sonde torch self-contained (réutilise le patron de `referential_game_probe.py`, ne le modifie pas) avec deux boutons : `no_coord` (receiver voit une vue directe BRUITÉE de la cible → métrique vivante) et l'ablation de perception (dérangement du one-hot cible du sender via `derange_rows`, à l'ÉVAL). `ablation_verdict` (déjà calibré) tranche COORD (X_DEMANDED) et NO-COORD (inerte → specificity_control). Calibrée par sender oracle/aléatoire. Coût borné : smoke d'abord, run-verdict n=12 plafonné, pur torch CPU.

**Tech Stack:** Python 3, torch (CPU), numpy, pytest. Réutilise `MambaAgent`, `make_population(backend="torch")`, `learn_episode`, `tools/s2_demand_ablation.derange_rows`, `tools/demand_marker.ablation_verdict`, `tools/experiment_preflight`.

## Global Constraints

- **Ablation d'ENTRÉE (verbatim)** : ablater = déranger le one-hot cible du sender via `derange_rows` (`tools/s2_demand_ablation.py`), À L'ÉVAL (within-subject : entraîner intact, puis évaluer perception intacte vs dérangée). Pas d'écriture dans le substrat → `functional_aliasing = "n/a"`.
- **NO-COORD doit rester VIVANT** : le receiver reçoit une vue directe BRUITÉE de la cible (`flip_p` réglé pour une accuracy médiane STRICTEMENT entre `1/K` et ~0.9). Un test DOIT asserter cette vivacité avant d'interpréter l'inertie (piège WARM-002). Interdit : vue directe parfaite (plafonnerait).
- **Unité = seed, n >= 12** (le `n_floor` de `ablation_verdict`). `intervention_verified=True`. `floor=1/K` déclaré.
- **Seam `sender_mode ∈ {"learned", "oracle", "random"}`** : `learned` = sender torch entraîné ; `oracle` = signal = index perçu (`argmax(s_in) % V`) ; `random` = signal aléatoire. `oracle`/`random` servent la CALIBRATION (contrôle positif/négatif), n'entraînent rien.
- **Nommage cliquet** : `run_perception_coordination_demand_probe` (motif `run_\w*probe`) trippe le cliquet → doit figurer dans `CALIBRATED` avec ses cas. Helpers privés (`_train_lewis`, `_eval_acc`, `_onehot`, `_noisy_onehot`, `_sample`) ne matchent aucun motif.
- **Bornage du coût (rituel)** : pur torch CPU, **aucun bail `kuzu`, aucun monde**. Pré-vol `declare_design`. SMOKE d'abord (mesurer le débit), PUIS run-verdict n=12 avec `episodes`/`n_agents` PLAFONNÉS. Persister les accuracies par seed (JSON) pour re-graver sans réentraîner. Ne pas extrapoler depuis un préfixe.
- **Ne PAS modifier `tools/referential_game_probe.py`** (référencé par LANG-001) — la sonde SP-2 est self-contained.
- **Commits path-scoped** : `git add <chemins explicites>` — JAMAIS `-A`/`.`/`-a`. Arbre partagé, sessions parallèles actives (hazard cliquet tree-wide → stash path-scoped d'un fichier étranger si besoin, jamais `--no-verify`). Branche `feat/d1-prod-pairing`.

## File Structure

- `tools/check_agi_taxonomy.py` (MODIFIÉ) — règle d'arête raffinée (`n/a` + `specificity_control`).
- `data/agi_taxonomy/schema/demand.schema.json` (MODIFIÉ) — `functional_aliasing` enum + `specificity_control`.
- `docs/REF/REF-AGI-TAXONOMY.md` (MODIFIÉ) — règle raffinée.
- `tools/perception_coordination_demand_probe.py` (NOUVEAU) — la sonde.
- `data/agi_taxonomy/demands.json` (MODIFIÉ) — la 1ʳᵉ arête (Task 3).
- `docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md` (NOUVEAU) — le record (Task 3).
- `tests/test_agi_taxonomy.py` (MODIFIÉ) — cas `n/a`/specificity.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — calibration de la sonde + `CALIBRATED`.
- `results/sp2_edge_accuracies.json` (NOUVEAU, Task 3) — accuracies par seed persistées.

---

### Task 1: Raffinement SP-1 (n/a + specificity_control)

**Files:**
- Modify: `tools/check_agi_taxonomy.py`
- Modify: `data/agi_taxonomy/schema/demand.schema.json`
- Modify: `docs/REF/REF-AGI-TAXONOMY.md`
- Test: `tests/test_agi_taxonomy.py`

**Interfaces:**
- Consumes: `validate_edge(edge, capability_ids)` (SP-1).
- Produces: règle raffinée — `functional_aliasing == "pass"` OU (`== "n/a"` ET `specificity_control == "pass"`).

- [ ] **Step 1: Écrire les tests de la règle raffinée (qui échouent)**

Add to `tests/test_agi_taxonomy.py`:

```python
def test_edge_accepts_na_aliasing_with_specificity_control():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a", specificity_control="pass")
    assert validate_edge(e, _IDS) == []


def test_edge_rejects_na_aliasing_without_specificity_control():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a")           # pas de specificity_control
    v = validate_edge(e, _IDS)
    assert any("specificity_control" in x for x in v)


def test_edge_rejects_na_aliasing_with_failed_specificity():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a", specificity_control="fail")
    v = validate_edge(e, _IDS)
    assert any("specificity_control" in x for x in v)


def test_edge_still_accepts_pass_aliasing():
    from tools.check_agi_taxonomy import validate_edge
    assert validate_edge(_valid_edge(functional_aliasing="pass"), _IDS) == []
```

Also UPDATE the existing `_valid_edge` helper in `tests/test_agi_taxonomy.py` so evidence overrides can set `functional_aliasing`/`specificity_control` (replace the helper with):

```python
def _valid_edge(**evidence_over):
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "functional_aliasing": "pass",
          "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_agi_taxonomy.py -k "na_aliasing or specificity or pass_aliasing" -v`
Expected: FAIL (la règle actuelle exige `== "pass"` strict, donc `n/a`+specificity est rejeté à tort ; ou specificity non reconnu).

- [ ] **Step 3: Raffiner la règle**

In `tools/check_agi_taxonomy.py`, REPLACE the `functional_aliasing` block in `validate_edge` (the `if ev.get("functional_aliasing") != "pass": ...`) with:

```python
    fa = ev.get("functional_aliasing")
    if fa == "pass":
        pass  # garde structurel/comportemental appliqué (CALIB-ALIAS)
    elif fa == "n/a":
        if ev.get("specificity_control") != "pass":
            v.append(f"arête {lbl} : functional_aliasing='n/a' EXIGE specificity_control='pass' "
                     "(contrôle de demande : ablation inerte là où la capacité n'est pas demandée)")
    else:
        v.append(f"arête {lbl} : functional_aliasing='{fa}' (attendu 'pass', ou 'n/a' + specificity_control)")
```

- [ ] **Step 4: Mettre à jour le schéma**

In `data/agi_taxonomy/schema/demand.schema.json`, set `evidence.properties.functional_aliasing` to `{"enum": ["pass", "n/a"]}` and add to `evidence.properties`: `"specificity_control": {"enum": ["pass", "fail"]}`. (Ne PAS ajouter `specificity_control` à `required` — il n'est requis que quand `functional_aliasing=="n/a"`, ce que le validateur impose.)

- [ ] **Step 5: Lancer, vérifier le succès**

Run: `python -m pytest tests/test_agi_taxonomy.py -v`
Expected: PASS (tous — les 10 existants + 4 nouveaux).

Run: `python tools/check_agi_taxonomy.py`
Expected: `4 capacités, 0 arêtes | 0 violations` → OK (demands.json toujours vide à ce stade).

- [ ] **Step 6: Mettre à jour REF**

In `docs/REF/REF-AGI-TAXONOMY.md`, under the edge-rule list, replace the `functional_aliasing == "pass"` bullet with:
`- `functional_aliasing == "pass"` (garde CALIB-ALIAS) OU `functional_aliasing == "n/a"` + `specificity_control == "pass"` (ablation d'ENTRÉE : pas de fuite de substrat, spécificité prouvée par un contrôle de demande — ablation inerte là où la capacité n'est pas demandée).`

- [ ] **Step 7: Commit**

```bash
git add tools/check_agi_taxonomy.py data/agi_taxonomy/schema/demand.schema.json docs/REF/REF-AGI-TAXONOMY.md tests/test_agi_taxonomy.py
git commit -m "feat(SP-2/SP-1): validateur accepte n/a-aliasing + specificity_control (ablation d'entree)"
```

---

### Task 2: Sonde + calibration (FUSIONNÉS) + smoke

**Files:**
- Create: `tools/perception_coordination_demand_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py` (CALIBRATED + cas oracle/aléatoire + smoke)

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `learn_episode`, `derange_rows`, `ablation_verdict`.
- Produces:
  - `run_perception_coordination_demand_probe(seeds, episodes, n_agents=32, K=6, V=8, lr=0.05, flip_p=0.3, sender_mode="learned") -> dict` : entraîne COORD et NO-COORD par seed, ablate à l'éval, renvoie
    `{"coord": <ablation_verdict dict>, "nocoord": <ablation_verdict dict>, "nocoord_alive": bool, "specificity_control": "pass"|"fail", "functional_aliasing": "n/a", "n": int, "coord_intact": [...], "coord_ablated": [...], "nocoord_intact": [...], "nocoord_ablated": [...]}`.

- [ ] **Step 1: Écrire un smoke unitaire de la sonde (qui échoue)**

Create `tests/test_sp2_edge.py` (tests unitaires rapides de la sonde, hors calibration) — actually add to the calibration file in Step 4; for the probe's own quick unit test use a NEW file:

Create `tests/test_perception_coordination_probe.py`:

```python
import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_na_aliasing_smoke():
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    # smoke minuscule : on vérifie la FORME + que functional_aliasing='n/a', pas les valeurs scientifiques
    r = run_perception_coordination_demand_probe(seeds=[0, 1], episodes=30, n_agents=8, K=4, V=6)
    assert r["functional_aliasing"] == "n/a"
    assert r["n"] == 2 and len(r["coord_intact"]) == 2 and len(r["nocoord_intact"]) == 2
    assert set(r) >= {"coord", "nocoord", "specificity_control", "nocoord_alive"}
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_perception_coordination_probe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.perception_coordination_demand_probe'`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/perception_coordination_demand_probe.py`:

```python
"""SP-2 — MESURE de l'arête « coordination demande perception » sur le jeu référentiel de Lewis.

Ablation d'ENTRÉE within-subject : à l'éval, on DÉRANGE le one-hot cible du sender (derange_rows,
in-distribution). Deux conditions : COORD (le receiver ne lit que le signal) -> l'ablation effondre ;
NO-COORD (le receiver a une vue directe BRUITÉE de la cible -> métrique vivante) -> l'ablation est inerte
(contrôle de demande = specificity_control). `functional_aliasing = "n/a"` : une ablation d'entrée n'écrit
rien dans le substrat, aucune fuite à garder (cf. CALIB-ALIAS).

Le nom `run_*probe` trippe le cliquet -> calibré (sender oracle/aléatoire) dans test_instrument_calibration.
Pur torch CPU, aucun bail. Usage : python tools/perception_coordination_demand_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.demand_marker import ablation_verdict
from tools.s2_demand_ablation import derange_rows


def _onehot(idx, size, I, n_agents):
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), idx % size] = 1.0
    return m


def _noisy_onehot(targets, K, I, n_agents, flip_p, rng):
    """Vue directe BRUITÉE de la cible : avec proba flip_p, one-hot sur un référent ALÉATOIRE (garde la
    métrique NO-COORD vivante, plafonnée à ~1-flip_p)."""
    shown = np.where(rng.random(n_agents) < flip_p, rng.randint(0, K, size=n_agents), targets)
    return _onehot(shown, K, I, n_agents)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _signal_from(s_in, sender, sender_mode, V, rng, n_agents):
    """Signal émis à partir de ce que le sender PERÇOIT (s_in, éventuellement dérangé). oracle/random =
    contrôles de calibration ; learned = sender torch."""
    if sender_mode == "oracle":
        return (np.asarray(s_in).argmax(axis=1) % V)          # émet l'index perçu
    if sender_mode == "random":
        return rng.randint(0, V, size=n_agents)               # décorrélé de la perception
    import torch
    sender.H = torch.zeros((n_agents, sender.N))
    preds_s, _ = sender.forward(s_in)
    return _sample(preds_s, V, rng, n_agents)


def _train_and_eval(seed, no_coord, episodes, n_agents, K, V, lr, flip_p, sender_mode, eval_batches=40):
    """Entraîne (learned) puis évalue perception INTACTE vs DÉRANGÉE. Renvoie (acc_intact, acc_ablated)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    try:
        sender = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = sender.I
        rng = np.random.RandomState(seed + 1)
        learned = sender_mode == "learned"
        if learned:
            sender.opt = torch.optim.Adam([sender.W], lr=lr)
        receiver.opt = torch.optim.Adam([receiver.W], lr=lr)

        for _ in range(episodes):
            targets = rng.randint(0, K, size=n_agents)
            s_in = _onehot(targets, K, I, n_agents)
            signal = _signal_from(s_in, sender, sender_mode, V, rng, n_agents)
            recv_in = (_noisy_onehot(targets, K, I, n_agents, flip_p, rng) if no_coord
                       else _onehot(signal, V, I, n_agents))
            receiver.H = torch.zeros((n_agents, receiver.N))
            preds_r, _ = receiver.forward(recv_in)
            guess = _sample(preds_r, K, rng, n_agents)
            adv = (guess == targets).astype(np.float32)
            adv = adv - adv.mean()
            if learned:
                sender.learn_episode([s_in], [[{"move": int(x)} for x in signal]], adv, gate_last_only=False)
            receiver.learn_episode([recv_in], [[{"move": int(x)} for x in guess]], adv, gate_last_only=False)

        def _eval(ablate):
            hits = []
            for _ in range(eval_batches):
                targets = rng.randint(0, K, size=n_agents)
                s_in = _onehot(targets, K, I, n_agents)
                if ablate:
                    s_in = derange_rows(s_in, rng)             # ABLATION de la perception du sender
                signal = _signal_from(s_in, sender, sender_mode, V, rng, n_agents)
                recv_in = (_noisy_onehot(targets, K, I, n_agents, flip_p, rng) if no_coord
                           else _onehot(signal, V, I, n_agents))
                receiver.H = torch.zeros((n_agents, receiver.N))
                pr, _ = receiver.forward(recv_in)
                guess = np.asarray(pr)[:, :K].argmax(axis=1)
                hits.append((guess == targets).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval(False), _eval(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def run_perception_coordination_demand_probe(seeds, episodes=1000, n_agents=32, K=6, V=8, lr=0.05,
                                             flip_p=0.3, sender_mode="learned"):
    """Mesure « coordination demande perception ». Par seed : COORD et NO-COORD, chacun éval intact/ablé.
    COORD -> ablation_verdict (attendu X_DEMANDED) ; NO-COORD -> inerte (specificity_control)."""
    ci, ca, ni, na = [], [], [], []
    for s in seeds:
        c_i, c_a = _train_and_eval(s, False, episodes, n_agents, K, V, lr, flip_p, sender_mode)
        n_i, n_a = _train_and_eval(s, True, episodes, n_agents, K, V, lr, flip_p, sender_mode)
        ci.append(c_i); ca.append(c_a); ni.append(n_i); na.append(n_a)

    floor = 1.0 / K
    coord = ablation_verdict(ci, ca, intervention_verified=True, floor=floor, ceiling=1.0)
    nocoord = ablation_verdict(ni, na, intervention_verified=True, floor=floor, ceiling=1.0)
    nocoord_med = float(np.median(ni))
    nocoord_alive = floor + 0.05 < nocoord_med < 0.9              # VIVANT (ni plancher ni plafond)
    specificity = "pass" if (nocoord["verdict"] == "X_DECOY" and nocoord_alive) else "fail"
    return {"coord": coord, "nocoord": nocoord, "nocoord_alive": nocoord_alive,
            "specificity_control": specificity, "functional_aliasing": "n/a", "n": len(seeds),
            "coord_intact": ci, "coord_ablated": ca, "nocoord_intact": ni, "nocoord_ablated": na}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("SP2_SEEDS", "12"))))
    ep = int(os.environ.get("SP2_EPISODES", "1000"))
    na = int(os.environ.get("SP2_AGENTS", "32"))
    r = run_perception_coordination_demand_probe(seeds, episodes=ep, n_agents=na)
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("coord", "nocoord", "specificity_control", "nocoord_alive",
                               "functional_aliasing", "n")}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Lancer le smoke unitaire de la sonde**

Run: `python -m pytest tests/test_perception_coordination_probe.py -v`
Expected: PASS (forme correcte, `functional_aliasing == "n/a"`, n=2). Quelques secondes.

- [ ] **Step 5: Déclarer l'instrument calibré + écrire la calibration (oracle/aléatoire)**

In `tests/sandbox/test_instrument_calibration.py`, add to `CALIBRATED`:

```python
    # SP-2 : « coordination demande perception » sur le jeu de Lewis. Contrôle positif = sender ORACLE
    # (signal = perception -> ablater effondre) ; contrôle négatif = sender ALÉATOIRE (inerte). Générateur A.
    "run_perception_coordination_demand_probe": ["*"],
```

Append to `tests/sandbox/test_instrument_calibration.py`:

```python
def test_sp2_oracle_sender_makes_perception_demanded():
    """CONTRÔLE POSITIF (générateur A) : avec un sender ORACLE (signal = index perçu), la coordination est
    parfaite et DÉRANGER la perception l'effondre -> COORD X_DEMANDED. Le banc SAIT produire l'effondrement.
    Aucun entraînement (oracle) -> quelques secondes."""
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    r = run_perception_coordination_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6,
                                                 sender_mode="oracle")
    assert r["coord"]["verdict"] == "X_DEMANDED", r["coord"]
    assert r["coord"]["ratio"] > 1.5


def test_sp2_random_sender_is_inert_no_false_demand():
    """CONTRÔLE NÉGATIF : avec un sender ALÉATOIRE (signal décorrélé), pas de coordination -> DÉRANGER la
    perception est inerte -> COORD PAS X_DEMANDED. Le banc ne FABRIQUE pas un effondrement inexistant."""
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    r = run_perception_coordination_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6,
                                                 sender_mode="random")
    assert r["coord"]["verdict"] != "X_DEMANDED", r["coord"]
```

Note d'implémentation : `episodes=0` doit être un cas VALIDE (pas d'entraînement) pour oracle/random — la boucle `for _ in range(episodes)` s'exécute 0 fois, l'éval fonctionne. Vérifier que le code ne divise jamais par `episodes`.

- [ ] **Step 6: Lancer la calibration + le cliquet**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k sp2 -v`
Expected: PASS (2 cas ; oracle → X_DEMANDED, random → pas X_DEMANDED). Quelques secondes (oracle/random n'entraînent pas).

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.`

- [ ] **Step 7: Commit (FUSIONNÉ — sonde + calibration)**

```bash
git add tools/perception_coordination_demand_probe.py tests/test_perception_coordination_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # confirmer UNIQUEMENT ces trois chemins
git commit -m "feat(SP-2): sonde coordination-demande-perception + calibration oracle/aleatoire (cliquet)"
```

Si le hook bloque sur un instrument d'une AUTRE session : stash path-scoped ce fichier étranger, commit, pop, vérifier identique — jamais `--no-verify`.

---

### Task 3: Run-verdict (n=12) + arête + record

**Files:**
- Create: `results/sp2_edge_accuracies.json`
- Modify: `data/agi_taxonomy/demands.json`
- Create: `docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md`

**Interfaces:**
- Consumes: `run_perception_coordination_demand_probe` (Task 2), `check_agi_taxonomy` (Task 1).
- Produces: la 1ʳᵉ arête dans `demands.json` + le record + les accuracies persistées.

- [ ] **Step 1: Pré-vol + SMOKE (mécanisme + débit)**

Run: `python -c "import time,json; from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe as R; t=time.time(); r=R(seeds=[0,1,2], episodes=300, n_agents=16, K=6); print('dt_s=%.1f' % (time.time()-t)); print('coord', r['coord']['verdict'], round(r['coord']['ratio'],2), 'nocoord_alive', r['nocoord_alive'], 'spec', r['specificity_control'])"`

Attendu (smoke, 3 seeds) : imprime `dt_s` (le débit — noter pour dimensionner le run n=12), `coord` tend vers X_DEMANDED, `nocoord_alive True`, `spec pass`. ⚠️ Le smoke à 3 seeds NE tranche PAS (n<12) — c'est un contrôle de MÉCANISME + débit, pas le verdict.

**Décision de bornage** : si `dt_s` (3 seeds, 300 ep) projette un run n=12 à `episodes` cible > ~15 min, RÉDUIRE `episodes`/`n_agents` (viser COORD émergent : `coord_intact` médian > `1/K + 0.15`). Ne PAS lancer un run non borné.

- [ ] **Step 2: Run-verdict n=12 (borné) + persister**

Run (ajuster `episodes`/`n_agents` d'après le smoke ; défaut prudent ci-dessous) :
`python -c "import json; from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe as R; r=R(seeds=list(range(12)), episodes=1000, n_agents=32, K=6); json.dump(r, open('results/sp2_edge_accuracies.json','w'), indent=2); print('coord', r['coord']['verdict'], round(r['coord']['ratio'],3), 'n', r['n']); print('nocoord', r['nocoord']['verdict'], 'alive', r['nocoord_alive'], 'spec', r['specificity_control']); print('coord_intact_med', sorted(r['coord_intact'])[6], 'coord_ablated_med', sorted(r['coord_ablated'])[6])"`

Attendu : `coord X_DEMANDED` (ratio > 1.5, métrique intacte vivante > 1/K+0.15), `nocoord alive True`, `spec pass`. Les accuracies sont persistées dans `results/sp2_edge_accuracies.json`.

**Si `coord` n'est PAS X_DEMANDED** : lire `coord_intact_med` — si ≤ `1/K+0.15`, la coordination n'a pas émergé (augmenter `episodes`, re-smoke). Si intact vivant mais pas d'effondrement, c'est un VRAI nul → le graver honnêtement (arête NON écrite, record négatif). Ne pas forcer.

- [ ] **Step 3: Écrire l'arête (seulement si X_DEMANDED + spec pass)**

Si et seulement si le run donne `coord X_DEMANDED` ET `specificity_control == "pass"`, remplacer le contenu de `data/agi_taxonomy/demands.json` par (insérer le `ratio` réel arrondi et le vrai `n`) :

```json
[
  {
    "capability": "language",
    "prerequisite": "perception",
    "strength": "hard",
    "evidence": {
      "ablation_verdict": "X_DEMANDED",
      "ratio": 0.0,
      "n": 12,
      "functional_aliasing": "n/a",
      "specificity_control": "pass",
      "record": "docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md"
    }
  }
]
```

Remplacer `"ratio": 0.0` par la valeur affichée à l'étape 2 (`coord ... <ratio>`).

- [ ] **Step 4: Valider l'arête**

Run: `python tools/check_agi_taxonomy.py`
Expected: `4 capacités, 1 arêtes | 0 violations` → OK. (Si violation : lire le message — le plus probable est `n/a` sans `specificity_control`, ou record inexistant → créer le record d'abord, Step 5.)

- [ ] **Step 5: Écrire le record**

Create `docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md` (insérer les valeurs réelles) :

```markdown
---
id: EDR-LANG-PERCEPTION
type: EDR
title: "Première arête MESURÉE du graphe AGI-Taxonomy : la coordination référentielle DEMANDE la perception (ablation d'entrée within-subject, X_DEMANDED ; inerte en NO-COORD)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
SP-1 a livré le graphe capability-demand (vide). Première arête MESURÉE : « language/coordination demande
perception » ? On l'établit sur le proxy bon marché du jeu de Lewis, par ablation d'ENTRÉE within-subject.

## Méthode
Jeu référentiel torch (sender/receiver = MambaAgent, learn_episode). Ablation = dérangement du one-hot cible
du sender À L'ÉVAL (derange_rows, in-distribution). COORD : le receiver ne lit que le signal. NO-COORD
(contrôle de demande VIVANT) : le receiver a une vue directe BRUITÉE de la cible (flip_p=0.3). n=12 seeds,
`ablation_verdict` (floor=1/K). Sonde calibrée (sender oracle → effondre ; aléatoire → inerte).

## Résultat
COORD : X_DEMANDED (ratio R_REEL ; intacte VIVANTE médiane M_INTACT > 1/K, ablée ~ hasard). NO-COORD :
inerte sur métrique VIVANTE (specificity_control = pass). Donc la coordination LIT causalement la perception
de la cible — arête `language → perception` gravée dans `data/agi_taxonomy/demands.json`, validée par
`check_agi_taxonomy`. `functional_aliasing = "n/a"` (ablation d'entrée, pas de fuite de substrat) justifié
par le contrôle de demande.

## Portée (bornée)
Proxy hors-monde (jeu de Lewis), pas la biosphère. Une seule arête ; les autres (perception→memory, …) sont
des itérations ultérieures. Coût borné (smoke + run n=12 plafonné, accuracies persistées
`results/sp2_edge_accuracies.json`).

## Ce que ça débloque
Le graphe AGI-Taxonomy n'est plus vide : première arête MESURÉE, opposable au validateur SP-1. Le pipeline
« mesurer une arête par ablation + garde de spécificité → écrire une arête valide » est prouvé de bout en bout.
Cf. `docs/superpowers/specs/2026-07-24-sp2-first-measured-edge-design.md`.
```

Remplacer `R_REEL`/`M_INTACT` par les valeurs de l'étape 2.

- [ ] **Step 6: Valider record + suite + cliquet**

Run: `python tools/check_record_links.py`   (CALIB/EDR non orphelin ; les autres orphelins = sessions //)
Run: `python tools/check_agi_taxonomy.py`   (1 arête, 0 violation)
Run: `python -m pytest tests/test_agi_taxonomy.py -q`   (tous PASS)
Run: `python tools/check_instrument_calibration.py`   (OK)

- [ ] **Step 7: Commit**

```bash
git add data/agi_taxonomy/demands.json docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md results/sp2_edge_accuracies.json
git commit -m "feat(SP-2): 1ere arete MESUREE language->perception (X_DEMANDED, n=12) + record + demands.json peuple"
```

---

## Self-Review

**Spec coverage :**
- §3 raffinement SP-1 (n/a + specificity_control) → Task 1 (schéma + validateur + REF + 4 tests). ✓
- §4 mesure (substrat, ablation d'entrée, COORD/NO-COORD, verdict, n=12) → Task 2 sonde. ✓
- §4.3 NO-COORD VIVANT (vue directe bruitée) → `_noisy_onehot` + `nocoord_alive` assertion. ✓
- §5 calibration (oracle/aléatoire, générateur A) → Task 2 Step 5 (2 cas + CALIBRATED). ✓
- §6 bornage du coût (smoke d'abord, run borné, persister) → Task 3 Steps 1-2. ✓
- §7 arête + validateur → Task 3 Steps 3-4. §7 record → Step 5. ✓
- §9 critères de succès → couverts. §11 risques (NO-COORD vivant, coût, calibration) → assertions + smoke + calibration. ✓

**Placeholder scan :** les seules valeurs à remplir (ratio réel, M_INTACT) sont MESURÉES au run (Task 3), explicitement marquées `R_REEL`/`"ratio": 0.0` à remplacer. Aucun TODO dans le code.

**Type consistency :** `run_perception_coordination_demand_probe(seeds, episodes, n_agents, K, V, lr, flip_p, sender_mode)` renvoie le dict `{coord, nocoord, nocoord_alive, specificity_control, functional_aliasing, n, coord_intact, coord_ablated, nocoord_intact, nocoord_ablated}` — utilisé identiquement en Task 2 (tests), Task 3 (run). L'arête (§7) porte `functional_aliasing:"n/a"` + `specificity_control:"pass"`, exactement ce que la règle raffinée de Task 1 exige. ✓
