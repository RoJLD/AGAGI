# Pont proxy→in-world du demand-marker + formalisation — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter le témoin causal within-subject (ablation de perception) sur les 5 mondes réels, et formaliser l'instrument en module réutilisable + REF + note méthodes.

**Architecture:** Un module pur `demand_marker.py` (verdict d'ablation, garde-fou n<12) partagé par le proxy S2-001 et un nouvel outil in-world `s2_demand_ablation.py`. L'ablation in-world = `PerceptionAblatedMamba(MambaBatchModel)` qui permute (dérange) les lignes de `batch_obs` avant `super().forward()` — injecté via le seam `batch_model_cls` de `s2_demand.run_condition`, sans modifier ce dernier.

**Tech Stack:** Python 3, numpy, pytest. Réutilise `tools/s2_demand.py` (import), `src/agents/mamba_agent.py` (`MambaBatchModel`), le HoF `data/hall_of_fame.pkl`.

## Global Constraints

- Arbre partagé : commits **path-scopés** (`git add <fichiers exacts>`, jamais `git add -A`/`.`).
- **Ne jamais modifier** `tools/s2_demand.py` (benchmark pré-enregistré) ni aucun fichier `src/**` / monde / outil //-authored. On IMPORTE, on ne patche pas.
- Seul fichier existant modifiable : `tools/world_demand_marker_probe.py` (S2-001, authored par cette lignée).
- RNG : tirer du flux global `np.random` (jamais un RNG privé non-seedé) pour préserver l'appariement du Harness.
- Verdicts code en anglais : `X_DEMANDED`, `X_DECOY`, `INCONCLUSIVE`.
- Garde-fou n<12 : aucun verdict POSITIF (`*_DEMANDED`) sous n<12 → `INCONCLUSIVE`. Ne PAS toucher `compute_ab_verdict` (partagé) — garde local.
- Convention record : préfixe thématique (`S2-002`), `gate:` + `tests:` obligatoires (règle anti-orphelin).
- Fin de course : `python tools/consolidate_records.py` doit rester `problemes=0` ; `python tools/check_record_links.py --report` : 0 NOUVEL orphelin.

---

## File Structure

- **Create** `tools/demand_marker.py` — fonction pure `ablation_verdict(intact, ablated, weight_on_x=None, ...)`. Aucune dépendance monde/torch. Unique définition du témoin.
- **Create** `tests/test_demand_marker.py` — verdicts effondrement/plat/n-floor + égalité arithmétique avec le calcul historique du proxy (non-régression).
- **Modify** `tools/world_demand_marker_probe.py` — router le ratio WITHIN via `ablation_verdict` (le reste inchangé).
- **Create** `tools/s2_demand_ablation.py` — `derange_rows`, `PerceptionAblatedMamba`, `run_ablation_map`, `main`. Importe `run_condition`/`WORLDS`/`load_champion_genome` de `s2_demand`.
- **Create** `tests/test_perception_ablation.py` — `derange_rows` (dérangement, no-mutation, B<2) + `PerceptionAblatedMamba.forward` passe l'obs dérangée.
- **Create** `tests/test_s2_ablation_smoke.py` — l'outil tourne sur 1 monde, K minimal (opt-in `slow`).
- **Create** `docs/REF/REF-DEMAND-MARKER.md` — record REF adoptable (`adopt_for`).
- **Create** `docs/EDR/S2-002_*.md` — verdict du push (carte per-monde), rempli depuis le run.
- **Create** `docs/roadmap/DEMAND_MARKER_METHOD.md` — note méthodes transversale.

---

## Task 1 : Module `demand_marker` + refactor S2-001 (non-régression)

**Files:**
- Create: `tools/demand_marker.py`
- Create: `tests/test_demand_marker.py`
- Modify: `tools/world_demand_marker_probe.py` (main : router le ratio within)

**Interfaces:**
- Produces: `ablation_verdict(intact, ablated, weight_on_x=None, n_floor=12, collapse_factor=1.5, decoy_ceiling=1.3, eps=1e-9) -> dict` avec clés `ratio: float`, `n: int`, `collapse: bool`, `decoy: bool`, `corroborant`, `verdict: str ∈ {"X_DEMANDED","X_DECOY","INCONCLUSIVE"}`.
- Consumes (refactor) : le proxy calcule déjà `within = ft/max(fa, 1e-9)` ; on remplace par `ablation_verdict(...)["ratio"]`.

- [ ] **Step 1 : Écrire les tests d'échec**

```python
# tests/test_demand_marker.py
import math
import statistics
from tools.demand_marker import ablation_verdict


def test_collapse_gives_demanded():
    intact = [200.0] * 12
    ablated = [40.0] * 12                      # effondrement 5x
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "X_DEMANDED"
    assert v["collapse"] is True
    assert math.isclose(v["ratio"], 5.0, rel_tol=1e-6)
    assert v["n"] == 12


def test_flat_gives_decoy():
    intact = [200.0] * 12
    ablated = [195.0] * 12                      # plat -> ratio ~1.03 < 1.3
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "X_DECOY"
    assert v["decoy"] is True


def test_n_floor_blocks_positive():
    intact = [200.0] * 5                         # n=5 < 12
    ablated = [40.0] * 5                          # effondrement franc MAIS sous-puissance
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "INCONCLUSIVE"        # garde-fou : pas de POSITIF sous n<12
    assert v["collapse"] is True                  # l'effet est là...
    assert v["n"] == 5                            # ...mais n insuffisant


def test_ratio_matches_legacy_proxy_formula():
    # non-régression : ablation_verdict doit reproduire EXACTEMENT le calcul historique
    # du proxy S2-001 : within = median(intact) / max(median(ablated), 1e-9)
    intact = [10.0, 30.0, 50.0, 70.0]            # median 40
    ablated = [5.0, 15.0, 25.0, 35.0]            # median 20
    legacy = statistics.median(intact) / max(statistics.median(ablated), 1e-9)
    v = ablation_verdict(intact, ablated)
    assert math.isclose(v["ratio"], legacy, rel_tol=1e-12)


def test_corroborant_passthrough():
    v = ablation_verdict([200.0] * 12, [40.0] * 12, weight_on_x=0.87)
    assert v["corroborant"] == 0.87
    v2 = ablation_verdict([200.0] * 12, [40.0] * 12)
    assert v2["corroborant"] is None
```

- [ ] **Step 2 : Lancer les tests, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_demand_marker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.demand_marker'`.

- [ ] **Step 3 : Implémenter le module**

```python
# tools/demand_marker.py
"""Instrument transversal : le témoin CAUSAL de « la capacité X est-elle exigée » = ablation
WITHIN-subject de X, pas « un agent équipé de X réussit » (between-subject, faux-positif).

ablation_verdict compare la fitness (survie) d'un MÊME sujet avec X intact vs X ablaté :
- ratio = median(intact) / median(ablated) ; ratio >> 1 => X est causalement porteur (X_DEMANDED) ;
  ratio ~ 1 => X est un leurre (X_DECOY).
- garde-fou n<12 : aucun verdict POSITIF sous puissance insuffisante (les petits n s'évaporent).
- corroborant optionnel weight_on_x = |W| que la politique met sur X (2e témoin ; le proxy montre
  |W|->0 quand X ne paie pas). Non calculable sur le champion HoF in-world -> None.

REF : docs/REF/REF-DEMAND-MARKER.md. Modalités : perception (S2-001, S2-002 in-world),
communication (LANG-006), généralisation (G1-001), mémoire (MEM-001).
"""
import statistics


def ablation_verdict(intact, ablated, weight_on_x=None,
                     n_floor=12, collapse_factor=1.5, decoy_ceiling=1.3, eps=1e-9):
    """intact, ablated : itérables de fitness appariées (survies par ère/seed). Renvoie le dict verdict.

    - collapse := ratio >= collapse_factor (X porteur)  ; decoy := ratio <= decoy_ceiling (X leurre).
    - verdict : X_DEMANDED si collapse ET n>=n_floor ; X_DECOY si decoy ; sinon INCONCLUSIVE.
    """
    intact = [float(x) for x in intact]
    ablated = [float(x) for x in ablated]
    n = min(len(intact), len(ablated))
    med_i = statistics.median(intact) if intact else 0.0
    med_a = statistics.median(ablated) if ablated else 0.0
    ratio = med_i / max(med_a, eps)
    collapse = ratio >= collapse_factor
    decoy = ratio <= decoy_ceiling
    if collapse and n >= n_floor:
        verdict = "X_DEMANDED"
    elif decoy:
        verdict = "X_DECOY"
    else:
        verdict = "INCONCLUSIVE"          # effet présent mais sous-puissant, OU zone grise
    return {"ratio": float(ratio), "n": int(n), "collapse": bool(collapse),
            "decoy": bool(decoy), "corroborant": weight_on_x, "verdict": verdict}
```

- [ ] **Step 4 : Lancer les tests, vérifier le succès**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_demand_marker.py -v`
Expected: PASS (5 tests).

Note edge : `test_flat_gives_decoy` — ratio 200/195 ≈ 1.026 ≤ 1.3 → `decoy=True`, verdict `X_DECOY`. `test_n_floor` — ratio 5.0 ≥ 1.5 → `collapse=True` mais n=5 < 12 → `INCONCLUSIVE`.

- [ ] **Step 5 : Refactorer S2-001 pour router le ratio within via le module**

Dans `tools/world_demand_marker_probe.py`, `main()`. Repérer (autour l. 124-132) :

```python
    for demanding, name in ((True, "DEMANDING"), (False, "TRIVIAL")):
        rows = [run_world(demanding, K, s, ticks=ticks) for s in seeds]
        ft = statistics.median(r["fit_true"] for r in rows)
        fa = statistics.median(r["fit_ablated"] for r in rows)
        ra = statistics.median(r["random_action"] for r in rows)
        ow = statistics.median(r["obs_weight"] for r in rows)
        between = ft / max(ra, 1e-9)          # « un survivant compétent existe ? »
        within = ft / max(fa, 1e-9)           # « la perception est-elle porteuse ? »
```

Remplacer les deux lignes `fa = ...` et `within = ...` par un appel au module (le ratio reste
arithmétiquement identique — non-régression garantie par `test_ratio_matches_legacy_proxy_formula`) :

```python
    from tools.demand_marker import ablation_verdict
    ...
    for demanding, name in ((True, "DEMANDING"), (False, "TRIVIAL")):
        rows = [run_world(demanding, K, s, ticks=ticks) for s in seeds]
        ft = statistics.median(r["fit_true"] for r in rows)
        fa = statistics.median(r["fit_ablated"] for r in rows)   # conservé pour l'affichage du tableau
        ra = statistics.median(r["random_action"] for r in rows)
        ow = statistics.median(r["obs_weight"] for r in rows)
        between = ft / max(ra, 1e-9)          # « un survivant compétent existe ? »
        wv = ablation_verdict([r["fit_true"] for r in rows],
                              [r["fit_ablated"] for r in rows],
                              weight_on_x=ow)  # ratio within + verdict, définition partagée
        within = wv["ratio"]                  # inchangé numériquement vs ft/max(fa,1e-9)
```

`fa` reste une médiane directe (pas de reconstruction circulaire) ; seul `within` passe par le module.

Le reste de `main` (calcul `between_falsepos`/`within_correct`, VERDICT) est INCHANGÉ.

- [ ] **Step 6 : Vérifier la non-régression du proxy (fumée rapide)**

Run: `WDM_SEEDS=2 WDM_TICKS=60 PYTHONIOENCODING=utf-8 python tools/world_demand_marker_probe.py`
Expected: s'exécute sans erreur, imprime le tableau + une ligne `VERDICT=...` (le verdict peut varier à
si peu de seeds ; on vérifie seulement l'absence de crash et que le ratio within reste fini/positif).

- [ ] **Step 7 : Commit (path-scopé)**

```bash
git add tools/demand_marker.py tests/test_demand_marker.py tools/world_demand_marker_probe.py
git commit -m "feat(S2-002): module demand_marker (témoin d'ablation partagé) + refactor S2-001

Extrait le témoin within-subject (ratio + garde-fou n<12 + verdict) en module réutilisable,
importé par le proxy S2-001. Ratio inchangé (non-régression testée). Prépare le pont in-world.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : Ablation in-world `s2_demand_ablation.py` + `PerceptionAblatedMamba`

**Files:**
- Create: `tools/s2_demand_ablation.py`
- Create: `tests/test_perception_ablation.py`
- Create: `tests/test_s2_ablation_smoke.py`

**Interfaces:**
- Consumes: `ablation_verdict` (Task 1) ; `from tools.s2_demand import run_condition, WORLDS, load_champion_genome` ; `from src.agents.mamba_agent import MambaBatchModel`.
- Produces:
  - `derange_rows(batch_obs, rng=None) -> np.ndarray` : copie permutée sans point fixe si B≥2, copie inchangée si B<2 ; ne mute jamais l'entrée.
  - `class PerceptionAblatedMamba(MambaBatchModel)` : `forward(batch_obs, env_surprise_batch=None)` délègue à `super().forward(derange_rows(batch_obs), env_surprise_batch)`.
  - `run_ablation_map(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=400) -> dict` : `{world: {within_ratio, between_ratio, verdict, n}}`.

- [ ] **Step 1 : Écrire les tests d'échec (ablation)**

```python
# tests/test_perception_ablation.py
import numpy as np
import pytest
from tools.s2_demand_ablation import derange_rows, PerceptionAblatedMamba
from src.agents.mamba_agent import MambaBatchModel


def test_derange_no_fixed_point():
    np.random.seed(0)
    obs = np.arange(20 * 4, dtype=np.float32).reshape(20, 4)  # 20 lignes distinctes
    out = derange_rows(obs)
    assert out.shape == obs.shape
    # aucune ligne ne reste à sa place (dérangement)
    assert not np.any(np.all(out == obs, axis=1))
    # c'est bien une PERMUTATION des lignes d'origine (ensemble préservé)
    assert sorted(out[:, 0].tolist()) == sorted(obs[:, 0].tolist())


def test_derange_does_not_mutate_input():
    np.random.seed(1)
    obs = np.arange(12 * 3, dtype=np.float32).reshape(12, 3)
    before = obs.copy()
    _ = derange_rows(obs)
    assert np.array_equal(obs, before)      # entrée intacte


def test_derange_small_batch_is_identity():
    obs1 = np.ones((1, 5), dtype=np.float32)
    assert np.array_equal(derange_rows(obs1), obs1)
    obs0 = np.zeros((0, 5), dtype=np.float32)
    assert derange_rows(obs0).shape == (0, 5)


def test_forward_feeds_deranged_obs(monkeypatch):
    # On capture ce que le parent reçoit, sans instancier le vrai moteur.
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(PerceptionAblatedMamba)      # saute __init__ (pas d'agents)
    np.random.seed(2)
    obs = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)
    inst.forward(obs)
    # le parent a reçu une obs DÉRANGÉE (aucune ligne à sa place), pas l'obs d'origine
    assert not np.any(np.all(captured["obs"] == obs, axis=1))
    assert sorted(captured["obs"][:, 0].tolist()) == sorted(obs[:, 0].tolist())
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_perception_ablation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.s2_demand_ablation'`.

- [ ] **Step 3 : Implémenter l'outil**

```python
# tools/s2_demand_ablation.py
"""S2-002 — Pont proxy→in-world du demand-marker : bras d'ablation-perception WITHIN-subject sur les
5 mondes réels. Le champion HoF joue INTACT vs perception PERMUTÉE (chaque agent reçoit l'obs d'un
pair -> décorrélée de SA réalité, mais dans-distribution). Si la survie s'effondre, la perception est
causalement porteuse (PERCEPTION_DEMANDED) ; sinon c'est un leurre pour CE champin (PERCEPTION_DECOY).
Contraste avec le between (champion vs réflexe) = rend visible in-world le faux-positif de S2-001.

N'importe PAS en modifiant s2_demand (benchmark pré-enregistré) : réutilise run_condition/WORLDS/
load_champion_genome. Ablation injectée via le seam batch_model_cls.

Usage : python tools/s2_demand_ablation.py   (env: S2ABL_SEED, S2ABL_K, S2ABL_AGENTS, S2ABL_TICKS,
S2ABL_WORLDS="soup,stoneage,...").
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaBatchModel
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS, load_champion_genome
from src.agents.baseline_models import ReflexBatchModel


def derange_rows(batch_obs, rng=None):
    """Permute les LIGNES de batch_obs entre agents. B>=2 : dérangement (aucun point fixe) -> chaque
    agent voit l'obs d'un PAIR (décorrélée de sa réalité, dans-distribution). B<2 : copie inchangée
    (near-death ; fuite négligeable et CONSERVATRICE). Ne mute jamais l'entrée. RNG = flux global
    np.random par défaut (seedé aux frontières par le Harness -> appariement préservé)."""
    B = batch_obs.shape[0]
    if B < 2:
        return batch_obs.copy()
    draw = (rng or np.random)
    perm = np.arange(B)
    while np.any(perm == np.arange(B)):        # rejet jusqu'à obtenir un dérangement
        perm = draw.permutation(B)
    return batch_obs[perm].copy()


class PerceptionAblatedMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception décorrélée : permute batch_obs avant le forward normal.
    Sous-classe MambaBatchModel -> réutilise entièrement le moteur/poids ; seule l'ENTRÉE change."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _median_survival(cond):
    """Survie médiane globale d'une condition run_condition (liste 'survival')."""
    s = cond.get("survival") or []
    return float(np.median(s)) if s else 0.0


def run_ablation_map(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=400):
    """Pour chaque monde : champion INTACT vs champion ABLATÉ (within) + réflexe (between). Renvoie
    {world: {within_ratio, between_ratio, verdict, n}}. n = K ères (unité d'appariement)."""
    worlds = worlds or list(WORLDS)
    champion = load_champion_genome()
    out = {}
    for w in worlds:
        wcls = WORLDS[w]
        intact = run_condition(wcls, None, champion, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        ablated = run_condition(wcls, PerceptionAblatedMamba, champion, seed, num_agents=num_agents,
                                max_ticks=max_ticks, n_eras=K)
        reflex = run_condition(wcls, ReflexBatchModel, None, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        # appariement par ère (même seed_at(seed, i)) : era_survival est la médiane par ère
        wv = ablation_verdict(intact["era_survival"], ablated["era_survival"])
        between_ratio = _median_survival(intact) / max(_median_survival(reflex), 1e-9)
        verdict = wv["verdict"].replace("X_", "PERCEPTION_")
        out[w] = {"within_ratio": wv["ratio"], "between_ratio": between_ratio,
                  "verdict": verdict, "n": wv["n"]}
    return out


def main():
    seed = int(os.environ.get("S2ABL_SEED", "2026"))
    K = int(os.environ.get("S2ABL_K", "12"))
    num_agents = int(os.environ.get("S2ABL_AGENTS", "20"))
    max_ticks = int(os.environ.get("S2ABL_TICKS", "400"))
    worlds_env = os.environ.get("S2ABL_WORLDS")
    worlds = worlds_env.split(",") if worlds_env else None

    m = run_ablation_map(worlds, seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
    print(f"\n=== S2-002 — ablation-perception within-subject in-world (seed={seed}, K={K}) ===")
    print(f"{'monde':12s} {'within':>8s} {'between':>8s}  verdict")
    for w, r in m.items():
        print(f"{w:12s} {r['within_ratio']:8.2f} {r['between_ratio']:8.2f}  {r['verdict']} (n={r['n']})")
    # lecture : within>>1 = perception causalement porteuse ; within~1 & between>>1 = between
    # FAUX-POSITIVE (survivant existe mais perception = leurre) -> le finding S2-001 rendu in-world.
    disagree = [w for w, r in m.items() if r["between_ratio"] >= 1.5 and r["within_ratio"] <= 1.3]
    print(f"\nDésaccords between/within (between crie demande, within dit leurre) : {disagree or 'aucun'}")
    print("-> Rédiger EDR-S2-002 à partir de cette carte.")
    return m


if __name__ == "__main__":
    main()
```

- [ ] **Step 4 : Lancer les tests d'ablation, vérifier le succès**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_perception_ablation.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5 : Écrire le smoke test (opt-in `slow`)**

```python
# tests/test_s2_ablation_smoke.py
import os
import pytest


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1",
                    reason="run in-world lourd : activer avec RUN_SLOW=1")
def test_ablation_map_smoke():
    from tools.s2_demand_ablation import run_ablation_map
    m = run_ablation_map(worlds=["stoneage"], seed=2026, K=2, num_agents=6, max_ticks=60)
    assert "stoneage" in m
    r = m["stoneage"]
    assert set(r) == {"within_ratio", "between_ratio", "verdict", "n"}
    assert r["within_ratio"] > 0.0
    assert r["verdict"] in {"PERCEPTION_DEMANDED", "PERCEPTION_DECOY", "INCONCLUSIVE"}
    assert r["n"] == 2
```

- [ ] **Step 6 : Lancer le smoke test**

Run: `RUN_SLOW=1 PYTHONIOENCODING=utf-8 python -m pytest tests/test_s2_ablation_smoke.py -v`
Expected: PASS (1 test). Si trop lent (>2 min), c'est acceptable — le test est opt-in ; noter le temps.

- [ ] **Step 7 : Commit (path-scopé)**

```bash
git add tools/s2_demand_ablation.py tests/test_perception_ablation.py tests/test_s2_ablation_smoke.py
git commit -m "feat(S2-002): bras d'ablation-perception within-subject in-world (5 mondes)

PerceptionAblatedMamba permute batch_obs entre agents (dérangement, world-agnostic) via le seam
batch_model_cls, sans modifier s2_demand. Carte per-monde within vs between = faux-positif rendu in-world.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3 : Exécuter le run + records (REF, EDR-S2-002) + note méthodes

**Files:**
- Create: `docs/REF/REF-DEMAND-MARKER.md`
- Create: `docs/EDR/S2-002_Perception_Ablation_InWorld_Demand_Marker.md`
- Create: `docs/roadmap/DEMAND_MARKER_METHOD.md`
- Modify (mémoire projet, hors repo) : `within-subject-demand-marker.md` + `MEMORY.md`

**Interfaces:**
- Consumes: `run_ablation_map` (Task 2) pour produire la carte per-monde chiffrée.

- [ ] **Step 1 : Lancer le run in-world complet (peut être long — arrière-plan possible)**

Run: `S2ABL_K=12 PYTHONIOENCODING=utf-8 python tools/s2_demand_ablation.py | tee results/s2_002_ablation_map.txt`
Expected: tableau per-monde (within/between/verdict) sur les 5 mondes + ligne « Désaccords ». Si un
monde plante (dépendance monde spécifique), réduire à `S2ABL_WORLDS="soup,stoneage,agricultural"` et
noter l'exclusion honnêtement dans l'EDR. **Copier la carte imprimée** pour l'étape 3.

> Note runtime : 5 mondes × 3 conditions × 12 ères. Si > ~10 min, lancer en arrière-plan et récupérer
> la sortie. `results/` est gitignored : la carte n'est PAS committée, elle va dans l'EDR.

- [ ] **Step 2 : Écrire le record REF adoptable**

```markdown
# docs/REF/REF-DEMAND-MARKER.md
---
id: REF-DEMAND-MARKER
type: REF
title: "Témoin causal de demande — ablation within-subject de la capacité X"
status: active
adopt_for: [S2-001, LANG-006, G1-001, MEM-001, S2-002]
---

## Énoncé
Le témoin CAUSAL de « la capacité X est-elle exigée / paie-t-elle » = **ablation WITHIN-subject de X**
sur le MÊME sujet (intact vs X neutralisé), PAS « un agent équipé de X réussit » (between-subject, qui
FAUX-POSITIVE : un survivant compétent peut exister dans un monde qui n'exige pas X).

## Prédiction validée (vérité-terrain)
- BETWEEN faux-positive sur les mondes TRIVIAUX (un survivant existe sans que X soit porteur).
- WITHIN tranche juste : effondrement SSI X est causalement porteur.
- Corroborant : le poids |W| que la politique met sur X → 0.000 exact quand X ne paie pas.

## Implémentation de référence
`tools/demand_marker.py::ablation_verdict` (ratio d'effondrement + garde-fou n<12 + verdict).

## Modalités couvertes
| Modalité | Record | Ablation | Résultat |
|---|---|---|---|
| perception (proxy) | S2-001 | obs décorrélée | within tranche, between faux-positif |
| perception (in-world) | S2-002 | permutation batch_obs, 5 mondes | (voir EDR-S2-002) |
| communication | LANG-006 | canal coupé | MI 1.04 vs 0.000 |
| généralisation | G1-001 | θ ablaté | Δ0.83 causal |
| mémoire | MEM-001 | mémoire remise à 0 | effondre 6-8× |
```

- [ ] **Step 3 : Écrire l'EDR-S2-002 depuis la carte du run**

Remplir la table `RESULTATS` avec les chiffres RÉELS de l'étape 1 (ne pas inventer). Verdict global
selon §4 du spec : `INWORLD_DEMAND_CAUSAL` si ≥1 monde `PERCEPTION_DEMANDED` ; `INWORLD_PERCEPTION_DECOY`
si tous plats ; `MIXED` sinon.

```markdown
# docs/EDR/S2-002_Perception_Ablation_InWorld_Demand_Marker.md
---
id: EDR-S2-002
type: EDR
title: "Ablation-perception within-subject in-world : le demand-marker franchit le pont proxy→in-world"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Le témoin within-subject (S2-001, proxy) tient-il sur le VRAI monde ? La perception du champion HoF
est-elle causalement porteuse de sa survie, ou un survivant compétent masque-t-il un leurre (le
faux-positif between du benchmark s2_demand) ?

## Méthode
`tools/s2_demand_ablation.py` : champion HoF INTACT vs perception PERMUTÉE (PerceptionAblatedMamba,
dérangement de batch_obs, within-subject) sur les 5 mondes ; contraste avec between (champion vs réflexe).
n = 12 ères appariées. Garde-fou n<12 (demand_marker).

## Résultats
<!-- COLLER la carte per-monde du run (within / between / verdict) ici -->
| monde | within | between | verdict |
|---|---|---|---|
| ... | ... | ... | ... |

Désaccords between/within : <...>

## Verdict
<INWORLD_DEMAND_CAUSAL | INWORLD_PERCEPTION_DECOY | MIXED> — <1 phrase d'interprétation honnête>.

## Portée & limites
Ablation du flux sensori-égocentrique COMPLET (perception + proprioception), pas la perception isolée
(affinage per-monde = follow-up). Corroborant |W| non disponible sur champion HoF. Cohérent /
contraste avec le fil « in-world NEUTRE » selon l'issue.
```

- [ ] **Step 4 : Écrire la note méthodes**

```markdown
# docs/roadmap/DEMAND_MARKER_METHOD.md
# Note méthodes — le témoin causal de demande (ablation within-subject)

## Problème
« La capacité X est-elle exigée par le monde ? » — le réflexe est de montrer qu'un agent équipé de X
réussit (BETWEEN-subject). C'est un faux-positif : un survivant compétent peut exister dans un monde qui
n'exige pas X (il survit par un autre canal).

## Instrument
Ablater X WITHIN-subject sur le MÊME sujet et mesurer l'effondrement de fitness. `ablation_verdict`
(tools/demand_marker.py) : ratio = median(intact)/median(ablated), garde-fou n<12, verdict
X_DEMANDED / X_DECOY / INCONCLUSIVE. Corroborant : |W|→0 quand X ne paie pas.

## Protocole générique (pont proxy→in-world)
Pour toute capacité dé-risquée en proxy, ajouter un BRAS D'ABLATION-X within-subject comme KPI causal
(pas la survie brute). Le between reste utile mais ne doit jamais servir de verdict de demande seul.

## Couverture (5 applications)
perception proxy (S2-001) → perception in-world (S2-002) ; communication (LANG-006) ; généralisation
(G1-001) ; mémoire (MEM-001). Chaque fois : within tranche là où between faux-positive.

## Limites
Ablation de flux complet vs canal isolé ; corroborant |W| indisponible sur poids non exposés (HoF).
```

- [ ] **Step 5 : Vérifier le graphe de records**

Run: `PYTHONIOENCODING=utf-8 python tools/consolidate_records.py`
Expected: `problemes=0` (le compte de records augmente ; REF-DEMAND-MARKER + EDR-S2-002 apparaissent).

Run: `PYTHONIOENCODING=utf-8 python tools/check_record_links.py --report`
Expected: 0 NOUVEL orphelin (EDR-S2-002 raccordé via `gate: G0` + `tests`; REF adoptée). Les 19
orphelins légataires connus restent (hors périmètre). Si un des 4 EDR listés dans `adopt_for` était
orphelin, il perd ce statut (bonus).

- [ ] **Step 6 : Mettre à jour la mémoire projet**

Éditer `C:\Users\robla\.claude\projects\c--Users-robla-VScode-Project-AGAGI\memory\within-subject-demand-marker.md` :
ajouter S2-002 comme 1re application IN-WORLD du témoin (5e application, 1er passage du pont proxy→in-world),
avec le verdict réel. Ajouter REF-DEMAND-MARKER comme implémentation de référence. Répercuter une ligne
dans `MEMORY.md` si un nouveau topic est créé (ici : mise à jour, pas de nouveau fichier).

- [ ] **Step 7 : Commit (path-scopé)**

```bash
git add docs/REF/REF-DEMAND-MARKER.md docs/EDR/S2-002_Perception_Ablation_InWorld_Demand_Marker.md docs/roadmap/DEMAND_MARKER_METHOD.md
git commit -m "docs(S2-002): REF-DEMAND-MARKER + EDR-S2-002 (carte per-monde) + note méthodes

Formalise le témoin en instrument de 1re classe (REF adoptable par 5 records) et grave le verdict
in-world de l'ablation-perception. Le demand-marker franchit le pont proxy→in-world (G0).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(La mémoire projet est hors repo — pas de `git add`.)

---

## Self-Review (auteur du plan)

**Couverture du spec :**
- §2 mécanisme A (permutation ligne) → Task 2 `derange_rows`/`PerceptionAblatedMamba`. ✅
- §3 push standalone important s2_demand → Task 2 `run_ablation_map`. ✅
- §4 interprétation verdicts → Task 2 `main` (désaccords) + Task 3 EDR §Résultats. ✅
- §5.1 module → Task 1 ; §5.2 REF → Task 3 Step 2 ; §5.3 note méthodes → Task 3 Step 4. ✅
- §6 tests (ablation/marker/smoke) → Task 1 & 2 tests. ✅
- §7 ancrage records → Task 3 Steps 2-5. ✅
- §8 3 commits path-scopés → Task 1/2/3 Step final. ✅
- §9 risques (effondrement partout / plat partout / runtime / monde qui plante) → Task 3 Step 1 (fallback worlds) + EDR verdict honnête. ✅

**Scan placeholders :** aucun TBD/TODO dans le CODE. L'EDR §Résultats est légitimement rempli DEPUIS le
run (Task 3 Step 1→3) — donnée d'expérience, pas un placeholder de plan.

**Cohérence des types :** `ablation_verdict(...)` renvoie `{ratio, n, collapse, decoy, corroborant,
verdict}` — mêmes clés en Task 1 (def/tests) et Task 2 (`wv["ratio"]`, `wv["verdict"]`, `wv["n"]`).
`run_ablation_map` renvoie `{world: {within_ratio, between_ratio, verdict, n}}` — mêmes clés dans `main`,
le smoke test, et l'EDR. `derange_rows`/`PerceptionAblatedMamba.forward` signatures alignées Task 2.
