# FamineWorld Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `FamineWorld` — un 2ᵉ monde causalement distinct (pénurie cyclique + stockage à coût) qui partage l'I/O de stoneage, pour re-mesurer le transfert G1 sur une vraie généralisation.

**Architecture:** `FamineWorld(Biosphere3D)` hérite le contrat I/O 59/108. Distinctness dans les MÉCANIQUES ajoutées : (1) régénération de nourriture cyclique via un seam minimal `food_regen_scale` ajouté à `Biosphere3D` (gelée en famine) ; (2) stockage = cache d'inventaire avec auto-consommation à la disette, dont le COÛT est le drain de portage existant (`carry_weight × 0.5`/tick). Validation par réutilisation des portes : S2 (G0) + curriculum_transfer (G1).

**Tech Stack:** Python 3.11, numpy, pytest. Lancement Windows : `py -3`, `PYTHONIOENCODING=utf-8` pour les sorties à caractères non-ASCII.

## Global Constraints

- **Héritage moteur** : `FamineWorld(Biosphere3D)` — NE PAS réécrire le moteur ; partager l'I/O 59/108. (spec §3)
- **Distinctness = mécaniques AJOUTÉES, pas config retirée** (≠ soup). (spec §3)
- **Distinctness PROUVÉE avant tout verdict de transfert** : un non-stockeur DOIT mourir sur ≥1 cycle famine, un stockeur survit. Si le non-stockeur survit → famine trop douce, re-calibrer. (spec §7, §8.1)
- **Non-régression** : le seam `food_regen_scale` défaut 1.0 → comportement `Biosphere3D` byte-inchangé ; `WORLD_FACTORY`/`DEFAULT_LADDER`/`s2_demand.WORLDS` existants intacts (ajout additif). (spec §5)
- **Repro** : tout run powered en `deterministic=True` ; `n≥8` seeds pour un verdict (leçon EDR-116). (spec §8.3-8.4)
- **Sessions parallèles / tree partagé** : commits PATH-SCOPED (liste explicite de fichiers), jamais `git add -A`.
- **Tests** : `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest <fichier> -q` (l'autoload de plugins casse la collecte sur ce repo).

---

### Task 1: Seam de régénération `food_regen_scale` dans Biosphere3D

**Files:**
- Modify: `src/worlds/world_1_stoneage.py` (`__init__` zone des seams ~ligne 46 ; bloc régén dans `step()` ~lignes 936-965)
- Test: `tests/test_world_famine.py`

**Interfaces:**
- Produces: attribut `self.food_regen_scale: float` (défaut `1.0`) sur `Biosphere3D`. Quand `> 0`, régénération nourriture active (comportement actuel). Quand `0.0`, **aucune** nouvelle nourriture (fruits d'arbre + proies) n'apparaît ce tick.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_world_famine.py` :
```python
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def _world(deterministic=True):
    w = Biosphere3D(WorldConfig())
    # neutralise la mémoire ambiante (repro) si présente
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    return w


def test_food_regen_scale_default_is_one():
    w = _world()
    assert w.food_regen_scale == 1.0


def test_food_regen_scale_zero_freezes_food_spawn():
    w = _world()
    w.food_regen_scale = 0.0
    # force les arbres fruitiers à vouloir spawner ce tick
    for td in w.tree_data:
        if td.get("is_fruit"):
            td["cooldown"] = 0
    n_items_before = len(w.items)
    n_preys_before = len(w.preys)
    w.step()
    # aucune nouvelle nourriture (fruits) ; les proies ne regénèrent pas
    assert len(w.items) <= n_items_before
    assert len(w.preys) <= n_preys_before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: FAIL — `AttributeError: 'Biosphere3D' object has no attribute 'food_regen_scale'`

- [ ] **Step 3: Write minimal implementation**

Dans `src/worlds/world_1_stoneage.py`, `__init__`, près des autres seams (après `self.benchmark_mode = False`) :
```python
        # Seam famine (FamineWorld) : échelle de régénération de la nourriture. 1.0 = normal
        # (non-régressif). 0.0 = aucune nouvelle nourriture (fruits + proies) -> phase de famine.
        self.food_regen_scale = 1.0
```
Puis dans `step()`, gater le spawn de fruits d'arbre — englober la boucle `for idx, (tx, ty, *tz_info) in enumerate(self.trees):` :
```python
        if self.food_regen_scale > 0:
            for idx, (tx, ty, *tz_info) in enumerate(self.trees):
                ...  # corps inchangé
```
Et la régén de proies — ajouter la condition de seam :
```python
        spawned = 0
        while (not self.training_mode) and self.food_regen_scale > 0 and len(self.preys) < self.config.target_prey_count and spawned < self.prey_regen_burst:
            ...  # corps inchangé
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Non-régression du moteur existant**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/sandbox/test_s2_demand.py tests/test_curriculum_soup_wiring.py -q`
Expected: PASS (l'ajout du seam défaut 1.0 ne change rien)

- [ ] **Step 6: Commit**

```bash
git add src/worlds/world_1_stoneage.py tests/test_world_famine.py
git commit -m "feat(world): seam food_regen_scale dans Biosphere3D (defaut 1.0, non-regressif) pour FamineWorld"
```

---

### Task 2: `FamineWorld` — cycle abondance/famine

**Files:**
- Create: `src/worlds/world_famine.py`
- Test: `tests/test_world_famine.py`

**Interfaces:**
- Consumes: `Biosphere3D`, `self.food_regen_scale` (Task 1).
- Produces: `class FamineWorld(Biosphere3D)` avec `__init__(self, config=None)`, attributs `cycle_abundance:int=60`, `cycle_famine:int=40`, méthode `is_famine() -> bool` (`(self.ticks % (cycle_abundance+cycle_famine)) >= cycle_abundance`), et `step()` qui pose `self.food_regen_scale = 0.0 if self.is_famine() else 1.0` avant `super().step()`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_world_famine.py` :
```python
from src.worlds.world_famine import FamineWorld


def test_famine_phase_schedule():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 5, 3
    # ticks 0..4 = abondance ; 5..7 = famine ; 8 = abondance
    phases = []
    for _ in range(9):
        phases.append(w.is_famine())
        w.ticks += 1
    assert phases == [False, False, False, False, False, True, True, True, False]


def test_famine_sets_food_regen_scale_zero():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 2, 2
    w.ticks = 2          # entre en famine
    w.step()
    assert w.food_regen_scale == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.worlds.world_famine'`

- [ ] **Step 3: Write minimal implementation**

Créer `src/worlds/world_famine.py` :
```python
"""FamineWorld (axe causalité temporelle) — pénurie cyclique + stockage à coût.

2e monde GENUINEMENT distinct (spec 2026-06-30-FamineWorld). Hérite du moteur canonique
Biosphere3D (contrat I/O 59/108 partagé) ; la distinctness est dans les mécaniques AJOUTÉES :
régénération de nourriture cyclique (gelée en famine) + cache d'inventaire auto-consommé à la
disette, dont le coût est le drain de portage existant. Survivre exige de STOCKER pendant
l'abondance -> gratification différée, que stoneage n'exige ni n'enseigne."""
from src.worlds.world_1_stoneage import Biosphere3D


class FamineWorld(Biosphere3D):
    def __init__(self, config=None):
        super().__init__(config)
        self.cycle_abundance = 60      # ticks d'abondance (variable d'expérience)
        self.cycle_famine = 40         # ticks de famine
        self.starve_threshold = 25.0   # sous ce niveau d'énergie, auto-consommation du cache

    def is_famine(self) -> bool:
        period = self.cycle_abundance + self.cycle_famine
        return (self.ticks % period) >= self.cycle_abundance

    def step(self):
        self.food_regen_scale = 0.0 if self.is_famine() else 1.0
        super().step()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_famine.py tests/test_world_famine.py
git commit -m "feat(world): FamineWorld cycle abondance/famine (gele la regen nourriture en famine)"
```

---

### Task 3: Stockage — cache d'inventaire auto-consommé (la gratification différée)

**Files:**
- Modify: `src/worlds/world_famine.py`
- Test: `tests/test_world_famine.py`

**Interfaces:**
- Consumes: `FamineWorld` (Task 2), champs agent `agent["inventory"]` (liste d'items dict avec `type`/`weight`), `agent["energy"]`.
- Produces: dans `FamineWorld.step()`, APRÈS `super().step()`, une passe d'**auto-consommation** : pour chaque agent vivant dont `energy < self.starve_threshold`, s'il porte un item de type alimentaire (`"Fruit"`) dans `inventory`, le retirer et faire `energy += FOOD_VALUE` (constante module `FOOD_VALUE = 30.0`, bornée à un plafond de réserve). Le COÛT du stockage est le drain de portage déjà appliqué par le moteur (`carry_weight × 0.5`/tick, `world_1_stoneage.py:662`). Aucun nouvel I/O.

> Note d'implémentation (discovery) : vérifier dans `world_1_stoneage.py` comment un Fruit entre dans `inventory` (action `grab`). Si les fruits ne sont ramassables qu'en consommation immédiate, ajouter dans `FamineWorld` une règle minimale : ramasser un Fruit sur sa case le met en `inventory` (stockage) au lieu de le consommer, le moteur facturant déjà le portage. Le TEST de distinctness (Step 1) est le juge : il échoue tant que stocker ne sauve pas réellement.

- [ ] **Step 1: Write the failing test (distinctness — le garde-fou central)**

Ajouter à `tests/test_world_famine.py` :
```python
from src.worlds.world_famine import FamineWorld, FOOD_VALUE


def test_auto_consume_from_cache_when_starving():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 0, 100   # famine permanente
    # un agent affamé portant un fruit en réserve
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # l'agent a auto-consommé son fruit -> énergie remontée (malgré le drain), cache vidé
    assert all(it.get("type") != "Fruit" for it in a["inventory"])
    assert a["energy"] > e0 - 5.0   # le gain FOOD_VALUE domine le drain du tick


def test_distinctness_non_storer_dies_storer_survives_famine():
    # Deux mondes identiques, famine longue. Le non-stockeur (cache vide) meurt ;
    # le stockeur (cache plein) survit nettement plus longtemps. PROUVE la distinctness.
    def survival(with_cache):
        w = FamineWorld(WorldConfig())
        if hasattr(w, "memory_retriever"):
            w.memory_retriever.stop()
        w.cycle_abundance, w.cycle_famine = 0, 300   # famine pure (pas de regen)
        w.add_agent(_fresh_model(w), energy=60.0)
        a = w.agents[0]
        if with_cache:
            for _ in range(10):
                a["inventory"].append({"type": "Fruit", "weight": 0.5})
        t = 0
        while w.agents and t < 300:
            w.step(); t += 1
        return t
    assert survival(with_cache=True) > survival(with_cache=False) + 20
```

Helper `_fresh_model` (en tête du fichier de test, si absent) :
```python
def _fresh_model(world):
    from src.agents.mamba_agent import MambaAgent
    m = MambaAgent()
    return m
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -k "auto_consume or distinctness" -q`
Expected: FAIL — `ImportError: cannot import name 'FOOD_VALUE'` puis (après ajout) distinctness échoue tant que l'auto-consommation n'est pas câblée.

- [ ] **Step 3: Write minimal implementation**

Dans `src/worlds/world_famine.py`, ajouter la constante et la passe d'auto-consommation :
```python
FOOD_VALUE = 30.0          # énergie rendue par un fruit consommé depuis le cache
RESERVE_CAP = 150.0        # plafond d'énergie via cache (réserve > energy_max stoneage)


class FamineWorld(Biosphere3D):
    # ... __init__, is_famine inchangés ...

    def step(self):
        self.food_regen_scale = 0.0 if self.is_famine() else 1.0
        super().step()
        # Auto-consommation du cache à la disette : redemption de la gratification différée.
        for a in self.agents:
            if a["energy"] < self.starve_threshold:
                for i, it in enumerate(a["inventory"]):
                    if isinstance(it, dict) and it.get("type") == "Fruit":
                        a["inventory"].pop(i)
                        a["energy"] = min(RESERVE_CAP, a["energy"] + FOOD_VALUE)
                        break
```

> Si le test de distinctness échoue parce que les fruits ne sont jamais mis en `inventory` par le ramassage (consommation immédiate), ajouter dans `FamineWorld` la règle de stockage minimale décrite dans la note d'interface (ramasser un Fruit → `inventory`), puis re-tester. Le test est le juge.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: PASS (6 tests, dont distinctness)

- [ ] **Step 5: Commit**

```bash
git add src/worlds/world_famine.py tests/test_world_famine.py
git commit -m "feat(world): FamineWorld cache d'inventaire auto-consomme (gratification differee, distinctness prouvee)"
```

---

### Task 4: Câblage (WORLD_FACTORY + s2_demand) + I/O compat

**Files:**
- Modify: `main_curriculum.py` (`WORLD_FACTORY` ~ligne 37)
- Modify: `tools/s2_demand.py` (`WORLDS` ~ligne 109)
- Test: `tests/test_world_famine.py`

**Interfaces:**
- Consumes: `FamineWorld`.
- Produces: `WORLD_FACTORY["famine"] = FamineWorld` (curriculum/G1) et `s2_demand.WORLDS["famine"] = FamineWorld` (G0). `_prepare_world("famine", cfg)` retourne une instance ; un `MambaAgent` s'y ajoute et `step()` tourne (I/O hérité, compat).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_world_famine.py` :
```python
def test_famine_wired_into_factories():
    from main_curriculum import WORLD_FACTORY, DEFAULT_LADDER
    from tools.s2_demand import WORLDS as S2_WORLDS
    from src.worlds.world_famine import FamineWorld
    assert WORLD_FACTORY["famine"] is FamineWorld
    assert S2_WORLDS["famine"] is FamineWorld
    # non-régression
    assert DEFAULT_LADDER == ["stoneage", "agricultural", "industrial"]
    for k in ("stoneage", "soup"):
        assert k in WORLD_FACTORY


def test_famine_io_compat_with_champion_agent():
    from src.environments.config import WorldConfig
    from src.worlds.world_famine import FamineWorld
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.add_agent(_fresh_model(w), energy=80.0)
    w.step()   # ne crashe pas : obs/action hérités de stoneage
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -k "wired or io_compat" -q`
Expected: FAIL — `KeyError: 'famine'`

- [ ] **Step 3: Write minimal implementation**

Dans `main_curriculum.py`, import + entrée :
```python
from src.worlds.world_famine import FamineWorld
```
```python
WORLD_FACTORY = {
    "soup": SoupWorld,
    "stoneage": Biosphere3D,
    "agricultural": AgriculturalWorld,
    "industrial": IndustrialWorld,
    "famine": FamineWorld,
}
```
Dans `tools/s2_demand.py`, import + entrée `WORLDS` :
```python
from src.worlds.world_famine import FamineWorld
```
```python
WORLDS = {"soup": SoupWorld, "stoneage": Biosphere3D,
          "agricultural": AgriculturalWorld, "industrial": IndustrialWorld,
          "famine": FamineWorld}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_world_famine.py -q`
Expected: PASS (8 tests)

- [ ] **Step 5: Non-régression câblage**

Run: `PYTHONIOENCODING=utf-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3 -m pytest tests/test_curriculum_soup_wiring.py tests/sandbox/test_s2_demand.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add main_curriculum.py tools/s2_demand.py tests/test_world_famine.py
git commit -m "feat(world): cable FamineWorld dans WORLD_FACTORY + s2_demand (G0/G1), I/O compat"
```

---

### Task 5: Run G0 sur FamineWorld + EDR (exécution + science)

**Files:**
- Create: `docs/EDR/NNN_Famine_World_Demands_Deferred_Gratification.md` (NNN = max EDR + 1, vérifier `ls docs/EDR/`)
- Modify: `docs/SDR/G1_competence_generalizes.md` (lier l'EDR si pertinent)

**Interfaces:**
- Consumes: `tools/s2_demand.py` (FamineWorld câblé). Exécution, pas de nouveau code.

- [ ] **Step 1: Calibrer (smoke)**

Lancer un smoke court pour vérifier que la famine n'est ni triviale ni 100% létale :
```bash
PYTHONIOENCODING=utf-8 py -3 -c "from tools.s2_demand import run_s2; print(run_s2(worlds=['famine'], seed=2026, K=2, num_agents=10, max_ticks=200, with_db=False)['worlds']['famine']['verdict'])"
```
Si verdict VOID/plancher partout → ajuster `cycle_famine`/`starve_threshold`/`FOOD_VALUE` dans `world_famine.py` (variable d'expérience) et re-smoke. Cible : un régime où le champion survit, l'aléatoire meurt.

- [ ] **Step 2: Run G0 powered**

```bash
PYTHONIOENCODING=utf-8 py -3 -c "from tools.s2_demand import run_s2; run_s2(worlds=['famine'], seed=2026, with_db=False)"
```
(K via power analysis ; champion HoF requis — déjà présent). Noter verdict + Cliff δ + p_monde + censure.

- [ ] **Step 3: Consigner l'EDR**

Rédiger `docs/EDR/NNN_*.md` avec frontmatter (`id: EDR-NNN`, `type: EDR`, `gate: G1`, `tests: [SDR-G1]`, `verdict: <EXIGE|FACTICE|INCONCLUSIF>`), le protocole, les chiffres, et l'interprétation (la gratification différée est-elle évolvable ? cf. spec §10). Puis :
```bash
py -3 tools/consolidate_records.py
```
Expected: `problemes=0`, `tested_by[G1]` inclut le nouvel EDR.

- [ ] **Step 4: Commit**

```bash
git add docs/EDR/NNN_Famine_World_Demands_Deferred_Gratification.md docs/SDR/G1_competence_generalizes.md
git commit -m "feat(G1): EDR NNN — FamineWorld, la gratification differee est-elle evolvable (verdict <...>)"
```

---

## Self-Review

**1. Spec coverage** (spec §3-§11) :
- Héritage Biosphere3D + I/O compat → Task 2 + Task 4 (`test_famine_io_compat`). ✅
- Régén cyclique (seam) → Task 1 + Task 2. ✅
- Stockage à coût (cache + auto-consommation, coût = portage) → Task 3. ✅
- Distinctness PROUVÉE (non-stockeur meurt) → Task 3 (`test_distinctness_...`). ✅
- Câblage curriculum + s2 + non-régression → Task 4. ✅
- Calibrage variable d'expérience → Task 5 Step 1. ✅
- Run G0 + EDR + consolidate → Task 5. ✅
- **Hors périmètre (spec §9, attendu)** : run G1 transfert stoneage/soup→famine = **sous-chantier suivant** (après G0 famine validé) ; mondes #2-4 du programme = backlog. Noté, pas un gap.

**2. Placeholder scan** : Task 3 contient une note de *discovery* explicite (chemin grab→inventory) bornée par un test-juge (distinctness) ; ce n'est pas un placeholder vague mais une incertitude réelle du codebase recherche, avec comportement+test précis. Task 5 `NNN` = numéro EDR à résoudre au moment du commit (sessions parallèles créent des EDR — déterminer `NNN` juste avant). Pas de TODO/TBD ailleurs.

**3. Type consistency** : `food_regen_scale` (float, défaut 1.0) cohérent Task 1↔2 ; `is_famine()`/`cycle_abundance`/`cycle_famine`/`starve_threshold` cohérents Task 2↔3 ; `FOOD_VALUE`/`RESERVE_CAP` (module-level) cohérents Task 3↔tests ; `WORLD_FACTORY["famine"]`/`WORLDS["famine"]` cohérents Task 4↔tests.
