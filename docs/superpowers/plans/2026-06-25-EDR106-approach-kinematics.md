# EDR 106 — Décomposition de l'APPROCHE (kinématique vs politique) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si le mur d'approche du forage est CINÉMATIQUE (proies fuyantes trop rapides) ou POLITIQUE (l'agent ne navigue pas vers les proies même immobiles), en balayant la vitesse des proies à N_APEX=0/metab=0.

**Architecture:** Ajoute un knob `prey_speed_scale` (config + `_move_preys`, inerte/byte-identique à 1.0) et un compteur de captures par espèce (extension du hook `trace_forage` d'EDR 105). Réutilise l'entonnoir `_measure_forage` d'EDR 105 pour lire `p_reach` ; un nouveau `main_approach` balaie la vitesse, un verdict porté par le niveau figé tranche KINEMATIQUE vs POLITIQUE.

**Tech Stack:** Python, numpy, `src/seed_ai/exp_stats.py` (Jonckheere-Terpstra), harnais `tools/lewis_survival_sweep.py`, pytest.

## Global Constraints

- **Commandement 15 (1 variable)** : seule variable balayée = `prey_speed_scale ∈ {1.0, 0.5, 0.25, 0.0}`. `trace_forage`/`trace_energy_sinks` et le compteur par espèce sont des **instruments inertes**, pas des variables.
- **Invariant RNG / inertie** : à `prey_speed_scale=1.0` (défaut), `_move_preys` doit être **byte-identique** à l'actuel — même valeur de `moves_per_tick`, même consommation de `np.random.rand()`, mêmes positions de proies. Le multiplicateur `* 1.0` est l'identité sur le chemin int/frac/rand. Protège les sessions parallèles.
- **ASCII only** dans tout `print`/littéral exécuté (Windows cp1252 : pas de `−`, `→`, `×`, accents dans les chaînes imprimées ; `->` est OK).
- **Reproductibilité** : `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; `memory_retriever.stop()+clear()` ; mêmes seeds appariés entre niveaux.
- **N_APEX=0**, `base_metabolism=0.0`, `forage_payoff=3`, `PREY_COUNT=15`, `NUM_AGENTS=24`, `max_ticks=150`.
- **Verdict porté par le niveau figé** (`prey_speed_scale=0.0`).

---

## File Structure

- `src/environments/config.py` — champ `prey_speed_scale: float = 1.0`.
- `src/worlds/world_1_stoneage.py` — `_move_preys` (scale + gel de la fuite-au-feu) ; compteur espèce dans le hook `trace_forage` (l.~751).
- `tools/lewis_survival_sweep.py` — param `_cfg(prey_speed_scale=…)` ; clés `cap_lapin/cap_cerf/cap_sanglier` + `reached_raw` dans `_measure_forage` ; `_verdict_approach` ; `_report_approach` ; `main_approach`.
- `tests/sandbox/test_edr106_approach_kinematics.py` — tests (calqués sur `tests/sandbox/test_edr105_forage_funnel.py`).

---

## Task 1: Knob `prey_speed_scale` + compteur par espèce (monde)

**Files:**
- Modify: `src/environments/config.py:59`
- Modify: `src/worlds/world_1_stoneage.py` (`_move_preys` ~l.569-581 ; hook espèce ~l.750-751)
- Test: `tests/sandbox/test_edr106_approach_kinematics.py`

**Interfaces:**
- Consumes: rien (premier task).
- Produces :
  - `cfg.prey_speed_scale` (float, défaut 1.0) multiplie la vitesse de toutes les proies dans `_move_preys` ; à 0.0 les proies sont figées (ni chasse/fuite, ni fuite-au-feu).
  - Quand `cfg.trace_forage=True`, un kill de proie régulière pose `agent["_forage_species"][type] += 1` ; absent quand `trace_forage=False`.

- [ ] **Step 1: Write the failing tests (config default + freeze + species)**

Créer `tests/sandbox/test_edr106_approach_kinematics.py` :

```python
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.harness import seed_at


def _mk_env(prey_speed_scale=None, trace_forage=False):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_forage = trace_forage
    if prey_speed_scale is not None:
        cfg.prey_speed_scale = prey_speed_scale
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(6):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def _prey_positions(env):
    return sorted((p["x"], p["y"], p["type"]) for p in env.preys)


def test_config_default_prey_speed_scale_one():
    assert WorldConfig().prey_speed_scale == 1.0


def test_scale_one_is_inert_vs_field_absent():
    # Ajout du champ a 1.0 == comportement sans le champ (getattr defaut 1.0) -> non-regression.
    seed_at(424242, 0)
    env_a = _mk_env(prey_speed_scale=1.0)
    seed_at(424242, 0)
    env_b = _mk_env(prey_speed_scale=None)
    delattr(env_b.config, "prey_speed_scale")   # simule l'absence du champ
    for _ in range(5):
        env_a.step()
        env_b.step()
    assert _prey_positions(env_a) == _prey_positions(env_b)


def test_scale_zero_freezes_preys():
    env = _mk_env(prey_speed_scale=0.0)
    env.config.target_prey_count = 0    # desactive le respawn (sinon positions aleatoires != deplacement)
    before = _prey_positions(env)
    for _ in range(5):
        env.step()
    after = _prey_positions(env)
    # aucune proie n'a BOUGE : sans respawn, les seules positions presentes en 'after' sont un
    # sous-ensemble de 'before' (un kill retire une position ; un deplacement creerait une position
    # nouvelle absente de 'before' -> ferait echouer l'assertion).
    assert after == [pos for pos in before if pos in after]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -v`
Expected: `test_config_default_prey_speed_scale_one` FAILS (`AttributeError`), les autres FAIL ou erreur (champ absent).

- [ ] **Step 3: Add the config field**

Dans `src/environments/config.py`, après la ligne 59 (`trace_forage: bool = False ...`), ajouter :

```python
    prey_speed_scale: float = 1.0      # EDR106 : multiplicateur global vitesse des proies (0 = fige ; defaut 1.0 = inerte)
```

- [ ] **Step 4: Apply the scale + freeze fire-flee in `_move_preys`**

Dans `src/worlds/world_1_stoneage.py`, dans `_move_preys`, remplacer le bloc fuite-au-feu + lecture de `moves_per_tick` (l.~569-581) :

```python
            fled = False
            for fx, fy in fire_pos:
                if abs(p["x"] - fx) <= 2 and abs(p["y"] - fy) <= 2:
                    p["x"] += 1 if p["x"] > fx else -1
                    p["y"] += 1 if p["y"] > fy else -1
                    p["x"] = np.clip(p["x"], 0, self.size - 1)
                    p["y"] = np.clip(p["y"], 0, self.size - 1)
                    fled = True
                    break
            if fled: continue
                
            cfg = self.config.preys.get(p["type"], None)
            moves_per_tick = cfg.moves_per_tick if cfg else 0
```

par :

```python
            scale = getattr(self.config, "prey_speed_scale", 1.0)   # EDR106 : 0 = proies figees
            fled = False
            if scale > 0:                                            # EDR106 : figees -> ne fuient pas le feu
                for fx, fy in fire_pos:
                    if abs(p["x"] - fx) <= 2 and abs(p["y"] - fy) <= 2:
                        p["x"] += 1 if p["x"] > fx else -1
                        p["y"] += 1 if p["y"] > fy else -1
                        p["x"] = np.clip(p["x"], 0, self.size - 1)
                        p["y"] = np.clip(p["y"], 0, self.size - 1)
                        fled = True
                        break
            if fled: continue
                
            cfg = self.config.preys.get(p["type"], None)
            moves_per_tick = (cfg.moves_per_tick if cfg else 0) * scale   # EDR106 : vitesse echelonnee
```

**Invariant RNG** : à `scale=1.0`, `(moves_per_tick) * 1.0` est numériquement identique (`int(2.0)==int(2)`, `2.0-2 == 2-2`), donc `np.random.rand()` est consommé à l'identique. Le `if scale > 0` est toujours vrai à 1.0 → fuite-au-feu inchangée. Ne PAS réordonner ni supprimer le `np.random.rand()`.

- [ ] **Step 5: Add the per-species counter in the regular-kill hook**

Localiser le hook revenu d'EDR 105 (~l.750-751) :

```python
                    if getattr(self.config, "trace_forage", False):
                        agent["_forage_income"] = agent.get("_forage_income", 0.0) + reward
```

Le remplacer par (ajoute le compteur espèce sous la même garde) :

```python
                    if getattr(self.config, "trace_forage", False):
                        agent["_forage_income"] = agent.get("_forage_income", 0.0) + reward
                        sp = agent.setdefault("_forage_species", {})   # EDR106 : captures par espece
                        sp[attacked_prey["type"]] = sp.get(attacked_prey["type"], 0) + 1
```

- [ ] **Step 6: Add the species + inertia tests**

Ajouter à `tests/sandbox/test_edr106_approach_kinematics.py` :

```python
def test_species_counter_records_kill():
    # Force un kill regulier : un agent et un Lapin (hp=1) sur la meme case, l'attaque auto le tue.
    env = _mk_env(prey_speed_scale=0.0, trace_forage=True)
    env.preys.clear()
    ag = env.agents[0]
    env.preys.append({"x": ag["x"], "y": ag["y"], "type": "Lapin", "stunned": 0, "hp": 1.0})
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    species = {}
    for a in pool:
        for k, v in a.get("_forage_species", {}).items():
            species[k] = species.get(k, 0) + v
    assert species.get("Lapin", 0) >= 1


def test_species_counter_inert_when_trace_off():
    env = _mk_env(prey_speed_scale=0.0, trace_forage=False)
    env.preys.clear()
    ag = env.agents[0]
    env.preys.append({"x": ag["x"], "y": ag["y"], "type": "Lapin", "stunned": 0, "hp": 1.0})
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert all("_forage_species" not in a for a in pool)
```

- [ ] **Step 7: Run all Task 1 tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -v`
Expected: les 5 tests PASS (config default, inert-vs-absent, freeze, species kill, species inert).

- [ ] **Step 8: Commit**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tests/sandbox/test_edr106_approach_kinematics.py
git commit -m "feat(EDR106): knob prey_speed_scale (inerte a 1.0) + compteur captures par espece"
```

---

## Task 2: `_cfg(prey_speed_scale)` + clés espèce/reached_raw dans `_measure_forage`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (signature `_cfg` ~l.34 ; corps de `_measure_forage` ~l.150-204)
- Test: `tests/sandbox/test_edr106_approach_kinematics.py`

**Interfaces:**
- Consumes: `agent["_forage_species"]` (Task 1) ; l'entonnoir `_measure_forage` (EDR 105).
- Produces: `_cfg(..., prey_speed_scale=1.0)` ; `_measure_forage` renvoie en plus `cap_lapin`, `cap_cerf`, `cap_sanglier` (moyennes de captures/agent par espèce) et `reached_raw` (liste des 0.0/1.0 « a atteint une proie » par agent, pour le test de tendance JT). Les clés EDR 105 existantes sont inchangées.

- [ ] **Step 1: Write the failing tests**

Ajouter à `tests/sandbox/test_edr106_approach_kinematics.py` :

```python
from tools.lewis_survival_sweep import _cfg, _measure_forage


def test_cfg_prey_speed_scale_param():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    assert cfg.prey_speed_scale == 0.0
    assert cfg.trace_forage is True


def test_measure_forage_has_species_and_reached_raw():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    agg = _measure_forage(cfg, [106, 107], n_apex=0, max_ticks=20)
    for k in ("cap_lapin", "cap_cerf", "cap_sanglier", "reached_raw"):
        assert k in agg
    assert 0.0 <= agg["p_reach"] <= 1.0
    assert isinstance(agg["reached_raw"], list)
    assert len(agg["reached_raw"]) == agg["n_agents"]
    assert all(v in (0.0, 1.0) for v in agg["reached_raw"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -k "prey_speed_scale_param or species_and_reached_raw" -v`
Expected: FAIL (`_cfg` n'accepte pas `prey_speed_scale` ; clés absentes).

- [ ] **Step 3: Add the `prey_speed_scale` param to `_cfg`**

Dans `tools/lewis_survival_sweep.py`, modifier la signature de `_cfg` (l.34) pour ajouter le param en dernière position, et poser le champ dans le corps (après la ligne `cfg.trace_forage = bool(trace_forage)`) :

```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB,
         trace_forage=False, prey_speed_scale=1.0):
```

et, dans le corps, juste après `cfg.trace_forage = bool(trace_forage)` :

```python
    cfg.prey_speed_scale = float(prey_speed_scale)            # EDR106
```

- [ ] **Step 4: Collect per-species captures + reached_raw in `_measure_forage`**

Dans `_measure_forage`, après la ligne `income_t, drain_t, captures, contacts, min_dists = [], [], [], [], []` (~l.154), ajouter :

```python
    cap_lapin, cap_cerf, cap_sanglier = [], [], []
```

Puis, dans la boucle sur le pool, après `min_dists.append(md)` (~l.194), ajouter :

```python
            sp = ag.get("_forage_species", {})
            cap_lapin.append(float(sp.get("Lapin", 0)))
            cap_cerf.append(float(sp.get("Cerf", 0)))
            cap_sanglier.append(float(sp.get("Sanglier", 0)))
```

Enfin, dans le dict de retour (~l.197-204), ajouter les 4 clés (`reached` est déjà la liste 0/1 collectée) :

```python
    return {"p_reach": mean(reached),
            "p_cap": mean(captured_if_reached),
            "income_t": med(income_t),
            "drain_t": med(drain_t),
            "mean_captures": mean(captures),
            "mean_contacts": mean(contacts),
            "mean_min_dist": mean(min_dists),
            "cap_lapin": mean(cap_lapin),
            "cap_cerf": mean(cap_cerf),
            "cap_sanglier": mean(cap_sanglier),
            "reached_raw": reached,
            "n_agents": len(income_t)}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -k "prey_speed_scale_param or species_and_reached_raw" -v`
Expected: les 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr106_approach_kinematics.py
git commit -m "feat(EDR106): _cfg(prey_speed_scale) + cap_* / reached_raw dans _measure_forage"
```

---

## Task 3: `_verdict_approach` + `_report_approach` + `main_approach`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (3 fonctions, près des `_verdict_*`/`_report_*`/`main_*` existants)
- Test: `tests/sandbox/test_edr106_approach_kinematics.py`

**Interfaces:**
- Consumes: le dict de `_measure_forage` (clés `p_reach`, `reached_raw`, `cap_*`, etc.).
- Produces :
  - `_verdict_approach(aggs)` où `aggs` = liste `(prey_speed_scale, agg)` → `"KINEMATIQUE"` si l'agg de `scale==0.0` a `p_reach ≥ 0.5`, sinon `"POLITIQUE"` (`"INDETERMINE"` si aucun niveau 0.0).
  - `_report_approach(h, aggs, R, n_eval, _return)` : table ASCII (p_reach/p_cap/captures + par espèce) + Jonckheere-Terpstra (tendance de `p_reach` quand la vitesse baisse, via `reached_raw`) + verdict (sur le figé) ; sauve une table **sans** `reached_raw` (évite de gonfler le JSON).
  - `main_approach(speed_levels=(1.0, 0.5, 0.25, 0.0), n_eval=8, R=4, seed=None, _return=False)`.

- [ ] **Step 1: Write the failing tests (2 branches du verdict)**

Ajouter à `tests/sandbox/test_edr106_approach_kinematics.py` :

```python
from tools.lewis_survival_sweep import _verdict_approach


def _approach_aggs(p_reach_frozen):
    return [(1.0, {"p_reach": 0.10, "reached_raw": [0.0]}),
            (0.0, {"p_reach": p_reach_frozen, "reached_raw": [1.0]})]


def test_verdict_approach_kinematique():
    assert _verdict_approach(_approach_aggs(0.80)) == "KINEMATIQUE"


def test_verdict_approach_politique():
    assert _verdict_approach(_approach_aggs(0.30)) == "POLITIQUE"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -k verdict_approach -v`
Expected: FAIL (`_verdict_approach` n'existe pas).

- [ ] **Step 3: Add `_verdict_approach`**

Ajouter dans `tools/lewis_survival_sweep.py` (après `_verdict_forage`) :

```python
def _verdict_approach(aggs):
    """EDR106 : verdict porte par le niveau FIGE (prey_speed_scale=0.0). p_reach>=0.5 -> KINEMATIQUE
    (proies immobiles atteintes -> le mur etait la fuite, vitesse relative) ; sinon POLITIQUE (la
    navigation est le mur, meme sans fuite). aggs = liste (prey_speed_scale, agg)."""
    frozen = next((a for s, a in aggs if s == 0.0), None)
    if frozen is None:
        return "INDETERMINE"
    return "KINEMATIQUE" if frozen["p_reach"] >= 0.5 else "POLITIQUE"
```

- [ ] **Step 4: Run the verdict tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -k verdict_approach -v`
Expected: les 2 tests PASS.

- [ ] **Step 5: Add `_report_approach` and `main_approach`**

Ajouter dans `tools/lewis_survival_sweep.py` (après `main_forage`, avant le `if __name__`) :

```python
def _report_approach(h, aggs, R, n_eval, _return):
    """Table APPROCHE (1 ligne/vitesse : p_reach, p_cap, captures totales + par espece) + Jonckheere-
    Terpstra (tendance p_reach quand la vitesse baisse) + verdict (porte par le niveau fige) + provenance.
    Tout ASCII (cp1252). aggs = liste de (prey_speed_scale, agg). reached_raw est retire avant sauvegarde."""
    verdict = _verdict_approach(aggs)
    jt = st.jonckheere_terpstra([a["reached_raw"] for _, a in aggs])
    print("\n=== EDR106 decomposition APPROCHE a N_APEX=0 (verdict sur prey_speed_scale=0) ===")
    print("  speed | p_reach p_cap | cap_tot cap_lapin cap_cerf cap_sanglier | min_dist | n")
    for s, a in aggs:
        print(f"  {s:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['mean_captures']:7.2f} {a['cap_lapin']:9.2f} {a['cap_cerf']:8.2f} "
              f"{a['cap_sanglier']:12.2f} | {a['mean_min_dist']:8.2f} | {a['n_agents']}")
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(p_reach croit qd vitesse baisse)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre, porte par le niveau fige) ===")
    print(f"  -> {verdict}")
    slim = {str(s): {k: v for k, v in a.items() if k != "reached_raw"} for s, a in aggs}
    h.save({"knob": "prey_speed_scale", "speed_levels": [s for s, _ in aggs], "R": R, "n_eval": n_eval,
            "jt": jt, "verdict": verdict, "table": slim})
    if _return:
        return {"verdict": verdict, "jt": jt, "table": slim, "R": R, "n_eval": n_eval}


def main_approach(speed_levels=(1.0, 0.5, 0.25, 0.0), n_eval=8, R=4, seed=None, _return=False):
    """EDR 106 : decompose l'APPROCHE en balayant prey_speed_scale a N_APEX=0/metab=0, forage_payoff=3.
    Verdict KINEMATIQUE (p_reach>=0.5 au niveau fige) vs POLITIQUE. Reutilise l'entonnoir trace_forage
    (EDR105). Co-active trace_forage ET trace_energy_sinks (instruments inertes)."""
    with Harness(seed=seed, name="lewis_approach_kinematics", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR106 : approche prey_speed_scale={speed_levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(speed_levels), label="niveaux prey_speed_scale")
        aggs = []
        for s in speed_levels:
            cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                       prey_speed_scale=s)
            aggs.append((s, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
            prog.update()
        return _report_approach(h, aggs, R, n_eval, _return)
```

- [ ] **Step 6: Run the full test file to verify everything passes**

Run: `python -m pytest tests/sandbox/test_edr106_approach_kinematics.py -v`
Expected: tous les tests PASS (config/inert/freeze/species ×2 de T1, cfg param/smoke de T2, 2 verdicts de T3).

- [ ] **Step 7: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr106_approach_kinematics.py
git commit -m "feat(EDR106): _verdict_approach + _report_approach (JT) + main_approach"
```

---

## Task 4: Run réduit + provenance (exécution, pas TDD)

**Files:**
- Lecture seule du code ci-dessus ; écrit `results/lewis_approach_kinematics_106.json` (via `h.save`).

**Interfaces:**
- Consumes: `main_approach` (Task 3).
- Produces: la table APPROCHE aux 4 niveaux de vitesse + le verdict + le JSON de provenance.

- [ ] **Step 1: Run réduit fidèle d'emblée**

Le run gelé (`R=4, n_eval=8`) est impraticablement lent à `metab=0` (et pire à `scale=0` : agents bien nourris survivent plus). Lancer directement le run réduit (l'APPROCHE est une propriété par-agent, robuste à `n_eval` ; `max_ticks=150 > gate`) :

```python
from tools.lewis_survival_sweep import main_approach
main_approach(speed_levels=(1.0, 0.5, 0.25, 0.0), n_eval=3, R=1, seed=106)
```

Expected: une table à 4 lignes (vitesses 1.0→0.0) + une ligne JT + une ligne VERDICT. À `scale=1.0`, `p_reach` doit être proche de la valeur EDR 105 (~0.18) ; le verdict est lu sur `scale=0.0`.

- [ ] **Step 2: Vérifier la provenance**

Run: `python -c "import json; d=json.load(open('results/lewis_approach_kinematics_106.json'))['data']; print(d['verdict']); print(d['speed_levels']); print({k: round(v['p_reach'],3) for k,v in d['table'].items()})"`
Expected: imprime le verdict (`KINEMATIQUE` ou `POLITIQUE`), les niveaux `[1.0, 0.5, 0.25, 0.0]`, et les `p_reach` par niveau.

- [ ] **Step 3 (conditionnel) : si le run réduit reste trop lent**

Si même `R=1, n_eval=3` dépasse ~15 min, réduire `max_ticks` à 80 (toujours > la survie ~27 ticks observée en EDR 105, donc fidèle au plateau de `min_dist`) et relancer ; documenter la réduction comme surdéterminée dans le doc EDR.

---

## Notes de réalisation

- Le doc de résultat `docs/EDR/106_*.md` et la MAJ mémoire `lewis-energy-economy-wall.md` sont écrits **après** le run, une fois le verdict connu.
- `results/` est gitignoré (artefacts régénérables) ; la provenance est citée par chemin + `seed=106` + commit, comme EDR 101/105.
- Le compteur par espèce s'active aussi pour `main_forage` (EDR 105) puisqu'il partage le hook `trace_forage` — c'est additif et inerte (lecture avec défaut `{}`), aucune régression.
