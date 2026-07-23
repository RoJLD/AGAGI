# SP-3 — Prerequisite-Recovery Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calibrer le demand-marker (`ablation_verdict`) sur un DAG de prérequis IMPOSÉ, en utilisant `withmarbleapp/os-taxonomy` comme clé de réponse externe, et graver le verdict go/no-go.

**Architecture:** Approche A1 (score imposé, analytique, pur numpy). Trois unités : un adaptateur qui lit un sous-graphe au format os-taxonomy → structure d'arêtes ; un monde-jouet à gate imposé dans `ground_truth_worlds.py` où l'acquisition d'un topic B est gatée par construction sur ses prérequis (avec transfert d'ancêtre pour fabriquer la corrélation) ; une sonde de récupération qui, par ablation within-subject de chaque prérequis candidat, appelle `ablation_verdict` et agrège en précision/rappel. Le tout branché sur le cliquet de calibration et le pré-vol.

**Tech Stack:** Python 3, numpy, pytest. Réutilise `tools/demand_marker.py::ablation_verdict` et `tools/experiment_preflight.py`. Aucune dépendance nouvelle, aucun torch, aucun KuzuDB.

## Global Constraints

- **Unité de réplication = seed.** Chaque verdict d'arête agrège ≥ **12** seeds (le `n_floor=12` de `ablation_verdict` : sous 12, aucun verdict, ni positif ni nul).
- **Déterminisme obligatoire** : toute stochasticité via `np.random.RandomState(seed)`. Jamais `Date.now`/`random` non seedé (contention + non-repro, cf. `CLAUDE.md`).
- **Métrique VIVANTE** : le score d'acquisition médian de tout bras interprété doit être STRICTEMENT entre `floor=15.0` et `ceiling=200.0` (sinon plancher/plafond → verdict fabriqué, piège WARM-002 / EDR-AUDIT-001). `floor=`/`ceiling=` sont passés à `ablation_verdict`.
- **Constantes du monde-jouet (verbatim, ne pas dériver)** : `income=0.1`, `hard_w=0.4`, `soft_w=0.2`, `T=200`, `transfer=0.9`, compétence `own` par défaut `1.0`, `own` des nœuds à ancêtre `0.1`.
- **Fixture = SOURCE UNIQUE dans `tools/`** : `fixture_subgraph()` vit dans `tools/os_taxonomy_adapter.py`, `fixture_world()` dans `tools/ground_truth_worlds.py`. Tests et CLI les IMPORTENT ; ne JAMAIS redéclarer le dict `world` ni le sous-graphe ailleurs (pas de duplication verbatim).
- **Nommage qui DOIT tripper le cliquet** : `run_prerequisite_recovery_probe` (motif `run_\w*probe`) et `prerequisite_recovery_verdict` (motif `\w*verdict\w*`). Sinon ils entrent non-calibrés (cf. `run_linear_sanity`). Les helpers (`effective_competence`, `acquisition_prob`, `acquisition_scores`, `fixture_world`, `fixture_subgraph`) NE doivent PAS matcher un motif d'instrument.
- **Pas de bail `kuzu`** : pur numpy, aucune simulation de monde → aucune ressource exclusive.
- **Licence** : le sous-graphe vendu crédite os-taxonomy (ODbL 1.0 + CC BY-SA 4.0) dans un `NOTICE`. La fixture v0 est **synthétique au FORMAT os-taxonomy** (ids lisibles, pas de copie de la base Marble — hygiène anti-fabrication). Vendre un vrai extrait Marble = tâche de suivi hors v0, avec vérification humaine des lignes.
- **Commits** : path-scoped (arbre partagé entre sessions parallèles, fichiers non-SP3 modifiés en cours). `git add <chemins SP-3 explicites>` UNIQUEMENT — JAMAIS `git add -A` ni `git add .`. Branche courante `feat/d1-prod-pairing`.

## File Structure

- `data/os_taxonomy/dependencies.json` — sous-graphe au format os-taxonomy (arêtes `topicId/prerequisiteId/strength/reason`). **Fixture synthétique.**
- `data/os_taxonomy/topics.json` — libellés des topics (format os-taxonomy).
- `data/os_taxonomy/NOTICE` — attribution de licence.
- `tools/os_taxonomy_adapter.py` — lecture JSON → structure de sous-graphe + `fixture_subgraph()`. Responsabilité unique : parsing/regroupement, aucun calcul scientifique.
- `tools/ground_truth_worlds.py` (MODIFIÉ) — ajout du monde-jouet à gate imposé (`effective_competence`, `acquisition_prob`, `acquisition_scores`, `fixture_world`), à côté de `partial_oracle`.
- `tools/prerequisite_recovery_probe.py` — la sonde (`run_prerequisite_recovery_probe`, `prerequisite_recovery_verdict`) + un `main()` CLI branché au pré-vol.
- `tests/test_prerequisite_recovery.py` — tests unitaires de l'adaptateur, du monde et de la sonde.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — entrée `CALIBRATED` + les cas de calibration (3 formes canoniques + spécificité corrélée + contraste de confond).
- `docs/EDR/CALIB-SP3_Prerequisite_Recovery_Calibration.md` — le record du verdict go/no-go.

---

### Task 1: Adaptateur os-taxonomy → sous-graphe (+ fixture source unique)

**Files:**
- Create: `data/os_taxonomy/dependencies.json`
- Create: `data/os_taxonomy/topics.json`
- Create: `data/os_taxonomy/NOTICE`
- Create: `tools/os_taxonomy_adapter.py`
- Test: `tests/test_prerequisite_recovery.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `load_dependencies(path) -> list[dict]` : lignes brutes `{"topicId","prerequisiteId","strength","reason"}`.
  - `subgraph_for(rows, target_id) -> dict` : `{"target": str, "hard": list[str], "soft": list[str], "non_edges": list[str]}` où `non_edges` = tout identifiant présent dans `rows` qui n'est NI le target NI un prérequis **transitif** (fermeture) du target. ⚠️ Transitif, pas direct : un ancêtre d'un prérequis (ex. Z, ancêtre du dur Ah) est un VRAI prérequis de B et NE doit PAS être une non-arête (sinon la sonde le récupère à juste titre et casse la précision attendue).
  - `fixture_subgraph(target_id="B_matter_movement") -> dict` : le sous-graphe de la fixture SP-3 (SOURCE UNIQUE — lit `data/os_taxonomy/dependencies.json`).

- [ ] **Step 1: Créer la fixture de dépendances (format os-taxonomy)**

Create `data/os_taxonomy/dependencies.json`:

```json
[
  {"topicId": "B_matter_movement", "prerequisiteId": "Ah_food_chains", "strength": "hard", "reason": "Fixture synthétique : prérequis DUR de B."},
  {"topicId": "B_matter_movement", "prerequisiteId": "As_biodiversity", "strength": "soft", "reason": "Fixture synthétique : prérequis MOU de B."},
  {"topicId": "Ah_food_chains", "prerequisiteId": "Z_producers", "strength": "hard", "reason": "Fixture synthétique : ancêtre partagé (source de corrélation)."},
  {"topicId": "Aprime_rainforest_web", "prerequisiteId": "Z_producers", "strength": "hard", "reason": "Fixture synthétique : NON-prérequis de B, corrélé à Ah via l'ancêtre Z."}
]
```

- [ ] **Step 2: Créer les libellés et le NOTICE**

Create `data/os_taxonomy/topics.json`:

```json
[
  {"id": "B_matter_movement", "title": "Matter movement in ecosystems"},
  {"id": "Ah_food_chains", "title": "Food chains with producers and predators"},
  {"id": "As_biodiversity", "title": "Biodiversity and ecosystems"},
  {"id": "Aprime_rainforest_web", "title": "Rainforest food webs"},
  {"id": "Z_producers", "title": "Producers (plants)"}
]
```

Create `data/os_taxonomy/NOTICE`:

```text
Format et méthodologie inspirés de withmarbleapp/os-taxonomy (Marble Skill Taxonomy),
double licence ODbL 1.0 (base) + CC BY-SA 4.0 (contenu).

Les fichiers de ce répertoire sont une FIXTURE SYNTHÉTIQUE au format os-taxonomy, destinée
à la calibration d'instrument (SP-3). Ce ne sont PAS une copie de la base de données Marble.
Vendre un extrait réel exige une vérification humaine des lignes source.
```

- [ ] **Step 3: Écrire les tests de l'adaptateur (qui échouent)**

Create `tests/test_prerequisite_recovery.py`:

```python
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPS = os.path.join(_ROOT, "data", "os_taxonomy", "dependencies.json")


def test_load_dependencies_reads_os_taxonomy_rows():
    from tools.os_taxonomy_adapter import load_dependencies
    rows = load_dependencies(_DEPS)
    assert isinstance(rows, list) and len(rows) == 4
    r = rows[0]
    assert set(r) >= {"topicId", "prerequisiteId", "strength", "reason"}
    assert {row["strength"] for row in rows} == {"hard", "soft"}


def test_subgraph_for_groups_by_strength_and_finds_non_edges():
    from tools.os_taxonomy_adapter import load_dependencies, subgraph_for
    sg = subgraph_for(load_dependencies(_DEPS), "B_matter_movement")
    assert sg["target"] == "B_matter_movement"
    assert sg["hard"] == ["Ah_food_chains"]
    assert sg["soft"] == ["As_biodiversity"]
    # Aprime n'est PAS un prérequis de B -> seul non_edge (candidat de spécificité, corrélé via Z)
    assert sg["non_edges"] == ["Aprime_rainforest_web"]
    # Z est un prérequis TRANSITIF de B (via Ah) -> EXCLU des non_edges
    assert "Z_producers" not in sg["non_edges"]
    assert "Ah_food_chains" not in sg["non_edges"]


def test_fixture_subgraph_is_the_single_source():
    from tools.os_taxonomy_adapter import fixture_subgraph
    sg = fixture_subgraph()
    assert sg["target"] == "B_matter_movement"
    assert sg["hard"] == ["Ah_food_chains"] and sg["soft"] == ["As_biodiversity"]
```

- [ ] **Step 4: Lancer les tests, vérifier l'échec**

Run: `python -m pytest tests/test_prerequisite_recovery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.os_taxonomy_adapter'`.

- [ ] **Step 5: Implémenter l'adaptateur**

Create `tools/os_taxonomy_adapter.py`:

```python
"""Adaptateur : un sous-graphe au format os-taxonomy (arêtes topicId/prerequisiteId/strength/reason)
-> structure regroupée pour la sonde de récupération de prérequis (SP-3).

Responsabilité UNIQUE : parsing et regroupement. Aucune affirmation scientifique ici (les noms ne
matchent volontairement AUCUN motif d'instrument du cliquet de calibration)."""
import json
import os

_FIXTURE_DEPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "os_taxonomy", "dependencies.json")


def load_dependencies(path):
    """Lit un fichier de dépendances au format os-taxonomy. Renvoie la liste brute des lignes."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def subgraph_for(rows, target_id):
    """Regroupe les prérequis DIRECTS de `target_id` par force, et liste les non-prérequis présents.

    non_edges = tout identifiant du graphe qui n'est NI le target NI un prérequis TRANSITIF (fermeture)
    du target : ce sont les candidats du test de spécificité (dont le non-prérequis CORRÉLÉ). ⚠️ On
    exclut la FERMETURE, pas seulement les prérequis directs : un ancêtre d'un prérequis (ex. Z, ancêtre
    du dur Ah) reste un VRAI prérequis de B — l'ablater effondre B à juste titre, donc ce n'est pas une
    non-arête."""
    hard = [r["prerequisiteId"] for r in rows
            if r["topicId"] == target_id and r["strength"] == "hard"]
    soft = [r["prerequisiteId"] for r in rows
            if r["topicId"] == target_id and r["strength"] == "soft"]
    prereqs_of = {}
    for r in rows:
        prereqs_of.setdefault(r["topicId"], []).append(r["prerequisiteId"])
    transitive, stack = set(), list(hard) + list(soft)
    while stack:                                    # fermeture transitive des prérequis du target
        node = stack.pop()
        if node in transitive:
            continue
        transitive.add(node)
        stack.extend(prereqs_of.get(node, []))
    ids = set()
    for r in rows:
        ids.add(r["topicId"])
        ids.add(r["prerequisiteId"])
    non_edges = sorted(ids - transitive - {target_id})
    return {"target": target_id, "hard": hard, "soft": soft, "non_edges": non_edges}


def fixture_subgraph(target_id="B_matter_movement"):
    """Le sous-graphe de la fixture SP-3 — SOURCE UNIQUE, importée par les tests et le CLI."""
    return subgraph_for(load_dependencies(_FIXTURE_DEPS), target_id)
```

- [ ] **Step 6: Lancer les tests, vérifier le succès**

Run: `python -m pytest tests/test_prerequisite_recovery.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add data/os_taxonomy/ tools/os_taxonomy_adapter.py tests/test_prerequisite_recovery.py
git commit -m "feat(SP-3): adaptateur os-taxonomy -> sous-graphe + fixture synthétique"
```

---

### Task 2: Monde-jouet à gate imposé (+ fixture_world source unique)

**Files:**
- Modify: `tools/ground_truth_worlds.py` (ajout en fin de fichier)
- Test: `tests/test_prerequisite_recovery.py` (ajout)

**Interfaces:**
- Consumes: `fixture_subgraph()` (Task 1) — clés `hard`, `soft`, `non_edges`.
- Produces (le paramètre `world` est un dict) :
  - `fixture_world() -> dict` : `{"income": 0.1, "hard_w": 0.4, "soft_w": 0.2, "own": {...}, "ancestor": {...}, "transfer": {...}}` — SOURCE UNIQUE de l'overlay du monde-jouet.
  - `effective_competence(node_id, world, zeroed=()) -> float` : compétence effective, 1 niveau de transfert d'ancêtre, `node_id in zeroed` force `0.0`.
  - `acquisition_prob(subgraph, world, zeroed=()) -> float` : `income + hard_w*mean(eff(hard)) + soft_w*mean(eff(soft))`, borné `[0,1]`.
  - `acquisition_scores(subgraph, world, seeds, zeroed=(), T=200) -> list[int]` : un `Binomial(T, p)` par seed.

- [ ] **Step 1: Écrire les tests du monde (qui échouent)**

Add to `tests/test_prerequisite_recovery.py`:

```python
def test_effective_competence_transfers_from_ancestor():
    from tools.ground_truth_worlds import effective_competence, fixture_world
    w = fixture_world()
    # Ah : own 0.1 + transfer 0.9 * eff(Z=1.0) = 1.0 (borné)
    assert effective_competence("Ah_food_chains", w) == 1.0
    # zeroer Z fait chuter Ah (perd le transfert) -> 0.1
    assert abs(effective_competence("Ah_food_chains", w, zeroed={"Z_producers"}) - 0.1) < 1e-9
    # zeroer Ah lui-même -> 0.0 (ablation chirurgicale)
    assert effective_competence("Ah_food_chains", w, zeroed={"Ah_food_chains"}) == 0.0


def test_acquisition_prob_matches_the_imposed_gate():
    from tools.ground_truth_worlds import acquisition_prob, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    w, sg = fixture_world(), fixture_subgraph()
    assert abs(acquisition_prob(sg, w) - 0.7) < 1e-9                                  # intact
    assert abs(acquisition_prob(sg, w, zeroed={"Ah_food_chains"}) - 0.3) < 1e-9       # ablate dur
    assert abs(acquisition_prob(sg, w, zeroed={"As_biodiversity"}) - 0.5) < 1e-9      # ablate mou
    assert abs(acquisition_prob(sg, w, zeroed={"Aprime_rainforest_web"}) - 0.7) < 1e-9  # non-arête = inerte


def test_acquisition_scores_are_alive_and_seed_deterministic():
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    w, sg = fixture_world(), fixture_subgraph()
    seeds = list(range(12))
    s = acquisition_scores(sg, w, seeds)
    assert len(s) == 12
    assert 15.0 < sorted(s)[len(s) // 2] < 200.0, "métrique doit être VIVANTE"
    assert acquisition_scores(sg, w, seeds) == s, "doit être déterministe par seed"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k "competence or acquisition" -v`
Expected: FAIL — `ImportError: cannot import name 'effective_competence'`.

- [ ] **Step 3: Implémenter le monde-jouet**

Append to `tools/ground_truth_worlds.py`:

```python
# ------------------------------------------------------------------------------------------------
# SP-3 — MONDE-JOUET À GATE IMPOSÉ (étalon pour la sonde de récupération de prérequis).
# Pur numpy, aucune sous-classe Biosphere3D — même esprit que `partial_oracle` : une réponse CONNUE
# PAR CONSTRUCTION. L'acquisition d'un topic B est gatée sur ses prérequis ; un transfert d'ancêtre
# fabrique la CORRÉLATION entre un vrai prérequis et un non-prérequis, pour tester la spécificité.
# ------------------------------------------------------------------------------------------------

def fixture_world():
    """Overlay du monde-jouet SP-3 (compétences/ancêtres imposés) — SOURCE UNIQUE, importée par les
    tests, le cliquet de calibration et le CLI. Les compétences sont des paramètres IMPOSÉS, distincts
    des données os-taxonomy (qui ne portent que la structure d'arêtes)."""
    return {
        "income": 0.1, "hard_w": 0.4, "soft_w": 0.2,
        "own": {"B_matter_movement": 1.0, "Ah_food_chains": 0.1, "As_biodiversity": 1.0,
                "Aprime_rainforest_web": 0.1, "Z_producers": 1.0},
        "ancestor": {"Ah_food_chains": "Z_producers", "Aprime_rainforest_web": "Z_producers"},
        "transfer": {"Ah_food_chains": 0.9, "Aprime_rainforest_web": 0.9},
    }


def effective_competence(node_id, world, zeroed=()):
    """Compétence effective d'un nœud, avec UN niveau de transfert d'ancêtre.

    `zeroed` : ensemble de nœuds ABLATÉS chirurgicalement -> compétence forcée à 0.0. C'est le canal
    de l'ablation within-subject : retirer la compétence à un nœud, sans toucher aux autres."""
    if node_id in zeroed:
        return 0.0
    own = float(world["own"].get(node_id, 1.0))
    anc = world.get("ancestor", {}).get(node_id)
    if anc is not None:
        own += float(world.get("transfer", {}).get(node_id, 0.0)) * effective_competence(anc, world, zeroed)
    return max(0.0, min(1.0, own))


def acquisition_prob(subgraph, world, zeroed=()):
    """Probabilité par pas d'acquérir le topic cible, GATÉE par construction sur ses prérequis :
    income (revenu plat obs-indépendant, garde la métrique VIVANTE) + hard_w*moyenne(eff des prérequis
    DURS) + soft_w*moyenne(eff des prérequis MOUS). Bornée [0,1]."""
    def _mean(ids):
        return sum(effective_competence(i, world, zeroed) for i in ids) / len(ids) if ids else 0.0
    p = (float(world["income"])
         + float(world["hard_w"]) * _mean(subgraph["hard"])
         + float(world["soft_w"]) * _mean(subgraph["soft"]))
    return max(0.0, min(1.0, p))


def acquisition_scores(subgraph, world, seeds, zeroed=(), T=200):
    """Score d'acquisition par seed = Binomial(T, p) — T pas, chacun réussit avec proba p. La variance
    inter-seeds rend la métrique NON dégénérée ; `p` est fixe pour un `zeroed` donné (déterministe)."""
    import numpy as np
    p = acquisition_prob(subgraph, world, zeroed)
    return [int(np.random.RandomState(int(s)).binomial(int(T), p)) for s in seeds]
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k "competence or acquisition" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/ground_truth_worlds.py tests/test_prerequisite_recovery.py
git commit -m "feat(SP-3): monde-jouet a gate impose (acquisition gatee + transfert d'ancetre)"
```

---

### Task 3: Sonde de récupération + verdict de graphe

**Files:**
- Create: `tools/prerequisite_recovery_probe.py`
- Test: `tests/test_prerequisite_recovery.py` (ajout)

**Interfaces:**
- Consumes: `acquisition_scores(...)`, `fixture_world()` (Task 2), `fixture_subgraph()` (Task 1), `ablation_verdict(...)` (`tools/demand_marker.py`).
- Produces:
  - `run_prerequisite_recovery_probe(subgraph, world, seeds, T=200, floor=15.0, ceiling=200.0) -> dict` :
    `{"edges": list[dict], "recovery": dict}`. Chaque élément de `edges` :
    `{"prereq": str, "strength": "hard"|"soft"|None, "ratio": float, "verdict": str}`.
  - `prerequisite_recovery_verdict(edges, imposed_hard) -> dict` :
    `{"precision": float, "recall": float, "recovered": list[str], "imposed_hard": list[str]}`.

- [ ] **Step 1: Écrire les tests de la sonde (qui échouent)**

Add to `tests/test_prerequisite_recovery.py`:

```python
def test_probe_recovers_hard_and_noops_on_correlated_non_edge():
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Ah_food_chains"]["verdict"] == "X_DEMANDED"           # prérequis dur récupéré
    assert by["Aprime_rainforest_web"]["verdict"] == "X_DECOY"       # non-arête corrélée = inerte
    # monotonie : dur > mou > non-arête (~1)
    assert by["Ah_food_chains"]["ratio"] > by["As_biodiversity"]["ratio"] > by["Aprime_rainforest_web"]["ratio"]
    assert abs(by["Aprime_rainforest_web"]["ratio"] - 1.0) < 1e-9


def test_graph_recovery_is_perfect_on_the_fixture():
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    rec = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))["recovery"]
    assert rec["precision"] == 1.0 and rec["recall"] == 1.0
    assert rec["recovered"] == ["Ah_food_chains"]
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k "probe or graph_recovery" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.prerequisite_recovery_probe'`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/prerequisite_recovery_probe.py`:

```python
"""SP-3 — Le demand-marker récupère-t-il un DAG de prérequis IMPOSÉ (os-taxonomy = clé de réponse) ?

Pour chaque prérequis candidat d'un topic cible, on ABLATE chirurgicalement sa compétence (bras
within-subject) et on lit l'effondrement du score d'acquisition via `ablation_verdict`. On agrège en
précision/rappel des arêtes récupérées vs imposées. Pur numpy, aucun bail.

Calibré sur vérité-terrain dans `tests/sandbox/test_instrument_calibration.py` (le nom `*_probe` /
`*verdict*` trippe volontairement le cliquet). Usage : python tools/prerequisite_recovery_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.demand_marker import ablation_verdict
from tools.ground_truth_worlds import acquisition_scores, fixture_world
from tools.os_taxonomy_adapter import fixture_subgraph


def run_prerequisite_recovery_probe(subgraph, world, seeds, T=200, floor=15.0, ceiling=200.0):
    """Récupère les prérequis d'un topic par ablation within-subject. Renvoie les verdicts par arête
    candidate + le recouvrement de graphe. Le bras intact est calculé UNE fois (partagé)."""
    intact = acquisition_scores(subgraph, world, seeds, zeroed=(), T=T)
    strength = {p: "hard" for p in subgraph["hard"]}
    strength.update({p: "soft" for p in subgraph["soft"]})
    candidates = list(subgraph["hard"]) + list(subgraph["soft"]) + list(subgraph["non_edges"])

    edges = []
    for prereq in candidates:
        ablated = acquisition_scores(subgraph, world, seeds, zeroed={prereq}, T=T)
        # intervention_verified=True : zeroer la compétence du nœud PERTURBE bien l'entrée (même si,
        # pour une non-arête, la cible ne la lit pas -> bras identiques, X_DECOY légitime).
        v = ablation_verdict(intact, ablated, intervention_verified=True, floor=floor, ceiling=ceiling)
        edges.append({"prereq": prereq, "strength": strength.get(prereq),
                      "ratio": v["ratio"], "verdict": v["verdict"]})

    return {"edges": edges, "recovery": prerequisite_recovery_verdict(edges, subgraph["hard"])}


def prerequisite_recovery_verdict(edges, imposed_hard):
    """Recouvrement de graphe : une arête est RÉCUPÉRÉE si son verdict est X_DEMANDED. Précision/rappel
    contre les prérequis DURS imposés (les mous ne sont pas une cible de récupération, cf. spec §7)."""
    recovered = sorted(e["prereq"] for e in edges if e["verdict"] == "X_DEMANDED")
    imposed = sorted(set(imposed_hard))
    tp = len(set(recovered) & set(imposed))
    precision = tp / len(recovered) if recovered else 1.0
    recall = tp / len(imposed) if imposed else 1.0
    return {"precision": precision, "recall": recall, "recovered": recovered, "imposed_hard": imposed}
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k "probe or graph_recovery" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/prerequisite_recovery_probe.py tests/test_prerequisite_recovery.py
git commit -m "feat(SP-3): sonde de recuperation de prerequis + verdict de graphe"
```

---

### Task 4: Cas de calibration + entrée du cliquet (le livrable central)

**Files:**
- Modify: `tests/sandbox/test_instrument_calibration.py` (ajout du dict `CALIBRATED` + cas)

**Interfaces:**
- Consumes: `run_prerequisite_recovery_probe`, `prerequisite_recovery_verdict` (Task 3) ; `acquisition_scores`, `fixture_world` (Task 2) ; `fixture_subgraph` (Task 1) ; `ablation_verdict`.
- Produces: deux nouvelles clés dans `CALIBRATED`, chacune avec ses cas. Aucune nouvelle API. **N'introduit AUCUN nouveau helper de fixture** — importe `fixture_world`/`fixture_subgraph` depuis `tools/`.

- [ ] **Step 1: Déclarer les instruments calibrés**

In `tests/sandbox/test_instrument_calibration.py`, add two entries to the `CALIBRATED` dict (inside the existing `{...}`):

```python
    # SP-3 : récupération d'un DAG de prérequis IMPOSÉ (os-taxonomy = clé de réponse). Contrôle positif
    # (prérequis DUR récupéré), SPÉCIFICITÉ sous confond corrélé (no-op sur non-arête même corrélée),
    # monotonie (dur > mou > non-arête), + contraste : une ablation par l'ANCÊTRE faux-positive.
    "run_prerequisite_recovery_probe": ["*"],
    "prerequisite_recovery_verdict": ["*"],
```

- [ ] **Step 2: Écrire les cas de calibration (qui échouent d'abord si CALIBRATED sans cas)**

Append to `tests/sandbox/test_instrument_calibration.py`:

```python
# --- SP-3 : run_prerequisite_recovery_probe / prerequisite_recovery_verdict --------------------------
# Étalon = un DAG de prérequis IMPOSÉ au format os-taxonomy (fixture SOURCE UNIQUE dans tools/). La
# réponse est connue PAR CONSTRUCTION : Ah est prérequis DUR de B, As MOU, Aprime NON-prérequis mais
# corrélé à Ah via l'ancêtre Z. On importe la fixture depuis tools/ (jamais de redéclaration locale).


def test_sp3_positive_control_recovers_a_hard_prerequisite():
    """CONTRÔLE POSITIF (générateur A) : sur un prérequis DUR imposé, l'ablation within-subject DOIT
    effondrer l'acquisition. Mesuré par construction : p 0.7 -> 0.3 (ratio ~2.33)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Ah_food_chains"]["verdict"] == "X_DEMANDED", by


def test_sp3_specificity_holds_under_correlation():
    """LE TEST QUI DÉCIDE LE GO/NO-GO. Aprime est un NON-prérequis de B, mais corrélé à Ah (ancêtre Z
    partagé). L'ablation CHIRURGICALE d'Aprime ne touche pas ce que B lit -> no-op, X_DECOY. La
    corrélation seule ne fait PAS faux-positiver un marqueur qui ablate le bon canal."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Aprime_rainforest_web"]["verdict"] == "X_DECOY", by
    assert abs(by["Aprime_rainforest_web"]["ratio"] - 1.0) < 1e-9


def test_sp3_metric_is_alive_not_floored_or_ceilinged():
    """La spécificité ne vaut que sur une métrique VIVANTE (piège WARM-002). Le bras intact médian doit
    être strictement entre le plancher et le plafond déclarés."""
    import numpy as np
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    med = float(np.median(acquisition_scores(fixture_subgraph(), fixture_world(), list(range(12)))))
    assert 15.0 < med < 200.0, f"métrique NON vivante (médiane {med})"


def test_sp3_ratio_is_monotone_hard_soft_nonedge():
    """MONOTONIE (direction) : dur > mou > non-arête (~1). Le mou n'est PAS tenu d'être X_DEMANDED —
    il est évalué par le RATIO, pas la catégorie (spec §7)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    by = {e["prereq"]: e for e in
          run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), list(range(12)))["edges"]}
    assert (by["Ah_food_chains"]["ratio"] > by["As_biodiversity"]["ratio"]
            > by["Aprime_rainforest_web"]["ratio"]), by


def test_sp3_confounded_ablation_would_false_positive():
    """LE CONTRASTE QUI REND LE RÉSULTAT NON-VACUEUX. Si on ablate Aprime par son ANCÊTRE Z (au lieu du
    canal chirurgical), Z alimente aussi Ah -> B s'effondre -> on attribuerait à tort une arête Aprime->B.
    C'est le mode d'échec que SP-2 doit éviter : la spécificité n'est PAS automatique, elle exige d'ablater
    le bon canal."""
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    from tools.demand_marker import ablation_verdict
    sg, w = fixture_subgraph(), fixture_world()
    intact = acquisition_scores(sg, w, list(range(12)))
    confounded = acquisition_scores(sg, w, list(range(12)), zeroed={"Z_producers"})  # ablation par l'ancêtre
    v = ablation_verdict(intact, confounded, intervention_verified=True, floor=15.0, ceiling=200.0)
    assert v["verdict"] == "X_DEMANDED", (
        "l'ablation par l'ancêtre DOIT effondrer B (faux positif si attribué à Aprime) : "
        f"{v['ratio']:.2f}")


def test_sp3_graph_recovery_precision_recall():
    """Recouvrement de graphe : sur la fixture, précision=rappel=1.0 (seul Ah récupéré, imposé dur)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    rec = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), list(range(12)))["recovery"]
    assert rec["precision"] == 1.0 and rec["recall"] == 1.0 and rec["recovered"] == ["Ah_food_chains"]
```

- [ ] **Step 3: Lancer les cas de calibration**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k sp3 -v`
Expected: PASS (6 tests).

- [ ] **Step 4: Vérifier que le cliquet est VERT (aucun nouvel instrument non calibré)**

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.` (exit 0). Les deux `*_probe`/`*verdict` détectés apparaissent comme calibrés.

Si à la place tu vois `[NOUVEL INSTRUMENT NON CALIBRÉ]` : la clé dans `CALIBRATED` ne matche pas le nom détecté — vérifier l'orthographe exacte `run_prerequisite_recovery_probe` / `prerequisite_recovery_verdict`.

- [ ] **Step 5: Commit**

```bash
git add tests/sandbox/test_instrument_calibration.py
git commit -m "test(SP-3): calibration du demand-marker sur un DAG de prerequis impose (cliquet vert)"
```

---

### Task 5: Pré-vol, CLI go/no-go, et record

**Files:**
- Modify: `tools/prerequisite_recovery_probe.py` (ajout d'un `main()`)
- Create: `docs/EDR/CALIB-SP3_Prerequisite_Recovery_Calibration.md`
- Test: `tests/test_prerequisite_recovery.py` (ajout d'un test du pré-vol)

**Interfaces:**
- Consumes: tout ce qui précède + `tools/experiment_preflight.py` (`declare_design`, `assert_positive_control`, `assert_not_degenerate`, `assert_ablation_changes_something`, `assert_no_aliasing`).
- Produces: `main() -> int` (0 = PASS, 1 = FAIL) ; imprime le verdict go/no-go.

- [ ] **Step 1: Écrire le test du pré-vol (qui échoue)**

Add to `tests/test_prerequisite_recovery.py`:

```python
def test_preflight_passes_and_main_reports_go():
    from tools.prerequisite_recovery_probe import main
    assert main() == 0, "le pré-vol + le go/no-go doivent PASSER sur la fixture calibrée"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k preflight -v`
Expected: FAIL — `ImportError: cannot import name 'main'`.

- [ ] **Step 3: Implémenter le pré-vol + `main()`**

Append to `tools/prerequisite_recovery_probe.py`:

```python
def main():
    """Pré-vol + go/no-go SP-3. Renvoie 0 (PASS = la spécificité tient sous corrélation) ou 1 (FAIL)."""
    import numpy as np
    from tools.experiment_preflight import (declare_design, assert_positive_control,
                                            assert_not_degenerate, assert_ablation_changes_something,
                                            assert_no_aliasing, PreflightError)
    sg, world = fixture_subgraph(), fixture_world()
    seeds = list(range(12))

    design = declare_design(
        question="L'ablation within-subject récupère-t-elle un DAG de prérequis imposé, sans "
                 "faux-positiver sur un non-prérequis corrélé ?",
        replication_unit="seed", n_independent=len(seeds),
        links={"gate_impose->score": "measured", "ablation->effondrement": "measured"},
        cost_estimate="pur numpy, < 1 s")
    print(f"DESIGN: {design['replication_unit']} n={design['n_independent']}")

    intact = acquisition_scores(sg, world, seeds)
    hard = sg["hard"][0]
    ablated_hard = acquisition_scores(sg, world, seeds, zeroed={hard})
    try:
        assert_not_degenerate(intact, label="score intact")                    # métrique vivante
        assert_ablation_changes_something(intact, ablated_hard, label="ablation dure")  # pas tautologique
        assert_no_aliasing(np.asarray(intact), np.asarray(ablated_hard))       # pas d'état partagé (n/a en A1)
        assert_positive_control(
            lambda: np.median(intact) / max(np.median(ablated_hard), 1e-9),
            expect_better_than=1.5, label="récupération du prérequis dur")
    except PreflightError as e:
        print(f"PRÉ-VOL ÉCHOUE: {e}")
        return 1

    out = run_prerequisite_recovery_probe(sg, world, seeds)
    by = {e["prereq"]: e for e in out["edges"]}
    rec = out["recovery"]
    non_edge = by["Aprime_rainforest_web"]
    passed = (by[hard]["verdict"] == "X_DEMANDED"
              and non_edge["verdict"] == "X_DECOY"
              and rec["precision"] == 1.0 and rec["recall"] == 1.0)
    verdict = "GO (spécificité tient sous corrélation)" if passed else "NO-GO (faux positif corrélé)"
    print(f"VERDICT SP-3 = {verdict} | dur={by[hard]['ratio']:.2f} ({by[hard]['verdict']}) "
          f"non-arête={non_edge['ratio']:.2f} ({non_edge['verdict']}) "
          f"| précision={rec['precision']} rappel={rec['recall']}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

Note : ce `main()` remplace le bloc `if __name__ == "__main__": sys.exit(main())` du bas du fichier créé en Task 3 (il n'existait pas encore de `main`). Ajouter `main()` AVANT ce bloc, ou déplacer le bloc en toute fin. Vérifier qu'il n'y a qu'UN seul `if __name__ == "__main__":`.

- [ ] **Step 4: Lancer le test et la CLI, vérifier le succès**

Run: `python -m pytest tests/test_prerequisite_recovery.py -k preflight -v`
Expected: PASS.

Run: `python tools/prerequisite_recovery_probe.py`
Expected: affiche `VERDICT SP-3 = GO (spécificité tient sous corrélation) | dur=2.xx (X_DEMANDED) non-arête=1.00 (X_DECOY) | précision=1.0 rappel=1.0`. **Noter le ratio dur affiché** (pour le record, Step 5).

- [ ] **Step 5: Écrire le record avec les valeurs mesurées**

Create `docs/EDR/CALIB-SP3_Prerequisite_Recovery_Calibration.md`. Remplacer `~2.3` par le ratio dur réellement affiché à l'étape 4 :

```markdown
---
id: CALIB-SP3
type: EDR
title: "Le demand-marker récupère un DAG de prérequis imposé et garde sa spécificité sous confond corrélé (os-taxonomy comme clé de réponse) — GO pour SP-2"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question
SP-2 (peupler un graphe de capacités par ablation) suppose que l'ablation within-subject récupère un DAG
de prérequis. Cet instrument, calibré (P2.4) sur un monde à UN canal sans confond, tient-il sur un DAG
avec structure de CORRÉLATION (prérequis partageant un ancêtre) ? os-taxonomy fournit la forme ; on l'impose
dans un monde-jouet analytique (A1) dont la réponse est connue par construction.

## Méthode
Sous-graphe au format os-taxonomy : B a un prérequis DUR (Ah) et MOU (As) ; Aprime est un NON-prérequis
corrélé à Ah via l'ancêtre partagé Z. Monde-jouet : acquisition de B gatée (`income + hard_w·eff(Ah) +
soft_w·eff(As)`), transfert d'ancêtre pour fabriquer la corrélation. Ablation within-subject chirurgicale
de chaque prérequis candidat → `ablation_verdict` (n=12 seeds, métrique VIVANTE, `intervention_verified`).

## Résultat
GO. Prérequis dur récupéré (X_DEMANDED, ratio ~2.3) ; non-prérequis corrélé INERTE (X_DECOY, ratio 1.00) ;
monotonie dur > mou > non-arête ; précision=rappel=1.0. Contraste gravé : une ablation par l'ANCÊTRE Z
faux-positive (X_DEMANDED) — la spécificité n'est PAS automatique, elle exige d'ablater le bon canal.

## Portée (bornée)
A1 démontre que la CORRÉLATION seule ne fait pas faux-positiver une ablation chirurgicale. L'aliasing de
SUBSTRAT (représentation partagée) est HORS de portée de A1 (pas de substrat partagé) → reste à vérifier en
SP-2 sur le substrat réel. Le contraste ancêtre montre le mode d'échec à éviter.

## Ce que ça débloque
SP-2 peut peupler le graphe de capacités par ablation within-subject, à condition d'ablater chirurgicalement
(pas par un ancêtre partagé). Cf. `docs/superpowers/specs/2026-07-23-sp3-prerequisite-recovery-calibration-design.md`.
```

- [ ] **Step 6: Vérifier les liens du record**

Run: `python tools/check_record_links.py`
Expected: aucun signalement d'orphelin pour `CALIB-SP3` (frontmatter `gate:`/`tests:`/`adopts:` présents).

- [ ] **Step 7: Lancer la suite SP-3 complète + le cliquet**

Run: `python -m pytest tests/test_prerequisite_recovery.py tests/sandbox/test_instrument_calibration.py -k "sp3 or prerequisite or competence or acquisition or probe or preflight or graph_recovery or fixture" -v`
Expected: tous PASS.

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.`

- [ ] **Step 8: Commit**

```bash
git add tools/prerequisite_recovery_probe.py tests/test_prerequisite_recovery.py docs/EDR/CALIB-SP3_Prerequisite_Recovery_Calibration.md
git commit -m "feat(SP-3): pre-vol + CLI go/no-go + record CALIB-SP3 (GO, specificite sous correlation)"
```

---

## Self-Review

**Spec coverage :**
- §2 question / go-no-go → Task 5 `main()` verdict GO/NO-GO. ✓
- §3 payload spécificité sous confond corrélé → Task 4 `test_sp3_specificity_holds_under_correlation` + `test_sp3_confounded_ablation_would_false_positive`. ✓
- §4 approche A1 → Task 2 monde analytique. ✓
- §5.1 adaptateur → Task 1. §5.2 monde-jouet → Task 2. §5.3 sonde + verdict de graphe → Task 3. ✓
- §7 trois formes canoniques (no-op / prédiction-linéarité / monotonie) → Task 4. Levée d'ambiguïté soft (ratio pas catégorie) → `test_sp3_ratio_is_monotone`. ✓
- §8 intégration : pré-vol → Task 5 ; cliquet → Task 4 ; licence/NOTICE → Task 1 ; record → Task 5. ✓
- §9 unité=seed, n≥12, métrique vivante → Global Constraints + `test_sp3_metric_is_alive`. ✓
- §10 portée v0 (1 B, 1 hard + 1 soft + 1 non-préreq corrélé) → fixture Task 1. ✓
- §13 risques (métrique morte, aliasing, tautologie, n<12) → gardes VIVANTE, `assert_no_aliasing`, contrôle de spécificité, n=12. ✓
- **Écart assumé vs spec §8** : fixture v0 synthétique au format os-taxonomy (pas extrait réel vendu), pour hygiène anti-fabrication + déterminisme. Vendre un extrait réel = suivi hors v0. Documenté dans Global Constraints + NOTICE.

**Placeholder scan :** aucun TBD/TODO ; tout le code est complet ; la seule valeur à reporter est le ratio dur mesuré, inséré au Step 5 de Task 5 depuis la sortie réelle du Step 4.

**Type consistency :** `subgraph` (clés `target/hard/soft/non_edges`), `world` (clés `income/hard_w/soft_w/own/ancestor/transfer`), `fixture_subgraph()`, `fixture_world()`, `acquisition_scores(subgraph, world, seeds, zeroed, T)`, `run_prerequisite_recovery_probe(subgraph, world, seeds, T, floor, ceiling)`, `prerequisite_recovery_verdict(edges, imposed_hard)` — noms et signatures identiques entre Tasks 1→5. Fixture importée depuis `tools/` partout (source unique). ✓
