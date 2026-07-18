# EDR 202 KCHAIN — Phase A (monde + viabilité par-K) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le monde KCHAIN(K) (composition à profondeur K, `prog` caché persistant) + politiques de référence + gate de viabilité par-K, et PROUVER via un GATE DUR que chaque K ∈ {2,3,4,5} admet un monde viable (oracle-chaîne survit, métronome/random meurent) AVANT de construire l'apprenant (Phase B).

**Architecture:** Nouveau fichier standalone `tools/kchain_edr.py` (pur numpy). Accumulateur à progression persistante : STEP accumule `prog` si (matériau présent & `prog<K−1`), CONSUME rend +R si `prog==K−1` ; mis-émission coûte. K=2 = COS structurel. `calibrate_K` balaie `(R,E0)` et vérifie les gates de viabilité.

**Tech Stack:** Python, numpy (déterministe `np.random.default_rng`), pytest.

## Global Constraints

- **Standalone pur numpy** : nouveau fichier `tools/kchain_edr.py` + `tests/sandbox/test_kchain_edr.py`. AUCUN import de `src/`/`world_1_stoneage.py`/`backend_torch.py`/`craft_or_starve_edr.py`. Additif (nouveaux fichiers).
- **Constantes gelées** : `NOOP=0, STEP=1, CONSUME=2, FORAGE=3, N_ACTIONS=8, N_NOISE=4, OBS_DIM=6`. `Params(p_mat=0.8, R=8.0, c_step=0.5, c_step_bad=2.0, c_consume=0.2, c_consume_empty=6.0, h=1.0, f_forage=4.0, E0=12.0, T=1000)`.
- **Progression persistante** : `prog ∈ {0,…,K−1}` NE se reset PAS par cycle ; seul CONSUME-réussi (prog==K−1) le remet à 0. `prog` est un état du MONDE (les politiques de référence le lisent ; l'apprenant de Phase B ne l'observera PAS).
- **Mort ABSORBANTE** vérifiée 1×/sous-pas (fin). **Gates viabilité** (médiane sur seeds pilotes) : inesc → oracle-chaîne ≥ 0.90, métronome ≤ 0.40, random ≤ 0.20 ; absent → oracle-forage ≥ 0.90, random ≤ 0.20.
- **HORS PÉRIMÈTRE Phase A** (= Phase B) : `NpChainLearner`, fenêtre-crédit W, curriculum, `generality_curve`, `decompose_2x2_chain`.
- **Déterminisme** : `np.random.default_rng(seed)` ; deux runs au même seed byte-identiques. Gates/verdicts gelés.
- **Tree partagé** : chemins ABSOLUS worktree pour les handoffs sous-agent ; commits path-scopés ; pytest/git préfixés `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && …`.

## File Structure

- `tools/kchain_edr.py` — CREATE : constantes, `Params`, `_build_obs`, `rollout_chain`, politiques (oracle_chain/metronome/random/oracle_forage), `survival_auc` (T1) ; `_run_chain_logged`, `binding_gap`, `_median_surv`, `check_viability_gates_K`, `calibrate_K`, `viability_gate_all_K`, `_report_viability` + `__main__` (T2).
- `tests/sandbox/test_kchain_edr.py` — CREATE : accounting/déterminisme/viabilité-sanité (T1) ; binding_gap + calibrate contrat (T2).

Deux tâches : **T1** = monde + politiques + survie ; **T2** = binding_gap + calibration/viabilité + gate DUR + CLI.

---

### Task 1: Monde KCHAIN + politiques de référence + survie

**Files:**
- Create: `tools/kchain_edr.py`
- Test: `tests/sandbox/test_kchain_edr.py`

**Interfaces:**
- Produces :
  - Constantes `NOOP,STEP,CONSUME,FORAGE,N_ACTIONS,N_NOISE,OBS_DIM` ; `Params` (dataclass frozen).
  - `_build_obs(mat, noise) -> obs[M,OBS_DIM]`.
  - `rollout_chain(policy, arm, K, params, seed, M, mat_stream=None) -> alive_matrix[M,T]` bool. `policy(obs, mem, prog) -> (actions[M] int, mem)`, `mem=None` au 1er appel ; `arm in {'inesc','absent'}`.
  - `oracle_chain_policy(K)`, `metronome_policy(K)`, `random_policy(seed)`, `oracle_forage_policy()`.
  - `survival_auc(alive_matrix) -> float` (médiane-par-agent, dernier quart).
  - `PILOT_SEEDS = (2000, 2001, 2002, 2003)`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/sandbox/test_kchain_edr.py` :

```python
import numpy as np
import pytest

from tools.kchain_edr import (
    Params, rollout_chain, survival_auc, NOOP, STEP, CONSUME, FORAGE, N_ACTIONS, OBS_DIM,
    oracle_chain_policy, metronome_policy, random_policy, oracle_forage_policy,
)


def test_oracle_chain_survives_with_materials_k2():
    # K=2, materiau TOUJOURS present : l'oracle STEP (prog 0->1) puis CONSUME (+R) -> gain net positif -> survit.
    p = Params(E0=50.0, T=8)
    mat = np.ones((1, 8), dtype=float)
    am = rollout_chain(oracle_chain_policy(2), 'inesc', 2, p, seed=0, M=1, mat_stream=mat)
    assert am.shape == (1, 8)
    assert am.all()   # drift positif -> vivant tout du long


def test_metronome_consume_empty_penalty_k3():
    # K=3, materiau ABSENT : le metronome STEP,STEP,CONSUME open-loop -> STEP gaspilles (pas de mat) -> prog reste 0
    # -> CONSUME a prog<K-1 = consume_empty (cout 6) -> meurt vite. E0 bas.
    p = Params(E0=6.0, T=30)
    mat = np.zeros((1, 30), dtype=float)
    am = rollout_chain(metronome_policy(3), 'inesc', 3, p, seed=0, M=1, mat_stream=mat)
    assert not am[:, -1].any()   # mort


def test_rollout_determinism():
    a = rollout_chain(random_policy(5), 'inesc', 3, Params(T=100), seed=5, M=16)
    b = rollout_chain(random_policy(5), 'inesc', 3, Params(T=100), seed=5, M=16)
    assert np.array_equal(a, b)


def test_survival_auc_range():
    am = rollout_chain(oracle_chain_policy(2), 'inesc', 2, Params(E0=50.0, T=40), seed=1, M=8)
    s = survival_auc(am)
    assert 0.0 <= s <= 1.0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.kchain_edr'`.

- [ ] **Step 3: Écrire le monde + les politiques**

Créer `tools/kchain_edr.py` :

```python
"""tools/kchain_edr.py — Ecologie KCHAIN (EDR 202) : composition a profondeur K parametrable.

Generalise CRAFT-OR-STARVE (EDR 200) : composer = accumuler K-1 pas (STEP, si materiau present) puis CONSUME.
La progression `prog` est CACHEE et PERSISTANTE ; seul CONSUME-a-prog-complet rend +R (mis-emission COUTE).
K=2 = COS structurel. But EDR 202 : le levier credit-horizon x curriculum generalise-t-il a K>2 ?
Phase A (ce fichier, PUR NUMPY, standalone) : monde + politiques de reference + gate de viabilite par-K.
Usage : python -m tools.kchain_edr  (calibration + gate de viabilite K in {2,3,4,5}).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass, replace

import numpy as np

NOOP, STEP, CONSUME, FORAGE = 0, 1, 2, 3
N_ACTIONS = 8
N_NOISE = 4
OBS_DIM = 2 + N_NOISE   # [mat, bias=1, noise x N_NOISE]

PILOT_SEEDS = (2000, 2001, 2002, 2003)


@dataclass(frozen=True)
class Params:
    p_mat: float = 0.8
    R: float = 8.0
    c_step: float = 0.5
    c_step_bad: float = 2.0
    c_consume: float = 0.2
    c_consume_empty: float = 6.0
    h: float = 1.0
    f_forage: float = 4.0
    E0: float = 12.0
    T: int = 1000


def _build_obs(mat, noise):
    """obs[M, OBS_DIM] = [mat, bias=1, noise x N_NOISE]. PAS de prog observable (cache)."""
    M = mat.shape[0]
    obs = np.zeros((M, OBS_DIM), dtype=np.float64)
    obs[:, 0] = mat
    obs[:, 1] = 1.0
    obs[:, 2:] = noise
    return obs


def rollout_chain(policy, arm, K, params, seed, M, mat_stream=None):
    """Deroule M agents (mondes PRIVES) sur T sous-pas. arm in {'inesc','absent'}.
    policy(obs[M,OBS_DIM], mem, prog[M]) -> (actions[M] int, mem) ; mem=None au 1er appel.
    prog PERSISTANT in {0..K-1} (les policies de reference le lisent ; l'apprenant Phase B ne l'observe pas).
    mat_stream optionnel [M,T] 0/1 force la matiere (tests). Retourne alive_matrix[M,T] bool (mort ABSORBANTE)."""
    rng = np.random.default_rng(seed)
    P = params
    E = np.full(M, P.E0, dtype=np.float64)
    prog = np.zeros(M, dtype=np.int64)
    alive = np.ones(M, dtype=bool)
    pending = np.zeros(M, dtype=np.float64)
    mem = None
    alive_matrix = np.zeros((M, P.T), dtype=bool)
    for t in range(P.T):
        if mat_stream is not None:
            mat = mat_stream[:, t].astype(np.float64)
        else:
            mat = (rng.random(M) < P.p_mat).astype(np.float64)
        obs = _build_obs(mat, rng.standard_normal((M, N_NOISE)))
        a, mem = policy(obs, mem, prog)
        a = np.asarray(a)
        matb = mat > 0.5
        if arm == 'inesc':
            step = alive & (a == STEP)
            step_ok = step & matb & (prog < K - 1)
            step_bad = step & ~step_ok
            cons = alive & (a == CONSUME)
            cons_ok = cons & (prog == K - 1)
            cons_empty = cons & ~cons_ok
            E = E - np.where(step_ok, P.c_step, 0.0) - np.where(step_bad, P.c_step_bad, 0.0)
            E = E + np.where(cons_ok, P.R, 0.0) - np.where(cons_ok, P.c_consume, 0.0) - np.where(cons_empty, P.c_consume_empty, 0.0)
            prog = np.where(step_ok, prog + 1, prog)
            prog = np.where(cons_ok, 0, prog)
        else:  # absent : FORAGE -> livraison inconditionnelle au sous-pas SUIVANT (delai apparie)
            E = E + np.where(alive, pending, 0.0)
            foraged = alive & (a == FORAGE)
            pending = np.where(foraged, P.f_forage, 0.0)
        E = E - np.where(alive, P.h, 0.0)
        alive = alive & (E > 0.0)
        alive_matrix[:, t] = alive
    return alive_matrix


def survival_auc(alive_matrix):
    """MEDIANE-PAR-AGENT de la fraction de sous-pas vivants sur le DERNIER QUART (defense anti-immortels)."""
    T = alive_matrix.shape[1]
    q = (3 * T) // 4
    per_agent = alive_matrix[:, q:].mean(axis=1)
    return float(np.median(per_agent))


def oracle_chain_policy(K):
    """Optimal : CONSUME si prog==K-1 ; sinon STEP si (mat & prog<K-1) ; sinon NOOP. Lit prog (oracle)."""
    def policy(obs, mem, prog):
        mat = obs[:, 0] > 0.5
        a = np.full(obs.shape[0], NOOP, dtype=int)
        a = np.where(mat & (prog < K - 1), STEP, a)
        a = np.where(prog == K - 1, CONSUME, a)
        return a, mem
    return policy


def metronome_policy(K):
    """Open-loop : STEP (K-1 fois) puis CONSUME, en boucle ; ne lit NI mat NI prog (compteur propre)."""
    def policy(obs, mem, prog):
        M = obs.shape[0]
        if mem is None:
            mem = {'c': np.zeros(M, dtype=np.int64)}
        c = mem['c']
        a = np.where(c < K - 1, STEP, CONSUME).astype(int)
        c = np.where(c < K - 1, c + 1, 0)
        mem = {'c': c}
        return a, mem
    return policy


def random_policy(seed):
    """Action uniforme sur N_ACTIONS ; rng propre (independant du monde) mais deterministe au seed."""
    rng = np.random.default_rng((int(seed) ^ 0x9E3779B9) & 0xFFFFFFFF)
    def policy(obs, mem, prog):
        M = obs.shape[0]
        return rng.integers(0, N_ACTIONS, size=M), mem
    return policy


def oracle_forage_policy():
    """Bras absent : FORAGE a chaque sous-pas (livraison inconditionnelle au suivant)."""
    def policy(obs, mem, prog):
        return np.full(obs.shape[0], FORAGE, dtype=int), mem
    return policy
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -q`
Expected: PASS — 4 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202"
git add -- tools/kchain_edr.py tests/sandbox/test_kchain_edr.py
git commit -m "feat(EDR-202): monde KCHAIN(K) + politiques de reference + survie (Phase A T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: binding_gap + calibration/viabilité par-K + GATE DUR + CLI

**Files:**
- Modify: `tools/kchain_edr.py` (APPEND + `__main__`)
- Test: `tests/sandbox/test_kchain_edr.py` (APPEND)

**Interfaces:**
- Consumes : `rollout_chain, _build_obs, survival_auc, oracle_chain_policy, metronome_policy, random_policy, oracle_forage_policy, Params, replace, PILOT_SEEDS, np, STEP, CONSUME, N_NOISE, K` (T1).
- Produces :
  - `_run_chain_logged(policy_act, arm, K, params, seed, M) -> (alive_matrix[M,T], (prog_log[T,M], cons_log[T,M], alive_log[T,M]))` : déroule avec `policy_act(obs, mem, prog)->(a, mem)`, journalise (prog AVANT action, action==CONSUME) par sous-pas.
  - `binding_gap(s2) -> float` : `P(CONSUME|prog==K-1) − P(CONSUME|prog<K-1)` sur agents vivants, dernier quart. `s2 = (prog_log, cons_log, alive_log, K)`.
  - `_median_surv(policy_factory, arm, K, params, seeds, M) -> float`.
  - `check_viability_gates_K(K, params, seeds, M) -> {"gates": {...}, "aucs": {...}}`.
  - `calibrate_K(K, seeds=PILOT_SEEDS, r_grid=(4.,6.,8.,10.,12.,16.), e0_grid=(8.,12.,16.,24.,32.), M=64) -> {"ok","R_K","E0_K","last"}`.
  - `viability_gate_all_K(k_grid=(2,3,4,5), seeds=PILOT_SEEDS, M=64) -> {"per_K":[{K,ok,R_K,E0_K}], "all_ok"}`.
  - `_report_viability(res)`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_kchain_edr.py` :

```python
from tools.kchain_edr import binding_gap, _run_chain_logged, calibrate_K


def test_binding_gap_oracle_high_metronome_low():
    # oracle : CONSUME ssi prog==K-1 -> binding_gap eleve. metronome : CONSUME open-loop -> ~0.
    P = Params(E0=50.0, T=200)
    orc = oracle_chain_policy(3)
    met = metronome_policy(3)
    _, so = _run_chain_logged(lambda obs, mem, prog: orc(obs, mem, prog), 'inesc', 3, P, seed=7, M=32)
    _, sm = _run_chain_logged(lambda obs, mem, prog: met(obs, mem, prog), 'inesc', 3, P, seed=7, M=32)
    go = binding_gap((*so, 3))
    gm = binding_gap((*sm, 3))
    assert go > 0.6           # l'oracle conditionne fortement (CONSUME ssi prog==K-1)
    assert gm < go - 0.3      # le metronome conditionne NETTEMENT moins (ne lit pas prog)


def test_calibrate_k_contract():
    # CONTRAT seulement (config reduite) : structure + la fenetre.
    res = calibrate_K(2, seeds=(2000,), r_grid=(8.0, 12.0), e0_grid=(12.0, 24.0), M=16)
    assert set(res) >= {"ok", "R_K", "E0_K", "last"}
    assert isinstance(res["ok"], bool)
    if res["ok"]:
        assert res["R_K"] in (8.0, 12.0) and res["E0_K"] in (12.0, 24.0)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "binding_gap or calibrate" -q`
Expected: FAIL — `ImportError: cannot import name 'binding_gap'`.

- [ ] **Step 3: Écrire les métriques + la calibration + le gate**

Ajouter à `tools/kchain_edr.py` (avant `if __name__`) :

```python
def _run_chain_logged(policy_act, arm, K, params, seed, M):
    """Comme rollout_chain mais journalise (prog AVANT action, action==CONSUME, alive) par sous-pas pour binding_gap.
    policy_act(obs, mem, prog) -> (actions, mem)."""
    rng = np.random.default_rng(seed)
    P = params
    E = np.full(M, P.E0, dtype=np.float64)
    prog = np.zeros(M, dtype=np.int64)
    alive = np.ones(M, dtype=bool)
    pending = np.zeros(M, dtype=np.float64)
    mem = None
    alive_matrix = np.zeros((M, P.T), dtype=bool)
    prog_log, cons_log, alive_log = [], [], []
    for t in range(P.T):
        mat = (rng.random(M) < P.p_mat).astype(np.float64)
        obs = _build_obs(mat, rng.standard_normal((M, N_NOISE)))
        a, mem = policy_act(obs, mem, prog)
        a = np.asarray(a)
        prog_log.append(prog.copy())
        cons_log.append(a == CONSUME)
        alive_log.append(alive.copy())
        matb = mat > 0.5
        if arm == 'inesc':
            step = alive & (a == STEP)
            step_ok = step & matb & (prog < K - 1)
            step_bad = step & ~step_ok
            cons = alive & (a == CONSUME)
            cons_ok = cons & (prog == K - 1)
            cons_empty = cons & ~cons_ok
            E = E - np.where(step_ok, P.c_step, 0.0) - np.where(step_bad, P.c_step_bad, 0.0)
            E = E + np.where(cons_ok, P.R, 0.0) - np.where(cons_ok, P.c_consume, 0.0) - np.where(cons_empty, P.c_consume_empty, 0.0)
            prog = np.where(step_ok, prog + 1, prog)
            prog = np.where(cons_ok, 0, prog)
        else:
            E = E + np.where(alive, pending, 0.0)
            foraged = alive & (a == FORAGE)
            pending = np.where(foraged, P.f_forage, 0.0)
        E = E - np.where(alive, P.h, 0.0)
        alive = alive & (E > 0.0)
        alive_matrix[:, t] = alive
    return alive_matrix, (np.array(prog_log), np.array(cons_log), np.array(alive_log))


def binding_gap(s2):
    """P(CONSUME|prog==K-1) - P(CONSUME|prog<K-1) sur les sous-pas des agents VIVANTS, dernier quart. s2=(prog,cons,alive,K)."""
    prog, cons, al, K = s2
    T = prog.shape[0]
    q = (3 * T) // 4
    prog, cons, al = prog[q:], cons[q:], al[q:]
    m1 = al & (prog == K - 1)
    m0 = al & (prog < K - 1)
    p1 = float(cons[m1].mean()) if m1.any() else 0.0
    p0 = float(cons[m0].mean()) if m0.any() else 0.0
    return p1 - p0


def _median_surv(policy_factory, arm, K, params, seeds, M):
    """Mediane sur les seeds de survival_auc (chacun deja mediane-par-agent)."""
    vals = []
    for s in seeds:
        am = rollout_chain(policy_factory(s), arm, K, params, seed=int(s), M=M)
        vals.append(survival_auc(am))
    return float(np.median(vals))


def check_viability_gates_K(K, params, seeds=PILOT_SEEDS, M=64):
    """Gates viabilite du monde K (inesc : oracle-chaine >=0.90, metronome <=0.40, random <=0.20 ;
    absent : oracle-forage >=0.90, random <=0.20). Le monde EXIGE-t-il le conditionnement a cette config ?"""
    orc = _median_surv(lambda s: oracle_chain_policy(K), 'inesc', K, params, seeds, M)
    met = _median_surv(lambda s: metronome_policy(K), 'inesc', K, params, seeds, M)
    rnd_i = _median_surv(lambda s: random_policy(s), 'inesc', K, params, seeds, M)
    forage = _median_surv(lambda s: oracle_forage_policy(), 'absent', K, params, seeds, M)
    rnd_a = _median_surv(lambda s: random_policy(s), 'absent', K, params, seeds, M)
    gates = {
        'G1_oracle_chain': bool(orc >= 0.90),
        'G2_metronome': bool(met <= 0.40),
        'G3_random_inesc': bool(rnd_i <= 0.20),
        'G4_forage': bool((forage >= 0.90) and (rnd_a <= 0.20)),
    }
    gates['ALL'] = bool(all(gates.values()))
    aucs = {'oracle_chain': orc, 'metronome': met, 'random_inesc': rnd_i, 'oracle_forage': forage, 'random_absent': rnd_a}
    return {'gates': gates, 'aucs': aucs}


def calibrate_K(K, seeds=PILOT_SEEDS, r_grid=(4., 6., 8., 10., 12., 16.), e0_grid=(8., 12., 16., 24., 32.), M=64):
    """Balaie (R, E0) et renvoie le 1er (R_K, E0_K) rendant le monde K viable (toutes gates). E0_K = BORNE INFERIEURE
    (Phase B re-calibre contre le headroom apprenant, cf I1). Autres params geles (spec)."""
    last = None
    for r in r_grid:
        for e0 in e0_grid:
            last = check_viability_gates_K(K, replace(Params(), R=r, E0=e0), seeds, M)
            if last['gates']['ALL']:
                return {'ok': True, 'R_K': r, 'E0_K': e0, 'last': last}
    return {'ok': False, 'R_K': None, 'E0_K': None, 'last': last}


def viability_gate_all_K(k_grid=(2, 3, 4, 5), seeds=PILOT_SEEDS, M=64):
    """GATE DUR de viabilite : pour chaque K, un (R,E0) doit rendre le monde viable. all_ok => Phase B autorisee."""
    per_K = []
    for K in k_grid:
        c = calibrate_K(K, seeds=seeds, M=M)
        per_K.append({'K': K, 'ok': c['ok'], 'R_K': c['R_K'], 'E0_K': c['E0_K']})
    return {'per_K': per_K, 'all_ok': bool(all(row['ok'] for row in per_K))}


def _report_viability(res):
    print("\n=== EDR 202 KCHAIN — GATE DUR de viabilite par-K (Phase A) ===")
    for row in res['per_K']:
        print("    K=%d  viable=%s  R_K=%s  E0_K=%s" % (row['K'], row['ok'], row['R_K'], row['E0_K']))
    print("=== %s ===" % ("TOUS VIABLES -> Phase B autorisee (RE-CALIBRER E0 contre headroom apprenant, I1)"
                          if res['all_ok'] else "AU MOINS UN K NON-VIABLE -> borner le K_grid de Phase B a la fenetre viable"))
```

Et ajouter le bloc `__main__` à la fin :

```python
if __name__ == "__main__":
    _report_viability(viability_gate_all_K())
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "binding_gap or calibrate" -q`
Expected: PASS — 2 tests verts. (Puis la suite complète : `python -m pytest tests/sandbox/test_kchain_edr.py -q`.)

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202"
git add -- tools/kchain_edr.py tests/sandbox/test_kchain_edr.py
git commit -m "feat(EDR-202): binding_gap + calibration/viabilite par-K + GATE DUR (Phase A T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## GATE DUR viabilité (hors tâches TDD — action du contrôleur après revue finale)

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m tools.kchain_edr` (2 passes byte-identiques).
- **TOUS VIABLES** (chaque K ∈ {2,3,4,5} admet un `(R_K,E0_K)` : oracle-chaîne ≥ 0.90, métronome ≤ 0.40, random ≤ 0.20, forage/absent OK) → le monde KCHAIN EXIGE le conditionnement à toute profondeur → **Phase B autorisée** (re-calibrer E0 contre le headroom apprenant, I1).
- **AU MOINS UN K NON-VIABLE** → borner le `K_grid` de Phase B à la fenêtre viable (résultat en soi : la profondeur casse la viabilité du monde AVANT même l'apprentissage) ; diagnostic (élargir `r_grid`/`e0_grid`, revoir `p_mat`) AVANT Phase B.
