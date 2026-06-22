# EDR 090 — Curriculum de Létalité : Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/lethality_curriculum.py` (EDR 090) : un harnais qui co-évolue une population sur le monde de Lewis en **rampant la létalité** (`leurre_frac 0.17→0.83`, porté par la maîtrise) et compare, au palier terminal, le substrat **curriculum vs flat** (cold start), apparié par seed — pour tester si le curriculum casse le chicken-and-egg d'EDR 089.

**Architecture:** Un seul fichier outil (mirroir de `tools/coevolve_use_long.py`), réutilisant les briques validées : `_setup_critical` (bouton de létalité, EDR 088), `has_graduated`/`GraduationConfig` (porte de maîtrise dormante, `src/curriculum/runner.py`), `exp_stats` (stats numpy pures), `Harness`/`seed_at` (appariement D1), `_reproduce`/`_load_champions`. Runner séquentiel + multiprocess (`mp == seq`). Pure survie/évitement — **pas de langage** (têtes référentielles, `decode_act`, FIABLE/BRUITÉ → EDR 091).

**Tech Stack:** Python 3, numpy (pur, pas de scipy), pytest, `ProcessPoolExecutor`. Pré-enregistrement : `docs/superpowers/specs/2026-06-22-EDR090-Lethality-Curriculum-design.md`.

---

## File Structure

- **Create:** `tools/lethality_curriculum.py` — tout le harnais EDR 090 (un fichier, suit le pattern `coevolve_use_long.py`).
- **Create:** `tests/sandbox/test_lethality_curriculum.py` — tests unitaires (mirroir de `tests/sandbox/test_coevolve_use_long.py`).
- **Untouched:** aucun artefact 087/088/089 modifié. Réutilisation par import seulement.

**Conventions de seed (par répétition, base = `rb`) — plages disjointes :**
- Curriculum, palier `idx`, ère `e` : `seed_at(rb + 10000 + idx*1000 + e)`.
- Flat, ère `e` : `seed_at(rb + 20000 + e)`.
- Mesure terminale, ère `i` : `seed_at(rb + 30000 + i)` — **identique entre les deux bras** (appariement de la mesure).
- Répétitions disjointes : `rb = base + r*100000` (100000 ≫ 30000+).

---

## Task 1: Scaffold + helpers purs (`_lethal_cfg`, `_survival_competence`, `_verdict`)

**Files:**
- Create: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_lethality_curriculum.py
import numpy as np
import pytest
from tools import lethality_curriculum as lc


def test_lethal_cfg_is_sweet_spot():
    cfg = lc._lethal_cfg()
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0


def test_survival_competence_bounds_and_median():
    assert lc._survival_competence([], max_ticks=300) == 0.0          # vide -> 0
    assert lc._survival_competence([150], max_ticks=300) == 0.5       # médiane normalisée
    assert lc._survival_competence([600], max_ticks=300) == 1.0       # clip haut
    assert lc._survival_competence([60, 120, 300], max_ticks=300) == pytest.approx(120 / 300)


def test_verdict_three_branches():
    # gate échoué (survie <= 120) -> négatif profond, peu importe les stats
    assert lc._verdict(90.0, wilcoxon_p=0.01, med=5.0, lo=2.0) == "NEGATIF PROFOND"
    # gate ok + effet significatif positif -> casse le bootstrap
    assert lc._verdict(150.0, wilcoxon_p=0.01, med=5.0, lo=2.0) == "CASSE LE BOOTSTRAP"
    # gate ok mais effet non significatif / IC traverse 0 -> pas le goulot
    assert lc._verdict(150.0, wilcoxon_p=0.20, med=1.0, lo=-1.0) == "PAS LE GOULOT"
    assert lc._verdict(150.0, wilcoxon_p=0.01, med=-1.0, lo=-3.0) == "PAS LE GOULOT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.lethality_curriculum'`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/lethality_curriculum.py
"""tools/lethality_curriculum.py — EDR 090 : un curriculum de létalité casse-t-il le chicken-and-egg
d'EDR 089 ? Variable unique = curriculum (rampe leurre_frac 0.17→0.83, porté par la maîtrise via
has_graduated dormant) vs flat (cold start à 0.83), apparié par seed, budget d'ères égal. Pure
survie/évitement (PAS de langage : têtes/decode_act/FIABLE-BRUITÉ → EDR 091).
Pré-enregistrement : docs/superpowers/specs/2026-06-22-EDR090-Lethality-Curriculum-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.curriculum.runner import GraduationConfig, has_graduated
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical

METAB, PAYOFF = 0.25, 3.0          # sweet spot survie longue (EDR 085)
PREY_COUNT = 15                    # forage food ; respawn n'ajoute JAMAIS Leurre/Ours -> n'altère pas
                                   # leurre_frac (= défaut WorldConfig ; explicite par robustesse).
LEVELS = (0.17, 0.33, 0.50, 0.67, 0.83)   # rampe de létalité (terminal = niveau décisif d'088)
N_APEX = 12
MAX_TICKS = 300
GATE = 120.0                       # survie médiane terminale minimale (gate de validité, comme 089)


def _grad_cfg():
    """Porte de maîtrise gelée (pré-enreg §5). Réutilise GraduationConfig dormant."""
    return GraduationConfig(window=4, eps_plateau=0.02, c_floor=0.5, patience=2, max_eras=10)


def _lethal_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _survival_competence(ticks_list, max_ticks=MAX_TICKS):
    """Compétence ∈[0,1] = survie médiane normalisée. À leurre_frac élevé, survivre EXIGE d'éviter les
    Leurres -> proxy d'évitement consommable par has_graduated (qui attend une compétence bornée)."""
    if len(ticks_list) == 0:
        return 0.0
    return float(np.clip(np.median(ticks_list) / max_ticks, 0.0, 1.0))


def _verdict(sc_med, wilcoxon_p, med, lo):
    """Règle de verdict pré-enregistrée (§4). sc_med = survie médiane curriculum au terminal."""
    if sc_med <= GATE:
        return "NEGATIF PROFOND"
    if wilcoxon_p < 0.05 and med > 0 and lo > 0:
        return "CASSE LE BOOTSTRAP"
    return "PAS LE GOULOT"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): scaffold + helpers purs (cfg, survival_competence, verdict)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `_run_era_clean` — l'ère déterministe à létalité réglable

**Files:**
- Modify: `tools/lethality_curriculum.py` (ajouter la fonction)
- Test: `tests/sandbox/test_lethality_curriculum.py` (ajouter le test)

- [ ] **Step 1: Write the failing test**

```python
def test_run_era_clean_keys_and_reproducible():
    cfg = lc._lethal_cfg()
    seed_from = __import__("src.seed_ai.harness", fromlist=["seed_at"]).seed_at
    champs = lc._load_champions()
    seed_from(7, 0)
    g = lc._reproduce(champs, 4, lc.MutationConfig(weight_init_std=2.0))
    seed_from(7, 0)
    a = lc._run_era_clean(cfg, g, leurre_frac=0.5, max_ticks=20)
    seed_from(7, 0)
    b = lc._run_era_clean(cfg, g, leurre_frac=0.5, max_ticks=20)
    assert set(a) == {"ticks", "kills", "leurre_hits", "survivors", "scored"}
    assert a["ticks"] == b["ticks"] and a["kills"] == b["kills"]      # seedé -> reproductible
    assert a["leurre_hits"] == b["leurre_hits"]
    assert len(a["scored"]) <= 5 and a["ticks"] <= 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_run_era_clean_keys_and_reproducible -q`
Expected: FAIL (`AttributeError: module ... has no attribute '_run_era_clean'`).

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/lethality_curriculum.py` :

```python
def _run_era_clean(cfg, genomes, leurre_frac, max_ticks=MAX_TICKS):
    """Une ère DÉTERMINISTE à létalité leurre_frac. _setup_critical pose les apex (Leurre dmg=50) ;
    memory_retriever stoppé AVANT la boucle (hazard mémoire ambiante KuzuDB, dette core d'089) ;
    forage food = PREY_COUNT. PAS de langage (use_ref_head/decode_act = False). Renvoie toujours
    {ticks,kills,leurre_hits,survivors,scored} (scored = top-5 (life_score, genome) pour la sélection)."""
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
    scored = sorted(
        [(calculate_life_score(a), a["model"].genome if "model" in a else a.get("genome")) for a in pool],
        key=lambda sg: sg[0], reverse=True,
    )[:5]
    return {
        "ticks": t,
        "kills": int(sum(ag.get("mammoth_kills", 0) for ag in pool)),
        "leurre_hits": int(getattr(env, "leurre_hits", 0)),
        "survivors": len(env.agents),
        "scored": scored,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_run_era_clean_keys_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _run_era_clean (ère déterministe à létalité réglable)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_coevolve_at` — co-évolution d'UN palier jusqu'à graduation

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_coevolve_at_shape_and_caps():
    cfg = lc._lethal_cfg()
    mc = lc.MutationConfig(weight_init_std=2.0)
    gcfg = lc.GraduationConfig(window=2, eps_plateau=0.02, c_floor=0.0, patience=1, max_eras=3)
    start = lc._load_champions()
    genomes, eras, history, graduated = lc._coevolve_at(
        cfg, mc, leurre_frac=0.5, start_genomes=start, grad_cfg=gcfg,
        base=1234, num_agents=4, max_ticks=20,
    )
    assert 1 <= eras <= 3                       # borné par max_eras
    assert len(history) == eras                 # une compétence par ère tenue
    assert len(genomes) == 5                    # top-5 portés
    assert all(0.0 <= c <= 1.0 for c in history)
    # reproductible
    g2, e2, h2, _ = lc._coevolve_at(cfg, mc, 0.5, start, gcfg, 1234, 4, 20)
    assert e2 == eras and h2 == history
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_coevolve_at_shape_and_caps -q`
Expected: FAIL (`AttributeError: ... '_coevolve_at'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _coevolve_at(cfg, mc, leurre_frac, start_genomes, grad_cfg, base, num_agents, max_ticks=MAX_TICKS):
    """Co-évolue UN palier de létalité jusqu'à graduation (has_graduated + patience K) ou max_eras
    (garde-temps). seed_at(base, era) -> reproductible. Compétence par ère = survie normalisée.
    Renvoie (best_genomes_top5, eras_held, history, graduated)."""
    best = [(0.0, g) for g in start_genomes]
    history, streak, graduated, era = [], 0, False, 0
    while era < grad_cfg.max_eras:
        era += 1
        seed_at(base, era)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        r = _run_era_clean(cfg, genomes, leurre_frac, max_ticks=max_ticks)
        history.append(_survival_competence([r["ticks"]], max_ticks))
        best = sorted(best + r["scored"], key=lambda sg: sg[0], reverse=True)[:5]
        if has_graduated(history, grad_cfg):
            streak += 1
            if streak >= grad_cfg.patience:
                graduated = True
                break
        else:
            streak = 0
    return [g for _s, g in best], era, history, graduated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_coevolve_at_shape_and_caps -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _coevolve_at (un palier jusqu'à graduation via has_graduated)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `_run_curriculum_arm` — enchaîner les paliers + transcript

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_curriculum_arm_transcript():
    cfg = lc._lethal_cfg()
    mc = lc.MutationConfig(weight_init_std=2.0)
    gcfg = lc.GraduationConfig(window=2, eps_plateau=0.02, c_floor=0.0, patience=1, max_eras=2)
    levels = (0.33, 0.83)
    genomes, total_eras, transcript = lc._run_curriculum_arm(
        cfg, mc, levels, gcfg, base=999, num_agents=4, max_ticks=20,
    )
    assert len(transcript) == 2                                   # une entrée par palier
    assert [row["level"] for row in transcript] == [0.33, 0.83]   # ordre croissant
    assert all(set(row) == {"level", "eras", "competence", "graduated"} for row in transcript)
    assert total_eras == sum(row["eras"] for row in transcript)   # budget = somme des paliers
    assert len(genomes) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_curriculum_arm_transcript -q`
Expected: FAIL (`AttributeError: ... '_run_curriculum_arm'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _run_curriculum_arm(cfg, mc, levels, grad_cfg, base, num_agents, max_ticks=MAX_TICKS):
    """Enchaîne les paliers de létalité (ordre croissant) en PORTANT les génomes d'un palier au
    suivant. base = rb + 10000 ; palier idx seedé sur base + idx*1000 (plages disjointes). Renvoie
    (final_genomes, total_eras, transcript) ; transcript = diagnostic 'où ça bloque' (une entrée/palier)."""
    genomes = _load_champions()
    transcript, total_eras = [], 0
    for idx, lf in enumerate(levels):
        genomes, eras, history, graduated = _coevolve_at(
            cfg, mc, lf, genomes, grad_cfg, base + idx * 1000, num_agents, max_ticks,
        )
        total_eras += eras
        transcript.append({
            "level": lf,
            "eras": eras,
            "competence": history[-1] if history else 0.0,
            "graduated": graduated,
        })
    return genomes, total_eras, transcript
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_curriculum_arm_transcript -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _run_curriculum_arm (enchaîne paliers + transcript diagnostic)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `_run_flat_arm` — cold start au terminal, budget matché

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_flat_arm_budget_and_reproducible():
    cfg = lc._lethal_cfg()
    mc = lc.MutationConfig(weight_init_std=2.0)
    a = lc._run_flat_arm(cfg, mc, terminal_frac=0.83, budget_eras=3, base=555, num_agents=4, max_ticks=20)
    b = lc._run_flat_arm(cfg, mc, terminal_frac=0.83, budget_eras=3, base=555, num_agents=4, max_ticks=20)
    assert len(a) == 5                          # top-5 portés
    # reproductible : mêmes génomes (comparaison via life_score sur ère seedée identique)
    seed_at = lc.seed_at
    seed_at(42, 0); ra = lc._run_era_clean(cfg, a, 0.83, max_ticks=20)
    seed_at(42, 0); rb = lc._run_era_clean(cfg, b, 0.83, max_ticks=20)
    assert ra["kills"] == rb["kills"] and ra["ticks"] == rb["ticks"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_flat_arm_budget_and_reproducible -q`
Expected: FAIL (`AttributeError: ... '_run_flat_arm'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _run_flat_arm(cfg, mc, terminal_frac, budget_eras, base, num_agents, max_ticks=MAX_TICKS):
    """CONTRÔLE : cold start directement au palier terminal pour EXACTEMENT budget_eras ères
    (= total curriculum de la même répétition -> budget égal). base = rb + 20000 ; seed_at(base, era).
    Pas de porte de maîtrise : on tourne tout le budget au terminal."""
    best = [(0.0, g) for g in _load_champions()]
    for era in range(1, budget_eras + 1):
        seed_at(base, era)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        r = _run_era_clean(cfg, genomes, terminal_frac, max_ticks=max_ticks)
        best = sorted(best + r["scored"], key=lambda sg: sg[0], reverse=True)[:5]
    return [g for _s, g in best]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_flat_arm_budget_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _run_flat_arm (cold start terminal, budget matché par seed)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `_measure_terminal` — net + survie au palier terminal (apparié)

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_measure_terminal_keys_and_reproducible():
    cfg = lc._lethal_cfg()
    mc = lc.MutationConfig(weight_init_std=2.0)
    genomes = lc._load_champions()
    a = lc._measure_terminal(cfg, mc, genomes, leurre_frac=0.83, base=321, num_agents=4, n_eval=3, max_ticks=20)
    b = lc._measure_terminal(cfg, mc, genomes, leurre_frac=0.83, base=321, num_agents=4, n_eval=3, max_ticks=20)
    assert set(a) == {"nets", "survs"}
    assert len(a["nets"]) == 3 and len(a["survs"]) == 3
    assert a == b                               # seedé (base+30000-style) -> apparié/reproductible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_measure_terminal_keys_and_reproducible -q`
Expected: FAIL (`AttributeError: ... '_measure_terminal'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _measure_terminal(cfg, mc, genomes, leurre_frac, base, num_agents, n_eval, max_ticks=MAX_TICKS):
    """Mesure n_eval ères propres au palier terminal sur la population évoluée. base = rb + 30000,
    IDENTIQUE entre curriculum et flat -> mesure appariée (mêmes mondes). net = kills − leurre_hits
    (qualité de discrimination) ; surv = ticks (survie de l'ère, gate >120 comme 089)."""
    nets, survs = [], []
    for i in range(n_eval):
        seed_at(base, i)
        gen = _reproduce(genomes, num_agents, mc)
        r = _run_era_clean(cfg, gen, leurre_frac, max_ticks=max_ticks)
        nets.append(int(r["kills"]) - int(r["leurre_hits"]))
        survs.append(int(r["ticks"]))
    return {"nets": nets, "survs": survs}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_measure_terminal_keys_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _measure_terminal (net + survie appariés au palier terminal)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `_one_rep_core` + `_report` + `main` (séquentiel)

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_main_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gcfg = lc.GraduationConfig(window=2, eps_plateau=0.02, c_floor=0.0, patience=1, max_eras=2)
    a = lc.main(R=2, levels=(0.33, 0.83), num_agents=4, n_eval=2, grad_cfg=gcfg,
                seed=3, max_ticks=20, _return=True)
    b = lc.main(R=2, levels=(0.33, 0.83), num_agents=4, n_eval=2, grad_cfg=gcfg,
                seed=3, max_ticks=20, _return=True)
    assert a["d_nets"] == b["d_nets"]                              # apparié/seedé -> identique
    assert len(a["d_nets"]) == 2
    assert "verdict" in a and "surv_med" in a
    assert len(a["transcripts"]) == 2 and len(a["transcripts"][0]) == 2   # R reps × len(levels)
    assert a["verdict"] in {"NEGATIF PROFOND", "CASSE LE BOOTSTRAP", "PAS LE GOULOT"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_main_runs_and_reproducible -q`
Expected: FAIL (`AttributeError: ... 'main'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _one_rep_core(cfg, mc, levels, grad_cfg, num_agents, n_eval, max_ticks, rb):
    """Une répétition COMPLÈTE (curriculum + flat appariés au même rb) : co-évolue les deux bras,
    mesure les deux au terminal (mondes de mesure identiques) -> diff appariée d_net + survies."""
    cur_genomes, total_eras, transcript = _run_curriculum_arm(
        cfg, mc, levels, grad_cfg, rb + 10000, num_agents, max_ticks)
    flat_genomes = _run_flat_arm(
        cfg, mc, levels[-1], total_eras, rb + 20000, num_agents, max_ticks)
    mc_meas = _measure_terminal(cfg, mc, cur_genomes, levels[-1], rb + 30000, num_agents, n_eval, max_ticks)
    mf_meas = _measure_terminal(cfg, mc, flat_genomes, levels[-1], rb + 30000, num_agents, n_eval, max_ticks)
    return {
        "d_net": float(np.mean(mc_meas["nets"]) - np.mean(mf_meas["nets"])),
        "net_curr": float(np.mean(mc_meas["nets"])),
        "net_flat": float(np.mean(mf_meas["nets"])),
        "surv_curr": list(mc_meas["survs"]),
        "surv_flat": list(mf_meas["survs"]),
        "transcript": transcript,
        "total_eras": total_eras,
    }


def _report(h, reps, R, levels, _return):
    """Stats appariées + verdict pré-enregistré + provenance. reps = liste de dicts _one_rep_core."""
    d_nets = [r["d_net"] for r in reps]
    surv_curr = [s for r in reps for s in r["surv_curr"]]
    net_curr = [r["net_curr"] for r in reps]
    net_flat = [r["net_flat"] for r in reps]
    transcripts = [r["transcript"] for r in reps]
    summ = st.paired_summary(d_nets)
    med = float(np.median(d_nets))
    lo, hi = st.bootstrap_ci(d_nets, np.mean, seed=h.seed)
    sc_med = float(np.median(surv_curr)) if surv_curr else 0.0
    verdict = _verdict(sc_med, summ["wilcoxon_p"], med, lo)
    print(f"\n=== net (kills−leurre_hits) au terminal {levels[-1]:.2f} : "
          f"CURRICULUM {np.mean(net_curr):.2f} vs FLAT {np.mean(net_flat):.2f} ({R} reps appariées) ===")
    print(f"  d (CURR−FLAT net) = {summ['mean']:+.2f} +/- {summ['se']:.2f} SE ; win {summ['win_rate']*100:.0f}% ; "
          f"Wilcoxon p={summ['wilcoxon_p']:.3f} ; médiane={med:+.2f} ; IC95=[{lo:+.2f},{hi:+.2f}]")
    print(f"  survie médiane curriculum = {sc_med:.0f} ticks (gate >{GATE:.0f})")
    print("=== VERDICT (pré-enregistré) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "levels": list(levels), "d_nets": d_nets, "net_curr": net_curr, "net_flat": net_flat,
            "summary": summ, "median": med, "ci": [lo, hi], "surv_med": sc_med,
            "transcripts": transcripts, "verdict": verdict})
    if _return:
        return {"d_nets": d_nets, "summary": summ, "median": med, "ci": [lo, hi],
                "surv_med": sc_med, "verdict": verdict, "transcripts": transcripts}


def main(R=8, levels=LEVELS, num_agents=24, n_eval=8, grad_cfg=None, seed=None, max_ticks=MAX_TICKS, _return=False):
    grad_cfg = grad_cfg or _grad_cfg()
    with Harness(seed=seed, name="lethality_curriculum", with_db=False) as h:
        base = h.seed
        cfg = _lethal_cfg()
        mc = MutationConfig(weight_init_std=2.0)
        print(f"EDR090 : curriculum de létalité vs flat. R={R}, levels={levels}, seed={base}.")
        reps = []
        prog = h.progress(R, label="répétitions curriculum vs flat")
        for r in range(R):
            rb = base + r * 100000
            np.random.seed(rb)
            reps.append(_one_rep_core(cfg, mc, levels, grad_cfg, num_agents, n_eval, max_ticks, rb))
            prog.update()
        return _report(h, reps, R, levels, _return)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_main_runs_and_reproducible -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _one_rep_core + _report + main (séquentiel, verdict pré-enregistré)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: `_one_rep` + `main_mp` (multiprocess, `mp == seq`)

**Files:**
- Modify: `tools/lethality_curriculum.py`
- Test: `tests/sandbox/test_lethality_curriculum.py`

- [ ] **Step 1: Write the failing test**

```python
def test_main_mp_matches_sequential(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gcfg = lc.GraduationConfig(window=2, eps_plateau=0.02, c_floor=0.0, patience=1, max_eras=2)
    seq = lc.main(R=2, levels=(0.33, 0.83), num_agents=4, n_eval=2, grad_cfg=gcfg,
                  seed=3, max_ticks=20, _return=True)
    mp = lc.main_mp(R=2, levels=(0.33, 0.83), num_agents=4, n_eval=2, grad_cfg=gcfg,
                    seed=3, max_ticks=20, n_procs=2, _return=True)
    assert mp["d_nets"] == seq["d_nets"]          # IDENTIQUE -> mp == seq déterministe
    assert mp["verdict"] == seq["verdict"] and mp["surv_med"] == seq["surv_med"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_main_mp_matches_sequential -q`
Expected: FAIL (`AttributeError: ... 'main_mp'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _one_rep(args):
    """Une répétition dans un process isolé. os.chdir(work_dir) -> hall_of_fame.pkl / results/
    identiques au parent ; np.random.seed(rb) -> état global identique au séquentiel. Silence le bruit."""
    import logging, warnings, os
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    rb, levels, num_agents, n_eval, grad_cfg, max_ticks, work_dir = args
    os.chdir(work_dir)
    np.random.seed(rb)
    cfg = _lethal_cfg()
    mc = MutationConfig(weight_init_std=2.0)
    return _one_rep_core(cfg, mc, levels, grad_cfg, num_agents, n_eval, max_ticks, rb)


def main_mp(R=8, levels=LEVELS, num_agents=24, n_eval=8, grad_cfg=None, seed=None,
            n_procs=4, max_ticks=MAX_TICKS, _return=False):
    from concurrent.futures import ProcessPoolExecutor
    grad_cfg = grad_cfg or _grad_cfg()
    with Harness(seed=seed, name="lethality_curriculum", with_db=False) as h:
        base = h.seed
        print(f"EDR090 MULTIPROCESS : R={R}, levels={levels}, n_procs={n_procs}, seed={base}.")
        import os as _os
        cwd = _os.getcwd()
        args = [(base + r * 100000, levels, num_agents, n_eval, grad_cfg, max_ticks, cwd) for r in range(R)]
        with ProcessPoolExecutor(max_workers=n_procs) as ex:
            reps = list(ex.map(_one_rep, args))      # ordre préservé -> déterministe
        return _report(h, reps, R, levels, _return)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py::test_main_mp_matches_sequential -q`
Expected: PASS.

- [ ] **Step 5: Run the full test file + commit**

Run: `python -m pytest tests/sandbox/test_lethality_curriculum.py -q`
Expected: PASS (9 tests).

```bash
WT="c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
git -C "$WT" add tools/lethality_curriculum.py tests/sandbox/test_lethality_curriculum.py
git -C "$WT" commit -m "feat(EDR090): _one_rep + main_mp (multiprocess, mp == seq vérifié)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Smoke run + pilote R=3 (gate-check) — EXÉCUTION

**Files:** aucun (exécution du harnais). Décision GO/NO-GO sur le run complet.

- [ ] **Step 1: Smoke run (bout-en-bout, ~1-2 min)**

Run (depuis le worktree) :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
HEADLESS=1 python -c "from tools import lethality_curriculum as lc; print(lc.main_mp(R=2, levels=(0.33,0.83), num_agents=8, n_eval=3, seed=11, n_procs=2, max_ticks=60, _return=True)['verdict'])"
```
Expected : s'exécute sans erreur, imprime un verdict ∈ {NEGATIF PROFOND, CASSE LE BOOTSTRAP, PAS LE GOULOT}.

- [ ] **Step 2: Pilote R=3 gate-check (paramètres réels, ~10-15 min)**

Run :
```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/edr090-lethality-curriculum"
HEADLESS=1 python -c "from tools import lethality_curriculum as lc; r=lc.main_mp(R=3, seed=190, n_procs=3, _return=True); print('GATE survie_med=', r['surv_med'], '->', 'OK' if r['surv_med']>120 else 'ECHEC (curriculum ne fabrique pas la survie)')"
```
Expected : imprime `surv_med` au terminal `0.83` et le statut du gate. **Inspecter les transcripts** (`r['transcripts']`) : à quel palier le curriculum cesse de graduer ?

- [ ] **Step 3: Décision GO/NO-GO (documentée, pas de code)**

- `surv_med > 120` → **GO run complet** (`main_mp(R=8, seed=190, n_procs=4)`), puis écrire l'EDR 090 selon le verdict pré-enregistré.
- `surv_med ≤ 120` → **NÉGATIF PROFOND confirmé** : le curriculum lui-même ne fabrique pas l'évitement. Écrire l'EDR 090 = ce finding (le verrou est la capacité d'apprentissage, pas le bootstrap), en s'appuyant sur les transcripts (le palier de blocage). **Ne pas** lancer le run complet à l'aveugle.

> Le pilote AVANT le run complet est la leçon d'089 : il a évité des heures de calcul en révélant le mur tôt.

---

## Self-Review (rempli par l'auteur du plan)

**1. Spec coverage :** chaque exigence du spec a une tâche.
- §2 variable curriculum vs flat → T4 (`_run_curriculum_arm`), T5 (`_run_flat_arm`), T7 (`_one_rep_core` apparie les deux). ✓
- §3.1 bouton létalité `_setup_critical` → T2. ✓
- §3.2 réutilisation `has_graduated`/`GraduationConfig` (pas `CurriculumRunner.run`) → T1 (import), T3 (usage). ✓
- §3.3 boucle/promotion génomes en mémoire + transcript → T3, T4. ✓
- §3.4 compétence survie → T1 (`_survival_competence`), T3 (usage). ✓
- §4 métrique net + gate + 3 branches de verdict → T1 (`_verdict`), T6 (net/survie), T7 (`_report`). ✓
- §5 paramètres gelés → T1 (`_grad_cfg`, constantes). ✓
- §6 outillage + mp → T8. ✓
- §7 pilote R=3 d'abord → T9. ✓
- §8 garde-fous repro (retriever stoppé, seed_at, mp==seq) → T2, T8. ✓
- §9 tests (survie→[0,1], transcript, budget, mp==seq) → T1, T4, T5, T8. ✓

**2. Placeholder scan :** aucun TBD/TODO ; code complet à chaque step ; commandes exactes. ✓

**3. Type consistency :** `_run_era_clean` renvoie toujours `{ticks,kills,leurre_hits,survivors,scored}` (T2), consommé tel quel par T3/T5/T6. `_coevolve_at` renvoie `(genomes, eras, history, graduated)` (T3), utilisé par T4. `_one_rep_core` renvoie un dict avec `d_net/surv_curr/surv_flat/transcript/total_eras/net_curr/net_flat` (T7), consommé par `_report` (T7) et produit par `_one_rep` (T8). `_verdict(sc_med, wilcoxon_p, med, lo)` (T1) appelé par `_report` (T7) avec `summ["wilcoxon_p"]`. Cohérent. ✓
