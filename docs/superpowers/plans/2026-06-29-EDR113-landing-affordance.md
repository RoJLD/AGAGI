# EDR 113 — Recompenser le pas final (affordance d'atterrissage) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si recompenser l'atterrissage sur une cellule-proie (`scaffold_land`, balaye {0,2,5,10}) monte le plafond de navigation `p_reach` de Lewis au-dela des ~0.36 d'EDR 107.

**Architecture:** Cabler un nouveau scaffold `scaffold_land` (config + monde, defaut 0.0 = non-regressif) verse dans le bloc `if attacked_prey:` de `world_1_stoneage.py`. Puis etendre `tools/lewis_survival_sweep.py` avec `main_landing_nav` qui balaye `scaffold_land` en reutilisant la boucle evolve_nav d'EDR 107 ; le bras `scaffold_land=0` reproduit EDR 107 (controle).

**Tech Stack:** Python, numpy, pytest. Reutilise `Biosphere3D`, `_evolve_nav_gen`, `_reproduce`, `_load_champions`, `_cfg`, `seed_at`, `Harness`, `MutationConfig`, `anneal`.

## Global Constraints

- **1 variable (Commandement 15)** : la SEULE difference entre bras est `scaffold_land`. Monde (Lewis vide d'apex, `base_metabolism=0.0`, `forage_payoff=3`, scaffold d'approche inchangé), substrat (prod baseline via `_load_champions`), selection (`calculate_life_score`, cliquet best-ever top-5), graines (deterministes par bras), mutation, ticks, population — tous identiques.
- **Non-regression** : `scaffold_land` defaut 0.0 partout. A 0.0, le terme ajoute est `+0.0` -> comportement byte-identique a l'actuel. Tous les mondes/EDR existants inchangés.
- **Placement du reward** : dans le bloc `if attacked_prey:` (atterrissage sur une cellule-proie), **tous gibiers** (PAS gaté sur `cfg.damage>0`, contrairement a `scaffold_bighit`). Annelé via `anneal(current_era, scaffold_eras=30)`.
- **ASCII-only dans tout `print` execute** (Windows cp1252) : `->` ASCII OK, pas de fleche unicode/accents/x.
- **Determinisme** : `seed_at` avant toute consommation RNG.
- **Provenance** : `results/` gitignore ; seed du run reel = 113 ; smoke seed=99113, determinisme seed=88113 (distincts de 113 pour ne pas ecraser la provenance). Run reel APRES revue ; AUCUN test relancé apres.
- **Verdict pre-enregistre** : AFFORDANCE LEVE / AFFORDANCE INERTE / AFFORDANCE AMBIGUE (seuils en Task 3).

---

### Task 1: `scaffold_land` — config + cablage monde (non-regressif)

**Files:**
- Modify: `src/environments/config.py` (ajouter le champ apres `prey_speed_scale`, l.60)
- Modify: `src/worlds/world_1_stoneage.py` (lire en `__init__` ~l.122 ; verser dans `if attacked_prey:` ~l.692)
- Test: `tests/sandbox/test_edr113_landing.py` (creer)

**Interfaces:**
- Consumes: `WorldConfig` (dataclass, `src/environments/config.py`) ; `Biosphere3D(config)` (`self.config` dispo des l.34) ; `anneal(era, n)` (importe dans `world_1_stoneage.py`, l.18).
- Produces: `WorldConfig.scaffold_land: float = 0.0` ; `Biosphere3D(cfg).scaffold_land` (float) ; reward `+= scaffold_land * anneal(era, scaffold_eras)` quand un agent est sur une cellule-proie.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_edr113_landing.py` :

```python
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def _cfg_land(scaffold_land):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.0
    cfg.forage_payoff = 3.0
    cfg.prey_speed_scale = 0.0      # proies figees (deterministe, EDR106)
    cfg.trace_forage = True         # pour lire _forage_contacts
    cfg.scaffold_land = float(scaffold_land)
    return cfg


def test_config_has_scaffold_land_default_zero():
    assert WorldConfig().scaffold_land == 0.0


def test_world_reads_scaffold_land():
    assert Biosphere3D(_cfg_land(0.0)).scaffold_land == 0.0
    assert Biosphere3D(_cfg_land(10.0)).scaffold_land == 10.0


def _run_with_prey_on_agent(scaffold_land, steps=40, seed=4242):
    """Place UN agent et UNE proie figee a la meme cellule ; renvoie (energie_totale, contacts)."""
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent
    seed_at(seed, 0)
    env = Biosphere3D(_cfg_land(scaffold_land))
    env.preys = [p for p in env.preys if p["type"] not in ("Mammouth", "Ours", "Leurre")]  # Lewis vide d'apex
    env.current_era = 1
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    a = MambaAgent()
    env.add_agent(a, energy=80.0)
    ag = env.agents[0]
    # forcer une proie petite (damage=0) sur la cellule de l'agent
    env.preys.append({"x": ag["x"], "y": ag["y"], "z": 0, "type": "Lapin", "hp": 1})
    contacts = 0
    for _ in range(steps):
        if not env.agents:
            break
        env.step()
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        contacts = max(contacts, max((p.get("_forage_contacts", 0) for p in pool), default=0))
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    total_energy = sum(p["energy"] for p in pool)
    return total_energy, contacts


def test_landing_reward_is_paid_monotone():
    # scaffold_land n'AJOUTE que de l'energie sur atterrissage -> env riche >= env pauvre,
    # strictement > si au moins un contact a eu lieu. Cible le PAS FINAL.
    e0, c0 = _run_with_prey_on_agent(0.0)
    eL, cL = _run_with_prey_on_agent(10.0)
    assert cL >= 1, "le scenario doit produire au moins un atterrissage (contact)"
    assert eL > e0, f"scaffold_land=10 doit enrichir vs 0 (eL={eL} e0={e0})"


def test_non_regression_byte_identical_at_zero():
    # Deux runs scaffold_land=0 -> energie totale identique (le defaut ne change rien).
    e0a, _ = _run_with_prey_on_agent(0.0, seed=777)
    e0b, _ = _run_with_prey_on_agent(0.0, seed=777)
    assert e0a == e0b
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -v`
Expected: FAIL — `AttributeError: 'WorldConfig' object has no attribute 'scaffold_land'` (et `Biosphere3D.scaffold_land` absent).

- [ ] **Step 3: Add the config field**

Dans `src/environments/config.py`, juste apres la ligne `prey_speed_scale: float = 1.0` (l.60) :

```python
    scaffold_land: float = 0.0         # EDR113 : recompense le PAS FINAL (atterrir sur une cellule-proie) ; defaut 0.0 = inerte/non-regressif
```

- [ ] **Step 4: Wire the world to read it (`__init__`)**

Dans `src/worlds/world_1_stoneage.py`, juste apres `self.scaffold_eras = 30` (l.122) :

```python
        self.scaffold_land = getattr(self.config, "scaffold_land", 0.0)   # EDR113 : scaffold du pas final (atterrissage sur proie)
```

- [ ] **Step 5: Wire the world to pay it (`if attacked_prey:`)**

Dans `src/worlds/world_1_stoneage.py`, remplacer le debut du bloc d'attaque (l.692-693) :

```python
        if attacked_prey:
            if getattr(self.config, "trace_forage", False):
```

par (inserer le reward comme PREMIERE instruction du bloc, AVANT le hook trace_forage) :

```python
        if attacked_prey:
            # EDR113 : scaffold du PAS FINAL — recompense l'atterrissage sur une cellule-proie
            # (tous gibiers, contrairement a scaffold_bighit gate sur damage>0). Annelé. Defaut 0.0 -> inerte.
            agent["energy"] += self.scaffold_land * anneal(getattr(self, "current_era", 1), self.scaffold_eras)
            if getattr(self.config, "trace_forage", False):
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -v`
Expected: PASS (4/4). Si `test_landing_reward_is_paid_monotone` echoue sur `cL >= 1` (aucun contact), augmenter `steps` a 80 dans `_run_with_prey_on_agent` (l'agent doit rester/retomber sur la proie figee ; le respawn la maintient) — NE PAS affaiblir l'assertion d'energie.

- [ ] **Step 7: Commit**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tests/sandbox/test_edr113_landing.py
git commit -m "feat(EDR113): scaffold_land (recompense le pas final) cable config + monde, non-regressif a 0"
```

---

### Task 2: `_cfg` param + `_landing_arm` (boucle evolve par niveau)

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (param `_cfg` ~l.35 ; ajouter `_landing_arm` apres les helpers EDR110)
- Test: `tests/sandbox/test_edr113_landing.py` (ajouter)

**Interfaces:**
- Consumes: `_cfg(forage_payoff, ..., trace_forage=False, prey_speed_scale=1.0)` (existant, l.35) ; `_load_champions()` ; `_reproduce(champions, num_agents, mc)` ; `_evolve_nav_gen(cfg, genomes, max_ticks) -> (scored, p_reach, stats)` (EDR107) ; `MutationConfig`, `seed_at`, `np`.
- Produces:
  - `_cfg(..., scaffold_land=0.0)` -> pose `cfg.scaffold_land = float(scaffold_land)`.
  - `_landing_arm(cfg, generations, num_agents, max_ticks, base_seed) -> dict` avec cles `scaffold_land, traj (list[float]), gen0 (float), first (float), plateau (float), stats (list[dict])`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_edr113_landing.py` :

```python
from tools.lewis_survival_sweep import _cfg, _landing_arm


def test_cfg_scaffold_land_param():
    assert _cfg(3).scaffold_land == 0.0
    assert _cfg(3, scaffold_land=5.0).scaffold_land == 5.0


def test_landing_arm_smoke_returns_expected_keys():
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True, scaffold_land=5.0)
    arm = _landing_arm(cfg, generations=2, num_agents=6, max_ticks=40, base_seed=99113)
    assert arm["scaffold_land"] == 5.0
    assert len(arm["traj"]) == 2
    assert 0.0 <= arm["plateau"] <= 1.0
    assert 0.0 <= arm["gen0"] <= 1.0
    assert len(arm["stats"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -k "cfg_scaffold_land or landing_arm" -v`
Expected: FAIL — `TypeError: _cfg() got an unexpected keyword argument 'scaffold_land'` puis `ImportError: cannot import name '_landing_arm'`.

- [ ] **Step 3: Add `scaffold_land` to `_cfg`**

Dans `tools/lewis_survival_sweep.py`, modifier la signature de `_cfg` (l.35-36) pour ajouter le parametre, et poser le champ avant `return cfg` (apres la ligne `cfg.prey_speed_scale = ...`, l.45) :

Signature (ajouter `scaffold_land=0.0` en fin) :
```python
def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB,
         trace_forage=False, prey_speed_scale=1.0, scaffold_land=0.0):
```
Avant `return cfg` :
```python
    cfg.scaffold_land = float(scaffold_land)                  # EDR113
```

- [ ] **Step 4: Implement `_landing_arm`**

Ajouter dans `tools/lewis_survival_sweep.py` (apres les helpers EDR110, p.ex. apres `_capacity_arm`) :

```python
def _landing_arm(cfg, generations, num_agents, max_ticks, base_seed):
    """EDR113 : un bras = evolue la navigation sous un cfg portant un scaffold_land donne. Calque
    main_evolve_nav (EDR107) : best_ever seedé par _load_champions, _reproduce (mc standard, add_node ON
    comme 107), _evolve_nav_gen, cliquet best-ever top-5. La SEULE variable entre bras est
    cfg.scaffold_land. Renvoie {scaffold_land, traj, gen0, first, plateau, stats}."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(base_seed, 0)
    champs = _load_champions()
    best_ever = [(0.0, g) for g in champs]
    traj, stats_hist = [], []
    for gen in range(1, generations + 1):
        seed_at(base_seed + gen, 0)
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents, mc)
        scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        traj.append(p_reach)
        stats_hist.append(stats)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    return {
        "scaffold_land": float(cfg.scaffold_land), "traj": traj,
        "gen0": float(traj[0]) if traj else 0.0,
        "first": float(np.median(traj[:k])) if traj else 0.0,
        "plateau": float(np.median(traj[-k:])) if traj else 0.0,
        "stats": stats_hist,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -k "cfg_scaffold_land or landing_arm" -v`
Expected: PASS (2/2).

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr113_landing.py
git commit -m "feat(EDR113): _cfg scaffold_land param + _landing_arm (evolve_nav par niveau)"
```

---

### Task 3: `_verdict_landing` + `_report_landing` + `main_landing_nav`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajouter les 3 fonctions apres `_landing_arm`)
- Test: `tests/sandbox/test_edr113_landing.py` (ajouter)

**Interfaces:**
- Consumes: `_landing_arm` (Task 2) ; `_cfg` ; `Harness(seed, name, with_db=False)` ; `seed_at` ; `_disable_kuzu()` ; `np.polyfit`, `np.median`.
- Produces:
  - `_verdict_landing(arms: list[dict]) -> str` in {"AFFORDANCE LEVE", "AFFORDANCE INERTE", "AFFORDANCE AMBIGUE"}.
  - `_report_landing(h, arms, generations, num_agents, max_ticks, _return) -> dict|None`.
  - `main_landing_nav(land_levels=(0.0,2.0,5.0,10.0), generations=20, num_agents=24, max_ticks=80, seed=113, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_edr113_landing.py` :

```python
from tools.lewis_survival_sweep import _verdict_landing, main_landing_nav


def _arm(land, plateau):
    return {"scaffold_land": land, "plateau": plateau, "gen0": plateau,
            "first": plateau, "traj": [plateau], "stats": []}


def test_verdict_leve_on_rising_plateaus():
    arms = [_arm(0, 0.36), _arm(2, 0.42), _arm(5, 0.50), _arm(10, 0.58)]
    assert _verdict_landing(arms) == "AFFORDANCE LEVE"


def test_verdict_inerte_on_flat_plateaus():
    arms = [_arm(0, 0.36), _arm(2, 0.35), _arm(5, 0.37), _arm(10, 0.36)]
    assert _verdict_landing(arms) == "AFFORDANCE INERTE"


def test_verdict_ambigue_on_descending_plateaus():
    arms = [_arm(0, 0.55), _arm(2, 0.40), _arm(5, 0.30), _arm(10, 0.20)]
    assert _verdict_landing(arms) == "AFFORDANCE AMBIGUE"


def test_main_landing_nav_smoke_and_determinism():
    r1 = main_landing_nav(land_levels=(0.0, 5.0), generations=2, num_agents=6,
                          max_ticks=40, seed=88113, _return=True)
    assert r1["verdict"] in ("AFFORDANCE LEVE", "AFFORDANCE INERTE", "AFFORDANCE AMBIGUE")
    assert len(r1["arms"]) == 2
    r2 = main_landing_nav(land_levels=(0.0, 5.0), generations=2, num_agents=6,
                          max_ticks=40, seed=88113, _return=True)
    assert [a["traj"] for a in r1["arms"]] == [a["traj"] for a in r2["arms"]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -k "verdict or main_landing" -v`
Expected: FAIL — `ImportError: cannot import name '_verdict_landing'`.

- [ ] **Step 3: Implement the 3 functions**

Ajouter dans `tools/lewis_survival_sweep.py` (apres `_landing_arm`) :

```python
def _verdict_landing(arms):
    """EDR113 : verdict pre-enregistre sur l'effet de scaffold_land (recompense du pas final) sur le
    plateau de navigation. delta = plateau(max) - plateau(0) ; slope = pente du plateau vs scaffold_land
    (echelle lineaire 0-10). AFFORDANCE LEVE si delta>=0.10 ET slope>0. AFFORDANCE INERTE si
    abs(delta)<0.10 ET abs(slope)<0.01. AFFORDANCE AMBIGUE sinon (signal partiel/non-monotone)."""
    arms = sorted(arms, key=lambda a: a["scaffold_land"])
    plateaus = [a["plateau"] for a in arms]
    delta = plateaus[-1] - plateaus[0]
    x = [a["scaffold_land"] for a in arms]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms) >= 2 else 0.0
    if delta >= 0.10 and slope > 0:
        return "AFFORDANCE LEVE"
    if abs(delta) < 0.10 and abs(slope) < 0.01:
        return "AFFORDANCE INERTE"
    return "AFFORDANCE AMBIGUE"


def _report_landing(h, arms, generations, num_agents, max_ticks, _return):
    """Table ASCII (1 ligne/bras : scaffold_land, gen0, first, plateau, delta_vs_base) + pente +
    delta(max-base) + verdict pre-enregistre. Sauvegarde JSON. Tout ASCII (cp1252)."""
    verdict = _verdict_landing(arms)
    arms_sorted = sorted(arms, key=lambda a: a["scaffold_land"])
    base_plateau = arms_sorted[0]["plateau"]
    plateaus = [a["plateau"] for a in arms_sorted]
    x = [a["scaffold_land"] for a in arms_sorted]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms_sorted) >= 2 else 0.0
    print("\n=== EDR113 scaffold_land (recompense pas final) -> plafond navigation Lewis ===")
    print("  land | gen0  first plateau | delta_vs_base")
    for a in arms_sorted:
        print(f"  {a['scaffold_land']:4.1f} | {a['gen0']:.3f} {a['first']:.3f} "
              f"{a['plateau']:.3f} | {a['plateau'] - base_plateau:+.3f}")
    print(f"  pente plateau vs scaffold_land = {slope:+.4f}  delta(max-base) = "
          f"{plateaus[-1] - plateaus[0]:+.3f} (gate +0.10)")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "scaffold_land", "land_levels": [a["scaffold_land"] for a in arms_sorted],
            "generations": generations, "num_agents": num_agents, "max_ticks": max_ticks,
            "slope": slope, "delta": plateaus[-1] - plateaus[0], "verdict": verdict,
            "arms": arms_sorted})
    if _return:
        return {"verdict": verdict, "arms": arms_sorted, "slope": slope,
                "delta": plateaus[-1] - plateaus[0]}


def main_landing_nav(land_levels=(0.0, 2.0, 5.0, 10.0), generations=20, num_agents=24,
                     max_ticks=80, seed=113, _return=False):
    """EDR 113 : balaye scaffold_land (recompense du pas final) et evolue la navigation a chaque niveau
    (boucle evolve_nav EDR107, metab=0, Lewis vide d'apex, forage_payoff=3). Lit gen0 + plateau.
    Verdict AFFORDANCE LEVE / INERTE / AMBIGUE. Bras land=0 reproduit EDR107 (controle)."""
    with Harness(seed=seed, name="lewis_landing_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR113 : scaffold_land nav, levels={land_levels}, gen={generations}, "
              f"pop={num_agents}, max_ticks={max_ticks}, seed={base}.")
        prog = h.progress(len(land_levels), label="niveaux scaffold_land")
        arms = []
        for land in land_levels:
            cfg = _cfg(3, base_metabolism=0.0, trace_forage=True, scaffold_land=land)
            arms.append(_landing_arm(cfg, generations, num_agents, max_ticks,
                                     base + int(round(land * 10))))
            prog.update()
        return _report_landing(h, arms, generations, num_agents, max_ticks, _return)
```

- [ ] **Step 4: Run the full EDR 113 test file**

Run: `python -m pytest tests/sandbox/test_edr113_landing.py -v`
Expected: PASS (tous : 4 Task1 + 2 Task2 + 4 Task3 = 10). Le smoke `main_landing_nav` (deux runs 2-gen) est lent (~1-2 min) mais doit passer.

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr113_landing.py
git commit -m "feat(EDR113): _verdict_landing + _report + main_landing_nav (balayage + verdict)"
```

---

### Task 4: Run reel + doc EDR + memoire (controleur, APRES revue de code)

> **Non-TDD.** Execute par le controleur une fois Tasks 1-3 revues et fusionnees. AUCUN test
> relancé apres le run reel (ecraserait le JSON de provenance — lecon EDR 107).

**Files:**
- Create: `docs/EDR/113_<verdict-slug>.md` (titre = verdict, ASCII)
- Modify (memoire, hors worktree) : `lewis-energy-economy-wall.md` + `MEMORY.md`

- [ ] **Step 1: Lancer le run reel (seed 113, 4 bras, 20 gen)**

Run: `python -c "from tools.lewis_survival_sweep import main_landing_nav; main_landing_nav()"`
Expected: table 4 lignes (land 0.0/2.0/5.0/10.0), pente, delta, verdict. Capturer le stdout integral (provenance primaire ; `results/lewis_landing_nav_113.json` gitignore). Le bras land=0.0 doit reproduire ~0.36 (controle EDR107).

- [ ] **Step 2: Re-lancer une fois pour confirmer le determinisme**

Run: meme commande. Expected: trajectoires `p_reach` identiques a Step 1. Si divergence -> investiguer (memory_retriever ? graine ?) avant de rediger.

- [ ] **Step 3: Rediger le doc EDR**

Creer `docs/EDR/113_<slug>.md` selon le moule 110 : contexte (signal-direction existe, mur = pas final, hypothese EDR105), methode (scaffold_land balaye, double lecture gen0/plateau, bras 0 = controle 107), TABLE des 4 bras, pente, delta, VERDICT pre-enregistre atteint, lecture secondaire gen0, distinction vs EDR111 (aide vs demande), caveats (R=1 ; in-world repro non figee comme 107), suite. Titre = le verdict (slug ASCII).

- [ ] **Step 4: Mettre a jour la memoire**

Mettre a jour `lewis-energy-economy-wall.md` (chaine ...110 -> 113) et la ligne d'index `MEMORY.md`. Lier `[[lewis-energy-economy-wall]]`, `[[nas-bottleneck-is-substrate-not-search]]`. Selon le verdict : LEVE = 1er levier-monde positif (pivot vers le design de monde) ; INERTE = dernier levier-monde elimine (verrou substrat surdetermine).

- [ ] **Step 5: Commit doc EDR**

```bash
git add docs/EDR/113_*.md
git commit -m "docs(EDR113): verdict <verdict> (recompenser le pas final ...)"
```

---

## Notes de revue (pour le reviewer final)

- **Non-regression** : `scaffold_land` defaut 0.0 ; verifier que le terme ajoute est `* scaffold_land` (donc +0.0 a defaut) et place dans `if attacked_prey:` SANS gate `damage>0`. `git diff origin/main -- src/` ne doit toucher que ces 2 points + le champ config.
- **1 variable** : `_landing_arm` ne varie QUE via `cfg.scaffold_land` ; `mc`/graines/pop identiques entre bras (porte par main_landing_nav).
- **ASCII** : grep les `print` ajoutes pour fleche unicode/accents.
- **Seuils du verdict** : delta>=0.10 ; slope vs scaffold_land (lineaire) ; abs(slope)<0.01 pour INERTE — coherents avec la spec section 5.
- **Seeds** : run reel 113 ; smoke/determinisme 88113/99113 distincts (provenance).
- **Placement reward** : confirmer qu'il est verse pour TOUS gibiers (le test `test_landing_reward_is_paid_monotone` utilise un Lapin damage=0, que `scaffold_bighit` n'aurait PAS recompense).
