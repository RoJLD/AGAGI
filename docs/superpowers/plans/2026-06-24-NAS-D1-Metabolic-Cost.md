# Coût métabolique d'activation (NAS Axe D-1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le calcul métabolique — chaque nœud actif d'un connectome draine de l'énergie par tick — pour que la sélection de la biosphère favorise les connectomes parcimonieux.

**Architecture:** Le forward de production (`MambaBatchModel.forward`) compte les nœuds actifs (`|H|>eps`) par agent et l'écrit sur l'agent (`last_activation_cost`). Le résolveur d'énergie du monde (`world_1_stoneage._resolve_biology`) ajoute `metabolic_cost_coef × last_activation_cost` au drain, gated par un coefficient de config dont le défaut `0.0` garantit la non-régression bit-exacte.

**Tech Stack:** Python 3, NumPy, pytest. Pas de nouvelle dépendance.

**Spec:** [`../specs/2026-06-24-NAS-D1-Metabolic-Cost-design.md`](../specs/2026-06-24-NAS-D1-Metabolic-Cost-design.md)

## Global Constraints

- **Non-régression bit-exacte** : à `metabolic_cost_coef = 0.0` (défaut), aucun terme n'est ajouté au drain — comportement identique au baseline. Garanti par un garde `if coef > 0.0`.
- **1 variable (Commandement 15)** : `metabolic_cost_coef` est la *seule* variable d'expérience. Le seuil d'activité `eps` est une **constante de design** = `0.1` (attribut de classe `MambaBatchModel.METABOLIC_ACTIVE_EPS`), pas un knob d'expérience. *(Déviation mineure vs spec §4 : on n'ajoute PAS `config.metabolic_active_eps` — YAGNI ; eps reste un attribut de classe modifiable.)*
- **Métrique** = comptage de nœuds actifs : `active_count = |{ i : |H_i| > eps }|` (validé au brainstorm).
- **Git** : commits **path-scoped** (`git add` avec chemins explicites, jamais `-A`/`.`) — sessions parallèles sur le même tree. Ne pas committer sans le feu vert de robla.
- `H` est post-`tanh` ∈ [-1, 1] ; le padding du batch (`max_N`) est à 0, donc < `eps`, donc jamais compté.

---

### Task 1: Config — coefficient métabolique gated

**Files:**
- Modify: `src/environments/config.py:70` (après `base_metabolism`/`forage_payoff`)
- Test: `tests/sandbox/test_metabolic_cost.py` (Create)

**Interfaces:**
- Consumes: rien.
- Produces: `WorldConfig.metabolic_cost_coef: float` (défaut `0.0`), lu par la Task 3.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_metabolic_cost.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.environments.config import WorldConfig


def test_metabolic_cost_coef_defaults_to_zero():
    # Non-régression : par défaut, aucun coût métabolique (comportement historique).
    config = WorldConfig()
    assert config.metabolic_cost_coef == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py::test_metabolic_cost_coef_defaults_to_zero -v`
Expected: FAIL avec `AttributeError: 'WorldConfig' object has no attribute 'metabolic_cost_coef'`

- [ ] **Step 3: Add the config field**

Dans `src/environments/config.py`, juste après la ligne `forage_payoff: float = 1.0` (`:71`) :

```python
    # NAS Axe D-1 (coût métabolique d'activation) : énergie drainée par nœud actif/tick.
    # 0.0 = off (non-régression bit-exacte). Seule variable d'expérience ; sweep typique 0 -> 0.01.
    metabolic_cost_coef: float = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py::test_metabolic_cost_coef_defaults_to_zero -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/environments/config.py tests/sandbox/test_metabolic_cost.py
git commit -m "feat(NAS-D1): config metabolic_cost_coef gated (defaut 0.0, non-regression)"
```

---

### Task 2: Comptage des nœuds actifs dans le forward

**Files:**
- Modify: `src/agents/mamba_agent.py` (helper module-level ; attr de classe `MambaBatchModel.METABOLIC_ACTIVE_EPS` ; `MambaAgent.__init__:36` ; `MambaBatchModel.forward:572` ; boucle write-back `:645-651`)
- Test: `tests/sandbox/test_metabolic_cost.py` (Modify)

**Interfaces:**
- Consumes: `self.H_prev_batch` (B, max_N) — état caché final du tick, assigné à `mamba_agent.py:572`.
- Produces:
  - `count_active_nodes(H: np.ndarray, eps: float) -> np.ndarray` — fonction module-level, `H (B,N)` → `(B,)` comptes int.
  - `MambaAgent.last_activation_cost: int` — nb de nœuds actifs au dernier forward (0 si jamais appelé).
  - `MambaBatchModel.activation_cost_batch: np.ndarray (B,)` et `MambaBatchModel.METABOLIC_ACTIVE_EPS: float = 0.1`.

- [ ] **Step 1: Write the failing test (helper + comptage paddé)**

Ajouter dans `tests/sandbox/test_metabolic_cost.py` :

```python
import numpy as np
from src.agents.mamba_agent import count_active_nodes, MambaAgent, MambaBatchModel


def test_count_active_nodes_ignores_subeps_and_padding():
    # 3 nœuds actifs (>0.1), le reste sous le seuil (padding/zéros) -> compte = 3.
    H = np.array([[0.5, -0.9, 0.2, 0.05, 0.0, 0.0]], dtype=np.float32)
    counts = count_active_nodes(H, eps=0.1)
    assert counts.tolist() == [3]


def test_last_activation_cost_set_after_forward():
    np.random.seed(0)
    a = MambaAgent()
    assert a.last_activation_cost == 0  # init avant tout forward
    model = MambaBatchModel([a])
    I = a.genome.num_inputs
    model.forward(np.ones((1, I), dtype=np.float32))
    N = a.genome.num_nodes
    assert isinstance(a.last_activation_cost, int)
    assert 0 <= a.last_activation_cost <= N
    # Cohérence avec le comptage direct sur l'état final.
    expected = int(count_active_nodes(model.H_prev_batch, MambaBatchModel.METABOLIC_ACTIVE_EPS)[0])
    assert a.last_activation_cost == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py -v -k "count_active or last_activation"`
Expected: FAIL avec `ImportError: cannot import name 'count_active_nodes'`

- [ ] **Step 3a: Add the module-level helper**

En haut de `src/agents/mamba_agent.py` (après les `import numpy as np`, avant `class MambaAgent`) :

```python
def count_active_nodes(H, eps):
    """Nb de nœuds dont l'activation dépasse eps, par ligne du batch. H (B,N) -> (B,) int.
    Le padding du batch (zéros) est < eps donc non compté. NAS Axe D-1."""
    return np.sum(np.abs(H) > eps, axis=1).astype(int)
```

- [ ] **Step 3b: Init `last_activation_cost` sur l'agent**

Dans `MambaAgent.__init__`, juste après `self.predictor_head = None` (`:36`) :

```python
        self.last_activation_cost = 0  # NAS Axe D-1 : nb de nœuds actifs au dernier forward
```

- [ ] **Step 3c: Add the class attribute eps**

Dans `class MambaBatchModel`, à côté des attributs de classe `ABLATE_THRESHOLDS` / `ABLATE_ROUTER` :

```python
    METABOLIC_ACTIVE_EPS = 0.1  # NAS Axe D-1 : seuil |H_i|>eps pour compter un nœud "actif"
```

- [ ] **Step 3d: Compute the batch cost in forward**

Dans `MambaBatchModel.forward`, juste après `self.H_prev_batch = H` (`:572`) :

```python
        # NAS Axe D-1 : coût d'activation = nb de nœuds actifs ce tick (lu par _resolve_biology).
        self.activation_cost_batch = count_active_nodes(self.H_prev_batch, MambaBatchModel.METABOLIC_ACTIVE_EPS)
```

- [ ] **Step 3e: Write the cost back onto each agent**

Dans la boucle de write-back `for i, a in enumerate(self.agents):` (`:645`), ajouter une ligne dans le corps (ex. après `a.H_prev[0] = self.H_prev_batch[i, map_idx]`) :

```python
            a.last_activation_cost = int(self.activation_cost_batch[i])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py -v -k "count_active or last_activation"`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the wired-genes regression to confirm no breakage**

Run: `python -m pytest tests/sandbox/test_wired_genes.py -v`
Expected: PASS (3 tests) — le forward n'a pas changé de comportement, juste ajouté une mesure.

- [ ] **Step 6: Commit**

```bash
git add src/agents/mamba_agent.py tests/sandbox/test_metabolic_cost.py
git commit -m "feat(NAS-D1): compte les noeuds actifs par tick (last_activation_cost)"
```

---

### Task 3: Appliquer le drain métabolique dans le monde

**Files:**
- Modify: `src/worlds/world_1_stoneage.py:617` (dans `_resolve_biology`, après le calcul de `drain`, AVANT les modulateurs nuit/feu `:621`)
- Test: `tests/sandbox/test_metabolic_cost.py` (Modify)

**Interfaces:**
- Consumes: `WorldConfig.metabolic_cost_coef` (Task 1) ; `agent["model"].last_activation_cost` (Task 2).
- Produces: rien (effet de bord sur `agent["energy"]`).

- [ ] **Step 1: Write the failing tests (gating + effet additif)**

Ajouter dans `tests/sandbox/test_metabolic_cost.py` :

```python
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def _fresh_world(coef, activation_cost):
    """Monde déterministe + 1 agent à (5,5), proies/items vidés, coût d'activation forcé."""
    np.random.seed(0)
    config = WorldConfig()
    config.metabolic_cost_coef = coef
    world = Biosphere3D(config=config)
    agent = MambaAgent(num_inputs=config.agent.num_inputs)
    world.add_agent(agent, x=5, y=5, z=0, energy=50.0)
    world.preys.clear()
    world.items.clear()
    world.agents[0]["model"].last_activation_cost = activation_cost
    return world


def _drain_once(world):
    a = world.agents[0]
    before = a["energy"]
    np.random.seed(123)  # fige toute aléa interne de _resolve_biology
    logits = np.zeros(world.config.agent.num_outputs, dtype=np.float32)
    world._resolve_biology(a, action=4, logits=logits)
    return before - a["energy"]


def test_coef_zero_ignores_activation_cost():
    # Gating : à coef=0, un coût d'activation énorme ne change RIEN (non-régression).
    drain_no_cost = _drain_once(_fresh_world(coef=0.0, activation_cost=0))
    drain_big_cost = _drain_once(_fresh_world(coef=0.0, activation_cost=1000))
    assert abs(drain_big_cost - drain_no_cost) < 1e-6


def test_coef_positive_adds_proportional_drain():
    # À coef>0, le drain augmente de coef * last_activation_cost.
    drain_0 = _drain_once(_fresh_world(coef=0.01, activation_cost=0))
    drain_10 = _drain_once(_fresh_world(coef=0.01, activation_cost=10))
    assert abs((drain_10 - drain_0) - 0.01 * 10) < 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py -v -k "coef_zero or coef_positive"`
Expected: FAIL — `test_coef_positive_adds_proportional_drain` échoue (drain identique : terme pas encore ajouté). *(Note : `test_coef_zero` peut déjà passer ; c'est attendu, c'est le garde-fou.)*

- [ ] **Step 3: Add the metabolic drain term**

Dans `src/worlds/world_1_stoneage.py`, dans `_resolve_biology`, juste après la ligne `drain = getattr(self.config, "base_metabolism", 1.0) * agent["model"].phenotype_energy_drain` (`:617`) et AVANT le bloc `# EXP-9 : Thermodynamique & Nuit` (`:619`) :

```python
        # NAS Axe D-1 : coût métabolique d'activation (gated). Placé avant la modulation nuit/feu
        # pour que "penser" coûte aussi plus cher la nuit (cohérence thermodynamique).
        coef = getattr(self.config, "metabolic_cost_coef", 0.0)
        if coef > 0.0:
            drain += coef * getattr(agent["model"], "last_activation_cost", 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py -v -k "coef_zero or coef_positive"`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full new test module + a biosphere smoke test**

Run: `python -m pytest tests/sandbox/test_metabolic_cost.py tests/sandbox/test_exp9_fire.py -v`
Expected: PASS (tous) — la modulation nuit/feu existante n'est pas cassée.

- [ ] **Step 6: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_metabolic_cost.py
git commit -m "feat(NAS-D1): drain metabolique = coef x noeuds actifs dans _resolve_biology"
```

---

## Self-Review

**1. Spec coverage :**
- Spec §2 métrique=comptage + eps 0.1 → Task 2 (`count_active_nodes`, `METABOLIC_ACTIVE_EPS=0.1`). ✓
- Spec §2 gating coef défaut 0.0 → Task 1 + garde `if coef>0.0` Task 3. ✓
- Spec §3 touche 1 (forward) → Task 2 ; touche 2 (`_resolve_biology`, avant nuit/feu) → Task 3. ✓
- Spec §4 config : `metabolic_cost_coef` livré (Task 1). **`metabolic_active_eps` non livré** — déviation assumée (Global Constraints : eps = constante de design, attribut de classe ; préserve le 1-variable). ✓ (documenté)
- Spec §5 non-régression bit-exacte → `test_coef_zero_ignores_activation_cost` + garde. ✓
- Spec §8 tests : (1) coef=0 identique → Task 3 t1 ; (2) drain ∝ count → Task 3 t2 ; (3) comptage paddé → Task 2 t1 ; (5) `last_activation_cost` set → Task 2 t2. **Test §8.4 (« sparse survit plus longtemps »)** non implémenté unitairement — c'est une propriété **émergente multi-tick** qui relève du protocole de mesure X2 (spec §6), pas d'un test unitaire ; couverte par l'expérience, hors plan d'implémentation. ✓ (justifié)

**2. Placeholder scan :** aucun TBD/TODO ; tout le code des steps est concret. ✓

**3. Type consistency :** `count_active_nodes(H, eps) -> (B,) int` utilisé identiquement en Task 2 (def) et tests ; `last_activation_cost: int` posé en Task 2, lu en Task 3 ; `metabolic_cost_coef: float` posé en Task 1, lu en Task 3. ✓

---

## Validation finale (post-implémentation, hors tâches)

Après les 3 tâches, lancer la suite ciblée :
```bash
python -m pytest tests/sandbox/test_metabolic_cost.py tests/sandbox/test_wired_genes.py tests/sandbox/test_exp9_fire.py -v
```
Puis (optionnel, hors plan) cabler une expérience X2 appariée multi-seed balayant `metabolic_cost_coef` (cf. spec §6) pour mesurer le ratio d'efficacité — c'est l'étape *science* qui valide ou réfute D1.
