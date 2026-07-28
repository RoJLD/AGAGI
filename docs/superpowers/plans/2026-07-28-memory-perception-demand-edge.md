# Deuxième arête mesurée (« memory demands perception ») Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MESURER et graver la deuxième arête capacité→capacité du graphe AGI-Taxonomy — « memory demands perception » — sur un proxy torch de rappel différé (delayed-match-to-sample), et l'ajouter à `demands.json` de façon validée.

**Architecture:** Une sonde torch self-contained (réutilise le patron de SP-2, ne modifie AUCUN probe existant) où la mémoire = l'état récurrent APPRIS du MambaAgent porté à travers les ticks. Deux conditions : `delayed` (obs de test vide → rétention requise) et `present` (obs de test = vue directe BRUITÉE → rétention inutile, contrôle de demande vivant). L'ablation = dérangement du one-hot de l'indice au tick d'ENCODAGE (à l'éval). `ablation_verdict` (déjà calibré) tranche DELAYED (X_DEMANDED) et PRESENT (inerte → specificity_control). Calibrée par un seam `memory_mode` oracle/aléatoire. Coût borné : smoke d'abord, run n=12 FOREGROUND plafonné.

**Tech Stack:** Python 3, torch (CPU), numpy, pytest. Réutilise `MambaAgent`, `make_population(backend="torch")`, `learn_episode`, `tools/s2_demand_ablation.derange_rows`, `tools/demand_marker.ablation_verdict`. Le validateur `tools/check_agi_taxonomy.py` accepte DÉJÀ `functional_aliasing="n/a"` + `specificity_control="pass"` (livré en SP-2) — aucune modification validateur.

## Global Constraints

- **Ablation d'ENTRÉE (verbatim)** : ablater = déranger le one-hot de l'indice au tick d'ENCODAGE via `derange_rows` (`tools/s2_demand_ablation.py`), À L'ÉVAL (within-subject : entraîner sur perception d'encodage intacte, puis évaluer intacte vs dérangée). Pas d'écriture substrat → `functional_aliasing = "n/a"`.
- **Mémoire = état récurrent PORTÉ** : dans un épisode, `H` est remis à zéro UNE fois au début, puis porté à travers encode→délai→test (JAMAIS remis à zéro entre les ticks de la séquence). C'est ce portage qui EST la rétention testée.
- **PRESENT doit rester VIVANT** : l'obs de test montre une vue directe BRUITÉE de l'indice (`flip_p` réglé pour une accuracy médiane STRICTEMENT entre `1/K` et ~0.9). Un test DOIT asserter cette vivacité avant d'interpréter l'inertie (piège WARM-002). Interdit : vue de test parfaite.
- **Unité = seed, n >= 12** (le `n_floor` de `ablation_verdict`). `intervention_verified=True`. `floor=1/K` déclaré.
- **Seam `memory_mode ∈ {"learned", "oracle", "random"}`** : `learned` = MambaAgent entraîné (rétention apprise) ; `oracle` = rétention PARFAITE (le guess = l'indice ENCODÉ, possiblement dérangé — BYPASSE l'agent, aucun entraînement) ; `random` = guess décorrélé (bypasse l'agent). `oracle`/`random` servent la CALIBRATION.
- **Nommage cliquet** : `run_memory_perception_demand_probe` (motif `run_\w*probe`) trippe le cliquet → doit figurer dans `CALIBRATED` avec ses cas. Helpers privés (`_train_and_eval`, `_onehot`, `_noisy_onehot`, `_sample`, `_softmax`) ne matchent aucun motif.
- **Bornage du coût (rituel)** : pur torch CPU, **aucun bail `kuzu`, aucun monde**. Pré-vol `declare_design`. SMOKE d'abord (mesurer le débit), PUIS run-verdict n=12 en **FOREGROUND** (leçon SP-2 : un run background a été perdu ~92 min) avec `episodes`/`n_agents`/`D` PLAFONNÉS. Persister les accuracies (`results/mem_perception_edge_accuracies.json`). Provenance : le verdict gravé vient de la fonction CALIBRÉE réelle.
- **Ne modifier AUCUN probe existant** (`memory_demand_world_probe.py`, `referential_game_probe.py`, `perception_coordination_demand_probe.py`) — la sonde est self-contained. Ne PAS modifier `check_agi_taxonomy.py` (déjà OK).
- **Commits path-scoped** : `git add <chemins explicites>` — JAMAIS `-A`/`.`/`-a`. Arbre partagé, sessions parallèles actives (hazard cliquet tree-wide → stash path-scoped d'un fichier étranger si besoin, jamais `--no-verify`). Branche `feat/d1-prod-pairing`.

## File Structure

- `tools/memory_perception_demand_probe.py` (NOUVEAU) — la sonde.
- `tests/test_memory_perception_probe.py` (NOUVEAU) — smoke unitaire (forme + `functional_aliasing='n/a'`).
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — `CALIBRATED` + cas oracle/aléatoire.
- `data/agi_taxonomy/demands.json` (MODIFIÉ, Task 2) — 2ᵉ arête ajoutée.
- `docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md` (NOUVEAU, Task 2) — le record.
- `results/mem_perception_edge_accuracies.json` (NOUVEAU, Task 2) — accuracies persistées.

---

### Task 1: Sonde + calibration (FUSIONNÉS) + smoke

**Files:**
- Create: `tools/memory_perception_demand_probe.py`
- Create: `tests/test_memory_perception_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py` (CALIBRATED + cas oracle/aléatoire)

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `learn_episode`, `derange_rows`, `ablation_verdict`. VÉRIFIER contre le code réel avant de faire confiance à la transcription : `TorchPopulationModel` attributs `.W`,`.I`,`.N`,`.H`,`.opt` ; `.forward(x) -> (preds, state)` ; `.learn_episode(inputs, actions, adv, gate_last_only=...)` ; flags `CONDITION_GATE`/`GATE_TARGET`. En particulier confirmer que **`forward` porte l'état** (soit `self.H` est mis à jour, soit l'état est le 2ᵉ retour à réassigner à `self.H`) et que `learn_episode` accepte une SÉQUENCE multi-tick avec `gate_last_only=True` (crédit du dernier tick). Si une signature diffère, adapter et le signaler.
- Produces:
  - `run_memory_perception_demand_probe(seeds, episodes=800, n_agents=16, K=6, D=2, lr=0.05, flip_p=0.3, memory_mode="learned") -> dict` renvoyant `{"delayed": <ablation_verdict dict>, "present": <ablation_verdict dict>, "present_alive": bool, "specificity_control": "pass"|"fail", "functional_aliasing": "n/a", "n": int, "delayed_intact": [...], "delayed_ablated": [...], "present_intact": [...], "present_ablated": [...]}`.

- [ ] **Step 1: Écrire le smoke unitaire de la sonde (qui échoue)**

Create `tests/test_memory_perception_probe.py`:

```python
import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_na_aliasing_smoke():
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    # smoke minuscule : FORME + functional_aliasing='n/a', pas les valeurs scientifiques
    r = run_memory_perception_demand_probe(seeds=[0, 1], episodes=30, n_agents=8, K=4, D=1)
    assert r["functional_aliasing"] == "n/a"
    assert r["n"] == 2 and len(r["delayed_intact"]) == 2 and len(r["present_intact"]) == 2
    assert set(r) >= {"delayed", "present", "specificity_control", "present_alive"}
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_memory_perception_probe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.memory_perception_demand_probe'`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/memory_perception_demand_probe.py`:

```python
"""AGI-Taxonomy — MESURE de l'arête « memory demands perception » sur un delayed-match-to-sample.

Mémoire = état récurrent APPRIS du MambaAgent, PORTÉ à travers les ticks (encode -> délai -> test).
Ablation d'ENTRÉE within-subject : à l'éval, on DÉRANGE le one-hot de l'indice au tick d'ENCODAGE
(derange_rows, in-distribution). Deux conditions : DELAYED (obs de test vide -> il faut la rétention) ->
l'ablation effondre ; PRESENT (obs de test = vue directe BRUITÉE de l'indice) -> l'ablation est inerte
(contrôle de demande = specificity_control). functional_aliasing="n/a" (ablation d'entrée, pas d'écriture
substrat -> pas de fuite à garder, cf. CALIB-ALIAS).

Le nom run_*probe trippe le cliquet -> calibré (memory oracle/aléatoire) dans test_instrument_calibration.
Pur torch CPU, aucun bail. Usage : python tools/memory_perception_demand_probe.py
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


def _noisy_onehot(cues, K, I, n_agents, flip_p, rng):
    """Vue directe BRUITÉE de l'indice au TEST : avec proba flip_p, one-hot sur un référent ALÉATOIRE
    (garde la métrique PRESENT vivante, plafonnée à ~1-flip_p)."""
    shown = np.where(rng.random(n_agents) < flip_p, rng.randint(0, K, size=n_agents), cues)
    return _onehot(shown, K, I, n_agents)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _seq_inputs(cues, condition, ablate, K, I, n_agents, D, flip_p, rng):
    """Construit la séquence [encode, délai×D, test]. encode = one-hot indice (dérangé si ablate).
    délai = zéros. test = zéros (delayed) ou vue bruitée (present)."""
    enc_in = _onehot(cues, K, I, n_agents)
    if ablate:
        enc_in = derange_rows(enc_in, rng)            # ABLATION de la perception à l'ENCODAGE
    zeros = np.zeros((n_agents, I), dtype=np.float32)
    test_in = (zeros if condition == "delayed"
               else _noisy_onehot(cues, K, I, n_agents, flip_p, rng))
    return [enc_in] + [zeros for _ in range(D)] + [test_in], enc_in


def _forward_seq(agent, inputs):
    """Forward la séquence en PORTANT l'état récurrent. Renvoie les preds du DERNIER tick (le test)."""
    import torch
    agent.H = torch.zeros((_n_agents_of(agent), agent.N))
    preds = None
    for x in inputs:
        preds, state = agent.forward(x)
        agent.H = state                                # porte H à travers les ticks (rétention)
    return preds


def _n_agents_of(agent):
    return agent.W.shape[0]


def _train_and_eval(seed, condition, episodes, n_agents, K, D, lr, flip_p, memory_mode, eval_batches=40):
    """Entraîne (learned) puis évalue perception d'encodage INTACTE vs DÉRANGÉE. Renvoie (acc_i, acc_a)."""
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
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        learned = memory_mode == "learned"
        if learned:
            agent.opt = torch.optim.Adam([agent.W], lr=lr)
            for _ in range(episodes):
                cues = rng.randint(0, K, size=n_agents)
                inputs, _enc = _seq_inputs(cues, condition, False, K, I, n_agents, D, flip_p, rng)
                preds = _forward_seq(agent, inputs)
                guess = _sample(preds, K, rng, n_agents)
                adv = (guess == cues).astype(np.float32)
                adv = adv - adv.mean()
                # crédit du DERNIER tick (le rappel) ; ticks intermédiaires = actions neutres
                acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(inputs) - 1)]
                acts.append([{"move": int(g)} for g in guess])
                agent.learn_episode(inputs, acts, adv, gate_last_only=True)

        def _eval(ablate):
            hits = []
            for _ in range(eval_batches):
                cues = rng.randint(0, K, size=n_agents)
                inputs, enc_in = _seq_inputs(cues, condition, ablate, K, I, n_agents, D, flip_p, rng)
                if memory_mode == "oracle":
                    guess = enc_in[:, :K].argmax(axis=1)   # rétention PARFAITE de ce qui a été encodé
                elif memory_mode == "random":
                    guess = rng.randint(0, K, size=n_agents)
                else:
                    preds = _forward_seq(agent, inputs)
                    guess = np.asarray(preds)[:, :K].argmax(axis=1)
                hits.append((guess == cues).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval(False), _eval(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def run_memory_perception_demand_probe(seeds, episodes=800, n_agents=16, K=6, D=2, lr=0.05,
                                       flip_p=0.3, memory_mode="learned"):
    """Mesure « memory demands perception ». Par seed : DELAYED et PRESENT, chacun éval intact/ablé.
    DELAYED -> ablation_verdict (attendu X_DEMANDED) ; PRESENT -> inerte (specificity_control)."""
    di, da, pi, pa = [], [], [], []
    for s in seeds:
        d_i, d_a = _train_and_eval(s, "delayed", episodes, n_agents, K, D, lr, flip_p, memory_mode)
        p_i, p_a = _train_and_eval(s, "present", episodes, n_agents, K, D, lr, flip_p, memory_mode)
        di.append(d_i); da.append(d_a); pi.append(p_i); pa.append(p_a)

    floor = 1.0 / K
    delayed = ablation_verdict(di, da, intervention_verified=True, floor=floor, ceiling=1.0)
    present = ablation_verdict(pi, pa, intervention_verified=True, floor=floor, ceiling=1.0)
    present_med = float(np.median(pi))
    present_alive = floor + 0.05 < present_med < 0.9              # VIVANT (ni plancher ni plafond)
    specificity = "pass" if (present["verdict"] == "X_DECOY" and present_alive) else "fail"
    return {"delayed": delayed, "present": present, "present_alive": present_alive,
            "specificity_control": specificity, "functional_aliasing": "n/a", "n": len(seeds),
            "delayed_intact": di, "delayed_ablated": da, "present_intact": pi, "present_ablated": pa}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("MP_SEEDS", "12"))))
    ep = int(os.environ.get("MP_EPISODES", "800"))
    na = int(os.environ.get("MP_AGENTS", "16"))
    r = run_memory_perception_demand_probe(seeds, episodes=ep, n_agents=na)
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("delayed", "present", "specificity_control", "present_alive",
                               "functional_aliasing", "n")}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Lancer le smoke unitaire**

Run: `python -m pytest tests/test_memory_perception_probe.py -v`
Expected: PASS (forme correcte, `functional_aliasing == "n/a"`, n=2). Quelques secondes. Si échec d'interface (H non porté, learn_episode multi-tick), corriger d'après le code réel et re-signaler.

- [ ] **Step 5: Déclarer l'instrument calibré + écrire la calibration (oracle/aléatoire)**

In `tests/sandbox/test_instrument_calibration.py`, add to `CALIBRATED`:

```python
    # « memory demands perception » (delayed-match torch). Contrôle positif = memory ORACLE (rétention
    # parfaite -> déranger l'encodage effondre) ; contrôle négatif = memory ALÉATOIRE (inerte). Générateur A.
    "run_memory_perception_demand_probe": ["*"],
```

Append to `tests/sandbox/test_instrument_calibration.py`:

```python
def test_mp_oracle_memory_makes_perception_demanded():
    """CONTRÔLE POSITIF (générateur A) : avec une mémoire ORACLE (rétention parfaite de l'indice encodé),
    DÉRANGER la perception à l'encodage l'effondre -> DELAYED X_DEMANDED. Le banc SAIT produire l'effondrement.
    Oracle BYPASSE l'agent (guess = indice encodé) -> aucun entraînement -> episodes=0 valide, quelques secondes."""
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    r = run_memory_perception_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                           memory_mode="oracle")
    assert r["delayed"]["verdict"] == "X_DEMANDED", r["delayed"]
    assert r["delayed"]["ratio"] > 1.5


def test_mp_random_memory_is_inert_no_false_demand():
    """CONTRÔLE NÉGATIF : avec une mémoire ALÉATOIRE (guess décorrélé de l'indice), DÉRANGER la perception
    est inerte -> DELAYED PAS X_DEMANDED. Le banc ne FABRIQUE pas un effondrement inexistant."""
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    r = run_memory_perception_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                           memory_mode="random")
    assert r["delayed"]["verdict"] != "X_DEMANDED", r["delayed"]
```

Note d'implémentation : pour `oracle`/`random`, le guess BYPASSE l'agent (pas d'entraînement), donc `episodes=0` est un cas VALIDE et rapide (contrairement à SP-2 où le lecteur devait être entraîné). Vérifier que le code ne divise jamais par `episodes` et que la boucle `for _ in range(episodes)` s'exécute 0 fois proprement.

- [ ] **Step 6: Lancer la calibration + le cliquet**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k "mp_oracle or mp_random" -v`
Expected: PASS (2 cas ; oracle → X_DEMANDED, random → pas X_DEMANDED). Quelques secondes (oracle/random n'entraînent pas).

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.`

- [ ] **Step 7: Commit (FUSIONNÉ — sonde + calibration)**

```bash
git add tools/memory_perception_demand_probe.py tests/test_memory_perception_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # confirmer UNIQUEMENT ces trois chemins
git commit -m "feat(MEM-PERCEPTION): sonde memory-demande-perception (delayed-match) + calibration oracle/aleatoire (cliquet)"
```

Si le hook bloque sur un instrument d'une AUTRE session : stash path-scoped ce fichier étranger, commit, pop, vérifier identique — jamais `--no-verify`.

---

### Task 2: Run-verdict (n=12, FOREGROUND) + arête + record

**Files:**
- Create: `results/mem_perception_edge_accuracies.json`
- Modify: `data/agi_taxonomy/demands.json`
- Create: `docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md`

**Interfaces:**
- Consumes: `run_memory_perception_demand_probe` (Task 1), `check_agi_taxonomy` (déjà livré).
- Produces: la 2ᵉ arête dans `demands.json` + le record + les accuracies persistées.

- [ ] **Step 1: Pré-vol + SMOKE (mécanisme + débit)**

Run: `python -c "import time,json; from tools.memory_perception_demand_probe import run_memory_perception_demand_probe as R; t=time.time(); r=R(seeds=[0,1,2], episodes=300, n_agents=16, K=6, D=2); print('dt_s=%.1f' % (time.time()-t)); print('delayed', r['delayed']['verdict'], round(r['delayed']['ratio'],2), 'present_alive', r['present_alive'], 'spec', r['specificity_control'], 'delayed_intact_med', sorted(r['delayed_intact'])[1])"`

Attendu (smoke, 3 seeds) : imprime `dt_s` (débit — noter pour dimensionner n=12), `delayed` tend vers X_DEMANDED, `present_alive True`, `spec pass`. ⚠️ Le smoke à 3 seeds NE tranche PAS (n<12) — mécanisme + débit seulement.

**Décision de bornage** : si `dt_s` (3 seeds, 300 ep) projette un run n=12 à `episodes` cible > ~15 min, RÉDUIRE `episodes`/`n_agents` (ou augmenter si DELAYED n'émerge pas : `delayed_intact` médian doit dépasser `1/K + 0.15` ≈ 0.32). Ne PAS lancer un run non borné. Ne PAS extrapoler une tendance depuis un préfixe court.

- [ ] **Step 2: Run-verdict n=12 (borné, FOREGROUND) + persister**

⚠️ En FOREGROUND (bloquant), JAMAIS en background (leçon SP-2 : run background perdu ~92 min).

Run (ajuster `episodes`/`n_agents`/`D` d'après le smoke ; défaut prudent ci-dessous) :
`python -c "import json; from tools.memory_perception_demand_probe import run_memory_perception_demand_probe as R; r=R(seeds=list(range(12)), episodes=800, n_agents=16, K=6, D=2); json.dump(r, open('results/mem_perception_edge_accuracies.json','w'), indent=2); print('delayed', r['delayed']['verdict'], round(r['delayed']['ratio'],3), 'n', r['n']); print('present', r['present']['verdict'], 'alive', r['present_alive'], 'spec', r['specificity_control']); print('delayed_intact_med', sorted(r['delayed_intact'])[6], 'delayed_ablated_med', sorted(r['delayed_ablated'])[6])"`

Attendu : `delayed X_DEMANDED` (ratio > 1.5, intacte vivante > 1/K+0.15), `present alive True`, `spec pass`. Accuracies persistées dans `results/mem_perception_edge_accuracies.json`.

**Si `delayed` n'est PAS X_DEMANDED** : lire `delayed_intact_med` — si ≤ `1/K+0.15`, la rétention n'a pas émergé (augmenter `episodes` ou réduire `D`, re-smoke — précédent MEM-001/EVO-002 : le rappel différé PEUT être maîtrisé). Si intact vivant mais pas d'effondrement, c'est un VRAI nul → le graver honnêtement (arête NON écrite, record négatif). Ne pas forcer.

- [ ] **Step 3: Ajouter l'arête (seulement si X_DEMANDED + spec pass)**

Si et seulement si le run donne `delayed X_DEMANDED` ET `specificity_control == "pass"` ET `delayed_intact` médian > `1/K+0.15`, LIRE `data/agi_taxonomy/demands.json` (il contient déjà l'arête SP-2 `language→perception`) et AJOUTER la 2ᵉ arête à la liste (insérer le `ratio` réel arrondi) :

```json
{
  "capability": "memory",
  "prerequisite": "perception",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 0.0,
    "n": 12,
    "functional_aliasing": "n/a",
    "specificity_control": "pass",
    "record": "docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md"
  }
}
```

Le fichier devient une liste de DEUX arêtes (ne PAS écraser l'arête SP-2). Remplacer `"ratio": 0.0` par la valeur affichée à l'étape 2.

- [ ] **Step 4: Écrire le record (avant validation, car check_agi_taxonomy exige le fichier existant)**

Create `docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md` (insérer les valeurs réelles) :

```markdown
---
id: EDR-MEM-PERCEPTION
type: EDR
title: "Deuxième arête MESURÉE du graphe AGI-Taxonomy : la mémoire APPRISE DEMANDE la perception (ablation d'entrée à l'encodage, within-subject, X_DEMANDED ; inerte quand la réponse est présente au test)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
SP-2 a gravé la 1ère arête (`language→perception`). Deuxième arête MESURÉE : « memory demands perception » ?
La rétention APPRISE route-t-elle causalement par la perception ? On l'établit sur un proxy torch de rappel
différé (delayed-match-to-sample), par ablation d'ENTRÉE within-subject à l'ENCODAGE.

## Méthode
Delayed-match torch (MambaAgent, mémoire = état récurrent PORTÉ ; learn_episode, crédit du rappel). Ablation =
dérangement du one-hot de l'indice au tick d'ENCODAGE À L'ÉVAL (derange_rows, in-distribution). DELAYED : l'obs
de test ne montre rien → il faut la rétention. PRESENT (contrôle de demande VIVANT) : l'obs de test = vue
directe BRUITÉE de l'indice (flip_p). n=12 seeds, `ablation_verdict` (floor=1/K). Sonde calibrée (memory oracle
→ effondre ; aléatoire → inerte).

## Résultat
DELAYED : X_DEMANDED (ratio R_REEL ; intacte VIVANTE médiane M_INTACT > 1/K+0.15, ablée ~ hasard). PRESENT :
inerte sur métrique VIVANTE (specificity_control = pass). Donc la rétention apprise LIT causalement la
perception à l'encodage — arête `memory → perception` gravée dans `data/agi_taxonomy/demands.json`, validée par
`check_agi_taxonomy`. `functional_aliasing = "n/a"` (ablation d'entrée, pas de fuite de substrat) justifié par
le contrôle de demande.

## Portée (bornée)
Proxy hors-monde (delayed-match), pas la biosphère. Mémoire = état récurrent APPRIS (pas la mémoire
tautologique de l'intégrateur numpy MEM-001, écartée à dessein). Une seule arête. Coût borné (smoke + run n=12
plafonné FOREGROUND, accuracies persistées `results/mem_perception_edge_accuracies.json`).

## Ce que ça débloque
Deuxième arête MESURÉE du graphe AGI-Taxonomy — la modalité MÉMOIRE entre dans le DAG de prérequis. Le pipeline
SP-2 (ablation d'entrée + garde de spécificité → arête valide) est reproduit sur une nouvelle capacité.
Cf. `docs/superpowers/specs/2026-07-28-memory-perception-demand-edge-design.md`.
```

Remplacer `R_REEL`/`M_INTACT` par les valeurs de l'étape 2.

- [ ] **Step 5: Valider (arête + record + suite + cliquet)**

Run: `python tools/check_agi_taxonomy.py`   (attendu `2 arêtes, 0 violations`)
Run: `python tools/check_record_links.py`   (EDR-MEM-PERCEPTION non orphelin ; autres orphelins = sessions //)
Run: `python -m pytest tests/test_agi_taxonomy.py -q`   (tous PASS ; `test_demands_shipped_graph_validates` valide 2 arêtes)
Run: `python tools/check_instrument_calibration.py`   (OK)

- [ ] **Step 6: Commit**

```bash
git add data/agi_taxonomy/demands.json docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md results/mem_perception_edge_accuracies.json
git status --short   # confirmer UNIQUEMENT ces trois chemins
git commit -m "feat(MEM-PERCEPTION): 2e arete MESUREE memory->perception (X_DEMANDED, n=12) + record + demands.json"
```

Si `results/` est gitignored, `git add -f results/mem_perception_edge_accuracies.json` (précédent tracké dans SP-2). Si le hook bloque sur un fichier étranger : stash path-scoped, commit, pop, vérifier — jamais `--no-verify`.

---

## Self-Review

**Spec coverage :**
- §3 proxy delayed-match torch self-contained → Task 1 sonde (`_seq_inputs`, `_forward_seq` portant H). ✓
- §4 conditions DELAYED/PRESENT (vue de test bruitée) → `_seq_inputs` + `_noisy_onehot` + `present_alive`. ✓
- §5 ablation d'entrée à l'encodage → `derange_rows` sur `enc_in` dans `_seq_inputs`, à l'éval. `functional_aliasing='n/a'`. ✓
- §6 verdict (DELAYED X_DEMANDED, PRESENT inerte, n=12, floor=1/K) → `run_..._probe` retour + Task 2 run. ✓
- §7 calibration seam oracle/aléatoire (générateur A) → Task 1 Step 5 (2 cas + CALIBRATED ; oracle bypasse l'agent, episodes=0 valide). ✓
- §8 bornage (smoke, run FOREGROUND borné, persister, provenance réelle) → Task 2 Steps 1-2. ✓
- §9 arête AJOUTÉE (2 arêtes) + record + nul honnête → Task 2 Steps 3-4, garde de verdict. ✓
- §11 critères → couverts. §13 risques (rétention n'émerge pas → oracle tranche ; PRESENT vivant ; multi-tick H porté ; calibration obligatoire) → assertions + smoke + calibration + note d'interface. ✓

**Placeholder scan :** seules valeurs à remplir = ratio réel + M_INTACT, MESURÉES au run (Task 2), marquées `R_REEL`/`"ratio": 0.0`. Aucun TODO dans le code.

**Type consistency :** `run_memory_perception_demand_probe(seeds, episodes, n_agents, K, D, lr, flip_p, memory_mode)` renvoie `{delayed, present, present_alive, specificity_control, functional_aliasing, n, delayed_intact, delayed_ablated, present_intact, present_ablated}` — utilisé identiquement en Task 1 (tests) et Task 2 (run). L'arête (§9) porte `functional_aliasing:"n/a"` + `specificity_control:"pass"`, exactement ce que le validateur (livré SP-2) exige. Helpers privés `_seq_inputs`/`_forward_seq`/`_onehot`/`_noisy_onehot`/`_sample`/`_softmax`/`n_agents_of` ne matchent aucun motif de cliquet (`n_agents_of` sans underscore mais ne matche ni `run_*probe`, `measure_*`, `benchmark_*`, etc. — vérifier au cliquet Task 1 Step 6). ✓
