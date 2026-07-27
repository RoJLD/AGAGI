# Monde à demande cognitive in-world — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Réaliser la recette S2-006 dans la biosphère stoneage derrière un flag `cognitive_demand` (défaut OFF), et prouver via l'ablation-perception in-world que la survie devient perception-SENSIBLE (oracle) — flip du NEUTRE de S2-003.

**Architecture:** Deux blocs GUARDÉS (défaut OFF) dans `world_1_stoneage.py` : un signal 2-bits global par tick (dans `bit_a/bit_b` de l'obs) + une récompense d'énergie quand l'agent se déplace dans la direction signalée, les gains standard étant neutralisés au RUN (`forage_payoff=0` + `base_metabolism` dur, leviers config existants). Un nouvel outil `tools/cognitive_demand_inworld.py` fournit un oracle lecteur-de-signal + son ablation et lance le demand-marker. Rien d'autre du monde n'est modifié ; OFF = strictement legacy.

**Tech Stack:** Python 3, numpy, pytest. Réutilise `tools/s2_demand.py` (run_condition/WORLDS), `tools/s2_demand_ablation.py` (derange_rows/PerceptionAblatedMamba), `tools/demand_marker.py`, `src/agents/baseline_models.py` (BaselineBatchModel), `src/worlds/world_1_stoneage.py` (Biosphere3D).

## Global Constraints

- Le mode est OFF PAR DÉFAUT et strictement non-régressif : tout le code monde est guardé `if getattr(self.config, "cognitive_demand", False):`. OFF ⇒ zéro chemin modifié.
- NE PAS modifier `tools/s2_demand.py`. IMPORTER seulement.
- Commits path-scopés (`git add <fichiers exacts>`, jamais `-A`/`.`). Pas de sessions // (mais règles git robla : commit uniquement dans les steps du plan).
- Signal 2-bits : `a,b ∈ {-1,+1}` ; direction correcte `dir = 2*(a>0) + (b>0) ∈ {0,1,2,3}` (mêmes 4 directions que les moves, world_1 action 0=N/1=S/2=O/3=E).
- Obs : `bit_a` = colonne index **12**, `bit_b` = index **13** (column_stack world_1:567-580).
- `_resolve_biology(self, agent, action, logits)` (world_1:644) reçoit l'action choisie `action = argmax(logits[:8])` (world_1:1205).
- Windows : préfixer `PYTHONIOENCODING=utf-8`. Racine repo `c:/Users/robla/VScode_Project/AGAGI`.
- Verdicts via `demand_marker.ablation_verdict` (garde-fou n≥12).

---

## File Structure
- **Modify** `src/environments/config.py` — ajouter `cognitive_demand: bool = False` et `cog_gain: float = 6.0` à `WorldConfig`.
- **Modify** `src/worlds/world_1_stoneage.py` — (a) fixer `self._cog_signal` en tête de `step()` ; (b) signal global dans l'obs (guardé) ; (c) récompense signal-matchée + skip gains standard dans `_resolve_biology` (guardé).
- **Create** `tests/test_cognitive_demand_world.py` — non-régression OFF + mécanique ON.
- **Create** `tools/cognitive_demand_inworld.py` — `CognitiveOracleBatchModel`, `CognitiveOracleAblated`, `run_cog_demand_map`, `main`.
- **Create** `tests/test_cognitive_demand_inworld.py` — décodage oracle + smoke opt-in.
- **Create** `docs/EDR/S2-009_Cognitive_Demand_World_InWorld_Recipe_Realized.md`.
- **Modify** `docs/REF/REF-DEMAND-MARKER.md` — adopt_for + ligne table.

---

## Task 1 : Flag config + mécanique monde guardée (défaut OFF non-régressif)

**Files:**
- Modify: `src/environments/config.py` (WorldConfig)
- Modify: `src/worlds/world_1_stoneage.py` (`step` tête, `get_batch_observations`, `_resolve_biology`)
- Test: `tests/test_cognitive_demand_world.py`

**Interfaces:**
- Produces : `WorldConfig.cognitive_demand: bool`, `WorldConfig.cog_gain: float` ; `Biosphere3D._cog_signal: tuple(float,float)` (posé chaque tick) ; comportement : en mode ON, `_resolve_biology` ajoute `cog_gain` à l'énergie ssi `action == dir(signal)`, et saute le scaffold d'approche + le gain fruit ; l'obs porte le signal en colonnes 12/13.

- [ ] **Step 1 : Écrire les tests d'échec**

```python
# tests/test_cognitive_demand_world.py
import numpy as np
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _fresh_world(cognitive_demand, cog_gain=6.0, base_metabolism=1.0):
    env = Biosphere3D()
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000
    env.config.cognitive_demand = cognitive_demand
    env.config.cog_gain = cog_gain
    env.config.base_metabolism = base_metabolism
    env.config.forage_payoff = 0.0            # neutralise la chasse (mode ON : corps insuffisant)
    return env


def test_off_mode_is_non_regressive():
    # OFF : pas d'attribut de signal exploité, l'énergie décroît par métabolisme comme avant (pas de cog_gain)
    env = _fresh_world(cognitive_demand=False, base_metabolism=1.0)
    a = MambaAgent(); env.add_agent(a, energy=50.0)
    e0 = env.agents[0]["energy"]
    env.step()
    assert env.agents[0]["energy"] < e0        # métabolisme draine, aucun cog_gain injecté


def test_on_mode_rewards_signal_matched_direction():
    # ON : forcer le signal, appeler _resolve_biology avec l'action == direction correcte -> +cog_gain net
    env = _fresh_world(cognitive_demand=True, cog_gain=6.0, base_metabolism=0.1)
    a = MambaAgent(); env.add_agent(a, energy=50.0)
    ag = env.agents[0]
    env._cog_signal = (1.0, 1.0)               # dir = 2*(1>0)+(1>0) = 3
    ag["energy"] = 50.0
    env._resolve_biology(ag, action=3, logits=np.zeros(120))   # action correcte
    correct_e = ag["energy"]
    ag["energy"] = 50.0
    env._resolve_biology(ag, action=0, logits=np.zeros(120))   # action fausse
    wrong_e = ag["energy"]
    assert correct_e > wrong_e                  # matcher le signal paie l'énergie
    assert correct_e - wrong_e >= 5.0           # ~cog_gain (6.0) de différentiel


def test_on_mode_signal_in_obs_columns_12_13():
    # ON : le signal global est présent dans l'obs (colonnes bit_a=12, bit_b=13) pour tous les agents
    env = _fresh_world(cognitive_demand=True)
    for _ in range(3):
        env.add_agent(MambaAgent(), energy=50.0)
    env._cog_signal = (1.0, -1.0)
    obs = env.get_batch_observations()
    assert np.allclose(obs[:, 12], 1.0)         # bit_a global
    assert np.allclose(obs[:, 13], -1.0)        # bit_b global
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_cognitive_demand_world.py -q`
Expected: FAIL (`_cog_signal` non posé / pas de cog_gain / obs non globale) — `test_on_mode_*` échouent ; `test_off_mode` peut passer déjà (c'est le contrôle non-régression).

- [ ] **Step 3 : Config — ajouter les champs**

Dans `src/environments/config.py`, classe `WorldConfig` (après `forage_payoff`, l. ~76) :

```python
    cognitive_demand: bool = False   # S2-009 : mode demande cognitive (défaut OFF, non-régressif).
    cog_gain: float = 6.0            # énergie payée quand l'agent bouge dans la direction signalée (mode ON).
```

- [ ] **Step 4 : world_1 — poser le signal en tête de `step()`**

Dans `src/worlds/world_1_stoneage.py`, au DÉBUT de `def step(self):` (l. 1062, avant tout traitement, et impérativement avant `get_batch_observations` l. 1126) :

```python
        if getattr(self.config, "cognitive_demand", False):
            self._cog_signal = (float(np.random.choice([-1.0, 1.0])),
                                float(np.random.choice([-1.0, 1.0])))   # signal 2-bits GLOBAL de CE tick
```

(np.random = flux global seedé par le Harness → appariement préservé.)

- [ ] **Step 5 : world_1 — signal global dans l'obs (guardé)**

Dans `get_batch_observations`, juste APRÈS le remplissage altar-gated de `bit_a`/`bit_b` (world_1:449-455, avant le `column_stack` l.567) :

```python
        if getattr(self.config, "cognitive_demand", False):
            sig = getattr(self, "_cog_signal", (1.0, 1.0))
            bit_a[:] = sig[0]        # signal GLOBAL (tous agents le voient), pas altar-gated
            bit_b[:] = sig[1]
```

- [ ] **Step 6 : world_1 — récompense signal-matchée + skip gains standard (guardé)**

Dans `_resolve_biology` : (a) envelopper le scaffold d'approche (world_1:679-685) ET le gain fruit (world_1:694-704) dans `if not getattr(self.config, "cognitive_demand", False):` (en mode ON, aucun raccourci corporel) ; (b) à la FIN de `_resolve_biology`, ajouter :

```python
        if getattr(self.config, "cognitive_demand", False):
            sig = getattr(self, "_cog_signal", (1.0, 1.0))
            correct_dir = 2 * (sig[0] > 0) + (sig[1] > 0)     # ∈ {0,1,2,3}
            if action == correct_dir:
                agent["energy"] = min(self.config.agent.energy_max,
                                      agent["energy"] + getattr(self.config, "cog_gain", 6.0))
```

- [ ] **Step 7 : Lancer les tests, vérifier le succès**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_cognitive_demand_world.py -q`
Expected: PASS (3 tests).

- [ ] **Step 8 : Non-régression globale du monde (OFF inchangé)**

Run: `RUN_SLOW=1 PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_torch_throw_gate_world.py tests/test_observability.py -q`
Expected: PASS (le mode OFF ne touche aucun chemin ; ces tests exercent world_1 en mode legacy).

- [ ] **Step 9 : Commit (path-scopé)**

```bash
git add src/environments/config.py src/worlds/world_1_stoneage.py tests/test_cognitive_demand_world.py
git commit -m "feat(S2-009): flag cognitive_demand sur stoneage (signal-matché + skip gains standard, défaut OFF)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : Oracle lecteur-de-signal + son ablation + outil de run

**Files:**
- Create: `tools/cognitive_demand_inworld.py`
- Test: `tests/test_cognitive_demand_inworld.py`

**Interfaces:**
- Consumes : `WorldConfig.cognitive_demand/cog_gain` (Task 1) ; `from tools.s2_demand import run_condition, WORLDS` ; `from tools.s2_demand_ablation import derange_rows` ; `from tools.demand_marker import ablation_verdict` ; `from src.agents.baseline_models import BaselineBatchModel`.
- Produces : `CognitiveOracleBatchModel(BaselineBatchModel)` (décode bit_a/bit_b idx 12/13 → logits sur la direction correcte) ; `CognitiveOracleAblated(CognitiveOracleBatchModel)` (derange l'obs avant décodage) ; `run_cog_demand_map(seed, K, num_agents, max_ticks, base_metabolism, cog_gain) -> dict {on: {ratio, verdict}, off: {ratio, verdict}}`.

- [ ] **Step 1 : Écrire les tests d'échec**

```python
# tests/test_cognitive_demand_inworld.py
import os
import numpy as np
import pytest
from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, CognitiveOracleAblated


class _Ag:
    def __init__(self, O=120):
        self.genome = type("G", (), {"num_outputs": O})()
        self.surprise = 0.0; self.surprise_momentum = 0.0


def test_oracle_picks_signal_direction():
    agents = [_Ag(), _Ag()]
    m = CognitiveOracleBatchModel(agents)
    obs = np.zeros((2, 20), dtype=np.float32)
    obs[0, 12] = 1.0;  obs[0, 13] = 1.0     # dir = 3
    obs[1, 12] = -1.0; obs[1, 13] = 1.0     # dir = 1
    logits, _ = m.forward(obs)
    assert int(np.argmax(logits[0, :8])) == 3
    assert int(np.argmax(logits[1, :8])) == 1


def test_oracle_ablated_decorrelates(monkeypatch):
    # l'oracle ablé décode un signal DÉRANGÉ -> au moins un agent reçoit une autre direction
    np.random.seed(0)
    agents = [_Ag() for _ in range(6)]
    obs = np.zeros((6, 20), dtype=np.float32)
    for i in range(6):
        obs[i, 12] = 1.0 if i % 2 else -1.0
        obs[i, 13] = 1.0
    intact, _ = CognitiveOracleBatchModel(agents).forward(obs)
    ablated, _ = CognitiveOracleAblated(agents).forward(obs)
    assert not np.array_equal(np.argmax(intact[:, :8], 1), np.argmax(ablated[:, :8], 1))
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_cognitive_demand_inworld.py::test_oracle_picks_signal_direction -q`
Expected: FAIL — `ModuleNotFoundError: tools.cognitive_demand_inworld`.

- [ ] **Step 3 : Implémenter l'outil**

```python
# tools/cognitive_demand_inworld.py
"""S2-009 — Réalise la recette S2-006 IN-WORLD (flag cognitive_demand sur stoneage) et prouve via
l'ablation-perception que la survie devient perception-SENSIBLE (oracle) — flip du NEUTRE de S2-003.

Oracle = lecteur-de-signal câblé (décode bit_a/bit_b de l'obs → direction correcte) : preuve DÉCISIVE que
le monde EXIGE la perception (intact survit, ablé s'effondre), indépendamment du crédit. Contraste mode OFF
(doit rester NEUTRE). Réutilise run_condition (seam batch_model_cls) + derange_rows + ablation_verdict.

Usage : python tools/cognitive_demand_inworld.py  (env: CDI_SEED, CDI_K, CDI_AGENTS, CDI_TICKS, CDI_METAB, CDI_COG)
REF-DEMAND-MARKER. NE modifie PAS s2_demand.
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.baseline_models import BaselineBatchModel
from tools.s2_demand_ablation import derange_rows
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS

BIT_A, BIT_B = 12, 13                                  # colonnes du signal dans l'obs (world_1 column_stack)


class CognitiveOracleBatchModel(BaselineBatchModel):
    """Décode le signal (bit_a/bit_b) → logits favorisant la direction correcte dir=2*(a>0)+(b>0)."""

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
        b = batch_obs[:, BIT_B] if batch_obs.shape[1] > BIT_B else np.ones(self.B)
        dirs = (2 * (a > 0) + (b > 0)).astype(int)
        for i in range(self.B):
            logits[i, dirs[i]] = 1.0
        return logits


class CognitiveOracleAblated(CognitiveOracleBatchModel):
    """Oracle recevant l'obs DÉRANGÉE (within-subject) → décode le signal d'un pair → rate."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _median_survival(cond):
    s = cond.get("survival") or []
    return float(np.median(s)) if s else 0.0


def _run_mode(cognitive_demand, seed, K, num_agents, max_ticks, base_metabolism, cog_gain):
    """Configure le régime (via un world_cls partiel) puis oracle intact vs ablé → verdict."""
    from src.worlds.world_1_stoneage import Biosphere3D

    def make_world():
        env = Biosphere3D()
        env.config.cognitive_demand = cognitive_demand
        env.config.cog_gain = cog_gain
        env.config.base_metabolism = base_metabolism
        env.config.forage_payoff = 0.0                # neutralise la chasse (corps insuffisant en ON)
        return env

    intact = run_condition(make_world, CognitiveOracleBatchModel, None, seed,
                           num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    ablated = run_condition(make_world, CognitiveOracleAblated, None, seed,
                            num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    v = ablation_verdict(intact["era_survival"], ablated["era_survival"])
    verdict = ("PERCEPTION_DEMANDED" if v["collapse"] and v["n"] >= 12
               else "NEUTRAL" if v["decoy"] else "MIXED")
    return {"ratio": v["ratio"], "verdict": verdict, "n": v["n"]}


def run_cog_demand_map(seed=2026, K=12, num_agents=12, max_ticks=200, base_metabolism=4.0, cog_gain=6.0):
    """Oracle intact vs ablé, mode ON vs OFF. ON attendu SENSIBLE (PERCEPTION_DEMANDED), OFF NEUTRE."""
    return {
        "on": _run_mode(True, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
        "off": _run_mode(False, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
    }


def main():
    seed = int(os.environ.get("CDI_SEED", "2026"))
    K = int(os.environ.get("CDI_K", "12"))
    num_agents = int(os.environ.get("CDI_AGENTS", "12"))
    max_ticks = int(os.environ.get("CDI_TICKS", "200"))
    metab = float(os.environ.get("CDI_METAB", "4.0"))
    cog = float(os.environ.get("CDI_COG", "6.0"))
    m = run_cog_demand_map(seed, K, num_agents, max_ticks, metab, cog)
    print(f"\n=== S2-009 — recette cognitive IN-WORLD (oracle, seed={seed}, K={K}, metab={metab}, cog={cog}) ===")
    print(f"{'mode':6s} {'ratio':>7s}  verdict")
    for mode in ("on", "off"):
        r = m[mode]
        print(f"{mode:6s} {r['ratio']:7.2f}  {r['verdict']} (n={r['n']})")
    print("\nAttendu : ON=PERCEPTION_DEMANDED (ratio>>1, le monde exige la perception) / OFF=NEUTRAL "
          "(ratio~1) -> la recette S2-006 flip la survie IN-WORLD. -> Rédiger EDR-S2-009.")
    return m


if __name__ == "__main__":
    main()
```

- [ ] **Step 4 : Lancer les tests unitaires, vérifier le succès**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_cognitive_demand_inworld.py::test_oracle_picks_signal_direction tests/test_cognitive_demand_inworld.py::test_oracle_ablated_decorrelates -q`
Expected: PASS (2 tests).

- [ ] **Step 5 : Smoke test opt-in**

```python
# append to tests/test_cognitive_demand_inworld.py
@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="run in-world lourd")
def test_cog_demand_map_smoke():
    from tools.cognitive_demand_inworld import run_cog_demand_map
    m = run_cog_demand_map(seed=2026, K=2, num_agents=6, max_ticks=60, base_metabolism=4.0, cog_gain=6.0)
    assert set(m) == {"on", "off"}
    for mode in ("on", "off"):
        assert set(m[mode]) == {"ratio", "verdict", "n"}
        assert m[mode]["ratio"] > 0.0
```

Run: `RUN_SLOW=1 PYTHONIOENCODING=utf-8 python -m pytest tests/test_cognitive_demand_inworld.py::test_cog_demand_map_smoke -q`
Expected: PASS (l'outil tourne 1 monde K=2 sans crash).

- [ ] **Step 6 : Commit (path-scopé)**

```bash
git add tools/cognitive_demand_inworld.py tests/test_cognitive_demand_inworld.py
git commit -m "feat(S2-009): oracle lecteur-de-signal + ablation in-world (preuve du flip perception-sensible)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3 : Run décisif + calibration + EDR-S2-009 + REF + mémoire

**Files:**
- Create: `docs/EDR/S2-009_Cognitive_Demand_World_InWorld_Recipe_Realized.md`
- Modify: `docs/REF/REF-DEMAND-MARKER.md`
- Modify (mémoire hors repo) : `s2-world-demand-thread.md`, `within-subject-demand-marker.md`

**Interfaces:** Consomme `run_cog_demand_map` (Task 2).

- [ ] **Step 1 : Calibrer le régime (corps insuffisant) puis lancer le run décisif**

Run: `CDI_K=12 CDI_METAB=4.0 CDI_COG=6.0 PYTHONIOENCODING=utf-8 python tools/cognitive_demand_inworld.py | tee results/s2_009_cog_demand.txt`

Attendu : `on` = `PERCEPTION_DEMANDED` (ratio ≫ 1), `off` = `NEUTRAL` (ratio ~1). **Calibration si `on` n'est pas SENSIBLE** : c'est que le régime n'a pas rendu le corps insuffisant OU l'oracle sature au cap. Ajuster et relancer : monter `CDI_METAB` (5.0, 6.0) pour durcir le corps ; vérifier que l'oracle intact NE sature PAS à `max_ticks` (si intact == cap partout, monter METAB) et que l'ablé s'effondre. Documenter la valeur retenue. Copier la carte pour l'EDR. (`results/` gitignored.)

- [ ] **Step 2 : Écrire l'EDR-S2-009 depuis le run**

```markdown
# docs/EDR/S2-009_Cognitive_Demand_World_InWorld_Recipe_Realized.md
---
id: EDR-S2-009
type: EDR
title: "La recette de demande cognitive RÉALISÉE in-world : la survie stoneage devient perception-SENSIBLE (flip S2-003)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-006 donnait la recette (corps insuffisant + demande structurée + devise de survie) en SIM. Tient-elle
DANS la biosphère ? Peut-on rendre la survie stoneage causalement perceptive (flip du NEUTRE in-world S2-003) ?

## Méthode
Flag `cognitive_demand` sur stoneage (`config.py` + `world_1_stoneage.py`, guardé défaut OFF) : signal
2-bits global (bit_a/bit_b de l'obs) → direction nourricière correcte ; s'y déplacer paie `cog_gain` en
ÉNERGIE ; gains standard neutralisés au run (`forage_payoff=0` + `base_metabolism` dur = corps insuffisant).
Oracle lecteur-de-signal (`tools/cognitive_demand_inworld.py`) intact vs ablé (obs dérangée), mode ON vs
OFF ; verdict via demand_marker (n=12 ères). metab=<retenu>, cog_gain=6.0.

## Résultats
<!-- COLLER results/s2_009_cog_demand.txt -->
| mode | ratio | verdict |
|---|---|---|
| ON  | ... | ... |
| OFF | ... | ... |

## Verdict
<COGNITIVE_DEMAND_RECIPE_REALIZED_INWORLD si ON SENSIBLE & OFF NEUTRE> — la recette S2-006 rend la survie
stoneage causalement perceptive IN-WORLD (l'ablation-perception de l'oracle effondre la survie ~Nx en ON,
inerte en OFF). Flip décisif du NEUTRE de S2-003 : le monde N'EXIGEAIT pas la perception par construction
d'objectif, pas par incapacité ; en satisfaisant les 3 conditions, il l'exige. Portée in-world établie.

## Portée & limites
Oracle = preuve que le monde EXIGE la perception (pas que le CRÉDIT in-world l'apprend — sonde intra-vie
= suite). Flag guardé défaut OFF (non-régressif). cog food = direction-signalée (proxy fidèle du mécanisme).
Converge S2-004→008, REF-DEMAND-MARKER, [[s2-world-demand-thread]].
```

- [ ] **Step 3 : REF — adopt_for + ligne table**

Dans `docs/REF/REF-DEMAND-MARKER.md` : ajouter `EDR-S2-009` à `adopt_for` ; ajouter ligne :
`| recette in-world | EDR-S2-009 | flag cognitive_demand stoneage, oracle intact/ablé | ON=PERCEPTION_DEMANDED (flip), OFF=NEUTRE → recette réalisée in-world |`

- [ ] **Step 4 : Vérifier le graphe**

Run: `PYTHONIOENCODING=utf-8 python tools/consolidate_records.py` → attendu `problemes=0`.
Run: `PYTHONIOENCODING=utf-8 python tools/check_record_links.py --report` → 0 NOUVEL orphelin.

- [ ] **Step 5 : Mémoire projet (hors repo, PAS de git add)**

Éditer `s2-world-demand-thread.md` + `within-subject-demand-marker.md` : ajouter S2-009 = recette réalisée
in-world (oracle flip la survie stoneage perception-SENSIBLE en ON / NEUTRE en OFF), avec le verdict réel.

- [ ] **Step 6 : Commit (path-scopé)**

```bash
git add docs/EDR/S2-009_Cognitive_Demand_World_InWorld_Recipe_Realized.md docs/REF/REF-DEMAND-MARKER.md
git commit -m "docs(S2-009): EDR recette cognitive réalisée in-world (flip perception-sensible) + REF

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4 (exploratoire, best-effort) : sonde crédit intra-vie

**Files:** Modify `tools/cognitive_demand_inworld.py` (ajouter un arm intra-vie) + EDR addendum.

**But :** répondre « le CRÉDIT in-world (REINFORCE, `use_torch_inworld`) apprend-il la nourriture cognitive ? ». Arm SECONDAIRE — ne bloque pas le livrable (l'oracle a déjà tranché « le monde exige »).

- [ ] **Step 1 : Lire l'API d'apprentissage in-world**

Lire dans `src/worlds/world_1_stoneage.py` comment `use_torch_inworld` / `_torch_pop` / `learn_episode` sont pilotés (autour de `def step` l.1062 et `def _learn_throw_gate` l.951-1010, et l'appel `learn_episode`), et `src/seed_ai/harness.py` pour le montage cohorte torch. Noter la séquence exacte pour : cohorte fraîche `use_torch_inworld=True`, `benchmark_mode=True`, K ères, apprentissage REINFORCE par ère.

- [ ] **Step 2 : Implémenter `run_credit_probe(...)` dans l'outil**

Ajouter une fonction qui monte une cohorte `use_torch_inworld=True` en mode `cognitive_demand`, la fait tourner K ères, mesure la survie médiane PAR ère (tendance = signal d'apprentissage), puis, si la cohorte survit significativement au-dessus du plancher, rejoue l'ablation (obs dérangée) → verdict. Code concret selon l'API relevée en Step 1 (séquence d'apprentissage identique à `_learn_throw_gate`).

- [ ] **Step 3 : Lancer + addendum EDR**

Run: `CDI_K=12 ... python tools/cognitive_demand_inworld.py --credit-probe` (ou une var d'env). Ajouter à l'EDR-S2-009 une section « Sonde crédit » : la survie monte-t-elle sur les ères (crédit apprend) ? Si oui, ablation SENSIBLE ; si non, verdict honnête « le monde exige mais le crédit n'apprend pas dans le budget » (finding fort, pinpointe le crédit — cohérent [[decisive-substrate-thesis-test]]).

- [ ] **Step 4 : Commit (path-scopé)**

```bash
git add tools/cognitive_demand_inworld.py docs/EDR/S2-009_Cognitive_Demand_World_InWorld_Recipe_Realized.md
git commit -m "feat(S2-009): sonde crédit intra-vie (use_torch_inworld) + addendum EDR"
```

---

## Self-Review (auteur du plan)

**Couverture spec :** §2 mécanique (flag+signal+reward+skip) → Task 1 ; §3 oracle+intra-vie → Task 2 (oracle) + Task 4 (intra-vie) ; §4 test demand-marker ON/OFF → Task 2/3 ; §5 tests → Task 1/2 ; §6 records → Task 3 ; §7 commits path-scopés → chaque Task ; §8 risques (guardé OFF, oracle décisif, suppression via config) → Task 1/2. ✅

**Placeholders :** aucun dans le CODE. L'EDR §Résultats est rempli DEPUIS le run (Task 3 Step 1→2) = donnée d'expérience. Task 4 Step 1-2 = arm exploratoire dont le code dépend d'une API à relever (marqué best-effort, ne bloque pas le livrable oracle).

**Cohérence des types :** `cognitive_demand`/`cog_gain` (config) ; `_cog_signal` tuple ; `dir=2*(a>0)+(b>0)` identique en obs (Task1 Step5), reward (Task1 Step6), oracle (Task2 Step3) ; colonnes 12/13 constantes `BIT_A/BIT_B` ; `run_cog_demand_map`→{on,off}→{ratio,verdict,n} identiques Task2/3.
