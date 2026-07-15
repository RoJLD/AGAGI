# EDR 202 KCHAIN — Phase B (apprenant + 2 leviers + courbe de généralité + 2×2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire l'apprenant récurrent numpy `NpChainLearner` + les deux leviers (fenêtre-crédit W, curriculum progressif-K à warm-start) et rendre deux verdicts gelés : la **courbe de généralité** (le levier crédit-horizon×curriculum binde-t-il la composition à K∈{2,3,4,5} → GÉNÉRIQUE, ou casse à K* → COS-SPÉCIFIQUE) et la **décomposition 2×2 @ K=3** (BOTH-NECESSARY / CREDIT-SUFFISANT / CURRICULUM-SUFFISANT).

**Architecture:** APPEND au fichier standalone `tools/kchain_edr.py` (pur numpy) livré en Phase A (#163). L'apprenant réutilise la structure PROUVÉE de COS (`craft_or_starve_edr.py` NpReinforceLearner/NpTickLearner) mais RE-IMPLÉMENTÉE standalone (aucun import de COS). Le levier crédit-horizon = fenêtre-crédit W (retour n-pas bufferisé, généralise le tick-return de COS) ; le levier curriculum = progressif-K où chaque cran fait warm(coût de mis-émission relâché + entropie)→cold(plein) — le bundle de bootstrap prouvé par COS L2. L'évaluation réutilise `_run_chain_logged`/`binding_gap`/`survival_auc` de Phase A.

**Tech Stack:** Python, numpy (déterministe `np.random.default_rng`), pytest.

## Global Constraints

- **Standalone pur numpy** : APPEND à `tools/kchain_edr.py` + `tests/sandbox/test_kchain_edr.py`. AUCUN import de `src/`/`world_1_stoneage.py`/`backend_torch.py`/`craft_or_starve_edr.py`. Additif.
- **Substrat à capacité FIXE** : `N_H=16` cachés CONSTANT sur TOUS les K (disculpe la capacité : 16 cachés ≫ compteur ≤5 états). `LR=0.02`, `TEMP=1.0`, baseline EMA(0.99). REINFORCE, **PAS de BPTT** (H_prev détaché).
- **Levier 1 — fenêtre-crédit W** : `advantage_t = (Σ_{i=0}^{W−1} δ_{t+i}) − baseline`, δ = delta d'énergie du sous-pas ; H_prev traité constant. `W=2` = analogue tick-return COS (aveugle dès K≥3) ; `W_long = 2*K` = fenêtre-chaîne.
- **Levier 2 — curriculum** : `curriculum-on` = progressif-K (K'=2→K), CHAQUE cran = warm(`c_consume_empty=c_warm=0.5` + `entropy_beta=0.01`)→cold(plein, `entropy_beta=0.0`). `curriculum-off` = 1 cran FROID direct au K cible, coût plein, sans warm, budget apparié (`n_episodes = n_stage*(K−1)`).
- **Headroom apprenant (caveat I1)** : `R_K` GELÉ de la Phase A (GATE DUR : `{2:4.0, 3:6.0, 4:8.0, 5:10.0}`) ; `E0_learner` = le PLUS GRAND E0 gardant le monde inescapable (oracle-chain ≥0.90, métronome ≤0.40, random ≤0.20) → runway maximal SANS casser l'inescapabilité.
- **Évaluation** : poids GELÉS, politique GREEDY (argmax), sur le monde PLEIN (`c_consume_empty` plein, `E0=E0_learner`). `composes = binding_gap ≥ 0.5 ET survival_auc ≥ 0.5`.
- **Verdicts gelés pré-enregistrés** ; **déterminisme** (`np.random.default_rng(seed)`, 2 runs même seed byte-identiques). On ne préjuge NI la courbe NI la cellule ouverte.
- **Tree partagé** : chemins ABSOLUS worktree pour les handoffs sous-agent ; commits path-scopés ; pytest/git préfixés `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && …`.

## File Structure

- `tools/kchain_edr.py` — APPEND :
  - T1 : `_softmax`, constantes `N_H/LR/TEMP`, `NpChainLearner`, `rollout_learn_window`, `evaluate_chain`.
  - T2 : `PHASE_A_R`, `calibrate_headroom_K`, `rollout_learn_curriculum_stage`, `rollout_learn_progressive`.
  - T3 : `generality_curve`, `decompose_2x2_chain`, `_report_generality`, `_report_decompose`, `SEEDS_RUN` + branche CLI `--kchain` (MODIFIE le bloc `__main__` de Phase A).
- `tests/sandbox/test_kchain_edr.py` — APPEND : déterminisme apprenant + shapes (T1) ; headroom contrat + progressif atteint K (T2) ; courbe contrat + 2×2 contrat (T3).

Trois tâches : **T1** = apprenant + fenêtre-W + éval ; **T2** = headroom + curriculum ; **T3** = courbe + 2×2 + verdicts + CLI.

---

### Task 1: NpChainLearner + fenêtre-crédit W + évaluation

**Files:**
- Modify: `tools/kchain_edr.py` (APPEND, après les fonctions de Phase A, avant le bloc `if __name__`)
- Test: `tests/sandbox/test_kchain_edr.py` (APPEND)

**Interfaces:**
- Consumes (Phase A) : `Params, replace, np, _build_obs, _run_chain_logged, binding_gap, survival_auc, NOOP, STEP, CONSUME, FORAGE, N_ACTIONS, N_NOISE, OBS_DIM`.
- Produces :
  - `_softmax(x) -> ndarray` (stable, axis=-1).
  - Constantes `N_H=16, LR=0.02, TEMP=1.0`.
  - `NpChainLearner(seed, arm)` : `.reset_state(M)`, `.act(obs)->actions[M]` (échantillonne + bufferise ctx), `.update_window(deltas, alives, W, entropy_beta=0.0)`. Attributs poids `W_ih[N_H,OBS_DIM], W_hh[N_H,N_H], b_h[N_H], W_out[N_ACTIONS,N_H], b_out[N_ACTIONS]`.
  - `rollout_learn_window(learner, arm, K, params, seed, M, n_episodes, W, entropy_beta=0.0) -> learner`.
  - `evaluate_chain(learner, arm, K, params, seed, M) -> {"survival","binding_gap","consume_rate"}`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_kchain_edr.py` :

```python
from tools.kchain_edr import (
    NpChainLearner, rollout_learn_window, evaluate_chain, N_H, N_ACTIONS as NA,
)


def test_chain_learner_determinism():
    # 2 entrainements fenetre-W au meme seed -> poids byte-identiques (determinisme REINFORCE).
    P = Params(E0=32.0, T=60)
    la = rollout_learn_window(NpChainLearner(seed=11, arm='inesc'), 'inesc', 3, P, seed=11, M=8, n_episodes=5, W=6)
    lb = rollout_learn_window(NpChainLearner(seed=11, arm='inesc'), 'inesc', 3, P, seed=11, M=8, n_episodes=5, W=6)
    assert np.array_equal(la.W_out, lb.W_out)
    assert np.array_equal(la.W_ih, lb.W_ih)
    assert np.array_equal(la.W_hh, lb.W_hh)


def test_window_credit_shapes():
    P = Params(E0=32.0, T=60)
    lr = rollout_learn_window(NpChainLearner(seed=1, arm='inesc'), 'inesc', 3, P, seed=1, M=8, n_episodes=3, W=6)
    assert lr.W_out.shape == (NA, N_H)
    ev = evaluate_chain(lr, 'inesc', 3, P, seed=99, M=8)
    assert set(ev) >= {"survival", "binding_gap", "consume_rate"}
    assert -1.0 <= ev["binding_gap"] <= 1.0
    assert 0.0 <= ev["survival"] <= 1.0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "determinism or window_credit" -q`
Expected: FAIL — `ImportError: cannot import name 'NpChainLearner'`.

- [ ] **Step 3: Écrire l'apprenant + la fenêtre-W + l'évaluation**

Ajouter à `tools/kchain_edr.py` (après les fonctions de Phase A, AVANT `if __name__`) :

```python
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
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "determinism or window_credit" -q`
Expected: PASS — 2 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202"
git add -- tools/kchain_edr.py tests/sandbox/test_kchain_edr.py
git commit -m "feat(EDR-202): NpChainLearner + fenetre-credit W + evaluation (Phase B T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Headroom apprenant (I1) + curriculum progressif-K à warm-start

**Files:**
- Modify: `tools/kchain_edr.py` (APPEND, avant `if __name__`)
- Test: `tests/sandbox/test_kchain_edr.py` (APPEND)

**Interfaces:**
- Consumes : T1 (`NpChainLearner, rollout_learn_window`) + Phase A (`check_viability_gates_K, replace, Params, PILOT_SEEDS, np`).
- Produces :
  - `PHASE_A_R = {2: 4.0, 3: 6.0, 4: 8.0, 5: 10.0}` (R_K gelés du GATE DUR de Phase A).
  - `calibrate_headroom_K(K, seeds=PILOT_SEEDS, e0_grid=(16.,24.,32.,48.,64.), M=64) -> {"R_K","E0_learner","grid"}`.
  - `rollout_learn_curriculum_stage(learner, arm, K_stage, params_stage, seed, M, n_warm, n_cold, W, c_warm=0.5, entropy_beta=0.01) -> learner`.
  - `rollout_learn_progressive(learner, arm, K, calib_fn, seed, M, n_stage, W, params_base=None, c_warm=0.5, entropy_beta=0.01) -> learner`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_kchain_edr.py` :

```python
from tools.kchain_edr import (
    calibrate_headroom_K, rollout_learn_progressive, PHASE_A_R,
)


def test_calibrate_headroom_contract():
    # CONTRAT (grille reduite) : structure + R_K = R gele Phase A + E0_learner dans la grille (ou None).
    res = calibrate_headroom_K(2, seeds=(2000,), e0_grid=(16.0, 24.0), M=16)
    assert set(res) >= {"R_K", "E0_learner", "grid"}
    assert res["R_K"] == PHASE_A_R[2]
    assert (res["E0_learner"] in (16.0, 24.0)) or (res["E0_learner"] is None)


def test_progressive_reaches_target_K():
    # CONTRAT : le curriculum progressif 2->3 s'entraine sans erreur et produit un learner evaluable (pas un verdict).
    stub = lambda K: {"R_K": 2.0 * K, "E0_learner": 24.0}
    lr = rollout_learn_progressive(
        NpChainLearner(seed=7, arm='inesc'), 'inesc', 3, stub, seed=7, M=8,
        n_stage=4, W=6, params_base=Params(T=40),
    )
    assert lr.W_out.shape[0] == NA
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "headroom or progressive_reaches" -q`
Expected: FAIL — `ImportError: cannot import name 'calibrate_headroom_K'`.

- [ ] **Step 3: Écrire le headroom + le curriculum**

Ajouter à `tools/kchain_edr.py` (avant `if __name__`) :

```python
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
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "headroom or progressive_reaches" -q`
Expected: PASS — 2 tests verts.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202"
git add -- tools/kchain_edr.py tests/sandbox/test_kchain_edr.py
git commit -m "feat(EDR-202): headroom apprenant (I1) + curriculum progressif-K warm-start (Phase B T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Courbe de généralité + décomposition 2×2 + verdicts + CLI

**Files:**
- Modify: `tools/kchain_edr.py` (APPEND + MODIFIE le bloc `if __name__`)
- Test: `tests/sandbox/test_kchain_edr.py` (APPEND)

**Interfaces:**
- Consumes : T1/T2 (`NpChainLearner, rollout_learn_window, rollout_learn_progressive, evaluate_chain, calibrate_headroom_K`) + Phase A (`replace, Params, np`).
- Produces :
  - `generality_curve(seeds, K_grid=(2,3,4,5), M=64, n_stage=40, calib_fn=None, params_base=None) -> {"grid":[{K,binding,survival,composes}], "verdict"}`.
  - `decompose_2x2_chain(seeds, K=3, M=64, n_stage=40, calib_fn=None, params_base=None) -> {"cells":{...}, "verdict"}`.
  - `_report_generality(res)`, `_report_decompose(res)`, `SEEDS_RUN=(3000,3001,3002)`.
  - CLI : `python -m tools.kchain_edr --kchain` lance courbe + 2×2 ; sans flag = gate de viabilité (Phase A).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_kchain_edr.py` :

```python
from tools.kchain_edr import generality_curve, decompose_2x2_chain

_STUB_CALIB = lambda K: {"R_K": 2.0 * K, "E0_learner": 24.0, "grid": []}
_GEN_VERDICTS = {"GENERIQUE"}   # + "COS-SPECIFIQUE(K*)" (prefixe verifie ci-dessous)
_DEC_VERDICTS = {"BOTH-NECESSARY", "CREDIT-SUFFISANT", "CURRICULUM-SUFFISANT", "INCOHERENT"}


def test_generality_curve_contract():
    res = generality_curve(seeds=(1000,), K_grid=(2, 3), M=8, n_stage=4,
                           calib_fn=_STUB_CALIB, params_base=Params(T=40))
    assert len(res["grid"]) == 2
    for row in res["grid"]:
        assert set(row) >= {"K", "binding", "survival", "composes"}
    assert (res["verdict"] in _GEN_VERDICTS) or res["verdict"].startswith("COS-SPECIFIQUE(")


def test_decompose_2x2_chain_contract():
    res = decompose_2x2_chain(seeds=(1000,), K=3, M=8, n_stage=4,
                              calib_fn=_STUB_CALIB, params_base=Params(T=40))
    assert len(res["cells"]) == 4
    assert res["verdict"] in _DEC_VERDICTS
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "generality_curve or decompose_2x2" -q`
Expected: FAIL — `ImportError: cannot import name 'generality_curve'`.

- [ ] **Step 3: Écrire la courbe + le 2×2 + les verdicts + la CLI**

Ajouter à `tools/kchain_edr.py` (avant `if __name__`) :

```python
# ============================ Phase B — courbe de generalite + decomposition 2x2 + verdicts ============================
# composes = binding_gap >= 0.5 ET survival >= 0.5 (memes seuils gelés que la Phase A / le ladder COS).
_COMPOSE_BIND = 0.5
_COMPOSE_SURV = 0.5
SEEDS_RUN = (3000, 3001, 3002)


def _composes(binding, survival):
    return bool(binding >= _COMPOSE_BIND and survival >= _COMPOSE_SURV)


def _train_full_lever(seed, arm, K, calib_fn, M, n_stage, params_base):
    """Le levier COMPLET : curriculum progressif-K (warm->cold) + fenetre W_long=2K. Retourne le learner entraine."""
    learner = NpChainLearner(seed=seed, arm=arm)
    rollout_learn_progressive(learner, arm, K, calib_fn, seed=seed, M=M, n_stage=n_stage, W=2 * K,
                              params_base=params_base)
    return learner


def generality_curve(seeds, K_grid=(2, 3, 4, 5), M=64, n_stage=40, calib_fn=None, params_base=None):
    """Pour chaque K : levier COMPLET (curriculum progressif + W_long=2K), eval GELEE. composes = bind>=0.5 & surv>=0.5.
    Verdict GELE : 'GENERIQUE' si composes a TOUS les K ; 'COS-SPECIFIQUE(K*)' si la 1re rupture est a K* (courbe rendue)."""
    calib_fn = calib_fn or calibrate_headroom_K
    P0 = params_base if params_base is not None else Params()
    grid, first_break = [], None
    for K in K_grid:
        cal = calib_fn(K)
        e0 = cal["E0_learner"] if cal["E0_learner"] is not None else P0.E0
        Peval = replace(P0, R=cal["R_K"], E0=e0)
        binds, survs = [], []
        for s in seeds:
            learner = _train_full_lever(int(s), 'inesc', K, calib_fn, M, n_stage, P0)
            ev = evaluate_chain(learner, 'inesc', K, Peval, seed=int(s) + 5000, M=M)
            binds.append(ev["binding_gap"]); survs.append(ev["survival"])
        b, sv = float(np.median(binds)), float(np.median(survs))
        comp = _composes(b, sv)
        grid.append({"K": K, "binding": b, "survival": sv, "composes": comp})
        if not comp and first_break is None:
            first_break = K
    verdict = "GENERIQUE" if first_break is None else "COS-SPECIFIQUE(%d)" % first_break
    return {"grid": grid, "verdict": verdict}


def _train_cell_chain(W_mode, curriculum, K, calib_fn, seed, M, n_stage, params_base):
    """Une cellule du 2x2. W = 2 (court) ou 2K (long). curriculum=True -> progressif-K warm->cold ;
    curriculum=False -> 1 cran FROID direct a K, cout plein, budget apparie (n_stage*(K-1) episodes)."""
    W = 2 if W_mode == 'short' else 2 * K
    cal = calib_fn(K)
    e0 = cal["E0_learner"] if cal["E0_learner"] is not None else params_base.E0
    P = replace(params_base, R=cal["R_K"], E0=e0)
    learner = NpChainLearner(seed=seed, arm='inesc')
    if curriculum:
        rollout_learn_progressive(learner, 'inesc', K, calib_fn, seed=seed, M=M, n_stage=n_stage, W=W,
                                  params_base=params_base)
    else:
        rollout_learn_window(learner, 'inesc', K, P, seed=seed, M=M, n_episodes=n_stage * (K - 1), W=W,
                             entropy_beta=0.0)
    ev = evaluate_chain(learner, 'inesc', K, P, seed=seed + 5000, M=M)
    return {"binding": ev["binding_gap"], "survival": ev["survival"]}


def decompose_2x2_chain(seeds, K=3, M=64, n_stage=40, calib_fn=None, params_base=None):
    """2x2 fenetre{short=2, long=2K} x curriculum{off, on} (bras inesc). Verdict GELE (arbre gate sur (long,on),
    sinon INCOHERENT) : CURRICULUM-SUFFISANT si (short,on) compose ; CREDIT-SUFFISANT si (long,off) compose ;
    sinon BOTH-NECESSARY. On ne prejuge PAS (replique EDR 201 a K=3)."""
    calib_fn = calib_fn or calibrate_headroom_K
    P0 = params_base if params_base is not None else Params()
    cells = {}
    for W_mode in ('short', 'long'):
        for curr in (False, True):
            binds, survs = [], []
            for s in seeds:
                c = _train_cell_chain(W_mode, curr, K, calib_fn, int(s), M, n_stage, P0)
                binds.append(c["binding"]); survs.append(c["survival"])
            b, sv = float(np.median(binds)), float(np.median(survs))
            cells[(W_mode, curr)] = {"binding": b, "survival": sv, "composes": _composes(b, sv)}
    long_on = cells[('long', True)]["composes"]
    short_on = cells[('short', True)]["composes"]
    long_off = cells[('long', False)]["composes"]
    if not long_on:
        verdict = "INCOHERENT"
    elif short_on:
        verdict = "CURRICULUM-SUFFISANT"
    elif long_off:
        verdict = "CREDIT-SUFFISANT"
    else:
        verdict = "BOTH-NECESSARY"
    return {"cells": cells, "verdict": verdict}


def _report_generality(res):
    print("\n=== EDR 202 KCHAIN — courbe de generalite (levier complet : curriculum + W_long) ===")
    for row in res["grid"]:
        print("    K=%d  binding=%+.3f  survie=%.3f  compose=%s"
              % (row["K"], row["binding"], row["survival"], row["composes"]))
    print("=== VERDICT COURBE : %s ===" % res["verdict"])
    print("    (GENERIQUE = le levier credit-horizon x curriculum binde la composition a toute profondeur ;")
    print("     COS-SPECIFIQUE(K*) = la loi a une limite de profondeur a K*)")


def _report_decompose(res):
    print("\n=== EDR 202 KCHAIN — decomposition 2x2 fenetre x curriculum (K=3, bras inesc) ===")
    label = {('short', False): '(W2,   off )', ('short', True): '(W2,   CURR)',
             ('long', False): '(Wlong,off )', ('long', True): '(Wlong,CURR)'}
    for key in (('short', False), ('short', True), ('long', False), ('long', True)):
        c = res["cells"][key]
        print("    %s  binding=%+.3f  survie=%.3f  compose=%s"
              % (label[key], c["binding"], c["survival"], c["composes"]))
    print("=== VERDICT 2x2 : %s ===" % res["verdict"])
```

Et MODIFIER le bloc `if __name__` de Phase A pour router selon `--kchain` :

```python
if __name__ == "__main__":
    import sys
    if "--kchain" in sys.argv:
        _report_generality(generality_curve(SEEDS_RUN))
        _report_decompose(decompose_2x2_chain(SEEDS_RUN))
    else:
        _report_viability(viability_gate_all_K())
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m pytest tests/sandbox/test_kchain_edr.py -k "generality_curve or decompose_2x2" -q`
Expected: PASS — 2 tests verts. (Puis la suite complète : `python -m pytest tests/sandbox/test_kchain_edr.py -q` → 12 verts.)

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202"
git add -- tools/kchain_edr.py tests/sandbox/test_kchain_edr.py
git commit -m "feat(EDR-202): courbe de generalite + decomposition 2x2 + verdicts + CLI --kchain (Phase B T3)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Run décisif (contrôleur, hors tâches TDD — après revue finale)

Run (arrière-plan, LOURD ~dizaines de min → ~1-2 h) : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/kchain-edr202" && python -m tools.kchain_edr --kchain`. Déterminisme prouvé par tests (1 pass suffit ; confirmer par une 2ᵉ passe si le temps le permet).

- **Courbe GÉNÉRIQUE** (le levier binde à K=2..5) → la loi crédit-horizon×curriculum est le débloqueur GÉNÉRIQUE du bootstrap de composition, pas un artefact de K=2. **COS-SPÉCIFIQUE(K\*)** → la loi a une limite de profondeur (rapporter K\* + la courbe).
- **2×2 @ K=3 = BOTH-NECESSARY** attendu (réplique EDR 201 en profondeur) ; CURRICULUM-SUFFISANT / CREDIT-SUFFISANT raffineraient.
- **Signaux à investiguer AVANT consolidation** : un `INCOHERENT` (la cellule levier-complet ne compose pas → tuning n_stage/M/headroom ou trap I1 non résolu) ; un `E0_learner=None` à un K (aucun E0 inescapable dans la grille → élargir e0_grid) ; W=2 (short) qui composerait à K≥3 (le crédit-horizon ne serait PAS le levier → réexaminer).
- Si le levier complet ne binde à AUCUN K (courbe plate négative) : c'est le trap I1/headroom → diagnostiquer (augmenter n_stage warm, vérifier `calibrate_headroom_K`, cf. COS L2) AVANT de conclure.
