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


# ============================ Phase B — apprenant recurrent + fenetre-credit W ============================
# Apprenant RE-IMPLEMENTE standalone (structure prouvee de COS craft_or_starve_edr NpReinforceLearner/NpTickLearner,
# AUCUN import). Le levier credit-horizon = fenetre-credit W : advantage_t = (somme des deltas d'energie sur les W
# sous-pas suivants) - baseline. W=2 = analogue tick-return COS (aveugle des K>=3) ; W_long=2K couvre la chaine.
# REINFORCE, PAS de BPTT (H_prev traite constant). N_H=16 FIXE sur tous les K -> disculpe la capacite.

N_H = 16
LR = 0.02
TEMP = 1.0


def _softmax(x):
    x = x - x.max(axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


class NpChainLearner:
    """Coeur recurrent H_t = tanh(W_ih·obs + W_hh·H_{t-1} + b_h) -> readout lineaire -> softmax(/TEMP).
    Bufferise les ctx d'un episode (act) ; credite chaque sous-pas t d'un retour fenetre-W (update_window) :
    advantage_t = (Σ_{i<W} δ_{t+i}) - baseline(EMA). H_prev traite constant -> PAS de BPTT. Poids persistants."""

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
        self._buf = []   # liste de (obs, H_prev, H_new, probs, actions) de l'episode courant

    def reset_state(self, M):
        self._H = np.zeros((M, N_H), dtype=np.float64)
        self._buf = []

    def act(self, obs):
        H_prev = self._H
        z = obs @ self.W_ih.T + H_prev @ self.W_hh.T + self.b_h
        H_new = np.tanh(z)
        logits = H_new @ self.W_out.T + self.b_out
        probs = _softmax(logits / TEMP)
        u = self._rng.random(probs.shape[0])
        actions = (probs.cumsum(axis=1) > u[:, None]).argmax(axis=1)
        self._H = H_new
        self._buf.append((obs, H_prev, H_new, probs, actions))
        return actions

    def update_window(self, deltas, alives, W, entropy_beta=0.0):
        """REINFORCE a retour fenetre-W sur les ctx bufferises. deltas/alives : listes de T tableaux (M,).
        Pour chaque sous-pas t : G_t = Σ_{i=0}^{W-1} δ_{t+i} (tronque a T) ; advantage = (G_t - baseline)·alive_t.
        Gradient applique a ctx_t (H_prev constant -> pas de BPTT). Bonus d'entropie optionnel (/TEMP, aligne 201)."""
        D = np.asarray(deltas, dtype=np.float64)   # [T, M]
        A = np.asarray(alives, dtype=np.float64)   # [T, M]
        T = D.shape[0]
        for t in range(T):
            hi = min(t + W, T)
            G = D[t:hi].sum(axis=0)                 # (M,) retour fenetre-W
            m = A[t]
            n = max(m.sum(), 1.0)
            self._baseline = 0.99 * self._baseline + 0.01 * float((G * m).sum() / n)
            adv = (G - self._baseline) * m
            obs, H_prev, H_new, probs, actions = self._buf[t]
            Mn = obs.shape[0]
            onehot = np.zeros_like(probs)
            onehot[np.arange(Mn), actions] = 1.0
            dlogits = (onehot - probs) * adv[:, None] / TEMP
            if entropy_beta:
                logp = np.log(probs + 1e-12)
                Hent = -(probs * logp).sum(axis=1, keepdims=True)
                dlogits = dlogits + entropy_beta * (-probs * (logp + Hent)) / TEMP * m[:, None]
            self.W_out += LR * (dlogits.T @ H_new) / n
            self.b_out += LR * dlogits.sum(axis=0) / n
            dz = (dlogits @ self.W_out) * (1.0 - H_new ** 2)
            self.W_ih += LR * (dz.T @ obs) / n
            self.W_hh += LR * (dz.T @ H_prev) / n
            self.b_h += LR * dz.sum(axis=0) / n
        self._buf = []


def rollout_learn_window(learner, arm, K, params, seed, M, n_episodes, W, entropy_beta=0.0):
    """Entraine `learner` en ligne : n_episodes vies (T sous-pas x M agents), reward = delta d'energie du sous-pas,
    mort ABSORBANTE. La dynamique du monde DOIT rester identique a rollout_chain (Phase A) : garder en synchro.
    Bufferise l'episode puis update_window (retour W). Retourne le learner entraine."""
    rng = np.random.default_rng(seed)
    P = params
    for _ in range(n_episodes):
        learner.reset_state(M)
        E = np.full(M, P.E0, dtype=np.float64)
        prog = np.zeros(M, dtype=np.int64)
        alive = np.ones(M, dtype=bool)
        pending = np.zeros(M, dtype=np.float64)
        deltas, alives = [], []
        for t in range(P.T):
            mat = (rng.random(M) < P.p_mat).astype(np.float64)
            obs = _build_obs(mat, rng.standard_normal((M, N_NOISE)))
            a = learner.act(obs)
            E_before = E.copy()
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
            deltas.append(np.where(alive, E - E_before, 0.0))
            alives.append(alive.astype(np.float64))
            alive = alive & (E > 0.0)
        learner.update_window(deltas, alives, W, entropy_beta)
    return learner


def evaluate_chain(learner, arm, K, params, seed, M):
    """Eval poids GELES + politique GREEDY (argmax, deterministe). Reutilise _run_chain_logged (Phase A) :
    survie (survival_auc) + binding_gap (P(CONSUME|prog==K-1)-P(CONSUME|prog<K-1)) + consume_rate.
    Un learner mort n'a pas de sous-pas vivants -> binding_gap=0 par defaut masque-vide = 'ne compose pas' (correct)."""
    def act(obs, mem, prog):
        H = mem if mem is not None else np.zeros((obs.shape[0], N_H), dtype=np.float64)
        z = obs @ learner.W_ih.T + H @ learner.W_hh.T + learner.b_h
        Hn = np.tanh(z)
        logits = Hn @ learner.W_out.T + learner.b_out
        a = _softmax(logits / TEMP).argmax(axis=1)
        return a, Hn
    am, s2 = _run_chain_logged(act, arm, K, params, seed, M)
    prog_log, cons_log, _al = s2
    return {"survival": survival_auc(am), "binding_gap": binding_gap((*s2, K)),
            "consume_rate": float(cons_log.mean())}


# ============================ Phase B — headroom apprenant (I1) + curriculum progressif-K ============================
# R_K GELE du GATE DUR de Phase A (oracle-viable, R_K≈2K). E0_learner = le PLUS GRAND E0 gardant le monde inescapable
# (random meurt) -> runway maximal pour l'apprenant SANS casser l'inescapabilite (repond au caveat I1 de COS).

PHASE_A_R = {2: 4.0, 3: 6.0, 4: 8.0, 5: 10.0}


def calibrate_headroom_K(K, seeds=PILOT_SEEDS, e0_grid=(16.0, 24.0, 32.0, 48.0, 64.0), M=64):
    """R_K gele (Phase A) ; balaie e0_grid ASCENDANT et retient le PLUS GRAND E0 gardant le monde inescapable
    (G1 oracle-chain >=0.90, G2 metronome <=0.40, G3 random <=0.20). Runway apprenant maximal sans casser
    l'inescapabilite (I1). Renvoie E0_learner=None si aucun E0 de la grille n'est inescapable (a diagnostiquer)."""
    R = PHASE_A_R[K]
    grid, best = [], None
    for e0 in e0_grid:
        g = check_viability_gates_K(K, replace(Params(), R=R, E0=e0), seeds, M)['gates']
        inesc_ok = bool(g['G1_oracle_chain'] and g['G2_metronome'] and g['G3_random_inesc'])
        grid.append({"E0": e0, "inescapable": inesc_ok})
        if inesc_ok:
            best = e0   # ascendant -> garde le plus grand E0 encore inescapable
    return {"R_K": R, "E0_learner": best, "grid": grid}


def rollout_learn_curriculum_stage(learner, arm, K_stage, params_stage, seed, M, n_warm, n_cold, W,
                                   c_warm=0.5, entropy_beta=0.01):
    """Un cran du curriculum : phase WARM (c_consume_empty=c_warm : explorer CONSUME est sur + bonus entropie) puis
    phase COLD (params PLEINS, sans entropie). Bootstrap du binding sequentiel que le cout de mis-emission plein
    empeche d'amorcer a froid (recette L2 de COS, generalisee a la profondeur). Poids persistants."""
    rollout_learn_window(learner, arm, K_stage, replace(params_stage, c_consume_empty=c_warm),
                         seed=seed, M=M, n_episodes=n_warm, W=W, entropy_beta=entropy_beta)
    rollout_learn_window(learner, arm, K_stage, params_stage,
                         seed=seed + 100, M=M, n_episodes=n_cold, W=W, entropy_beta=0.0)
    return learner


def rollout_learn_progressive(learner, arm, K, calib_fn, seed, M, n_stage, W, params_base=None,
                              c_warm=0.5, entropy_beta=0.01):
    """Curriculum progressif-K : entraine successivement sur les mondes K'=2,3,...,K (MEME learner, poids persistants),
    chaque cran = warm->cold (rollout_learn_curriculum_stage) au (R_{K'}, E0_{K'}) de calib_fn. n_stage episodes/cran
    (moitie warm, moitie cold). W FIXE (le levier) sur tous les crans. params_base fournit les params geles (T, couts)."""
    P0 = params_base if params_base is not None else Params()
    for i, Kp in enumerate(range(2, K + 1)):
        cal = calib_fn(Kp)
        e0 = cal["E0_learner"] if cal["E0_learner"] is not None else P0.E0
        P = replace(P0, R=cal["R_K"], E0=e0)
        n_warm = n_stage // 2
        n_cold = n_stage - n_warm
        rollout_learn_curriculum_stage(learner, arm, Kp, P, seed=seed + 1000 * i, M=M,
                                       n_warm=n_warm, n_cold=n_cold, W=W, c_warm=c_warm, entropy_beta=entropy_beta)
    return learner


if __name__ == "__main__":
    _report_viability(viability_gate_all_K())
