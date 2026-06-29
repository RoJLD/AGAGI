# Moteur de consolidation EDR/ADR/SDR — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un outil pur Python qui scanne `docs/{EDR,ADR,SDR}/`, construit le graphe de décisions (SDR→EDR→ADR), valide sa cohérence (échoue sur lien cassé), et génère l'état de la roadmap G0→G4.

**Architecture:** Module sans état `tools/consolidate_records.py` : `parse_record` (frontmatter YAML) → `scan_records` (dossiers) → `build_graph` (nœuds+arêtes) → `validate_graph` (problèmes) → `roadmap_state` (par porte) → `main` (écrit `results/records_graph.json`, exit≠0 si problème). Aucun LLM, aucune dépendance simulation. Tolérant aux EDR existants sans frontmatter (record « non lié », signalé).

**Tech Stack:** Python 3.11, PyYAML, pytest. Pattern de header tools/ (insertion racine projet sur `sys.path`).

## Global Constraints

- **Pas de LLM, pas de réseau** : consolidation = index statique pur (décision spec §4.3).
- **Anti-théâtre** : `main` sort en code ≠0 si un lien `motivates`/`triggers`/`tests` pointe vers un id inexistant, ou si une SDR `status: validated` n'a aucun EDR `validated` qui la teste (spec §4.3, §8.2).
- **Tolérance migration** : un record `.md` sans frontmatter est accepté comme record « non lié » (`linked: False`), jamais une erreur dure (spec §4.3 note migration).
- **Ids canoniques** : `SDR-G{0..4}`, `ADR-{NNN}`, `EDR-{NNN}` (EDR dérivé du nom de fichier `docs/EDR/NNN_*.md` si pas de frontmatter).
- **Sortie versionnée** : le graphe JSON va dans `results/` (gitignoré, dev local) — ne PAS committer le JSON généré.
- **Sessions parallèles** : commits path-scoped sur les fichiers créés/modifiés uniquement (jamais `git add -A`).

---

### Task 1: Parser de frontmatter (`parse_record`)

**Files:**
- Create: `tools/consolidate_records.py`
- Test: `tests/test_consolidate_records.py`
- Modify: `requirements.txt` (ajouter `PyYAML>=6.0`)

**Interfaces:**
- Produces: `parse_record(path: str) -> dict | None` — retourne un dict record avec clés `id, type, title, status, gate, motivates, triggers, tests, verdict, file, linked`. `linked=False` si pas de frontmatter mais nom de fichier EDR reconnu. `None` si fichier non-record (ni frontmatter, ni nom EDR `NNN_*.md`).
- Record dict shape (canonique, réutilisé par toutes les tâches) :
  ```python
  {"id": "SDR-G1", "type": "SDR", "title": "...", "status": "open",
   "gate": "G1", "motivates": ["EDR-105"], "triggers": [], "tests": [],
   "verdict": None, "file": "docs/SDR/G1_....md", "linked": True}
  ```

- [ ] **Step 1: Ajouter la dépendance YAML**

Modifier `requirements.txt`, ajouter à la fin :
```
PyYAML>=6.0
```

- [ ] **Step 2: Write the failing test**

Créer `tests/test_consolidate_records.py` :
```python
import os
import re
import json
import pathlib

import pytest

from tools.consolidate_records import (
    parse_record, scan_records, build_graph, validate_graph, roadmap_state, main,
)


def _write(p: pathlib.Path, text: str) -> str:
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_record_reads_frontmatter(tmp_path):
    f = _write(tmp_path / "G1_transfer.md", (
        "---\n"
        "id: SDR-G1\n"
        "type: SDR\n"
        "title: La competence generalise-t-elle\n"
        "status: open\n"
        "gate: G1\n"
        "motivates: [EDR-105, EDR-108]\n"
        "---\n"
        "# corps libre\n"
    ))
    rec = parse_record(f)
    assert rec["id"] == "SDR-G1"
    assert rec["type"] == "SDR"
    assert rec["gate"] == "G1"
    assert rec["motivates"] == ["EDR-105", "EDR-108"]
    assert rec["triggers"] == [] and rec["tests"] == []
    assert rec["linked"] is True


def test_parse_record_tolerates_edr_without_frontmatter(tmp_path):
    f = _write(tmp_path / "105_Forage_Bottleneck.md", "# EDR 105 sans frontmatter\n")
    rec = parse_record(f)
    assert rec["id"] == "EDR-105"
    assert rec["type"] == "EDR"
    assert rec["linked"] is False


def test_parse_record_returns_none_for_non_record(tmp_path):
    f = _write(tmp_path / "README.md", "# pas un record\n")
    assert parse_record(f) is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.consolidate_records'`

- [ ] **Step 4: Write minimal implementation**

Créer `tools/consolidate_records.py` :
```python
"""Consolidation des records de décision (SDR/ADR/EDR) en un graphe statique.

Scanne docs/{SDR,ADR,EDR}/, lit le frontmatter YAML, construit le graphe causal
SDR --MOTIVE--> EDR --DECLENCHE--> ADR (+ EDR --TESTE--> SDR), valide sa cohérence
et génère l'état de la roadmap G0->G4. Pur, sans LLM, sans réseau.
Spec : docs/superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md (section 4)."""
import os
import re
import sys
import json

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_LIST_KEYS = ("motivates", "triggers", "tests")
_EDR_NAME = re.compile(r"^(\d{3})_.+\.md$")


def _empty_record(file: str) -> dict:
    return {"id": None, "type": None, "title": "", "status": "open", "gate": None,
            "motivates": [], "triggers": [], "tests": [], "verdict": None,
            "file": file, "linked": False}


def parse_record(path: str) -> dict | None:
    """Lit un record .md. Frontmatter YAML -> record lié. EDR nommé NNN_*.md sans
    frontmatter -> record toléré non lié. Sinon None (fichier non-record)."""
    name = os.path.basename(path)
    text = open(path, encoding="utf-8").read()
    rec = _empty_record(os.path.relpath(path, _ROOT).replace(os.sep, "/"))

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            for k, v in meta.items():
                if k in _LIST_KEYS:
                    rec[k] = list(v) if v else []
                elif k in rec:
                    rec[k] = v
            if rec["id"]:
                return rec

    m = _EDR_NAME.match(name)
    if m:
        rec["id"] = f"EDR-{int(m.group(1)):03d}"
        rec["type"] = "EDR"
        rec["title"] = name[4:-3].replace("_", " ")
        return rec
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py requirements.txt
git commit -m "feat(records): parser frontmatter SDR/ADR/EDR tolerant (consolidation)"
```

---

### Task 2: Scan des dossiers (`scan_records`)

**Files:**
- Modify: `tools/consolidate_records.py`
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: `parse_record`
- Produces: `scan_records(root: str = _ROOT) -> list[dict]` — scanne `docs/SDR`, `docs/ADR`, `docs/EDR` sous `root`, retourne tous les records (triés par id), ignore les fichiers non-record et les dossiers absents.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_consolidate_records.py` :
```python
def test_scan_records_collects_all_types(tmp_path):
    (tmp_path / "docs" / "SDR").mkdir(parents=True)
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    _write(tmp_path / "docs" / "SDR" / "G0_validity.md",
           "---\nid: SDR-G0\ntype: SDR\ntitle: t\nstatus: open\ngate: G0\n---\n")
    _write(tmp_path / "docs" / "EDR" / "105_Forage.md", "# edr\n")
    _write(tmp_path / "docs" / "EDR" / "not_an_edr.md", "# noise\n")
    recs = scan_records(str(tmp_path))
    ids = sorted(r["id"] for r in recs)
    assert ids == ["EDR-105", "SDR-G0"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_consolidate_records.py::test_scan_records_collects_all_types -v`
Expected: FAIL — `ImportError: cannot import name 'scan_records'` (déjà importé en tête → collection error)

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/consolidate_records.py` :
```python
def scan_records(root: str = _ROOT) -> list[dict]:
    out: list[dict] = []
    for sub in ("docs/SDR", "docs/ADR", "docs/EDR"):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not name.endswith(".md"):
                continue
            rec = parse_record(os.path.join(d, name))
            if rec is not None:
                out.append(rec)
    out.sort(key=lambda r: r["id"])
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(records): scan docs/{SDR,ADR,EDR} en liste de records"
```

---

### Task 3: Construction du graphe (`build_graph`)

**Files:**
- Modify: `tools/consolidate_records.py`
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: liste de records (`scan_records`)
- Produces: `build_graph(records: list[dict]) -> dict` — retourne `{"nodes": [...], "edges": [...]}`. Chaque edge = `{"from": id, "to": id, "rel": REL}` avec `REL` ∈ `{"MOTIVE", "DECLENCHE", "TESTE"}` issus respectivement de `motivates`, `triggers`, `tests`. Les nœuds = `{"id","type","title","status","gate","verdict","linked"}`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_consolidate_records.py` :
```python
def test_build_graph_emits_typed_edges():
    recs = [
        {"id": "SDR-G1", "type": "SDR", "title": "t", "status": "open", "gate": "G1",
         "motivates": ["EDR-105"], "triggers": [], "tests": [], "verdict": None,
         "file": "f", "linked": True},
        {"id": "EDR-105", "type": "EDR", "title": "t", "status": "refuted", "gate": "G1",
         "motivates": [], "triggers": ["ADR-007"], "tests": ["SDR-G1"], "verdict": "NEUTRE",
         "file": "f", "linked": True},
    ]
    g = build_graph(recs)
    rels = sorted((e["from"], e["to"], e["rel"]) for e in g["edges"])
    assert rels == [
        ("EDR-105", "ADR-007", "DECLENCHE"),
        ("EDR-105", "SDR-G1", "TESTE"),
        ("SDR-G1", "EDR-105", "MOTIVE"),
    ]
    assert {n["id"] for n in g["nodes"]} == {"SDR-G1", "EDR-105"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_consolidate_records.py::test_build_graph_emits_typed_edges -v`
Expected: FAIL — `cannot import name 'build_graph'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/consolidate_records.py` :
```python
_REL = {"motivates": "MOTIVE", "triggers": "DECLENCHE", "tests": "TESTE"}
_NODE_KEYS = ("id", "type", "title", "status", "gate", "verdict", "linked")


def build_graph(records: list[dict]) -> dict:
    nodes = [{k: r[k] for k in _NODE_KEYS} for r in records]
    edges = []
    for r in records:
        for key, rel in _REL.items():
            for target in r[key]:
                edges.append({"from": r["id"], "to": target, "rel": rel})
    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(records): build_graph -> noeuds + aretes typees MOTIVE/DECLENCHE/TESTE"
```

---

### Task 4: Validation de cohérence (`validate_graph`)

**Files:**
- Modify: `tools/consolidate_records.py`
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: liste de records
- Produces: `validate_graph(records: list[dict]) -> list[dict]` — retourne la liste des problèmes. Chaque problème = `{"kind": K, "record": id, "detail": str}`. `K` ∈ `{"broken_link", "unsupported_gate"}`. `broken_link` : un id cité dans `motivates`/`triggers`/`tests` n'existe pas. `unsupported_gate` : une SDR `status == "validated"` sans aucun EDR `status == "validated"` qui la `tests`. Liste vide = cohérent.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_consolidate_records.py` :
```python
def _rec(id, type, **kw):
    base = {"id": id, "type": type, "title": "t", "status": "open", "gate": None,
            "motivates": [], "triggers": [], "tests": [], "verdict": None,
            "file": "f", "linked": True}
    base.update(kw)
    return base


def test_validate_flags_broken_link():
    recs = [_rec("SDR-G1", "SDR", gate="G1", motivates=["EDR-999"])]
    probs = validate_graph(recs)
    assert any(p["kind"] == "broken_link" and "EDR-999" in p["detail"] for p in probs)


def test_validate_flags_validated_gate_without_validated_edr():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="validated"),
        _rec("EDR-105", "EDR", gate="G1", status="refuted", tests=["SDR-G1"]),
    ]
    probs = validate_graph(recs)
    assert any(p["kind"] == "unsupported_gate" and p["record"] == "SDR-G1" for p in probs)


def test_validate_clean_graph_has_no_problems():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="validated", motivates=["EDR-105"]),
        _rec("EDR-105", "EDR", gate="G1", status="validated", tests=["SDR-G1"]),
    ]
    assert validate_graph(recs) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_consolidate_records.py -k validate -v`
Expected: FAIL — `cannot import name 'validate_graph'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/consolidate_records.py` :
```python
def validate_graph(records: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in records}
    problems: list[dict] = []

    for r in records:
        for key in _LIST_KEYS:
            for target in r[key]:
                if target not in by_id:
                    problems.append({"kind": "broken_link", "record": r["id"],
                                     "detail": f"{r['id']}.{key} -> {target} inexistant"})

    for r in records:
        if r["type"] == "SDR" and r["status"] == "validated":
            supporters = [s for s in records
                          if s["type"] == "EDR" and s["status"] == "validated"
                          and r["id"] in s["tests"]]
            if not supporters:
                problems.append({"kind": "unsupported_gate", "record": r["id"],
                                 "detail": f"{r['id']} validee sans EDR valide qui la teste"})
    return problems
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(records): validate_graph (liens casses + portes validees non soutenues)"
```

---

### Task 5: État roadmap + `main` (JSON + exit code)

**Files:**
- Modify: `tools/consolidate_records.py`
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: `scan_records`, `build_graph`, `validate_graph`
- Produces:
  - `roadmap_state(records: list[dict]) -> dict` — `{gate: {"sdr": id|None, "status": str, "tested_by": [edr_ids], "triggered_adr": [adr_ids]}}` pour `gate` ∈ `G0..G4`. `tested_by` = EDR dont `tests` contient la SDR de la porte OU dont `gate` == la porte. `triggered_adr` = ADR cités dans `triggers` de ces EDR.
  - `main(argv=None) -> int` — écrit `results/records_graph.json` (`{"graph":..., "roadmap":..., "problems":...}`), imprime un résumé, retourne `1` si problèmes (sinon `0`). Le bloc `if __name__` appelle `sys.exit(main())`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_consolidate_records.py` :
```python
def test_roadmap_state_maps_gate_to_records():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="open", motivates=["EDR-105"]),
        _rec("EDR-105", "EDR", gate="G1", status="refuted", tests=["SDR-G1"],
             triggers=["ADR-007"]),
    ]
    state = roadmap_state(recs)
    assert state["G1"]["sdr"] == "SDR-G1"
    assert state["G1"]["tested_by"] == ["EDR-105"]
    assert state["G1"]["triggered_adr"] == ["ADR-007"]
    assert state["G0"]["sdr"] is None


def test_main_exits_nonzero_on_broken_link(tmp_path, monkeypatch, capsys):
    (tmp_path / "docs" / "SDR").mkdir(parents=True)
    (tmp_path / "results").mkdir()
    _write(tmp_path / "docs" / "SDR" / "G1_x.md",
           "---\nid: SDR-G1\ntype: SDR\ntitle: t\nstatus: open\ngate: G1\n"
           "motivates: [EDR-999]\n---\n")
    rc = main(["--root", str(tmp_path)])
    assert rc == 1
    out = json.loads((tmp_path / "results" / "records_graph.json").read_text(encoding="utf-8"))
    assert out["problems"]
```

> Note : le test `test_main_exits_zero_on_clean_repo` (qui exige les records seed) est ajouté en **Task 6**, pas ici — il ne peut passer qu'une fois les SDR/ADR écrits. Chaque commit reste ainsi vert.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_consolidate_records.py -k "roadmap_state or main_exits" -v`
Expected: FAIL — `cannot import name 'roadmap_state'`

(Note : `test_main_exits_zero_on_clean_repo` échouera tant que les records seed de la Task 6 ne sont pas écrits — c'est attendu, il passera après la Task 6.)

- [ ] **Step 3: Write minimal implementation**

Ajouter à `tools/consolidate_records.py` :
```python
import argparse

_GATES = ("G0", "G1", "G2", "G3", "G4")


def roadmap_state(records: list[dict]) -> dict:
    sdr_by_gate = {r["gate"]: r for r in records if r["type"] == "SDR"}
    state: dict = {}
    for g in _GATES:
        sdr = sdr_by_gate.get(g)
        sdr_id = sdr["id"] if sdr else None
        tested_by = sorted(
            r["id"] for r in records
            if r["type"] == "EDR" and (r["gate"] == g or (sdr_id and sdr_id in r["tests"]))
        )
        triggered = sorted({adr for r in records if r["id"] in tested_by for adr in r["triggers"]})
        state[g] = {"sdr": sdr_id, "status": sdr["status"] if sdr else "absent",
                    "tested_by": tested_by, "triggered_adr": triggered}
    return state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Consolide les records SDR/ADR/EDR.")
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)

    records = scan_records(args.root)
    graph = build_graph(records)
    problems = validate_graph(records)
    roadmap = roadmap_state(records)

    out_dir = os.path.join(args.root, "results")
    os.makedirs(out_dir, exist_ok=True)
    payload = {"graph": graph, "roadmap": roadmap, "problems": problems}
    with open(os.path.join(out_dir, "records_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(f"records={len(records)} edges={len(graph['edges'])} problemes={len(problems)}")
    for p in problems:
        print(f"  [{p['kind']}] {p['detail']}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python -m pytest tests/test_consolidate_records.py -k "roadmap_state or main_exits_nonzero" -v`
Expected: PASS (`test_main_exits_zero_on_clean_repo` reste rouge jusqu'à Task 6 — ne pas la lancer ici)

- [ ] **Step 5: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(records): roadmap_state + main (JSON results/records_graph.json, exit code)"
```

---

### Task 6: Records seed (SDR G0→G4, ADR rétro) + roadmap + run vert end-to-end

**Files:**
- Create: `docs/SDR/G0_world_demands_intelligence.md` … `docs/SDR/G4_agent_anticipates.md` (5 fichiers)
- Create: `docs/ADR/001_engine_ga_gradient_baldwin.md`, `docs/ADR/002_preserve_dims_default_on.md` (2 fichiers)
- Create: `docs/roadmap/FIL_DIRECTEUR_AGI.md`
- Modify: aucun code (validation end-to-end)

**Interfaces:**
- Consumes: tout le module `consolidate_records`. Cette tâche prouve que le vrai repo est cohérent (`main([]) == 0`).

- [ ] **Step 1: Écrire les 5 SDR (un par porte)**

`docs/SDR/G0_world_demands_intelligence.md` :
```markdown
---
id: SDR-G0
type: SDR
title: Le monde EXIGE-t-il l'intelligence
status: open
gate: G0
motivates: []
---
# SDR-G0 — Porte de validité

Hypothèse falsifiable : un champion HoF survit significativement mieux qu'un agent
dummy/aléatoire dans chaque monde aval. KPI `survival_ratio(champion)/survival_ratio(dummy)`,
multi-seed appairé, powered. Si ≈1 → monde factice. Inclut le sous-chantier compute
(parallélisme/early-stopping) prérequis de G1. Réf : spec §3 G0.
```

`docs/SDR/G1_competence_generalizes.md` :
```markdown
---
id: SDR-G1
type: SDR
title: La competence generalise-t-elle (north-star)
status: open
gate: G1
motivates: [EDR-105, EDR-108]
---
# SDR-G1 — Généralisation zéro-shot (north-star)

Hypothèse : champion évolué en monde A atteint la compétence en monde B jamais vu mieux que
tabula-rasa, à compute égal. KPI `transfer_ratio`, test de signe, multi-seed appairé.
Outil existant `tools/curriculum_transfer.py`. Si NEUTRE/NUIT → verrou répertoire-monde
(EDR 105/108) → ADR enrichir-affordance. Réf : spec §3 G1.
```

`docs/SDR/G2_agent_composes.md` :
```markdown
---
id: SDR-G2
type: SDR
title: L'agent compose-t-il
status: open
gate: G2
motivates: []
---
# SDR-G2 — Composition

Hypothèse : l'agent enchaîne des compétences acquises séparément en une séquence nouvelle non
récompensée directement (craft multi-étapes L3+, EDR 018). KPI taux d'émergence vs ablation +
transfert (↔G1). Réf : spec §3 G2.
```

`docs/SDR/G3_language_pays.md` :
```markdown
---
id: SDR-G3
type: SDR
title: Le langage paye-t-il (cloture Arc 4)
status: open
gate: G3
motivates: [EDR-087, EDR-088]
---
# SDR-G3 — Le langage paye

Pré-condition levée par G0-G2 (gate compétence d'EDR 075). Hypothèse : le code référentiel
fiable (`use_ref_head`, EDR 074) améliore causalement la chasse coop/survie des auditeurs.
KPI `mammoth_kills`/survie ON vs OFF, powered R≥4, 12 confounds (EDR 087).
Outil `tools/wire_ref_head.py`. Réf : spec §3 G3.
```

`docs/SDR/G4_agent_anticipates.md` :
```markdown
---
id: SDR-G4
type: SDR
title: L'agent anticipe-t-il (capstone)
status: open
gate: G4
motivates: [EDR-095]
---
# SDR-G4 — Planification instrumentale

Hypothèse : brancher l'organe de rêve sur `world_model.predict()` (vraie simulation, pas le
random-shooting latent réfuté EDR 095 ni le depth-1 linéaire réfuté) produit une anticipation
qui paye. KPI `anticipation_bench`, depth-k / g bilinéaire. Réf : spec §3 G4.
```

- [ ] **Step 2: Écrire les 2 ADR rétro**

`docs/ADR/001_engine_ga_gradient_baldwin.md` :
```markdown
---
id: ADR-001
type: ADR
title: Moteur GA externe + gradient interne + Baldwin
status: validated
gate: null
motivates: []
triggers: []
tests: []
---
# ADR-001 — Le moteur invariant des portes

Décision : le GA explore le substrat (topologies, demandes-monde, diversité), le gradient
(Actor-Critic intra-vie) apprend dans la vie, Baldwin façonne des inits apprenables.
Le GA n'est PAS le moteur de l'intelligence mais de la recherche de substrat.
Fondé sur EDR 064/067-070 (mutation seule = chercheur faible). Réf : spec §2.
```

`docs/ADR/002_preserve_dims_default_on.md` :
```markdown
---
id: ADR-002
type: ADR
title: preserve_dims ON par defaut (evolution topologique active)
status: validated
gate: null
motivates: []
triggers: []
tests: []
---
# ADR-002 — Évolution topologique en prod

Décision : `preserve_dims=True` par défaut (PR #58) → `from_genome` n'aplatit plus l'archi,
`add_node` persiste, les réseaux grossissent (cap soft 256). Escape-hatch `=False` conservé.
Corrige le bug keystone. Réf : mémoire from-genome-flattens-architecture.
```

- [ ] **Step 3: Écrire la roadmap stratégique**

`docs/roadmap/FIL_DIRECTEUR_AGI.md` :
```markdown
# Fil directeur AGI — les 5 portes G0→G4

> Stratégie qui chapeaute SCIENCE/NAS/BACKEND/FRONTEND. Continue (ne remplace pas)
> `../FIL_CONDUCTEUR.md`. État auto-généré : `tools/consolidate_records.py` → `results/records_graph.json`.
> Design : `../superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md`.

## Thèse réconciliée
« Le bon est trouvé si le monde l'EXIGE (010/012) ET si l'agent l'APPREND (067) » — les deux se
mesurent en un point : la **généralisation zéro-shot** (`transfer_ratio`, north-star).

## Moteur (ADR-001, ADR-002)
GA (recherche de substrat) + gradient (apprentissage intra-vie) + Baldwin. Évolution topologique active.

## Les 5 portes (bottom-up par dépendance, capacités stratifiées EDR 075)
| Porte | Question | KPI | Outil | Record |
|---|---|---|---|---|
| **G0** | Le monde exige ? | survival_ratio champion/dummy | à créer | SDR-G0 |
| **G1** | Ça généralise ? ★ | transfer_ratio | `tools/curriculum_transfer.py` | SDR-G1 |
| **G2** | Ça compose ? | émergence chaîne non récompensée | à créer | SDR-G2 |
| **G3** | Le langage paye ? | mammoth_kills ON/OFF | `tools/wire_ref_head.py` | SDR-G3 |
| **G4** | Ça anticipe ? | anticipation_bench | `tools/anticipation_bench.py` | SDR-G4 |

> On ne franchit une porte que si la précédente est mesurée (verdict EDR powered).
> Méthode : Commandement 15 (1 variable, powered, valide-ou-revert). Négatifs = livrables.

## Consolidation (SDR→EDR→ADR)
`docs/{SDR,ADR,EDR}/` + frontmatter `motivates`/`triggers`/`tests`. `tools/consolidate_records.py`
construit le graphe, échoue sur lien cassé (anti-théâtre). Niveau actuel : index statique (pas de LLM).
```

- [ ] **Step 4: Lancer la consolidation sur le vrai repo (doit être vert)**

Run: `python tools/consolidate_records.py`
Expected: `problemes=0` imprimé, exit 0. (Les `motivates` pointent vers EDR-087/088/095/105/108 qui existent dans `docs/EDR/` ; aucune SDR n'est `validated` → pas d'`unsupported_gate`.)

- [ ] **Step 5: Lancer toute la suite de tests (incl. le test repo-propre)**

Run: `python -m pytest tests/test_consolidate_records.py -v`
Expected: PASS (9 tests, dont `test_main_exits_zero_on_clean_repo`)

- [ ] **Step 6: Commit**

```bash
git add docs/SDR docs/ADR docs/roadmap/FIL_DIRECTEUR_AGI.md
git commit -m "docs(roadmap): records seed SDR G0-G4 + ADR moteur + FIL_DIRECTEUR_AGI"
```

---

## Self-Review

**1. Spec coverage** (spec §4 + §6 périmètre « dans le périmètre ») :
- Taxonomie EDR/ADR/SDR → Task 6 (records seed) + parser Task 1. ✅
- Frontmatter normalisé (schéma §4.3) → Task 1 (parse) + Task 6 (exemples réels). ✅
- `tools/consolidate_records.py` (scan, graphe JSON, liens cassés, état roadmap) → Tasks 2-5. ✅
- Anti-théâtre (exit≠0 sur lien cassé / porte validée non soutenue) → Task 4 + Task 5. ✅
- Tolérance migration EDR sans frontmatter → Task 1 (`test_parse_record_tolerates_edr_without_frontmatter`). ✅
- `FIL_DIRECTEUR_AGI.md` → Task 6. ✅
- Premiers SDR G0-G4 + ADR rétro (moteur, preserve_dims) → Task 6. ✅
- **Hors périmètre (différé, attendu)** : endpoints `/api/adr`+`/api/sdr`, vue frontend → **plan séparé** (suivi). G0 benchmark + compute → **plan 2**. Noté, pas un gap.

**2. Placeholder scan** : aucun TBD/TODO ; chaque step de code montre le code complet ; chaque step de test montre l'assertion. ✅

**3. Type consistency** : record dict shape identique partout (`id,type,title,status,gate,motivates,triggers,tests,verdict,file,linked`) ; `_LIST_KEYS` réutilisé en Task 1/4 ; `_REL` (Task 3) et `_GATES` (Task 5) cohérents ; signatures `parse_record`/`scan_records`/`build_graph`/`validate_graph`/`roadmap_state`/`main` stables entre import (Task 1) et définitions. ✅
