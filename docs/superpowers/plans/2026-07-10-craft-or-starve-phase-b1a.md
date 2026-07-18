# EDR 200 CRAFT-OR-STARVE — Phase B1a (apprenant L0 + gate d'apprentissage) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Établir l'apprenant L0 (cœur récurrent numpy + REINFORCE tronqué) et prouver, via un GATE DUR, qu'un apprenant PEUT apprendre le conditionnement means→ends dans l'écologie CRAFT-OR-STARVE — le point que le fil torch in-world (EDR 172) a montré cassé (cohorte éteinte avant l'horizon d'apprentissage).

**Architecture:** Étend `tools/craft_or_starve_edr.py` (Phase A). Ajoute une boucle d'apprentissage batch (`rollout_learn`) qui, contrairement au `rollout` de référence, propage la récompense (delta d'énergie par sous-pas) à l'apprenant pour qu'il mette à jour ses poids en ligne. L0 = cœur récurrent `H_t = tanh(W_ih·obs + W_hh·H_{t-1} + b_h)` → readout linéaire → softmax, entraîné par REINFORCE **tronqué 1-pas** (H détaché entre sous-pas, PAS de BPTT — EDR 146/147). Pur numpy (gradient manuel). Le gate mesure si L0 apprend à conditionner CONSUME sur l'inventaire (binding_gap > null-métronome) tout en gardant un headroom de survie (G4).

**Tech Stack:** Python, numpy (déterministe `np.random.default_rng`), pytest. Pur numpy en B1a (torch = B1b). AUCUN import de `src/`/`backend_torch.py`.

## Global Constraints

- **Additif strict** : modifier UNIQUEMENT (par APPEND) `tools/craft_or_starve_edr.py` et `tests/sandbox/test_craft_or_starve_edr.py`. Ne pas éditer le code Phase A existant (monde, policies, gates). Aucun import de `src/`/`world_1_stoneage.py`/`backend_torch.py`. **B1a = PUR NUMPY.**
- **Périmètre B1a UNIQUEMENT** : cœur récurrent numpy + `NpReinforceLearner` (L0) + `rollout_learn` + `binding_gap`/`null_metronome_gap` + re-calibration apprenant + GATE DUR. HORS périmètre (B1b/B2) : torch L1/L2, parité G7, `decode_auc`, `compute_verdict`, runner 3×2×16.
- **Constantes gelées héritées Phase A** : `NOOP=0, CRAFT=1, CONSUME=2, FORAGE=3, N_ACTIONS=8, N_NOISE=4, OBS_DIM=6`, `Params(p_mat=0.5, R=8, h=1, c_consume_empty=6, c_craft_nomat=3, c_craft=0.5, f_forage=4, T=800)`. Réutilise `rollout`/`survival_auc`/`_build_obs`/politiques.
- **Nouvelles constantes B1a** : `N_H=12` (dim état caché), `LR=0.02` (REINFORCE), `TEMP=1.0` (softmax). Baseline = moyenne glissante des retours (EMA `decay=0.99`).
- **Crédit L0** : REINFORCE **tronqué 1-pas** — à chaque sous-pas, `advantage = reward − baseline` où `reward` = delta d'énergie du sous-pas ; gradient de `logπ(a)` rétropropagé **uniquement à travers le sous-pas courant** (H_prev détaché) → pas de BPTT. Ascension de gradient `params += LR·advantage·∇logπ`, moyennée sur le batch.
- **binding_gap** = `P(CONSUME|inv=1) − P(CONSUME|inv=0)` mesuré au niveau TICK sur les transitions S2 réelles (poids gelés en éval).
- **GATE DUR apprenant (I1, contre EDR 172)** : L0, entraîné puis évalué, doit sur ≥1 `E0` satisfaire simultanément : (a) **G4 headroom** `survie(L0, absent) ∈ [0.4, 0.85]` ; (b) **apprend le conditionnement** `binding_gap(L0, inesc) − null_metronome_gap ≥ 0.15`. Sinon STOP (le substrat ne peut pas apprendre dans COS → informatif, mais bloque le verdict substrat-vs-crédit de B2).
- **Déterminisme** : `np.random.default_rng(seed)` ; deux entraînements au même seed byte-identiques. Path-scopé.

---

## File Structure

- `tools/craft_or_starve_edr.py` — APPEND : `N_H/LR/TEMP`, `_softmax`, `NpReinforceLearner` (init/act/observe_reward/finish_substep), `rollout_learn`, `evaluate_learner`, `binding_gap`, `null_metronome_gap`, `recalibrate_learner`.
- `tests/sandbox/test_craft_or_starve_edr.py` — APPEND : tests apprenant (déterminisme, apprentissage sur monde-jouet, binding_gap, gate).

Trois tâches : **T1** = cœur récurrent + `NpReinforceLearner` + `rollout_learn` (batch, crédit en ligne) ; **T2** = métriques binding_gap + null-métronome + `evaluate_learner` ; **T3** = re-calibration apprenant + GATE DUR.

---

### Task 1: Cœur récurrent numpy + apprenant L0 (REINFORCE tronqué) + boucle d'apprentissage

**Files:**
- Modify: `tools/craft_or_starve_edr.py` (APPEND)
- Test: `tests/sandbox/test_craft_or_starve_edr.py` (APPEND)

**Interfaces:**
- Consumes : `Params, rollout, _build_obs, N_ACTIONS, N_NOISE, OBS_DIM, NOOP, CRAFT, CONSUME, FORAGE` (Phase A).
- Produces :
  - Constantes `N_H=12, LR=0.02, TEMP=1.0`.
  - `_softmax(logits) -> probs` (stable, axis=-1).
  - `NpReinforceLearner(seed, arm)` : cœur récurrent numpy + REINFORCE 1-pas. Méthodes : `reset_state(M)` (H←0), `act(obs) -> actions[M]` (échantillonne, mémorise le contexte du sous-pas), `update(rewards[M])` (applique le gradient REINFORCE du DERNIER `act`, advantage=reward−baseline EMA).
  - `rollout_learn(learner, arm, params, seed, M, n_episodes) -> learner` (entraîne en ligne : n_episodes vies de T ticks × 2 sous-pas × M agents ; reward = delta d'énergie du sous-pas ; mort absorbante). Retourne le learner entraîné (poids persistants).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_craft_or_starve_edr.py` :

```python
from tools.craft_or_starve_edr import (
    N_H, LR, TEMP, _softmax, NpReinforceLearner, rollout_learn,
)


def test_softmax_stable_and_normalized():
    p = _softmax(np.array([[1000.0, 1000.0, 1000.0, 0, 0, 0, 0, 0]]))
    assert np.isfinite(p).all()
    assert abs(p.sum() - 1.0) < 1e-9
    assert p[0, 0] == pytest.approx(p[0, 1])


def test_learner_shapes_and_determinism():
    l1 = NpReinforceLearner(seed=0, arm="inesc")
    l1.reset_state(4)
    obs = np.zeros((4, 6))
    a = l1.act(obs)
    assert a.shape == (4,) and a.dtype.kind in "iu"
    assert (a >= 0).all() and (a < N_ACTIONS).all()
    # deux rollouts d'apprentissage au meme seed -> poids byte-identiques
    a_learner = rollout_learn(NpReinforceLearner(seed=7, arm="inesc"), "inesc", Params(E0=16.0, T=40), seed=7, M=8, n_episodes=3)
    b_learner = rollout_learn(NpReinforceLearner(seed=7, arm="inesc"), "inesc", Params(E0=16.0, T=40), seed=7, M=8, n_episodes=3)
    assert np.array_equal(a_learner.W_out, b_learner.W_out)
    assert np.array_equal(a_learner.W_hh, b_learner.W_hh)


def test_learner_updates_weights():
    # l'apprentissage DOIT bouger les poids (sinon le gradient est nul = bug)
    learner = NpReinforceLearner(seed=1, arm="inesc")
    W0 = learner.W_out.copy()
    rollout_learn(learner, "inesc", Params(E0=16.0, T=60), seed=1, M=16, n_episodes=5)
    assert not np.allclose(learner.W_out, W0)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "softmax or learner" -q`
Expected: FAIL — `ImportError: cannot import name 'NpReinforceLearner'`.

- [ ] **Step 3: Écrire le cœur + l'apprenant + la boucle**

Ajouter à `tools/craft_or_starve_edr.py` :

```python
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
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "softmax or learner" -q`
Expected: PASS — 3 tests verts.

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/cos-phase-b
git add -- tools/craft_or_starve_edr.py tests/sandbox/test_craft_or_starve_edr.py
git commit -m "feat(EDR-200): apprenant L0 REINFORCE tronque + boucle rollout_learn (Phase B1a T1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Métriques d'évaluation — binding_gap tick-level + null-métronome + `evaluate_learner`

**Files:**
- Modify: `tools/craft_or_starve_edr.py` (APPEND)
- Test: `tests/sandbox/test_craft_or_starve_edr.py` (APPEND)

**Interfaces:**
- Consumes : `NpReinforceLearner, rollout_learn, rollout, survival_auc, Params` (T1/Phase A).
- Produces :
  - `evaluate_learner(learner, arm, params, seed, M) -> dict{"survival","binding_gap","p_c_inv1","p_c_inv0","craft_rate"}` : éval poids GELÉS (pas d'update), mesure survie (AUC médiane-par-agent, dernier quart) + statistiques de conditionnement au niveau TICK sur S2.
  - `null_metronome_gap(params, seed, M) -> float` : binding_gap d'un métronome open-loop (borne null de course l'horloge).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_craft_or_starve_edr.py` :

```python
from tools.craft_or_starve_edr import evaluate_learner, null_metronome_gap


def test_evaluate_learner_contract():
    learner = rollout_learn(NpReinforceLearner(seed=2, arm="inesc"), "inesc", Params(E0=16.0, T=80), seed=2, M=16, n_episodes=8)
    res = evaluate_learner(learner, "inesc", Params(E0=16.0, T=200), seed=99, M=32)
    assert set(res) >= {"survival", "binding_gap", "p_c_inv1", "p_c_inv0", "craft_rate"}
    assert 0.0 <= res["survival"] <= 1.0
    assert -1.0 <= res["binding_gap"] <= 1.0
    # binding_gap == p_c_inv1 - p_c_inv0
    assert res["binding_gap"] == pytest.approx(res["p_c_inv1"] - res["p_c_inv0"], abs=1e-9)


def test_null_metronome_gap_is_low():
    # l'horloge open-loop ne conditionne pas sur inv -> gap ~0 (borne null). Materiau stochastique p_mat=0.5.
    g = null_metronome_gap(Params(E0=16.0, T=200), seed=5, M=64)
    assert abs(g) < 0.15
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "evaluate or null_metron" -q`
Expected: FAIL — `ImportError: cannot import name 'evaluate_learner'`.

- [ ] **Step 3: Écrire les métriques**

Ajouter à `tools/craft_or_starve_edr.py` :

```python
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
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "evaluate or null_metron" -q`
Expected: PASS — 2 tests verts.

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/cos-phase-b
git add -- tools/craft_or_starve_edr.py tests/sandbox/test_craft_or_starve_edr.py
git commit -m "feat(EDR-200): metriques d'eval apprenant (binding_gap tick-level, null-metronome) (Phase B1a T2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Re-calibration apprenant (E0 vs G4 headroom) + GATE DUR

**Files:**
- Modify: `tools/craft_or_starve_edr.py` (APPEND, + bloc `__main__` mis à jour)
- Test: `tests/sandbox/test_craft_or_starve_edr.py` (APPEND)

**Interfaces:**
- Consumes : `NpReinforceLearner, rollout_learn, evaluate_learner, null_metronome_gap, Params, PILOT_SEEDS` (T1/T2/Phase A).
- Produces : `recalibrate_learner(seeds=PILOT_SEEDS, e0_grid=(8.0,12.0,16.0,24.0,32.0), M=32, n_episodes=60) -> dict{"ok","E0_learner","grid","gate"}` : pour chaque E0, entraîne L0 (arm inesc ET absent, seeds appariés), évalue, et teste le GATE DUR apprenant : `G4 headroom (survie absent ∈ [0.4,0.85])` ET `binding_gap(inesc) − null ≥ 0.15`. Retourne le 1er E0 qui passe (ou `ok=False`).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/sandbox/test_craft_or_starve_edr.py` :

```python
from tools.craft_or_starve_edr import recalibrate_learner


def test_recalibrate_learner_contract():
    # on ne prejuge PAS du verdict (GATE DUR du controleur) : on verifie le CONTRAT + la fenetre.
    res = recalibrate_learner(seeds=(1000,), e0_grid=(16.0, 32.0), M=16, n_episodes=10)
    assert "ok" in res and "grid" in res and "gate" in res
    assert len(res["grid"]) == 2
    for row in res["grid"]:
        assert set(row) >= {"E0", "g4_headroom", "binding_adv", "pass"}
    if res["ok"]:
        assert res["E0_learner"] in (16.0, 32.0)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "recalibrate_learner" -q`
Expected: FAIL — `ImportError: cannot import name 'recalibrate_learner'`.

- [ ] **Step 3: Écrire la re-calibration + le GATE DUR**

Ajouter à `tools/craft_or_starve_edr.py` :

```python
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
```

Et remplacer le bloc `__main__` existant par :

```python
if __name__ == "__main__":
    import sys as _s
    if "--learner" in _s.argv:
        _report_learner(recalibrate_learner())
    else:
        _report(calibrate())
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `cd .claude/worktrees/cos-phase-b && python -m pytest tests/sandbox/test_craft_or_starve_edr.py -k "recalibrate_learner" -q`
Expected: PASS — 1 test vert. (Puis la suite complète doit rester verte : `python -m pytest tests/sandbox/test_craft_or_starve_edr.py -q`.)

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/cos-phase-b
git add -- tools/craft_or_starve_edr.py tests/sandbox/test_craft_or_starve_edr.py
git commit -m "feat(EDR-200): re-calibration apprenant + GATE DUR (l'apprenant apprend le conditionnement) (Phase B1a T3)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## GATE DUR (hors tâches TDD — action du contrôleur après revue finale)

Run: `cd .claude/worktrees/cos-phase-b && python -m tools.craft_or_starve_edr --learner` (2 passes byte-identiques).
- **PASSE** (un `E0` donne à L0 : G4 headroom absent ∈ [0.4,0.85] ET binding_adv inesc ≥ 0.15) → un apprenant APPREND le conditionnement dans COS ; `E0_learner` figé comme **borne inférieure** (I1) → **Phase B1b** (torch L1/L2 + parité G7 + decode_auc) autorisée.
- **ÉCHOUE** (aucun `E0`) → **STOP**. L'apprenant n'apprend pas le conditionnement dans COS (headroom insuffisant OU pas de binding). C'est un **résultat en soi** (converge EDR 172 : la viabilité de l'apprenant, pas le substrat, domine) → diagnostic (élargir n_episodes/grid, revoir LR, ou conclure que le verdict substrat-vs-crédit de B2 est prématuré) AVANT toute Phase B1b/B2.
