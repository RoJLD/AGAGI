# EDR 114 — Sonde borne-sup (primitive d'atteinte oracle) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si une primitive d'atteinte parfaite (oracle obstacle-aware « va sur la proie la plus proche ») ferme `p_reach` (->~1) en Lewis, tranchant le verrou navigation entre POLITIQUE apprise et MECANIQUE-monde.

**Architecture:** Flag monde `reach_oracle` (config + world) qui remplace l'action de chaque agent par un pas glouton vers la proie la plus proche avec evitement d'obstacle a 1 pas (utilise prey-dir + geometrie, tous deux observes). Puis `main_reach_oracle` mesure `p_reach` via `_measure_forage` (EDR 105, SANS evolution) sur la matrice 2x2 {oracle off/on} x {prey_speed 1.0/0.0}.

**Tech Stack:** Python, numpy, pytest. Reutilise `Biosphere3D`, `_measure_forage`, `_cfg`, `Harness`, `seed_at`, `_disable_kuzu`, `MambaAgent`.

## Global Constraints

- **Non-regression** : `reach_oracle` defaut `False` partout -> a False, aucun override, comportement byte-identique a l'actuel. Tous mondes/EDR existants inchangés.
- **Oracle obstacle-aware** : `_reach_oracle_action` choisit le 1er pas non bloque (in-bounds ET `geometry[0,ty,tx]==0`) parmi les axes vers la proie (plus grand ecart d'abord). Mapping sim : `0=N(y-1) 1=S(y+1) 2=E(x+1) 3=O(x-1)`. Sur la proie / aucune proie -> `6` (no-op ; l'attaque est par co-localisation).
- **`_measure_forage` EXIGE `trace_forage=True` ET `trace_energy_sinks=True`** (co-activer les deux, comme `main_approach`).
- **Matrice** : `oracle in (False, True)` x `speed in (1.0, 0.0)`, graines APPARIEES (`base + r*1000 + i`). Verdict porte par la cellule (oracle=True, speed=0.0).
- **Seuils verdict** : FERME si p_reach (oracle+figees) >= 0.90 ; NE FERME PAS si < 0.50 ; PARTIELLE sinon.
- **ASCII-only dans tout `print` execute** (cp1252) : `->` ASCII OK, pas de fleche unicode/accents.
- **Determinisme** : `seed_at` avant consommation RNG (gere par `_measure_forage`). Seeds : run reel 114 ; smoke 99114 ; determinisme 88114 (distincts pour ne pas ecraser la provenance).
- **`reached_raw`** (liste, non serialisable) retire de chaque agg avant `h.save` (comme `_report_approach`).
- Run reel APRES revue ; AUCUN test relancé apres (provenance — lecon EDR 107).

---

### Task 1: `reach_oracle` — config + cablage monde (oracle + override, non-regressif)

**Files:**
- Modify: `src/environments/config.py` (ajouter le champ apres `scaffold_land`, l.61)
- Modify: `src/worlds/world_1_stoneage.py` (lire en `__init__` apres le read `scaffold_land` ; methode `_reach_oracle_action` ; override apres l.1066)
- Test: `tests/sandbox/test_edr114_reach_oracle.py` (creer)

**Interfaces:**
- Consumes: `WorldConfig` (dataclass) ; `Biosphere3D(config)` (`self.config`, `self.size`, `self.geometry`, `self.preys`) ; `np` (importe).
- Produces: `WorldConfig.reach_oracle: bool = False` ; `Biosphere3D.reach_oracle` (bool) ; `Biosphere3D._reach_oracle_action(agent) -> int` ; override de `action` quand `reach_oracle` est ON.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_edr114_reach_oracle.py` :

```python
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent


def _cfg_oracle(reach_oracle=False, prey_speed_scale=0.0):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.0
    cfg.forage_payoff = 3.0
    cfg.prey_speed_scale = prey_speed_scale
    cfg.trace_forage = True
    cfg.reach_oracle = reach_oracle
    return cfg


def test_config_has_reach_oracle_default_false():
    assert WorldConfig().reach_oracle is False


def test_world_reads_reach_oracle():
    assert Biosphere3D(_cfg_oracle(reach_oracle=False)).reach_oracle is False
    assert Biosphere3D(_cfg_oracle(reach_oracle=True)).reach_oracle is True


def _oracle_action_with_prey_at(env, ax, ay, px, py):
    env.geometry[:] = 0
    env.preys = [{"x": px, "y": py, "z": 0, "type": "Lapin", "hp": 1}]
    return env._reach_oracle_action({"x": ax, "y": ay, "z": 0})


def test_reach_oracle_action_direction_and_sidestep():
    env = Biosphere3D(_cfg_oracle(reach_oracle=True))
    a = 10
    # (a) directions pures (grille libre)
    assert _oracle_action_with_prey_at(env, a, a, a + 3, a) == 2      # proie EST
    assert _oracle_action_with_prey_at(env, a, a, a - 3, a) == 3      # proie OUEST
    assert _oracle_action_with_prey_at(env, a, a, a, a + 3) == 1      # proie SUD
    assert _oracle_action_with_prey_at(env, a, a, a, a - 3) == 0      # proie NORD
    assert _oracle_action_with_prey_at(env, a, a, a, a) == 6          # meme cellule
    # (b) evitement : proie au NORD-EST (prefere EST=2), mais EST bloque -> axe secondaire NORD=0
    env.geometry[:] = 0
    env.geometry[0, a, a + 1] = 1                                     # bloque la cellule EST
    env.preys = [{"x": a + 3, "y": a - 1, "z": 0, "type": "Lapin", "hp": 1}]
    assert env._reach_oracle_action({"x": a, "y": a, "z": 0}) == 0    # sidestep vers NORD


def _run_min(env, steps):
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    for _ in range(steps):
        if not env.agents:
            break
        env.step()


def test_non_regression_determinism_at_false():
    # reach_oracle=False -> deux runs memes graines = energie totale identique (defaut inerte).
    def run():
        seed_at(555, 0)
        env = Biosphere3D(_cfg_oracle(reach_oracle=False))
        env.preys = [p for p in env.preys if p["type"] not in ("Mammouth", "Ours", "Leurre")]
        env.current_era = 1
        env.add_agent(MambaAgent(), energy=80.0)
        _run_min(env, 20)
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        return sum(p["energy"] for p in pool)
    assert run() == run()


def test_oracle_reaches_frozen_prey():
    # Verification directe que la primitive FONCTIONNE : oracle + proie figee + grille libre ->
    # l'agent atteint la proie (forage_min_dist <= 0) en ~distance Manhattan ticks.
    seed_at(606, 0)
    env = Biosphere3D(_cfg_oracle(reach_oracle=True, prey_speed_scale=0.0))
    env.geometry[:] = 0
    env.preys = []                                  # vider toutes les proies generees
    env.current_era = 1
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    env.add_agent(MambaAgent(), energy=80.0)
    ag = env.agents[0]
    ax, ay = ag["x"], ag["y"]
    px, py = min(ax + 8, env.size - 1), ay         # proie figee a ~8 cases a l'est, chemin libre
    env.preys = [{"x": px, "y": py, "z": 0, "type": "Lapin", "hp": 1}]
    dist = abs(px - ax) + abs(py - ay)
    for _ in range(dist + 10):
        if not env.agents:
            break
        env.step()
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        if any(p.get("_forage_min_dist", 9999) <= 0 for p in pool):
            break
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert any(p.get("_forage_min_dist", 9999) <= 0 for p in pool), "l'oracle doit atteindre la proie figee"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr114_reach_oracle.py -v`
Expected: FAIL — `AttributeError: 'WorldConfig' object has no attribute 'reach_oracle'` (puis `_reach_oracle_action` absent).

- [ ] **Step 3: Add the config field**

Dans `src/environments/config.py`, juste apres la ligne `scaffold_land: float = 0.0 ...` (l.61) :

```python
    reach_oracle: bool = False         # EDR114 : override l'action par une primitive d'atteinte (oracle) ; defaut False = inerte/non-regressif
```

- [ ] **Step 4: Wire the world `__init__` + add `_reach_oracle_action`**

Dans `src/worlds/world_1_stoneage.py`, juste apres la ligne `self.scaffold_land = getattr(self.config, "scaffold_land", 0.0) ...` (cablage EDR113 dans `__init__`) :

```python
        self.reach_oracle = getattr(self.config, "reach_oracle", False)   # EDR114 : oracle d'atteinte (override action)
```

Puis ajouter la methode (placement libre dans la classe, p.ex. juste avant `def get_batch_observations`) :

```python
    def _reach_oracle_action(self, agent):
        """EDR114 : primitive d'atteinte (oracle, pas d'apprentissage) -> pas glouton vers la proie la
        plus proche (Manhattan) AVEC evitement d'obstacle a 1 pas (utilise prey-dir ET geometrie, tous
        deux observes par l'agent : dn/ds/de/dw + lidar). Mapping : 0=N(y-1) 1=S(y+1) 2=E(x+1) 3=O(x-1).
        Sur la proie / aucune proie -> 6 (no-op ; l'attaque est par co-localisation)."""
        if not self.preys:
            return 6
        ax, ay = int(agent["x"]), int(agent["y"])
        dists = [abs(p["x"] - ax) + abs(p["y"] - ay) for p in self.preys]
        p = self.preys[int(np.argmin(dists))]
        dx, dy = int(p["x"]) - ax, int(p["y"]) - ay
        if dx == 0 and dy == 0:
            return 6
        ew = 2 if dx > 0 else 3
        ns = 1 if dy > 0 else 0
        if abs(dx) >= abs(dy):
            cand = ([ew] if dx != 0 else []) + ([ns] if dy != 0 else [])
        else:
            cand = ([ns] if dy != 0 else []) + ([ew] if dx != 0 else [])
        for a in cand:
            tx, ty = ax, ay
            if a == 0: ty -= 1
            elif a == 1: ty += 1
            elif a == 2: tx += 1
            elif a == 3: tx -= 1
            if 0 <= tx < self.size and 0 <= ty < self.size and self.geometry[0, ty, tx] == 0:
                return a
        return cand[0] if cand else 6
```

- [ ] **Step 5: Wire the action override**

Dans `src/worlds/world_1_stoneage.py`, remplacer la ligne (~l.1067) :

```python
            agent["last_action"] = action
```

par (inserer l'override JUSTE AVANT, apres toute la logique de politique argmax/decode_act/epsilon-greedy) :

```python
            if getattr(self, "reach_oracle", False):
                action = self._reach_oracle_action(agent)   # EDR114 : override -> primitive d'atteinte
            agent["last_action"] = action
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr114_reach_oracle.py -v`
Expected: PASS (5/5). Si `test_oracle_reaches_frozen_prey` echoue (l'agent n'atteint pas), verifier que l'override est bien place AVANT le bloc mouvement (l.1294) et que `geometry` est bien vide dans le test ; NE PAS affaiblir l'assertion.

- [ ] **Step 7: Commit**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tests/sandbox/test_edr114_reach_oracle.py
git commit -m "feat(EDR114): reach_oracle (primitive d'atteinte obstacle-aware) cable config + monde, non-regressif"
```

---

### Task 2: harnais — `_cfg` param + `_verdict_reach` + `_report_reach` + `main_reach_oracle`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (param `_cfg` ~l.35 ; ajouter les 3 fonctions apres `main_approach`)
- Test: `tests/sandbox/test_edr114_reach_oracle.py` (ajouter)

**Interfaces:**
- Consumes: `_cfg(...)` (l.35, EDR113 a deja `scaffold_land`) ; `_measure_forage(cfg, seeds, n_apex=0, max_ticks=150) -> dict{p_reach,p_cap,mean_captures,cap_lapin,cap_cerf,cap_sanglier,mean_min_dist,n_agents,reached_raw,...}` ; `Harness`, `seed_at`, `_disable_kuzu` ; `Biosphere3D.reach_oracle` (Task 1).
- Produces:
  - `_cfg(..., reach_oracle=False)` -> pose `cfg.reach_oracle = bool(reach_oracle)`.
  - `_verdict_reach(aggs) -> str` (aggs = liste `(oracle: bool, speed: float, agg: dict)`).
  - `_report_reach(h, aggs, R, n_eval, _return) -> dict|None`.
  - `main_reach_oracle(speeds=(1.0, 0.0), n_eval=8, R=1, seed=114, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_edr114_reach_oracle.py` :

```python
from tools.lewis_survival_sweep import _cfg, _verdict_reach, main_reach_oracle


def test_cfg_reach_oracle_param():
    assert _cfg(3).reach_oracle is False
    assert _cfg(3, reach_oracle=True).reach_oracle is True


def _agg(oracle, speed, p_reach):
    return (oracle, speed, {"p_reach": p_reach, "p_cap": 1.0, "mean_captures": 0.0,
                            "cap_lapin": 0.0, "cap_cerf": 0.0, "cap_sanglier": 0.0,
                            "mean_min_dist": 0.0, "n_agents": 100, "reached_raw": [1, 0]})


def test_verdict_reach_branches():
    # cellule decisive = (oracle=True, speed=0.0)
    ferme = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.40), _agg(True, 0.0, 0.95)]
    assert _verdict_reach(ferme) == "PRIMITIVE FERME"
    bloc = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.30), _agg(True, 0.0, 0.30)]
    assert _verdict_reach(bloc) == "PRIMITIVE NE FERME PAS"
    part = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.60), _agg(True, 0.0, 0.70)]
    assert _verdict_reach(part) == "PRIMITIVE PARTIELLE"


def test_main_reach_oracle_smoke_and_determinism():
    r1 = main_reach_oracle(speeds=(1.0, 0.0), n_eval=2, R=1, seed=88114, _return=True)
    assert r1["verdict"] in ("PRIMITIVE FERME", "PRIMITIVE NE FERME PAS", "PRIMITIVE PARTIELLE", "INDETERMINE")
    assert len(r1["table"]) == 4
    r2 = main_reach_oracle(speeds=(1.0, 0.0), n_eval=2, R=1, seed=88114, _return=True)
    assert r1["table"] == r2["table"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr114_reach_oracle.py -k "cfg_reach_oracle or verdict_reach or main_reach_oracle" -v`
Expected: FAIL — `TypeError: _cfg() got an unexpected keyword argument 'reach_oracle'` puis `ImportError: cannot import name '_verdict_reach'`.

- [ ] **Step 3: Add `reach_oracle` to `_cfg`**

Dans `tools/lewis_survival_sweep.py`, modifier la signature de `_cfg` (l.35-36) pour ajouter `reach_oracle=False` en fin, et poser le champ avant `return cfg` (apres `cfg.scaffold_land = ...`, l.46) :

Signature :
```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB,
         trace_forage=False, prey_speed_scale=1.0, scaffold_land=0.0, reach_oracle=False):
```
Avant `return cfg` :
```python
    cfg.reach_oracle = bool(reach_oracle)                     # EDR114
```

- [ ] **Step 4: Implement `_verdict_reach`, `_report_reach`, `main_reach_oracle`**

Ajouter dans `tools/lewis_survival_sweep.py`, apres `main_approach` :

```python
def _verdict_reach(aggs):
    """EDR114 : verdict pre-enregistre porte par la cellule (oracle=True, speed=0.0). FERME si son
    p_reach>=0.90 (le monde permet d'atteindre une cible immobile -> mur = POLITIQUE/substrat) ;
    NE FERME PAS si <0.50 (mecanique-monde cassee) ; PARTIELLE sinon. aggs = liste (oracle, speed, agg)."""
    cell = next((a for o, s, a in aggs if o is True and s == 0.0), None)
    if cell is None:
        return "INDETERMINE"
    pr = cell["p_reach"]
    if pr >= 0.90:
        return "PRIMITIVE FERME"
    if pr < 0.50:
        return "PRIMITIVE NE FERME PAS"
    return "PRIMITIVE PARTIELLE"


def _report_reach(h, aggs, R, n_eval, _return):
    """Table 2x2 (1 ligne/cellule : oracle, speed, p_reach, p_cap, min_dist, n) + lecture cinematique
    (oracle figees vs mobiles) + verdict pre-enregistre + provenance. reached_raw retire avant save.
    Tout ASCII (cp1252). aggs = liste (oracle, speed, agg)."""
    verdict = _verdict_reach(aggs)
    print("\n=== EDR114 borne-sup primitive d'atteinte (verdict sur oracle=True, figees) ===")
    print("  oracle | speed | p_reach p_cap | min_dist | n")
    for o, s, a in aggs:
        print(f"  {str(bool(o)):<6} | {s:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['mean_min_dist']:8.2f} | {a['n_agents']}")
    orc_frozen = next((a['p_reach'] for o, s, a in aggs if o is True and s == 0.0), None)
    orc_moving = next((a['p_reach'] for o, s, a in aggs if o is True and s == 1.0), None)
    if orc_frozen is not None and orc_moving is not None:
        print(f"  cinematique (oracle) : figees={orc_frozen:.2f} vs mobiles={orc_moving:.2f} "
              f"(delta={orc_frozen - orc_moving:+.2f})")
    print("=== VERDICT (pre-enregistre, porte par oracle+figees) ===")
    print(f"  -> {verdict}")
    table = [{"oracle": bool(o), "speed": s, **{k: v for k, v in a.items() if k != "reached_raw"}}
             for o, s, a in aggs]
    h.save({"knob": "reach_oracle x prey_speed_scale", "R": R, "n_eval": n_eval,
            "verdict": verdict, "table": table})
    if _return:
        return {"verdict": verdict, "table": table, "R": R, "n_eval": n_eval}


def main_reach_oracle(speeds=(1.0, 0.0), n_eval=8, R=1, seed=114, _return=False):
    """EDR 114 : sonde borne-sup. Mesure p_reach sous l'oracle d'atteinte (override action) vs politique
    apprise, x {proies mobiles, figees}, a N_APEX=0/metab=0/forage_payoff=3, SANS evolution (replicas
    via _measure_forage). Verdict PRIMITIVE FERME/NE FERME PAS/PARTIELLE (porte par oracle+figees)."""
    with Harness(seed=seed, name="lewis_reach_oracle", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR114 : borne-sup oracle, speeds={speeds}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]   # memes seeds/cellule
        prog = h.progress(2 * len(speeds), label="cellules (oracle x speed)")
        aggs = []
        for oracle in (False, True):
            for s in speeds:
                cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                           prey_speed_scale=s, reach_oracle=oracle)
                aggs.append((oracle, s, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
                prog.update()
        return _report_reach(h, aggs, R, n_eval, _return)
```

- [ ] **Step 5: Run the full EDR 114 test file**

Run: `python -m pytest tests/sandbox/test_edr114_reach_oracle.py -v`
Expected: PASS (tous : 5 Task1 + 3 Task2 = 8). Le smoke `main_reach_oracle` (deux runs 4 cellules x n_eval=2) est un peu lent (~1-2 min, pas d'evolution) mais doit passer et montrer `table` identiques.

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr114_reach_oracle.py
git commit -m "feat(EDR114): _cfg reach_oracle param + _verdict_reach + _report + main_reach_oracle (matrice 2x2)"
```

---

### Task 3: Run reel + doc EDR + memoire (controleur, APRES revue de code)

> **Non-TDD.** Execute par le controleur une fois Tasks 1-2 revues. AUCUN test relancé apres le run reel.

**Files:**
- Create: `docs/EDR/114_<verdict-slug>.md` (titre = verdict, ASCII)
- Modify (memoire, hors worktree) : `lewis-energy-economy-wall.md` + `MEMORY.md`

- [ ] **Step 1: Lancer le run reel (seed 114, 4 cellules, n_eval=8)**

Run: `python -c "from tools.lewis_survival_sweep import main_reach_oracle; main_reach_oracle()"`
Expected: table 4 cellules (oracle False/True x speed 1.0/0.0), lecture cinematique, verdict. Capturer le stdout integral (provenance ; `results/lewis_reach_oracle_114.json` gitignore). **Controle** : les cellules oracle=False doivent reproduire ~0.36 (mobiles) / ~0.21 (figees) ; sinon investiguer le harnais avant d'interpreter.

- [ ] **Step 2: Re-lancer une fois pour confirmer le determinisme**

Run: meme commande. Expected: table identique a Step 1. Si divergence -> investiguer (memory_retriever ambiant ?) avant de rediger.

- [ ] **Step 3: Rediger le doc EDR**

Creer `docs/EDR/114_<slug>.md` selon le moule 113 : contexte (tous leviers-monde elimines, question pendante = borne-sup jamais testee), methode (oracle obstacle-aware, matrice 2x2, sans evolution), TABLE 4 cellules, lecture cinematique, VERDICT pre-enregistre atteint, ce qu'il implique (FERME -> substrat confirme par exclusion / NE FERME PAS -> rouvre le monde), caveats (oracle 1-pas pas full pathfinding ; R=1 ; genome inerte sous oracle), suite. Titre = le verdict (slug ASCII).

- [ ] **Step 4: Mettre a jour la memoire**

Mettre a jour `lewis-energy-economy-wall.md` (chaine ...113 -> 114) et la ligne d'index `MEMORY.md`. Lier `[[lewis-energy-economy-wall]]`, `[[nas-bottleneck-is-substrate-not-search]]`, et `[[sota-gap-substrate]]` (si FERME : converge le mandat migration moteur).

- [ ] **Step 5: Commit doc EDR**

```bash
git add docs/EDR/114_*.md
git commit -m "docs(EDR114): verdict <verdict> (la primitive d'atteinte ... le plafond de navigation)"
```

---

## Notes de revue (pour le reviewer final)

- **Non-regression** : `reach_oracle=False` defaut -> override jamais pris (`if getattr(self,"reach_oracle",False)`). `git diff origin/main -- src/` ne doit ajouter que : champ config, read `__init__`, methode `_reach_oracle_action`, bloc override de 2 lignes. Zero autre logique monde modifiee.
- **Oracle correct** : `_reach_oracle_action` choisit le 1er pas non bloque (geometrie) ; verifier le mapping 0=N/1=S/2=E/3=O coherent avec le bloc mouvement (l.1297-1300) ; verifier le fallback `cand[0]` (les deux axes bloques) ne crashe pas.
- **Borne-sup honnete** : confirmer que l'oracle n'utilise que de l'info OBSERVEE par l'agent (position relative proie = `dn/ds/de/dw` ; geometrie 1-pas = `lidar`). Pas de pathfinding global (caveat assume : rare dead-end possible -> verdict sur l'agregat).
- **`_measure_forage`** : co-activation `trace_forage=True` ET `trace_energy_sinks=True` presente dans `main_reach_oracle`.
- **Seuils verdict** : 0.90 / 0.50 sur la cellule (oracle=True, speed=0.0) — coherents avec la spec section 5.
- **Controles** : cellules oracle=False reproduisent l'ordre de grandeur 106/107/113 (a verifier au run, Task 3).
- **Seeds** : run reel 114 ; smoke/determinisme 99114/88114 distincts (provenance).
- **ASCII** : grep les `print` ajoutes pour fleche unicode/accents.
