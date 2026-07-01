# Territoires de recherche — Partie 1 (Fondation) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poser la fondation de la spécialisation de la recherche AGAGI : un registre vivant des territoires + le schéma d'IDs préfixés + l'outillage consolidate qui recense les préfixes et signale les doublons — sans toucher aux 151 EDR legacy.

**Architecture:** Trois livrables indépendants. (1) `docs/roadmap/SPECIALITES.md` = registre source-de-vérité (10 territoires, convention d'IDs, commons+intendants). (2) `consolidate_records.py` gagne un recensement par préfixe (`prefix_counts`) qui alimentera le cartographe. (3) le même outil gagne une détection de doublons d'id émise en `warnings` non-bloquants (les 5 doublons legacy existants restent tolérés ; les futurs EDR préfixés ne collisionnent jamais par construction).

**Tech Stack:** Python 3, pytest, PyYAML (déjà en place). Docs Markdown.

## Global Constraints

- **IDs préfixés append-only** : format `EDR-<PREFIX>-<nnn>` (nnn zéro-paddé à 3). Un préfixe n'est JAMAIS réutilisé ni renuméroté.
- **Legacy cohabite, intouché** : les `EDR-nnn` (1-151) et fichiers `NNN_*.md` ne sont ni renommés ni renumérotés.
- **EDR préfixé = frontmatter obligatoire** (`id: EDR-<PREFIX>-<nnn>`) ; déjà parsé par `parse_record` sans changement.
- **Doublon d'id = WARNING non-bloquant** en Partie 1 (rc du consolidate inchangé) ; `test_main_exits_zero_on_clean_repo` doit rester vert.
- **TDD** (RED→GREEN), **commits path-scoped**, un commit par tâche. Communication et docs en **français**.
- Fin de message de commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Structure des fichiers

- CRÉÉ `docs/roadmap/SPECIALITES.md` — registre vivant (une section par territoire + en-tête convention/commons).
- MODIFIÉ `docs/roadmap/SCIENCE.md` — pointeur vers le registre (2 lignes).
- MODIFIÉ `tools/consolidate_records.py` — `_prefix_of()`, `find_duplicate_ids()`, `prefix_counts`+`warnings` dans le payload et l'affichage.
- MODIFIÉ `tests/test_consolidate_records.py` — tests des deux nouvelles fonctions + présence des clés payload.

---

### Task 1: Registre vivant `SPECIALITES.md` + pointeur

**Files:**
- Create: `docs/roadmap/SPECIALITES.md`
- Modify: `docs/roadmap/SCIENCE.md` (ajouter un pointeur en tête de la section « Statut des Vagues (pointeurs) »)

**Interfaces:**
- Consumes: rien (doc).
- Produces: le registre que le cartographe (Partie 2) lira ; la convention d'IDs que les EDR futurs suivront.

- [ ] **Step 1: Créer le registre**

Créer `docs/roadmap/SPECIALITES.md` avec exactement ce contenu :

```markdown
# Registre des territoires de recherche — AGAGI

> Source de vérité de la spécialisation. Éditer la carte = éditer ce fichier (path-scoped, ligne-à-ligne).
> Design : `docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md`.

## Convention d'identifiants

- Nouveaux records : `EDR-<PREFIX>-<nnn>` (nnn zéro-paddé à 3, séquence propre au préfixe). Frontmatter `id:` obligatoire.
- Nom de fichier miroir : `docs/EDR/<PREFIX>-<nnn>_Titre.md` (ex. `SUB-012_...md`).
- **Append-only** : un préfixe n'est jamais réutilisé ni renuméroté → collision impossible.
- Legacy `EDR-nnn` (1-151) : intouché, cohabite.
- Collaboration : un pilote (préfixe propriétaire) + champ frontmatter `also: [PREFIX, …]`.

## Commons partagés (intendant désigné, read-mostly)

| Commons | Intendant | Notes |
|---------|-----------|-------|
| Sim de monde | WLD | WLD/CRAFT/NAV/FAM le LISENT ; chacun écrit ses propres probes |
| `tools/consolidate_records.py` | INFRA | outil de graphe des records |
| Core substrat | SUB | moteur torch/legacy |
| `tools/substrate_ab_compositional.py` | BIND | banc compositionnel |

## Territoires

### SUB — Substrat & Moteur d'apprentissage
- statut: actif
- couche: Substrat/Moteur
- question_phare: Moteur torch ≥ legacy + exploiter le gradient (BPTT in-world)
- fichiers_possedes: tools/substrate_world_ab.py, tools/torch_*_probe.py
- memoire: sota-gap-substrate.md
- legacy_edr: 134,135,137,138,139,140,141,143,144,145
- frontiere_courante: BPTT fenêtré in-world (persister le graphe K ticks)
- ponts_actifs: [BIND (portage means→ends), MEM (BPTT-mémoire)]
- filiation: —

### BIND — Crédit compositionnel & means→ends
- statut: actif (résolu sur proxy → portage)
- couche: Substrat/Cognition
- question_phare: Cracker le means→ends conditionnel
- fichiers_possedes: tools/substrate_ab_compositional.py
- memoire: coop-competence-is-population-property.md
- legacy_edr: 128,129,130,131,132,133,136,149
- frontiere_courante: porter la recette (gate + anti-saturation) en substrat torch-prod
- ponts_actifs: [SUB (portage)]
- filiation: —

### MEM — Mémoire
- statut: dormant (Partie A close)
- couche: Substrat
- question_phare: La mémoire paie-t-elle, et quand
- fichiers_possedes: —
- memoire: memory-architecture-audit.md
- legacy_edr: 062,064,067,120,123
- frontiere_courante: BPTT-mémoire in-world (pont SUB)
- ponts_actifs: [SUB]
- filiation: —

### WLD — Demande d'intelligence & plancher
- statut: actif
- couche: Monde
- question_phare: Le monde exige-t-il l'intelligence (métrique life_score)
- fichiers_possedes: (commons sim de monde — intendant)
- memoire: s2-world-demand-thread.md, world-floor-survivability-gate.md
- legacy_edr: 085,124
- frontiere_courante: réparer le gate de cohérence life_score (survivant≠marqueur)
- ponts_actifs: —
- filiation: —

### CRAFT — Craft, rétention & outils
- statut: actif
- couche: Monde
- question_phare: Pourquoi le craft n'est pas retenu
- fichiers_possedes: tools/craft_*.py
- memoire: world-floor-survivability-gate.md
- legacy_edr: 125,127
- frontiere_courante: mécanisme de rétention du craft en cohorte fixe
- ponts_actifs: —
- filiation: —

### NAV — Navigation & économie d'énergie
- statut: dormant
- couche: Monde
- question_phare: Le mur de navigation (approche vs capture)
- fichiers_possedes: tools/lewis_survival_sweep.py, tools/nav_*.py
- memoire: lewis-energy-economy-wall.md
- legacy_edr: 090,107,110,113,114
- frontiere_courante: mur = politique/substrat (pont SUB) ; dette knob disable_repro
- ponts_actifs: [SUB]
- filiation: —

### FAM — Famine, stockage & spécialisation
- statut: dormant
- couche: Monde
- question_phare: Émergence de spécialisation world-spécifique
- fichiers_possedes: tools/famine_harshness_probe.py, tools/cross_world_transfer.py
- memoire: fil-directeur-agi-gates.md
- legacy_edr: 129,130
- frontiere_courante: durcir réfuté → levier = substrat/moteur (pont SUB)
- ponts_actifs: [SUB]
- filiation: —

### COG — Types d'intelligence & organes cognitifs
- statut: partiellement clos (ToM clos, dreaming réfuté)
- couche: Cognition
- question_phare: Quels types émergent / sont dissociables
- fichiers_possedes: tools/tom_probe.py, tools/anticipation_bench.py
- memoire: intelligence-typing-flat-connectome.md, dreaming-organ-not-dead.md, planner-depth1-refuted.md
- legacy_edr: 093,094,095,150,151
- frontiere_courante: —
- ponts_actifs: —
- filiation: —

### INFRA — Instruments, méthodo & reproductibilité
- statut: continu
- couche: Instruments
- question_phare: Garder les bancs sains et reproductibles
- fichiers_possedes: tools/consolidate_records.py, tools/cartography.py (Partie 2)
- memoire: biosphere-ambient-memory-nonrepro.md, multiprocess-experiment-hazards.md, parallel-sessions-shared-tree.md
- legacy_edr: —
- frontiere_courante: cartographe automatique (Partie 2)
- ponts_actifs: [tous]
- filiation: —

### PROD — Migration prod, Backend & Frontend
- statut: actif
- couche: Prod
- question_phare: Porter les recettes validées en prod
- fichiers_possedes: (roadmap BACKEND.md / FRONTEND.md)
- memoire: sweep-view-backend-patch-pending.md
- legacy_edr: —
- frontiere_courante: embarquer gate+anti-saturation (BIND) et adaptateur torch (SUB) en prod
- ponts_actifs: [BIND, SUB]
- filiation: —

## Doublons legacy connus (à nettoyer de façon coordonnée, cf. cartographe)

EDR-093, EDR-094, EDR-100, EDR-105, EDR-113 : deux records distincts partagent le numéro (collisions
de sessions //). Tolérés (legacy cohabite) ; signalés en `warnings` par consolidate.
```

- [ ] **Step 2: Ajouter le pointeur dans SCIENCE.md**

Dans `docs/roadmap/SCIENCE.md`, juste sous le titre `## Statut des Vagues (pointeurs)`, insérer la ligne :

```markdown
- 🗺️ **Territoires de recherche & convention d'IDs** : `docs/roadmap/SPECIALITES.md` (registre vivant, source de vérité de la spécialisation).
```

- [ ] **Step 3: Vérifier que le registre ne casse pas consolidate**

Run: `PYTHONPATH=. python tools/consolidate_records.py`
Expected: `records=... problemes=0` (le registre est dans docs/roadmap/, hors des dossiers scannés SDR/ADR/EDR/REF → aucun impact).

- [ ] **Step 4: Commit**

```bash
git add docs/roadmap/SPECIALITES.md docs/roadmap/SCIENCE.md
git commit -m "docs(territoires): registre vivant SPECIALITES.md + convention IDs préfixés (Partie 1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Recensement par préfixe dans consolidate

**Files:**
- Modify: `tools/consolidate_records.py` (ajouter `_prefix_of` ; `prefix_counts` dans `main`)
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: `scan_records() -> list[dict]` (records avec clé `id`).
- Produces: `_prefix_of(rec_id: str|None) -> str` (préfixe de territoire : `SUB`/`REF`/`LEGACY`) ; payload de `main` gagne la clé `prefix_counts: dict[str,int]`.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_consolidate_records.py` :

```python
def test_prefix_of_classifies_ids():
    from tools.consolidate_records import _prefix_of
    assert _prefix_of("EDR-SUB-012") == "SUB"
    assert _prefix_of("EDR-BIND-003") == "BIND"
    assert _prefix_of("EDR-140") == "LEGACY"
    assert _prefix_of("SDR-G1") == "LEGACY"
    assert _prefix_of("REF-NEAT-2002") == "REF"
    assert _prefix_of(None) == "LEGACY"


def test_main_payload_has_prefix_counts(tmp_path):
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    (tmp_path / "results").mkdir()
    _write(tmp_path / "docs" / "EDR" / "140_Legacy.md", "# legacy\n")
    _write(tmp_path / "docs" / "EDR" / "SUB-012_New.md",
           "---\nid: EDR-SUB-012\ntype: EDR\ntitle: t\nstatus: validated\n---\n")
    from tools.consolidate_records import main
    main(["--root", str(tmp_path)])
    out = json.loads((tmp_path / "results" / "records_graph.json").read_text(encoding="utf-8"))
    assert out["prefix_counts"]["LEGACY"] == 1
    assert out["prefix_counts"]["SUB"] == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_consolidate_records.py::test_prefix_of_classifies_ids tests/test_consolidate_records.py::test_main_payload_has_prefix_counts -v`
Expected: FAIL (`_prefix_of` inexistant ; `prefix_counts` absent du payload).

- [ ] **Step 3: Implémenter `_prefix_of` et le recensement**

Dans `tools/consolidate_records.py`, ajouter la fonction juste après `parse_record` (avant `scan_records`) :

```python
def _prefix_of(rec_id) -> str:
    """Préfixe de territoire d'un id. `EDR-SUB-012` -> 'SUB' ; `EDR-140` -> 'LEGACY' ;
    `SDR-G1` -> 'LEGACY' ; `REF-NEAT-2002` -> 'REF'. Alimente le recensement du cartographe."""
    if not rec_id:
        return "LEGACY"
    parts = str(rec_id).split("-")
    if parts[0] == "REF":
        return "REF"
    if len(parts) >= 3 and parts[1].isalpha():   # EDR-<PREFIX>-<num>
        return parts[1]
    return "LEGACY"
```

Ajouter l'import en tête (`from collections import Counter`) — sous `import argparse` :

```python
from collections import Counter
```

Dans `main`, après `roadmap = roadmap_state(records)`, calculer le recensement et l'ajouter au payload :

```python
    prefix_counts = dict(Counter(_prefix_of(r["id"]) for r in records))
```

et modifier la ligne `payload = {...}` pour inclure la clé :

```python
    payload = {"graph": graph, "roadmap": roadmap, "problems": problems,
               "prefix_counts": prefix_counts}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_consolidate_records.py -q`
Expected: PASS (tous, y compris `test_main_exits_zero_on_clean_repo`).

- [ ] **Step 5: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(consolidate): recensement par préfixe (matière du cartographe)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Détection de doublons d'id en warnings non-bloquants

**Files:**
- Modify: `tools/consolidate_records.py` (ajouter `find_duplicate_ids` ; `warnings` dans `main`, affichage)
- Test: `tests/test_consolidate_records.py`

**Interfaces:**
- Consumes: `scan_records() -> list[dict]` (records avec `id` et `file`).
- Produces: `find_duplicate_ids(records: list[dict]) -> list[dict]` (chaque élément `{"id": str, "files": list[str]}`, trié) ; payload de `main` gagne la clé `warnings: list[dict]`. Le code de retour de `main` reste `1 if problems else 0` (les warnings ne bloquent pas).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_consolidate_records.py` :

```python
def test_find_duplicate_ids_flags_collisions():
    from tools.consolidate_records import find_duplicate_ids
    recs = [
        _rec("EDR-093", "EDR"), _rec("EDR-093", "EDR"),
        _rec("EDR-140", "EDR"),
    ]
    recs[0]["file"] = "docs/EDR/093_A.md"
    recs[1]["file"] = "docs/EDR/093_B.md"
    dups = find_duplicate_ids(recs)
    assert len(dups) == 1
    assert dups[0]["id"] == "EDR-093"
    assert dups[0]["files"] == ["docs/EDR/093_A.md", "docs/EDR/093_B.md"]


def test_find_duplicate_ids_empty_when_unique():
    from tools.consolidate_records import find_duplicate_ids
    assert find_duplicate_ids([_rec("EDR-140", "EDR"), _rec("EDR-141", "EDR")]) == []


def test_main_reports_warnings_without_failing(tmp_path):
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    (tmp_path / "results").mkdir()
    # deux fichiers legacy qui résolvent au même id EDR-093
    _write(tmp_path / "docs" / "EDR" / "093_First.md", "# a\n")
    _write(tmp_path / "docs" / "EDR" / "093_Second.md", "# b\n")
    from tools.consolidate_records import main
    rc = main(["--root", str(tmp_path)])
    assert rc == 0   # doublon = WARNING, pas un problème bloquant
    out = json.loads((tmp_path / "results" / "records_graph.json").read_text(encoding="utf-8"))
    assert any(w["id"] == "EDR-093" for w in out["warnings"])
    assert out["problems"] == []
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_consolidate_records.py::test_find_duplicate_ids_flags_collisions tests/test_consolidate_records.py::test_main_reports_warnings_without_failing -v`
Expected: FAIL (`find_duplicate_ids` inexistant ; `warnings` absent du payload).

- [ ] **Step 3: Implémenter `find_duplicate_ids` et les warnings**

Dans `tools/consolidate_records.py`, ajouter la fonction après `validate_graph` :

```python
def find_duplicate_ids(records: list[dict]) -> list[dict]:
    """Ids apparaissant plus d'une fois = collision de sessions parallèles.
    Retourne [{"id", "files":[...]}] trié. Signalé en WARNING NON BLOQUANT : le legacy
    cohabite (5 doublons connus 093/094/100/105/113), et les EDR préfixés ne collisionnent
    jamais par construction. Le cartographe (Partie 2) exploite cette liste pour proposer un
    nettoyage coordonné."""
    from collections import defaultdict
    by_id: dict = defaultdict(list)
    for r in records:
        by_id[r["id"]].append(r["file"])
    return [{"id": i, "files": sorted(fs)} for i, fs in sorted(by_id.items()) if len(fs) > 1]
```

Dans `main`, après le calcul de `prefix_counts`, ajouter :

```python
    warnings = find_duplicate_ids(records)
```

Modifier `payload` pour inclure `warnings` :

```python
    payload = {"graph": graph, "roadmap": roadmap, "problems": problems,
               "prefix_counts": prefix_counts, "warnings": warnings}
```

Après la boucle qui imprime les `problems`, ajouter l'affichage des warnings (sans changer le `return`) :

```python
    for w in warnings:
        print(f"  [warning] doublon d'id {w['id']} : {', '.join(w['files'])}")
```

Le `return 1 if problems else 0` reste inchangé.

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_consolidate_records.py -q`
Expected: PASS (tous). En particulier `test_main_exits_zero_on_clean_repo` reste vert (les 5 doublons legacy sont des warnings, pas des problèmes).

- [ ] **Step 5: Vérifier sur le vrai repo (warnings peuplés, rc=0)**

Run: `PYTHONPATH=. python tools/consolidate_records.py; echo "rc=$?"`
Expected: `problemes=0`, `rc=0`, et 5 lignes `[warning] doublon d'id EDR-093/094/100/105/113 …`.

- [ ] **Step 6: Commit**

```bash
git add tools/consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat(consolidate): warnings non-bloquants sur doublons d'id (collisions //)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Auto-revue (couverture du spec Partie 1)

- Registre vivant `SPECIALITES.md` (§1.3) → Task 1. ✔ (convention IDs §1.4, commons/intendants §1.1, évolution §1.2 documentées dans l'en-tête + sections).
- IDs préfixés parsés (§1.6, cas frontmatter) → déjà supporté par `parse_record` (vérifié) ; recensement `_prefix_of` → Task 2. ✔
- Doublon d'id signalé (§1.6) → Task 3, en `warnings` (décision utilisateur : non-bloquant Partie 1). ✔
- Compte par préfixe pour le cartographe (§1.6, §2.1) → Task 2 (`prefix_counts`). ✔
- Legacy intouché (non-objectif) → aucune tâche ne renomme/renumérote. ✔
- Collaboration `also:` (§1.5) → convention documentée dans le registre (Task 1) ; le champ est optionnel et déjà toléré par le parser YAML (ignoré s'il n'est pas dans `rec`). Pas de code requis en Partie 1. ✔

## Hors périmètre (Partie 2, plan séparé)

`tools/cartography.py`, le dossier `docs/roadmap/cartographie/`, le pass agent sémantique, le nettoyage coordonné des 5 doublons legacy.
