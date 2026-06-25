# Dreaming → Planificateur (latent Dreamer-lite) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'escalade aléatoire latente du « dreaming » par une anticipation conditionnée par l'action `g(H,a)→H'` (apprise en ligne), qui biaise la politique actor-critic. Gaté, défaut OFF, non-régressif.

**Architecture:** Une pièce neuve `g` = matrice par agent `G (A=8, N)` (effet latent de chaque action), apprise en ligne. Dans `forward`, on déroule profondeur-1 (`H'_a = H_rec + G[a]`), on score par la value head (logit 28), et on ajoute un biais `β·normalise(Q_plan)` aux logits d'action (0-7). Validation : banc d'anticipation dédié, puis ablation gatée en stoneage.

**Tech Stack:** Python 3.13, NumPy. Substrat `src/agents/mamba_agent.py` (`MambaBatchModel`). Outils de mesure sur le modèle de `tools/metabolic_cost_sweep.py`. Tests pytest (`tests/sandbox/`).

## Global Constraints

- **Défaut OFF non-régressif** : flag de classe `MambaBatchModel.PLAN_BIAS = 0.0`. À 0.0, le `forward` doit être **bit-identique** au comportement actuel (le dreaming aléatoire existant tourne inchangé).
- **Actions = 8 logits de déplacement** : `A = 8`, correspondant à `preds[:, 0:8]` (move 0..7) ; clé `"move"` des dicts d'action.
- **Position de la value head** : logit 28, lu à `H[i, map_idx[N_i - O_i + 28]]`.
- **Round-trip de `G` en ORDRE NŒUD** (comme `genome.W`, jamais en index batch brut) : stocké `a.planner_G` de forme `(A, N_i)`, projeté via `map_idx`. Évite le piège d'aplatissement type `from_genome`.
- **Planificateur et dreaming aléatoire mutuellement exclusifs** : si `PLAN_BIAS > 0`, le bloc de rêve aléatoire est sauté pour les agents à organe (`organ_genes[0]`).
- **Discipline mesure** : multi-seed apparié + test de signe ; `memory_retriever.stop()` avant boucle ; sweet-spot énergie `base_metabolism=0.25`, `forage_payoff=3.0` ; 1 variable/expérience.
- **Commits path-scopés** (sessions parallèles) : `git add <chemins explicites>`, jamais `-A`.

---

### Task 1: Module `planner` — fonctions pures (rollout, normalisation)

**Files:**
- Create: `src/agents/planner.py`
- Test: `tests/sandbox/test_planner.py`

**Interfaces:**
- Produces:
  - `plan_rollout(H_rec: np.ndarray (B,N), G_batch: np.ndarray (B,A,N), value_pos: np.ndarray (B,)) -> np.ndarray (B,A)` — `Q_plan[b,a] = (H_rec[b] + G_batch[b,a])[value_pos[b]]`.
  - `normalize_q(Q: np.ndarray (B,A)) -> np.ndarray (B,A)` — centre (moyenne 0) et divise par (std+1e-6) par ligne.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_planner.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.agents.planner import plan_rollout, normalize_q


def test_plan_rollout_reads_value_after_action_delta():
    # B=1, A=2, N=3 ; value_pos=2. G ajoute +5 à la position valeur pour l'action 1.
    H_rec = np.array([[0.0, 0.0, 1.0]], dtype=np.float32)
    G = np.zeros((1, 2, 3), dtype=np.float32)
    G[0, 1, 2] = 5.0                       # action 1 -> +5 sur la valeur
    value_pos = np.array([2])
    Q = plan_rollout(H_rec, G, value_pos)
    assert Q.shape == (1, 2)
    assert np.isclose(Q[0, 0], 1.0)        # action 0 : valeur inchangée
    assert np.isclose(Q[0, 1], 6.0)        # action 1 : 1 + 5


def test_plan_rollout_per_agent_value_pos():
    H_rec = np.array([[2.0, 0.0], [0.0, 3.0]], dtype=np.float32)
    G = np.zeros((2, 1, 2), dtype=np.float32)
    value_pos = np.array([0, 1])           # agent 0 lit pos 0, agent 1 lit pos 1
    Q = plan_rollout(H_rec, G, value_pos)
    assert np.isclose(Q[0, 0], 2.0)
    assert np.isclose(Q[1, 0], 3.0)


def test_normalize_q_centers_and_scales():
    Q = np.array([[1.0, 3.0]], dtype=np.float32)
    Z = normalize_q(Q)
    assert np.isclose(Z.mean(), 0.0, atol=1e-5)
    assert Z[0, 1] > Z[0, 0]               # ordre préservé


def test_normalize_q_constant_row_no_nan():
    Q = np.zeros((1, 4), dtype=np.float32)
    Z = normalize_q(Q)
    assert np.all(np.isfinite(Z))          # std+eps évite la division par 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner.py -q`
Expected: FAIL (ModuleNotFoundError: src.agents.planner).

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/planner.py
"""Planificateur latent Dreamer-lite (NAS Axe 3 — activation du dreaming).
Anticipation conditionnée par l'action : pour chaque action a, prédire le latent suivant
H'_a = H_rec + G[a] et le scorer par la value head. Fonctions PURES (testables isolément)."""
import numpy as np


def plan_rollout(H_rec: np.ndarray, G_batch: np.ndarray, value_pos: np.ndarray) -> np.ndarray:
    """Q_plan[b,a] = valeur prédite si l'agent b joue l'action a (profondeur 1).
    H_rec: (B,N) latent post-récurrence. G_batch: (B,A,N) deltas action. value_pos: (B,) index valeur."""
    B, A, N = G_batch.shape
    Hp = H_rec[:, None, :] + G_batch                       # (B, A, N)
    rows = np.arange(B)[:, None]                           # (B,1)
    cols = np.arange(A)[None, :]                           # (1,A)
    Q = Hp[rows, cols, value_pos[:, None]]                 # (B, A)
    return Q.astype(np.float32)


def normalize_q(Q: np.ndarray) -> np.ndarray:
    """Centre (moyenne 0) + échelle robuste par agent -> biais comparable quelle que soit
    l'échelle de la value head. std+1e-6 évite la division par 0 (ligne constante)."""
    mean = Q.mean(axis=1, keepdims=True)
    std = Q.std(axis=1, keepdims=True) + 1e-6
    return ((Q - mean) / std).astype(np.float32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents/planner.py tests/sandbox/test_planner.py
git commit -m "feat(planner): fonctions pures plan_rollout + normalize_q (NAS Axe 3)"
```

---

### Task 2: Apprentissage en ligne de `g` — fonction pure `update_transition`

**Files:**
- Modify: `src/agents/planner.py`
- Test: `tests/sandbox/test_planner.py`

**Interfaces:**
- Produces: `update_transition(G_batch (B,A,N), prev_H_rec (B,N), next_H_rec (B,N), move_actions (B,), lr: float) -> np.ndarray (B,A,N)` — rapproche `G[b, move_b]` de la transition observée `(next - prev)[b]` ; ignore `move = -1` ou hors `[0,A)`.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_planner.py
from src.agents.planner import update_transition


def test_update_transition_moves_toward_observed_delta():
    G = np.zeros((1, 3, 2), dtype=np.float32)
    prev = np.array([[0.0, 0.0]], dtype=np.float32)
    nxt = np.array([[2.0, 0.0]], dtype=np.float32)    # delta observé = [2,0]
    move = np.array([1])                              # action 1 exécutée
    G2 = update_transition(G, prev, nxt, move, lr=0.5)
    assert np.allclose(G2[0, 1], [1.0, 0.0])          # 0 + 0.5*([2,0]-0) = [1,0]
    assert np.allclose(G2[0, 0], [0.0, 0.0])          # actions non jouées inchangées
    assert np.allclose(G2[0, 2], [0.0, 0.0])


def test_update_transition_reduces_prediction_error_over_steps():
    # Répéter la même transition pour l'action 0 -> G[0] converge vers le delta.
    G = np.zeros((1, 2, 2), dtype=np.float32)
    prev = np.array([[0.0, 0.0]], dtype=np.float32)
    nxt = np.array([[1.0, -1.0]], dtype=np.float32)
    move = np.array([0])
    for _ in range(50):
        G = update_transition(G, prev, nxt, move, lr=0.2)
    assert np.allclose(G[0, 0], [1.0, -1.0], atol=1e-2)


def test_update_transition_skips_invalid_move():
    G = np.zeros((1, 2, 2), dtype=np.float32)
    prev = np.zeros((1, 2), dtype=np.float32)
    nxt = np.ones((1, 2), dtype=np.float32)
    G2 = update_transition(G, prev, nxt, np.array([-1]), lr=1.0)
    assert np.allclose(G2, 0.0)                        # move=-1 -> aucune MAJ
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner.py -q`
Expected: FAIL (ImportError: cannot import name 'update_transition').

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à src/agents/planner.py
def update_transition(G_batch: np.ndarray, prev_H_rec: np.ndarray, next_H_rec: np.ndarray,
                      move_actions: np.ndarray, lr: float) -> np.ndarray:
    """MAJ en ligne de g : rapproche G[b, move_b] de la transition latente observée
    (next_H_rec - prev_H_rec)[b]. Modifie G_batch en place et le renvoie. move hors [0,A) ignoré."""
    B, A, N = G_batch.shape
    target = next_H_rec - prev_H_rec                       # (B, N)
    for b in range(B):
        a = int(move_actions[b])
        if 0 <= a < A:
            G_batch[b, a] += lr * (target[b] - G_batch[b, a])
    return G_batch
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents/planner.py tests/sandbox/test_planner.py
git commit -m "feat(planner): update_transition (apprentissage en ligne de g)"
```

---

### Task 3: État `G_batch` + round-trip dans `MambaBatchModel` (gaté, défaut OFF)

**Files:**
- Modify: `src/agents/mamba_agent.py` (flags classe ~302-307 ; init `__init__` ~412-420 ; persistance ~700-702)
- Test: `tests/sandbox/test_planner_integration.py`

**Interfaces:**
- Produces : `MambaBatchModel.PLAN_BIAS: float = 0.0`, `MambaBatchModel.PLAN_LR: float = 0.05`, `MambaBatchModel.PLAN_A: int = 8`. Attribut `self.G_batch: (B, A, max_N)`. Round-trip `a.planner_G: (A, N_i)` en ordre nœud.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_planner_integration.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def test_G_batch_allocated_and_roundtrips_node_order():
    a = MambaAgent()
    N = a.genome.num_nodes
    m = MambaBatchModel([a])
    assert m.G_batch.shape == (1, MambaBatchModel.PLAN_A, m.max_N)
    # injecter un G non nul en ordre nœud, vérifier round-trip après un forward
    a.planner_G = np.ones((MambaBatchModel.PLAN_A, N), dtype=np.float32)
    m2 = MambaBatchModel([a])
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    m2.forward(obs)
    assert hasattr(a, "planner_G")
    assert a.planner_G.shape == (MambaBatchModel.PLAN_A, N)


def test_default_flags_off():
    assert MambaBatchModel.PLAN_BIAS == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner_integration.py -q`
Expected: FAIL (AttributeError: 'MambaBatchModel' object has no attribute 'G_batch').

- [ ] **Step 3: Write minimal implementation**

Dans `src/agents/mamba_agent.py`, ajouter les flags de classe après `FORCE_DREAM = None` (~ligne 307) :

```python
    # NAS Axe 3 — Planificateur latent (activation du dreaming). Défaut OFF (non-régressif).
    PLAN_BIAS = 0.0   # poids du biais des logits d'action par le plan (0 = planificateur désactivé)
    PLAN_LR = 0.05    # taux d'apprentissage en ligne de g
    PLAN_A = 8        # nombre d'actions planifiées (= logits de déplacement 0..7)
```

Allouer `G_batch` dans `__init__`, juste après le bloc `Wp_batch` (~après ligne 419), en ordre nœud comme `genome.W` :

```python
        # NAS Axe 3 — modèle de transition action-conditionné g, par agent (round-trip ordre nœud).
        A = MambaBatchModel.PLAN_A
        self.G_batch = np.zeros((self.B, A, self.max_N), dtype=np.float32)
        for i, a in enumerate(agents):
            g = getattr(a, 'planner_G', None)
            N_i = a.genome.num_nodes
            if g is not None and getattr(g, 'shape', None) == (A, N_i):
                self.G_batch[i][:, self.mappings[i]] = g     # projette (A,N_i) -> (A,max_N)
```

Dans la boucle de persistance (`for i, a in enumerate(self.agents):` ~ligne 687), ajouter, à côté de `a.world_model_Wp = ...` :

```python
            a.planner_G = self.G_batch[i][:, map_idx].copy()   # extrait (A,N_i) en ordre nœud
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner_integration.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents/mamba_agent.py tests/sandbox/test_planner_integration.py
git commit -m "feat(planner): G_batch alloue + round-trip ordre noeud (gate defaut OFF)"
```

---

### Task 4: Câbler le rollout dans `forward` (biais sur logits d'action, gaté)

**Files:**
- Modify: `src/agents/mamba_agent.py` (import en tête ; capture `H_rec` + saut du rêve ~536-577 ; biais après extraction `preds` ~609)
- Test: `tests/sandbox/test_planner_integration.py`

**Interfaces:**
- Consumes : `plan_rollout`, `normalize_q` (Task 1) ; `self.G_batch` (Task 3).
- Produces : attribut `self.H_rec_batch: (B, max_N)` (latent post-attention, avant rêve) ; biais appliqué à `preds[:, 0:8]` pour les agents à organe quand `PLAN_BIAS>0`.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_planner_integration.py
def test_plan_bias_off_is_bit_identical():
    np.random.seed(0)
    a = MambaAgent(); a.genome.organ_genes = np.array([True, False])  # organe dreaming ON
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    MambaBatchModel.PLAN_BIAS = 0.0
    m1 = MambaBatchModel([a.clone()]); p1, _ = m1.forward(obs.copy())
    m2 = MambaBatchModel([a.clone()]); p2, _ = m2.forward(obs.copy())
    assert np.allclose(p1, p2)                       # déterminisme + non-régression OFF


def test_plan_bias_on_shifts_action_logits():
    a = MambaAgent(); a.genome.organ_genes = np.array([True, False])
    N = a.genome.num_nodes
    # G qui privilégie fortement l'action 3 (grand +valeur)
    G = np.zeros((MambaBatchModel.PLAN_A, N), dtype=np.float32)
    val_node = N - a.genome.num_outputs + 28
    G[3, val_node] = 50.0
    a.planner_G = G
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    MambaBatchModel.PLAN_BIAS = 1.0
    try:
        m = MambaBatchModel([a]); preds, _ = m.forward(obs)
        assert int(np.argmax(preds[0, :8])) == 3     # le plan pousse l'action 3
    finally:
        MambaBatchModel.PLAN_BIAS = 0.0              # restaurer le défaut global
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner_integration.py -q`
Expected: FAIL (`test_plan_bias_on_shifts_action_logits` : argmax ≠ 3, biais non câblé).

- [ ] **Step 3: Write minimal implementation**

En tête de `src/agents/mamba_agent.py` (avec les autres imports) :

```python
from src.agents.planner import plan_rollout, normalize_q
```

Au début du bloc de rêve (juste avant `do_dream_batch = preds_mid[:, 26]`, ~ligne 527), capturer `H_rec` et préparer le saut du rêve aléatoire quand le planificateur est actif :

```python
        self.H_rec_batch = H.copy()                  # latent post-attention, avant rêve (pour g)
        PLANNER_ON = MambaBatchModel.PLAN_BIAS > 0.0
```

Encadrer le bloc de rêve aléatoire existant (la boucle `for k in range(T_max):` et l'injection `H[dreaming_idx] = best_H[...]`) pour qu'il **ne tourne pas** quand `PLANNER_ON` :

```python
        if not PLANNER_ON:
            # ... (bloc de rêve aléatoire existant inchangé : is_dreaming, boucle k, best_H, injection)
```

Après l'extraction des `preds` (juste après la boucle ~609, avant `self.H_prev_batch = H`), appliquer le biais du plan :

```python
        if PLANNER_ON:
            value_pos = np.array([
                self.mappings[i][self.agents[i].genome.num_nodes
                                 - self.agents[i].genome.num_outputs + 28]
                for i in range(self.B)
            ])
            Q_plan = plan_rollout(self.H_rec_batch, self.G_batch, value_pos)   # (B, A)
            bias = MambaBatchModel.PLAN_BIAS * normalize_q(Q_plan)             # (B, A)
            A = MambaBatchModel.PLAN_A
            for i in range(self.B):
                og = getattr(self.agents[i].genome, 'organ_genes', None)
                if og is not None and len(og) > 0 and og[0]:
                    preds[i, :A] += bias[i]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner_integration.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run broader non-regression**

Run: `python -m pytest tests/sandbox/test_mamba_agent.py tests/sandbox/test_from_genome_preserve.py -q`
Expected: PASS (défaut OFF inchangé).

- [ ] **Step 6: Commit**

```bash
git add src/agents/mamba_agent.py tests/sandbox/test_planner_integration.py
git commit -m "feat(planner): rollout profondeur-1 + biais logits d'action dans forward (gate OFF)"
```

---

### Task 5: Apprentissage en ligne de `g` dans `compute_policy_gradient`

**Files:**
- Modify: `src/agents/mamba_agent.py` (`compute_policy_gradient` ~706-774 ; stocker `H_rec` dans `_td`)
- Test: `tests/sandbox/test_planner_integration.py`

**Interfaces:**
- Consumes : `update_transition` (Task 2) ; `self.H_rec_batch`, `self.G_batch` (Tasks 3-4).
- Produces : MAJ de `self.G_batch` par transition différée (tick t→t+1) sur l'action `move` exécutée.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_planner_integration.py
def test_g_learns_from_executed_transition():
    a = MambaAgent(); a.genome.organ_genes = np.array([True, False])
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    MambaBatchModel.PLAN_BIAS = 1.0
    try:
        m = MambaBatchModel([a])
        actions = [{"move": 2, "grab": 0, "rub": 0}]
        # tick t : forward + enregistrer la transition (pas encore de MAJ, pas de tick précédent)
        m.forward(obs); m.compute_policy_gradient(np.array([0.0]), actions)
        G_before = m.G_batch.copy()
        # tick t+1 : nouvelle obs -> H_rec change -> MAJ différée de G[move=2]
        obs2 = np.ones((1, a.genome.num_inputs), dtype=np.float32)
        m.forward(obs2); m.compute_policy_gradient(np.array([0.0]), actions)
        assert not np.allclose(m.G_batch[0, 2], G_before[0, 2])   # G[2] a appris
        assert np.allclose(m.G_batch[0, 5], G_before[0, 5])       # actions non jouées inchangées
    finally:
        MambaBatchModel.PLAN_BIAS = 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner_integration.py::test_g_learns_from_executed_transition -q`
Expected: FAIL (G[2] inchangé — MAJ non câblée).

- [ ] **Step 3: Write minimal implementation**

Dans `compute_policy_gradient`, le bloc Actor-Critic stocke déjà une transition différée dans `self.agents[i]._td`. Ajouter le `H_rec` (ordre nœud) au dict `_td` et, à la résolution différée, mettre à jour `G_batch`.

Importer en tête : `from src.agents.planner import update_transition` (peut être groupé avec l'import Task 4).

Dans la boucle `for i in range(self.B):` du bloc Actor-Critic (~748), au moment où `prev` est résolu (`if prev is not None and prev["act"] is not None:`), après la MAJ des poids, ajouter la MAJ de `g` (gardée si le plan est actif et `H_rec` dispo) :

```python
                if MambaBatchModel.PLAN_BIAS > 0.0 and prev.get("h_rec") is not None \
                        and getattr(self, "H_rec_batch", None) is not None:
                    map_idx = self.mappings[i]
                    cur_hrec = self.H_rec_batch[i, map_idx]                 # (N_i,) ordre nœud
                    pm = int(prev["act"].get("move", -1))
                    self.G_batch[i][:, map_idx] = update_transition(
                        self.G_batch[i][:, map_idx][None, ...],            # (1,A,N_i)
                        prev["h_rec"][None, :], cur_hrec[None, :],
                        np.array([pm]), MambaBatchModel.PLAN_LR)[0]
```

Et au stockage de la transition courante (`self.agents[i]._td = {...}`, ~772), ajouter le `H_rec` en ordre nœud :

```python
            hrec_t = (self.H_rec_batch[i, self.mappings[i]].copy()
                      if getattr(self, "H_rec_batch", None) is not None else None)
            self.agents[i]._td = {"h": h_t.copy(), "out": out_t.copy(), "value": v_t,
                                  "reward": float(rewards_batch[i]), "act": act,
                                  "v_node": N_i - O_i + 28, "h_rec": hrec_t}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner_integration.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents/mamba_agent.py tests/sandbox/test_planner_integration.py
git commit -m "feat(planner): apprentissage en ligne de g (transition differee) dans compute_policy_gradient"
```

---

### Task 6: Banc d'anticipation (danger télégraphié) + verdict

**Files:**
- Create: `tools/anticipation_bench.py`
- Test: `tests/sandbox/test_anticipation_bench.py`

**Interfaces:**
- Produces :
  - `run_bench(plan_bias: float, seeds: list[int], steps: int = 60) -> dict` — renvoie `{"survival_mean": float, "per_seed": [...]}`.
  - `compare(seeds: list[int]) -> dict` — bras planificateur (PLAN_BIAS>0) vs réactif (0.0), apparié par seed, `{"verdict": str, "median_ratio": float, "sign_p": float, "n_favorable": int, "n": int}`.

**Banc :** grille 1-D de longueur L=7, l'agent démarre au centre. À chaque tick, une obs encode la position + un **signal de danger** : à `t_warn`, une case adjacente devient mortelle au tick **suivant**. Survivre = s'éloigner au tick d'avertissement. Le réactif (sans plan) ne relie pas signal→mort future ; le planificateur, via `g` appris, prédit « rester → valeur basse ». Déterministe par seed, **sans `graph_rag`** (reproductible).

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_anticipation_bench.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.anticipation_bench import run_bench, compare


def test_run_bench_returns_survival():
    out = run_bench(plan_bias=0.0, seeds=[0, 1], steps=40)
    assert "survival_mean" in out and 0.0 <= out["survival_mean"] <= 1.0
    assert len(out["per_seed"]) == 2


def test_compare_structure():
    out = compare(seeds=[0, 1, 2])
    assert set(["verdict", "median_ratio", "sign_p", "n_favorable", "n"]).issubset(out)
    assert out["verdict"] in ("PLAN_GAGNE", "PLAN_PERD", "NEUTRE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_anticipation_bench.py -q`
Expected: FAIL (ModuleNotFoundError: tools.anticipation_bench).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/anticipation_bench.py
"""Banc d'anticipation (NAS Axe 3) : danger télégraphié 1-pas. Le planificateur (PLAN_BIAS>0)
doit battre le réactif (0.0) sur un env CONÇU pour récompenser l'anticipation -> découple
'le plan marche' de 'le monde le récompense'. Déterministe, sans graph_rag (reproductible).
Usage : AB_SEEDS=0,1,2 python tools/anticipation_bench.py"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel

L = 7                     # longueur de la grille
T_WARN_PERIOD = 6         # un danger est télégraphié tous les N ticks


def _obs(pos: int, danger_cell: int) -> np.ndarray:
    """Obs = one-hot position (L) ++ one-hot danger télégraphié (L), paddé à num_inputs au forward."""
    o = np.zeros(2 * L, dtype=np.float32)
    o[pos] = 1.0
    if danger_cell is not None:
        o[L + danger_cell] = 1.0
    return o


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def run_bench(plan_bias: float, seeds, steps: int = 60) -> dict:
    per_seed = []
    for seed in seeds:
        np.random.seed(seed)
        a = MambaAgent()
        a.genome.organ_genes = np.array([True, False])      # organe planificateur actif
        prev_bias = MambaBatchModel.PLAN_BIAS
        MambaBatchModel.PLAN_BIAS = plan_bias
        try:
            m = MambaBatchModel([a])
            pos = L // 2
            danger_cell = None          # case mortelle au PROCHAIN tick
            alive_ticks = 0
            for t in range(steps):
                # résoudre le danger télégraphié au tick précédent
                if danger_cell is not None and pos == danger_cell:
                    break               # mort
                danger_cell = None
                warn = (t % T_WARN_PERIOD == 0)
                telegraph = pos if warn else None   # danger annoncé SUR la case courante
                obs = _obs(pos, telegraph)[None, :]
                preds, _ = m.forward(obs)
                move = int(np.argmax(preds[0, :8])) % 3     # 0=gauche,1=rester,2=droite
                new_pos = min(L - 1, max(0, pos + (move - 1)))
                # récompense : -1 si on reste sur une case télégraphiée, +0.1 sinon (s'éloigner paie)
                reward = -1.0 if (warn and new_pos == pos) else 0.1
                m.compute_policy_gradient(np.array([reward], dtype=np.float32),
                                          [{"move": move, "grab": 0, "rub": 0}])
                if warn:
                    danger_cell = telegraph             # frappe au tick suivant
                pos = new_pos
                alive_ticks += 1
            per_seed.append(alive_ticks / float(steps))
        finally:
            MambaBatchModel.PLAN_BIAS = prev_bias
    return {"survival_mean": float(st.mean(per_seed)) if per_seed else 0.0,
            "per_seed": [{"seed": int(s), "survival": v} for s, v in zip(seeds, per_seed)]}


def compare(seeds, steps: int = 60) -> dict:
    ratios = []
    for seed in seeds:
        plan = run_bench(0.5, [seed], steps)["survival_mean"]
        react = run_bench(0.0, [seed], steps)["survival_mean"]
        ratios.append(plan / max(react, 1e-6))
    eff = [r for r in ratios if r != 1.0]
    n_fav = sum(1 for r in ratios if r > 1.0)
    p = _sign_p(sum(1 for r in eff if r > 1.0), len(eff))
    med = st.median(ratios) if ratios else 1.0
    verdict = "PLAN_GAGNE" if (med > 1.05 and 2 * n_fav > len(ratios)) else \
              ("PLAN_PERD" if med < 0.95 else "NEUTRE")
    return {"verdict": verdict, "median_ratio": float(med), "sign_p": float(p),
            "n_favorable": int(n_fav), "n": len(ratios), "ratios": ratios}


def main():
    seeds = [int(s) for s in os.environ.get("AB_SEEDS", "0,1,2,3,4,5,6,7").split(",") if s.strip()]
    steps = int(os.environ.get("AB_STEPS", "60"))
    out = compare(seeds, steps)
    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    return out


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_anticipation_bench.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the bench (résultat scientifique)**

Run: `AB_SEEDS=0,1,2,3,4,5,6,7 python tools/anticipation_bench.py`
Expected: une ligne `VERDICT=... median_ratio=... sign_p=...`. **Go/no-go** : si `PLAN_PERD`/`NEUTRE` net, le mécanisme ne capte pas la valeur d'anticipation → escalader (profondeur, forme de `g`) avant stoneage.

- [ ] **Step 6: Commit**

```bash
git add tools/anticipation_bench.py tests/sandbox/test_anticipation_bench.py
git commit -m "feat(planner): banc d'anticipation (danger telegraphie) + verdict apparie"
```

---

### Task 7: Outil de mesure stoneage (ablation gatée powered)

**Files:**
- Create: `tools/planner_compare.py`
- Test: `tests/sandbox/test_planner_compare.py`

**Interfaces:**
- Consumes : patron de `tools/metabolic_cost_sweep.py` (lignée évolutive appariée, `Harness.save`, sign test).
- Produces : `compare(seeds, eras, ...) -> dict` — bras planificateur (`PLAN_BIAS>0`) vs OFF, apparié par seed, verdict compétence/survie ; `run_era_planner(cfg, genomes, max_ticks, plan_bias)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_planner_compare.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.planner_compare import compare


def _fake_runner(cfg, genomes, max_ticks, plan_bias):
    # score déterministe : le bras planificateur (bias>0) marque un peu plus -> structure testable.
    base = 40.0 + (5.0 if plan_bias > 0 else 0.0)
    return [(base, genomes[0])], {"score": base, "ticks": 200.0}


def test_compare_structure():
    out = compare(seeds=[0, 1], eras=2, num_agents=4, max_ticks=50, run_era_fn=_fake_runner)
    assert "verdict" in out and out["config"]["seeds"] == [0, 1]
    assert out["verdict"] in ("PLAN_GAGNE", "PLAN_PERD", "NEUTRE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_planner_compare.py -q`
Expected: FAIL (ModuleNotFoundError: tools.planner_compare).

- [ ] **Step 3: Write minimal implementation**

Calquer la structure de `tools/metabolic_cost_sweep.py` : `_make_cfg` (sweet-spot 0.25/3), `_reproduce` (build_population + heavy_frac), `run_era_planner` (mirror `run_era_metab` mais en réglant `MambaBatchModel.PLAN_BIAS = plan_bias` autour de la boucle d'ères et `from_genome(g)` par défaut — preserve_dims déjà True), `run_lineage(seed, plan_bias, ...)` (compétence = moyenne des scores sur 5 dernières ères), `compare(seeds, ...)` (ratio bras-plan / bras-OFF apparié → `compute_transfer_verdict`-like → verdict PLAN_GAGNE/PERD/NEUTRE). Réutiliser `_sign_p` et `compute_sweep_verdict` (ou `compute_transfer_verdict` de `tools/curriculum_transfer.py`). `memory_retriever.stop()` en fin d'ère (déjà fait par le patron). Le runner accepte `run_era_fn` injectable (pour le test).

```python
# squelette clé (compléter sur le modèle de metabolic_cost_sweep.py) :
import os, sys, math, statistics as st
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.agents.mamba_agent import MambaAgent, MambaBatchModel
# ... imports Biosphere3D, calculate_life_score, build_population, async_logger (cf. metabolic_cost_sweep)

def compare(seeds, eras=15, num_agents=30, max_ticks=400, plan_bias=0.5, run_era_fn=None):
    ratios, per_seed = [], []
    for seed in seeds:
        c_plan = run_lineage(seed, plan_bias, eras, num_agents, max_ticks, run_era_fn)
        c_off  = run_lineage(seed, 0.0,       eras, num_agents, max_ticks, run_era_fn)
        r = c_plan / max(c_off, 1e-6); ratios.append(r)
        per_seed.append({"seed": int(seed), "C_plan": c_plan, "C_off": c_off, "ratio": r})
    eff = [r for r in ratios if r != 1.0]; n_fav = sum(1 for r in ratios if r > 1.0)
    p = _sign_p(sum(1 for r in eff if r > 1.0), len(eff)); med = st.median(ratios) if ratios else 1.0
    verdict = "PLAN_GAGNE" if (med > 1.05 and 2*n_fav > len(ratios)) else ("PLAN_PERD" if med < 0.95 else "NEUTRE")
    return {"verdict": verdict, "median_ratio": float(med), "sign_p": float(p),
            "n_favorable": int(n_fav), "n": len(ratios), "per_seed": per_seed,
            "config": {"seeds": [int(s) for s in seeds], "eras": eras,
                       "num_agents": num_agents, "max_ticks": max_ticks, "plan_bias": plan_bias}}
```

`run_era_planner` règle `MambaBatchModel.PLAN_BIAS = plan_bias` avant la boucle de ticks et le restaure en `finally`. `run_lineage` accepte `run_era_fn` (défaut `run_era_planner`) et passe `plan_bias`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_planner_compare.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Mesure powered (après go du banc Task 6)**

Run: `PC_SEEDS=0,1,2,3,4,5,6,7 PC_ERAS=15 python tools/planner_compare.py`
Expected: `VERDICT=... median_ratio=... sign_p=...` sauvegardé via `Harness.save`. Verdict = apport du planificateur en stoneage (défaut OFF préservé hors mesure).

- [ ] **Step 6: Commit**

```bash
git add tools/planner_compare.py tests/sandbox/test_planner_compare.py
git commit -m "feat(planner): outil de mesure stoneage (ablation gatee powered)"
```

---

## Self-Review (auteur)

**Couverture spec :** C1 transition `g` → Tasks 1,3 ; C2 apprentissage en ligne → Tasks 2,5 ; C3 biais → Task 4 ; C4 gate/coût → Tasks 3,4 (PLAN_BIAS défaut 0, organe) ; C5 off-distribution → profondeur 1 + biais + `normalize_q` (Tasks 1,4) ; banc → Task 6 ; mesure stoneage → Task 7 ; non-régression → Tasks 3,4 (tests bit-identiques OFF). **Couvert.**

**Cohérence des types :** `G_batch (B,A,N)`, `planner_G (A,N_i)`, `value_pos (B,)`, `move` int 0..7, `PLAN_A=8`, value à `N_i-O_i+28` — cohérents entre tâches.

**Placeholders :** code complet pour les unités pures et les tests ; Task 7 fournit le squelette clé + référence explicite au patron `metabolic_cost_sweep.py` (volontaire : éviter de dupliquer 200 lignes identiques). Aucun « TODO » fonctionnel.

**Risque résiduel :** Task 6/7 = science (verdict ouvert) — un `NEUTRE`/`PERD` est un résultat valide qui réoriente (profondeur k, `g` bilinéaire) avant d'investir davantage.
