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
    """Balaie TOUT le grid E0 et renvoie la fenetre viable + le E0 minimal viable (BORNE INFERIEURE).
    Autres params figes (spec §1). ATTENTION : le E0 minimal viable NE DOIT PAS etre gele pour la Phase B
    (un apprenant quasi-aleatoire mourrait avant d'apprendre) ; la Phase B doit RE-CALIBRER E0 contre G4
    (headroom apprenant) avant les seeds confirmatoires."""
    base = base if base is not None else Params()
    grid = []
    ok_e0, ok_res, last = None, None, None
    for e0 in e0_grid:
        last = check_viability_gates(replace(base, E0=e0), seeds, M)
        grid.append({'E0': e0, 'all': bool(last['gates']['ALL']),
                     'composer': last['aucs']['oracle_composer'], 'metronome': last['aucs']['metronome']})
        if last['gates']['ALL'] and ok_e0 is None:
            ok_e0, ok_res = e0, last
    ok = ok_e0 is not None
    return {'ok': ok, 'grid': grid, 'E0_min_viable': ok_e0,
            'params': replace(base, E0=ok_e0) if ok else base,
            'result': ok_res, 'last': last}


def _report(res):
    full = res.get('result') or res.get('last') or {}
    a, g = full.get('aucs', {}), full.get('gates', {})
    print("\n=== CRAFT-OR-STARVE — gates de viabilite (Phase A pilote) ===")
    print("  E0 MINIMAL VIABLE : %s  (BORNE INFERIEURE — NE PAS geler ; Phase B recalibre E0 contre G4 headroom)"
          % res.get('E0_min_viable'))
    print("  TOUTES gates (au E0 minimal) : %s" % res.get('ok'))
    print("  fenetre viable (grid E0) :")
    for row in res.get('grid', []):
        print("    E0=%5.1f  ALL=%s  composer=%.3f  metronome=%.3f"
              % (row['E0'], row['all'], row['composer'], row['metronome']))
    print("  AUC (au E0 minimal) : composer=%.3f random_inesc=%.3f metronome=%.3f forage=%.3f random_absent=%.3f"
          % (a.get('oracle_composer', float('nan')), a.get('random_inesc', float('nan')),
             a.get('metronome', float('nan')), a.get('oracle_forage', float('nan')), a.get('random_absent', float('nan'))))
    print("  gates (au E0 minimal) : %s" % g)
    print("=== GATE DUR : %s ===" % ("PASSE -> Phase B autorisee (RE-CALIBRER E0 contre G4 AVANT seeds confirmatoires)"
                                     if res.get('ok') else "ECHOUE -> reviser le design AVANT Phase B"))


if __name__ == "__main__":
    _report(calibrate())
