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
