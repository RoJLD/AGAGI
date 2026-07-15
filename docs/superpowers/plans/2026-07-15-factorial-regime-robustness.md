# Robustesse aux régimes de la structure de facteurs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rejouer le factoriel 2⁴ du binding in-world (`compare_factorial`, EDR-177) dans plusieurs régimes (neutralisé / létal / payoff-rare) et comparer les 4 effets principaux, pour tester si la structure de facteurs (no_consume dominant, F2/F4 inertes) est invariante au régime.

**Architecture:** Une modif d'une ligne (exposer `night` en param de `compare_factorial`, défaut `False` = non-régressif) + un nouveau driver `tools/factorial_regime_sweep.py` qui définit les régimes, boucle `compare_factorial`+`_factorial_effects` par régime, et imprime une table comparative facteur×régime + le verdict cellule-0 par régime (garde-fou K≥12). Le factoriel et les 4 flags monde d'EDR-177 sont réutilisés tels quels.

**Tech Stack:** Python 3, numpy, torch, pytest.

## Global Constraints

- `night` défaut `False` dans `compare_factorial` ⇒ le régime neutralisé et tous les appels existants (CLI factorial, tests) sont inchangés (non-régressif). `penalty=0.0` reste hardcodé (non-biaisé, invariant du factoriel).
- **Zéro modification** de `src/backend_torch.py` ni de `compute_ab_verdict` (`tools/substrate_ab.py`).
- Garde-fou power-evaporation : pas de verdict POSITIF sous n=12 (le driver garde la conclusion cellule-0 positive derrière `len(seeds) >= 12`).
- Valeurs de régime létal/rare = valeurs de DÉPART (létal : `night=True, energy=150.0, base_metabolism=0.20` ; rare : `prey_sparse=2, prey_dense=8`) ; elles seront calibrées à l'exécution (hors périmètre du plan).
- Commits path-scopés (arbre partagé). Worktree `.worktrees/regime-sweep`, branche `chantier/factorial-regime-sweep`.

---

### Task 1: Exposer `night` en paramètre de `compare_factorial`

**Files:**
- Modify: `tools/torch_throw_gate_inworld_ab.py` (signature `compare_factorial` ligne 323-325 ; `kw` dict ligne 333)
- Test: `tests/sandbox/test_torch_throw_gate_factorial.py`

**Interfaces:**
- Consumes: `run_arm(..., night=...)` (param existant, ligne 41).
- Produces: `compare_factorial(..., night=False)` — le régime nuit devient pilotable, défaut `False`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/sandbox/test_torch_throw_gate_factorial.py` (le fichier importe déjà `run_arm, compare_factorial, _factorial_effects`) :

```python
import inspect


def test_compare_factorial_night_param_defaults_false():
    """EDR-178 : night est exposé en param de compare_factorial, défaut False (non-régressif :
    le régime neutralisé et le mode CLI factorial restent inchangés)."""
    sig = inspect.signature(compare_factorial)
    assert "night" in sig.parameters
    assert sig.parameters["night"].default is False


def test_compare_factorial_accepts_night_true():
    """compare_factorial accepte night=True (régime létal) et complète un run court sans crash,
    en renvoyant les 16 cellules."""
    cells = compare_factorial(seeds=(0,), prey_sparse=15, prey_dense=30, ticks=6, warmup=2,
                              n_agents=4, night=True)
    assert len(cells) == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py::test_compare_factorial_night_param_defaults_false -v`
Expected: FAIL (`assert "night" in sig.parameters` échoue — le param n'existe pas encore).

- [ ] **Step 3: Write minimal implementation**

Dans `tools/torch_throw_gate_inworld_ab.py`, modifier la signature de `compare_factorial` (lignes 323-325). Remplacer :

```python
def compare_factorial(seeds=(0, 1, 2, 3), prey_sparse=15, prey_dense=300, ticks=120, warmup=30,
                      n_agents=30, respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0,
                      energy=250.0, spear_weight=2.0, antisat=0.3):
```

par :

```python
def compare_factorial(seeds=(0, 1, 2, 3), prey_sparse=15, prey_dense=300, ticks=120, warmup=30,
                      n_agents=30, respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0,
                      energy=250.0, spear_weight=2.0, antisat=0.3, night=False):
```

Puis, dans le `kw` dict (ligne 333), remplacer `night=False` par `night=night` :

```python
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=night,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff, energy=energy,
              spear_weight=spear_weight, penalty=0.0, antisat=antisat)
```

(`penalty=0.0` reste hardcodé — invariant du factoriel.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py -v`
Expected: PASS (les 2 nouveaux tests + tous les tests factoriels existants restent verts ; le défaut `night=False` préserve le comportement neutralisé).

- [ ] **Step 5: Commit**

```bash
git add tools/torch_throw_gate_inworld_ab.py tests/sandbox/test_torch_throw_gate_factorial.py
git commit -m "feat(BIND): expose night dans compare_factorial (defaut False, EDR-178 regimes)"
```

---

### Task 2: Driver `factorial_regime_sweep.py` (sweep 3 régimes + table comparative)

**Files:**
- Create: `tools/factorial_regime_sweep.py`
- Test: `tests/sandbox/test_factorial_regime_sweep.py`

**Interfaces:**
- Consumes: `compare_factorial(..., night=...)` (Task 1) + `_factorial_effects(cells) -> {"main": {facteur: float}, "interactions": {...}}` (EDR-177, existant).
- Produces: `REGIMES` (dict nom→knobs) ; `run_sweep(regimes, seeds, ticks, warmup, n_agents) -> {nom: {"cells": list, "effects": dict}}` ; `_regime_main_effects_table(regime_effects) -> {facteur: {nom: float}}` (pur).

- [ ] **Step 1: Write the failing test**

Créer `tests/sandbox/test_factorial_regime_sweep.py` :

```python
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.factorial_regime_sweep import (REGIMES, run_sweep, _regime_main_effects_table)


def test_regimes_defined():
    """Les 3 régimes attendus sont définis, chacun avec les knobs de régime."""
    assert set(REGIMES) == {"neutralise", "letal", "rare"}
    for rk in REGIMES.values():
        assert set(rk) == {"night", "energy", "base_metabolism", "prey_sparse", "prey_dense"}
    assert REGIMES["neutralise"]["night"] is False        # baseline = EDR-177
    assert REGIMES["letal"]["night"] is True               # régime nuit létal


def test_regime_main_effects_table_pivots_by_factor():
    """_regime_main_effects_table (pur) pivote {régime: effects} en {facteur: {régime: effet}}."""
    regime_effects = {
        "A": {"main": {"no_consume": 0.4, "weightless": 0.0, "dense": 0.1, "conditional_credit": 0.0}},
        "B": {"main": {"no_consume": 0.5, "weightless": 0.3, "dense": 0.2, "conditional_credit": 0.0}},
    }
    tbl = _regime_main_effects_table(regime_effects)
    assert tbl["no_consume"] == {"A": 0.4, "B": 0.5}
    assert tbl["weightless"] == {"A": 0.0, "B": 0.3}       # F2 émerge en régime B
    assert set(tbl) == {"no_consume", "weightless", "dense", "conditional_credit"}


def test_run_sweep_smoke():
    """run_sweep tourne un sous-ensemble de régimes en config minuscule et renvoie cells+effects par régime."""
    tiny = {"neutralise": REGIMES["neutralise"], "rare": REGIMES["rare"]}
    out = run_sweep(tiny, seeds=(0,), ticks=6, warmup=2, n_agents=4)
    assert set(out) == {"neutralise", "rare"}
    for name, res in out.items():
        assert len(res["cells"]) == 16
        assert "main" in res["effects"] and "no_consume" in res["effects"]["main"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_factorial_regime_sweep.py::test_regimes_defined -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.factorial_regime_sweep'`).

- [ ] **Step 3: Write minimal implementation**

Créer `tools/factorial_regime_sweep.py` :

```python
"""EDR-178 : robustesse aux régimes de la structure de facteurs du binding in-world.

Rejoue le factoriel 2^4 (compare_factorial, EDR-177) dans 3 régimes et compare les 4 effets
principaux : la structure trouvée par EDR-177 (no_consume dominant, F2/F4 inertes) est-elle
invariante au régime, ou F2 (weightless) émerge-t-il sous survie contrainte / F4
(conditional_credit) sous payoff rare ? Régimes létal/rare = valeurs de DÉPART, calibrées à
l'exécution. Non-biaisé (penalty=0) hérité de compare_factorial.

Usage : python tools/factorial_regime_sweep.py
  (env : FRS_SEEDS, FRS_TICKS, FRS_WARMUP, FRS_AGENTS, FRS_REGIMES=neutralise,letal,rare)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import compare_factorial, _factorial_effects

# Régimes : mêmes 16 cellules 2^4, seuls les knobs de régime changent. Létal/rare = valeurs de
# DÉPART (calibrées à l'exécution : voir spec §Calibration).
REGIMES = {
    "neutralise": dict(night=False, energy=250.0, base_metabolism=0.05, prey_sparse=15, prey_dense=300),
    "letal":      dict(night=True,  energy=150.0, base_metabolism=0.20, prey_sparse=15, prey_dense=300),
    "rare":       dict(night=False, energy=250.0, base_metabolism=0.05, prey_sparse=2,  prey_dense=8),
}

_FACTORS = ("no_consume", "weightless", "dense", "conditional_credit")


def run_sweep(regimes, seeds=(0, 1, 2, 3), ticks=120, warmup=30, n_agents=30):
    """Pour chaque régime nommé (dict de knobs), lance compare_factorial + _factorial_effects.
    Retourne {nom: {"cells": [...], "effects": {...}}}."""
    out = {}
    for name, rk in regimes.items():
        cells = compare_factorial(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=n_agents, **rk)
        out[name] = {"cells": cells, "effects": _factorial_effects(cells)}
    return out


def _regime_main_effects_table(regime_effects):
    """Pivote {nom: effects (de _factorial_effects)} en {facteur: {nom: effet_principal}}."""
    return {f: {name: eff["main"][f] for name, eff in regime_effects.items()} for f in _FACTORS}


def _cell0(cells):
    """La cellule tout-propre (T,T,T,T)."""
    return next(c for c in cells if c["no_consume"] and c["weightless"]
                and c["dense"] and c["conditional_credit"])


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    seeds = tuple(int(x) for x in os.environ.get("FRS_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("FRS_TICKS", "120"))
    warmup = int(os.environ.get("FRS_WARMUP", "30"))
    agents = int(os.environ.get("FRS_AGENTS", "30"))
    names = os.environ.get("FRS_REGIMES", "neutralise,letal,rare").split(",")
    regimes = {n: REGIMES[n] for n in names if n in REGIMES}

    out = run_sweep(regimes, seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents)
    effects = {n: res["effects"] for n, res in out.items()}
    tbl = _regime_main_effects_table(effects)

    cols = list(regimes)
    print("EFFETS PRINCIPAUX (diff propre - confond) par regime :")
    print(f"  {'facteur':22s} " + " ".join(f"{c:>12s}" for c in cols))
    for f in _FACTORS:
        print(f"  {f:22s} " + " ".join(f"{tbl[f][c]:+12.3f}" for c in cols))

    _lab = {"GRADIENT_GAGNE": "BINDE", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PLAT"}
    print("\nCELLULE-0 (tout-propre) par regime :")
    for n in cols:
        c0 = _cell0(out[n]["cells"])
        v = c0["verdict"]
        pos = v["verdict"] == "GRADIENT_GAGNE"
        if pos and len(seeds) >= 12:
            concl = "BINDE (K>=12)"
        elif pos:
            concl = f"BINDING_APPARENT n={len(seeds)}<12 NON-CONCLUANT"
        else:
            concl = _lab.get(v["verdict"], "?")
        print(f"  {n:12s} diff={c0['median_diff']:+.3f} kills={c0['median_kills']:.0f} "
              f"-> {v['verdict']} ({concl}) sign_p={v.get('sign_p')}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_factorial_regime_sweep.py -v`
Expected: PASS (3 tests ; le smoke lance 2 régimes × 16 cellules à ticks=6, ~30-60s).

- [ ] **Step 5: Run the full factorial + regime suite (non-régression)**

Run: `python -m pytest tests/sandbox/test_torch_throw_gate_factorial.py tests/sandbox/test_factorial_regime_sweep.py -v`
Expected: PASS (tests factoriels d'EDR-177 + Task 1 + les 3 nouveaux).

- [ ] **Step 6: Commit**

```bash
git add tools/factorial_regime_sweep.py tests/sandbox/test_factorial_regime_sweep.py
git commit -m "feat(BIND): driver factorial_regime_sweep — sweep 3 regimes + table comparative (EDR-178)"
```

---

## Self-Review

**1. Spec coverage :**
- Exposer `night` → Task 1. ✅
- Driver `factorial_regime_sweep.py` (REGIMES + run_sweep + table pivot + __main__ + garde K≥12) → Task 2. ✅
- 3 régimes neutralisé/létal/rare avec valeurs de départ → REGIMES dict (Task 2). ✅
- Verdict cellule-0 par régime + garde-fou K≥12 → __main__ (Task 2). ✅
- Non-régression (night défaut False) → Task 1 test signature + suite complète. ✅
- Zéro modif backend_torch/compute_ab_verdict → aucun fichier touché ne les inclut. ✅
- Calibration = étape d'exécution hors périmètre (valeurs de départ gravées) → noté Global Constraints. ✅

**2. Placeholder scan :** aucun TBD/TODO ; tout bloc de code complet ; valeurs de régime concrètes (départ, calibration explicitement hors-périmètre). ✅

**3. Type consistency :** `compare_factorial(..., night=False)`, `run_sweep(regimes, seeds, ticks, warmup, n_agents) -> {nom:{"cells","effects"}}`, `_regime_main_effects_table(regime_effects) -> {facteur:{nom:effet}}`, `_factorial_effects(cells)["main"][facteur]` : noms/signatures cohérents entre définition et usages (tests, __main__). ✅

## Notes d'exécution (post-plan, hors tâches)

- **Calibration d'abord** : sonde de survie sur la cellule NWDK à quelques seeds pour ajuster `letal` (viser cohorte vivante ~½ fenêtre post-warmup sous attrition) et `rare` (kills médians dense ~3-8) ; éditer `REGIMES` si besoin.
- Puis run K=12 (`FRS_SEEDS=0..11`) sur les 3 régimes → EDR-178 (table facteur×régime + verdicts cellule-0).
- PR base `feat/d1-prod-pairing` : rapatrie factoriel + EDR-177 (orphelin #164) + regime-sweep + EDR-178.
