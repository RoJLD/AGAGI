# A/B transfer_ratio torch vs legacy dans le monde — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans pour exécuter ce plan tâche par tâche. Les étapes utilisent des cases (`- [ ]`).

**Goal:** Faire vivre le substrat torch (gradient) dans le vrai moteur-monde via le seam `batch_model_cls`, puis mesurer le `transfer_ratio` (north-star G1) torch vs legacy, powered et apparié, et consigner l'EDR.

**Architecture:** Le monde (`Biosphere3D.step`) construit son batch via `self.batch_model_cls(models, world_model=...)` (seam S2 existant, `world_1_stoneage.py:42,988`). On écrit un adaptateur `TorchBatchModel` **conforme au contrat MambaBatchModel** (forward→(logits B×O, compute_spent), `compute_policy_gradient`, sync d'état agent), réutilisant la dynamique LTC + Actor-Critic TD autograd déjà livrée (`src/agents/backend_torch.py`). On injecte la classe via une config, on branche le choix dans `make_run_era_fn`/`curriculum_transfer`, puis on lance l'A/B.

**Tech Stack:** Python 3.13, numpy, torch (requirements-torch.txt, optionnel), pytest. Connectome LTC, Actor-Critic TD.

## Global Constraints

- **Non-régression absolue** : `batch_model_cls` défaut = `MambaBatchModel` ; tout chemin legacy reste byte-identique. torch chargé paresseusement (cœur numpy intact).
- **1 variable (Cmd 15)** : l'A/B doit isoler la *règle d'apprentissage*. Le substrat torch (MVP) n'a PAS d'organes (NTM/router/TTC) → confound. **Décision** : 3 bras — `legacy-full`, `legacy-core` (organes ablés via flags existants), `torch-core` ; la comparaison propre est **torch-core vs legacy-core**, `legacy-full` sert de référence prod. Documenter tout résidu de confound (NTM/TTC non ablables proprement) en caveat EDR.
- **Powered avant de conclure** : ≥10 seeds appariés, test de signe ; un signal à peu de seeds ne conclut pas (historique 057/075/077/082/083).
- **Repro** : `deterministic=True` (memory_retriever neutralisé), seed aux frontières (`SeedManager.seed_boundary`).
- **Path-scoped commits** (sessions parallèles, cf. mémoire `parallel-sessions-shared-tree`).
- **Numéro EDR** : vérifier les libres avant d'écrire (110-115 pris ; collisions parallèles fréquentes — `find . -path '*/docs/EDR/1*'`).

**Contrat exact du seam** (à satisfaire par `TorchBatchModel`, lu dans `world_1_stoneage.py`) :
- `__init__(self, models: list[MambaAgent], world_model=None)`
- `forward(batch_obs: np.ndarray, env_surprise_batch=None) -> (batch_logits: np.ndarray (B,O), compute_spent: np.ndarray (B,))`
- `compute_policy_gradient(rewards_batch: np.ndarray, actions_batch: list[dict])` — dict `{"move":int,"grab":0/1,"rub":0/1}`
- Effets de bord lus en aval : `a["model"].surprise_momentum` (float), `.attention_mask`, `.ntm_memory`, `.explicit_memory`, `.genome.W` (write-back) ; tolérer les attributs de classe posés par le monde (`KWTA_KEEP_FRAC`, `PLAN_BIAS`, …).

---

### Task 1: `TorchBatchModel` — forward conforme (B×O) avec padding hétérogène

**Files:**
- Create: `src/agents/torch_batch_model.py`
- Test: `tests/sandbox/test_torch_batch_model.py`

**Interfaces:**
- Consumes: `MambaAgent` (`.genome.W/.num_inputs/.num_outputs/.num_nodes`), `_step` LTC de `backend_torch` (réécrit ici en version padée).
- Produces: `TorchBatchModel(models, world_model=None)` ; `.forward(batch_obs, env_surprise_batch=None) -> (np.ndarray (B,O), np.ndarray (B,))`.

- [ ] **Step 1: Écrire le test d'échec (forward shape + hétérogène)**

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np, pytest
pytest.importorskip("torch")
from src.agents.mamba_agent import MambaAgent
from src.agents.torch_batch_model import TorchBatchModel

def test_forward_shape_heterogeneous():
    np.random.seed(0)
    models = [MambaAgent(), MambaAgent()]  # même dim ici ; padding teste l'élastique
    bm = TorchBatchModel(models)
    O = max(m.genome.num_outputs for m in models)
    logits, spent = bm.forward(np.zeros((2, models[0].genome.num_inputs), dtype=np.float32))
    assert logits.shape == (2, O)
    assert spent.shape == (2,)
    assert np.all(np.isfinite(logits))
```

- [ ] **Step 2: Lancer, vérifier l'échec** — `pytest tests/sandbox/test_torch_batch_model.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implémenter init + forward (padding élastique + LTC différentiable)**

Réutiliser le mapping élastique de `MambaBatchModel.__init__` (`world... mamba_agent.py:357-379`) pour `W_batch (B,max_N,max_N)` + `mappings`, puis la récurrence LTC de `backend_torch._step`. `forward` : injecte l'obs aux capteurs, applique un pas LTC, lit les `O` derniers nœuds → `(B,O)`.

```python
import numpy as np
try:
    import torch
except Exception:
    torch = None

class TorchBatchModel:
    KWTA_KEEP_FRAC = 1.0           # tolère les attrs posés par le monde (no-op torch)
    def __init__(self, models, world_model=None):
        if torch is None:
            raise NotImplementedError("torch absent (requirements-torch.txt)")
        self.agents = models           # NB: le monde passe les .model (MambaAgent)
        self.B = len(models)
        self.world_model = world_model
        if self.B == 0:
            return
        self.max_I = max(m.genome.num_inputs for m in models)
        self.max_O = max(m.genome.num_outputs for m in models)
        self.max_H = max(m.genome.num_nodes - m.genome.num_inputs - m.genome.num_outputs for m in models)
        self.max_N = min(self.max_I + self.max_H + self.max_O, 256)
        W = np.zeros((self.B, self.max_N, self.max_N), dtype=np.float32)
        self.mappings = []
        for i, m in enumerate(models):
            I_i, O_i, N_i = m.genome.num_inputs, m.genome.num_outputs, m.genome.num_nodes
            idx = np.zeros(N_i, dtype=int)
            for s in range(I_i): idx[s] = s
            for s in range(I_i, N_i - O_i): idx[s] = self.max_I + (s - I_i)
            for s in range(N_i - O_i, N_i): idx[s] = (self.max_I + self.max_H) + (s - (N_i - O_i))
            idx = np.clip(idx, 0, self.max_N - 1)
            self.mappings.append(idx)
            W[i][idx[:, None], idx[None, :]] = m.genome.W
        self.W = torch.tensor(W, requires_grad=True)
        self.H = torch.zeros((self.B, self.max_N))
        self.opt = torch.optim.SGD([self.W], lr=0.04)
        self._eye = torch.eye(self.max_N)
        self._last = None
        self._prev = None

    def _step(self, obs_t, H_in):
        H = H_in.clone()
        H[:, :obs_t.shape[1]] = obs_t
        diag = torch.diagonal(self.W, dim1=1, dim2=2)
        delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
        excit = torch.bmm(H.unsqueeze(1), self.W * (1.0 - self._eye)).squeeze(1)
        return (1.0 - delta) * H + delta * torch.tanh(excit)

    def forward(self, batch_obs, env_surprise_batch=None):
        if self.B == 0:
            return np.array([]), np.array([])
        x = np.zeros((self.B, self.max_I), dtype=np.float32)
        x[:, :batch_obs.shape[1]] = batch_obs
        obs_t = torch.tensor(x)
        H_in = self.H.detach()
        with torch.no_grad():
            H_new = self._step(obs_t, H_in)
        self.H = H_new.detach()
        self._last = (obs_t, H_in)
        logits = H_new[:, self.max_N - self.max_O:self.max_N]
        return logits.cpu().numpy(), np.ones(self.B, dtype=np.float32)  # compute_spent neutre (pas de TTC)
```

- [ ] **Step 4: Lancer, vérifier le succès** — `pytest tests/sandbox/test_torch_batch_model.py -q` → PASS.

- [ ] **Step 5: Commit** — `git add src/agents/torch_batch_model.py tests/sandbox/test_torch_batch_model.py && git commit -m "feat(agents): TorchBatchModel forward conforme (B×O) padding élastique"`

---

### Task 2: Sync d'état agent + `compute_policy_gradient` (contrat aval)

**Files:**
- Modify: `src/agents/torch_batch_model.py`
- Test: `tests/sandbox/test_torch_batch_model.py`

**Interfaces:**
- Produces: `forward` met à jour `a.genome.W`, `a.surprise_momentum`, `a.attention_mask`, `a.ntm_memory`, `a.explicit_memory` (valeurs sûres) ; `compute_policy_gradient(rewards, actions)` Actor-Critic TD différé (réutilise la logique de `backend_torch._td_update`, indices nœud via `mappings[i]`).

- [ ] **Step 1: Test — forward synchronise les attributs lus par le monde**

```python
def test_forward_syncs_agent_state():
    np.random.seed(0); m = MambaAgent(); bm = TorchBatchModel([m])
    bm.forward(np.zeros((1, m.genome.num_inputs), dtype=np.float32))
    assert isinstance(m.surprise_momentum, float)
    assert m.attention_mask is not None and m.ntm_memory is not None
```

- [ ] **Step 2: Test — compute_policy_gradient apprend (value monte, W change)**

```python
def test_cpg_actor_critic_learns():
    np.random.seed(0); m = MambaAgent(); bm = TorchBatchModel([m])
    rng = np.random.RandomState(1); obs = (rng.randn(1, m.genome.num_inputs)*0.5).astype(np.float32)
    v0 = float(bm.forward(obs)[0][0, 28]); W0 = m.genome.W.copy()
    for _ in range(40):
        bm.forward(obs); bm.compute_policy_gradient(np.array([5.0], np.float32), [{"move":0,"grab":0,"rub":0}])
    vN = float(bm.forward(obs)[0][0, 28])
    assert vN > v0 and not np.allclose(W0, m.genome.W)
```

- [ ] **Step 3: Lancer, vérifier l'échec** (attrs absents / cpg inexistant).

- [ ] **Step 4: Implémenter sync + cpg**

Dans `forward`, avant le `return`, écrire pour chaque agent : `a.genome.W = (bloc W démappé via mappings[i])` ; `a.surprise_momentum = float(env_surprise_batch[i]) if env_surprise_batch is not None else 0.0` ; `a.attention_mask = np.ones(a.genome.num_inputs, np.float32)` ; `a.ntm_memory = getattr(a,"ntm_memory",np.zeros((10,5),np.float32))` ; `a.explicit_memory = np.zeros(5, np.float32)`. Implémenter `compute_policy_gradient` en copiant la structure différée de `backend_torch.TorchPopulationModel.learn`/`_td_update` (value = out[:,28], move/grab(24)/rub(25), δ=r+γV'−V, γ=0.9) en indexant `out` sur le bloc `[max_N-max_O:max_N]`, puis write-back W via `mappings`.

- [ ] **Step 5: Lancer → PASS. Commit** — `git commit -m "feat(agents): TorchBatchModel sync état + Actor-Critic TD (contrat aval)"`

---

### Task 3: Le monde tourne avec `batch_model_cls=TorchBatchModel` (non-régression legacy)

**Files:**
- Test: `tests/sandbox/test_world_torch_backend.py`
- (lecture) `src/worlds/world_1_stoneage.py:42,988,995,1444`

**Interfaces:**
- Consumes: `Biosphere3D`, `WorldConfig`, `TorchBatchModel`, `MambaAgent`.

- [ ] **Step 1: Test — legacy inchangé (non-régression) + torch ne crashe pas sur N ticks**

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np, pytest
pytest.importorskip("torch")
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.agents.torch_batch_model import TorchBatchModel

def _world(cls=None, seed=0, n=6):
    np.random.seed(seed)
    env = Biosphere3D(WorldConfig())
    if hasattr(env, "memory_retriever"): env.memory_retriever.stop(); env.memory_retriever.clear()
    if cls is not None: env.batch_model_cls = cls
    for _ in range(n):
        a = MambaAgent(); env.add_agent(a, energy=50.0)
    return env

def test_world_runs_with_torch_backend():
    env = _world(TorchBatchModel)
    for _ in range(20):
        if not env.agents: break
        env.step()
    assert True  # pas de crash = contrat satisfait
```

- [ ] **Step 2: Lancer** — corriger toute `AttributeError` (attribut aval manquant) en complétant le sync Task 2 jusqu'à PASS.

- [ ] **Step 3: Commit** — `git commit -m "test(world): Biosphere3D tourne sous batch_model_cls=TorchBatchModel"`

---

### Task 4: Brancher le choix de backend dans `make_run_era_fn` / `curriculum_transfer`

**Files:**
- Modify: `main_curriculum.py:74-101` (`make_run_era_fn` accepte `batch_model_cls=None`, l'assigne à `env.batch_model_cls` après `_prepare_world`)
- Modify: `tools/curriculum_transfer.py:63-91` (`run_transfer_experiment(..., batch_model_cls=None)`, propagé à `make_run_era_fn`)
- Test: `tests/sandbox/test_transfer_backend_param.py`

**Interfaces:**
- Produces: `make_run_era_fn(..., batch_model_cls=None)` ; `run_transfer_experiment(..., batch_model_cls=None)`.

- [ ] **Step 1: Test — make_run_era_fn injecte la classe**

```python
def test_run_era_uses_injected_batch_model_cls(monkeypatch):
    # run_era_fn injecté testable sans biosphère : on vérifie la signature accepte le param
    from main_curriculum import make_run_era_fn
    import inspect
    assert "batch_model_cls" in inspect.signature(make_run_era_fn).parameters
```

- [ ] **Step 2: Lancer → FAIL (param absent).**

- [ ] **Step 3: Implémenter** — ajouter `batch_model_cls=None` à `make_run_era_fn` ; dans `run_era_fn`, après `env = _prepare_world(...)` : `if batch_model_cls is not None: env.batch_model_cls = batch_model_cls`. Idem propager depuis `run_transfer_experiment` (param + passage à `make_run_era_fn`).

- [ ] **Step 4: Lancer → PASS. Commit** — `git commit -m "feat(transfer): param batch_model_cls dans make_run_era_fn + curriculum_transfer"`

---

### Task 5: Bras de contrôle du confound (legacy-core ablé)

**Files:**
- Create: `tools/transfer_ab_backends.py` (orchestre les 3 bras)
- Test: `tests/sandbox/test_transfer_ab_backends.py`

**Interfaces:**
- Produces: `make_legacy_core_cls()` → sous-classe de `MambaBatchModel` avec `ABLATE_THRESHOLDS=True, ABLATE_ROUTER=True` (organes neutralisés pour se rapprocher du torch-core) ; `run_three_arms(seeds, ...)` → `{legacy_full, legacy_core, torch_core}` ratios.

- [ ] **Step 1: Test — legacy-core a les flags d'ablation actifs**

```python
def test_legacy_core_ablates_organs():
    from tools.transfer_ab_backends import make_legacy_core_cls
    cls = make_legacy_core_cls()
    assert cls.ABLATE_THRESHOLDS is True and cls.ABLATE_ROUTER is True
```

- [ ] **Step 2: Lancer → FAIL. Implémenter** `make_legacy_core_cls` (sous-classe avec flags) + `run_three_arms` qui appelle `run_transfer_experiment(batch_model_cls=cls, ...)` pour chaque bras. **Step 3: PASS. Commit.**

> Caveat à documenter dans l'EDR : NTM/TTC ne sont pas ablables proprement → `torch-core` vs `legacy-core` réduit le confound sans l'éliminer ; `legacy-full` = référence prod.

---

### Task 6: Lancer l'A/B transfer_ratio powered + EDR

**Files:**
- Run: `tools/transfer_ab_backends.py` (ou `curriculum_transfer` par bras)
- Create: `docs/EDR/<NNN>_Torch_Substrate_Transfer_Ratio_AB.md`
- (peut nécessiter) Modify: REF-LTC `adopt_for += [EDR-NNN]`

- [ ] **Step 1: Vérifier numéro EDR libre** — `find . -path '*/docs/EDR/1*' | sort` ; choisir le 1er libre (≥116, attention collisions parallèles).

- [ ] **Step 2: Run powered** — ≥10 seeds appariés, `deterministic=True`, sweet-spot énergie (`SWEET_METAB=0.25`, `SWEET_PAYOFF=3.0`), budget compute pensé (profiler 1 seed d'abord). Capturer `transfer_ratio` par bras + test de signe.

- [ ] **Step 3: Écrire l'EDR** — frontmatter `verdict:` honnête (TRANSFERE/NEUTRE/NUIT par bras) ; comparer torch-core vs legacy-core (1 variable) et vs legacy-full (prod) ; caveats (NTM/TTC non ablés, compute_spent neutre torch, MVP). Relier au graphe (`REF-LTC -A_ADOPTER_POUR-> EDR-NNN`).

- [ ] **Step 4: Consolider + commit** — `python tools/consolidate_records.py` (0 problème) ; `git add docs/EDR/<NNN>_*.md docs/REF/LTC_Hasani_2021.md && git commit -m "docs(EDR-NNN): A/B transfer_ratio torch vs legacy"`

---

## Self-Review

- **Couverture spec** : seam (T3) · contrat forward+cpg (T1,T2) · threading transfert (T4) · confound (T5) · mesure+EDR (T6). ✓
- **Non-régression** : défaut legacy partout (T3,T4) ; torch opt-in. ✓
- **1 variable** : bras legacy-core vs torch-core (T5), confound résiduel documenté. ✓
- **Powered** : ≥10 seeds + test de signe (T6, Global Constraints). ✓
- **Risques connus** : (a) le forward torch-core n'a pas NTM/TTC → comportement-monde différent (confound) ; (b) coût compute du transfert en biosphère (profiler avant 10 seeds) ; (c) collision numéro EDR (vérifier au moment T6) ; (d) `compute_spent` neutre torch fausse le `brain_cost` → documenter ou répliquer un coût proportionnel à N.

## Execution Handoff

Plan complet et sauvé. Deux options d'exécution :
1. **Subagent-Driven (recommandé)** — un subagent frais par tâche, revue entre tâches.
2. **Inline** — exécution en session avec checkpoints.
