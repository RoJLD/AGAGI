# QD sauve-t-il le tier CRAFT mort ? — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un banc tooling `tools/qd_tier_rescue.py` qui tranche — falsifiablement — si la sélection QD (MAP-Elites, niches diverses) propage le tier CRAFT mort que la sélection `life_score` droppe.

**Architecture:** Deux bras évolutifs appariés par seed (HoF `life_score` réutilisé d'EDR 125 / QD nouveau), mesurés sur cohorte fixe par l'instrument per-type d'EDR 125 (`_measure_profile` + `_tier_fractions`). Verdict gelé sur Δfrac_craft. Tout est réutilisé par imports — zéro `src/` modifié.

**Tech Stack:** Python 3, numpy. Réutilise `tools/competence_profile.py` + `tools/map_elites_compare.py` + `src/seed_ai/map_elites.py` (tous sur origin/main).

## Global Constraints

- TOOLING pur : `git diff <merge-base> HEAD -- src/` VIDE. Ne modifie NI `src/` NI FamineWorld NI torch NI `substrate_ab*` (fichiers actifs de la session //).
- Tout `print` exécuté est **ASCII-only** (cp1252 Windows). Accents autorisés seulement dans docstrings/commentaires non exécutés.
- Réutilise par IMPORT (zéro modif) : `competence_profile.{_evolve_champions,_measure_profile,_tier_fractions}`, `map_elites_compare.{_make_cfg,_seed_genome,_reproduce,run_era_pool}`, `map_elites.MapElitesArchive`.
- Déterminisme mesure : `SeedManager.seed_boundary` + `benchmark_mode` + memory_retriever neutralisé (assurés par `_measure_profile` réutilisé).
- Verdict pré-enregistré (gelé) : primaire `frac_craft`, seuil Δ ≥ 0.10.
- Seed réel 1260, smoke 99260 (distincts).
- Tests dans `tests/sandbox/test_qd_tier_rescue.py`. AUCUN test relancé après le run réel (EDR 107).

---

### Task 1: Squelette module + helpers de verdict (logique pure)

**Files:**
- Create: `tools/qd_tier_rescue.py`
- Test: `tests/sandbox/test_qd_tier_rescue.py`

**Interfaces:**
- Consumes: `src.seed_ai.map_elites.MapElitesArchive` (attribut `.cells: dict[(size_bin,tier)] -> (score,genome,stats)`).
- Produces: `_tier_coverage(archive) -> dict` (clés `cells_tier0..3`) ; `_verdict_qd_rescue(fracs_hof, fracs_qd) -> str` (∈ {`"QD_RESCUE_CRAFT CONFIRME"`, `"QD_NEUTRE"`, `"QD_NUIT"`}).

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_qd_tier_rescue.py
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.map_elites import MapElitesArchive
from tools.qd_tier_rescue import _tier_coverage, _verdict_qd_rescue


def test_tier_coverage_counts_cells_per_tier():
    arch = MapElitesArchive()
    # cellules aux tiers {0,1,2,2,3} sur des size_bins distincts
    arch.cells = {
        (0, 0): (1.0, object(), {}),
        (1, 1): (1.0, object(), {}),
        (2, 2): (1.0, object(), {}),
        (3, 2): (1.0, object(), {}),
        (4, 3): (1.0, object(), {}),
    }
    assert _tier_coverage(arch) == {"cells_tier0": 1, "cells_tier1": 1, "cells_tier2": 2, "cells_tier3": 1}


def test_tier_coverage_empty_archive():
    assert _tier_coverage(MapElitesArchive()) == {"cells_tier0": 0, "cells_tier1": 0, "cells_tier2": 0, "cells_tier3": 0}


def test_verdict_qd_rescue_confirme():
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.15}) == "QD_RESCUE_CRAFT CONFIRME"


def test_verdict_qd_rescue_neutre():
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.05}) == "QD_NEUTRE"


def test_verdict_qd_rescue_nuit():
    assert _verdict_qd_rescue({"frac_craft": 0.20}, {"frac_craft": 0.05}) == "QD_NUIT"


def test_verdict_qd_rescue_lift_but_still_floored_is_neutre():
    # d=0.09 < 0.10 -> pas CONFIRME meme si qd bouge un peu
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.10}) == "QD_NEUTRE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_qd_tier_rescue.py -v`
Expected: FAIL avec `ModuleNotFoundError` / `ImportError` (`tools.qd_tier_rescue` inexistant).

- [ ] **Step 3: Create the module skeleton + pure helpers**

```python
# tools/qd_tier_rescue.py
"""tools/qd_tier_rescue.py — QD sauve-t-il le tier CRAFT mort ? (P3 audit memoire).

Rebranche l'instrument per-type d'EDR 125 (_measure_profile + _tier_fractions) sur les DEUX bras
evolutifs de map_elites_compare : HoF (mono-objectif life_score) vs QD (archive MAP-Elites, niches
diverses). La selection top-5 par life_score DROPPE un genome craft-pur (spears x300 < forager+apex) ;
l'archive QD garde une elite dans la cellule tier=2. Question gelee : QD leve-t-il frac_craft de >=0.10
(=> selection sauve le craft) ou non (=> mur = substrat/atteignabilite, EDR 111) ?

Tooling pur (pas de src/ modifie ; competence_profile/map_elites_compare/map_elites importes).
Usage : python -m tools.qd_tier_rescue
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.map_elites import MapElitesArchive
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool
from tools.competence_profile import _evolve_champions, _measure_profile, _tier_fractions


def _tier_coverage(archive):
    """Nb de cellules occupees par tier (readout : le craft/apex existe-t-il dans l'archive ?)."""
    tiers = [cell[1] for cell in archive.cells.keys()]
    return {f"cells_tier{t}": sum(1 for x in tiers if x == t) for t in range(4)}


def _verdict_qd_rescue(fracs_hof, fracs_qd):
    """Primaire = frac_craft. CONFIRME si QD leve le craft de >=0.10 ET le sort du plancher (>=0.10) ;
    QD_NUIT si degrade de >=0.10 ; sinon QD_NEUTRE (mur = substrat/atteignabilite, pas selection)."""
    d = fracs_qd["frac_craft"] - fracs_hof["frac_craft"]
    if d >= 0.10 and fracs_qd["frac_craft"] >= 0.10:
        return "QD_RESCUE_CRAFT CONFIRME"
    if d <= -0.10:
        return "QD_NUIT"
    return "QD_NEUTRE"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_qd_tier_rescue.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Verify zero src/ change**

Run: `git status --short src/` (attendu : VIDE) puis `git add tools/qd_tier_rescue.py tests/sandbox/test_qd_tier_rescue.py`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(qd-tier-rescue): squelette + verdict frac_craft (logique pure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Bras QD évolutif + mesure + report + main

**Files:**
- Modify: `tools/qd_tier_rescue.py` (ajoute fonctions après les helpers de Task 1)
- Test: `tests/sandbox/test_qd_tier_rescue.py` (ajoute 2 tests)

**Interfaces:**
- Consumes: `_evolve_champions(seed, eras, num_agents, max_ticks) -> list[Genome]` (bras HoF, EDR 125) ; `_measure_profile(cfg, genomes, max_ticks, disable_repro) -> list[dict]` ; `_tier_fractions(stats_list) -> dict` ; `run_era_pool(cfg, genomes, max_ticks) -> (pool, meta)` où `pool` = liste de `(score, genome, stats)` ; `MapElitesArchive` (`.upsert(score,genome,stats)`, `.sample(n) -> list[genome]`, `.coverage() -> int`, `.cells`) ; `_reproduce(genomes, num_agents) -> list[genome]` ; `_seed_genome(idx) -> genome`.
- Produces: `_evolve_qd_champions(seed, eras, num_agents, max_ticks, run_era_fn=None) -> (list, MapElitesArchive)` ; `_measure_arm(champs, num_agents, max_ticks) -> dict` ; `_report_qd_rescue(h, per_seed, R, _return)` ; `main_qd_tier_rescue(R, eras, num_agents, max_ticks, seed, _return) -> dict|None`.

- [ ] **Step 1: Write the failing tests**

```python
# Ajouter a tests/sandbox/test_qd_tier_rescue.py
import types

from tools.qd_tier_rescue import _evolve_qd_champions, main_qd_tier_rescue


def test_evolve_qd_champions_populates_craft_cell_with_fake_runner():
    def _g(nodes):
        return types.SimpleNamespace(num_nodes=nodes)

    def fake_runner(cfg, genomes, max_ticks):
        pool = [
            (10.0, _g(160), {"num_nodes": 160, "preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0}),
            (50.0, _g(200), {"num_nodes": 200, "preys_eaten": 2, "spears_crafted": 3, "mammoth_kills": 0}),
        ]
        return pool, {"score": 50.0, "ticks": 10.0}

    champs, archive = _evolve_qd_champions(seed=99260, eras=2, num_agents=6, max_ticks=10, run_era_fn=fake_runner)
    assert archive.coverage() > 0
    assert _tier_coverage(archive)["cells_tier2"] >= 1  # le genome crafteur (spears=3) peuple la cellule tier=2
    assert isinstance(champs, list)


def test_smoke_main_qd_tier_rescue_returns_verdict():
    res = main_qd_tier_rescue(R=1, eras=2, num_agents=10, max_ticks=80, seed=99260, _return=True)
    assert res["verdict"] in {"QD_RESCUE_CRAFT CONFIRME", "QD_NEUTRE", "QD_NUIT"}
    assert "d_craft" in res
    assert len(res["per_seed"]) == 1
    assert set(res["per_seed"][0].keys()) >= {"seed", "hof", "qd", "coverage"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_qd_tier_rescue.py -k "fake_runner or smoke" -v`
Expected: FAIL avec `ImportError` (`_evolve_qd_champions` / `main_qd_tier_rescue` inexistants).

- [ ] **Step 3: Implement evolution QD arm + measure + report + main**

```python
# Ajouter a tools/qd_tier_rescue.py apres _verdict_qd_rescue

def _evolve_qd_champions(seed, eras=12, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras QD : archive MAP-Elites, reproduit depuis niches diverses (sample). Renvoie (champions, archive).
    Mirror de run_lineage_qd (map_elites_compare) mais renvoie les genomes champions + l'archive.
    run_era_fn injectable (defaut run_era_pool) pour les tests."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    archive = MapElitesArchive()
    genomes = [_seed_genome(i) for i in range(num_agents)]
    for _ in range(eras):
        pool, _m = run_era_fn(cfg, genomes, max_ticks)
        for s, g, st in pool:
            archive.upsert(s, g, st)
        champ = archive.sample(5)
        genomes = _reproduce(champ, num_agents) if champ else [MambaAgent().genome for _ in range(num_agents)]
    return archive.sample(5), archive


def _measure_arm(champs, num_agents, max_ticks):
    """Replique les champions a num_agents et mesure le profil per-tier sur cohorte fixe (benchmark_mode).
    Bras vide -> fractions nulles (_frac_reaching([]) == 0.0)."""
    if not champs:
        return _tier_fractions([])
    reps = (champs * (num_agents // len(champs) + 1))[:num_agents]
    stats = _measure_profile(_make_cfg(), reps, max_ticks=max_ticks, disable_repro=True)
    return _tier_fractions(stats)


def _report_qd_rescue(h, per_seed, R, _return):
    """Table ASCII (HOF forg/craf/apex | QD forg/craf/apex | QD craft/apex cells) + moyenne + Delta + verdict."""
    def _mean(arm, k):
        return float(np.mean([p[arm][k] for p in per_seed]))
    keys = ("frac_forage", "frac_craft", "frac_apex")
    hof = {k: _mean("hof", k) for k in keys}
    qd = {k: _mean("qd", k) for k in keys}
    verdict = _verdict_qd_rescue(hof, qd)
    dcraft = qd["frac_craft"] - hof["frac_craft"]
    print("\n=== QD sauve-t-il le tier CRAFT ? (cohorte fixe, 2 bras apparies) ===")
    print("  seed | HOF  forg  craf  apex | QD   forg  craf  apex | QDcells t2/t3")
    for p in per_seed:
        hf, qf, cv = p["hof"], p["qd"], p["coverage"]
        print(f"  {p['seed']:4d} |      {hf['frac_forage']:5.3f} {hf['frac_craft']:5.3f} {hf['frac_apex']:5.3f} "
              f"|      {qf['frac_forage']:5.3f} {qf['frac_craft']:5.3f} {qf['frac_apex']:5.3f} "
              f"|   {cv['cells_tier2']:2d}/{cv['cells_tier3']:2d}")
    print(f"  MOYEN|      {hof['frac_forage']:5.3f} {hof['frac_craft']:5.3f} {hof['frac_apex']:5.3f} "
          f"|      {qd['frac_forage']:5.3f} {qd['frac_craft']:5.3f} {qd['frac_apex']:5.3f}")
    print(f"  d(craft) = {dcraft:+.3f}")
    print("=== VERDICT (QD sauve le craft ?) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "d_craft": dcraft, "mean_hof": hof, "mean_qd": qd, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "d_craft": dcraft, "mean_hof": hof, "mean_qd": qd, "per_seed": per_seed, "R": R}


def main_qd_tier_rescue(R=3, eras=12, num_agents=30, max_ticks=400, seed=1260, _return=False):
    """Pour chaque seed base+r : evolue 2 bras (HoF life_score / QD niches), mesure le profil per-tier de
    chacun sur cohorte fixe, agrege R seeds, verdict QD-sauve-craft."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            hof_champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            qd_champs, archive = _evolve_qd_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            per_seed.append({
                "seed": int(s),
                "hof": _measure_arm(hof_champs, num_agents, max_ticks),
                "qd": _measure_arm(qd_champs, num_agents, max_ticks),
                "coverage": _tier_coverage(archive),
            })
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="qd_tier_rescue", with_db=False, config=WorldConfig())
    return _report_qd_rescue(h, per_seed, R, _return)


if __name__ == "__main__":
    main_qd_tier_rescue()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_qd_tier_rescue.py -v`
Expected: PASS (8 tests). Le smoke prend quelques dizaines de secondes (Biosphere réelle, R=1 eras=2).

- [ ] **Step 5: Verify zero src/ change**

Run: `git diff --stat $(git merge-base origin/main HEAD) HEAD -- src/` (attendu : VIDE).

- [ ] **Step 6: Commit**

```bash
git add tools/qd_tier_rescue.py tests/sandbox/test_qd_tier_rescue.py
git commit -m "feat(qd-tier-rescue): bras QD evolutif + mesure per-tier + main

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage** : §3 méthode (2 bras) → Task 2 `main`. §4.1 `_evolve_qd_champions` → Task 2. §4.2 `_tier_coverage` → Task 1. §4.3 `_verdict_qd_rescue` → Task 1. §4.4 `_report_qd_rescue` → Task 2. §4.5 `main` → Task 2. §7 tests 1-4 → Task 1 (t1,t2) + Task 2 (t3 fake runner, t4 smoke). Couvert.
- **Placeholders** : aucun ; code complet à chaque step.
- **Type consistency** : `_verdict_qd_rescue(fracs_hof, fracs_qd)` prend des dicts avec clé `frac_craft` (tests + `_report` cohérents) ; `_evolve_qd_champions` renvoie `(list, archive)` (test 3 + `main` cohérents) ; `_measure_arm` renvoie un dict `_tier_fractions` (clés `frac_*` + `n`) consommé par `_report`. Cohérent.
- **Run réel** (hors plan, après revue) : `python -m tools.qd_tier_rescue` (seed 1260, R=3), 2 passes byte-identiques, puis EDR 126 + mémoire + PR.
