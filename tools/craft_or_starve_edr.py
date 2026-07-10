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


# ============================ Phase B1a : apprenant L0 (REINFORCE tronque, pur numpy) ============================
N_H = 12
LR = 0.02
TEMP = 1.0


def _softmax(logits):
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class NpReinforceLearner:
    """Cœur recurrent H_t = tanh(W_ih·obs + W_hh·H_{t-1} + b_h) -> readout lineaire -> softmax(/TEMP).
    Credit = REINFORCE TRONQUE 1-pas : le gradient de logπ(a) ne remonte QUE le sous-pas courant (H_prev detache,
    PAS de BPTT). advantage = reward - baseline (EMA). Poids persistants (apprentissage en ligne). Pur numpy."""

    def __init__(self, seed, arm):
        rng = np.random.default_rng((int(seed) ^ 0x51ED270B) & 0xFFFFFFFF)
        s = 1.0 / np.sqrt(N_H)
        self.W_ih = (rng.standard_normal((N_H, OBS_DIM)) * s).astype(np.float64)
        self.W_hh = (rng.standard_normal((N_H, N_H)) * s).astype(np.float64)
        self.b_h = np.zeros(N_H, dtype=np.float64)
        self.W_out = (rng.standard_normal((N_ACTIONS, N_H)) * s).astype(np.float64)
        self.b_out = np.zeros(N_ACTIONS, dtype=np.float64)
        self.arm = arm
        self._rng = np.random.default_rng((int(seed) ^ 0x2C1B3A9F) & 0xFFFFFFFF)  # echantillonnage d'actions
        self._baseline = 0.0
        self._H = None
        self._ctx = None   # (obs, H_prev, H_new, probs, actions) du dernier act

    def reset_state(self, M):
        self._H = np.zeros((M, N_H), dtype=np.float64)

    def act(self, obs):
        H_prev = self._H
        z = obs @ self.W_ih.T + H_prev @ self.W_hh.T + self.b_h
        H_new = np.tanh(z)
        logits = H_new @ self.W_out.T + self.b_out
        probs = _softmax(logits / TEMP)
        u = self._rng.random(probs.shape[0])
        actions = (probs.cumsum(axis=1) > u[:, None]).argmax(axis=1)
        self._H = H_new
        self._ctx = (obs, H_prev, H_new, probs, actions)
        return actions

    def update(self, rewards, alive):
        """REINFORCE 1-pas sur le DERNIER act. advantage = reward - baseline (EMA), masque les morts."""
        obs, H_prev, H_new, probs, actions = self._ctx
        M = obs.shape[0]
        r = np.asarray(rewards, dtype=np.float64)
        m = np.asarray(alive, dtype=np.float64)
        n = max(m.sum(), 1.0)
        self._baseline = 0.99 * self._baseline + 0.01 * float((r * m).sum() / n)
        adv = (r - self._baseline) * m                                    # (M,) morts -> 0
        onehot = np.zeros_like(probs)
        onehot[np.arange(M), actions] = 1.0
        dlogits = (onehot - probs) * adv[:, None] / TEMP                  # d(adv·logπ(a))/dlogits
        # backprop tronque (H_prev traite comme constante -> pas de BPTT)
        self.W_out += LR * (dlogits.T @ H_new) / n
        self.b_out += LR * dlogits.sum(axis=0) / n
        dH = dlogits @ self.W_out                                         # (M, N_H)
        dz = dH * (1.0 - H_new ** 2)
        self.W_ih += LR * (dz.T @ obs) / n
        self.W_hh += LR * (dz.T @ H_prev) / n
        self.b_h += LR * dz.sum(axis=0) / n


def rollout_learn(learner, arm, params, seed, M, n_episodes):
    """Entraine `learner` en ligne : n_episodes vies (T ticks x 2 sous-pas x M agents), reward = delta d'energie
    du sous-pas, mort ABSORBANTE. Meme dynamique de monde que `rollout` (Phase A). Retourne le learner entraine."""
    rng = np.random.default_rng(seed)
    P = params
    for _ in range(n_episodes):
        learner.reset_state(M)
        E = np.full(M, P.E0, dtype=np.float64)
        inv = np.zeros(M, dtype=bool)
        alive = np.ones(M, dtype=bool)
        pending = np.zeros(M, dtype=np.float64)
        for t in range(P.T):
            # --- S1 ---
            mat = (rng.random(M) < P.p_mat).astype(np.float64)
            obs1 = _build_obs(mat, 0, rng.standard_normal((M, N_NOISE)))
            a1 = learner.act(obs1)
            E_before = E.copy()
            matb = mat > 0.5
            if arm == "inesc":
                crafted = alive & (a1 == CRAFT)
                inv = np.where(crafted & matb, True, inv)
                E = E - np.where(crafted & matb, P.c_craft, 0.0) - np.where(crafted & ~matb, P.c_craft_nomat, 0.0)
            else:
                foraged = alive & (a1 == FORAGE)
                pending = np.where(foraged, P.f_forage, 0.0)
            E = E - np.where(alive, P.h, 0.0)
            learner.update(np.where(alive, E - E_before, 0.0), alive)
            # --- S2 ---
            obs2 = _build_obs(np.zeros(M), 1, rng.standard_normal((M, N_NOISE)))
            a2 = learner.act(obs2)
            E_before = E.copy()
            if arm == "inesc":
                consume = alive & (a2 == CONSUME)
                got = consume & inv
                E = E + np.where(got, P.R, 0.0) - np.where(consume & ~inv, P.c_consume_empty, 0.0)
                inv = np.where(got, False, inv)
            else:
                E = E + np.where(alive, pending, 0.0)
                pending = np.zeros(M, dtype=np.float64)
            E = E - np.where(alive, P.h, 0.0)
            learner.update(np.where(alive, E - E_before, 0.0), alive)
            alive = alive & (E > 0.0)
    return learner


# ============================ Phase B1a Task 2 : metriques d'evaluation (poids GELES) ============================

def _run_frozen(policy_act, arm, params, seed, M):
    """Deroule M agents avec une politique GELEE `policy_act(obs, H_state)->(actions, H_state)`, en collectant
    au niveau TICK (S2) : (inv_avant_consume, action==CONSUME). Retourne (alive_matrix[M,T], list de (invb, cons))."""
    rng = np.random.default_rng(seed)
    P = params
    E = np.full(M, P.E0, dtype=np.float64)
    inv = np.zeros(M, dtype=bool)
    alive = np.ones(M, dtype=bool)
    pending = np.zeros(M, dtype=np.float64)
    Hstate = [None]
    alive_matrix = np.zeros((M, P.T), dtype=bool)
    s2_inv, s2_cons, s2_alive = [], [], []
    for t in range(P.T):
        mat = (rng.random(M) < P.p_mat).astype(np.float64)
        obs1 = _build_obs(mat, 0, rng.standard_normal((M, N_NOISE)))
        a1, Hstate[0] = policy_act(obs1, Hstate[0])
        matb = mat > 0.5
        if arm == "inesc":
            crafted = alive & (a1 == CRAFT)
            inv = np.where(crafted & matb, True, inv)
            E = E - np.where(crafted & matb, P.c_craft, 0.0) - np.where(crafted & ~matb, P.c_craft_nomat, 0.0)
        else:
            pending = np.where(alive & (a1 == FORAGE), P.f_forage, 0.0)
        E = E - np.where(alive, P.h, 0.0)
        obs2 = _build_obs(np.zeros(M), 1, rng.standard_normal((M, N_NOISE)))
        a2, Hstate[0] = policy_act(obs2, Hstate[0])
        inv_at_s2 = inv.copy()
        if arm == "inesc":
            consume = alive & (a2 == CONSUME)
            got = consume & inv
            E = E + np.where(got, P.R, 0.0) - np.where(consume & ~inv, P.c_consume_empty, 0.0)
            inv = np.where(got, False, inv)
        else:
            E = E + np.where(alive, pending, 0.0)
            pending = np.zeros(M, dtype=np.float64)
        E = E - np.where(alive, P.h, 0.0)
        s2_inv.append(inv_at_s2.copy()); s2_cons.append(a2 == CONSUME); s2_alive.append(alive.copy())
        alive = alive & (E > 0.0)
        alive_matrix[:, t] = alive
    return alive_matrix, (np.array(s2_inv), np.array(s2_cons), np.array(s2_alive))


def _binding_from_log(s2):
    """P(CONSUME|inv=1) - P(CONSUME|inv=0) sur les transitions S2 des agents VIVANTS, dernier quart."""
    inv, cons, al = s2                      # chacun [T, M]
    T = inv.shape[0]
    q = (3 * T) // 4
    inv, cons, al = inv[q:], cons[q:], al[q:]
    m1 = al & inv
    m0 = al & ~inv
    p1 = float(cons[m1].mean()) if m1.any() else 0.0
    p0 = float(cons[m0].mean()) if m0.any() else 0.0
    craft_rate = float(inv.mean())
    return p1, p0, craft_rate


def evaluate_learner(learner, arm, params, seed, M):
    """Eval poids GELES (pas d'update) : survie (AUC mediane-par-agent) + conditionnement TICK-level."""
    def act(obs, H):
        if H is None:
            H = np.zeros((obs.shape[0], N_H), dtype=np.float64)
        z = obs @ learner.W_ih.T + H @ learner.W_hh.T + learner.b_h
        Hn = np.tanh(z)
        logits = Hn @ learner.W_out.T + learner.b_out
        # eval = poids GELES + politique GREEDY (argmax) -> deterministe, pas de rng d'echantillonnage
        a = _softmax(logits / TEMP).argmax(axis=1)
        return a, Hn
    am, s2 = _run_frozen(act, arm, params, seed, M)
    p1, p0, craft_rate = _binding_from_log(s2)
    return {"survival": survival_auc(am), "binding_gap": p1 - p0,
            "p_c_inv1": p1, "p_c_inv0": p0, "craft_rate": craft_rate}


def null_metronome_gap(params, seed, M):
    """binding_gap d'un metronome open-loop (CRAFT en S1, CONSUME en S2) -> borne null (ne lit pas inv)."""
    def act(obs, H):
        phase = int(round(float(obs[0, 1])))
        a = np.full(obs.shape[0], CRAFT if phase == 0 else CONSUME, dtype=int)
        return a, H
    _, s2 = _run_frozen(act, "inesc", params, seed, M)
    p1, p0, _ = _binding_from_log(s2)
    return p1 - p0


def recalibrate_learner(seeds=PILOT_SEEDS, e0_grid=(8.0, 12.0, 16.0, 24.0, 32.0), M=32, n_episodes=60):
    """GATE DUR apprenant (I1, contre EDR 172 : cohorte eteinte avant l'horizon d'apprentissage).
    Pour chaque E0 : entraine L0 (arm inesc ET absent, seeds appariés), evalue, teste :
    (a) G4 headroom : mediane_seeds survie(L0, absent) dans [0.4, 0.85] ;
    (b) apprend : mediane_seeds [binding_gap(L0, inesc) - null_metronome_gap] >= 0.15.
    Renvoie le 1er E0 qui passe les DEUX. Balaie tout le grid (fenetre auditable)."""
    grid = []
    ok_e0 = None
    for e0 in e0_grid:
        P = replace(Params(), E0=e0)
        head, adv = [], []
        for s in seeds:
            li = rollout_learn(NpReinforceLearner(seed=int(s), arm="inesc"), "inesc", P, seed=int(s), M=M, n_episodes=n_episodes)
            la = rollout_learn(NpReinforceLearner(seed=int(s), arm="absent"), "absent", P, seed=int(s), M=M, n_episodes=n_episodes)
            ei = evaluate_learner(li, "inesc", P, seed=int(s) + 5000, M=M)
            ea = evaluate_learner(la, "absent", P, seed=int(s) + 5000, M=M)
            ng = null_metronome_gap(P, seed=int(s) + 5000, M=M)
            head.append(ea["survival"])
            adv.append(ei["binding_gap"] - ng)
        g4 = float(np.median(head))
        badv = float(np.median(adv))
        passed = bool((0.4 <= g4 <= 0.85) and (badv >= 0.15))
        grid.append({"E0": e0, "g4_headroom": g4, "binding_adv": badv, "pass": passed})
        if passed and ok_e0 is None:
            ok_e0 = e0
    return {"ok": ok_e0 is not None, "E0_learner": ok_e0, "grid": grid,
            "gate": "PASSE" if ok_e0 is not None else "ECHOUE"}


def _report_learner(res):
    print("\n=== CRAFT-OR-STARVE — GATE DUR apprenant (Phase B1a) ===")
    print("  E0 apprenant retenu : %s  |  gate : %s" % (res.get("E0_learner"), res.get("gate")))
    print("  fenetre (E0 -> G4 headroom absent / binding_adv inesc / pass) :")
    for row in res.get("grid", []):
        print("    E0=%5.1f  headroom=%.3f  binding_adv=%+.3f  pass=%s"
              % (row["E0"], row["g4_headroom"], row["binding_adv"], row["pass"]))
    print("=== %s ===" % ("PASSE -> Phase B1b (torch L1/L2 + parite) autorisee, E0_learner fige (borne inf, cf I1)"
                          if res.get("ok") else "ECHOUE -> l'apprenant n'apprend pas le conditionnement dans COS ; STOP + diagnostic (converge EDR 172)"))


if __name__ == "__main__":
    import sys as _s
    if "--learner" in _s.argv:
        _report_learner(recalibrate_learner())
    else:
        _report(calibrate())
