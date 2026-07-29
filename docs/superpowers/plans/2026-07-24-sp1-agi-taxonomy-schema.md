# SP-1 — AGI-Taxonomy Schema + Validator-Ratchet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer le modèle de données du graphe capability-demand (schéma JSON façon os-taxonomy) + un validateur-cliquet qui rejette toute arête sans preuve mesurée complète, avec le vocabulaire v0 = 4 capacités réelles en nœuds.

**Architecture:** JSON sous `data/agi_taxonomy/` (nœuds = `capabilities.json`, arêtes = `demands.json` vide en v0) + fichiers JSON-Schema descriptifs + `tools/check_agi_taxonomy.py` (Python stdlib pur, calqué sur `check_instrument_calibration.py`) qui impose la sémantique de preuve. Aucune dépendance nouvelle, aucun run coûteux.

**Tech Stack:** Python 3 (stdlib `json`/`os`/`argparse` uniquement), pytest, JSON.

## Global Constraints

- **Aucune dépendance nouvelle** : le validateur est en stdlib pur (pas de `jsonschema`). Les fichiers `schema/*.json` sont le CONTRAT de format (lisible + pour SP-4) ; le validateur impose les champs+sémantique en Python.
- **Règles de validité d'une arête (verbatim)** : une arête n'est valide que si `evidence.ablation_verdict == "X_DEMANDED"` ET `evidence.n` est un entier `>= 12` ET `evidence.functional_aliasing == "pass"` ET `evidence.record` pointe un fichier existant ET `capability`/`prerequisite` sont des `id` présents dans `capabilities.json` ET `strength ∈ {hard, soft}`.
- **`strength` est DESCRIPTIF** (hard/soft = magnitude du ratio), il ne relâche PAS la règle de verdict : hard ET soft exigent `X_DEMANDED`.
- **`demands.json` reste VIDE (`[]`) en v0** — aucune arête fabriquée. Les vraies arêtes sont le livrable mesuré de SP-2.
- **Nœuds v0 (4, verbatim)** : `perception`→`docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md`/`tools/s2_demand.py` ; `memory`→`docs/EDR/MEM-001_Memory_Pays_Iff_Task_Demands_Delayed_Recall.md`/`tools/memory_demand_world_probe.py` ; `language`→`docs/EDR/LANG-006_Language_Pays_Iff_Task_Demands_Coordination.md`/`tools/language_payoff_probe.py` ; `generalization`→`docs/EDR/G1-001_Generalization_Is_Causal_Skill_Only_Under_Varied_Training.md`/`tools/generalization_transfer_probe.py`. (Tous vérifiés existants.)
- **Nom du validateur** : commence par `check_` → exclu du scan du cliquet de calibration (comme `check_record_links.py`). Ses fonctions (`validate_node`, `validate_edge`, `validate_graph`, `main`) ne matchent aucun motif d'instrument.
- **Baseline** : `tools/agi_taxonomy_baseline.json` ; le validateur gère son absence (défaut vide). Vide en v0 (0 violation). Ne PAS committer de baseline en v0.
- **Pas d'EDR** : SP-1 est de l'infra (schéma+validateur), documentée en REF, pas un verdict scientifique.
- **Commits path-scoped** : `git add <chemins explicites>` uniquement — JAMAIS `git add -A`/`.`/`-a`. Arbre partagé, sessions parallèles actives. Branche `feat/d1-prod-pairing`.

## File Structure

- `data/agi_taxonomy/schema/capability.schema.json` (NOUVEAU) — contrat de forme d'un nœud.
- `data/agi_taxonomy/schema/demand.schema.json` (NOUVEAU) — contrat de forme d'une arête.
- `data/agi_taxonomy/capabilities.json` (NOUVEAU) — les 4 nœuds réels.
- `data/agi_taxonomy/demands.json` (NOUVEAU) — `[]` (vide en v0).
- `tools/check_agi_taxonomy.py` (NOUVEAU) — le validateur-cliquet.
- `tests/test_agi_taxonomy.py` (NOUVEAU) — tests des nœuds réels + fixtures d'arête.
- `docs/REF/REF-AGI-TAXONOMY.md` (NOUVEAU) — doc infra du schéma+validateur.

---

### Task 1: Modèle de données (schéma + capabilities.json + demands.json vide)

**Files:**
- Create: `data/agi_taxonomy/schema/capability.schema.json`
- Create: `data/agi_taxonomy/schema/demand.schema.json`
- Create: `data/agi_taxonomy/capabilities.json`
- Create: `data/agi_taxonomy/demands.json`
- Test: `tests/test_agi_taxonomy.py`

**Interfaces:**
- Consumes: rien.
- Produces: les 4 fichiers de données. `capabilities.json` = liste de 4 objets `{id,title,description,evidence_criterion,probe,record}` ; `demands.json` = `[]`.

- [ ] **Step 1: Créer les fichiers de schéma**

Create `data/agi_taxonomy/schema/capability.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AGI-Taxonomy capability node",
  "type": "object",
  "required": ["id", "title", "description", "evidence_criterion", "probe", "record"],
  "properties": {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string"},
    "evidence_criterion": {"type": "string"},
    "probe": {"type": "string"},
    "record": {"type": "string"}
  }
}
```

Create `data/agi_taxonomy/schema/demand.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AGI-Taxonomy demand edge (Y demands X)",
  "type": "object",
  "required": ["capability", "prerequisite", "strength", "evidence"],
  "properties": {
    "capability": {"type": "string"},
    "prerequisite": {"type": "string"},
    "strength": {"enum": ["hard", "soft"]},
    "evidence": {
      "type": "object",
      "required": ["ablation_verdict", "ratio", "n", "functional_aliasing", "record"],
      "properties": {
        "ablation_verdict": {"type": "string"},
        "ratio": {"type": "number"},
        "n": {"type": "integer"},
        "functional_aliasing": {"type": "string"},
        "record": {"type": "string"}
      }
    }
  }
}
```

- [ ] **Step 2: Créer les données (4 nœuds réels + arêtes vides)**

Create `data/agi_taxonomy/capabilities.json`:

```json
[
  {
    "id": "perception",
    "title": "Perception (lecture de l'observation)",
    "description": "La politique lit l'observation et l'utilise causalement pour agir.",
    "evidence_criterion": "ablation within-subject de l'observation (obs randomisée/occultée) effondre la survie",
    "probe": "tools/s2_demand.py",
    "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"
  },
  {
    "id": "memory",
    "title": "Mémoire (rappel différé)",
    "description": "La politique retient une information pour l'utiliser après un délai.",
    "evidence_criterion": "ablation within-subject de la mémoire effondre le rappel différé",
    "probe": "tools/memory_demand_world_probe.py",
    "record": "docs/EDR/MEM-001_Memory_Pays_Iff_Task_Demands_Delayed_Recall.md"
  },
  {
    "id": "language",
    "title": "Langage référentiel / coordination",
    "description": "La politique émet et lit un signal porteur d'information pour coordonner.",
    "evidence_criterion": "ablation within-subject du canal de communication effondre la coordination",
    "probe": "tools/language_payoff_probe.py",
    "record": "docs/EDR/LANG-006_Language_Pays_Iff_Task_Demands_Coordination.md"
  },
  {
    "id": "generalization",
    "title": "Généralisation (compétence causale)",
    "description": "La compétence transfère à des conditions non vues, seulement sous entraînement varié.",
    "evidence_criterion": "variation d'entraînement within-subject : la compétence n'est causale que sous entraînement varié",
    "probe": "tools/generalization_transfer_probe.py",
    "record": "docs/EDR/G1-001_Generalization_Is_Causal_Skill_Only_Under_Varied_Training.md"
  }
]
```

Create `data/agi_taxonomy/demands.json`:

```json
[]
```

- [ ] **Step 3: Écrire le test du modèle de données (qui échoue)**

Create `tests/test_agi_taxonomy.py`:

```python
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_capabilities_v0_shape_and_files_exist():
    caps = _load("capabilities.json")
    assert [c["id"] for c in caps] == ["perception", "memory", "language", "generalization"]
    for c in caps:
        assert set(c) >= {"id", "title", "description", "evidence_criterion", "probe", "record"}
        assert os.path.isfile(os.path.join(_ROOT, c["probe"])), f"probe absent : {c['probe']}"
        assert os.path.isfile(os.path.join(_ROOT, c["record"])), f"record absent : {c['record']}"


def test_demands_v0_is_empty():
    assert _load("demands.json") == [], "demands.json doit être VIDE en v0 (arêtes = livrable SP-2)"
```

- [ ] **Step 4: Lancer, vérifier l'échec puis le succès**

Run: `python -m pytest tests/test_agi_taxonomy.py -v`
Expected first: FAIL — `FileNotFoundError` (les fichiers de données n'existent pas encore si les tests tournent avant Steps 1-2). Après Steps 1-2 en place : PASS (2 tests).

(Note : ce sont des données statiques ; l'ordre TDD ici est « écrire les fichiers, puis le test qui les contraint ». Si tu écris le test d'abord, il échoue en FileNotFoundError, ce qui est la phase RED attendue.)

- [ ] **Step 5: Commit**

```bash
git add data/agi_taxonomy/ tests/test_agi_taxonomy.py
git commit -m "feat(SP-1): schema + capabilities.json (4 noeuds reels) + demands.json vide"
```

---

### Task 2: Validateur-cliquet + REF doc

**Files:**
- Create: `tools/check_agi_taxonomy.py`
- Create: `docs/REF/REF-AGI-TAXONOMY.md`
- Test: `tests/test_agi_taxonomy.py` (ajout)

**Interfaces:**
- Consumes: `data/agi_taxonomy/capabilities.json` + `demands.json` (Task 1).
- Produces:
  - `validate_node(node) -> list[str]` (violations).
  - `validate_edge(edge, capability_ids) -> list[str]`.
  - `validate_graph(capabilities, demands) -> list[str]`.
  - `main(argv=None) -> int` (exit 1 sur NOUVELLE violation vs baseline).

- [ ] **Step 1: Écrire les tests du validateur (qui échouent)**

Add to `tests/test_agi_taxonomy.py`:

```python
def _valid_edge(**evidence_over):
    """Arête FIXTURE valide-de-forme (record = un vrai EDR pour que _exists passe). Les tests écrasent
    un champ d'evidence pour vérifier chaque règle de rejet."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "functional_aliasing": "pass",
          "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}


_IDS = {"perception", "memory", "language", "generalization"}


def test_real_capabilities_pass_validation():
    from tools.check_agi_taxonomy import validate_graph
    assert validate_graph(_load("capabilities.json"), []) == []


def test_empty_graph_has_no_violations():
    from tools.check_agi_taxonomy import main
    assert main([]) == 0


def test_valid_edge_is_accepted():
    from tools.check_agi_taxonomy import validate_edge
    assert validate_edge(_valid_edge(), _IDS) == []


def test_edge_rejected_when_verdict_not_demanded():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(ablation_verdict="INCONCLUSIVE"), _IDS)
    assert any("X_DEMANDED" in x for x in v)


def test_edge_rejected_when_underpowered():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(n=8), _IDS)
    assert any("n=" in x or ">= 12" in x for x in v)


def test_edge_rejected_when_functional_aliasing_not_pass():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(functional_aliasing="fail"), _IDS)
    assert any("functional_aliasing" in x for x in v)


def test_edge_rejected_when_record_missing():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(record="docs/EDR/DOES_NOT_EXIST.md"), _IDS)
    assert any("record" in x for x in v)


def test_edge_rejected_when_prerequisite_unknown():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge()
    e["prerequisite"] = "telepathy"
    v = validate_edge(e, _IDS)
    assert any("telepathy" in x for x in v)
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_agi_taxonomy.py -k "valid or edge or empty_graph or real_capabilities" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.check_agi_taxonomy'`.

- [ ] **Step 3: Implémenter le validateur**

Create `tools/check_agi_taxonomy.py`:

```python
"""Cliquet du graphe AGI-Taxonomy — calqué sur check_record_links / check_instrument_calibration.

Une arête « Y demande X » n'existe que si elle porte sa PREUVE mesurée complète : verdict d'ablation
X_DEMANDED (demand-marker SP-3), n >= 12 (n_floor), garde d'aliasing fonctionnel `pass` (CALIB-ALIAS),
et un record docs/EDR existant. Une arête sans preuve est REJETÉE. Baseline gelée (vide en v0).

Le fichier commence par `check_` -> exclu du scan du cliquet de calibration (pas d'auto-référence).

Usage :
  python tools/check_agi_taxonomy.py                    # exit 1 sur toute NOUVELLE violation
  python tools/check_agi_taxonomy.py --report           # liste tout, exit 0
  python tools/check_agi_taxonomy.py --update-baseline  # gèle l'état courant
"""
import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")
_CAPS = os.path.join(_DATA, "capabilities.json")
_DEMANDS = os.path.join(_DATA, "demands.json")
_BASELINE = os.path.join(_ROOT, "tools", "agi_taxonomy_baseline.json")
_VALID_STRENGTH = {"hard", "soft"}


def _exists(rel):
    return bool(rel) and os.path.isfile(os.path.join(_ROOT, rel))


def validate_node(node):
    """Violations d'un nœud-capacité (liste vide = conforme)."""
    v = []
    nid = node.get("id", "?")
    for f in ("id", "title", "description", "evidence_criterion", "probe", "record"):
        if not node.get(f):
            v.append(f"nœud {nid} : champ requis manquant/vide '{f}'")
    if node.get("probe") and not _exists(node["probe"]):
        v.append(f"nœud {nid} : probe inexistant '{node['probe']}'")
    if node.get("record") and not _exists(node["record"]):
        v.append(f"nœud {nid} : record inexistant '{node['record']}'")
    return v


def validate_edge(edge, capability_ids):
    """Violations d'une arête-demande. La preuve mesurée COMPLÈTE est exigée (cf. docstring module)."""
    v = []
    lbl = f"{edge.get('capability', '?')}->{edge.get('prerequisite', '?')}"
    for f in ("capability", "prerequisite", "strength", "evidence"):
        if edge.get(f) in (None, ""):
            v.append(f"arête {lbl} : champ requis manquant '{f}'")
    if edge.get("strength") not in _VALID_STRENGTH:
        v.append(f"arête {lbl} : strength invalide '{edge.get('strength')}' (attendu hard|soft)")
    for ref in ("capability", "prerequisite"):
        if edge.get(ref) and edge[ref] not in capability_ids:
            v.append(f"arête {lbl} : {ref} '{edge[ref]}' absent de capabilities.json")
    ev = edge.get("evidence") or {}
    if ev.get("ablation_verdict") != "X_DEMANDED":
        v.append(f"arête {lbl} : ablation_verdict='{ev.get('ablation_verdict')}' "
                 "(exigé X_DEMANDED — demand-marker SP-3)")
    if not isinstance(ev.get("n"), int) or ev.get("n", 0) < 12:
        v.append(f"arête {lbl} : n={ev.get('n')} (exigé entier >= 12, n_floor)")
    if ev.get("functional_aliasing") != "pass":
        v.append(f"arête {lbl} : functional_aliasing='{ev.get('functional_aliasing')}' "
                 "(exigé 'pass' — garde CALIB-ALIAS)")
    if not _exists(ev.get("record")):
        v.append(f"arête {lbl} : record de preuve manquant/inexistant '{ev.get('record')}'")
    return v


def validate_graph(capabilities, demands):
    """Toutes les violations du graphe (nœuds puis arêtes)."""
    ids = {c.get("id") for c in capabilities}
    out = []
    for c in capabilities:
        out += validate_node(c)
    for e in demands:
        out += validate_edge(e, ids)
    return out


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="Liste toutes les violations, exit 0.")
    ap.add_argument("--update-baseline", action="store_true", help="Gèle l'état courant.")
    args = ap.parse_args(argv)

    caps = _load(_CAPS, [])
    demands = _load(_DEMANDS, [])
    violations = validate_graph(caps, demands)

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"violations": violations}, fh, indent=2, ensure_ascii=False)
        print(f"baseline gelé : {len(violations)} violations -> {_BASELINE}")
        return 0

    known = set(_load(_BASELINE, {"violations": []}).get("violations", []))
    nouvelles = [x for x in violations if x not in known]
    print(f"AGI-Taxonomy : {len(caps)} capacités, {len(demands)} arêtes | "
          f"{len(violations)} violations (dont {len(nouvelles)} NOUVELLES)")
    if args.report:
        for x in violations:
            print("  -", x)
        return 0
    for x in nouvelles:
        print("  [NOUVELLE VIOLATION]", x)
    if nouvelles:
        print("\nUne arête n'existe que si elle porte sa preuve (X_DEMANDED, n>=12, aliasing pass, record).")
        return 1
    print("OK : aucune nouvelle violation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Lancer les tests du validateur, vérifier le succès**

Run: `python -m pytest tests/test_agi_taxonomy.py -v`
Expected: PASS (10 tests : 2 données + 8 validateur).

- [ ] **Step 5: Vérifier le comportement CLI**

Run: `python tools/check_agi_taxonomy.py`
Expected: `AGI-Taxonomy : 4 capacités, 0 arêtes | 0 violations (dont 0 NOUVELLES)` puis `OK : aucune nouvelle violation.` (exit 0).

- [ ] **Step 6: Vérifier que le validateur est HORS du cliquet de calibration**

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.` — `check_agi_taxonomy.py` (préfixe `check_`) n'est PAS scanné, donc n'ajoute aucun instrument non calibré.

- [ ] **Step 7: Écrire la doc REF**

Create `docs/REF/REF-AGI-TAXONOMY.md`:

```markdown
# REF — AGI-Taxonomy : graphe capability-demand

Modèle de données de l'arc AGI-Taxonomy (backlog P4.3), au format `withmarbleapp/os-taxonomy`.

## Fichiers
- `data/agi_taxonomy/capabilities.json` — nœuds (capacités). Chaque nœud porte un `evidence_criterion`
  (le test de demande within-subject), un `probe` (la sonde) et un `record` (docs/EDR) — tous vérifiés existants.
- `data/agi_taxonomy/demands.json` — arêtes « Y demande X ». **Vide tant qu'aucune arête n'a passé la
  chaîne de preuve** (peuplé par SP-2, par ablation mesurée).
- `data/agi_taxonomy/schema/*.json` — contrat de forme (JSON Schema, pour lecture + publication SP-4).

## Le cliquet — `tools/check_agi_taxonomy.py`
Calqué sur `check_record_links` / `check_instrument_calibration` (baseline gelée, `--report`,
`--update-baseline`, exit 1 sur nouvelle violation). **Une arête n'existe que si elle porte sa preuve
mesurée COMPLÈTE** :
- `ablation_verdict == "X_DEMANDED"` (demand-marker, cf. CALIB-SP3) ;
- `n >= 12` (n_floor de `ablation_verdict`) ;
- `functional_aliasing == "pass"` (garde `assert_no_functional_aliasing`, cf. CALIB-ALIAS) ;
- `record` = un docs/EDR existant ; `capability`/`prerequisite` présents dans `capabilities.json`.

`strength` (hard/soft) est DESCRIPTIF (magnitude du ratio) et ne relâche PAS la règle de verdict.

## Ajouter une arête
Interdit de l'affirmer : il faut la MESURER (ablation within-subject + garde d'aliasing), écrire le record,
puis ajouter l'objet dans `demands.json` avec son `evidence`. Le cliquet rejette toute arête incomplète.
```

- [ ] **Step 8: Commit**

```bash
git add tools/check_agi_taxonomy.py tests/test_agi_taxonomy.py docs/REF/REF-AGI-TAXONOMY.md
git status --short   # confirmer UNIQUEMENT ces trois chemins
git commit -m "feat(SP-1): validateur-cliquet check_agi_taxonomy (preuve exigee par arete) + REF"
```

Si le hook pre-commit bloque sur un instrument non calibré d'une AUTRE session (hazard tree-wide vécu sur CALIB-ALIAS), stash path-scoped ce fichier étranger, commit, pop, vérifier identique — jamais `--no-verify`.

---

## Self-Review

**Spec coverage :**
- §2 objectif (schéma + validateur + 4 nœuds, demands vide) → Tasks 1+2. ✓
- §3 constat honnête (v0 = nœuds, pas d'arête fabriquée) → `demands.json = []` + fixtures pour l'enforcement. ✓
- §4 modèle de données → Task 1. §5 schéma → Task 1 (+ sémantique strength en Global Constraints). §6 validateur (règles verbatim) → Task 2 `validate_edge`. ✓
- §7 portée v0 → 2 tasks, pur JSON, pas de hook obligatoire. ✓
- §8 tests (nœuds + 6 fixtures d'arête + baseline vide) → Task 1 (2) + Task 2 (8). ✓
- §9 intégration (exclu du cliquet calib, REF) → Task 2 Steps 6-7. ✓
- §11 critères de succès → couverts. §12 risques (schéma qui n'oppose rien / fabrication / référence fantôme) → validateur + demands vide + `_exists`. ✓

**Placeholder scan :** aucun TBD/TODO ; code complet ; les 4 chemins de nœuds sont vérifiés existants (Global Constraints).

**Type consistency :** `validate_node(node)`, `validate_edge(edge, capability_ids)`, `validate_graph(capabilities, demands)`, `main(argv)` — signatures identiques entre Task 2 et les tests. Les champs d'arête (`ablation_verdict/ratio/n/functional_aliasing/record`) et de nœud (`id/title/description/evidence_criterion/probe/record`) sont identiques entre schéma (§Task 1), données, validateur et tests. ✓
