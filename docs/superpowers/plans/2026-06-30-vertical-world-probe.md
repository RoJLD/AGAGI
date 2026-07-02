# Probe verticalité Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/vertical_world_probe.py` — un probe A/B (2D vs 3D via `use_3d`) qui mesure si un champion transplanté exploite l'affordance verticale (utilisation de Z), pour décider si la verticalité porte du signal.

**Architecture:** Fonction de décision PURE (`classify_vertical_signal`) testée en isolation, + un harnais `measure_arm` qui monte `Biosphere3D`, fait tourner une cohorte fixe de clones et instrumente l'usage de Z depuis la boucle (zéro modif `src/`). Calque de `tools/famine_harshness_probe.py`.

**Tech Stack:** Python, numpy, pytest. Lecture seule de `src/worlds/world_1_stoneage.py` (`Biosphere3D`), `src/agents/mamba_agent.py` (`MambaAgent`), `src/environments/config.py` (`WorldConfig`), `src/seed_ai/harness.py` (`seed_at`), `src/seed_ai/persistence.py` (`load_hall_of_fame`).

## Global Constraints

- Backend Python. **Aucune modification de `src/`** — fichiers neufs uniquement.
- Single-process (pas de multiprocess → évite les hazards ProcessPool/KuzuDB).
- Fonction de décision PURE et testée ; seuils explicites/paramétrés (pas de nombres magiques cachés).
- Reproductibilité : `seed_at(seed, era)`, `w.benchmark_mode=True`, `w.memory_retriever.stop()/clear()` si présent.
- Worktree `c:\Users\robla\VScode_Project\AGAGI-probe`, branche `probe/vertical-world` (depuis `main`).
- Commits **path-scoped** (`git commit -- <chemins>`, jamais `git add -A`). Trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Le HoF est gitignored : le probe le lit via `HOF_PATH` (env). Ne PAS committer de `.pkl`.

## File Structure

- **Create** `tools/vertical_world_probe.py` — fonction pure + harnais `measure_arm` + `run_probe` + `main`.
- **Create** `tests/test_vertical_world_probe.py` — tests unitaires (fonction pure) + smoke d'intégration.

---

### Task 1: Fonction de décision pure `classify_vertical_signal`

**Files:**
- Create: `tools/vertical_world_probe.py`
- Test: `tests/test_vertical_world_probe.py`

**Interfaces:**
- Produces : `classify_vertical_signal(z_range_3d, updown_frac_3d, updown_floor=0.25, margin=1.2, z_eps=0.5, survival_2d=None, survival_3d=None) -> dict`. Renvoie `{verdict, z_range_3d, updown_frac_3d, threshold, survival_ratio}`. `verdict ∈ {"Z_UTILISE","Z_INERTE"}`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_vertical_world_probe.py` :

```python
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.vertical_world_probe import classify_vertical_signal


def test_z_utilise_quand_range_et_updown_au_dessus_du_seuil():
    r = classify_vertical_signal(z_range_3d=2.0, updown_frac_3d=0.40)
    assert r["verdict"] == "Z_UTILISE"
    assert r["threshold"] == 0.25 * 1.2


def test_z_inerte_quand_range_nul():
    r = classify_vertical_signal(z_range_3d=0.0, updown_frac_3d=0.40)
    assert r["verdict"] == "Z_INERTE"


def test_z_inerte_quand_updown_sous_seuil():
    r = classify_vertical_signal(z_range_3d=2.0, updown_frac_3d=0.10)
    assert r["verdict"] == "Z_INERTE"


def test_survival_ratio_calcule_quand_fourni():
    r = classify_vertical_signal(2.0, 0.40, survival_2d=100.0, survival_3d=60.0)
    assert abs(r["survival_ratio"] - 0.6) < 1e-9


def test_survival_ratio_none_si_non_fourni():
    r = classify_vertical_signal(2.0, 0.40)
    assert r["survival_ratio"] is None


def test_survival_2d_zero_ne_divise_pas_par_zero():
    r = classify_vertical_signal(2.0, 0.40, survival_2d=0.0, survival_3d=5.0)
    assert r["survival_ratio"] > 0  # epsilon au dénominateur, pas d'exception
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `cd /c/Users/robla/VScode_Project/AGAGI-probe && python -m pytest tests/test_vertical_world_probe.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (le module/fonction n'existe pas).

- [ ] **Step 3: Créer le module avec la fonction pure**

Créer `tools/vertical_world_probe.py` :

```python
"""Probe VERTICALITÉ : un champion évolué en 2D exploite-t-il l'affordance verticale quand
on active use_3d ? Compare 2 bras (2D/3D) sur une cohorte fixe de clones d'un champion HoF.
Métrique de DÉCISION = utilisation de Z dans le bras 3D (z-range + fraction Up/Down chez les
survivants) ; survie = interprétatif (le cube 3D est plus creux). Détecteur de POSITIF bon
marché avant tout investissement de visualisation 3D. Voir spec 2026-06-30-vertical-world-probe."""
import os
import sys
import json
import statistics
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def classify_vertical_signal(z_range_3d: float, updown_frac_3d: float,
                             updown_floor: float = 0.25, margin: float = 1.2,
                             z_eps: float = 0.5,
                             survival_2d: Optional[float] = None,
                             survival_3d: Optional[float] = None) -> Dict:
    """PUR. Verdict d'utilisation de Z dans le bras 3D.
    Z_UTILISE si z_range_3d > z_eps ET updown_frac_3d > updown_floor*margin ; sinon Z_INERTE.
    updown_floor = 2/8 (Up+Down sur 8 actions argmax) ; margin = marge au-dessus du hasard ;
    z_eps = au moins une transition de couche. survival_ratio interprétatif (epsilon anti /0)."""
    threshold = updown_floor * margin
    z_used = z_range_3d > z_eps
    updown_used = updown_frac_3d > threshold
    verdict = "Z_UTILISE" if (z_used and updown_used) else "Z_INERTE"
    survival_ratio: Optional[float] = None
    if survival_2d is not None and survival_3d is not None:
        survival_ratio = survival_3d / max(survival_2d, 1e-6)
    return {"verdict": verdict, "z_range_3d": z_range_3d, "updown_frac_3d": updown_frac_3d,
            "threshold": threshold, "survival_ratio": survival_ratio}
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `cd /c/Users/robla/VScode_Project/AGAGI-probe && python -m pytest tests/test_vertical_world_probe.py -q`
Expected: PASS — 6 tests verts.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(probe): classify_vertical_signal pur + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- tools/vertical_world_probe.py tests/test_vertical_world_probe.py
```

---

### Task 2: Harnais `measure_arm` + `run_probe` + `main` + smoke

**Files:**
- Modify: `tools/vertical_world_probe.py`
- Test: `tests/test_vertical_world_probe.py`

**Interfaces:**
- Consumes : `classify_vertical_signal` (Task 1) ; `Biosphere3D`, `MambaAgent`, `WorldConfig`, `seed_at`, `load_hall_of_fame`.
- Produces :
  - `measure_arm(genome, use_3d, seed, n_eras=2, n_agents=12, max_ticks=600) -> dict` → `{"survival": float, "z_range": float, "updown_frac": float}`
  - `run_probe(genome, seeds, **kw) -> dict` → agrégats par bras + `verdict`.

- [ ] **Step 1: Écrire le smoke d'intégration qui échoue**

Ajouter à `tests/test_vertical_world_probe.py` :

```python
def test_measure_arm_smoke_3d_tourne_et_renvoie_les_cles():
    from tools.vertical_world_probe import measure_arm
    from src.agents.mamba_agent import MambaAgent
    genome = MambaAgent().genome  # génome frais, aucune dépendance HoF
    out = measure_arm(genome, use_3d=True, seed=42, n_eras=1, n_agents=3, max_ticks=20)
    assert set(out.keys()) == {"survival", "z_range", "updown_frac"}
    assert out["z_range"] >= 0.0
    assert 0.0 <= out["updown_frac"] <= 1.0
```

- [ ] **Step 2: Lancer le smoke, vérifier qu'il échoue**

Run: `cd /c/Users/robla/VScode_Project/AGAGI-probe && python -m pytest tests/test_vertical_world_probe.py::test_measure_arm_smoke_3d_tourne_et_renvoie_les_cles -q`
Expected: FAIL — `ImportError: cannot import name 'measure_arm'`.

- [ ] **Step 3: Ajouter le harnais dans `tools/vertical_world_probe.py`**

Ajouter les imports sim (après `import numpy as np`) et les fonctions (après `classify_vertical_signal`) :

```python
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at


def measure_arm(genome, use_3d: bool, seed: int, n_eras: int = 2,
                n_agents: int = 12, max_ticks: int = 600) -> Dict:
    """Fait tourner une cohorte fixe de clones du génome dans Biosphere3D (2D ou 3D).
    Instrumente l'usage de Z depuis la boucle (zéro modif src/). Retourne survie médiane
    (médiane de médianes par ère) + z_range/updown_frac moyens chez les survivants (steps >=
    médiane des steps de l'ère)."""
    surv_per_era: List[float] = []
    z_ranges: List[float] = []
    updown_fracs: List[float] = []
    for era in range(max(1, n_eras)):
        seed_at(seed, era)
        cfg = WorldConfig()
        cfg.use_3d = use_3d
        w = Biosphere3D(cfg)
        if hasattr(w, "memory_retriever") and w.memory_retriever is not None:
            w.memory_retriever.stop()
            w.memory_retriever.clear()
        w.benchmark_mode = True
        for _ in range(n_agents):
            a = MambaAgent()
            a.from_genome(genome)
            w.add_agent(a, energy=80.0)
        tracker: Dict = {}  # id -> {z_min,z_max,ups,downs,steps}
        t = 0
        while w.agents and t < max_ticks:
            w.step()
            for a in w.agents:
                aid = a["id"]
                z = int(a.get("z", 0))
                la = int(a.get("last_action", -1))
                tr = tracker.setdefault(aid, {"z_min": z, "z_max": z, "ups": 0, "downs": 0, "steps": 0})
                tr["z_min"] = min(tr["z_min"], z)
                tr["z_max"] = max(tr["z_max"], z)
                if la == 4:
                    tr["ups"] += 1
                elif la == 5:
                    tr["downs"] += 1
                tr["steps"] += 1
            t += 1
        ages = [int(a["age"]) for a in w.agents + list(getattr(w, "dead_agents", []))]
        surv_per_era.append(float(np.median(ages)) if ages else 0.0)
        # Survivors = agents ayant vécu >= médiane des steps de l'ère (proxy survie).
        steps_list = [tr["steps"] for tr in tracker.values() if tr["steps"] > 0]
        if steps_list:
            med_steps = float(np.median(steps_list))
            for tr in tracker.values():
                if tr["steps"] >= med_steps and tr["steps"] > 0:
                    z_ranges.append(float(tr["z_max"] - tr["z_min"]))
                    updown_fracs.append((tr["ups"] + tr["downs"]) / tr["steps"])
    return {
        "survival": float(statistics.median(surv_per_era)) if surv_per_era else 0.0,
        "z_range": float(np.mean(z_ranges)) if z_ranges else 0.0,
        "updown_frac": float(np.mean(updown_fracs)) if updown_fracs else 0.0,
    }


def run_probe(genome, seeds: List[int], n_eras: int = 2, n_agents: int = 12,
              max_ticks: int = 600) -> Dict:
    """2 bras (2D/3D) sur K seeds appariés. Agrège (médiane survie, moyenne z-usage) et classifie."""
    a2d = [measure_arm(genome, False, s, n_eras, n_agents, max_ticks) for s in seeds]
    a3d = [measure_arm(genome, True, s, n_eras, n_agents, max_ticks) for s in seeds]
    surv_2d = float(statistics.median([r["survival"] for r in a2d]))
    surv_3d = float(statistics.median([r["survival"] for r in a3d]))
    z_range_3d = float(np.mean([r["z_range"] for r in a3d]))
    updown_frac_3d = float(np.mean([r["updown_frac"] for r in a3d]))
    verdict = classify_vertical_signal(z_range_3d, updown_frac_3d,
                                       survival_2d=surv_2d, survival_3d=surv_3d)
    return {"seeds": list(seeds), "arm_2d": a2d, "arm_3d": a3d,
            "survival_2d": surv_2d, "survival_3d": surv_3d, **verdict}
```

- [ ] **Step 4: Lancer le smoke, vérifier qu'il passe**

Run: `cd /c/Users/robla/VScode_Project/AGAGI-probe && python -m pytest tests/test_vertical_world_probe.py -q`
Expected: PASS — 7 tests verts (6 purs + 1 smoke). Le smoke peut prendre quelques secondes (20 ticks × 3 agents).

- [ ] **Step 5: Ajouter `main()` (lecture HoF + sortie)**

Ajouter en fin de `tools/vertical_world_probe.py` :

```python
def main():
    import importlib
    import src.seed_ai.persistence as P
    hof = os.environ.get("HOF_PATH", "data/hall_of_fame.pkl")
    os.environ["HOF_PATH"] = hof
    importlib.reload(P)
    entries = P.load_hall_of_fame()[1]
    if not entries:
        print(f"ERREUR: Hall of Fame vide/absent à HOF_PATH={hof}. "
              f"Pointe HOF_PATH sur un HoF stoneage évolué.")
        return None
    genome = entries[0].genome
    seeds = [int(x) for x in os.environ.get("VWP_SEEDS", "42,43,44,45,46").split(",") if x.strip()]
    n_eras = int(os.environ.get("VWP_ERAS", "2"))
    n_agents = int(os.environ.get("VWP_AGENTS", "12"))
    max_ticks = int(os.environ.get("VWP_TICKS", "600"))
    r = run_probe(genome, seeds, n_eras=n_eras, n_agents=n_agents, max_ticks=max_ticks)
    print(f"seeds={r['seeds']}")
    print(f"survie   2D={r['survival_2d']:.1f}  3D={r['survival_3d']:.1f}  "
          f"ratio={r['survival_ratio']:.2f}" if r['survival_ratio'] is not None else "")
    print(f"z_range_3d={r['z_range_3d']:.2f}  updown_frac_3d={r['updown_frac_3d']:.3f}  "
          f"seuil={r['threshold']:.3f}")
    print(f"VERDICT: {r['verdict']}")
    print("VWP_JSON", json.dumps(r))
    return r


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Vérifier la suite complète du probe**

Run: `cd /c/Users/robla/VScode_Project/AGAGI-probe && python -m pytest tests/test_vertical_world_probe.py -q`
Expected: PASS — 7 tests verts.

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(probe): harnais measure_arm/run_probe/main + smoke 3D

Cohorte fixe de clones, instrumentation Z depuis la boucle (zero modif src/),
benchmark_mode + memory_retriever.stop pour la repro. HoF via HOF_PATH.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- tools/vertical_world_probe.py tests/test_vertical_world_probe.py
```

---

## Notes d'exécution

- **Ordre** : Task 1 (fonction pure, fondation testable) puis Task 2 (harnais).
- **Pas de revue finale séparée** : 2 tâches cohérentes, un seul script backend ; si les revues de tâche sont propres et les gates vertes, la revue whole-branch est repliée dans la revue de Task 2.
- **Modèles SDD** : Task 1 = transcription (code+tests fournis) → implémenteur haiku ; Task 2 = intégration sim (imports, boucle, instrumentation) → implémenteur sonnet ; reviewers sonnet.
- **Après merge du code** : LE CONTRÔLEUR lance le probe réel pour produire le verdict :
  `HOF_PATH=/c/Users/robla/VScode_Project/AGAGI/data/hall_of_fame.pkl python -m tools.vertical_world_probe`
  (lecture seule du HoF du tree principal ; ~quelques minutes single-process). Ce run N'EST PAS une tâche du plan (il produit la donnée scientifique, pas du code) — il suit la clôture de branche.
- **Pas de numéro EDR** ici (collisions inter-sessions) : le record EDR s'écrira après le run, en coordination.
