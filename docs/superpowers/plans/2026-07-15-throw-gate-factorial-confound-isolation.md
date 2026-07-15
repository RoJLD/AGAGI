# Banc factoriel 2⁴ — isolation des confounds du binding in-world — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isoler par un factoriel complet 2⁴ les 4 confounds nommés par EDR-176 (consommation, poids-portage, densité-payoff, crédit marginal-vs-conditionnel) et trancher si la cellule tout-propre fait émerger le binding in-world du throw-gate.

**Architecture:** Trois flags monde (`torch_throw_no_consume`, `torch_throw_weightless`, `torch_throw_conditional_credit`) défaut OFF, chacun implémenté via une petite méthode pure et testable (`_maybe_reseed_spear`, `_carry_weight`, `_throw_advantage`) gated par `torch_throw_gate`. Le banc `tools/torch_throw_gate_inworld_ab.py` gagne 3 params `run_arm` + une fonction `compare_factorial` (16 cellules) + un helper pur `_factorial_effects` (effets principaux + interactions). Le 4ᵉ facteur (densité) est piloté par le knob banc existant `prey_count`.

**Tech Stack:** Python 3, numpy, torch (REINFORCE 1-pas), pytest. Pur numpy/torch dans le substrat, aucune dépendance nouvelle.

## Global Constraints

- Les 3 flags monde default `False` ⇒ comportement identique à l'actuel (non-régressif) ; actifs seulement si `torch_throw_gate` (lui-même default `False`).
- **Zéro modification de `src/backend_torch.py`** ni de `compute_ab_verdict` (`tools/substrate_ab.py`, partagé, garde-fou puissance).
- Régime du banc factoriel (couche-1 neutralisée, non-biaisé) : `penalty=0.0, antisat=0.3, night=False, energy=250.0, base_metabolism=0.05, forage_payoff=3.0, respawn_p=0.06, spear_weight=2.0` — seuls les 4 facteurs varient.
- Densité : `prey_sparse = 15`, `prey_dense = 300`.
- Cellule-0 (tout-propre) = `(no_consume, weightless, dense, conditional_credit) = (True, True, True, True)`.
- Commits **path-scopés** (arbre partagé, sessions parallèles). Travail dans le worktree `.worktrees/throw-gate-factorial` (branche `chantier/throw-gate-factorial`, basée sur `chantier/throw-gate-rp-sweep`, PR #162 amont).
- Isolation du signal dans les tests de crédit : `torch_throw_antisat = 0.0` (sinon Adam sature en signe au 1er pas).

---

### Task 1: F1 — flag `torch_throw_no_consume` + reseed du spear post-throw

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (init ~ligne 69 ; nouvelle méthode `_maybe_reseed_spear` ; appel après ligne 1435)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: rien (premier facteur).
- Produces: `self.torch_throw_no_consume` (bool, default False) ; `self._maybe_reseed_spear(agent: dict, thrown_item: dict) -> None`.

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `tests/sandbox/test_torch_throw_gate_world.py` :

```python
def test_no_consume_default_and_reseed():
    """F1 (EDR-177) : torch_throw_no_consume reseed un Spear apres un throw de Spear -> le contexte
    spear PERSISTE a travers le throw (sinon la consommation gonfle P(throw|¬spear), EDR-174).
    Defaut OFF = non-regressif (aucun reseed)."""
    assert _fresh_world().torch_throw_no_consume is False          # defaut retro-compatible

    # OFF : pas de reseed, l'inventaire reste vide apres un throw de spear
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    agent = {"inventory": []}
    w._maybe_reseed_spear(agent, {"type": "Spear", "weight": 2.0})
    assert agent["inventory"] == []                                # OFF => no-op

    # ON : reseed d'un Spear en tete d'inventaire
    w.torch_throw_no_consume = True
    w._maybe_reseed_spear(agent, {"type": "Spear", "weight": 2.0})
    assert len(agent["inventory"]) == 1 and agent["inventory"][0]["type"] == "Spear"

    # ON mais item non-Spear (ex. Wood) => pas de reseed
    agent2 = {"inventory": []}
    w._maybe_reseed_spear(agent2, {"type": "Wood", "weight": 1.0})
    assert agent2["inventory"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_no_consume_default_and_reseed -v`
Expected: FAIL avec `AttributeError: 'Biosphere3D' object has no attribute 'torch_throw_no_consume'` (puis `_maybe_reseed_spear` manquante).

- [ ] **Step 3: Write minimal implementation**

3a. Init : dans `src/worlds/world_1_stoneage.py`, après la ligne `self.torch_throw_aim_radius = 5.0` et son commentaire (ligne 69), avant `self._throw_w = None` (ligne 70), insérer :

```python
        self.torch_throw_no_consume = False  # F1 (EDR-177) : reseed spear post-throw => contexte persiste
```

3b. Méthode : ajouter cette méthode juste avant `def _learn_throw_gate(self):` (ligne 1065) :

```python
    def _maybe_reseed_spear(self, agent, thrown_item):
        """F1 (EDR-177) : si torch_throw_no_consume (gate ON) et un Spear vient d'etre lance, re-insere
        un Spear en tete d'inventaire -> le contexte-spear PERSISTE a travers le throw. Sinon la
        consommation met l'agent en ¬spear et gonfle mecaniquement P(throw|¬spear) (anti-bind, EDR-174).
        No-op si flag OFF ou item non-Spear."""
        if (self.use_torch_inworld and self.torch_throw_gate
                and self.torch_throw_no_consume and isinstance(thrown_item, dict)
                and thrown_item.get("type") == "Spear"):
            agent["inventory"].insert(0, {"type": "Spear", "weight": 2.0})
```

3c. Appel : dans le bloc balistique, après le bloc `if not is_fueled: self.items.append(thrown_item)` (lignes 1434-1435), insérer l'appel :

```python
                if not is_fueled:
                    self.items.append(thrown_item)
                self._maybe_reseed_spear(agent, thrown_item)   # F1 (no-op si flag OFF)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_no_consume_default_and_reseed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(BIND): F1 torch_throw_no_consume — reseed spear post-throw (EDR-177 factoriel)"
```

---

### Task 2: F2 — flag `torch_throw_weightless` + découplage portage/dégâts

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (init ~ligne 69 ; nouvelle méthode `_carry_weight` ; remplacement ligne 729)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: rien (indépendant de F1).
- Produces: `self.torch_throw_weightless` (bool, default False) ; `self._carry_weight(inventory: list) -> float`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_torch_throw_gate_world.py` :

```python
def test_weightless_default_and_carry_decoupling():
    """F2 (EDR-177) : torch_throw_weightless exempte le Spear du COUT DE PORTAGE (detresse energetique
    = contexte-spear confondu au cout), SANS toucher les degats du throw (qui lisent le poids reel).
    Defaut OFF = non-regressif."""
    assert _fresh_world().torch_throw_weightless is False          # defaut retro-compatible

    inv = [{"type": "Spear", "weight": 2.0}, {"type": "Wood", "weight": 1.0}]

    # OFF : le Spear compte dans le portage -> 2.0 + 1.0 = 3.0
    w = _fresh_world()
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    assert w._carry_weight(inv) == 3.0

    # ON : le Spear est exempte -> seul le Wood compte = 1.0
    w.torch_throw_weightless = True
    assert w._carry_weight(inv) == 1.0

    # ON mais gate OFF -> pas d'exemption (garde torch_throw_gate)
    w.torch_throw_gate = False
    assert w._carry_weight(inv) == 3.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_weightless_default_and_carry_decoupling -v`
Expected: FAIL avec `AttributeError: ... torch_throw_weightless` (puis `_carry_weight` manquante).

- [ ] **Step 3: Write minimal implementation**

3a. Init : après la ligne ajoutée en Task 1 (`self.torch_throw_no_consume = False`), insérer :

```python
        self.torch_throw_weightless = False  # F2 (EDR-177) : Spear exempte du cout de portage (degats gardes)
```

3b. Méthode : ajouter juste avant `def _maybe_reseed_spear(self, agent, thrown_item):` :

```python
    def _carry_weight(self, inventory):
        """Somme des poids portes (cout de portage = carry_weight * 0.5 energie/tick). F2 (EDR-177) : si
        torch_throw_weightless (gate ON), le Spear est EXEMPTE du portage -> decouple la detresse-portage
        des degats du throw (qui lisent thrown_item['weight'] reel, inchange). No-op si flag OFF."""
        wl = self.use_torch_inworld and self.torch_throw_gate and self.torch_throw_weightless
        return sum(
            i.get("weight", 1.0) if isinstance(i, dict) else 1.0
            for i in inventory
            if not (wl and isinstance(i, dict) and i.get("type") == "Spear")
        )
```

3c. Remplacement : à la ligne 729, remplacer :

```python
        carry_weight = sum(i.get("weight", 1.0) if isinstance(i, dict) else 1.0 for i in agent["inventory"])
```

par :

```python
        carry_weight = self._carry_weight(agent["inventory"])
```

(La ligne 730 `agent["energy"] -= carry_weight * 0.5` reste inchangée. Les dégâts ligne ~1438 `damage = energy_spent * weight` restent inchangés : `weight` vient de `thrown_item`, pas de ce calcul.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_weightless_default_and_carry_decoupling -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(BIND): F2 torch_throw_weightless — decouple portage/degats (EDR-177 factoriel)"
```

---

### Task 3: F4 — flag `torch_throw_conditional_credit` + baseline par contexte

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (init ~ligne 69 ; nouvelle méthode `_throw_advantage` ; remplacement ligne 1101 dans `_learn_throw_gate`)
- Test: `tests/sandbox/test_torch_throw_gate_world.py`

**Interfaces:**
- Consumes: `_throw_ctx` par agent (déjà posé ligne 1276 quand gate ON).
- Produces: `self.torch_throw_conditional_credit` (bool, default False) ; `self._throw_advantage(r: np.ndarray, ctx: np.ndarray) -> np.ndarray`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_torch_throw_gate_world.py` :

```python
def test_throw_advantage_marginal_vs_conditional():
    """F4 (EDR-177) : _throw_advantage centre les recompenses. Marginal (defaut) = r - moyenne globale.
    Conditionnel (torch_throw_conditional_credit) = baseline PAR GROUPE de contexte -> retire la
    difference ENTRE contextes (le marginal 'throw+spear paie'), ne garde que la variation INTRA-contexte
    (le contingent means->ends). Cas ou spear-agents killent, ¬spear non : le conditionnel aplatit."""
    r = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
    ctx = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)         # 2 spear (r=1), 2 ¬spear (r=0)

    w = _fresh_world()
    w.torch_throw_conditional_credit = False
    assert np.allclose(w._throw_advantage(r, ctx), np.array([0.5, 0.5, -0.5, -0.5]))   # marginal

    w.torch_throw_conditional_credit = True
    assert np.allclose(w._throw_advantage(r, ctx), np.array([0.0, 0.0, 0.0, 0.0]))     # conditionnel : plat


def test_conditional_credit_changes_learn_update():
    """F4 bout-en-bout : a H/init/agents identiques (mais _throw_ctx mixtes), le credit conditionnel DOIT
    produire un update d'optimiseur different du marginal."""
    import torch

    def _run(conditional):
        w = _fresh_world()
        w.use_torch_inworld = True
        w.torch_throw_gate = True
        w.torch_throw_conditional_credit = conditional
        w.torch_throw_antisat = 0.0        # isole le signal (cf. tests penalty/shaping)
        w._torch_pop = _FakePop(6)
        w._ensure_throw_gate()
        w._torch_pop.H = torch.arange(18, dtype=torch.float32).reshape(3, 6)
        w.agents = [{"_throw_did": True, "_throw_kill_tool": True, "_throw_ctx": True},
                    {"_throw_did": True, "_throw_kill_tool": False, "_throw_ctx": True},
                    {"_throw_did": True, "_throw_kill_tool": False, "_throw_ctx": False}]
        w._learn_throw_gate()
        return w._throw_w.detach().clone()

    assert _fresh_world().torch_throw_conditional_credit is False   # defaut retro-compatible
    assert not torch.allclose(_run(False), _run(True))            # le credit conditionnel change l'update
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py::test_throw_advantage_marginal_vs_conditional tests/sandbox/test_torch_throw_gate_world.py::test_conditional_credit_changes_learn_update -v`
Expected: FAIL avec `AttributeError: ... torch_throw_conditional_credit` (puis `_throw_advantage` manquante).

- [ ] **Step 3: Write minimal implementation**

3a. Init : après la ligne ajoutée en Task 2 (`self.torch_throw_weightless = False`), insérer :

```python
        self.torch_throw_conditional_credit = False  # F4 (EDR-177) : baseline REINFORCE par contexte spear/¬spear
```

3b. Méthode : ajouter juste avant `def _carry_weight(self, inventory):` :

```python
    def _throw_advantage(self, r, ctx):
        """Centre les recompenses REINFORCE du throw-gate. Marginal (defaut) : r - moyenne(r). Conditionnel
        (torch_throw_conditional_credit, F4/EDR-177) : baseline PAR GROUPE de contexte (spear vs ¬spear) ->
        l'avantage reflete 'throw a aide SACHANT mon contexte' (le contingent means->ends) plutot que
        'throw paie en moyenne' (le marginal, qui credite juste la correlation contexte-recompense).
        `r`, `ctx` : np.ndarray (B,) ; ctx in {0.,1.} = presence-spear par agent. Retourne np.ndarray (B,)."""
        if not self.torch_throw_conditional_credit:
            return r - float(r.mean())
        adv = r.copy()
        for grp in (0.0, 1.0):
            m = (ctx == grp)
            if m.any():
                adv[m] = r[m] - float(r[m].mean())   # baseline intra-contexte
        return adv
```

3c. Remplacement : dans `_learn_throw_gate`, à la ligne 1101, remplacer :

```python
        ret = torch.tensor(r - float(r.mean()))
```

par :

```python
        ctx = np.array([1.0 if a.get("_throw_ctx") else 0.0 for a in self.agents], dtype=np.float32)
        ret = torch.tensor(self._throw_advantage(r, ctx))   # F4 : marginal (defaut) ou conditionnel
```

(Placement APRÈS le shuffle lignes 1099-1100 : les deux bras appliquent `_throw_advantage(r_permute?, ctx_reel)` — seul le shuffle de `r` diffère entre ON/SHUFFLE, ce qui garde le témoin d'artefact valide.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py -v -k "conditional or advantage"`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/sandbox/test_torch_throw_gate_world.py
git commit -m "feat(BIND): F4 torch_throw_conditional_credit — baseline par contexte (EDR-177 factoriel)"
```

---

### Task 4: Câbler les 3 facteurs dans `run_arm`

**Files:**
- Modify: `tools/torch_throw_gate_inworld_ab.py` (signature + corps de `run_arm`, ~lignes 40-76)
- Test: `tests/sandbox/test_torch_throw_gate_factorial.py` (nouveau)

**Interfaces:**
- Consumes: `self.torch_throw_no_consume`, `self.torch_throw_weightless`, `self.torch_throw_conditional_credit` (Tasks 1-3) ; `w.config.target_prey_count` via `prey_count` (existant).
- Produces: `run_arm(..., no_consume=False, weightless=False, conditional_credit=False)` — pose les flags monde avant la boucle sim.

- [ ] **Step 1: Write the failing test**

Créer `tests/sandbox/test_torch_throw_gate_factorial.py` :

```python
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import run_arm


def test_run_arm_accepts_factorial_knobs():
    """run_arm accepte no_consume/weightless/conditional_credit et complete un run court sans crash,
    en renvoyant les cles attendues (les flags sont poses sur le monde avant la boucle)."""
    out = run_arm(shuffle=False, seed=0, ticks=6, warmup=2, n_agents=4, prey_count=15,
                  no_consume=True, weightless=True, conditional_credit=True,
                  base_metabolism=0.05, forage_payoff=3.0, energy=250.0, night=False,
                  penalty=0.0, antisat=0.3)
    assert "binding_gap_inworld" in out and "kills_with_tool" in out
    assert isinstance(out["binding_gap_inworld"], float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py::test_run_arm_accepts_factorial_knobs -v`
Expected: FAIL avec `TypeError: run_arm() got an unexpected keyword argument 'no_consume'`.

- [ ] **Step 3: Write minimal implementation**

3a. Signature : dans `tools/torch_throw_gate_inworld_ab.py`, étendre la signature de `run_arm` (lignes 40-43). Remplacer :

```python
def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
            base_metabolism=1.0, forage_payoff=1.0, penalty=-0.5, night=True,
            energy=80.0, spear_weight=2.0, shaping=False, antisat=None,
            warm_w=None, warm_b=None, lr=None, prey_count=None, prey_regen=None):
```

par :

```python
def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
            base_metabolism=1.0, forage_payoff=1.0, penalty=-0.5, night=True,
            energy=80.0, spear_weight=2.0, shaping=False, antisat=None,
            warm_w=None, warm_b=None, lr=None, prey_count=None, prey_regen=None,
            no_consume=False, weightless=False, conditional_credit=False):
```

3b. Corps : après la ligne `w.torch_throw_shaping = shaping` (ligne 71), insérer :

```python
    w.torch_throw_no_consume = no_consume            # F1 (EDR-177)
    w.torch_throw_weightless = weightless             # F2 (EDR-177)
    w.torch_throw_conditional_credit = conditional_credit  # F4 (EDR-177)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py::test_run_arm_accepts_factorial_knobs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_factorial.py
git commit -m "feat(BIND): cable les 3 facteurs F1/F2/F4 dans run_arm (EDR-177 factoriel)"
```

---

### Task 5: `compare_factorial` — driver des 16 cellules 2⁴

**Files:**
- Modify: `tools/torch_throw_gate_inworld_ab.py` (nouvelle fonction `compare_factorial`, après `compare_rp_sweep` ~ligne 316)
- Test: `tests/sandbox/test_torch_throw_gate_factorial.py`

**Interfaces:**
- Consumes: `run_arm(..., no_consume, weightless, conditional_credit, prey_count)` (Task 4) ; `compute_ab_verdict` (importé ligne 22).
- Produces: `compare_factorial(seeds=(0,1,2,3), prey_sparse=15, prey_dense=300, ticks=120, warmup=30, n_agents=30, respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0, energy=250.0, spear_weight=2.0, antisat=0.3) -> list[dict]`. Chaque cellule expose : `no_consume, weightless, dense, conditional_credit` (bool, True=propre), `prey_count`, `verdict`, `median_diff`, `median_gap_on`, `median_kills`, `median_throw`, `diffs` (list par seed), `rows`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_torch_throw_gate_factorial.py` (et étendre l'import) :

```python
from tools.torch_throw_gate_inworld_ab import run_arm, compare_factorial


def test_compare_factorial_returns_16_cells():
    """compare_factorial produit les 16 cellules 2^4 distinctes, dont la cellule-0 tout-propre
    (T,T,T,T), chacune avec verdict + diffs. Config minuscule (smoke)."""
    cells = compare_factorial(seeds=(0,), prey_sparse=15, prey_dense=30, ticks=6, warmup=2, n_agents=4)
    assert len(cells) == 16
    keys = {(c["no_consume"], c["weightless"], c["dense"], c["conditional_credit"]) for c in cells}
    assert len(keys) == 16                                    # toutes les combinaisons distinctes
    assert (True, True, True, True) in keys                   # cellule-0 (tout-propre)
    for c in cells:
        assert "verdict" in c and "median_diff" in c and isinstance(c["diffs"], list)
        assert c["prey_count"] == (30 if c["dense"] else 15)  # densite mappee sur prey_count
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py::test_compare_factorial_returns_16_cells -v`
Expected: FAIL avec `ImportError: cannot import name 'compare_factorial'`.

- [ ] **Step 3: Write minimal implementation**

Ajouter cette fonction après `compare_rp_sweep` (après la ligne 316, avant `if __name__ == "__main__":`) :

```python
def compare_factorial(seeds=(0, 1, 2, 3), prey_sparse=15, prey_dense=300, ticks=120, warmup=30,
                      n_agents=30, respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0,
                      energy=250.0, spear_weight=2.0, antisat=0.3):
    """Factoriel 2^4 (EDR-177) : isole les 4 confounds du binding in-world. Facteurs (True=propre) :
    no_consume (F1), weightless (F2), dense (F3 : prey_count=dense/sparse), conditional_credit (F4).
    Regime couche-1 neutralisee + non-biaise (penalty=0) -> seuls les 4 facteurs varient. Par cellule :
    K seeds x {ON, SHUFFLE}, diff = gap_ON - gap_SHUFFLE, verdict via compute_ab_verdict. La cellule
    tout-propre (T,T,T,T) est le test decisif : le substrat binde-t-il in-world PROPREMENT ?"""
    import itertools
    import statistics as _st
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=False,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff, energy=energy,
              spear_weight=spear_weight, penalty=0.0, antisat=antisat)
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        prey = prey_dense if dn else prey_sparse
        rows, kills, throws = [], [], []
        for s in seeds:
            on = run_arm(shuffle=False, seed=s, prey_count=prey, no_consume=nc, weightless=wl,
                         conditional_credit=cc, **kw)
            sh = run_arm(shuffle=True, seed=s, prey_count=prey, no_consume=nc, weightless=wl,
                         conditional_credit=cc, **kw)
            diff = on["binding_gap_inworld"] - sh["binding_gap_inworld"]
            rows.append({"seed": s, "on": on["binding_gap_inworld"],
                         "shuffle": sh["binding_gap_inworld"], "diff": diff})
            kills.append(on["kills_with_tool"]); throws.append(on["throw_rate"])
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn, "conditional_credit": cc,
                      "prey_count": prey, "verdict": compute_ab_verdict(rows, band=0.02),
                      "median_diff": _st.median([r["diff"] for r in rows]),
                      "median_gap_on": _st.median([r["on"] for r in rows]),
                      "median_kills": _st.median(kills), "median_throw": _st.median(throws),
                      "diffs": [r["diff"] for r in rows], "rows": rows})
    return cells
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py::test_compare_factorial_returns_16_cells -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_factorial.py
git commit -m "feat(BIND): compare_factorial — driver 16 cellules 2^4 (EDR-177)"
```

---

### Task 6: `_factorial_effects` (effets principaux + interactions) + mode CLI `factorial`

**Files:**
- Modify: `tools/torch_throw_gate_inworld_ab.py` (helper pur `_factorial_effects` après `compare_factorial` ; branche `elif ... == "factorial"` dans `__main__`)
- Test: `tests/sandbox/test_torch_throw_gate_factorial.py`

**Interfaces:**
- Consumes: la liste de cellules produite par `compare_factorial` (Task 5) — clés `no_consume, weightless, dense, conditional_credit, diffs`.
- Produces: `_factorial_effects(cells) -> {"main": {facteur: float}, "interactions": {"f×g": float}}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_torch_throw_gate_factorial.py` (et étendre l'import) :

```python
import itertools
from tools.torch_throw_gate_inworld_ab import (run_arm, compare_factorial, _factorial_effects)


def test_factorial_effects_isolates_main_effect():
    """_factorial_effects (pur) : sur 16 cellules synthetiques ou diff=+1 SSI conditional_credit propre,
    l'effet principal de conditional_credit vaut +1.0 et les 3 autres 0.0 (isolation)."""
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        diff = 1.0 if cc else 0.0
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn,
                      "conditional_credit": cc, "diffs": [diff, diff]})
    eff = _factorial_effects(cells)
    assert abs(eff["main"]["conditional_credit"] - 1.0) < 1e-9
    assert abs(eff["main"]["no_consume"]) < 1e-9
    assert abs(eff["main"]["weightless"]) < 1e-9
    assert abs(eff["main"]["dense"]) < 1e-9
    assert "no_consume×conditional_credit" in eff["interactions"]


def test_factorial_effects_detects_interaction():
    """Interaction 2-way : diff=+1 SSI (no_consume ET conditional_credit) tous deux propres (effet
    non-additif). L'interaction no_consume×conditional_credit doit etre positive et non nulle."""
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        diff = 1.0 if (nc and cc) else 0.0
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn,
                      "conditional_credit": cc, "diffs": [diff]})
    eff = _factorial_effects(cells)
    assert eff["interactions"]["no_consume×conditional_credit"] > 0.2   # interaction reelle detectee
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py -k effects -v`
Expected: FAIL avec `ImportError: cannot import name '_factorial_effects'`.

- [ ] **Step 3: Write minimal implementation**

3a. Helper : ajouter après `compare_factorial` (avant `if __name__ == "__main__":`) :

```python
def _factorial_effects(cells):
    """Effets principaux + interactions 2-way sur la carte 2^4 (EDR-177). Chaque cellule expose ses 4
    niveaux booleens (True=propre) + `diffs` (liste des diff ON-SHUFFLE par seed). Effet principal d'un
    facteur = moyenne(diffs | facteur propre) - moyenne(diffs | facteur confound), poole sur les 8
    cellules de chaque niveau. Interaction 2-way = demi-difference des effets simples croises."""
    import statistics as _st
    factors = ("no_consume", "weightless", "dense", "conditional_credit")

    def _pool(pred):
        vals = [d for c in cells if pred(c) for d in c["diffs"]]
        return _st.mean(vals) if vals else 0.0

    main = {f: _pool(lambda c, f=f: c[f]) - _pool(lambda c, f=f: not c[f]) for f in factors}
    inter = {}
    for i in range(len(factors)):
        for j in range(i + 1, len(factors)):
            f, g = factors[i], factors[j]
            both = _pool(lambda c, f=f, g=g: c[f] and c[g])
            neither = _pool(lambda c, f=f, g=g: (not c[f]) and (not c[g]))
            only_f = _pool(lambda c, f=f, g=g: c[f] and not c[g])
            only_g = _pool(lambda c, f=f, g=g: (not c[f]) and c[g])
            inter[f"{f}×{g}"] = 0.5 * ((both + neither) - (only_f + only_g))
    return {"main": main, "interactions": inter}
```

3b. Mode CLI : dans le bloc `__main__`, après la branche `elif os.environ.get("TTG_MODE") == "rpsweep":` (le bloc se termine ligne ~400), ajouter :

```python
    elif os.environ.get("TTG_MODE") == "factorial":
        ps = int(os.environ.get("TTG_PREY_SPARSE", "15"))
        pd = int(os.environ.get("TTG_PREY_DENSE", "300"))
        cells = compare_factorial(seeds=seeds, prey_sparse=ps, prey_dense=pd, ticks=ticks,
                                  warmup=warmup, n_agents=agents, respawn_p=rp,
                                  base_metabolism=bm, forage_payoff=fp, energy=en,
                                  spear_weight=sw, antisat=(asat if asat is not None else 0.3))
        _lab = {"GRADIENT_GAGNE": "BINDE", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PLAT"}

        def _tag(c):
            return ("N" if c["no_consume"] else ".") + ("W" if c["weightless"] else ".") + \
                   ("D" if c["dense"] else ".") + ("K" if c["conditional_credit"] else ".")

        for c in sorted(cells, key=lambda c: c["median_diff"], reverse=True):
            v = c["verdict"]
            print(f"[{_tag(c)}] diff={c['median_diff']:+.3f} gap_ON={c['median_gap_on']:+.3f} "
                  f"kills={c['median_kills']:.0f} throw={c['median_throw']:.2f} "
                  f"-> {v['verdict']} ({_lab.get(v['verdict'], '?')}) sign_p={v.get('sign_p')}")
        eff = _factorial_effects(cells)
        print("\nEFFETS PRINCIPAUX (diff propre - diff confound) :")
        for f, e in eff["main"].items():
            print(f"  {f:22s} {e:+.3f}")
        print("INTERACTIONS 2-way :")
        for p, e in eff["interactions"].items():
            print(f"  {p:34s} {e:+.3f}")
        c0 = next(c for c in cells if c["no_consume"] and c["weightless"] and c["dense"]
                  and c["conditional_credit"])
        v0 = c0["verdict"]
        print(f"\nCELLULE-0 (tout-propre NWDK) : diff={c0['median_diff']:+.3f} gap_ON={c0['median_gap_on']:+.3f} "
              f"-> {v0['verdict']} sign_p={v0.get('sign_p')}")
        print("CONCLUSION:", "SUBSTRAT_BINDE_IN_WORLD_PROPRE" if v0["verdict"] == "GRADIENT_GAGNE"
              else "VERROU_IN_WORLD_PLUS_PROFOND")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py -v`
Expected: PASS (tous les tests du fichier)

- [ ] **Step 5: Run the full throw-gate suite (non-régression)**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_world.py tests/sandbox/test_torch_throw_gate_factorial.py -v`
Expected: PASS (les 12 tests monde d'origine + les nouveaux tests factoriels)

- [ ] **Step 6: Commit**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_factorial.py
git commit -m "feat(BIND): _factorial_effects + mode CLI factorial (EDR-177)"
```

---

## Self-Review

**1. Spec coverage :**
- 4 facteurs → F1 (Task 1), F2 (Task 2), F3 (densité, via `prey_count` piloté par `compare_factorial` Task 5), F4 (Task 3). ✅
- `run_arm` +3 params → Task 4. ✅
- `compare_factorial` 16 cellules ON-vs-SHUFFLE → Task 5. ✅
- Effets principaux + interactions + test-titre cellule-0 → Task 6 (`_factorial_effects` + mode CLI). ✅
- Tests 3 knobs + fidélité → Tasks 1-3 (knobs), Task 5 (fidélité cellule-0 présente/structure). ✅
- Non-régression (défaut OFF, gated) → asserts de défaut dans chaque test + Task 6 Step 5 (suite complète). ✅
- Zéro modif `backend_torch.py` / `compute_ab_verdict` → aucun fichier touché ne les inclut. ✅

**2. Placeholder scan :** aucun TBD/TODO ; tout bloc de code est complet et exécutable ; commandes exactes. ✅

**3. Type consistency :** `_maybe_reseed_spear(agent, thrown_item)`, `_carry_weight(inventory)`, `_throw_advantage(r, ctx)`, `compare_factorial(...) -> list[dict]` avec clés `no_consume/weightless/dense/conditional_credit/diffs`, `_factorial_effects(cells) -> {"main","interactions"}` : noms et signatures identiques entre définition (Tasks 1-6) et usages (tests, `compare_factorial`, mode CLI). Le mapping `dense` (bool) → `prey_count` (int) est cohérent Task 5/test. ✅

## Notes d'exécution (post-plan, hors tâches)

- Après merge : lancer la carte K=8 (`TTG_MODE=factorial TTG_SEEDS=0,1,2,3,4,5,6,7`), puis confirmation K=12 sur cellule-0. Rédiger `docs/EDR/177_*.md` (verdict SUBSTRAT_BINDE_IN_WORLD_PROPRE ou VERROU_PLUS_PROFOND).
- PR future : mentionner #162 en dépendance amont.
