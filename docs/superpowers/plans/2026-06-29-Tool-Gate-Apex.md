# Tool-gate de l'apex — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre l'apex (chasse au mammouth) tool-gaté via un knob `mammoth_hp`, vérifier mécaniquement que le gate gate (pré-check de calibration), puis re-run l'A/B contrôle vs gate pour trancher si une stratégie craft→apex distincte émerge (répertoire enrichi) ou si l'apex s'effondre (verrou substrat).

**Architecture:** Un knob `mammoth_hp` sur `WorldConfig` (défaut 100 = non-régressif), lu au spawn du Mammouth et propagé par le probe via `EVP_MAMMOTH_HP` — même patron que `base_metabolism`/`forage_payoff`. Un helper de calibration analytique (constantes de combat RÉELLES) choisit/valide le hp de gate. Puis A/B contrôle (100) vs gate (validé) × 3 seeds sur `evolve_ceiling_probe`, lecture de `frac_tool`/`frac_apex` par ère.

**Tech Stack:** Python 3.13, `dataclasses`, pytest (marqueur `slow`), env `EVP_*`/`CT_*`/`EXPERIMENT_SEED`, helpers `src/environments/stone_economy.py`.

## Global Constraints

- **Tree partagé** : commits path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu. NE PAS stager `data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` (artefacts runtime concurrents).
- **Quiet-log** : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- **Sweet spot** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0`.
- **Non-régressif** : `mammoth_hp` défaut **100.0** = comportement byte-identique à l'actuel (le Mammouth spawne déjà à hp=100). `coop_reward` reste True (non touché). Les smokes existants restent verts.
- **Détection de succès du run par EXIT CODE python** (PAS grep sur log redirigé — piège EDR 108 : `2>/dev/null` avale `TRAJ` → grep échoue → JSON non copié).
- **Anti-théâtre** : le pré-check de calibration (bare échoue / lance réussit) DOIT passer AVANT le run évolutif ; trajectoire par ère ; contraste apparié ; le bras contrôle hp=100 DOIT reproduire l'apex 108/109 (~0.21 ère0, déclin) ; distinction explicite vs EDR 039/041 (autre levier `coop_reward=False`, instruments périmés).

---

### Task 1 : knob `mammoth_hp` câblé de bout en bout (config → monde → probe)

**Files:**
- Modify: `src/environments/config.py` (champ `mammoth_hp` sur `WorldConfig`, après `forage_payoff` `:76`)
- Modify: `src/worlds/world_1_stoneage.py` (`_spawn_prey_instance` `:299` — surcharge hp du Mammouth)
- Modify: `tools/evolve_ceiling_probe.py` (env `EVP_MAMMOTH_HP` → `config.mammoth_hp`, près des assignations `:56-58`)
- Test: `tests/sandbox/test_mammoth_hp_knob.py` (créer)

**Interfaces:**
- Produces : `WorldConfig.mammoth_hp: float` (défaut 100.0) ; le Mammouth spawné a `hp == config.mammoth_hp` ; `EVP_MAMMOTH_HP` (env) surcharge `config.mammoth_hp` dans `run_evolution`/`main` du probe.

- [ ] **Step 1 : Write the failing test**

Créer `tests/sandbox/test_mammoth_hp_knob.py` :

```python
# tests/sandbox/test_mammoth_hp_knob.py
import pytest

from src.environments.config import WorldConfig


def test_mammoth_hp_default_is_100():
    """Non-régression : le défaut reste 100.0 (comportement historique)."""
    assert WorldConfig().mammoth_hp == 100.0


@pytest.mark.slow
def test_spawned_mammoth_uses_config_hp(monkeypatch):
    """Le Mammouth spawné lit config.mammoth_hp ; les autres proies sont inchangées."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.worlds.world_1_stoneage import Biosphere3D
    cfg = WorldConfig()
    cfg.mammoth_hp = 250.0
    world = Biosphere3D(config=cfg)   # __init__ appelle _spawn_preys() -> 1 Mammouth + 3 Lapins + ...
    mammoths = [p for p in world.preys if p["type"] == "Mammouth"]
    lapins = [p for p in world.preys if p["type"] == "Lapin"]
    assert mammoths and all(m["hp"] == 250.0 for m in mammoths)
    assert lapins and all(l["hp"] == 1.0 for l in lapins)  # Lapin inchangé (PreyConfig.hp=1.0)
```

> Note d'ancrage : la classe du monde est `Biosphere3D(config: WorldConfig = None)` (`world_1_stoneage.py:24,33`) ; son `__init__` initialise `geometry`/`preys` et appelle `_spawn_preys()` (`:162`), qui spawne 1 Mammouth + 3 Lapins + 2 Cerfs + 2 Sangliers via `_spawn_prey_instance` (`:309-311`). Donc construire le monde suffit à exercer la surcharge de hp.

- [ ] **Step 2 : Run test to verify it fails**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_mammoth_hp_knob.py -v` (le 1er test ne nécessite pas `-m slow`)
Expected : FAIL — `AttributeError: 'WorldConfig' object has no attribute 'mammoth_hp'`.

- [ ] **Step 3 : Add the `mammoth_hp` field to WorldConfig**

Dans `src/environments/config.py`, juste APRÈS la ligne `forage_payoff: float = 1.0     # multiplicateur de la nutrition d'une proie (↑ = foraging plus payant)` (`:76`), ajouter :

```python
    # Tool-gate de l'apex (EDR 111) : hp du Mammouth. Défaut 100.0 = comportement historique
    # (non-régression bit-exacte). Relevé (~250) -> la riposte cumulée tue le pack mains-nues
    # avant le kill mais pas le pack-lance (5x plus efficace) -> l'outil devient nécessaire.
    mammoth_hp: float = 100.0
```

- [ ] **Step 4 : Read the config hp at Mammoth spawn**

Dans `src/worlds/world_1_stoneage.py`, `_spawn_prey_instance` (`:298-300`), remplacer :

```python
                cfg = self.config.preys.get(p_type, None)
                hp = cfg.hp if cfg else 1.0
                self.preys.append({"x": x, "y": y, "type": p_type, "stunned": 0, "hp": hp})
```

par :

```python
                cfg = self.config.preys.get(p_type, None)
                hp = cfg.hp if cfg else 1.0
                if p_type == "Mammouth":
                    hp = float(getattr(self.config, "mammoth_hp", hp))  # tool-gate EDR 111
                self.preys.append({"x": x, "y": y, "type": p_type, "stunned": 0, "hp": hp})
```

- [ ] **Step 5 : Run the test to verify it passes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_mammoth_hp_knob.py -v -m "slow or not slow"`
Expected : PASS — défaut 100.0 ; Mammouth spawné à 250.0 ; Lapin à 1.0.

- [ ] **Step 6 : Wire `EVP_MAMMOTH_HP` into the probe**

Dans `tools/evolve_ceiling_probe.py`, dans `run_evolution`, juste APRÈS la ligne `config.forage_payoff = float(os.environ.get("CT_PAYOFF", "3.0"))` (`:57`), ajouter :

```python
    config.mammoth_hp = float(os.environ.get("EVP_MAMMOTH_HP", "100"))   # tool-gate EDR 111 (100 = contrôle)
```

- [ ] **Step 7 : Non-regression — existing probe smokes still green**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_evolve_ceiling_probe.py tests/sandbox/test_diverse_selection.py -v -m slow`
Expected : PASS (les défauts inchangés : `EVP_MAMMOTH_HP` absent → 100 → comportement historique).

- [ ] **Step 8 : Commit (path-scoped)**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tools/evolve_ceiling_probe.py tests/sandbox/test_mammoth_hp_knob.py
git commit -m "feat(world): knob mammoth_hp (tool-gate apex EDR111) cable config->monde->probe, defaut 100 non-regressif

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2 : pré-check de calibration du gate (analytique, constantes RÉELLES)

**Files:**
- Create: `tools/tool_gate_calibration.py`
- Test: `tests/sandbox/test_tool_gate_calibration.py` (créer)

**Interfaces:**
- Consumes : `BASE_DAMAGE` (10.0), `SPEAR_DAMAGE` (50.0) de `src/environments/stone_economy.py` ; riposte du Mammouth = `WorldConfig().preys["Mammouth"].damage` (50.0) ; hp agent = `WorldConfig().agent.energy_max` (100.0).
- Produces : `gate_diagnostic(mammoth_hp, pack_size, *, config=None) -> dict` avec clés `bare_kills` (bool), `spear_kills` (bool), `gate_valid` (bool = `not bare_kills and spear_kills`), `break_pack_size` (int — la plus petite taille de pack mains-nues qui re-casse le gate à ce hp).

Modèle (ancré sur la mécanique réelle, `world_1_stoneage.py:592-700`) : un attaquant sur la case du Mammouth livre `weapon_damage` par tick et absorbe `riposte` par tick ; il survit `floor(agent_hp / riposte)` ticks d'attaque. Un pack de `P` livre donc au plus `survivable_ticks * P * weapon_damage` avant de mourir. Le pack TUE ssi ce total `>= mammoth_hp`.

- [ ] **Step 1 : Write the failing test**

Créer `tests/sandbox/test_tool_gate_calibration.py` :

```python
# tests/sandbox/test_tool_gate_calibration.py
from tools.tool_gate_calibration import gate_diagnostic


def test_control_hp_bare_hands_still_kills():
    """hp=100 (contrôle) : un pack mains-nues réaliste tue encore (reproduit l'actuel)."""
    d = gate_diagnostic(mammoth_hp=100.0, pack_size=5)
    assert d["bare_kills"] is True
    assert d["gate_valid"] is False


def test_gate_hp_blocks_bare_hands_but_not_spear():
    """hp=250 (gate) : le pack mains-nues échoue, le pack-lance réussit."""
    d = gate_diagnostic(mammoth_hp=250.0, pack_size=5)
    assert d["bare_kills"] is False
    assert d["spear_kills"] is True
    assert d["gate_valid"] is True


def test_break_pack_size_reported():
    """Le gate à hp=250 cède pour un pack mains-nues assez grand ; on le rapporte honnêtement.
    survivable_ticks=floor(100/50)=2 ; bare livre 2*P*10 ; casse ssi 20*P >= 250 -> P >= 13."""
    d = gate_diagnostic(mammoth_hp=250.0, pack_size=5)
    assert d["break_pack_size"] == 13
```

- [ ] **Step 2 : Run test to verify it fails**

Run : `python -m pytest tests/sandbox/test_tool_gate_calibration.py -v`
Expected : FAIL — `ModuleNotFoundError: No module named 'tools.tool_gate_calibration'`.

- [ ] **Step 3 : Implement the calibration helper**

Créer `tools/tool_gate_calibration.py` :

```python
"""Pré-check de calibration du tool-gate de l'apex (EDR 111).

Vérifie ANALYTIQUEMENT, à partir des constantes de combat RÉELLES, qu'un hp de Mammouth donné
« gate » l'apex : un pack mains-nues meurt de la riposte cumulée avant le kill, mais un pack-lance
(5x plus efficace) survit. C'est un garde-fou anti-théâtre : sans lui, l'A/B serait ininterprétable.

Mécanique modélisée (world_1_stoneage.py:592-700) : un attaquant sur la case du Mammouth livre
`weapon_damage`/tick et absorbe `riposte`/tick ; il survit `floor(agent_hp / riposte)` ticks. Un pack
de P livre au plus `survivable_ticks * P * weapon_damage` avant de mourir, et TUE ssi >= mammoth_hp.

NB : le verdict empirique reste l'A/B (le bras contrôle hp=100 doit reproduire l'apex 108/109).
Ce module choisit/valide le hp de gate AVANT de lancer.
"""
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.environments.stone_economy import BASE_DAMAGE, SPEAR_DAMAGE


def gate_diagnostic(mammoth_hp, pack_size, *, config=None):
    """Le hp donné gate-t-il l'apex pour un pack de `pack_size` ? Renvoie un dict de diagnostic."""
    config = config or WorldConfig()
    agent_hp = float(config.agent.energy_max)            # 100.0
    riposte = float(config.preys["Mammouth"].damage)     # 50.0
    survivable_ticks = math.floor(agent_hp / riposte) if riposte > 0 else 10 ** 9

    def kills(weapon_damage):
        delivered = survivable_ticks * pack_size * weapon_damage
        return delivered >= mammoth_hp

    bare_kills = kills(BASE_DAMAGE)
    spear_kills = kills(SPEAR_DAMAGE)
    # Plus petite taille de pack mains-nues qui re-casse le gate : survivable*P*BASE >= hp.
    per_agent_bare = survivable_ticks * BASE_DAMAGE
    break_pack_size = math.ceil(mammoth_hp / per_agent_bare) if per_agent_bare > 0 else 10 ** 9
    return {
        "mammoth_hp": float(mammoth_hp),
        "pack_size": int(pack_size),
        "survivable_ticks": int(survivable_ticks),
        "bare_kills": bool(bare_kills),
        "spear_kills": bool(spear_kills),
        "gate_valid": bool((not bare_kills) and spear_kills),
        "break_pack_size": int(break_pack_size),
    }


if __name__ == "__main__":
    hp = float(os.environ.get("GATE_HP", "250"))
    for p in (3, 5, 8, 12, 20):
        print(gate_diagnostic(hp, p))
```

- [ ] **Step 4 : Run the test to verify it passes**

Run : `python -m pytest tests/sandbox/test_tool_gate_calibration.py -v`
Expected : PASS — contrôle hp=100 bare tue ; gate hp=250 bare échoue / lance réussit ; `break_pack_size == 13`.

- [ ] **Step 5 : Sanity-print the gate across pack sizes**

Run : `python tools/tool_gate_calibration.py`
Expected : à hp=250, `gate_valid=True` pour packs 3/5/8/12 et `gate_valid=False` à partir de pack=13+ (`bare_kills=True`). Confirme le hp de gate retenu = **250** et la taille de rupture **13** (à rapporter dans l'EDR).

- [ ] **Step 6 : Commit (path-scoped)**

```bash
git add tools/tool_gate_calibration.py tests/sandbox/test_tool_gate_calibration.py
git commit -m "feat(probe): pre-check de calibration du tool-gate (bare echoue/lance reussit, constantes reelles)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3 : Re-run A/B contrôle vs gate + EDR 111 (pas de code applicatif)

**Files:**
- Create: `docs/EDR/111_<verdict>.md`

**Interfaces:**
- Consumes : Task 1 (`EVP_MAMMOTH_HP` → `config.mammoth_hp`) ; Task 2 (hp de gate validé = 250, break_pack_size = 13) ; sortie `results/evolve_ceiling_probe_0.json` (s'écrase).
- Produces : EDR documentant `frac_tool(ère)` + `frac_apex(ère)` par bras (contrôle 100 vs gate 250), et le verdict (issue 1 enrichi / issue 2 effondré).

- [ ] **Step 1 : Run contrôle (hp=100), seeds 0/1/2 (détection succès par exit code)**

```bash
SCRATCH="C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/eb814eca-e9fe-4f79-b0f7-d5d509e03b7b/scratchpad"
for s in 0 1 2; do
  if timeout 480 env AGISEED_QUIET_LOG=1 EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage \
      EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 \
      EVP_MAMMOTH_HP=100 CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=$s \
      python -u tools/evolve_ceiling_probe.py > "$SCRATCH/tg_ctrl_s${s}.log" 2>&1; then
    cp results/evolve_ceiling_probe_0.json "$SCRATCH/tg_ctrl_s${s}.json"; echo "OK ctrl_s$s"
  else echo "FAIL ctrl_s$s (exit $?)"; fi
done
```
**Détection de succès = exit code de python** (via `if timeout ... python ...; then`), PAS un grep sur la sortie (piège EDR 108).

- [ ] **Step 2 : Run gate (hp=250), seeds 0/1/2**

Idem Step 1 avec `EVP_MAMMOTH_HP=250`, sauver `tg_gate_s${s}.json` / `tg_gate_s${s}.log`.

- [ ] **Step 3 : Contrôle de cohérence (le bras contrôle reproduit 108/109)**

Moyenner `frac_apex(ère)` du bras contrôle (hp=100, 3 seeds). VÉRIFIER qu'il reproduit l'apex de 108/109 :
ère0 ≈ 0.228, ères tardives (6-11) ≈ 0.082. Si écart → signaler (non-repro). C'est le contrôle de validité
du harnais AVANT toute lecture du gate.

- [ ] **Step 4 : Lire frac_tool + frac_apex + verdict**

Moyenner par bras (3 seeds), trajectoire par ère :
- **`frac_tool`** (`spears_crafted`) : monte-t-il nettement sous gate (vs plancher ~0.016 en contrôle) ?
- **`frac_apex`** (`mammoth_kills`) : tenu (issue 1) ou effondré (issue 2) sous gate ?
- Lecture secondaire : `behavioral_diversity` / `bdiv_spears` (le tier lance sort-il du plancher ?).
- **Verdict** :
  - **Issue 1 (enrichi)** : `frac_tool` ↑ ET `frac_apex` tenu → le monde exigeait une 2ᵉ stratégie, elle émerge → répertoire-monde = levier confirmé.
  - **Issue 2 (effondré)** : `frac_apex` ↓↓ ET `frac_tool` au plancher → le substrat ne porte pas l'outil sous demande → verrou substrat/architecture (converge EDR 107).
  - Transition partielle (apex baisse, tool monte un peu) → décrire, ne pas surclaim.

- [ ] **Step 5 : Vérifier le prochain numéro EDR libre**

Run : `git fetch origin main --quiet; { ls docs/EDR/; git show origin/main:docs/EDR | tail -n +3; } | grep -oE "^1[01][0-9]" | sort -u | tail` — confirmer **111** libre (109 = ce thread ; 110 = capacity-nav réservé session Lewis).

- [ ] **Step 6 : Écrire l'EDR 111**

Créer `docs/EDR/111_<verdict>.md` : contexte (convergence 104-109 → répertoire-monde ; coop court-circuite l'outil EDR 096) ; **manipulation** (knob `mammoth_hp` 100→250, gate via riposte) ; **pré-check de calibration** (Task 2 : bare échoue / lance réussit à hp=250, `break_pack_size=13` rapporté comme limite honnête) ; table `frac_tool(ère)` + `frac_apex(ère)` par bras ; contraste apparié contrôle vs gate ; contrôle de cohérence (contrôle = 108/109) ; verdict (issue 1 / 2) ; **distinction EDR 039/041** (autre levier `coop_reward=False`, instruments périmés avant EDR 096/058) ; caveat taille de pack (gate cède au-delà de 12 mains-nues — les `n` observés sont-ils sous ce seuil ?) ; liens `[[coop-competence-is-population-property]]` / `[[nas-bottleneck-is-substrate-not-search]]` / `[[lewis-energy-economy-wall]]` (si issue 2) + EDR 109 ; statut + suite.

- [ ] **Step 7 : Commit (path-scoped)**

```bash
git add docs/EDR/111_*.md
git commit -m "docs(EDR111): tool-gate de l'apex -> craft emerge (repertoire) vs apex effondre (substrat)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- Knob `mammoth_hp` sur `WorldConfig` défaut 100 (spec Unité 1) → Task 1 Step 3. ✅
- Lecture au spawn du Mammouth, autres proies inchangées (spec Unité 1) → Task 1 Step 4. ✅
- `EVP_MAMMOTH_HP` → config (spec Unité 3) → Task 1 Step 6. ✅
- Pré-check de calibration bare échoue/lance réussit, constantes réelles (spec Unité 2) → Task 2. ✅
- A/B contrôle vs gate × 3 seeds, détection par exit code (spec Unité 3) → Task 3 Steps 1-2. ✅
- frac_tool + frac_apex par ère, verdict issue 1/2 (spec Instrument) → Task 3 Step 4. ✅
- Cohérence contrôle = 108/109 (spec Contrôles) → Task 3 Step 3. ✅
- Distinction EDR 039/041 (spec Contrôles) → Task 3 Step 6. ✅
- Non-régression hp=100 byte-identique (spec Tests) → Task 1 Steps 1, 7. ✅
- EDR 111 (spec Variables) → Task 3 Steps 5-6. ✅

**2. Placeholder scan :** `<verdict>` (Task 3 nom de fichier) résolu en Step 4-6 (intentionnel). Pas de TBD/TODO ; code complet pour chaque step de code.

**3. Type consistency :** `mammoth_hp` (float) cohérent config→world (`getattr(self.config, "mammoth_hp", hp)`)→probe (`config.mammoth_hp = float(...)`). `gate_diagnostic(mammoth_hp, pack_size, *, config=None) -> dict` avec clés `bare_kills`/`spear_kills`/`gate_valid`/`break_pack_size` cohérentes entre Step 3 (def) et les asserts du test (Step 1). Constantes `BASE_DAMAGE`/`SPEAR_DAMAGE` importées de `stone_economy`, riposte/energy_max lus de `WorldConfig` (réels). `EVP_MAMMOTH_HP` défaut "100" cohérent avec le défaut config 100.0.
