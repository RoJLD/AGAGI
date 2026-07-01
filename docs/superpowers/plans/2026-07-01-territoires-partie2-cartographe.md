# Territoires de recherche — Partie 2 (Cartographe automatique) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bâtir le cartographe : un script déterministe (`tools/cartography.py`) qui moissonne le corpus (registre SPECIALITES.md + EDR + mémoire + sortie consolidate) en un JSON de signaux reproductible (gaps, verdicts ouverts, territoires dormants, termes-verrou, orphelins), plus le prompt de la passe agent qui l'interprète en rapport — sans jamais éditer le registre.

**Architecture:** Moteur HYBRIDE. La couche déterministe (ce plan, Tasks 1-6) réutilise `scan_records`/`_prefix_of` de `tools/consolidate_records.py` (Partie 1), parse les sections territoire de `SPECIALITES.md`, et calcule 6 signaux. La couche sémantique (Task 7) est un PROMPT documenté que l'humain lance à la demande pour produire un rapport. Détection = automatique ; création/scission/fusion de territoire = approuvée par l'humain, qui seul édite le registre.

**Tech Stack:** Python 3, pytest, stdlib uniquement (`re`, `json`, `unicodedata`, `datetime`, `collections`). Aucune dépendance nouvelle. Docs Markdown.

## Global Constraints

- **Script déterministe pur** : `tools/cartography.py` n'appelle AUCUN LLM et AUCUN réseau. La couche agent est un prompt Markdown séparé (Task 7).
- **Réutilisation, pas duplication** : importer `scan_records` et `_prefix_of` depuis `tools.consolidate_records` (Partie 1, sur main). Ne pas réécrire le scan des records.
- **Lecture seule sur le registre** : le cartographe LIT `SPECIALITES.md` ; il ne l'écrit JAMAIS. Toute naissance/scission/fusion de territoire = édition humaine approuvée.
- **Heuristiques advisory** : lister-et-laisser-trancher. Aucun signal ne supprime, masque ni renomme un record. Faux positifs tolérés (l'agent affine, l'humain approuve).
- **Signaux reproductibles** : à `--date` fixé et corpus fixé, le JSON est identique. `datetime.date.today()` seulement comme défaut de `--date`.
- **Legacy intouché** : aucun fichier `docs/EDR/NNN_*.md` modifié.
- **TDD** (RED→GREEN), **commits path-scoped**, un commit par tâche, **français**. Tests lancés avec `PYTHONPATH=.`.
- Fin de message de commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Structure des fichiers

- CRÉÉ `tools/cartography.py` — moisson déterministe. Une fonction pure par signal + `main()` d'assemblage.
- CRÉÉ `tests/test_cartography.py` — tests unitaires (fonctions pures) + intégration (`main` sur mini-repo tmp).
- CRÉÉ `docs/roadmap/cartographie/README.md` — rôle, comment lancer, boucle d'approbation, cadence.
- CRÉÉ `docs/roadmap/cartographie/PROMPT_CARTOGRAPHE.md` — le prompt de la passe agent + le gabarit de rapport.

Les fonctions pures (Tasks 1-5) sont testées en isolation ; `main` (Task 6) les assemble et écrit `signals-<date>.json`. Task 7 est documentaire.

**Faits du corpus (ancrage, vérifiés)** — utiles pour les fixtures de test :
- `docs/EDR/` : ~145 fichiers ; ~22 ont un frontmatter YAML (`id/type/title/status/gate/verdict/tests`), les autres sont juste `NNN_*.md` sans frontmatter (record toléré non lié).
- `verdict:` frontmatter : mot-clé court (`INCONCLUSIF`, `EXIGE`, `NEUTRE`…) OU paragraphe quoté. `status:` ∈ {`validated`, `accepted`, `refuted`}. Seul `INCONCLUSIF` apparaît en frontmatter ; `VOID`/`INDÉTERMINÉ` vivent dans les titres/corps.
- Marqueurs de leads réels : « piste suivante », « Prochain chantier », « prochaine piste », « prochain levier », « piste principale/prioritaire », « piste amont », « actionnable ».
- Termes-verrou réels : verrou / mur / RÉFUTÉ / bassin / plancher (avec variantes accentuées et fléchies : verrouillent, réfutée…).
- Section territoire de `SPECIALITES.md` : `### CODE — Label` puis lignes `- champ: valeur` (`statut`, `couche`, `question_phare`, `fichiers_possedes`, `memoire`, `legacy_edr`, `frontiere_courante`, `ponts_actifs`, `filiation`). `legacy_edr` = numéros séparés par virgules, ou commençant par `—` (vide/annoté).

---

### Task 1: Parser des territoires de `SPECIALITES.md`

**Files:**
- Create: `tools/cartography.py`
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: rien (parse du texte brut).
- Produces: `parse_territories(text: str) -> list[dict]` — chaque territoire `{"code": str, "label": str, "legacy_edr": list[int], "statut": str, "couche": str, "question_phare": str, ...}` (les champs `- clé: valeur` deviennent des clés ; `legacy_edr` est une `list[int]`, vide si la valeur commence par `—`).

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_cartography.py` avec :

```python
import os
import json

import pytest

from tools.cartography import parse_territories


SPEC_SNIPPET = """# Registre

## Territoires

### SUB — Substrat & Moteur d'apprentissage
- statut: actif
- couche: Substrat/Moteur
- question_phare: Moteur torch ≥ legacy
- fichiers_possedes: tools/substrate_world_ab.py
- legacy_edr: 134,135,137
- ponts_actifs: [BIND]
- filiation: —

### FAM — Famine
- statut: dormant
- couche: Monde
- question_phare: Spécialisation
- legacy_edr: — (fil suivi en mémoire, 129_*/130_* = BIND)
- filiation: —

## Doublons legacy connus

EDR-093 ...
"""


def test_parse_territories_extracts_fields():
    terrs = parse_territories(SPEC_SNIPPET)
    assert [t["code"] for t in terrs] == ["SUB", "FAM"]
    sub = terrs[0]
    assert sub["label"].startswith("Substrat")
    assert sub["statut"] == "actif"
    assert sub["question_phare"] == "Moteur torch ≥ legacy"
    assert sub["legacy_edr"] == [134, 135, 137]


def test_parse_territories_empty_legacy_when_dash():
    terrs = parse_territories(SPEC_SNIPPET)
    fam = terrs[1]
    # valeur commençant par — : legacy_edr vide MÊME si le texte contient 129/130
    assert fam["legacy_edr"] == []
    assert fam["statut"] == "dormant"


def test_parse_territories_stops_at_next_h2():
    terrs = parse_territories(SPEC_SNIPPET)
    # la section "## Doublons" ne crée pas de territoire
    assert len(terrs) == 2
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -v`
Expected: FAIL (`ModuleNotFoundError: tools.cartography` ou `parse_territories` inexistant).

- [ ] **Step 3: Créer `tools/cartography.py` avec l'entête et `parse_territories`**

Créer `tools/cartography.py` :

```python
"""Cartographe — moisson déterministe de signaux sur le corpus de recherche AGAGI.

Lit le registre (docs/roadmap/SPECIALITES.md), les records (via consolidate),
la mémoire, et extrait des SIGNAUX (gaps, verdicts ouverts, territoires dormants,
termes-verrou, orphelins) dans un JSON reproductible. Pur : aucun LLM, aucun réseau.
La passe sémantique (interprétation) est un prompt séparé (docs/roadmap/cartographie/).
Design : docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md (Partie 2)."""
import os
import re
import sys
import json
import argparse
import unicodedata
from collections import Counter
from datetime import date as _date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.consolidate_records import scan_records, _prefix_of


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    """Majuscule + sans accents : pour comparer INDÉTERMINÉ == INDETERMINE, etc."""
    return _strip_accents(s).upper()


_TERR_HEAD = re.compile(r"^###\s+([A-Z]+)\s+[—-]\s+(.*)$")
_FIELD = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")


def parse_territories(text: str) -> list[dict]:
    """Parse les sections territoire de SPECIALITES.md. Chaque `### CODE — Label`
    suivi de lignes `- champ: valeur` -> dict. `legacy_edr` -> list[int]
    (vide si la valeur commence par '—', même si le texte contient des chiffres)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    terrs: list[dict] = []
    cur = None
    for line in text.split("\n"):
        mh = _TERR_HEAD.match(line)
        if mh:
            cur = {"code": mh.group(1), "label": mh.group(2).strip(), "legacy_edr": []}
            terrs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("## "):        # section suivante -> hors zone territoire
            cur = None
            continue
        mf = _FIELD.match(line)
        if mf:
            key, val = mf.group(1), mf.group(2).strip()
            if key == "legacy_edr":
                cur["legacy_edr"] = ([int(n) for n in re.findall(r"\d{1,3}", val)]
                                    if not val.startswith("—") else [])
            else:
                cur[key] = val
    return terrs
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py
git commit -m "feat(cartographie): parser des territoires de SPECIALITES.md (fondation)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Orphelins — EDR non rattachés à un territoire

**Files:**
- Modify: `tools/cartography.py` (ajouter `_edr_number`, `territory_of`, `orphan_edrs`)
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: `parse_territories` (Task 1) ; `_prefix_of` (consolidate).
- Produces:
  - `_edr_number(rec_id) -> int | None` : `'EDR-140'->140`, `'EDR-093'->93`, `'EDR-SUB-012'->None`, `None->None`.
  - `territory_of(edr_num, territories) -> str | None` : code du territoire dont `legacy_edr` contient le numéro, sinon `None`.
  - `orphan_edrs(records, territories) -> list[dict]` : `[{"id", "file", "reason"}]`. Legacy orphelin SEULEMENT si son numéro est strictement supérieur au max de tous les `legacy_edr` connus (auto-calibré, « plus récent que tout le registre ») ; préfixé orphelin si son préfixe n'est pas un code de territoire connu (hors REF).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_cartography.py` :

```python
def _rec(id, type="EDR", file="f.md"):
    return {"id": id, "type": type, "file": file}


TERRS = [
    {"code": "SUB", "label": "S", "legacy_edr": [134, 135]},
    {"code": "BIND", "label": "B", "legacy_edr": [128, 129]},
]


def test_edr_number_parsing():
    from tools.cartography import _edr_number
    assert _edr_number("EDR-140") == 140
    assert _edr_number("EDR-093") == 93
    assert _edr_number("EDR-SUB-012") is None
    assert _edr_number(None) is None


def test_territory_of_maps_by_legacy():
    from tools.cartography import territory_of
    assert territory_of(134, TERRS) == "SUB"
    assert territory_of(128, TERRS) == "BIND"
    assert territory_of(999, TERRS) is None
    assert territory_of(None, TERRS) is None


def test_orphan_edrs_recent_legacy_and_unknown_prefix():
    from tools.cartography import orphan_edrs
    records = [
        _rec("EDR-134"),                 # mappé SUB -> pas orphelin
        _rec("EDR-100"),                 # legacy non mappé MAIS < max(135) -> pas orphelin
        _rec("EDR-200"),                 # legacy > max mappé (135) -> ORPHELIN
        _rec("EDR-SUB-012"),             # préfixe connu -> pas orphelin
        _rec("EDR-ZZZ-001"),             # préfixe inconnu -> ORPHELIN
        _rec("REF-NEAT-2002", type="REF"),  # pas un EDR -> ignoré
    ]
    orphans = orphan_edrs(records, TERRS)
    ids = sorted(o["id"] for o in orphans)
    assert ids == ["EDR-200", "EDR-ZZZ-001"]
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py::test_edr_number_parsing tests/test_cartography.py::test_territory_of_maps_by_legacy tests/test_cartography.py::test_orphan_edrs_recent_legacy_and_unknown_prefix -v`
Expected: FAIL (`_edr_number`/`territory_of`/`orphan_edrs` inexistants).

- [ ] **Step 3: Implémenter**

Dans `tools/cartography.py`, ajouter après `parse_territories` :

```python
def _edr_number(rec_id) -> int | None:
    """Numéro legacy d'un id EDR. 'EDR-140'->140, 'EDR-093'->93 ;
    'EDR-SUB-012' (préfixé) -> None ; None -> None."""
    if not rec_id:
        return None
    m = re.fullmatch(r"EDR-(\d{1,3})", str(rec_id))
    return int(m.group(1)) if m else None


def territory_of(edr_num, territories) -> str | None:
    """Code du territoire dont legacy_edr contient ce numéro, sinon None."""
    if edr_num is None:
        return None
    for t in territories:
        if edr_num in t.get("legacy_edr", []):
            return t["code"]
    return None


def orphan_edrs(records, territories) -> list[dict]:
    """EDR non rattachables. Legacy : orphelin si son numéro > max des legacy_edr connus
    (plus récent que tout ce que le registre mappe). Préfixé : orphelin si son préfixe
    n'est pas un territoire connu (REF exclu). Advisory (aucune suppression)."""
    codes = {t["code"] for t in territories}
    mapped: set = set()
    for t in territories:
        mapped.update(t.get("legacy_edr", []))
    max_mapped = max(mapped) if mapped else 0
    out: list[dict] = []
    for r in records:
        if r.get("type") != "EDR":
            continue
        num = _edr_number(r["id"])
        if num is not None:
            if num not in mapped and num > max_mapped:
                out.append({"id": r["id"], "file": r.get("file"),
                            "reason": "legacy récent non mappé"})
        else:
            prefix = _prefix_of(r["id"])
            if prefix not in codes and prefix != "REF":
                out.append({"id": r["id"], "file": r.get("file"),
                            "reason": f"préfixe {prefix} inconnu"})
    return out
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py
git commit -m "feat(cartographie): détection des EDR orphelins (auto-calibrée sur le registre)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Verdicts ouverts (non tranchés)

**Files:**
- Modify: `tools/cartography.py` (ajouter `unresolved_verdicts`)
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: `_norm` (Task 1).
- Produces: `unresolved_verdicts(records) -> list[dict]` : `[{"id", "file", "marker", "verdict"}]` pour les EDR dont le champ `verdict` OU le `title` porte un marqueur non tranché (`INCONCLUSIF`/`INCONCLUSIVE`/`VOID`/`INDÉTERMINÉ`), comparaison sans accents/casse.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_cartography.py` :

```python
def test_unresolved_verdicts_matches_verdict_and_title():
    from tools.cartography import unresolved_verdicts
    records = [
        {"id": "EDR-121", "type": "EDR", "file": "a.md",
         "title": "Stockage INCONCLUSIVE", "verdict": "INCONCLUSIF"},
        {"id": "EDR-151", "type": "EDR", "file": "b.md",
         "title": "ToM comportementale INDÉTERMINÉ", "verdict": None},
        {"id": "EDR-112", "type": "EDR", "file": "c.md",
         "title": "Le monde exige", "verdict": "EXIGE"},
        {"id": "SDR-G1", "type": "SDR", "file": "d.md",
         "title": "porte VOID", "verdict": None},   # pas un EDR -> ignoré
    ]
    res = unresolved_verdicts(records)
    ids = sorted(r["id"] for r in res)
    assert ids == ["EDR-121", "EDR-151"]
    by_id = {r["id"]: r for r in res}
    assert by_id["EDR-121"]["marker"] == "INCONCLUSIF"
    assert by_id["EDR-151"]["marker"] == "INDETERMINE"
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py::test_unresolved_verdicts_matches_verdict_and_title -v`
Expected: FAIL (`unresolved_verdicts` inexistant).

- [ ] **Step 3: Implémenter**

Dans `tools/cartography.py`, ajouter après `orphan_edrs` :

```python
_UNRESOLVED = ("INCONCLUSIF", "INCONCLUSIVE", "VOID", "INDETERMINE")


def unresolved_verdicts(records) -> list[dict]:
    """EDR dont le verdict OU le titre porte un marqueur non tranché
    (INCONCLUSIF/VOID/INDÉTERMINÉ), comparaison sans accents ni casse. Advisory."""
    out: list[dict] = []
    for r in records:
        if r.get("type") != "EDR":
            continue
        hay = _norm(r.get("verdict") or "") + " " + _norm(r.get("title") or "")
        marker = next((m for m in _UNRESOLVED if m in hay), None)
        if marker:
            out.append({"id": r["id"], "file": r.get("file"),
                        "marker": marker, "verdict": r.get("verdict")})
    return out
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py
git commit -m "feat(cartographie): signal des verdicts ouverts (INCONCLUSIF/VOID/INDÉTERMINÉ)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Leads pendants (pistes ouvertes)

**Files:**
- Modify: `tools/cartography.py` (ajouter `pending_leads`)
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: `_norm` (Task 1).
- Produces: `pending_leads(files) -> list[dict]` où `files` est une `list[tuple[str, str]]` de `(relpath, texte)`. Retourne `[{"file", "line", "marker", "snippet"}]` — une entrée par ligne portant un marqueur de piste (première correspondance retenue), `snippet` = ligne strippée tronquée à 200 caractères.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_cartography.py` :

```python
def test_pending_leads_scans_markers_case_insensitive():
    from tools.cartography import pending_leads
    files = [
        ("docs/EDR/131_x.md",
         "Contexte.\nintervention précoce (warm-start) → c'est la piste suivante directe.\nFin."),
        ("memory/edr090.md", "Le prochain levier est l'adaptation du substrat."),
        ("docs/EDR/010_y.md", "Rien à signaler ici."),
    ]
    leads = pending_leads(files)
    assert len(leads) == 2
    by_file = {l["file"]: l for l in leads}
    assert by_file["docs/EDR/131_x.md"]["line"] == 2
    assert by_file["docs/EDR/131_x.md"]["marker"] == "piste suivante"
    assert by_file["memory/edr090.md"]["marker"] == "prochain levier"
    assert "warm-start" in by_file["docs/EDR/131_x.md"]["snippet"]
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py::test_pending_leads_scans_markers_case_insensitive -v`
Expected: FAIL (`pending_leads` inexistant).

- [ ] **Step 3: Implémenter**

Dans `tools/cartography.py`, ajouter après `unresolved_verdicts` :

```python
_LEAD_MARKERS = ("piste suivante", "prochain chantier", "prochaine piste",
                 "prochain levier", "prochaine sonde", "prochain build",
                 "piste principale", "piste prioritaire", "piste amont",
                 "actionnable")


def pending_leads(files) -> list[dict]:
    """Scanne des (relpath, texte) pour des marqueurs de piste ouverte. Retourne
    {file, line, marker, snippet}. Une entrée par ligne (1re correspondance).
    Sans accents ni casse. Advisory (l'agent croise avec l'aval)."""
    markers = [(_norm(m), m) for m in _LEAD_MARKERS]
    out: list[dict] = []
    for relpath, text in files:
        for i, raw in enumerate((text or "").replace("\r\n", "\n").split("\n"), 1):
            hn = _norm(raw)
            for mn, m in markers:
                if mn in hn:
                    out.append({"file": relpath, "line": i, "marker": m,
                                "snippet": raw.strip()[:200]})
                    break
    return out
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py
git commit -m "feat(cartographie): signal des leads pendants (marqueurs de piste)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Termes-verrou (bottlenecks) par territoire

**Files:**
- Modify: `tools/cartography.py` (ajouter `lock_term_counts`)
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: `_norm`, `territory_of` (Tasks 1-2).
- Produces: `lock_term_counts(edr_texts, territories) -> dict` où `edr_texts` est une `list[dict]` de `{"num": int|None, "prefix": str, "text": str}`. Retourne `{"per_territory": {code: int}, "per_term": {term: {"total": int, "territories": [codes triés], "systemic": bool}}}`. `systemic` = vrai si le terme touche ≥3 territoires. Comptage par racine avec bornes de mot (voir patterns) pour éviter les faux positifs (« murmure », etc.).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_cartography.py` :

```python
def test_lock_term_counts_by_territory_and_systemic():
    from tools.cartography import lock_term_counts
    territories = [
        {"code": "SUB", "legacy_edr": [134]},
        {"code": "BIND", "legacy_edr": [128]},
        {"code": "NAV", "legacy_edr": [110]},
    ]
    edr_texts = [
        {"num": 134, "prefix": "LEGACY", "text": "le VERROU tient, les seeds verrouillent"},
        {"num": 128, "prefix": "LEGACY", "text": "hypothèse RÉFUTÉE ; c'est un bassin"},
        {"num": 110, "prefix": "LEGACY", "text": "au plancher, le mur reste ; réfutée aussi"},
        {"num": 999, "prefix": "LEGACY", "text": "un murmure sans verrou-mot"},  # non mappé
    ]
    res = lock_term_counts(edr_texts, territories)
    # "verrou" (VERROU + verrouillent) compte 2 sur SUB
    assert res["per_territory"]["SUB"] == 2
    # "réfuté" apparaît sur BIND et NAV -> 2 territoires, pas systémique (<3)
    assert res["per_term"]["refute"]["systemic"] is False
    assert sorted(res["per_term"]["refute"]["territories"]) == ["BIND", "NAV"]
    # "murmure" ne doit PAS compter comme "mur"
    assert "mur" not in res["per_territory"] or res["per_term"]["mur"]["total"] == 1
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py::test_lock_term_counts_by_territory_and_systemic -v`
Expected: FAIL (`lock_term_counts` inexistant).

- [ ] **Step 3: Implémenter**

Dans `tools/cartography.py`, ajouter après `pending_leads` :

```python
# Racines avec bornes de mot : capturent les formes fléchies/accentuées
# (verrouillent, réfutée, réfutent) sans faux positifs (murmure, muraille).
_LOCK_PATTERNS = {
    "verrou": r"\bVERROU",
    "mur": r"\bMURS?\b",
    "refute": r"\bREFUT",
    "bassin": r"\bBASSIN",
    "plancher": r"\bPLANCH",
}


def lock_term_counts(edr_texts, territories) -> dict:
    """Compte les termes-verrou par territoire (mappé via territory_of/préfixe) et
    transverse. edr_texts: [{num, prefix, text}]. `systemic` = terme dans ≥3 territoires."""
    per_territory: dict = {}
    per_term = {t: {"total": 0, "territories": set()} for t in _LOCK_PATTERNS}
    compiled = {t: re.compile(p) for t, p in _LOCK_PATTERNS.items()}
    for e in edr_texts:
        code = territory_of(e.get("num"), territories)
        if code is None and e.get("prefix") not in (None, "LEGACY", "REF"):
            code = e["prefix"]
        hay = _norm(e.get("text") or "")
        for term, rx in compiled.items():
            c = len(rx.findall(hay))
            if not c:
                continue
            per_term[term]["total"] += c
            if code:
                per_territory[code] = per_territory.get(code, 0) + c
                per_term[term]["territories"].add(code)
    per_term_out = {t: {"total": v["total"],
                        "territories": sorted(v["territories"]),
                        "systemic": len(v["territories"]) >= 3}
                    for t, v in per_term.items()}
    return {"per_territory": per_territory, "per_term": per_term_out}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py
git commit -m "feat(cartographie): signal des termes-verrou par territoire (bottlenecks)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Assemblage `main()` + dormance + JSON de signaux

**Files:**
- Modify: `tools/cartography.py` (ajouter `dormant_territories`, helpers de lecture, `main`)
- Test: `tests/test_cartography.py`

**Interfaces:**
- Consumes: toutes les fonctions Tasks 1-5 ; `scan_records`, `_prefix_of` (consolidate).
- Produces:
  - `dormant_territories(territories, k=30) -> list[dict]` : `[{"code", "statut", "dernier_edr", "gap", "dormant"}]` où `gap = max_legacy_global - max(legacy_edr du territoire)` et `dormant = gap >= k`.
  - `main(argv=None) -> int` : écrit `<out-dir>/signals-<date>.json` avec les clés `date`, `prefix_counts`, `dormant_territories`, `orphans`, `unresolved_verdicts`, `pending_leads`, `lock_terms` ; imprime un résumé ; retourne 0. Args : `--root`, `--memory-dir` (défaut None → mémoire ignorée), `--out-dir` (défaut `<root>/docs/roadmap/cartographie`), `--date` (défaut `date.today()`), `--dormant-gap` (défaut 30).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_cartography.py` :

```python
def test_dormant_territories_flags_by_gap():
    from tools.cartography import dormant_territories
    terrs = [
        {"code": "SUB", "statut": "actif", "legacy_edr": [140, 145]},
        {"code": "NAV", "statut": "dormant", "legacy_edr": [90, 110]},
        {"code": "MEM", "statut": "dormant", "legacy_edr": []},
    ]
    res = {d["code"]: d for d in dormant_territories(terrs, k=30)}
    assert res["SUB"]["dormant"] is False and res["SUB"]["gap"] == 0
    assert res["NAV"]["dernier_edr"] == 110 and res["NAV"]["gap"] == 35
    assert res["NAV"]["dormant"] is True
    assert res["MEM"]["dernier_edr"] == 0 and res["MEM"]["dormant"] is True


def test_main_writes_signals_json(tmp_path):
    from tools.cartography import main
    # mini registre + mini corpus EDR
    (tmp_path / "docs" / "roadmap").mkdir(parents=True)
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    (tmp_path / "docs" / "roadmap" / "SPECIALITES.md").write_text(
        "## Territoires\n\n"
        "### SUB — Substrat\n- statut: actif\n- legacy_edr: 134,135\n- filiation: —\n\n"
        "### BIND — Binding\n- statut: actif\n- legacy_edr: 128\n- filiation: —\n\n"
        "## Fin\n", encoding="utf-8")
    # EDR mappé (corps avec un lead + un terme-verrou)
    (tmp_path / "docs" / "EDR" / "134_Sub.md").write_text(
        "# EDR 134\nLe VERROU tient. c'est la piste suivante directe.\n", encoding="utf-8")
    # EDR legacy récent non mappé (> 135) -> orphelin
    (tmp_path / "docs" / "EDR" / "200_New.md").write_text("# EDR 200\n", encoding="utf-8")
    # EDR avec verdict INCONCLUSIF (frontmatter)
    (tmp_path / "docs" / "EDR" / "121_Inc.md").write_text(
        "---\nid: EDR-121\ntype: EDR\ntitle: t\nstatus: accepted\nverdict: INCONCLUSIF\n---\n",
        encoding="utf-8")

    rc = main(["--root", str(tmp_path), "--date", "2026-07-01"])
    assert rc == 0
    out = json.loads((tmp_path / "docs" / "roadmap" / "cartographie"
                      / "signals-2026-07-01.json").read_text(encoding="utf-8"))
    assert out["date"] == "2026-07-01"
    assert set(out) >= {"date", "prefix_counts", "dormant_territories", "orphans",
                        "unresolved_verdicts", "pending_leads", "lock_terms"}
    assert any(o["id"] == "EDR-200" for o in out["orphans"])
    assert any(v["id"] == "EDR-121" for v in out["unresolved_verdicts"])
    assert any(l["marker"] == "piste suivante" for l in out["pending_leads"])
    assert out["lock_terms"]["per_territory"].get("SUB", 0) >= 1
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py::test_dormant_territories_flags_by_gap tests/test_cartography.py::test_main_writes_signals_json -v`
Expected: FAIL (`dormant_territories`/`main` inexistants).

- [ ] **Step 3: Implémenter**

Dans `tools/cartography.py`, ajouter après `lock_term_counts` :

```python
def dormant_territories(territories, k: int = 30) -> list[dict]:
    """Dormance par écart de records : gap = (max legacy global) - (max legacy du territoire).
    dormant si gap >= k. Proxy de récence sans dates (le numéro EDR est ~monotone)."""
    global_max = 0
    for t in territories:
        if t.get("legacy_edr"):
            global_max = max(global_max, max(t["legacy_edr"]))
    out: list[dict] = []
    for t in territories:
        last = max(t["legacy_edr"]) if t.get("legacy_edr") else 0
        gap = global_max - last
        out.append({"code": t["code"], "statut": t.get("statut", ""),
                    "dernier_edr": last, "gap": gap, "dormant": gap >= k})
    return out


def _read_texts(root, relpaths) -> list:
    """Lit (relpath, texte) pour chaque chemin relatif existant sous root."""
    files = []
    for rel in relpaths:
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                files.append((rel, fh.read()))
        except OSError:
            continue
    return files


def _memory_files(memory_dir) -> list:
    """Lit (memory/<nom>, texte) pour chaque .md du dossier mémoire, s'il existe."""
    if not memory_dir or not os.path.isdir(memory_dir):
        return []
    out = []
    for name in sorted(os.listdir(memory_dir)):
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(memory_dir, name), encoding="utf-8") as fh:
                out.append((f"memory/{name}", fh.read()))
        except OSError:
            continue
    return out


def build_signals(root, memory_dir, the_date, dormant_gap) -> dict:
    """Assemble tous les signaux (pur, sans écriture disque)."""
    with open(os.path.join(root, "docs", "roadmap", "SPECIALITES.md"),
              encoding="utf-8") as fh:
        territories = parse_territories(fh.read())

    records = scan_records(root)
    edr_records = [r for r in records if r.get("type") == "EDR"]
    edr_files = _read_texts(root, [r["file"] for r in edr_records])
    text_by_file = dict(edr_files)
    edr_texts = [{"num": _edr_number(r["id"]), "prefix": _prefix_of(r["id"]),
                  "text": text_by_file.get(r["file"], "")} for r in edr_records]
    mem_files = _memory_files(memory_dir)

    return {
        "date": the_date,
        "prefix_counts": dict(Counter(_prefix_of(r["id"]) for r in records)),
        "dormant_territories": dormant_territories(territories, dormant_gap),
        "orphans": orphan_edrs(records, territories),
        "unresolved_verdicts": unresolved_verdicts(records),
        "pending_leads": pending_leads(edr_files + mem_files),
        "lock_terms": lock_term_counts(edr_texts, territories),
    }


def main(argv=None) -> int:
    """Moissonne les signaux et écrit docs/roadmap/cartographie/signals-<date>.json."""
    ap = argparse.ArgumentParser(description="Cartographe — moisson de signaux déterministes.")
    ap.add_argument("--root", default=_ROOT)
    ap.add_argument("--memory-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--dormant-gap", type=int, default=30)
    args = ap.parse_args(argv)

    the_date = args.date or _date.today().isoformat()
    out_dir = args.out_dir or os.path.join(args.root, "docs", "roadmap", "cartographie")
    signals = build_signals(args.root, args.memory_dir, the_date, args.dormant_gap)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"signals-{the_date}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(signals, fh, ensure_ascii=False, indent=2)

    print(f"cartographie {the_date}: "
          f"orphelins={len(signals['orphans'])} "
          f"verdicts_ouverts={len(signals['unresolved_verdicts'])} "
          f"leads={len(signals['pending_leads'])} "
          f"-> {os.path.relpath(out_path, args.root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: PASS (tous).

- [ ] **Step 5: Vérifier sur le vrai repo**

Run: `PYTHONPATH=. python tools/cartography.py --date 2026-07-01; echo "rc=$?"`
Expected: `rc=0`, une ligne de résumé, et le fichier `docs/roadmap/cartographie/signals-2026-07-01.json` créé (orphelins/verdicts/leads non vides).

- [ ] **Step 6: Commit**

```bash
git add tools/cartography.py tests/test_cartography.py docs/roadmap/cartographie/signals-2026-07-01.json
git commit -m "feat(cartographie): main() — assemblage des signaux + dormance -> signals JSON

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

Note : le `signals-<date>.json` généré est committé comme premier instantané de référence (régénérable). S'il est volumineux ou bruyant, l'implémenteur peut à la place l'ignorer et ne committer que le code — mentionner le choix dans le rapport.

---

### Task 7: Passe agent (prompt) + README de la boucle d'approbation

**Files:**
- Create: `docs/roadmap/cartographie/README.md`
- Create: `docs/roadmap/cartographie/PROMPT_CARTOGRAPHE.md`

**Interfaces:**
- Consumes: le JSON produit par `main` (Task 6).
- Produces: documentation (aucun code). Ce n'est PAS du TDD (docs pures) — la vérification est une relecture.

- [ ] **Step 1: Créer le README de la cartographie**

Créer `docs/roadmap/cartographie/README.md` avec exactement ce contenu :

````markdown
# Cartographie de la recherche — mode d'emploi

Le cartographe repère automatiquement les **gaps, bottlenecks et territoires émergents** de la
recherche AGAGI, puis propose (sans jamais décider) des évolutions du registre
`docs/roadmap/SPECIALITES.md`. Design : `docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md`.

## Deux couches

1. **Signaux (déterministe)** — `tools/cartography.py`. Moissonne le corpus (registre + EDR +
   mémoire) en un JSON reproductible. Aucun LLM, aucun réseau.
2. **Interprétation (agent, à la demande)** — le prompt `PROMPT_CARTOGRAPHE.md`. Une session lead
   le lance sur le JSON de signaux ; il produit un `rapport-<date>.md` (gaps classés, bottlenecks,
   territoires candidats avec preuve, ponts proposés).

## Lancer les signaux

```bash
PYTHONPATH=. python tools/cartography.py
# options : --date AAAA-MM-JJ  --memory-dir <dossier mémoire>  --dormant-gap 30
```

Sortie : `docs/roadmap/cartographie/signals-<date>.json`. Les signaux sont bruts et advisory
(faux positifs attendus) — c'est la passe agent qui les affine.

## Lancer la passe agent

Ouvrir `PROMPT_CARTOGRAPHE.md`, y injecter le chemin du dernier `signals-<date>.json`, et le
donner à un sous-agent. Le rapport est écrit dans `docs/roadmap/cartographie/rapport-<date>.md`.

## Boucle d'approbation (règle d'or)

- La détection est **automatique** ; le rapport est **advisory**.
- **Création / scission / fusion** d'un territoire = une session lead (ou l'humain) approuve, puis
  **édite `SPECIALITES.md` à la main** (naissance officielle, commit path-scoped).
- **Le cartographe ne touche JAMAIS le registre.** Il lit, il propose ; il n'écrit que dans
  `cartographie/`.

## Cadence

À la demande. Idéalement en fin de session lead, ou hebdomadaire. Pas de cron imposé (coût token
de la passe agent).
````

- [ ] **Step 2: Créer le prompt de la passe agent**

Créer `docs/roadmap/cartographie/PROMPT_CARTOGRAPHE.md` avec exactement ce contenu :

````markdown
# Prompt — Passe cartographe (interprétation sémantique)

> Donner ce prompt à un sous-agent, après avoir remplacé `<CHEMIN_SIGNALS>` par le chemin du
> dernier `signals-<date>.json`. Le sous-agent NE MODIFIE PAS le registre ; il écrit seulement le
> rapport.

---

Tu es le cartographe de la recherche AGAGI. Lis le fichier de signaux déterministes
`<CHEMIN_SIGNALS>` (produit par `tools/cartography.py`) et le registre
`docs/roadmap/SPECIALITES.md`. Les signaux sont bruts et peuvent contenir des faux positifs :
ton rôle est de les INTERPRÉTER, pas de les recopier.

Produis un rapport dans `docs/roadmap/cartographie/rapport-<date>.md` (même date que le fichier de
signaux) avec ces sections :

1. **Gaps classés** — à partir de `pending_leads` + `unresolved_verdicts`. Pour chaque gap réel
   (écarte les faux positifs, ex. un lead déjà repris par un EDR aval) : territoire propriétaire,
   amorce de question, priorité (impact × facilité : haute/moyenne/basse), et la PREUVE (fichier +
   ligne du signal).

2. **Bottlenecks** — à partir de `lock_terms`. Les territoires à forte densité de termes-verrou, et
   les termes `systemic` (≥3 territoires) → candidat à un territoire transverse ou à un pont.

3. **Émergence** — à partir de `orphans`. Regroupe les orphelins sémantiquement cohérents en
   **territoires candidats** : préfixe proposé (3-4 lettres, non déjà utilisé), question phare, et
   les EDR-preuve qui le motivent. Signale aussi les territoires à SCINDER (deux sous-questions) ou
   à FUSIONNER (deux territoires qui convergent), avec preuve.

4. **Ponts proposés** — paires de territoires dont les EDR/leads récents se citent.

Règles :
- Chaque proposition de création/scission/fusion DOIT porter sa preuve (les records qui la motivent),
  pour que l'humain puisse approuver.
- Tu n'édites PAS `SPECIALITES.md`. Tu écris uniquement le rapport.
- Sois concis et priorisé : un tableau par section, pas de prose longue.

## Gabarit de rapport

```markdown
# Rapport cartographe — <date>

## 1. Gaps classés
| Gap | Territoire | Priorité | Preuve (fichier:ligne) | Amorce de question |
|-----|-----------|----------|------------------------|--------------------|

## 2. Bottlenecks
| Territoire / terme | Densité | Systémique ? | Lecture |
|--------------------|---------|--------------|---------|

## 3. Émergence (territoires candidats / scissions / fusions)
| Proposition | Préfixe | Question phare | EDR-preuve |
|-------------|---------|----------------|------------|

## 4. Ponts proposés
| Territoire A | Territoire B | Preuve |
|--------------|--------------|--------|

## Décisions demandées à l'humain
- [ ] ...
```
````

- [ ] **Step 3: Vérifier que la doc ne casse pas consolidate ni cartography**

Run: `PYTHONPATH=. python tools/consolidate_records.py >/dev/null; echo "consolidate rc=$?"; PYTHONPATH=. python -m pytest tests/test_cartography.py -q`
Expected: `consolidate rc=0` et tous les tests cartography verts (la doc est hors des dossiers scannés).

- [ ] **Step 4: Commit**

```bash
git add docs/roadmap/cartographie/README.md docs/roadmap/cartographie/PROMPT_CARTOGRAPHE.md
git commit -m "docs(cartographie): README boucle d'approbation + prompt de la passe agent

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Auto-revue (couverture du spec Partie 2)

- Signaux déterministes `tools/cartography.py` (§2.1) → Tasks 1-6. ✔
  - Leads pendants (gaps) → Task 4 (`pending_leads`). ✔
  - Verdicts abandonnés → Task 3 (`unresolved_verdicts`). ✔ (borné : frontmatter+titre ; « sans record aval qui tranche » délégué à l'agent, cf. bornage).
  - Territoires dormants → Task 6 (`dormant_territories`, gap de records faute de dates). ✔
  - Termes-verrou (bottlenecks) → Task 5 (`lock_term_counts`, per-territory + systemic ≥3). ✔
  - Comptes par préfixe → Task 6 (`prefix_counts`, réutilise consolidate). ✔
  - Orphelins → Task 2 (`orphan_edrs`, auto-calibré). ✔
  - Sortie `signals-<date>.json` → Task 6. ✔
- Interprétation (pass agent, §2.2) → Task 7 (`PROMPT_CARTOGRAPHE.md` : gaps classés / bottlenecks / émergence / ponts, avec preuve). ✔
- Boucle d'approbation (§2.3 : détection auto, création approuvée, cartographe ne touche pas le registre) → Task 7 (`README.md`). ✔
- Cadence (§2.4 : à la demande / hebdo) → Task 7 (`README.md`). ✔
- Réutilise le registre + comptes/préfixe de la Partie 1 (dépendance §« Découpage ») → Tasks 1,2,6 importent consolidate. ✔

## Hors périmètre (bornage assumé, cf. spec §Bornage)

- **Cross-référence aval fine** (un lead « repris » par un EDR aval, un verdict « tranché » par un
  record ultérieur) : c'est la passe AGENT qui la fait (le script liste, l'agent affine). Le script
  ne tente pas de résoudre l'aval de façon déterministe (trop de faux négatifs).
- **Hook dans `consolidate_records.py`** (lancer la cartographie en fin de consolidate) : NON retenu
  en v1 — `cartography.py` reste autonome et réutilise consolidate par import. Évite de re-toucher un
  fichier partagé. Réévaluable plus tard.
- **Génération du rapport par du code** : non — le rapport est produit par l'agent (le prompt),
  l'humain approuve, et lui seul édite `SPECIALITES.md`.
