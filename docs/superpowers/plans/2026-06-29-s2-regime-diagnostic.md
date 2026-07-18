# Diagnostic de régime S2 — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un outil de diagnostic `tools/s2_regime_diagnostic.py` qui tranche pourquoi le champion HoF ≈ dummy au benchmark S2 (sous-puissance H1 / effet plancher de régime H2 / n'exige-pas-réel H3) et recommande le régime d'énergie où lancer le S2 confirmatoire.

**Architecture:** Réutilise `run_condition` (de `tools/s2_demand.py`) pour la mesure et `src/seed_ai/s2_stats.py` (Cliff δ, Wilcoxon apparié) pour les stats. Une grille 2 régimes (défaut 1.0/1.0, sweet 0.25/3.0) × 3 agents (champion, reflex, random) sur le monde stoneage, K=8 ères appariées. Le cœur est une fonction PURE de verdict testée sur cellules synthétiques. Une seule modif chirurgicale gatée d'un fichier existant : ajout d'un paramètre optionnel `config=None` à `run_condition`.

**Tech Stack:** Python 3.13, numpy, stdlib. Aucune nouvelle dépendance. Réutilise Harness/seed_at (D1), `s2_stats`, `baseline_models`.

## Global Constraints

- **Modif d'`run_condition` non-régressive** : le paramètre `config` est optionnel, défaut `None` → `env = world_cls()` (chemin actuel bit-exact ; `tools/s2_demand.py:run_s2` inchangé).
- **Outil exploratoire** : n'amende PAS la pré-enregistration S2 (`docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md`). Seuils de diagnostic nommés et figés, distincts des seuils confirmatoires.
- **Réutilise** : `cliffs_delta`, `wilcoxon_signed_rank`, `ALPHA`, `CLIFF_THRESH` de `src/seed_ai/s2_stats.py` ; `run_condition`, `load_champion_genome` de `tools/s2_demand.py` ; `RandomActionBatchModel`, `ReflexBatchModel` de `src/agents/baseline_models.py` ; `Harness`, `seed_at`, `_git_short_commit` de `src/seed_ai/harness.py` ; `Biosphere3D` de `src/worlds/world_1_stoneage.py`.
- **Régimes** : `REGIMES = {"defaut": (1.0, 1.0), "sweet": (0.25, 3.0)}` — `(base_metabolism, forage_payoff)`.
- **Seuils diagnostic** : `SURV_FLOOR_FRAC = 0.5`, `CENSORED_SURV = 0.25`, `LIFT_RATIO = 1.5`.
- **Défauts du run réel** : `seed=2026, K=8, num_agents=20, max_ticks=400`.
- **Verdicts** : `SOUS_PUISSANCE` / `CONFOND_PLANCHER` / `N_EXIGE_PAS_REEL` / `AMBIGU`.
- **Commits path-scopés** : `git add` des seuls fichiers listés (tree partagé entre sessions parallèles). Message terminé par `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Python (Windows)** : lancer les tests avec `python -m pytest ...` (repli `py -m pytest ...`).

---

### Task 1: Hook de régime dans `run_condition` (modif gatée + tests fake-env)

**Files:**
- Modify: `tools/s2_demand.py` (fonction `run_condition`, signature + ligne `env = world_cls()`)
- Test: `tests/sandbox/test_s2_regime_hook.py`

**Interfaces:**
- Consumes: `run_condition` existant.
- Produces: `run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1, config=None)` — `config=None` → `world_cls()` (inchangé) ; `config` fourni → `world_cls(config)` (construit l'env au régime voulu).

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_s2_regime_hook.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.environments.config import WorldConfig
from tools.s2_demand import run_condition


class _FakeEnv:
    """Env minimal qui ENREGISTRE le config reçu et ne simule rien (agents vide -> boucle no-op)."""
    last_config = "UNSET"

    def __init__(self, config=None):
        _FakeEnv.last_config = config
        self.agents = []
        self.dead_agents = []
        self.benchmark_mode = False
        self.night_enabled = True
        self.current_era = 0

    def add_agent(self, agent, energy=0.0):
        pass

    def step(self):
        pass


def test_run_condition_default_passes_no_config():
    _FakeEnv.last_config = "UNSET"
    run_condition(_FakeEnv, None, None, seed=1, num_agents=1, max_ticks=1, n_eras=1)
    assert _FakeEnv.last_config is None        # défaut -> world_cls() -> config None


def test_run_condition_forwards_regime_config():
    cfg = WorldConfig(base_metabolism=0.25, forage_payoff=3.0)
    run_condition(_FakeEnv, None, None, seed=1, num_agents=1, max_ticks=1, n_eras=1, config=cfg)
    assert _FakeEnv.last_config is cfg          # config fourni -> world_cls(config)
    assert _FakeEnv.last_config.base_metabolism == 0.25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_regime_hook.py -q`
Expected: FAIL — `test_run_condition_forwards_regime_config` lève `TypeError: run_condition() got an unexpected keyword argument 'config'`.

- [ ] **Step 3: Write minimal implementation**

Dans `tools/s2_demand.py`, modifier la signature de `run_condition` (ajouter `config=None` en dernier paramètre) et la ligne de construction de l'env.

Signature — remplacer :
```python
def run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1):
```
par :
```python
def run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1, config=None):
```

Construction de l'env — remplacer la ligne :
```python
        env = world_cls()
```
par :
```python
        env = world_cls(config) if config is not None else world_cls()
```

(Mettre à jour la docstring de `run_condition` : ajouter une phrase « `config` (WorldConfig) fixe le régime à la construction ; `None` = défaut historique. »)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_regime_hook.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/s2_demand.py tests/sandbox/test_s2_regime_hook.py
git commit -m "feat(s2-diag): hook config de régime dans run_condition (gaté, non-régressif)"
```

---

### Task 2: Verdict pur `regime_diagnostic_verdict` + seuils (nouveau fichier)

**Files:**
- Create: `tools/s2_regime_diagnostic.py`
- Test: `tests/sandbox/test_s2_regime_diagnostic.py`

**Interfaces:**
- Consumes: `cliffs_delta`, `wilcoxon_signed_rank`, `ALPHA`, `CLIFF_THRESH` de `src/seed_ai/s2_stats.py`.
- Produces:
  - `REGIMES = {"defaut": (1.0, 1.0), "sweet": (0.25, 3.0)}`.
  - `SURV_FLOOR_FRAC=0.5`, `CENSORED_SURV=0.25`, `LIFT_RATIO=1.5`.
  - `regime_diagnostic_verdict(cells: dict, max_ticks: int = 400) -> dict` — `cells[regime][agent]` = dict de `run_condition` (clés `survival`, `era_survival`, `censored_frac`). Renvoie `{verdict, regime_recommande, lift, per_regime, thresholds}`.
  - Helpers internes `_beats`, `_strongest_baseline`, `_survivable` (testés via la fonction publique).

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_s2_regime_diagnostic.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.s2_regime_diagnostic import regime_diagnostic_verdict, REGIMES


def _cell(survival, era_survival=None, censored=0.0):
    return {"survival": list(survival),
            "era_survival": list(era_survival if era_survival is not None else survival),
            "life_score": list(survival), "era_life": list(survival),
            "censored_frac": censored}


def _sep_regime(champ_age, base_age, n=8, censored=0.0, max_ticks=400):
    """Régime où le champion DOMINE le baseline : n ères appariées toutes positives + pools disjoints."""
    return {"champion": _cell([champ_age] * n, censored=censored),
            "reflex_naive": _cell([base_age] * n),
            "random_action": _cell([base_age] * n)}


def _equal_regime(age, n=8, censored=0.0):
    """Régime où champion ≈ baselines (aucune séparation)."""
    return {"champion": _cell([age] * n, censored=censored),
            "reflex_naive": _cell([age] * n),
            "random_action": _cell([age] * n)}


def test_sous_puissance_when_champion_beats_at_default():
    cells = {"defaut": _sep_regime(300, 50), "sweet": _sep_regime(300, 50)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "SOUS_PUISSANCE"
    assert v["regime_recommande"] == "defaut"
    assert v["per_regime"]["defaut"]["beats"] is True


def test_confond_plancher_when_default_floored_but_sweet_separates():
    # défaut : tous au plancher (20 << 0.5*400) et égaux -> non survivable, pas de séparation
    # sweet : champion 300 (survivable) domine baseline 50, lift = 300/20 = 15 >= 1.5
    cells = {"defaut": _equal_regime(20), "sweet": _sep_regime(300, 50)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "CONFOND_PLANCHER"
    assert v["regime_recommande"] == "sweet"
    assert v["per_regime"]["defaut"]["survivable"] is False
    assert v["per_regime"]["sweet"]["survivable"] is True


def test_n_exige_pas_reel_when_sweet_survivable_but_no_separation():
    # sweet survivable (300 >= 200) ET champion ≈ dummy -> finding réel
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(300)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "N_EXIGE_PAS_REEL"
    assert v["regime_recommande"] is None


def test_ambigu_when_no_regime_survivable_and_no_separation():
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(30)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "AMBIGU"
    assert v["regime_recommande"] is None


def test_survivable_via_censored_fraction():
    # médiane basse (100 < 200) MAIS 30% censurés -> survivable par CENSORED_SURV ; champ ≈ dummy
    cells = {"defaut": _equal_regime(20),
             "sweet": {"champion": _cell([100] * 8, censored=0.30),
                       "reflex_naive": _cell([100] * 8), "random_action": _cell([100] * 8)}}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["per_regime"]["sweet"]["survivable"] is True
    assert v["verdict"] == "N_EXIGE_PAS_REEL"


def test_thresholds_and_regimes_reported():
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(30)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["thresholds"]["CLIFF_THRESH"] == 0.33
    assert REGIMES["sweet"] == (0.25, 3.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_regime_diagnostic.py -q`
Expected: FAIL (ModuleNotFoundError: tools.s2_regime_diagnostic).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/s2_regime_diagnostic.py
"""tools/s2_regime_diagnostic.py — Diagnostic de régime S2 (outillage EXPLORATOIRE).
Tranche pourquoi le champion HoF ≈ dummy au benchmark S2 : sous-puissance (H1), effet plancher de
régime énergétique (H2), ou n'exige-pas-réel (H3). Grille 2 régimes × 3 agents sur stoneage, K ères
appariées. Recommande le régime où lancer le S2 confirmatoire. N'amende PAS la pré-reg S2.
Spec : docs/superpowers/specs/2026-06-29-s2-regime-diagnostic-design.md
Usage : python tools/s2_regime_diagnostic.py   (EXPERIMENT_SEED=2026 par défaut)"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.s2_stats import cliffs_delta, wilcoxon_signed_rank, ALPHA, CLIFF_THRESH

# Régimes énergétiques (base_metabolism, forage_payoff). 'defaut' = prod/historique ; 'sweet' = EDR085.
REGIMES = {"defaut": (1.0, 1.0), "sweet": (0.25, 3.0)}

# Seuils DIAGNOSTIC (exploratoires, ajustables) — distincts des seuils confirmatoires pré-enregistrés.
SURV_FLOOR_FRAC = 0.5     # médiane d'âge >= 50% de max_ticks -> régime survivable (absolu)
CENSORED_SURV = 0.25      # OU >= 25% censurés (survivants à max_ticks) -> survivable
LIFT_RATIO = 1.5          # sweet relève la survie >= 1.5x le défaut -> "sort du plancher"


def _beats(champ, base):
    """Le champion BAT le baseline : p<ALPHA (Wilcoxon signé apparié sur era_survival) ET
    Cliff δ >= CLIFF_THRESH (sur les individus poolés). Renvoie {p, cliff, beats}."""
    ce = np.asarray(champ["era_survival"], dtype=float)
    be = np.asarray(base["era_survival"], dtype=float)
    m = min(ce.size, be.size)
    _w, p = wilcoxon_signed_rank(ce[:m] - be[:m])
    cliff = cliffs_delta(champ["survival"], base["survival"])
    return {"p": float(p), "cliff": float(cliff), "beats": bool(p < ALPHA and cliff >= CLIFF_THRESH)}


def _strongest_baseline(regime_cells):
    """Baseline (hors 'champion') à plus haute survie médiane = le plus dur à battre."""
    keys = [k for k in regime_cells if k != "champion"]
    return max(keys, key=lambda k: float(np.median(regime_cells[k]["survival"]))
               if regime_cells[k]["survival"] else 0.0)


def _median(cell):
    return float(np.median(cell["survival"])) if cell["survival"] else 0.0


def _survivable(champ, max_ticks):
    """Régime survivable : médiane d'âge du champion >= SURV_FLOOR_FRAC*max_ticks OU censuré >= CENSORED_SURV."""
    return bool(_median(champ) >= SURV_FLOOR_FRAC * max_ticks
                or float(champ.get("censored_frac", 0.0)) >= CENSORED_SURV)


def regime_diagnostic_verdict(cells, max_ticks=400):
    """Verdict du diagnostic à partir de `cells[regime][agent]` (dicts run_condition). Table §C de la spec.
    Ordre : (1) champion bat au défaut -> SOUS_PUISSANCE ; sinon (2a) défaut au plancher + sweet survivable
    (lift) + champion bat au sweet -> CONFOND_PLANCHER ; (2b) sweet survivable + champion ne bat pas ->
    N_EXIGE_PAS_REEL ; (2c) sinon -> AMBIGU."""
    per = {}
    for regime, rc in cells.items():
        sb = _strongest_baseline(rc)
        cmp = _beats(rc["champion"], rc[sb])
        per[regime] = {"strongest_baseline": sb, "p": cmp["p"], "cliff": cmp["cliff"],
                       "beats": cmp["beats"], "survivable": _survivable(rc["champion"], max_ticks),
                       "champ_median": _median(rc["champion"]),
                       "censored_frac": float(rc["champion"].get("censored_frac", 0.0))}
    md, ms = per.get("defaut", {}), per.get("sweet", {})
    md_med, ms_med = md.get("champ_median", 0.0), ms.get("champ_median", 0.0)
    lift = (ms_med / md_med) if md_med > 0 else (float("inf") if ms_med > 0 else 1.0)

    if md.get("beats"):
        verdict, reco = "SOUS_PUISSANCE", "defaut"
    elif (not md.get("survivable")) and ms.get("survivable") and lift >= LIFT_RATIO and ms.get("beats"):
        verdict, reco = "CONFOND_PLANCHER", "sweet"
    elif ms.get("survivable") and not ms.get("beats"):
        verdict, reco = "N_EXIGE_PAS_REEL", None
    else:
        verdict, reco = "AMBIGU", None

    return {"verdict": verdict, "regime_recommande": reco, "lift": float(lift), "per_regime": per,
            "thresholds": {"ALPHA": ALPHA, "CLIFF_THRESH": CLIFF_THRESH,
                           "SURV_FLOOR_FRAC": SURV_FLOOR_FRAC, "CENSORED_SURV": CENSORED_SURV,
                           "LIFT_RATIO": LIFT_RATIO}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_regime_diagnostic.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/s2_regime_diagnostic.py tests/sandbox/test_s2_regime_diagnostic.py
git commit -m "feat(s2-diag): verdict pur regime_diagnostic_verdict + seuils (H1/H2/H3)"
```

---

### Task 3: Pilote de mesure `run_diagnostic` + CLI + test d'intégration

**Files:**
- Modify: `tools/s2_regime_diagnostic.py`
- Test: `tests/sandbox/test_s2_regime_diagnostic.py`

**Interfaces:**
- Consumes: `regime_diagnostic_verdict`, `REGIMES` (Task 2) ; `run_condition`, `load_champion_genome` de `tools/s2_demand.py` ; `RandomActionBatchModel`, `ReflexBatchModel` de `src/agents/baseline_models.py` ; `Biosphere3D` de `src/worlds/world_1_stoneage.py` ; `WorldConfig` de `src/environments/config.py` ; `Harness`, `_git_short_commit` de `src/seed_ai/harness.py`.
- Produces:
  - `AGENTS: dict` — `{"champion","reflex_naive","random_action"}`.
  - `_make_config(base_metabolism, forage_payoff) -> WorldConfig`.
  - `run_diagnostic(seed=2026, K=8, num_agents=20, max_ticks=400) -> dict` — `cells[regime][agent]`.
  - `run_diagnostic_main(seed=2026, K=8, num_agents=20, max_ticks=400, with_db=False) -> dict` — orchestre, sauve `results/s2_regime_diagnostic_<seed>.json`, imprime la table + la reco, renvoie le report.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_s2_regime_diagnostic.py
import pytest
from tools.s2_regime_diagnostic import run_diagnostic_main


def test_run_diagnostic_main_smoke(tmp_path, monkeypatch):
    """Pilote bout-en-bout à minuscule échelle, HoF mocké (champion = génome frais), KuzuDB désactivé."""
    from tools.lethality_curriculum import _disable_kuzu
    from src.agents.mamba_agent import MambaAgent
    _disable_kuzu()                                   # déterminisme + pas de contention KuzuDB
    monkeypatch.setattr("tools.s2_regime_diagnostic.load_champion_genome",
                        lambda: MambaAgent().genome)  # pas besoin d'un vrai HoF en CI
    monkeypatch.chdir(tmp_path)                        # ne pollue pas results/
    (tmp_path / "results").mkdir()
    report = run_diagnostic_main(seed=1, K=1, num_agents=2, max_ticks=3)
    assert report["verdict"] in {"SOUS_PUISSANCE", "CONFOND_PLANCHER", "N_EXIGE_PAS_REEL", "AMBIGU"}
    assert set(report["per_regime"]) == {"defaut", "sweet"}
    for regime in ("defaut", "sweet"):
        assert "beats" in report["per_regime"][regime]
    assert (tmp_path / "results" / "s2_regime_diagnostic_1.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_s2_regime_diagnostic.py::test_run_diagnostic_main_smoke -q`
Expected: FAIL (ImportError: cannot import name 'run_diagnostic_main').

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/s2_regime_diagnostic.py (imports paresseux dans les fonctions pour garder le cœur pur testable sans la sim)
def _make_config(base_metabolism, forage_payoff):
    """WorldConfig au régime voulu (base_metabolism, forage_payoff) ; reste = défauts."""
    from src.environments.config import WorldConfig
    return WorldConfig(base_metabolism=base_metabolism, forage_payoff=forage_payoff)


# Agents du diagnostic. fresh_genome=True -> agents frais ; batch_model_cls=None -> moteur normal (champion).
def _agents():
    from src.agents.baseline_models import RandomActionBatchModel, ReflexBatchModel
    return {
        "champion":      {"batch_model_cls": None,                   "fresh_genome": False},
        "reflex_naive":  {"batch_model_cls": ReflexBatchModel,       "fresh_genome": True},
        "random_action": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": True},
    }


AGENTS = ("champion", "reflex_naive", "random_action")


def run_diagnostic(seed=2026, K=8, num_agents=20, max_ticks=400):
    """Grille 2 régimes × 3 agents sur stoneage -> cells[regime][agent] = dict run_condition."""
    from tools.s2_demand import run_condition, load_champion_genome
    from src.worlds.world_1_stoneage import Biosphere3D
    champion = load_champion_genome()
    agents = _agents()
    cells = {}
    for regime, (bm, fp) in REGIMES.items():
        cfg = _make_config(bm, fp)
        rc = {}
        for name in AGENTS:
            spec = agents[name]
            genome = None if spec["fresh_genome"] else champion
            rc[name] = run_condition(Biosphere3D, spec["batch_model_cls"], genome, seed,
                                     num_agents=num_agents, max_ticks=max_ticks, n_eras=K, config=cfg)
        cells[regime] = rc
    return cells


_ACTION = {
    "SOUS_PUISSANCE":   "le VOID n'était que du bruit -> lancer le S2 confirmatoire AU DÉFAUT (pré-reg tel quel).",
    "CONFOND_PLANCHER": "effet plancher au régime dur -> lancer le S2 confirmatoire AU SWEET-SPOT (addendum daté à la pré-reg).",
    "N_EXIGE_PAS_REEL": "le monde n'exige PAS l'intelligence même survivable -> finding fort (formaliser via S2 confirmatoire).",
    "AMBIGU":           "inconclusif (aucun régime survivable, ou cas contradictoire) -> re-powerer / élargir les régimes.",
}


def _print_table(report):
    print(f"\n=== S2 — Diagnostic de régime (seed={report['seed']}, commit={report['commit']}, K={report['K']}) ===")
    for regime, r in report["per_regime"].items():
        print(f"  {regime:7s} : survivable={str(r['survivable']):5s} | médiane_champ={r['champ_median']:6.1f} "
              f"| censuré={r['censored_frac']*100:3.0f}% | vs {r['strongest_baseline']:13s} "
              f"p={r['p']:.3f} Cliff δ={r['cliff']:+.2f} bat={r['beats']}")
    print(f"  -> VERDICT : {report['verdict']} (lift sweet/défaut={report['lift']:.2f})")
    print(f"  -> {_ACTION.get(report['verdict'], '')}")
    if report["regime_recommande"]:
        print(f"  -> régime recommandé pour le S2 confirmatoire : {report['regime_recommande']}")


def run_diagnostic_main(seed=2026, K=8, num_agents=20, max_ticks=400, with_db=False):
    """Orchestre le diagnostic, sauve le report (results/s2_regime_diagnostic_<seed>.json), imprime."""
    from src.seed_ai.harness import Harness, _git_short_commit
    with Harness(seed=seed, name="s2_regime_diagnostic", with_db=with_db) as h:
        cells = run_diagnostic(seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
        v = regime_diagnostic_verdict(cells, max_ticks=max_ticks)
        report = {"seed": seed, "commit": _git_short_commit(), "K": K, **v}
        h.save(report)
    _print_table(report)
    return report


if __name__ == "__main__":
    run_diagnostic_main(seed=int(os.getenv("EXPERIMENT_SEED", "2026")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_s2_regime_diagnostic.py -q`
Expected: PASS (7 passed — 6 de Task 2 + le smoke d'intégration).

- [ ] **Step 5: Vérifier la non-régression de `s2_demand` (le hook n'a rien cassé)**

Run: `python -m pytest tests/sandbox/test_s2_regime_hook.py tests/sandbox/test_s2_regime_diagnostic.py -q`
Expected: PASS (9 passed au total). Si une suite `tests/sandbox/test_s2_demand*.py` existe, la lancer aussi — attendu : inchangée (verte).

- [ ] **Step 6: Commit**

```bash
git add tools/s2_regime_diagnostic.py tests/sandbox/test_s2_regime_diagnostic.py
git commit -m "feat(s2-diag): pilote run_diagnostic + CLI (grille régime×agent, report + reco)"
```

---

## Self-Review (auteur)

**Couverture spec :** Hook config `run_condition`→T1 (+ tests non-régression/injection). Verdict pur + 4 issues + survivabilité (plancher/censuré/lift) + seuils→T2 (6 tests synthétiques couvrant les 4 verdicts + bascules). Pilote grille 2×3 + Harness + save JSON + table + reco→T3. Footguns (benchmark_mode/nuit/scaffolds/memory_retriever) hérités de `run_condition` ; `_disable_kuzu()` en test d'intégration→T3. HoF vide lève (via `load_champion_genome`, réutilisé). **Tout couvert.** Monde unique stoneage = `Biosphere3D` direct (T3). Hors-périmètre (4 mondes, run confirmatoire, câblage prod) absent du plan — conforme.

**Types cohérents :** `cells[regime][agent]` = dict `run_condition` (`survival`/`era_survival`/`censored_frac`) partout ; `regime_diagnostic_verdict(cells, max_ticks)->{verdict, regime_recommande, lift, per_regime, thresholds}` (T2) consommé par `run_diagnostic_main` (T3) ; `run_condition(..., config=None)` (T1) appelé avec `config=cfg` (T3) ; `REGIMES`/seuils définis T2, réutilisés T3. `_make_config(bm,fp)->WorldConfig`.

**Placeholders :** code complet + tests complets ; stubs `_FakeEnv`/`_cell`/`_sep_regime`/`_equal_regime` déterministes ; `tmp_path`+`_disable_kuzu` (zéro pollution `results/`, zéro KuzuDB, HoF mocké). Aucun « TODO ».

**Risque :** le smoke d'intégration construit un vrai `Biosphere3D` à `max_ticks=3` × 6 cellules — court mais réel ; `_disable_kuzu()` AVANT toute construction (appelé en tête de test). `wilcoxon_signed_rank` valide la séparation à n=8 (z≈2.45, p≈0.014<0.05 pour 8 diffs positives) — les tests synthétiques utilisent n=8.
