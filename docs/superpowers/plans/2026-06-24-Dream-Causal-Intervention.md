# Intervention Causale du Dreaming (Phase 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trancher causalement le paradoxe Q2a (le dreaming cause-t-il un meilleur sort ?) via un hook moteur gated `FORCE_DREAM` et une sonde qui balaye la profondeur de rêve forcée {off,1,4,8} → courbe dose-réponse de la survie.

**Architecture:** Unité 1 = hook gated dans `src/agents/mamba_agent.py` (attribut de classe `MambaBatchModel.FORCE_DREAM` + helper PUR `_resolve_dreaming`, pattern d'ablation `ABLATE_*`, défaut None). Unité 2 = `tools/dream_causal_probe.py` (helpers purs + orchestration réutilisant `run_era_organ`, flag réinit en try/finally).

**Tech Stack:** Python 3.13, numpy, pytest. Réutilise `run_era_organ` (`tools.dreaming_probe`), `survival_competence` (`src.curriculum.competence`), `_sign_test_p` (`tools.curriculum_transfer`), `Harness`, `async_logger`.

## Global Constraints

- **Unité 1 modifie `src/`** : gated, défaut `None` = comportement historique inchangé (pattern `ABLATE_*`). Le helper `_resolve_dreaming` DOIT avoir son test moteur unitaire.
- **Réinit du flag** : `MambaBatchModel.FORCE_DREAM` est un état global de classe → la sonde le pose puis le remet à `None` en `try/finally`. Un bras qui oublie pollue les suivants ET la prod.
- **Headless** : `os.environ["AGISEED_QUIET_LOG"]="1"` dans `main()` AVANT `async_logger.start()`.
- **Fuite d'env (leçon EDR 093)** : test de provenance → `monkeypatch.setenv("AGISEED_QUIET_LOG","0")` AVANT `main()`.
- **Substrat** : `run_era_organ(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db)` renvoie `[{"age","total_dreams","has_organ"}, ...]` (tous agents). Sweet spot = `0.25/3.0`. `bool` est sous-classe de `int` en Python → le helper DOIT exclure `True/False` du cas `int K`.
- **Fichiers** : `src/agents/mamba_agent.py` (Unité 1) ; `tools/dream_causal_probe.py` + tests `tests/sandbox/test_resolve_dreaming.py` (moteur) et `tests/sandbox/test_dream_causal_probe.py` (sonde).

---

## File Structure

- **Modify** `src/agents/mamba_agent.py` — attribut classe + helper pur `_resolve_dreaming` + câblage forward.
- **Create** `tests/sandbox/test_resolve_dreaming.py` — test moteur du helper pur.
- **Create** `tools/dream_causal_probe.py` — sonde causale (helpers + orchestration + main).
- **Create** `tests/sandbox/test_dream_causal_probe.py` — tests sonde + provenance.

---

### Task 1: Hook moteur gated `FORCE_DREAM` + `_resolve_dreaming`

**Files:**
- Modify: `src/agents/mamba_agent.py` (attr classe ~ligne 270 ; helper module-level avant `class MambaBatchModel` ~ligne 263 ; câblage ~lignes 501-511)
- Test: `tests/sandbox/test_resolve_dreaming.py`

**Interfaces:**
- Produces: `MambaBatchModel.FORCE_DREAM` (attribut de classe, défaut `None`) ;
  `_resolve_dreaming(force_dream, has_mcts: np.ndarray, do_dream: np.ndarray, surprise: np.ndarray, dream_thr: float, surprise_thr: float) -> tuple[np.ndarray, np.ndarray]` (is_dreaming bool, K_individual int).

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_resolve_dreaming.py
import numpy as np
from src.agents.mamba_agent import _resolve_dreaming


def _inputs():
    has_mcts = np.array([True, True, False], dtype=bool)
    do_dream = np.array([0.5, 0.05, 0.9], dtype=np.float32)   # agent1 logit haut, agent2 bas
    surprise = np.array([0.9, 0.9, 0.9], dtype=np.float32)    # surprise haute partout
    return has_mcts, do_dream, surprise


def test_resolve_none_is_normal_autoselection():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming(None, has_mcts, do_dream, surprise, 0.1, 0.05)
    # agent0 : organe + logit 0.5>0.1 + surprise -> rêve ; agent1 : logit 0.05<0.1 -> non ; agent2 : pas d'organe -> non
    assert list(is_dream) == [True, False, False]
    assert K[0] == int(np.clip(0.5 * 8, 1, 8)) and K[1] == 0 and K[2] == 0


def test_resolve_off_nobody_dreams():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming("off", has_mcts, do_dream, surprise, 0.1, 0.05)
    assert not is_dream.any()
    assert (K == 0).all()


def test_resolve_int_forces_carriers_at_depth_K():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming(4, has_mcts, do_dream, surprise, 0.1, 0.05)
    # tous les porteurs d'organe rêvent (logit/surprise ignorés), profondeur fixe 4
    assert list(is_dream) == [True, True, False]
    assert K[0] == 4 and K[1] == 4 and K[2] == 0


def test_resolve_bool_not_treated_as_int_K():
    """bool est sous-classe d'int : True NE DOIT PAS forcer K=1 (sinon ABLATE-like accidentel)."""
    has_mcts, do_dream, surprise = _inputs()
    is_dream_true, _ = _resolve_dreaming(True, has_mcts, do_dream, surprise, 0.1, 0.05)
    is_dream_none, _ = _resolve_dreaming(None, has_mcts, do_dream, surprise, 0.1, 0.05)
    assert list(is_dream_true) == list(is_dream_none)    # True traité comme None (normal)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_resolve_dreaming.py -q -p no:cacheprovider`
Expected: FAIL (cannot import `_resolve_dreaming`).

- [ ] **Step 3: Add the pure helper (module-level, AVANT `class MambaBatchModel:` ~ligne 263)**

```python
def _resolve_dreaming(force_dream, has_mcts, do_dream, surprise, dream_thr, surprise_thr):
    """Résout (is_dreaming, K_individual) selon FORCE_DREAM (intervention causale, EDR 094).
    None -> auto-sélection normale ; "off" -> personne ne rêve ; int K (>=1) -> tous les porteurs
    d'organe rêvent à profondeur FIXE K. Pur (numpy), testable sans batch model.
    NB: bool est sous-classe d'int -> on exclut True/False du cas int K."""
    if force_dream == "off":
        is_dreaming = np.zeros(len(has_mcts), dtype=bool)
    elif isinstance(force_dream, int) and not isinstance(force_dream, bool):
        is_dreaming = has_mcts.copy()
    else:  # None (ou valeur non reconnue) -> comportement historique
        is_dreaming = has_mcts & (do_dream > dream_thr) & (surprise > surprise_thr)

    if isinstance(force_dream, int) and not isinstance(force_dream, bool):
        K_individual = np.where(is_dreaming, force_dream, 0)
    else:
        K_individual = np.where(is_dreaming, np.clip((do_dream * 8).astype(int), 1, 8), 0)
    return is_dreaming, K_individual
```

- [ ] **Step 4: Add the class attribute (après `ABLATE_ROUTER = False`, ~ligne 270)**

```python
    FORCE_DREAM = None          # intervention causale (EDR 094) : None|"off"|int K (profondeur forcée)
```

- [ ] **Step 5: Wire into the forward — remplacer les lignes `is_dreaming = (...)` ... `K_individual = np.where(...)` (~501-511) par :**

```python
        is_dreaming, K_individual = _resolve_dreaming(
            MambaBatchModel.FORCE_DREAM, has_mcts_batch, do_dream_batch,
            self.surprise_momentum_batch, DREAM_THRESHOLD, SURPRISE_THRESHOLD,
        )
```

- [ ] **Step 6: Run the helper test + a broad non-regression on the engine**

Run: `python -m pytest tests/sandbox/test_resolve_dreaming.py -q -p no:cacheprovider`
Expected: PASS (4 tests).

Run (non-régression : la forward s'importe et un test moteur existant passe) :
`python -m pytest tests/sandbox/test_dreaming_probe.py::test_run_era_organ_smoke_seeds_organ -q -p no:cacheprovider`
Expected: PASS (le défaut `FORCE_DREAM=None` laisse le comportement inchangé).

- [ ] **Step 7: Commit**

```bash
git add src/agents/mamba_agent.py tests/sandbox/test_resolve_dreaming.py
git commit -m "feat(engine): hook gated FORCE_DREAM + _resolve_dreaming (intervention causale, EDR 094)"
```

---

### Task 2: Helper pur `dose_response_verdict`

**Files:**
- Create: `tools/dream_causal_probe.py`
- Test: `tests/sandbox/test_dream_causal_probe.py`

**Interfaces:**
- Consumes: `_sign_test_p` (de `tools.curriculum_transfer`).
- Produces: `dose_response_verdict(per_arm: dict, eps: float = 0.02) -> dict` avec clés
  `ratio`, `sign_p`, `n_favorable`, `n`, `verdict` ∈ {`CAUSE_BENEFIQUE`,`CAUSE_NUISIBLE`,`NEUTRE`},
  `ratios_par_K`. `per_arm` = `{"off": [survie/seed], 1: [...], 4: [...], 8: [...]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_dream_causal_probe.py
from tools.dream_causal_probe import dose_response_verdict


def test_dose_response_benefique_when_survival_rises_with_K():
    per_arm = {"off": [0.10, 0.10, 0.10, 0.10, 0.10],
               1: [0.12, 0.12, 0.12, 0.12, 0.12],
               4: [0.16, 0.16, 0.16, 0.16, 0.16],
               8: [0.20, 0.20, 0.20, 0.20, 0.20]}     # K8/off = 2.0 partout
    v = dose_response_verdict(per_arm)
    assert v["verdict"] == "CAUSE_BENEFIQUE"
    assert v["ratio"] > 1.0 and v["ratios_par_K"]["8"] > v["ratios_par_K"]["1"]


def test_dose_response_nuisible_when_survival_falls_with_K():
    per_arm = {"off": [0.20]*5, 1: [0.18]*5, 4: [0.14]*5, 8: [0.10]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "CAUSE_NUISIBLE"


def test_dose_response_neutre_when_flat():
    per_arm = {"off": [0.15]*5, 1: [0.15]*5, 4: [0.151]*5, 8: [0.149]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "NEUTRE"
    assert dose_response_verdict({})["verdict"] == "NEUTRE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_dream_causal_probe.py::test_dose_response_benefique_when_survival_rises_with_K -q -p no:cacheprovider`
Expected: FAIL (cannot import `dose_response_verdict`).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/dream_causal_probe.py
"""Sonde d'intervention causale du dreaming (Phase 2). Le dreaming CAUSE-t-il un meilleur sort, ou
corrèle-t-il à la détresse (EDR 093/094) ? Force l'acte + la profondeur du rêve via le hook gated
MambaBatchModel.FORCE_DREAM ; balaye {off,1,4,8} -> courbe dose-réponse de la survie.
Spec : docs/superpowers/specs/2026-06-24-Dream-Causal-Intervention-design.md. Diagnostic causal."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p


def _paired_ratios(arm: List[float], off: List[float]) -> List[float]:
    m = min(len(arm), len(off))
    return [arm[i] / max(off[i], 1e-6) for i in range(m)]


def dose_response_verdict(per_arm: Dict, eps: float = 0.02) -> Dict:
    """Verdict ancré sur le bras le plus profond (max K) vs off, apparié par seed. Renvoie aussi la
    courbe dose-réponse complète (ratio apparié médian de chaque bras-K vs off)."""
    off = per_arm.get("off", [])
    ks = sorted(k for k in per_arm if k != "off")
    if not off or not ks:
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0,
                "verdict": "NEUTRE", "ratios_par_K": {}}
    ratios_par_K = {}
    for k in ks:
        pr = _paired_ratios(per_arm[k], off)
        ratios_par_K[str(k)] = float(statistics.median(pr)) if pr else 1.0
    pr = _paired_ratios(per_arm[ks[-1]], off)            # bras le plus profond
    ratio = float(statistics.median(pr)) if pr else 1.0
    effective = [r for r in pr if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in pr if r > 1.0)
    if ratio > 1.0 + eps and sign_p < 0.1:
        verdict = "CAUSE_BENEFIQUE"
    elif ratio < 1.0 - eps and sign_p < 0.1:
        verdict = "CAUSE_NUISIBLE"
    else:
        verdict = "NEUTRE"
    return {"ratio": ratio, "sign_p": sign_p, "n_favorable": n_fav, "n": len(pr),
            "verdict": verdict, "ratios_par_K": ratios_par_K}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_dream_causal_probe.py -q -p no:cacheprovider`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/dream_causal_probe.py tests/sandbox/test_dream_causal_probe.py
git commit -m "feat(dream-causal): dose_response_verdict (courbe profondeur->survie)"
```

---

### Task 3: Orchestration `run_causal` (balaye {off,1,4,8}, réinit flag)

**Files:**
- Modify: `tools/dream_causal_probe.py`
- Test: `tests/sandbox/test_dream_causal_probe.py` (smoke, `slow`)

**Interfaces:**
- Consumes: `run_era_organ` (`tools.dreaming_probe`), `survival_competence` (`src.curriculum.competence`), `MambaBatchModel` (`src.agents.mamba_agent`), `dose_response_verdict`.
- Produces: `run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1,4,8)) -> dict`.

- [ ] **Step 1: Write the implementation**

```python
# (append to tools/dream_causal_probe.py)
from src.curriculum.competence import survival_competence
from src.agents.mamba_agent import MambaBatchModel
from tools.dreaming_probe import run_era_organ

log = logging.getLogger("AGIseed.DreamCausal")


def run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1, 4, 8)) -> Dict:
    """Par seed, balaye les bras ["off", *ks] à organe ON (100%) + sweet spot. Pose FORCE_DREAM
    AVANT l'ère, le REMET à None en finally (anti-pollution). Survie appariée par seed -> verdict."""
    arms = ["off", *[int(k) for k in ks]]
    per_arm = {arm: [] for arm in arms}
    for seed in seeds:
        for arm in arms:
            MambaBatchModel.FORCE_DREAM = arm if arm == "off" else int(arm)
            try:
                stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
            finally:
                MambaBatchModel.FORCE_DREAM = None      # OBLIGATOIRE : etat global de classe
            per_arm[arm].append(survival_competence(stats))
        log.info("  seed=%s survie %s", seed,
                 {str(a): round(per_arm[a][-1], 3) for a in arms})
    verdict = dose_response_verdict(per_arm)
    return {**verdict, "per_arm": {str(a): v for a, v in per_arm.items()},
            "config": {"target": target, "seeds": [int(s) for s in seeds], "ks": list(ks),
                       "num_agents": num_agents, "max_ticks": max_ticks}}
```

- [ ] **Step 2: Write the smoke test (lent, vérifie la réinit du flag)**

```python
# (append to tests/sandbox/test_dream_causal_probe.py)
import os
import pytest


@pytest.mark.slow
def test_run_causal_smoke_resets_flag(monkeypatch):
    """Smoke biosphère : 1 seed, ks=(1,) -> forme du retour ET FORCE_DREAM remis à None après."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from src.agents.mamba_agent import MambaBatchModel
    from tools.dream_causal_probe import run_causal
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_causal([0], "stoneage", num_agents=20, max_ticks=40, shared_db=db, ks=(1,))
    finally:
        async_logger.stop()
    assert MambaBatchModel.FORCE_DREAM is None          # reset garanti (try/finally)
    assert "verdict" in res and set(res["per_arm"]) == {"off", "1"}
```

- [ ] **Step 3: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_dream_causal_probe.py::test_run_causal_smoke_resets_flag -q -p no:cacheprovider`
Expected: PASS (~15-40 s).

- [ ] **Step 4: Commit**

```bash
git add tools/dream_causal_probe.py tests/sandbox/test_dream_causal_probe.py
git commit -m "feat(dream-causal): run_causal (balaye {off,1,4,8}, reinit flag en finally)"
```

---

### Task 4: `main()` + provenance

**Files:**
- Modify: `tools/dream_causal_probe.py`
- Test: `tests/sandbox/test_dream_causal_probe.py` (provenance via monkeypatch)

**Interfaces:**
- Consumes: `run_causal`, `Harness`, `async_logger`, `_acquire_shared_db`, `WorldConfig`.
- Produces: `main() -> dict`.

- [ ] **Step 1: Write the implementation**

```python
# (append to tools/dream_causal_probe.py)
from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse, AVANT start()
    target = os.environ.get("DC_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DC_SEEDS", "0,1,2").split(",") if s.strip()]
    ks = tuple(int(k) for k in os.environ.get("DC_KS", "1,4,8").split(",") if k.strip())
    num_agents = int(os.environ.get("DC_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DC_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde causale : cible=%s seeds=%s ks=%s agents=%d ticks=%d ===",
                 target, seeds, ks, num_agents, max_ticks)
        result = run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=ks)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_causal", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s ratio(Kmax/off)=%.3f sign_p=%.3f | courbe=%s -> %s",
             result["verdict"], result["ratio"], result["sign_p"], result["ratios_par_K"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
```

- [ ] **Step 2: Write the provenance test (monkeypatch, sans biosphère)**

```python
# (append to tests/sandbox/test_dream_causal_probe.py)
import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dream_causal_probe as dc
    monkeypatch.setattr(dc, "run_causal", lambda *a, **k: {
        "ratio": 1.5, "sign_p": 0.05, "n_favorable": 5, "n": 5, "verdict": "CAUSE_BENEFIQUE",
        "ratios_par_K": {"1": 1.1, "4": 1.3, "8": 1.5},
        "per_arm": {"off": [0.1], "1": [0.11], "4": [0.13], "8": [0.15]},
        "config": {"target": "stoneage", "seeds": [0], "ks": [1, 4, 8]}})
    monkeypatch.setattr(dc.async_logger, "start", lambda: None)
    monkeypatch.setattr(dc.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dc, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DC_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dc.main()
    assert result["verdict"] == "CAUSE_BENEFIQUE"
    files = glob.glob(str(tmp_path / "results" / "dream_causal_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict"] == "CAUSE_BENEFIQUE"
    assert "commit" in data and "git_dirty" in data
```

- [ ] **Step 3: Run all non-slow tests + anti-fuite combiné**

Run: `python -m pytest tests/sandbox/test_dream_causal_probe.py tests/sandbox/test_async_logger.py -q -p no:cacheprovider -m "not slow"`
Expected: PASS (dose_response x3, provenance, + tests async_logger ; `test_quiet_mode_off_by_default` ne doit PAS échouer → preuve d'isolation de la fuite d'env).

- [ ] **Step 4: Commit**

```bash
git add tools/dream_causal_probe.py tests/sandbox/test_dream_causal_probe.py
git commit -m "feat(dream-causal): main + provenance (Phase 2 complet)"
```

---

### Task 5: Run réel + interprétation (pas de code)

**Files:** aucun (exécution + lecture).

- [ ] **Step 1: Lancer la sonde (stoneage, 5 seeds, balayage {off,1,4,8})**

Run: `DC_TARGET=stoneage DC_SEEDS=0,1,2,3,4 DC_KS=1,4,8 DC_NUM_AGENTS=40 DC_MAX_TICKS=400 python tools/dream_causal_probe.py`
Expected: une ligne `VERDICT=... ratio(Kmax/off)=... | courbe={...}` + un JSON dans `results/dream_causal_0.json`.

- [ ] **Step 2: Lire le verdict + la courbe et conclure**

- `CAUSE_BENEFIQUE` (survie monte avec K) → **rêver cause un meilleur sort** ; q2a (EDR 093) était un corrélat de détresse. Le dreaming aide → barreau suivant : le dreaming forcé fait-il émerger des autels ?
- `CAUSE_NUISIBLE` (survie baisse avec K) → **rêver nuit** (coût > bénéfice) ; reconsidérer l'organe comme levier d'exploration.
- `NEUTRE` (plat) → le dreaming est causalement neutre sur la survie ; le paradoxe Q2a était un pur corrélat. L'organe MCTS n'est pas le bon levier d'exploration ; pivoter (levier I nouveauté ou II auto-craft, EDR 014).

Rapporter la **courbe complète** `ratios_par_K` (monotone ? pic ? plat ?), JAMAIS le label nu. Signaler la sous-puissance (`sign_p`, n=5).

- [ ] **Step 3: Écrire l'EDR du résultat** (numéro libre suivant, ex. 095) et committer.

---

## Self-Review

**Spec coverage :** Hook `FORCE_DREAM` (None/off/int K) + `_resolve_dreaming` + câblage forward + test
moteur → Task 1. `dose_response_verdict` (ancré K-max vs off, courbe complète) → Task 2. `run_causal`
(balaye {off,*ks}, réinit try/finally, réutilise `run_era_organ`+`survival_competence`) → Task 3.
`main` (quiet-log avant start, provenance Harness) → Task 4. Garde-fous : réinit flag testée (Task 3
Step 2 assert `FORCE_DREAM is None`) ; hook moteur testé (Task 1) ; courbe rapportée (Task 2/4) ;
fuite d'env isolée (Task 4 Step 2) ; bool-pas-int (Task 1 Step 1 test). ✓

**Placeholder scan :** aucun TODO/TBD ; le test de provenance (Task 4 Step 2) utilise le bloc `with
open(...)` propre. ✓

**Type consistency :** `run_era_organ` → `[{age,total_dreams,has_organ}]` → `survival_competence`
consomme `age` ✓. `run_causal` produit `per_arm={arm:[survie]}` avec arms `"off"`+int → consommé par
`dose_response_verdict` (clé `"off"` + int) ✓. `dose_response_verdict` produit
`{ratio,sign_p,n_favorable,n,verdict,ratios_par_K}` → `main` lit `verdict/ratio/sign_p/ratios_par_K`
✓. `MambaBatchModel.FORCE_DREAM` posé/réinit par `run_causal` ↔ lu par `_resolve_dreaming` dans la
forward ✓.
