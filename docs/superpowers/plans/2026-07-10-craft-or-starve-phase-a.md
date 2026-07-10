# EDR 200 CRAFT-OR-STARVE — Phase A (pilote) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le pilote de l'écologie CRAFT-OR-STARVE (moteur de monde + politiques de référence + gates de viabilité) pour prouver que le monde EXIGE le conditionnement AVANT de construire les substrats (Phase B).

**Architecture:** Un seul fichier tool `tools/craft_or_starve_edr.py`, **pur numpy** (aucun torch en Phase A — torch entre en Phase B avec les substrats). Un monde de survie à 2 sous-pas (craft/consume) où la matière est exogène-stochastique et la mis-émission coûte, rollout vectorisé sur une cohorte, métrique de survie médiane-par-agent, 4 politiques de référence câblées, et un vérificateur de gates de viabilité + une routine de calibration de `E0`.

**Tech Stack:** Python, numpy (déterministe via `np.random.default_rng`), pytest. AUCUN torch, AUCUN import de `src/`.

## Global Constraints

- **Additif strict** : créer UNIQUEMENT `tools/craft_or_starve_edr.py` et `tests/sandbox/test_craft_or_starve_edr.py`. Ne modifier AUCUN fichier existant. Aucun import de `src/`, `world_1_stoneage.py`, `backend_torch.py` (fil // actif). **Phase A = PUR NUMPY** (pas de torch).
- **Périmètre Phase A UNIQUEMENT** : monde + politiques de référence + métrique + gates de viabilité + calibration. Les substrats L0/L1/L2, `compute_verdict`, le runner 3×2×16 sont **HORS PÉRIMÈTRE** (Phase B, contingente).
- **Constantes gelées (du spec §1 ; `E0` est le knob de calibration)** : `p_mat=0.5, R=8.0, h=1.0, c_consume_empty=6.0, c_craft_nomat=3.0, c_craft=0.5, f_forage=4.0, T=800, N_ACTIONS=8` (4 nommées + 4 leurres), `OBS_DIM=6`.
- **Actions** : `NOOP=0, CRAFT=1, CONSUME=2, FORAGE=3` ; indices 4-7 = leurres.
- **Gates de viabilité Phase A** (world-only ; G4/G6/G7/G8 = Phase B) : `G1` oracle-composeur médiane ≥ 0.90 (inesc) ; `G2` random ≤ 0.20 (inesc) ; `G3` oracle-forage ≥ 0.90 ∧ random ≤ 0.20 (absent) ; `G5` métronome ≤ 0.40 (inesc).
- **Métrique** : `survival_auc` = MÉDIANE-PAR-AGENT de la fraction de ticks vivants sur le DERNIER QUART (défense anti-immortels).
- **Déterminisme** : `np.random.default_rng(seed)` ; deux rollouts au même seed byte-identiques.
- **GATE DUR (après T2, action contrôleur)** : lancer `calibrate()` ; si aucun `E0` ne fait passer G1∧G2∧G3∧G5, **STOP** et réviser le design AVANT toute Phase B.
- **Path-scopé** : `git add -- <chemins exacts>`, jamais `git add -A`.

---

## File Structure

- `tools/craft_or_starve_edr.py` — Phase A : constantes/`Params`, `_build_obs`, `rollout`, `survival_auc`, les 4 politiques de référence, `check_viability_gates`, `calibrate`.
- `tests/sandbox/test_craft_or_starve_edr.py` — tests TDD Phase A.

Deux tâches : **T1** = moteur de monde + politiques + métrique (comptabilité énergétique exacte, déterminisme) ; **T2** = gates de viabilité + calibration (le monde discrimine le conditionnement).

---

### Task 1: Moteur de monde + politiques de référence + métrique

**Files:**
- Create: `tools/craft_or_starve_edr.py`
- Test: `tests/sandbox/test_craft_or_starve_edr.py`

**Interfaces:**
- Produces :
  - `Params` (dataclass frozen, champs et défauts ci-dessous).
  - `rollout(policy, arm, params, seed, M, mat_stream=None) -> np.ndarray[bool] (M, T)` : `alive_matrix` (vivant en fin de tick). `arm ∈ {'inesc','absent'}`. `policy` = callable `(obs[M,OBS_DIM], mem, phase) -> (actions[M] int, mem)` (mem=None au 1er appel).
  - `survival_auc(alive_matrix) -> float`.
  - Fabriques de politiques : `oracle_composer_policy()`, `metronome_policy()`, `oracle_forage_policy()`, `random_policy(seed)` — chacune retourne un callable de signature policy.
  - Constantes `NOOP, CRAFT, CONSUME, FORAGE, N_ACTIONS, N_NOISE, OBS_DIM`.

- [ ] **Step 1: Écrire les tests qui échouent (monde + comptabilité + déterminisme)**

Créer `tests/sandbox/test_craft_or_starve_edr.py` :

```python
import numpy as np
import pytest

from tools.craft_or_starve_edr import (
    Params, rollout, survival_auc, NOOP, CRAFT, CONSUME, FORAGE, N_ACTIONS, OBS_DIM,
    oracle_composer_policy, metronome_policy, oracle_forage_policy, random_policy,
)


def test_composer_accounting_alternating_stream():
    # stream mat = [1,0,1,0] : composeur => cycle mat=1 : +5.5 ; cycle mat=0 : -2.0. E0 haut => reste vivant.
    p = Params(E0=100.0, T=4)
    mat = np.array([[1, 0, 1, 0]], dtype=float)
    am = rollout(oracle_composer_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    assert am.shape == (1, 4)
    assert am.all()  # E0=100, drift positif => vivant tout du long


def test_metronome_dies_faster_than_composer_same_stream():
    # meme stream : metronome cycle mat=1 : +5.5 ; cycle mat=0 : -11.0 (craft-sans-mat -3 + consume-vide -6 + 2h)
    p = Params(E0=6.0, T=8)
    mat = np.array([[0, 0, 0, 0, 0, 0, 0, 0]], dtype=float)  # que du mat=0 : pire cas
    am_metro = rollout(metronome_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    am_comp = rollout(oracle_composer_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    # metronome : -11/cycle => mort au 1er cycle (E0=6) ; composeur : -2/cycle => survit plus longtemps
    assert not am_metro[0, 0]                 # metronome mort des le 1er tick
    assert am_comp[:, :2].all()               # composeur encore vivant a t=0 et t=1


def test_absorbing_death():
    p = Params(E0=1.5, T=5)
    mat = np.zeros((1, 5), dtype=float)
    am = rollout(metronome_policy(), 'inesc', p, seed=0, M=1, mat_stream=mat)
    # une fois mort, reste mort (monotone decroissant de alive)
    a = am[0]
    assert not a[-1]
    for i in range(1, len(a)):
        assert not (a[i] and not a[i - 1])   # jamais de resurrection


def test_absent_arm_forage_delivers_unconditionally():
    # bras absent : FORAGE en S1 => +f_forage a S2 sans condition. oracle_forage survit (net +2/cycle).
    p = Params(E0=6.0, T=50, f_forage=4.0)
    am_forage = rollout(oracle_forage_policy(), 'absent', p, seed=1, M=1)
    am_noop = rollout(metronome_policy(), 'absent', p, seed=1, M=1)  # ne forage jamais (CRAFT/CONSUME inertes en absent)
    assert am_forage.all()          # forage net positif => vivant
    assert not am_noop[0, -1]       # jamais de nourriture => meurt


def test_determinism_two_rollouts_identical():
    p = Params(E0=10.0, T=100)
    a = rollout(random_policy(7), 'inesc', p, seed=7, M=32)
    b = rollout(random_policy(7), 'inesc', p, seed=7, M=32)
    assert np.array_equal(a, b)


def test_survival_auc_range_and_median():
    # alive_matrix synthetique : 3 agents, T=8, dernier quart = 2 derniers ticks
    am = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1],   # vivant : dernier quart = 1.0
        [1, 1, 1, 1, 1, 1, 0, 0],   # mort avant dernier quart : 0.0
        [1, 1, 1, 1, 1, 1, 1, 0],   # dernier quart = [1,0] => 0.5
    ], dtype=bool)
    # medianes-par-agent = median(1.0, 0.0, 0.5) = 0.5
    assert survival_auc(am) == pytest.approx(0.5)


def test_obs_shape_and_action_space():
    p = Params(E0=100.0, T=1)
    seen = {}

    def probe(obs, mem, phase):
        seen['obs_dim'] = obs.shape[1]
        return np.full(obs.shape[0], NOOP, dtype=int), mem

    rollout(probe, 'inesc', p, seed=0, M=3)
    assert seen['obs_dim'] == OBS_DIM
    assert N_ACTIONS == 8
```

- [ ] **Step 2: Lancer les tests, vérifier l'échec**

Run: `cd .claude/worktrees/craft-or-starve && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (le module n'existe pas).

- [ ] **Step 3: Écrire le moteur de monde + politiques + métrique**

Créer `tools/craft_or_starve_edr.py` :

```python
"""tools/craft_or_starve_edr.py — Ecologie decisive CRAFT-OR-STARVE (EDR 200, bloc 200+).

Phase A (pilote, PUR NUMPY) : un monde de survie ou CONSUME conditionne sur un inventaire crafte est la SEULE
source d'energie ; la matiere est EXOGENE-stochastique (defait l'horloge) et la mis-emission COUTE (rend le
binding fitness-pertinent). But du pilote : prouver via les GATES DE VIABILITE que le monde EXIGE le conditionnement
(l'oracle-composeur vit, le metronome/random meurent) AVANT de construire les substrats (Phase B). Additif, aucun
import de src/ ni du fil torch //. Spec : docs/superpowers/specs/2026-07-10-craft-or-starve-decisive-edr-design.md.
Usage : python -m tools.craft_or_starve_edr  (lance la calibration + rapport des gates)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass, replace

import numpy as np

# --- espace d'actions (4 nommees + 4 leurres pour le regime READOUT_GAP de la Phase B) ---
NOOP, CRAFT, CONSUME, FORAGE = 0, 1, 2, 3
N_ACTIONS = 8
N_NOISE = 4
OBS_DIM = 2 + N_NOISE   # [mat, phase, noise x N_NOISE]


@dataclass(frozen=True)
class Params:
    p_mat: float = 0.5
    R: float = 8.0
    h: float = 1.0
    c_consume_empty: float = 6.0
    c_craft_nomat: float = 3.0
    c_craft: float = 0.5
    f_forage: float = 4.0
    E0: float = 10.0
    T: int = 800


def _build_obs(mat, phase, noise):
    """obs[M, OBS_DIM] = [mat (valide S1), phase (0/1), noise x N_NOISE]."""
    M = mat.shape[0]
    obs = np.zeros((M, OBS_DIM), dtype=np.float64)
    obs[:, 0] = mat
    obs[:, 1] = float(phase)
    obs[:, 2:] = noise
    return obs


def rollout(policy, arm, params, seed, M, mat_stream=None):
    """Deroule M agents (mondes PRIVES disjoints) sur T ticks (2 sous-pas S1/S2 chacun).
    arm in {'inesc','absent'}. policy: callable (obs[M,OBS_DIM], mem, phase)->(actions[M] int, mem), mem=None au 1er appel.
    mat_stream (optionnel [M,T] 0/1) force la sequence de matiere (tests) ; sinon tiree de rng(seed).
    Retourne alive_matrix [M, T] bool (etat vivant en FIN de tick). Mort = E<=0 ABSORBANTE."""
    rng = np.random.default_rng(seed)
    P = params
    E = np.full(M, P.E0, dtype=np.float64)
    inv = np.zeros(M, dtype=bool)
    alive = np.ones(M, dtype=bool)
    pending = np.zeros(M, dtype=np.float64)
    mem = None
    alive_matrix = np.zeros((M, P.T), dtype=bool)
    for t in range(P.T):
        # --- S1 : phase craft ---
        if mat_stream is not None:
            mat = mat_stream[:, t].astype(np.float64)
        else:
            mat = (rng.random(M) < P.p_mat).astype(np.float64)
        obs1 = _build_obs(mat, 0, rng.standard_normal((M, N_NOISE)))
        a1, mem = policy(obs1, mem, 0)
        a1 = np.asarray(a1)
        matb = mat > 0.5
        if arm == 'inesc':
            crafted = alive & (a1 == CRAFT)
            inv = np.where(crafted & matb, True, inv)
            E = E - np.where(crafted & matb, P.c_craft, 0.0) - np.where(crafted & ~matb, P.c_craft_nomat, 0.0)
        else:  # absent : FORAGE programme une livraison inconditionnelle a S2 (delai APPARIE au craft->consume)
            foraged = alive & (a1 == FORAGE)
            pending = np.where(foraged, P.f_forage, 0.0)
        E = E - np.where(alive, P.h, 0.0)
        alive = alive & (E > 0.0)
        # --- S2 : phase consume ---
        obs2 = _build_obs(np.zeros(M), 1, rng.standard_normal((M, N_NOISE)))
        a2, mem = policy(obs2, mem, 1)
        a2 = np.asarray(a2)
        if arm == 'inesc':
            consume = alive & (a2 == CONSUME)
            got = consume & inv
            E = E + np.where(got, P.R, 0.0) - np.where(consume & ~inv, P.c_consume_empty, 0.0)
            inv = np.where(got, False, inv)
        else:
            E = E + np.where(alive, pending, 0.0)
            pending = np.zeros(M, dtype=np.float64)
        E = E - np.where(alive, P.h, 0.0)
        alive = alive & (E > 0.0)
        alive_matrix[:, t] = alive
    return alive_matrix


def survival_auc(alive_matrix):
    """MEDIANE-PAR-AGENT de la fraction de ticks vivants sur le DERNIER QUART (defense anti-immortels EDR)."""
    T = alive_matrix.shape[1]
    q = (3 * T) // 4
    per_agent = alive_matrix[:, q:].mean(axis=1)
    return float(np.median(per_agent))


# --- politiques de reference (cablees, references/oracles ; ne "trichent" pas : lisent mat dans obs, portent leur propre inv) ---

def oracle_composer_policy():
    """Optimal conditionnel : CRAFT ssi mat (observe en S1) ; CONSUME ssi a crafte-avec-mat (inv porte en mem)."""
    def policy(obs, mem, phase):
        M = obs.shape[0]
        if phase == 0:
            mat = obs[:, 0] > 0.5
            a = np.where(mat, CRAFT, NOOP)
            mem = {'inv': mat.copy()}          # crafte-avec-mat -> inv=1
        else:
            if mem is None:
                mem = {'inv': np.zeros(M, dtype=bool)}
            a = np.where(mem['inv'], CONSUME, NOOP)
            mem = {'inv': np.zeros(M, dtype=bool)}
        return a.astype(int), mem
    return policy


def metronome_policy():
    """Open-loop periode-2 : CRAFT en S1, CONSUME en S2, sans jamais lire l'etat."""
    def policy(obs, mem, phase):
        M = obs.shape[0]
        a = np.full(M, CRAFT if phase == 0 else CONSUME, dtype=int)
        return a, mem
    return policy


def oracle_forage_policy():
    """Bras absent : FORAGE en S1 (livraison inconditionnelle a S2)."""
    def policy(obs, mem, phase):
        M = obs.shape[0]
        a = np.full(M, FORAGE if phase == 0 else NOOP, dtype=int)
        return a, mem
    return policy


def random_policy(seed):
    """Action uniforme sur N_ACTIONS ; rng propre (independant du monde) mais deterministe au seed."""
    rng = np.random.default_rng((int(seed) ^ 0x9E3779B9) & 0xFFFFFFFF)
    def policy(obs, mem, phase):
        M = obs.shape[0]
        return rng.integers(0, N_ACTIONS, size=M), mem
    return policy
```

- [ ] **Step 4: Lancer les tests, vérifier le succès**

Run: `cd .claude/worktrees/craft-or-starve && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -q`
Expected: PASS — 7 tests verts.

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/craft-or-starve
git add -- tools/craft_or_starve_edr.py tests/sandbox/test_craft_or_starve_edr.py
git commit -m "feat(EDR-200): moteur de monde CRAFT-OR-STARVE + politiques de reference + metrique (Phase A T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Gates de viabilité + calibration

**Files:**
- Modify: `tools/craft_or_starve_edr.py` (ajouter `check_viability_gates`, `calibrate`, bloc `__main__`)
- Test: `tests/sandbox/test_craft_or_starve_edr.py` (ajouter tests gates/discrimination/déterminisme)

**Interfaces:**
- Consumes : `Params, rollout, survival_auc`, les 4 fabriques de politiques (T1).
- Produces :
  - `PILOT_SEEDS = (1000, 1001, 1002, 1003)` (set DISJOINT du set confirmatoire Phase B).
  - `check_viability_gates(params, seeds=PILOT_SEEDS, M=128) -> dict` avec clés `{'gates': {...bools, 'ALL': bool}, 'aucs': {...floats}}`.
  - `calibrate(seeds=PILOT_SEEDS, e0_grid=(6.0,8.0,10.0,12.0,16.0,24.0), base=None, M=128) -> dict` : premier `E0` qui fait passer G1∧G2∧G3∧G5, sinon `{'ok': False, ...}`.

- [ ] **Step 1: Écrire les tests qui échouent (gates + discrimination)**

Ajouter à `tests/sandbox/test_craft_or_starve_edr.py` :

```python
from tools.craft_or_starve_edr import check_viability_gates, calibrate, PILOT_SEEDS


def test_gates_structure_and_bools():
    res = check_viability_gates(Params(E0=16.0), seeds=(1000, 1001), M=32)
    assert set(res['gates']) >= {'G1_oracle_composer', 'G2_random_inesc', 'G3_forage', 'G5_metronome', 'ALL'}
    assert set(res['aucs']) >= {'oracle_composer', 'random_inesc', 'oracle_forage', 'random_absent', 'metronome'}
    for v in res['gates'].values():
        assert isinstance(v, (bool, np.bool_))


def test_world_discriminates_conditioning():
    # coeur du pilote : a E0 confortable, l'oracle-composeur survit BEAUCOUP mieux que metronome ET random.
    res = check_viability_gates(Params(E0=16.0), seeds=(1000, 1001), M=64)
    a = res['aucs']
    assert a['oracle_composer'] > a['metronome']
    assert a['oracle_composer'] > a['random_inesc']
    assert a['oracle_composer'] >= 0.90        # G1 doit tenir a E0 confortable
    assert a['metronome'] <= 0.40              # G5 : l'horloge ne survit pas


def test_gates_deterministic():
    r1 = check_viability_gates(Params(E0=12.0), seeds=(1000, 1001), M=32)
    r2 = check_viability_gates(Params(E0=12.0), seeds=(1000, 1001), M=32)
    assert r1['aucs'] == r2['aucs']


def test_calibrate_returns_ok_or_report():
    # on ne prejuge PAS du verdict (c'est le GATE DUR du controleur) : on verifie le CONTRAT de retour.
    res = calibrate(seeds=(1000, 1001), e0_grid=(16.0, 24.0), M=32)
    assert 'ok' in res
    if res['ok']:
        assert res['result']['gates']['ALL']
        assert res['params'].E0 in (16.0, 24.0)
```

- [ ] **Step 2: Lancer les nouveaux tests, vérifier l'échec**

Run: `cd .claude/worktrees/craft-or-starve && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "gates or discrimin or calibrate" -q`
Expected: FAIL — `ImportError: cannot import name 'check_viability_gates'`.

- [ ] **Step 3: Ajouter les gates + calibration + `__main__`**

Ajouter à `tools/craft_or_starve_edr.py` (après `random_policy`) :

```python
PILOT_SEEDS = (1000, 1001, 1002, 1003)   # set DISJOINT du set confirmatoire Phase B


def _median_auc(policy_factory, arm, params, seeds, M):
    """Mediane sur les seeds de survival_auc (chacun deja mediane-par-agent sur M agents)."""
    vals = []
    for s in seeds:
        am = rollout(policy_factory(s), arm, params, seed=int(s), M=M)
        vals.append(survival_auc(am))
    return float(np.median(vals))


def check_viability_gates(params, seeds=PILOT_SEEDS, M=128):
    """Gates de viabilite Phase A (world-only) : le monde EXIGE-t-il le conditionnement ?
    G1 oracle-composeur>=0.90 (inesc) ; G2 random<=0.20 (inesc) ; G3 oracle-forage>=0.90 ET random<=0.20 (absent) ;
    G5 metronome<=0.40 (inesc). (G4/G6/G7/G8 = Phase B : substrats.)"""
    comp = _median_auc(lambda s: oracle_composer_policy(), 'inesc', params, seeds, M)
    rand_inesc = _median_auc(lambda s: random_policy(s), 'inesc', params, seeds, M)
    forage = _median_auc(lambda s: oracle_forage_policy(), 'absent', params, seeds, M)
    rand_absent = _median_auc(lambda s: random_policy(s), 'absent', params, seeds, M)
    metro = _median_auc(lambda s: metronome_policy(), 'inesc', params, seeds, M)
    gates = {
        'G1_oracle_composer': bool(comp >= 0.90),
        'G2_random_inesc': bool(rand_inesc <= 0.20),
        'G3_forage': bool((forage >= 0.90) and (rand_absent <= 0.20)),
        'G5_metronome': bool(metro <= 0.40),
    }
    gates['ALL'] = bool(all(gates.values()))
    aucs = {'oracle_composer': comp, 'random_inesc': rand_inesc, 'oracle_forage': forage,
            'random_absent': rand_absent, 'metronome': metro}
    return {'gates': gates, 'aucs': aucs}


def calibrate(seeds=PILOT_SEEDS, e0_grid=(6.0, 8.0, 10.0, 12.0, 16.0, 24.0), base=None, M=128):
    """Balaie E0 ; renvoie le PREMIER qui fait passer TOUTES les gates (GATE DUR), sinon un rapport d'echec.
    Les autres params sont figes (spec §1). E0 tamponne la variance precoce du composeur."""
    base = base if base is not None else Params()
    last = None
    for e0 in e0_grid:
        p = replace(base, E0=e0)
        last = check_viability_gates(p, seeds, M)
        if last['gates']['ALL']:
            return {'ok': True, 'E0': e0, 'params': p, 'result': last}
    return {'ok': False, 'params': base, 'last': last}


def _report(res):
    a, g = res.get('result', res.get('last', {})).get('aucs', {}), res.get('result', res.get('last', {})).get('gates', {})
    print("\n=== CRAFT-OR-STARVE — gates de viabilite (Phase A) ===")
    print("  E0 retenu : %s  |  TOUTES gates : %s" % (res.get('E0', 'AUCUN'), res.get('ok')))
    print("  AUC oracle_composer=%.3f  random_inesc=%.3f  metronome=%.3f" %
          (a.get('oracle_composer', float('nan')), a.get('random_inesc', float('nan')), a.get('metronome', float('nan'))))
    print("  AUC oracle_forage=%.3f  random_absent=%.3f" %
          (a.get('oracle_forage', float('nan')), a.get('random_absent', float('nan'))))
    print("  gates : %s" % g)
    print("=== GATE DUR : %s ===" % ("PASSE -> Phase B autorisee" if res.get('ok') else "ECHOUE -> reviser le design AVANT Phase B"))


if __name__ == "__main__":
    _report(calibrate())
```

- [ ] **Step 4: Lancer toute la suite, vérifier le succès**

Run: `cd .claude/worktrees/craft-or-starve && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -q`
Expected: PASS — 11 tests verts (7 de T1 + 4 de T2). Note : `test_world_discriminates_conditioning` fait tourner des rollouts (quelques secondes).

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/craft-or-starve
git add -- tools/craft_or_starve_edr.py tests/sandbox/test_craft_or_starve_edr.py
git commit -m "feat(EDR-200): gates de viabilite + calibration E0 (Phase A T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## GATE DUR (hors tâches TDD — action du contrôleur après T2)

Après la revue finale des 2 tâches, le contrôleur lance la **calibration réelle** :

Run: `cd .claude/worktrees/craft-or-starve && python -m tools.craft_or_starve_edr`
- **Si `GATE DUR : PASSE`** (un `E0` fait passer G1∧G2∧G3∧G5, byte-identique en 2 passes) → le monde EXIGE le conditionnement ; les params sont GELÉS ; la **Phase B** (substrats L0/L1/L2 + `compute_verdict` + runner 3×2×16) devient autorisée → nouveau brainstorm/spec/plan pour la Phase B.
- **Si `GATE DUR : ÉCHOUE`** (aucun `E0`) → **STOP**. Le monde ne discrimine pas proprement (fenêtre de calibration trop étroite) → réviser le design (élargir la grille, ajuster `R/c/c'`, revoir le contrôle absent) AVANT toute Phase B. Consigner l'échec + les AUC obtenus.
