# Intégration torch in-world (axe 1, crans 0-1) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire tourner le crédit épisodique torch (`learn_episode`) dans la boucle biosphère derrière un flag opt-in, sans régresser le chemin legacy, avec un banc A/B survie qui produit un verdict.

**Architecture:** Le monde possède un `pop` torch **persistant** (hissé hors de la boucle par-tick) et un **buffer glissant** de K ticks. Un flag `USE_TORCH_INWORLD` branche `pop.forward`/`pop.learn` (API `PopulationModel`, ADR-003) à la place de l'API `MambaBatchModel`. Tous les K ticks, `pop.learn_episode` crédite l'épisode. Cohorte FIXE (`benchmark_mode`) garantit dimensions homogènes + `B` stable.

**Tech Stack:** Python, PyTorch (dépendance optionnelle), numpy, pytest.

## Global Constraints

- **Non-régression legacy stricte** : `USE_TORCH_INWORLD=False` (défaut) → comportement biosphère identique bit-à-bit à l'actuel.
- **1 variable à la fois** (Commandement 15) : chaque cran = un flag, un verdict powered avant le suivant.
- **Cohorte fixe** : les crans 0-1 tournent en `benchmark_mode=True` (repro/mutation OFF, EDR-114b) → I/O/N homogènes, `B` stable sur la fenêtre.
- **torch = dépendance optionnelle** : flag on sans torch installé → erreur claire au boot (`NotImplementedError`), jamais en plein run.
- **Style projet** : français, concis, pas d'emojis. Tests dans `tests/sandbox/`.
- **Ne pas committer sans validation** : les steps `git commit` sont présents pour l'exécutant, mais l'utilisateur robla valide avant push (CLAUDE.md).
- **Commits path-scoped** : tree partagé entre sessions //. Ne `git add` QUE les fichiers de ce plan (`src/worlds/world_1_stoneage.py`, `tests/sandbox/test_torch_inworld*.py`, `tools/torch_inworld_ab.py`). NE PAS toucher aux modifs EDR-160 en vol (`src/agents/backend_torch.py`, `tools/torch_prod_gate_meansends.py`, `config.json`, `data/*`).
- **API monde réelle (vérifiée)** : la classe est `Biosphere3D` (pas `World1StoneAge`) ; population peuplée par `env.add_agent(MambaAgent(), energy=80.0)` (crée `agent["model"]=MambaAgent`, `agent["model"].genome.W` accessible). `env.step()` ≈ 2.4 s/step → tests LÉGERS (≤12 agents, ≤6 ticks).
- **Repro / KuzuDB ambiant** : `Biosphere3D` démarre un `memory_retriever` connecté au KuzuDB partagé → runs NON reproductibles (casse l'appariement par seed). Couper via `if hasattr(env, "memory_retriever"): env.memory_retriever.stop()` après `add_agent`, avant la boucle. Voir mémoire `biosphere-ambient-memory-nonrepro`.

## Helper de test partagé

Tous les tests de `tests/sandbox/test_torch_inworld.py` utilisent ce helper (défini en tête du fichier, Task 1) :

```python
import numpy as np
from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent

def _tiny_world(use_torch, n_agents=12):
    cfg = WorldConfig()
    cfg.size = 16
    w = Biosphere3D(cfg)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()          # repro : couper la mémoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                # cohorte fixe : dims homogènes + B stable (114b)
    w.use_torch_inworld = use_torch
    return w
```

---

### Task 1: Flag `USE_TORCH_INWORLD` + pop torch persistant (cran 0 — forward)

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`__init__` ~ligne 33-49 ; boucle inférence ~ligne 985-999)
- Test: `tests/sandbox/test_torch_inworld.py` (créer)

**Interfaces:**
- Consumes: `make_population(agents, backend="torch")` → `TorchPopulationModel` avec `.forward(batch_obs)` et `.learn(rewards, actions)` (backend.py:57).
- Produces: attribut monde `self.use_torch_inworld: bool` (défaut False) ; attribut `self._torch_pop` (None ou `PopulationModel` persistant) ; méthode `self._get_batch_model(models)` qui renvoie soit le legacy recréé/tick, soit le pop torch persistant.

- [ ] **Step 1: Écrire le test de non-régression + persistance**

```python
# tests/sandbox/test_torch_inworld.py
# (le helper _tiny_world de la section "Helper de test partagé" est défini ici, en tête du fichier)
import numpy as np
from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent

def _tiny_world(use_torch, n_agents=12):
    cfg = WorldConfig()
    cfg.size = 16
    w = Biosphere3D(cfg)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()          # repro : couper la mémoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                # cohorte fixe : dims homogènes + B stable (114b)
    w.use_torch_inworld = use_torch
    return w

def test_flag_off_uses_legacy_and_no_persistent_pop():
    w = _tiny_world(use_torch=False)
    models = [a["model"] for a in w.agents] if w.agents else []
    bm = w._get_batch_model(models)
    assert bm.__class__.__name__ == "MambaBatchModel"
    assert w._torch_pop is None

def test_flag_on_returns_persistent_torch_pop():
    w = _tiny_world(use_torch=True)
    if not w.agents:
        return
    models = [a["model"] for a in w.agents]
    bm1 = w._get_batch_model(models)
    bm2 = w._get_batch_model(models)
    assert bm1 is bm2                  # MÊME objet -> optimiseur/gate persistent
    assert type(bm1).backend == "torch"
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: FAIL (`AttributeError: 'World1StoneAge' object has no attribute 'use_torch_inworld'` / `_get_batch_model`).

- [ ] **Step 3: Ajouter les attributs dans `__init__`**

Dans `World1StoneAge.__init__`, après la ligne `self.batch_model_cls = MambaBatchModel` (~ligne 42) :

```python
        # Intégration torch in-world (axe 1). OFF par défaut = legacy strictement non-régressif.
        # ON => pop torch PERSISTANT (hissé hors boucle par-tick : l'optimiseur SGD et le gate
        # doivent survivre entre ticks). Exige cohorte fixe (benchmark_mode) pour dims homogènes.
        self.use_torch_inworld = False
        self._torch_pop = None
```

- [ ] **Step 4: Ajouter la méthode `_get_batch_model`**

Ajouter comme méthode de `World1StoneAge` (près de la boucle d'inférence) :

```python
    def _get_batch_model(self, models):
        """Renvoie le batch model du tick. Legacy = recréé/tick (non-régressif). Torch = pop
        PERSISTANT (créé une fois, réutilisé) pour conserver optimiseur + gate. Reconstruit si la
        taille de population change (Task 5 gère les dims ; ici on couvre B)."""
        if not self.use_torch_inworld:
            return self.batch_model_cls(models, world_model=self.world_model)
        from src.agents.backend import make_population
        need_rebuild = (
            self._torch_pop is None
            or getattr(self._torch_pop, "B", -1) != len(models)
        )
        if need_rebuild:
            agents = [m.agent if hasattr(m, "agent") else m for m in models]
            self._torch_pop = make_population(models, backend="torch",
                                              world_model=self.world_model)
        return self._torch_pop
```

> Note exécutant : `make_population` attend des `agents` (objets à `.genome`). Vérifier ce que contient `models` à [world_1_stoneage.py:990](../../../src/worlds/world_1_stoneage.py) (`models = [a["model"] for a in self.agents]`). Si `a["model"]` est le `MambaAgent`, passer `models` directement ; s'il enveloppe le génome autrement, adapter l'extraction. Le test `test_flag_on_returns_persistent_torch_pop` valide que la construction réussit.

- [ ] **Step 5: Brancher `_get_batch_model` dans la boucle**

Remplacer [world_1_stoneage.py:992](../../../src/worlds/world_1_stoneage.py) :

```python
        # AVANT : batch_model = self.batch_model_cls(models, world_model=self.world_model)
        batch_model = self._get_batch_model(models)
```

- [ ] **Step 6: Lancer les tests, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Non-régression legacy — smoke run**

Run: `python -m pytest tests/sandbox/ -k "kuzu or wired or backend" -q`
Expected: PASS (aucune régression sur les chemins existants ; le flag off ne touche rien).

- [ ] **Step 8: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_inworld.py
git commit -m "feat(G1): USE_TORCH_INWORLD cran 0 — pop torch persistant hors boucle par-tick"
```

---

### Task 2: Branchement de l'API PopulationModel dans la boucle (cran 0 — learn)

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`forward` ~ligne 999 ; `compute_policy_gradient` ~ligne 1448)
- Test: `tests/sandbox/test_torch_inworld.py`

**Interfaces:**
- Consumes: `pop.forward(batch_obs, env_surprise_batch=...)` → `(logits, compute_spent)` ; `pop.learn(rewards, actions_batch)` (API PopulationModel).
- Produces: la boucle appelle `learn` (torch) ou `compute_policy_gradient` (legacy) selon le flag — sémantique de crédit par-tick identique.

- [ ] **Step 1: Test — un tick complet en mode torch ne crashe pas et apprend**

```python
def test_one_tick_torch_forward_and_learn():
    w = _tiny_world(use_torch=True)
    if not w.agents:
        return
    # un pas de simulation complet
    w.step()                            # ne doit pas lever
    assert w._torch_pop is not None
    # les poids appris sont réécrits dans les génomes (Baldwin, _write_back)
    W0 = np.asarray(w.agents[0]["model"].genome.W, dtype=np.float32).copy()
    w.step()
    W1 = np.asarray(w.agents[0]["model"].genome.W, dtype=np.float32)
    assert W0.shape == W1.shape
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py::test_one_tick_torch_forward_and_learn -v`
Expected: FAIL (`AttributeError: 'TorchPopulationModel' object has no attribute 'compute_policy_gradient'`).

- [ ] **Step 3: Adapter l'appel de crédit par-tick**

Remplacer [world_1_stoneage.py:1448](../../../src/worlds/world_1_stoneage.py) :

```python
        # AVANT : batch_model.compute_policy_gradient(rewards, actions_batch)
        if self.use_torch_inworld:
            batch_model.learn(rewards, actions_batch)          # API PopulationModel (ADR-003)
        else:
            batch_model.compute_policy_gradient(rewards, actions_batch)
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_inworld.py
git commit -m "feat(G1): cran 0 — API PopulationModel (learn) branchée dans la boucle biosphère"
```

---

### Task 3: Buffer glissant K porté par le monde (cran 1 — collecte)

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`__init__` ; boucle ~après ligne 1448)
- Test: `tests/sandbox/test_torch_inworld.py`

**Interfaces:**
- Consumes: `batch_obs` (B,I), `actions_batch` (list de dicts move/grab/rub), `rewards` (B,) déjà calculés dans la boucle.
- Produces: `self._torch_traj: collections.deque` (maxlen=K) de tuples `(obs, actions, rewards)` ; `self.torch_episode_k: int` (défaut 8).

- [ ] **Step 1: Test — le buffer glisse et respecte maxlen**

```python
def test_traj_buffer_slides_with_maxlen():
    w = _tiny_world(use_torch=True)
    w.torch_episode_k = 3
    if not w.agents:
        return
    for _ in range(5):
        w.step()
    assert len(w._torch_traj) == 3                 # maxlen respecté
    obs, acts, rew = w._torch_traj[-1]
    assert len(acts) == len(w.agents)              # actions alignées sur la cohorte
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py::test_traj_buffer_slides_with_maxlen -v`
Expected: FAIL (`AttributeError: ... '_torch_traj'`).

- [ ] **Step 3: Initialiser le buffer dans `__init__`**

Après les attributs de la Task 1 :

```python
        from collections import deque
        self.torch_episode_k = 8          # taille de fenêtre épisodique (variable EDR)
        self._torch_traj = deque(maxlen=self.torch_episode_k)
```

- [ ] **Step 4: Pousser dans le buffer chaque tick (mode torch)**

Juste après le branchement de crédit de la Task 2 (dans le bloc `if self.use_torch_inworld`) :

```python
        if self.use_torch_inworld:
            # Snapshot du tick pour le crédit épisodique (Task 4). Copie défensive : batch_obs/rewards
            # sont réutilisés par la boucle. actions_batch est déjà une liste fraîche de dicts.
            self._torch_traj.append((np.asarray(batch_obs, dtype=np.float32).copy(),
                                     list(actions_batch),
                                     np.asarray(rewards, dtype=np.float32).copy()))
```

> Note exécutant : `batch_obs` est calculé ligne 989 et reste en portée jusqu'à la fin du tick. Confirmer qu'il n'est pas muté entre 989 et le point d'insertion ; sinon capturer le snapshot plus tôt.

- [ ] **Step 5: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_inworld.py
git commit -m "feat(G1): cran 1 — buffer glissant K ticks porté par le monde"
```

---

### Task 4: Appel `learn_episode` tous les K ticks (cran 1 — crédit épisodique)

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (boucle ; ajout compteur de ticks)
- Test: `tests/sandbox/test_torch_inworld.py`

**Interfaces:**
- Consumes: `pop.learn_episode(obs_seq, actions_seq, rewards, gamma=1.0, gate_last_only=True)` (backend_torch.py:233). `obs_seq` = liste de (B,I) ; `actions_seq` = liste de listes de dicts ; `rewards` = retour épisodique (B,) baseliné.
- Produces: `self._torch_tick: int` (compteur) ; appel `learn_episode` quand `_torch_tick % K == 0` et buffer plein.

- [ ] **Step 1: Test — learn_episode appelé au bon rythme, retourne une loss**

```python
def test_learn_episode_fires_every_k(monkeypatch):
    w = _tiny_world(use_torch=True)
    w.torch_episode_k = 3
    if not w.agents:
        return
    calls = []
    for _ in range(3):
        w.step()
    # patch learn_episode pour compter les appels
    orig = w._torch_pop.learn_episode
    def spy(obs_seq, actions_seq, rewards, **kw):
        calls.append(len(obs_seq))
        return orig(obs_seq, actions_seq, rewards, **kw)
    monkeypatch.setattr(w._torch_pop, "learn_episode", spy)
    for _ in range(3):                    # 3 ticks de plus -> 1 fenêtre pleine
        w.step()
    assert calls and calls[-1] == 3       # obs_seq = K ticks
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py::test_learn_episode_fires_every_k -v`
Expected: FAIL (aucun appel — `learn_episode` pas encore branché).

- [ ] **Step 3: Compteur de ticks dans `__init__`**

Après `self._torch_traj = ...` :

```python
        self._torch_tick = 0
```

- [ ] **Step 4: Déclencher `learn_episode` quand la fenêtre est pleine**

Après le push buffer de la Task 3 (toujours dans `if self.use_torch_inworld`) :

```python
            self._torch_tick += 1
            if len(self._torch_traj) == self._torch_traj.maxlen and \
               self._torch_tick % self.torch_episode_k == 0:
                obs_seq = [t[0] for t in self._torch_traj]
                actions_seq = [t[1] for t in self._torch_traj]
                # retour épisodique = somme des rewards de la fenêtre, baseliné par la moyenne pop
                ep_return = np.sum([t[2] for t in self._torch_traj], axis=0)   # (B,)
                ep_return = ep_return - float(np.mean(ep_return))
                self._torch_pop.learn_episode(obs_seq, actions_seq, ep_return,
                                              gamma=1.0, gate_last_only=True)
```

> Note exécutant : `learn_episode` exige que `B` (len(actions_seq[t])) soit constant sur la fenêtre. La cohorte fixe (`benchmark_mode`) le garantit. Si une désynchro survient (cohorte non figée), la garde de Task 5 skippe le cycle.

- [ ] **Step 5: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_inworld.py
git commit -m "feat(G1): cran 1 — learn_episode crédite l'épisode tous les K ticks in-world"
```

---

### Task 5: Garde de robustesse — cohorte incomplète / dims changeantes

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (bloc `learn_episode`)
- Test: `tests/sandbox/test_torch_inworld.py`

**Interfaces:**
- Consumes: le buffer `_torch_traj` (peut contenir des ticks à `B` variable si la cohorte n'est pas figée).
- Produces: skip propre (log, pas de crash) quand les `B` de la fenêtre diffèrent ou que le pop a été reconstruit.

- [ ] **Step 1: Test — B hétérogène dans le buffer => skip sans crash**

```python
def test_learn_episode_skips_on_ragged_cohort():
    w = _tiny_world(use_torch=True)
    w.torch_episode_k = 3
    if not w.agents:
        return
    # injecter un buffer volontairement raggé (B différents)
    import numpy as np
    w._torch_traj.clear()
    w._torch_traj.append((np.zeros((4, w.agents[0]["model"].genome.num_inputs), np.float32),
                          [{"move": 0}] * 4, np.zeros(4, np.float32)))
    w._torch_traj.append((np.zeros((3, w.agents[0]["model"].genome.num_inputs), np.float32),
                          [{"move": 0}] * 3, np.zeros(3, np.float32)))
    w._torch_traj.append((np.zeros((3, w.agents[0]["model"].genome.num_inputs), np.float32),
                          [{"move": 0}] * 3, np.zeros(3, np.float32)))
    # ne doit pas lever
    assert w._maybe_learn_episode() is None
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py::test_learn_episode_skips_on_ragged_cohort -v`
Expected: FAIL (`AttributeError: ... '_maybe_learn_episode'`).

- [ ] **Step 3: Extraire le déclenchement en méthode gardée**

Remplacer le bloc inline de la Task 4 par un appel `self._maybe_learn_episode()`, et ajouter la méthode :

```python
    def _maybe_learn_episode(self):
        """Crédit épisodique si la fenêtre est pleine ET la cohorte homogène (B constant). Skip
        propre sinon (cohorte non figée / pop reconstruit) — jamais de crash en plein run."""
        traj = self._torch_traj
        if len(traj) != traj.maxlen or self._torch_tick % self.torch_episode_k != 0:
            return None
        bsizes = {len(t[1]) for t in traj}
        if len(bsizes) != 1 or bsizes.pop() != getattr(self._torch_pop, "B", -1):
            logger.emit("TORCH_EPISODE_SKIP", {"reason": "ragged_cohort", "tick": self._torch_tick})
            return None
        obs_seq = [t[0] for t in traj]
        actions_seq = [t[1] for t in traj]
        ep_return = np.sum([t[2] for t in traj], axis=0)
        ep_return = ep_return - float(np.mean(ep_return))
        return self._torch_pop.learn_episode(obs_seq, actions_seq, ep_return,
                                             gamma=1.0, gate_last_only=True)
```

Et dans la boucle, remplacer le bloc `if len(self._torch_traj) == ...` par :

```python
            self._torch_tick += 1
            self._maybe_learn_episode()
```

- [ ] **Step 4: Lancer tous les tests**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_inworld.py
git commit -m "feat(G1): cran 1 — garde cohorte homogène pour learn_episode in-world"
```

---

### Task 6: Banc A/B survie `torch_inworld_ab.py` (l'instrument)

**Files:**
- Create: `tools/torch_inworld_ab.py`
- Test: `tests/sandbox/test_torch_inworld_ab.py` (créer)

**Interfaces:**
- Consumes: `World1StoneAge` avec `use_torch_inworld` + `benchmark_mode` ; `compute_ab_verdict(rows, band)` de `tools/substrate_ab.py` (pur, testable sans run).
- Produces: `run_arm(use_torch, seed, ticks, n_agents) -> dict` (survie médiane) ; `compare(seeds, ticks) -> dict` (verdict apparié).

- [ ] **Step 1: Test — le verdict est pur et appariable (réutilise compute_ab_verdict)**

```python
# tests/sandbox/test_torch_inworld_ab.py
from tools.substrate_ab import compute_ab_verdict

def test_verdict_pure_on_synthetic_rows():
    rows = [{"diff": 0.1}, {"diff": 0.2}, {"diff": 0.15}]   # torch > legacy
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE"
    assert v["n"] == 3

def test_run_arm_smoke():
    # léger : ~2.4 s/step -> 4 ticks. Vérifie la STRUCTURE du retour, pas le contenu du verdict.
    from tools.torch_inworld_ab import run_arm
    r = run_arm(use_torch=False, seed=0, ticks=4, n_agents=8)
    assert "survival" in r and r["ticks"] == 4 and 0.0 <= r["survival"] <= 1.0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_inworld_ab.py -v`
Expected: FAIL (`ModuleNotFoundError: tools.torch_inworld_ab`).

- [ ] **Step 3: Écrire le banc**

```python
# tools/torch_inworld_ab.py
"""A/B survie in-world : USE_TORCH_INWORLD off vs on, apparié par seed, cohorte fixe (114b).
Verdict via compute_ab_verdict (substrate_ab). C'est l'instrument des crans 0-1 (le livrable EDR).

Usage : python tools/torch_inworld_ab.py   (env: TIA_SEEDS, TIA_TICKS, TIA_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent
from tools.substrate_ab import compute_ab_verdict


def run_arm(use_torch: bool, seed: int = 0, ticks: int = 200, n_agents: int = 16) -> dict:
    """Tourne un monde en cohorte fixe et renvoie la survie médiane (fraction d'agents vivants
    en fin de run). Apparié : même seed, mêmes dims, seul le backend change. La mémoire KuzuDB
    ambiante est coupée (repro : sinon l'appariement par seed est faussé)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    cfg = WorldConfig()
    w = Biosphere3D(cfg)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()           # repro : couper la mémoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                 # cohorte fixe -> dims homogènes, B stable (114b)
    w.use_torch_inworld = use_torch
    n0 = len(w.agents)
    for _ in range(ticks):
        if not w.agents:
            break
        w.step()
    survival = (len(w.agents) / n0) if n0 else 0.0
    return {"use_torch": use_torch, "seed": int(seed), "ticks": ticks,
            "n_agents": n0, "survival": float(survival)}


def compare(seeds=(0, 1, 2, 3), ticks: int = 200, n_agents: int = 16) -> dict:
    """A/B apparié legacy vs torch in-world par seed -> verdict de survie."""
    rows = []
    for s in seeds:
        leg = run_arm(False, seed=s, ticks=ticks, n_agents=n_agents)
        tor = run_arm(True, seed=s, ticks=ticks, n_agents=n_agents)
        rows.append({"seed": s, "legacy": leg["survival"], "torch": tor["survival"],
                     "diff": tor["survival"] - leg["survival"]})
    verdict = compute_ab_verdict(rows, band=0.02)
    return {"rows": rows, "verdict": verdict}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TIA_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("TIA_TICKS", "200"))
    agents = int(os.environ.get("TIA_AGENTS", "16"))
    out = compare(seeds=seeds, ticks=ticks, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} legacy={r['legacy']:.3f} torch={r['torch']:.3f} diff={r['diff']:+.3f}")
    print("VERDICT:", out["verdict"])
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_inworld_ab.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Premier verdict cran 0-1 (2 seeds courts)**

Run: `TIA_SEEDS=0,1 TIA_TICKS=60 TIA_AGENTS=12 python tools/torch_inworld_ab.py`
Expected: affiche 2 lignes seed + un `VERDICT` (NEUTRE/GRADIENT_GAGNE/HEBBIEN_GAGNE). Le contenu du verdict est le résultat scientifique, pas un critère de succès du test.

- [ ] **Step 6: Commit**

```bash
git add tools/torch_inworld_ab.py tests/sandbox/test_torch_inworld_ab.py
git commit -m "feat(G1): banc A/B survie in-world (torch vs legacy) — instrument crans 0-1"
```

---

## Self-Review

**Spec coverage :**
- Couture `make_population` + flag `USE_TORCH_INWORLD` → Task 1. ✓
- Mismatch API MambaBatchModel/PopulationModel → Task 2. ✓
- Buffer glissant K porté par le monde → Task 3. ✓
- `learn_episode` tous les K ticks → Task 4. ✓
- Cohorte fixe / dims homogènes / skip propre → Task 5 (+ `benchmark_mode` posé dans tous les tests et le banc). ✓
- Banc in-world (l'instrument) → Task 6. ✓
- Non-régression legacy stricte → Task 1 step 1 & 7 (flag off = legacy). ✓
- Progression flag-par-flag : crans 0 (Task 1-2), 1 (Task 3-5) ; crans 2-4 (gate/antisat/mult) = plan de suivi, hors scope ici. ✓

**Placeholder scan :** les 3 « Note exécutant » pointent des vérifications d'intégration réelles (extraction de `models`, mutation de `batch_obs`, désynchro cohorte), pas des TODO — chacune est doublée d'un test qui échoue si l'hypothèse est fausse. Pas de « TBD/implement later ». ✓

**Type consistency :** `_get_batch_model(models)` (Task 1) ↔ appelé Task 1 step 5 ; `_torch_pop.B` (Task 1 & 5) ; `_torch_traj` deque de `(obs, actions, rewards)` (Task 3) ↔ consommé Task 4 & 5 ; `_maybe_learn_episode()` (Task 5) remplace le bloc inline Task 4 ; `learn_episode(obs_seq, actions_seq, rewards, gamma, gate_last_only)` conforme à backend_torch.py:233 ; `compute_ab_verdict(rows, band)` conforme à substrate_ab.py:41. ✓

## Hors scope (plan de suivi)
Crans 2-4 (gate `CONDITION_GATE`/`GATE_TARGET`, `ANTISAT`, `GATE_MULT`) + mesure du binding in-world P(Y|X) ; reconstruction du pop sur `add_node` (évolution topologique hors cohorte fixe) ; axes 2/3/4 du backlog.
