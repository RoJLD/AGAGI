# EDR 093 — Sweep Économie d'Énergie : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/lewis_survival_sweep.py` (EDR 093) : balayer `forage_payoff` et mesurer la survie médiane des champions stoneage en Lewis à létalité 0, pour localiser (ou réfuter) un premier barreau survivable.

**Architecture:** Un fichier outil (pattern `coevolve_use_long.py`/`lethality_curriculum.py`). Pas d'évolution, pas de langage : pure mesure de survie des champions répliqués, par niveau de `forage_payoff`, appariée par seed entre niveaux. Réutilise le socle 090 mergé (`_setup_critical`, `_disable_kuzu`, `exp_stats`, `Harness`).

**Tech Stack:** Python 3, numpy (pur), pytest. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR093-Lewis-Survival-Sweep-design.md`.

## Global Constraints

- **1 variable** : `forage_payoff` ∈ `(3, 6, 12, 24, 48)`. Tout le reste fixe.
- Fixes gelés : `base_metabolism=0.25`, `N_APEX=12`, `leurre_frac=0`, `PREY_COUNT=15`, `max_ticks=300`, `num_agents=24`, `n_eval=8`, `R=4`, gate survie `120`, `max_population=150` (défensif).
- **Pas d'évolution, pas de langage** (`use_ref_head=False`, `decode_act=False`, champions répliqués via `_reproduce`).
- Reproductibilité : `_disable_kuzu()` avant toute création de monde ; `seed_at(seed, 0)` par ère ; mêmes seeds entre niveaux (appariement).
- Survie = **âge par agent** (`agent["age"]`) sur le pool (`env.agents + env.dead_agents`), agrégé en médiane par niveau.
- Cause de mort : `energy <= 0` = famine ; `hp <= 0 and energy > 0` = combat.
- Commits path-scopés (sessions parallèles) ; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Create:** `tools/lewis_survival_sweep.py` — tout le harnais EDR 093.
- **Create:** `tests/sandbox/test_lewis_survival_sweep.py` — tests unitaires.
- **Untouched:** aucun artefact existant modifié (réutilisation par import).

---

## Task 1: Scaffold + helpers purs (`_cfg`, `_verdict`)

**Files:**
- Create: `tools/lewis_survival_sweep.py`
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Produces : `LEVELS=(3,6,12,24,48)`, `METAB=0.25`, `N_APEX=12`, `PREY_COUNT=15`, `MAX_TICKS=300`, `GATE=120.0` ; `_cfg(forage_payoff) -> WorldConfig` ; `_verdict(levels, medians, gate=GATE) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_lewis_survival_sweep.py
import numpy as np
import pytest
from tools import lewis_survival_sweep as lss


def test_cfg_sets_payoff_metab_cap():
    cfg = lss._cfg(12)
    assert cfg.forage_payoff == 12.0
    assert cfg.base_metabolism == 0.25
    assert cfg.max_population == 150


def test_verdict_three_branches():
    levels = (3, 6, 12, 24, 48)
    # franchit le gate des le niveau 12 (<=24) -> barreau trouve
    assert lss._verdict(levels, [10, 50, 130, 200, 260]) == "BARREAU TROUVE"
    # ne franchit qu'a 48 (x16) -> trop cher
    assert lss._verdict(levels, [10, 20, 40, 90, 150]) == "BARREAU TROP CHER"
    # ne franchit jamais -> pas de rung
    assert lss._verdict(levels, [5, 8, 10, 30, 60]) == "PAS DE RUNG"
    # franchit des le 1er niveau accessible (24) -> trouve
    assert lss._verdict(levels, [10, 20, 100, 121, 130]) == "BARREAU TROUVE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.lewis_survival_sweep'`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/lewis_survival_sweep.py
"""tools/lewis_survival_sweep.py — EDR 093 : un premier barreau survivable en Lewis existe-t-il ?
Balaye forage_payoff (revenu/kill) et mesure la survie mediane des champions stoneage en Lewis a
letalite 0 (isole l'energie). PAS d'evolution, PAS de langage. Fonde sur le diagnostic post-090 :
mort par FAMINE (actions -10 x densite apex >> forage), pas letalite.
Pre-enregistrement : docs/superpowers/specs/2026-06-24-EDR093-Lewis-Survival-Sweep-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical
from tools.lethality_curriculum import _disable_kuzu

METAB = 0.25                       # sweet-spot energie 085 (fixe)
LEVELS = (3, 6, 12, 24, 48)        # forage_payoff balaye : de 085 vers x16
N_APEX = 12                        # densite d'apex (fixe, comme 088/090)
PREY_COUNT = 15                    # forage food non-rare (= defaut WorldConfig)
MAX_TICKS = 300
NUM_AGENTS = 24
GATE = 120.0                       # survie mediane minimale d'un barreau survivable (089/090)
CHEAP_MAX = 24                     # forage_payoff <= 24 (x8) = barreau "acceptable" ; 48 (x16) = trop cher


def _cfg(forage_payoff):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    return cfg


def _verdict(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau) -> 3 branches pre-enregistrees. Le 1er niveau qui franchit
    le gate determine le verdict : <=CHEAP_MAX -> barreau trouve ; sinon (seulement 48) -> trop cher ;
    aucun -> pas de rung (la depense est le mur)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "PAS DE RUNG"
    return "BARREAU TROUVE" if min(crossed) <= CHEAP_MAX else "BARREAU TROP CHER"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr093-lewis-survival"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR093): scaffold + helpers purs (_cfg, _verdict)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `_measure_survival` — survie + causes + kills des champions

**Files:**
- Modify: `tools/lewis_survival_sweep.py`
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_disable_kuzu` (déjà importé).
- Produces : `_measure_survival(cfg, seeds, leurre_frac=0.0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS) -> {"ticks": list[int], "famine": int, "combat": int, "kills": list[float]}`. `ticks` = âges de TOUS les agents (pool = vivants + morts) sur toutes les ères ; `kills` = mammoth_kills moyen/agent par ère.

- [ ] **Step 1: Write the failing test**

```python
def test_measure_survival_keys_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3)
    a = lss._measure_survival(cfg, seeds=[7, 8], num_agents=4, max_ticks=30)
    b = lss._measure_survival(cfg, seeds=[7, 8], num_agents=4, max_ticks=30)
    assert set(a) == {"ticks", "famine", "combat", "kills"}
    assert len(a["kills"]) == 2                       # un kills moyen par ere (2 seeds)
    assert len(a["ticks"]) >= 8                        # >= num_agents par ere, pool inclut les morts
    assert all(0 <= t <= 30 for t in a["ticks"])       # ages bornes par max_ticks
    assert a == b                                      # seede -> reproductible
    assert a["famine"] + a["combat"] <= len(a["ticks"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_keys_and_reproducible -q`
Expected: FAIL (`AttributeError: ... '_measure_survival'`).

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/lewis_survival_sweep.py` :

```python
def _measure_survival(cfg, seeds, leurre_frac=0.0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
    """Mesure la survie des CHAMPIONS (repliques, pas d'evolution) en Lewis a letalite leurre_frac.
    Une ere par seed (appariement entre niveaux : meme seed -> meme monde initial). memory_retriever
    stoppe avant la boucle. Renvoie ages (pool), causes de mort (famine/combat), kills moyens/ere."""
    mc = MutationConfig(weight_init_std=2.0)
    champs = _load_champions()
    ticks, famine, combat, kills = [], 0, 0, []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, leurre_frac, n_apex=N_APEX)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
        env.use_ref_head = False
        env.decode_act = False
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        ticks.extend(int(ag.get("age", 0)) for ag in pool)
        famine += sum(1 for ag in pool if ag.get("energy", 1.0) <= 0)
        combat += sum(1 for ag in pool if ag.get("hp", 1.0) <= 0 and ag.get("energy", 1.0) > 0)
        kills.append(float(np.mean([ag.get("mammoth_kills", 0) for ag in pool])) if pool else 0.0)
    return {"ticks": ticks, "famine": famine, "combat": combat, "kills": kills}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_measure_survival_keys_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr093-lewis-survival"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR093): _measure_survival (survie + causes de mort + kills des champions)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_report` + `main` — sweep, médianes, JT, verdict, provenance

**Files:**
- Modify: `tools/lewis_survival_sweep.py`
- Test: `tests/sandbox/test_lewis_survival_sweep.py`

**Interfaces:**
- Consumes : `_cfg`, `_measure_survival`, `_verdict`, `st.jonckheere_terpstra`, `Harness`, `_disable_kuzu`.
- Produces : `main(levels=LEVELS, n_eval=8, R=4, seed=None, _return=False)`. Avec `_return=True`, renvoie `{"levels", "medians", "jt", "verdict", "table"}`.

- [ ] **Step 1: Write the failing test**

```python
def test_main_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main(levels=(3, 48), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main(levels=(3, 48), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [3, 48]
    assert set(a["table"][3]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"BARREAU TROUVE", "BARREAU TROP CHER", "PAS DE RUNG"}
```

(NB : ce test tourne une vraie simulation réduite ; il peut prendre ~30-60 s.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main'`).

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/lewis_survival_sweep.py` :

```python
def _report(h, levels, groups, R, n_eval, _return):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    verdict = _verdict(levels, medians)
    table = {}
    print(f"\n=== EDR093 sweep forage_payoff : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        table[lv] = {"median": med, "famine": g["famine"], "combat": g["combat"],
                     "mean_kills": mk, "n": n}
        print(f"  payoff={lv:<3} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
              f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"levels": list(levels), "R": R, "n_eval": n_eval, "medians": medians,
            "jt": jt, "verdict": verdict, "table": {str(k): v for k, v in table.items()}})
    if _return:
        return {"levels": list(levels), "medians": medians, "jt": jt,
                "verdict": verdict, "table": table}


def main(levels=LEVELS, n_eval=8, R=4, seed=None, _return=False):
    with Harness(seed=seed, name="lewis_survival_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR093 : sweep forage_payoff={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux forage_payoff")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(lv), seeds))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py::test_main_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Run the full test file + commit**

Run: `python -m pytest tests/sandbox/test_lewis_survival_sweep.py -q`
Expected: PASS (4 tests).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr093-lewis-survival"
git -C "$WT" add tools/lewis_survival_sweep.py tests/sandbox/test_lewis_survival_sweep.py
git -C "$WT" commit -m "feat(EDR093): _report + main (sweep, medianes, JT, verdict pre-enregistre)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Run direct (EXÉCUTION) — la mesure + le verdict

**Files:** aucun (exécution du harnais).

- [ ] **Step 1: Smoke (bout-en-bout réduit, ~1 min)**

Run (depuis le worktree) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr093-lewis-survival"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; print(lss.main(levels=(3,12,48), n_eval=3, R=1, seed=21, _return=True)['verdict'])" 2>/dev/null
```
Expected : imprime la table + un verdict ∈ {BARREAU TROUVE, BARREAU TROP CHER, PAS DE RUNG}, sans erreur.

- [ ] **Step 2: Run complet (params gelés, ~quelques min)**

Run :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr093-lewis-survival"
HEADLESS=1 PYTHONUNBUFFERED=1 python -c "from tools import lewis_survival_sweep as lss; lss.main(seed=193)" 2>/dev/null
```
Expected : table survie × `forage_payoff` (5 niveaux, R=4, n_eval=8), JT, verdict. Provenance dans `results/lewis_survival_sweep_193.json`.

- [ ] **Step 3: Décision (documentée, pas de code)** — écrire l'EDR 093 selon la branche atteinte :
  - **BARREAU TROUVE** → premier rung survivable à payoff X (apex intacts) ; base d'un curriculum corrigé.
  - **BARREAU TROP CHER** → un rung existe mais à ×16 ; économie profondément cassée.
  - **PAS DE RUNG** → la dépense (actions −10) est le mur (vérifier `kills≈0` au niveau haut) ; pivot vers coûts d'action / `N_APEX`.

---

## Self-Review (auteur du plan)

**1. Spec coverage :**
- §2 variable `forage_payoff` (3..48), reste fixe → T1 (`_cfg`, `LEVELS`), T2 (mesure). ✓
- §3 métrique survie médiane + JT + verdict 3 branches → T1 (`_verdict`), T3 (`_report` médianes+JT). ✓
- §3 sous-produits famine/combat + kills → T2 (`_measure_survival` les renvoie), T3 (table). ✓
- §4 params gelés → T1 (constantes), T3 (`main` défauts R=4/n_eval=8). ✓
- §5 réutilisation (`_setup_critical`, `_disable_kuzu`, `exp_stats`, `Harness`, `_load_champions`, `_reproduce`) → T1/T2 imports. ✓
- §5 pairing seeds entre niveaux → T3 (`seeds` indépendant du niveau). ✓
- §6 tests (cfg, measure, verdict, main) → T1/T2/T3. ✓
- §7 run direct → T4. ✓
- §8 `_disable_kuzu` avant monde → T3 (`main` l'appelle avant la boucle) + tests l'appellent. ✓

**2. Placeholder scan :** aucun TBD ; code complet à chaque step ; commandes exactes. ✓

**3. Type consistency :** `_cfg(payoff)->WorldConfig` (T1) consommé par T2/T3. `_measure_survival(...)->{ticks,famine,combat,kills}` (T2) consommé par `_report` (T3) qui lit `g["ticks"]/["kills"]/["famine"]/["combat"]`. `_verdict(levels, medians)` (T1) appelé par `_report` (T3). Cohérent. ✓
