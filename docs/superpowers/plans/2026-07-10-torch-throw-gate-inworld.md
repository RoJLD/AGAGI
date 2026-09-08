# B2 — Throw-gate in-world Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Câbler dans la vraie boucle biosphère le throw-gate binaire validé isolé par EDR-171 — router le throw (logit 8) sur le contexte spear-en-inventaire porté par `H`, renforcé par l'outcome réel (kill-avec-outil), avec un témoin shuffle.

**Architecture:** Une tête apprise au niveau MONDE (`_throw_w` N-dim partagé population + `_throw_b` scalaire + Adam), superposée au pop torch persistant, path-scopée à `world_1_stoneage.py` (zéro modif `backend_torch.py`). Sous `use_torch_inworld AND torch_throw_gate` : injection d'un biais sur `logits[8]` (lu sur `H.detach()`, W gelé), décision throw stochastique, REINFORCE immédiat 1-pas sur l'outcome. Un banc neuf mesure `binding_gap = P(throw|spear) − P(throw|¬spear)` sur deux bras (ON vs SHUFFLE), verdict `compute_ab_verdict`.

**Tech Stack:** Python, numpy, PyTorch (importé paresseusement, gardé par flags), pytest.

## Global Constraints

- **Path-scopé.** Modifier UNIQUEMENT `src/worlds/world_1_stoneage.py` (+ son test) et créer `tools/torch_throw_gate_inworld_ab.py` (+ son test). ZÉRO modification de `src/agents/backend_torch.py`. `git add` explicite des seuls fichiers de la tâche, JAMAIS `git add -A`.
- **Flag-par-flag.** Toute la Brique B2 est gardée par `self.use_torch_inworld AND self.torch_throw_gate`. `torch_throw_gate=False` (défaut) ⇒ crans 0-1 STRICTEMENT inchangés. `use_torch_inworld=False` ⇒ legacy strictement non-régressif.
- **W gelé.** La tête lit `self._torch_pop.H.detach()` — pas de rétro-propagation dans le tronc.
- **torch importé paresseusement** dans les méthodes gardées (le monde legacy est numpy, pas de dépendance torch dure).
- **Style :** français, concis, pas d'emojis. Shell PowerShell (Windows). Tests via `python -m pytest ...`. TDD, commits path-scopés.
- **Repro banc :** stopper `env.memory_retriever` AVANT la boucle ; `benchmark_mode=True` (cohorte fixe, dims homogènes) ; CRN par seed.
- **Alignement identité :** au point du bloc torch (≈ lignes 1517-1531) et de la tête, `self._torch_pop.H.shape[0] == len(self.agents)` (mortalité appliquée APRÈS la boucle). Skip propre sinon.

## Pré-flight (contrôleur, AVANT Task 1)

Vérifier les attributs porteurs par un smoke jetable (ne pas committer) :
```powershell
python -c "import numpy as np; from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig; from src.agents.mamba_agent import MambaAgent; w=Biosphere3D(WorldConfig()); [w.add_agent(MambaAgent(), energy=80.0) for _ in range(4)]; w.memory_retriever.stop() if hasattr(w,'memory_retriever') else None; w.current_era=1; w.benchmark_mode=True; w.use_torch_inworld=True; w.step(); p=w._torch_pop; print('N', p.N, 'H', tuple(p.H.shape), 'agents', len(w.agents))"
```
Attendu : `H == (len(agents), N)`. Si l'attribut diffère (ex. `p.hidden` au lieu de `p.H`), corriger les références dans toutes les tâches avant de dispatcher.

---

## File Structure

- `src/worlds/world_1_stoneage.py` — tête throw-gate : attributs (Task 1), init paresseuse `_ensure_throw_gate` (Task 1), injection biais + décision stochastique + records + détection kill-outil + `_pg["throw"]` (Task 2), REINFORCE `_learn_throw_gate` + câblage (Task 3).
- `tests/sandbox/test_torch_throw_gate_world.py` — tests de la tête (Tasks 1-3).
- `tools/torch_throw_gate_inworld_ab.py` — banc A/B : `run_arm` + semis (Task 4), `compare` + verdict + `__main__` (Task 5).
- `tests/sandbox/test_torch_throw_gate_inworld_ab.py` — tests du banc (Tasks 4-5).

---

## Task 1 : Attributs + init paresseuse `_ensure_throw_gate`

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (bloc `__init__`, après `self._torch_tick = 0` ≈ ligne 54 ; nouvelle méthode près de `_get_batch_model` ≈ ligne 937)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: `self._torch_pop` (pop torch persistant, attribut `.N`), existant.
- Produces: attributs `self.torch_throw_gate: bool`, `self.torch_throw_gate_lr: float`, `self.torch_throw_antisat: float`, `self.torch_throw_shuffle: bool`, `self._throw_w`, `self._throw_b`, `self._throw_opt`, `self._throw_shuf_rng`, `self._throw_kills_tool: int`. Méthode `self._ensure_throw_gate() -> None`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/sandbox/test_torch_throw_gate_world.py` :
```python
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent


class _FakePop:
    """Stub minimal du pop torch : expose seulement .N (dim cachee)."""
    def __init__(self, n):
        self.N = n
        self.B = 0


def _fresh_world():
    w = Biosphere3D(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    return w


def test_throw_gate_defaults_off():
    w = _fresh_world()
    assert w.torch_throw_gate is False
    assert w._throw_w is None and w._throw_opt is None
    assert w._throw_kills_tool == 0


def test_ensure_throw_gate_noop_when_off():
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = False        # gate OFF -> no-op meme si pop present
    w._torch_pop = _FakePop(8)
    w._ensure_throw_gate()
    assert w._throw_w is None


def test_ensure_throw_gate_builds_head():
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(8)
    w._ensure_throw_gate()
    assert tuple(w._throw_w.shape) == (8,)
    assert tuple(w._throw_b.shape) == (1,)
    assert w._throw_opt is not None and w._throw_shuf_rng is not None
    prev = w._throw_w
    w._ensure_throw_gate()            # idempotent : ne recree pas
    assert w._throw_w is prev
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py -v`
Expected: FAIL (`AttributeError: 'Biosphere3D' object has no attribute 'torch_throw_gate'`).

- [ ] **Step 3: Ajouter les attributs dans `__init__`**

Dans `src/worlds/world_1_stoneage.py`, juste après `self._torch_tick = 0` (≈ ligne 54) :
```python
        # Throw-gate in-world (B2, EDR-171 -> biosphere). Tete apprise au niveau MONDE (readout
        # partage population sur H) qui route l'action "ends" (throw, logit 8) sur le contexte
        # spear-en-inventaire. OFF par defaut => crans 0-1 strictement inchanges. Exige
        # use_torch_inworld. W gele (H detache) ; REINFORCE immediat 1-pas sur l'outcome.
        self.torch_throw_gate = False
        self.torch_throw_gate_lr = 0.05
        self.torch_throw_antisat = 6.0
        self.torch_throw_shuffle = False     # bras temoin : recompense permutee
        self._throw_w = None                 # torch (N,) : cree paresseusement au 1er tick torch
        self._throw_b = None                 # torch (1,)
        self._throw_opt = None               # Adam([_throw_w, _throw_b])
        self._throw_shuf_rng = None          # RandomState fixe pour le shuffle
        self._throw_kills_tool = 0           # compteur KPI : throws de spear touchant une prey
```

- [ ] **Step 4: Ajouter la méthode `_ensure_throw_gate`**

Dans `src/worlds/world_1_stoneage.py`, juste avant `def _get_batch_model` (≈ ligne 937) :
```python
    def _ensure_throw_gate(self):
        """Init paresseuse de la tete throw-gate (B2). No-op si gate OFF, deja init, ou pop absent.
        Cree w_throw (N-dim partage population), b_throw (scalaire), l'optimiseur Adam et le RNG de
        shuffle. Appelee au 1er tick torch quand pop.N est connu."""
        if not (self.use_torch_inworld and self.torch_throw_gate):
            return
        if self._throw_w is not None:
            return
        if self._torch_pop is None:
            return
        import torch
        N = self._torch_pop.N
        self._throw_w = torch.zeros(N, requires_grad=True)
        self._throw_b = torch.zeros(1, requires_grad=True)
        self._throw_opt = torch.optim.Adam([self._throw_w, self._throw_b],
                                           lr=self.torch_throw_gate_lr)
        self._throw_shuf_rng = np.random.RandomState(12345)
```

- [ ] **Step 5: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit (path-scopé)**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(G1): throw-gate B2 - attributs + init paresseuse _ensure_throw_gate"
```

---

## Task 2 : Injection du biais + décision stochastique + records + `_pg["throw"]`

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (appel `_ensure_throw_gate` après forward ≈ ligne 1063 ; injection avant `do_throw` ≈ ligne 1142 ; détection kill-outil dans le bloc balistique ≈ ligne 1289 ; `_pg` ≈ ligne 1330)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: `self._ensure_throw_gate()`, `self._throw_w/_throw_b` (Task 1) ; `self._torch_pop.H` (torch `(B,N)`) ; `has_spear` (déjà importé, ligne 18) ; `logits = batch_logits[idx]` (numpy) ; `thrown_item`, `hit_entity`, `self.preys` (bloc balistique existant).
- Produces: par agent et par tick sous le gate — `agent["_throw_ctx"]: bool` (has_spear AVANT le throw), `agent["_throw_did"]: bool`, `agent["_throw_kill_tool"]: bool` ; clé `"throw"` dans `agent["_pg"]`.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/sandbox/test_torch_throw_gate_world.py` :
```python
def _torch_world(n_agents=4, seed=0):
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    w = _fresh_world()
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    w.current_era = 1
    w.benchmark_mode = True
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    for a in w.agents:                       # semer un spear (contexte present)
        a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})
    return w


def test_gate_on_step_records_and_H_shape():
    w = _torch_world()
    w.step()
    # pop.H aligne sur les agents (assomption porteuse)
    assert w._torch_pop.H.shape[0] == len(w.agents)
    assert w._torch_pop.H.shape[1] == w._torch_pop.N
    for a in w.agents:
        assert "_throw_did" in a and isinstance(a["_throw_did"], bool)
        assert "_throw_ctx" in a and isinstance(a["_throw_ctx"], bool)
        assert "throw" in a["_pg"]


def test_gate_off_is_nonregressive():
    np.random.seed(1)
    w = _fresh_world()
    for _ in range(4):
        w.add_agent(MambaAgent(), energy=80.0)
    w.current_era = 1
    w.benchmark_mode = True
    # use_torch_inworld reste False, torch_throw_gate reste False : legacy pur
    w.step()                                  # ne doit pas crasher
    for a in w.agents:
        assert "_throw_did" not in a          # aucun record B2 en legacy
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_gate_on_step_records_and_H_shape -v`
Expected: FAIL (`KeyError: '_throw_did'` ou `'throw'`).

- [ ] **Step 3: Appeler `_ensure_throw_gate` après le forward**

Dans `src/worlds/world_1_stoneage.py`, juste après le bloc `batch_logits, compute_spent = batch_model.forward(...)` et sa normalisation `compute_spent` (après ≈ ligne 1069, avant la boucle par-agent ≈ ligne 1075) :
```python
        if self.use_torch_inworld and self.torch_throw_gate:
            self._ensure_throw_gate()          # init paresseuse (pop.N connu apres forward)
```

- [ ] **Step 4: Injecter le biais + décision stochastique**

Dans `src/worlds/world_1_stoneage.py`, REMPLACER la ligne `do_throw = float(logits[8]) > 0` (≈ ligne 1142) par :
```python
            if (self.use_torch_inworld and self.torch_throw_gate
                    and self._throw_w is not None):
                import torch
                h_i = self._torch_pop.H[idx].detach()
                z = float(h_i @ self._throw_w) + float(self._throw_b)
                p_throw = 1.0 / (1.0 + np.exp(-np.clip(float(logits[8]) + z, -10.0, 10.0)))
                do_throw = bool(np.random.rand() < p_throw)
                agent["_throw_ctx"] = bool(has_spear(agent["inventory"]))  # AVANT le pop
                agent["_throw_did"] = do_throw
                agent["_throw_kill_tool"] = False        # arme par le bloc balistique si kill-outil
            else:
                do_throw = float(logits[8]) > 0
```

- [ ] **Step 5: Détecter le kill-avec-outil dans le bloc balistique**

Dans `src/worlds/world_1_stoneage.py`, dans le bloc `if hit_entity:` (≈ lignes 1289-1296), après `agent["throw_feedback"] = 1.0` :
```python
                    if (thrown_item.get("type") == "Spear"
                            and any(hit_entity is p for p in self.preys)):
                        agent["_throw_kill_tool"] = True   # KPI : spear lance touchant une prey
```

- [ ] **Step 6: Ajouter `throw` au dict de crédit `_pg`**

Dans `src/worlds/world_1_stoneage.py`, REMPLACER (≈ ligne 1330) :
```python
            agent["_pg"] = {"move": int(action), "grab": 1 if do_grab > 0 else 0,
                            "rub": 1 if do_rub > 0 else 0}
```
par :
```python
            agent["_pg"] = {"move": int(action), "grab": 1 if do_grab > 0 else 0,
                            "rub": 1 if do_rub > 0 else 0,
                            "throw": 1 if do_throw else 0}
```

- [ ] **Step 7: Lancer les tests**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py -v`
Expected: PASS (5 tests : les 3 de Task 1 + les 2 nouveaux).

- [ ] **Step 8: Commit (path-scopé)**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(G1): throw-gate B2 - biais logit[8] + decision stochastique + records + _pg[throw]"
```

---

## Task 3 : REINFORCE immédiat `_learn_throw_gate` + shuffle + câblage

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (nouvelle méthode près de `_maybe_learn_episode` ≈ ligne 958 ; câblage dans le bloc torch ≈ lignes 1517-1531)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: `self._torch_pop.H` (torch `(B,N)`) ; `agent["_throw_did"]`, `agent["_throw_kill_tool"]` (Task 2) ; `self._throw_w/_throw_b/_throw_opt/_throw_shuf_rng`, `self.torch_throw_shuffle`, `self.torch_throw_antisat` (Task 1) ; `logger.emit` (importé).
- Produces: `self._learn_throw_gate() -> float | None` (loss, ou None si skip) ; incrémente `self._throw_kills_tool`.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/sandbox/test_torch_throw_gate_world.py` :
```python
def test_learn_throw_gate_steps_optimizer():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    # H fixe (3 agents x 6) ; agent 0 kill-outil, agent 1 throw-rate, agent 2 pas de throw
    w._torch_pop.H = torch.randn(3, 6)
    w.agents = [{"_throw_did": True, "_throw_kill_tool": True},
                {"_throw_did": True, "_throw_kill_tool": False},
                {"_throw_did": False, "_throw_kill_tool": False}]
    w0 = w._throw_w.detach().clone()
    loss = w._learn_throw_gate()
    assert loss is not None
    assert not torch.equal(w._throw_w.detach(), w0)   # l'optimiseur a bouge les poids
    assert w._throw_kills_tool == 1                    # 1 kill-outil credite


def test_learn_throw_gate_shuffle_runs():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w.torch_throw_shuffle = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    w._torch_pop.H = torch.randn(4, 6)
    w.agents = [{"_throw_did": bool(i % 2), "_throw_kill_tool": False} for i in range(4)]
    assert w._learn_throw_gate() is not None            # bras shuffle ne crashe pas


def test_learn_throw_gate_skips_on_desync():
    import torch
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w._torch_pop = _FakePop(6)
    w._ensure_throw_gate()
    w._torch_pop.H = torch.randn(3, 6)
    w.agents = [{"_throw_did": False, "_throw_kill_tool": False}]   # B(3) != agents(1)
    assert w._learn_throw_gate() is None
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_learn_throw_gate_steps_optimizer -v`
Expected: FAIL (`AttributeError: ... has no attribute '_learn_throw_gate'`).

- [ ] **Step 3: Ajouter la méthode `_learn_throw_gate`**

Dans `src/worlds/world_1_stoneage.py`, juste après `def _maybe_learn_episode` (après ≈ ligne 987) :
```python
    def _learn_throw_gate(self):
        """REINFORCE immediat 1-pas de la tete throw-gate (B2). Recompute p (differentiable) depuis
        H cache ce tick, utilise les decisions _throw_did stockees, recompense = outcome (kill-avec-
        outil +1.0, autre throw -0.5, pas de throw 0.0). Shuffle => permute r parmi les vivants
        (permutation seed-deterministe) pour decorreler recompense/contexte. Skip propre (log, pas
        de crash) si gate OFF, pop absent, ou desync B != len(agents). Baseline = moyenne population."""
        if not (self.use_torch_inworld and self.torch_throw_gate) or self._throw_w is None:
            return None
        if self._torch_pop is None:
            return None
        import torch
        H = self._torch_pop.H.detach()
        B = H.shape[0]
        if B == 0 or B != len(self.agents):
            logger.emit("TORCH_THROW_SKIP", {"reason": "pop_desync", "tick": self._torch_tick})
            return None
        did = np.array([1.0 if a.get("_throw_did") else 0.0 for a in self.agents],
                       dtype=np.float32)
        r = np.zeros(B, dtype=np.float32)
        n_kill = 0
        for i, a in enumerate(self.agents):
            if not a.get("_throw_did"):
                r[i] = 0.0
            elif a.get("_throw_kill_tool"):
                r[i] = 1.0
                n_kill += 1
            else:
                r[i] = -0.5
        self._throw_kills_tool += n_kill
        if self.torch_throw_shuffle:
            r = r[self._throw_shuf_rng.permutation(B)]   # decorrele recompense/contexte
        ret = torch.tensor(r - float(r.mean()))
        z = H @ self._throw_w + self._throw_b
        p = torch.sigmoid(torch.clamp(z, -10.0, 10.0))
        did_t = torch.tensor(did)
        logp = did_t * torch.log(p + 1e-6) + (1 - did_t) * torch.log(1 - p + 1e-6)
        loss = -(ret * logp).mean() + self.torch_throw_antisat * p.mean() ** 2
        self._throw_opt.zero_grad()
        loss.backward()
        self._throw_opt.step()
        return float(loss.item())
```

- [ ] **Step 4: Câbler l'appel dans le bloc torch**

Dans `src/worlds/world_1_stoneage.py`, dans le bloc `if self.use_torch_inworld:` (≈ lignes 1517-1531), juste après `self._maybe_learn_episode()` (≈ ligne 1531) :
```python
            if self.torch_throw_gate:
                self._learn_throw_gate()       # REINFORCE immediat de la tete throw (B2)
```

- [ ] **Step 5: Lancer les tests**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit (path-scopé)**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(G1): throw-gate B2 - REINFORCE immediat _learn_throw_gate + shuffle + cablage"
```

---

## Task 4 : Banc `run_arm` + semis des spears

**Files:**
- Create: `tools/torch_throw_gate_inworld_ab.py`
- Test: `tests/sandbox/test_torch_throw_gate_inworld_ab.py`

**Interfaces:**
- Consumes: `Biosphere3D`, `WorldConfig`, `MambaAgent` ; attributs monde de Tasks 1-3 (`use_torch_inworld`, `torch_throw_gate`, `torch_throw_shuffle`, `_throw_kills_tool`) ; records `agent["_throw_ctx"]/["_throw_did"]` ; `has_spear` (stone_economy).
- Produces: `run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5) -> dict` avec clés `shuffle`, `seed`, `binding_gap_inworld`, `kills_with_tool`, `spear_n`, `nospear_n`, `throw_rate`. Helpers `_seed_spears(world)`, `_reseed_spears(world, rng, respawn_p)`.

- [ ] **Step 1: Écrire le smoke test**

Créer `tests/sandbox/test_torch_throw_gate_inworld_ab.py` :
```python
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_arm_smoke_keys_and_bounds():
    from tools.torch_throw_gate_inworld_ab import run_arm
    r = run_arm(shuffle=False, seed=0, ticks=40, warmup=20, n_agents=8)
    for k in ("shuffle", "seed", "binding_gap_inworld", "kills_with_tool",
              "spear_n", "nospear_n", "throw_rate"):
        assert k in r
    assert -1.0 <= r["binding_gap_inworld"] <= 1.0
    assert 0.0 <= r["throw_rate"] <= 1.0
    assert r["kills_with_tool"] >= 0
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_inworld_ab.py -v`
Expected: FAIL (`ModuleNotFoundError` / `ImportError: run_arm`).

- [ ] **Step 3: Écrire l'en-tête + helpers + `run_arm`**

Créer `tools/torch_throw_gate_inworld_ab.py` :
```python
"""B2 : câblage du throw-gate in-world (cran 2, biosphere). Banc A/B apparie ON vs SHUFFLE :
mesure binding_gap = P(throw | spear-en-inventaire) - P(throw | pas de spear) sur la VRAIE
presence, dans les deux bras. ON = tete entrainee sur la vraie recompense (kill-avec-outil) ;
SHUFFLE = recompense permutee (temoin d'artefact, joyau 169->171). Les spears sont SEMES
exogenement (decouplage du mur du craft EDR-125/127) : spawn + re-semis probabiliste quand
l'inventaire se vide -> melange dynamique spear/¬spear. Verdict via compute_ab_verdict.

Usage : python tools/torch_throw_gate_inworld_ab.py   (env: TTG_SEEDS, TTG_TICKS, TTG_WARMUP, TTG_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.environments.stone_economy import has_spear
from tools.substrate_ab import compute_ab_verdict


def _seed_spears(world):
    """Sème un spear en tete d'inventaire de chaque agent (contexte present, throwable en premier)."""
    for a in world.agents:
        a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})


def _reseed_spears(world, rng, respawn_p):
    """Re-sème un spear aux agents vivants qui n'en ont plus, avec proba respawn_p -> melange
    dynamique spear/¬spear a travers agents et temps (les deux contextes restent echantillonnes)."""
    for a in world.agents:
        if not has_spear(a["inventory"]) and rng.rand() < respawn_p:
            a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})


def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5):
    """Tourne un monde torch avec le throw-gate, sème/re-sème des spears, agrege le binding_gap
    sur la fenetre post-warmup (couples agent,tick sur la VRAIE presence-spear). CRN par seed.
    ON (shuffle=False) vs SHUFFLE (recompense permutee, contexte decorrele)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    w = Biosphere3D(WorldConfig())
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()               # repro : couper la memoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                     # cohorte fixe -> dims homogenes (114b)
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w.torch_throw_shuffle = shuffle
    rng = np.random.RandomState(seed + 100)
    _seed_spears(w)
    spear_n = spear_thr = nospear_n = nospear_thr = 0
    for t in range(ticks):
        if not w.agents:
            break
        w.step()
        _reseed_spears(w, rng, respawn_p)
        if t >= warmup:
            for a in w.agents:
                ctx = a.get("_throw_ctx")
                if ctx is None:
                    continue
                did = 1 if a.get("_throw_did") else 0
                if ctx:
                    spear_n += 1
                    spear_thr += did
                else:
                    nospear_n += 1
                    nospear_thr += did
    p_spear = (spear_thr / spear_n) if spear_n else 0.0
    p_nospear = (nospear_thr / nospear_n) if nospear_n else 0.0
    tot_n = spear_n + nospear_n
    return {"shuffle": bool(shuffle), "seed": int(seed),
            "binding_gap_inworld": float(p_spear - p_nospear),
            "kills_with_tool": int(getattr(w, "_throw_kills_tool", 0)),
            "spear_n": int(spear_n), "nospear_n": int(nospear_n),
            "throw_rate": float((spear_thr + nospear_thr) / tot_n) if tot_n else 0.0}
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_inworld_ab.py -v`
Expected: PASS (1 test). (Smoke court : 40 ticks × 8 agents, quelques secondes.)

- [ ] **Step 5: Commit (path-scopé)**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_inworld_ab.py
git commit -m "feat(G1): banc B2 - run_arm throw-gate in-world + semis spears + binding_gap"
```

---

## Task 5 : `compare` + verdict + `__main__`

**Files:**
- Modify: `tools/torch_throw_gate_inworld_ab.py` (ajouter `compare` + `__main__`)
- Test: `tests/sandbox/test_torch_throw_gate_inworld_ab.py` (test du verdict pur)

**Interfaces:**
- Consumes: `run_arm` (Task 4), `compute_ab_verdict(rows, band)` (déjà importé).
- Produces: `compare(seeds=(0,1,2,3), ticks=400, warmup=200, n_agents=32) -> dict{rows, verdict}` (diff = gap_ON − gap_SHUFFLE par seed).

- [ ] **Step 1: Écrire le test du verdict pur**

Ajouter à `tests/sandbox/test_torch_throw_gate_inworld_ab.py` :
```python
def test_verdict_pure_true_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.30}, {"diff": 0.25}, {"diff": 0.40}]   # gap ON - gap SHUFFLE > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3
```

- [ ] **Step 2: Lancer, vérifier le succès (`compute_ab_verdict` existe déjà)**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_inworld_ab.py::test_verdict_pure_true_binds_more -v`
Expected: PASS.

- [ ] **Step 3: Ajouter `compare` + `__main__`**

Ajouter à `tools/torch_throw_gate_inworld_ab.py` :
```python
def compare(seeds=(0, 1, 2, 3), ticks=400, warmup=200, n_agents=32):
    """A/B apparie ON vs SHUFFLE par seed -> verdict. diff = gap_ON - gap_SHUFFLE. diff>0 = le
    throw-gate route sur la VRAIE presence-spear et generalise (pas artefact : le shuffle est plat)."""
    rows = []
    for s in seeds:
        on = run_arm(shuffle=False, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents)
        sh = run_arm(shuffle=True, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents)
        rows.append({"seed": s, "on": on["binding_gap_inworld"], "shuffle": sh["binding_gap_inworld"],
                     "kills_on": on["kills_with_tool"],
                     "diff": on["binding_gap_inworld"] - sh["binding_gap_inworld"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TTG_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("TTG_TICKS", "400"))
    warmup = int(os.environ.get("TTG_WARMUP", "200"))
    agents = int(os.environ.get("TTG_AGENTS", "32"))
    out = compare(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_SHUF={r['shuffle']:+.3f} "
              f"diff={r['diff']:+.3f} (kills_ON={r['kills_on']})")
    print("VERDICT:", out["verdict"])
    _label = {"GRADIENT_GAGNE": "BINDING_INWORLD_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS",
              "NEUTRE": "PAS_DE_BINDING_INWORLD"}
    print("INTERPRETATION:", _label.get(out["verdict"]["verdict"], out["verdict"]["verdict"]))
```

- [ ] **Step 4: Lancer TOUT le fichier de test**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_inworld_ab.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit (path-scopé)**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_inworld_ab.py
git commit -m "feat(G1): banc B2 - compare ON vs SHUFFLE + verdict + main"
```

## PÉRIMÈTRE : ne PAS lancer le run powered dans les tâches

Les tâches font UNIQUEMENT les smokes courts. Le run powered (`python tools/torch_throw_gate_inworld_ab.py`, 400 ticks × 4 seeds × 2 bras = plusieurs minutes) est lancé par le CONTRÔLEUR après la revue finale, pas par les subagents.
