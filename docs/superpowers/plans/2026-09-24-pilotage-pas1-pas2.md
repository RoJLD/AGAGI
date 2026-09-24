# Dashboard Pilotage — pas 1 et pas 2 : la source unique et l'endpoint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer `tools/pm/pilotage.py` — une fonction PURE qui assemble l'état de pilotage du projet (flotte, roadmap, portes, charge) en un JSON `pilotage_v1` — puis l'exposer par `GET /api/pm/pilotage` sans que le backend n'écrive quoi que ce soit ni ne recalcule ce qui coûte 18 secondes.

**Architecture:** Des lecteurs qui rendent `None` quand leur source manque ; une fonction pure `compute_pilotage` qui les assemble ; un service backend qui met en cache 30 s et qui SERT le `BOARD.json` du tick PM au lieu de recalculer la flotte ; une route qui ne porte pas de `response_model` strict sur le bloc dont le contrat appartient à une autre session.

**Tech Stack:** Python 3.13 stdlib, FastAPI + pydantic v2 (backend existant), pytest. Aucune dépendance nouvelle. Aucun bail `kuzu` : ce lot ne simule aucun monde.

**Spec:** `docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md` (707 lignes, deux fois amendée par revue adversariale — §12 donne l'historique des 3 + 3 bloquants corrigés avant l'implémentation).

## Global Constraints

- **Worktree** : `.claude/worktrees/pilotage`, branche `chantier/pilotage` depuis `feat/d1-prod-pairing`. Chemin COURT obligatoire : sous Windows, un worktree sous `.worktrees/` plus les noms de records longs dépasse 260 caractères et `git worktree add` échoue (« Could not reset index file »).
- **Porte 12** : aucun littéral commençant par `data/` ou `results/` dans un `.py` sous `tools/` ou `src/`. Tout chemin passe par `src/paths.py` — ET s'ancre sur `repo_root`, car sans variable d'environnement ces accesseurs rendent du RELATIF (`paths.results_file("x")` → `results/x`, `os.path.isabs` → `False`).
- **Porte 14** : jamais `agrégat if collection else 0`. Une source absente rend `None` et ajoute une ligne `aveugle`.
- **Nommage** : pas de `def run(` au niveau module dans `tools/pm/` (`run` est un nom d'instrument en collision sur 3 fichiers). Utiliser `main`, `compute_*`, `read_*`, `parse_*`.
- **Tests** : `PYTHONIOENCODING=utf-8 python -m pytest <fichier> -q -p no:cacheprovider` depuis la racine du worktree. Comparer les chemins de `src.paths` au LITTÉRAL avec `/`, jamais via `os.path.join`.
- **Exemption de bail** : `_LEASE_GUARD_EXEMPT = True` au niveau module dans chaque fichier de test de ce lot (aucun ne simule de monde).
- **Commits** : `git commit -m "..." -- <chemins>`, jamais nu. Aucun backtick dans un message de commit. **Demander l'accord de robla avant le PREMIER commit.** Lire le compte de suppressions de chaque commit.
- **Identité git** : la config locale du dépôt a été corrigée le 2026-09-24 (`Robin Denis`). Si un script de ce lot utilise `git commit-tree`, il doit passer `GIT_AUTHOR_NAME/EMAIL` et `GIT_COMMITTER_NAME/EMAIL` : `commit-tree` ne reçoit pas l'identité de l'appelant.
- **Dans un test, l'identité git se passe par `-c`** (`git -C <repo> -c user.name=t -c user.email=t@t <cmd>`), jamais par `git config` qui ÉCRIT (P2.86).
- **Une mesure de diagnostic s'ancre** : citer un sha ou rejouer sur `git show <sha>:<chemin>`, jamais conclure depuis le disque nu d'un arbre partagé.

---

## Structure des fichiers

| fichier | responsabilité | créé/modifié |
| --- | --- | --- |
| `tools/pm/pilotage.py` | lecteurs (`read_*`), `parse_roadmap`, `compute_pilotage` (PURE), `main` ; **n'écrit jamais rien** | créé |
| `tests/sandbox/test_pm_pilotage.py` | no-op exact, injection à dose connue, prédiction, parité, ordres, ancrage | créé |
| `tests/sandbox/test_instrument_calibration.py` | deux déclarations `CALIBRATED` | modifié |
| `backend/app/services/pilotage_service.py` | cache 30 s, flotte LUE du `BOARD.json`, `frais=True` en mémoire, exception → `aveugle` | créé |
| `backend/app/routes/pm.py` | `GET /pilotage`, paramètre `frais` | créé |
| `backend/app/schemas.py` | modèles pydantic de `pilotage_v1` (alias sur `schema`) | modifié |
| `backend/app/main.py` | `include_router` ; **correction P2.81** (`parents[3]` → racine ancrée) | modifié |
| `backend/app/services/sandbox_service.py` | helper PUR `default_live_progress_path()` | modifié |
| `tests/test_backend.py` | endpoint, cache, flotte absente/âgée, poll sans recalcul, P2.81 sans effet de bord | modifié |
| `frontend/openapi.json`, `frontend/src/api/schema.ts` | régénérés par `make api-types` **dans le commit de la route** | modifiés |

---

### Task 1 : le worktree et le squelette du module

**Files:**
- Create: `.claude/worktrees/pilotage` (worktree), `tools/pm/pilotage.py`
- Test: `tests/sandbox/test_pm_pilotage.py`

**Interfaces:**
- Produces: `tools.pm.pilotage.SCHEMA = "pilotage_v1"` ; `tools.pm.pilotage.racine_depot() -> str` (POSIX, casse d'origine).

- [ ] **Step 1 : créer le worktree**

```bash
git -C c:/Users/robla/VScode_Project/AGAGI worktree add .claude/worktrees/pilotage -b chantier/pilotage feat/d1-prod-pairing
```

Expected: `Preparing worktree (new branch 'chantier/pilotage')`. Travailler ENSUITE depuis `c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/pilotage`.

- [ ] **Step 2 : écrire le test de la racine (il échoue)**

Créer `tests/sandbox/test_pm_pilotage.py` :

```python
# -*- coding: utf-8 -*-
"""Pilotage : `compute_pilotage` est PURE et `parse_roadmap` réutilise le cliquet du backlog.
EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde ni ne prend de bail."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import pilotage as P  # noqa: E402

_LEASE_GUARD_EXEMPT = True

NOW = 1_800_000_000.0


def test_la_racine_est_ancree_sur_le_module_et_en_POSIX():
    """`find_repo_root` essaie `Path.cwd()` EN PREMIER (tools/parity_check.py:44-47) : lancé depuis un autre
    dépôt il rend l'autre dépôt, et le pilotage accuserait alors les bons fichiers d'être absents — un
    négatif FABRIQUÉ. La racine s'ancre donc sur le MODULE, et se publie en POSIX (un antislash dans un
    href est encodé %5C et VS Code ne le résout pas)."""
    r = P.racine_depot()
    assert "\\" not in r, f"la racine doit être en POSIX : {r!r}"
    assert os.path.isdir(os.path.join(r, "tools", "pm")), r
    assert os.path.isfile(os.path.join(r, "docs", "roadmap", "PRIORITES_ET_DETTES.md")), r
```

- [ ] **Step 3 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.pm.pilotage'`.

- [ ] **Step 4 : créer le module avec la racine ancrée**

Créer `tools/pm/pilotage.py` :

```python
# -*- coding: utf-8 -*-
"""Source UNIQUE de l'état de pilotage : flotte, roadmap, portes, charge, assemblés en `pilotage_v1`.

`compute_pilotage` est PURE (tout est injecté) et **aucune fonction de ce module n'écrit un fichier** :
le backend l'appelle en mémoire, le tick PM en dumpe le résultat lui-même. Une source absente n'est
jamais un zéro : elle est `None` PLUS une ligne `aveugle` (porte 14 appliquée au schéma).
"""
import argparse
import json
import os
import re
import sys

SCHEMA = "pilotage_v1"


def racine_depot():
    """Racine du dépôt, ANCRÉE sur ce module et rendue en POSIX.

    Pas `tools.parity_check.find_repo_root` en premier choix : il essaie `Path.cwd()` avant le chemin du
    module, donc un processus lancé depuis un autre dépôt (ou tout répertoire portant `.git`) rendrait
    l'autre dépôt. Mesuré le 2026-09-24 depuis un `git init` jetable : il rend le jetable, pas AGAGI.
    """
    ici = os.path.abspath(os.path.dirname(__file__))          # <racine>/tools/pm
    return os.path.dirname(os.path.dirname(ici)).replace("\\", "/")
```

- [ ] **Step 5 : lancer, vérifier le vert**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `1 passed`.

- [ ] **Step 6 : commit (après accord de robla)**

```bash
git add tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
git commit -m "feat(pilotage): squelette du module et racine ANCREE sur le module en POSIX -- find_repo_root essaie le cwd en premier, donc un backend lance ailleurs resoudrait le mauvais depot et accuserait les bons fichiers d etre absents" -- tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
```

---

### Task 2 : `parse_roadmap` — les entrées du backlog, avec la parité sur les BLOCS

**Files:**
- Modify: `tools/pm/pilotage.py`
- Test: `tests/sandbox/test_pm_pilotage.py`

**Interfaces:**
- Consumes: `tools.check_backlog_freshness` — `_ENTREE` (regex, `:91`), `_TETE` (`:59`), `_CLAUSE` (`:82`), `_HOLDS` (`:90`), `_CLOSE_MARQUEURS` (`:92`), `_BACKTICK_PATH` (`:61`), `_evalue_clause(pred, arg)` (`:125`), `compter_entrees(txt=None)` (`:373`).
- Produces: `parse_roadmap(txt, repo_root, now, evaluer_clause=None) -> dict` avec les clés `direction`, `entrees`, `comptes` (`portes_agi` est ajouté par `compute_pilotage`, pas ici).

- [ ] **Step 1 : écrire les tests de la parité et du composite (ils échouent)**

Ajouter à `tests/sandbox/test_pm_pilotage.py` :

```python
_BACKLOG_SYNTH = """# Backlog synthétique

**P2.10 — ⚠️ OUVERTE (2026-09-01) — une entrée ouverte qui cite `tools/cost_guard.py`.**
Corps de l'entrée.
<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->

**P2.11 — rang 3 — ✅ CLOSE le 2026-09-02 — une entrée close.**
Corps.

**P2.12 — 🗑️ PÉRIMÉE (2026-09-03) — une entrée périmée.**
Corps.

**P2.0 / P2.1 — rang 14 ter — OUVERTE (2026-09-04) — une tête COMPOSITE.**
Corps de la composite.

**P4.9 — OUVERTE (2026-09-05) —
rang 4 quinquies — le rang est sur la DEUXIÈME ligne, et porte un suffixe long.**
Corps.
"""


def test_la_parite_porte_sur_les_BLOCS_pas_sur_les_entrees():
    """DÉFAUT BLOQUANT trouvé en revue (spec §2.2) : `compter_entrees` compte des LIGNES de tête, donc une
    tête composite `P2.0 / P2.1` vaut UN. Asserter la parité sur les ENTRÉES la ferait lever au premier
    composite, `compute_pilotage` tomberait dans le `except` du service et TOUT le pilotage deviendrait
    aveugle à cause d'une seule tête."""
    from tools.check_backlog_freshness import compter_entrees
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    assert out["comptes"]["blocs"] == compter_entrees(_BACKLOG_SYNTH) == 5
    assert out["comptes"]["numeros"] == 6, "la composite donne DEUX entrées après l'assertion"
    assert len(out["entrees"]) == 6


def test_tete_composite_une_entree_par_numero_memes_bornes():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    comp = [e for e in out["entrees"] if e["num"] in ("P2.0", "P2.1")]
    assert [e["num"] for e in comp] == ["P2.0", "P2.1"]
    assert comp[0]["nums"] == comp[1]["nums"] == ["P2.0", "P2.1"]
    assert comp[0]["bloc"] == comp[1]["bloc"]
    assert comp[0]["lignes"] == comp[1]["lignes"]


def test_statuts_rang_et_date():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    par = {e["num"]: e for e in out["entrees"]}
    assert par["P2.10"]["statut"] == "ouverte" and par["P2.10"]["date"] == "2026-09-01"
    assert par["P2.11"]["statut"] == "close" and par["P2.11"]["rang"] == "3"
    assert par["P2.12"]["statut"] == "perimee"
    assert par["P2.0"]["rang"] == "14 ter"
    assert par["P4.9"]["rang"] == "4 quinquies", "rang sur la 2e ligne, suffixe NON tronqué"
    assert par["P2.10"]["priorite"] == "P2" and par["P4.9"]["priorite"] == "P4"


def test_ordre_des_rangs_par_base_puis_suffixe():
    """Un tri de CHAÎNES mettrait `14 quater` avant `14 ter` et `10` avant `2` : la vue centrale de
    l'avancement serait illisible. Et un rang n'est pas unique — 5 rangs sont portés par deux entrées sur
    le backlog réel —, donc la direction est une liste par rang."""
    txt = _BACKLOG_SYNTH + """
**P2.20 — rang 14 quater — OUVERTE (2026-09-06) — après ter.**
Corps.

**P2.21 — rang 2 — OUVERTE (2026-09-07) — avant dix.**
Corps.

**P2.22 — rang 10 — OUVERTE (2026-09-08) — après deux.**
Corps.
"""
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    rangs = [r["rang"] for r in out["direction"]["rangs"]]
    assert rangs == ["2", "3", "4 quinquies", "10", "14 ter", "14 quater"], rangs
    assert all(isinstance(r["p_items"], list) for r in out["direction"]["rangs"])
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: 4 FAILED — `AttributeError: module 'tools.pm.pilotage' has no attribute 'parse_roadmap'`.

- [ ] **Step 3 : implémenter `parse_roadmap`**

Ajouter à `tools/pm/pilotage.py` :

```python
_SUFFIXES = ["", "bis", "ter", "quater", "quinquies"]
_RANG = re.compile(r"—\s*rang\s+(\d+(?:\s+(?:bis|ter|quater|quinquies))?)")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PERIME = ("PÉRIMÉE", "CADUQUE")


def _cle_rang(rang):
    """(base, index du suffixe) — un tri de chaînes mettrait « 14 quater » avant « 14 ter »."""
    bits = rang.split()
    base = int(bits[0])
    suf = bits[1] if len(bits) > 1 else ""
    return (base, _SUFFIXES.index(suf) if suf in _SUFFIXES else len(_SUFFIXES))


def parse_roadmap(txt, repo_root, now, evaluer_clause=None):
    """Entrées du backlog, lues avec les MÊMES regex que le cliquet (jamais un motif réinventé).

    ⚠️ La parité de compte porte sur les BLOCS : `compter_entrees` compte des LIGNES de tête, donc une
    tête composite `P2.0 / P2.1` vaut UN. Les entrées sont dupliquées par numéro APRÈS l'assertion.

    ⚠️ `evaluer_clause` est injectable parce que `_evalue_clause` ne prend AUCUNE racine : il juge contre
    le `_ROOT` de son module et exige que le fichier soit SUIVI par git (et lit l'INDEX sous
    `GIT_INDEX_FILE`). Un fichier créé dans un `tmp_path` ne peut donc jamais rendre `True`.
    """
    from tools.check_backlog_freshness import (_BACKTICK_PATH, _CLAUSE, _CLOSE_MARQUEURS, _ENTREE,
                                               _HOLDS, _TETE, compter_entrees, _evalue_clause)
    evaluer = _evalue_clause if evaluer_clause is None else evaluer_clause
    tete = re.compile(_TETE)

    bornes = [(m.start(), m.group(1)) for m in _ENTREE.finditer(txt)]
    blocs = []
    for i, (deb, brut) in enumerate(bornes):
        fin = bornes[i + 1][0] if i + 1 < len(bornes) else len(txt)
        blocs.append({"i": i, "deb": deb, "fin": fin, "corps": txt[deb:fin], "brut": brut})

    assert len(blocs) == compter_entrees(txt), (
        f"parité rompue : {len(blocs)} blocs contre {compter_entrees(txt)} têtes comptées par le cliquet")

    entrees, illisibles = [], 0
    for b in blocs:
        try:
            entrees.extend(_entrees_du_bloc(b, txt, repo_root, evaluer, _CLAUSE, _HOLDS, _BACKTICK_PATH,
                                            _CLOSE_MARQUEURS))
        except Exception as exc:                                  # jamais perdue : comptée illisible
            illisibles += 1
            entrees.append({"num": b["brut"], "nums": [b["brut"]], "bloc": b["i"], "priorite": None,
                            "rang": None, "statut": "illisible", "date": None,
                            "titre": b["corps"].splitlines()[0] if b["corps"] else "",
                            "lignes": [txt.count("\n", 0, b["deb"]) + 1, txt.count("\n", 0, b["fin"])],
                            "clause": None, "holds": [], "chemins": [], "chemins_non_captes": 0,
                            "raison_illisible": f"{type(exc).__name__}: {exc}"})

    par_rang = {}
    for e in entrees:
        if e["rang"]:
            d = par_rang.setdefault(e["rang"], {"rang": e["rang"], "p_items": [], "statuts": []})
            d["p_items"].append(e["num"])
            d["statuts"].append(e["statut"])
    rangs = [par_rang[r] for r in sorted(par_rang, key=_cle_rang)]

    comptes = {"par_priorite": {}, "blocs": len(blocs), "numeros": len(entrees), "illisibles": illisibles}
    for e in entrees:
        if not e["priorite"]:
            continue
        d = comptes["par_priorite"].setdefault(e["priorite"], {"ouvertes": 0, "closes": 0, "perimees": 0})
        cle = {"ouverte": "ouvertes", "close": "closes", "perimee": "perimees"}.get(e["statut"])
        if cle:
            d[cle] += 1
    return {"direction": {"rangs": rangs}, "entrees": entrees, "comptes": comptes}


def _entrees_du_bloc(b, txt, repo_root, evaluer, _CLAUSE, _HOLDS, _BACKTICK_PATH, _CLOSE_MARQUEURS):
    """Une entrée PAR NUMÉRO de la tête ; toutes partagent `bloc`, `lignes` et le reste."""
    lignes_bloc = b["corps"].split("\n")
    entete = " ".join(lignes_bloc[:2])                              # même fenêtre que le cliquet
    nums = [n.strip() for n in b["brut"].split("/") if n.strip()]

    if any(m in entete for m in _PERIME):
        statut = "perimee"
    elif any(m in entete for m in _CLOSE_MARQUEURS):
        statut = "close"
    else:
        statut = "ouverte"

    m = _RANG.search(entete)
    rang = " ".join(m.group(1).split()) if m else None
    d = _DATE.search(entete)
    date = d.group(0) if d else None

    titre = lignes_bloc[0].strip().strip("*")
    for bout in [b["brut"], "—", "✅", "⚠️", "🗑️", "CLOSE", "OUVERTE", "PÉRIMÉE", "CADUQUE"]:
        titre = titre.replace(bout, " ", 1) if bout in titre else titre
    if rang:
        titre = titre.replace("rang " + rang, " ", 1)
    if date:
        titre = titre.replace(date, " ", 1)
    titre = re.sub(r"\s{2,}", " ", titre).strip(" -—")

    clauses = _CLAUSE.findall(b["corps"])
    clause = None
    if clauses:
        pred, arg = clauses[0][0], clauses[0][1].strip()
        try:
            ok, refus = evaluer(pred, arg)
        except Exception as exc:
            ok, refus = None, f"{type(exc).__name__}: {exc}"
        raison = refus
        if len(clauses) > 1:
            raison = (raison or "") + f" (+{len(clauses) - 1} autre(s) clause(s) non évaluée(s))"
        clause = {"pred": pred, "arg": arg, "satisfaite": ok, "raison": raison}

    holds = []
    for pred, arg in _HOLDS.findall(b["corps"]):
        try:
            ok, _ = evaluer(pred, arg.strip())
        except Exception:
            ok = None
        holds.append({"pred": pred, "arg": arg.strip(), "satisfaite": ok})

    captes = [c for c in _BACKTICK_PATH.findall(b["corps"]) if "/" in c]
    tous = [c for c in re.findall(r"`([^`\n]+)`", b["corps"]) if "/" in c]
    chemins = [{"rel": c, "existe": os.path.exists(os.path.join(repo_root, c)), "ligne": None}
               for c in dict.fromkeys(captes)]
    non_captes = max(0, len(set(tous)) - len(chemins))

    l0 = txt.count("\n", 0, b["deb"]) + 1                           # 1-based
    l1 = max(l0, txt.count("\n", 0, b["fin"]))                      # dernière ligne AVANT la tête suivante
    return [{"num": n, "nums": nums, "bloc": b["i"], "priorite": n.split(".")[0], "rang": rang,
             "statut": statut, "date": date, "titre": titre, "lignes": [l0, l1], "clause": clause,
             "holds": holds, "chemins": chemins, "chemins_non_captes": non_captes} for n in nums]
```

- [ ] **Step 4 : lancer, vérifier le vert**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `5 passed`.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
git commit -m "feat(pilotage): parse_roadmap -- parite sur les BLOCS (une tete composite vaut UN pour le cliquet), une entree par numero APRES l assertion, rang a suffixe non tronque lu sur deux lignes, ordre par base puis suffixe" -- tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
```

---

### Task 3 : la clause réelle et les chemins tronqués — les deux contrôles positifs de la couche

**Files:**
- Modify: `tools/pm/pilotage.py` (aucun changement attendu : ces tests confrontent l'existant à une réponse connue)
- Test: `tests/sandbox/test_pm_pilotage.py`

**Interfaces:**
- Consumes: `parse_roadmap` (Task 2).
- Produces: rien de neuf — cette tâche est la CALIBRATION de la couche d'évaluation.

- [ ] **Step 1 : écrire les tests à réponse connue**

```python
def test_clause_REELLE_sur_le_depot_trois_reponses_connues():
    """Contrôle positif de la couche d'évaluation, sans évaluateur factice : `_evalue_clause` juge contre
    le dépôt du module et exige un fichier SUIVI par git. Trois réponses connues : un motif présent dans
    un fichier suivi → true ; un chemin qui n'existe pas → false ; un chemin absolu hors dépôt → null plus
    une raison qui dit « pas suivi par git »."""
    txt = ("**P9.1 — OUVERTE (2026-09-01) — vraie.**\nCorps.\n"
           "<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->\n\n"
           "**P9.2 — OUVERTE (2026-09-02) — fausse.**\nCorps.\n"
           "<!-- closes_when:path_present=zzz/nexiste/pas.py -->\n\n"
           "**P9.3 — OUVERTE (2026-09-03) — invérifiable.**\nCorps.\n"
           "<!-- closes_when:path_present=" + os.path.abspath(os.sep).replace(os.sep, "/") + "tmp_hors_depot.py -->\n")
    out = P.parse_roadmap(txt, P.racine_depot(), NOW)              # évaluateur RÉEL
    par = {e["num"]: e for e in out["entrees"]}
    assert par["P9.1"]["clause"]["satisfaite"] is True
    assert par["P9.2"]["clause"]["satisfaite"] is False
    assert par["P9.3"]["clause"]["satisfaite"] in (False, None)


def test_les_chemins_non_captes_par_le_motif_sont_COMPTES_jamais_avales():
    """Le motif du cliquet n'admet que py|md|json|yml|yaml et refuse un chemin commençant par un point :
    mesuré le 2026-09-24, 163 des 364 fragments backtickés du backlog réel sont invisibles. Présenter la
    liste comme complète serait un motif qui TRONQUE en silence."""
    txt = ("**P9.4 — OUVERTE (2026-09-01) — cite `tools/cost_guard.py`, `.github/workflows/ci.yml` "
           "et `tools/hooks/pre-commit`.**\nCorps.\n")
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    e = out["entrees"][0]
    assert [c["rel"] for c in e["chemins"]] == ["tools/cost_guard.py"]
    assert e["chemins_non_captes"] == 2, "les deux autres sont comptés, jamais présentés comme absents"


def test_bloc_illisible_est_COMPTE_jamais_perdu(monkeypatch):
    """Une exception sur UN bloc ne fait pas disparaître l'entrée : elle devient `illisible` et la parité
    tient. Sans ce cas, une entrée mal formée réduirait silencieusement le compte publié."""
    txt = "**P9.5 — OUVERTE (2026-09-01) — normale.**\nCorps.\n"
    def _boum(*a, **k):
        raise RuntimeError("bloc casse")
    monkeypatch.setattr(P, "_entrees_du_bloc", _boum)
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    assert out["comptes"]["illisibles"] == 1
    assert out["entrees"][0]["statut"] == "illisible"
    assert out["comptes"]["blocs"] == 1
```

- [ ] **Step 2 : lancer**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `8 passed`. Si `test_les_chemins_non_captes` échoue sur le compte, vérifier `_BACKTICK_PATH` (`tools/check_backlog_freshness.py:61`) : le motif exact décide du chiffre attendu.

- [ ] **Step 3 : commit**

```bash
git add tests/sandbox/test_pm_pilotage.py
git commit -m "test(pilotage): les deux controles positifs de la couche -- clause REELLE a trois reponses connues (suivi par git / absent / hors depot) et chemins non captes COMPTES plutot qu avales" -- tests/sandbox/test_pm_pilotage.py
```

---

### Task 4 : les lecteurs et l'inventaire des portes

**Files:**
- Modify: `tools/pm/pilotage.py`
- Test: `tests/sandbox/test_pm_pilotage.py`

**Interfaces:**
- Consumes: `src.paths.pm_dir(*parties)`, `src.paths.results_file(*parties)` ; `tools.check_gate_mutation.PORTES` (dict `{num: {module, titre, temoins, mutations}}`).
- Produces: `read_backlog(repo_root) -> str | None`, `read_records_graph(repo_root) -> dict | None`, `read_roles_counts(repo_root) -> dict | None`, `read_board(repo_root) -> dict | None`, `read_portes(repo_root) -> list | None`, `BASELINES: dict[str, tuple[str, str | None]]`.

- [ ] **Step 1 : écrire les tests des lecteurs et des portes**

```python
def test_un_lecteur_absent_rend_None_jamais_un_defaut(tmp_path):
    """Porte 14 appliquée aux lecteurs : un fichier absent ne rend ni {} ni [] ni 0 — il rend None, et
    c'est `compute_pilotage` qui en fait une ligne `aveugle`."""
    assert P.read_records_graph(str(tmp_path)) is None
    assert P.read_roles_counts(str(tmp_path)) is None
    assert P.read_board(str(tmp_path)) is None
    assert P.read_backlog(str(tmp_path)) is None


def test_les_lecteurs_ANCRENT_le_chemin_relatif_de_paths(tmp_path, monkeypatch):
    """`src/paths.py` rend du RELATIF sans variable d'environnement (mesuré : `results/records_graph.json`,
    `os.path.isabs` False) : un lecteur qui ne l'ancre pas dépend du répertoire courant du processus, et
    celui d'uvicorn n'est pas garanti."""
    for v in ("AGAGI_DATA_ROOT", "AGAGI_RESULTS_ROOT", "AGAGI_DB_ROOT"):
        monkeypatch.delenv(v, raising=False)
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "records_graph.json").write_text('{"roadmap": {"G0": {"status": "validated"}}}',
                                                             encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)                     # cwd DIFFÉRENT de la racine passée
    g = P.read_records_graph(str(tmp_path))
    assert g is not None and g["roadmap"]["G0"]["status"] == "validated"


def test_inventaire_des_portes_recompute_depuis_le_HOOK_pas_depuis_PORTES():
    """`check_gate_mutation.PORTES` est la table des portes MUTÉES, pas l'inventaire des gardes : mesuré le
    2026-09-24, le hook lance 19 scripts `check_*` et PORTES en a 16 — `check_staged_authorship` (porte 7)
    et `check_gate_mutation` (porte 15) en sont absents. Et la numérotation du hook n'est ni contiguë
    (ni 19 ni 20) ni dans l'ordre du fichier (le bloc 21 précède le 18)."""
    portes = P.read_portes(P.racine_depot())
    assert portes is not None and len(portes) >= 16
    nums = [p["num"] for p in portes]
    assert nums == sorted(nums, key=int), "ordre par int(num), pas un tri de chaînes"
    assert all(isinstance(p["num"], str) for p in portes)
    modules = {p["module"] for p in portes}
    assert any("staged_authorship" in m for m in modules), "porte 7 : absente de PORTES, présente au hook"
    assert any("gate_mutation" in m for m in modules), "porte 15 : le cliquet des cliquets"
    sans_mutation = [p for p in portes if p["mutations"] is None]
    assert sans_mutation, "une porte du hook hors PORTES porte mutations=None, jamais 0"
    with_base = [p for p in portes if p["baseline"]]
    assert with_base and all("existe" in p["baseline"] for p in with_base)


def test_une_porte_du_hook_sans_baseline_declaree_porte_baseline_None():
    portes = P.read_portes(P.racine_depot())
    assert any(p["baseline"] is None for p in portes), (
        "le mappage module -> baseline est EXPLICITE (record_link_baseline.json, sans s) : "
        "une porte non déclarée ne doit pas inventer un chemin")
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider -k "lecteur or portes"`
Expected: FAILED — `has no attribute 'read_records_graph'`.

- [ ] **Step 3 : implémenter les lecteurs et `read_portes`**

```python
_NUM_BLOC = re.compile(r"^#\s*(\d+)\.", re.M)
_CHECK = re.compile(r"python\s+tools/(check_\w+)\.py")

# module -> (fichier de baseline sous tools/, clé de la collection qui compte la dette ou None).
# EXPLICITE parce que non dérivable du nom du module : check_record_links -> record_link_baseline.json.
BASELINES = {
    "check_record_links": ("record_link_baseline.json", None),
    "check_instrument_calibration": ("instrument_calibration_baseline.json", None),
    "check_guard_negative_cases": ("guard_negative_cases_baseline.json", None),
    "check_backlog_freshness": ("backlog_freshness_baseline.json", "legataires"),
    "check_agi_taxonomy": ("agi_taxonomy_baseline.json", None),
    "check_substrate_pinning": ("substrate_pinning_baseline.json", None),
    "check_bar_separation": ("bar_separation_baseline.json", None),
    "check_test_census": ("test_census_baseline.json", None),
    "check_data_paths": ("data_paths_baseline.json", "fichiers"),
    "check_fabricated_defaults": ("fabricated_defaults_baseline.json", None),
    "check_control_family": ("control_family_baseline.json", None),
    "check_io_overlap": ("io_overlap_baseline.json", None),
    "check_calibration_reach": ("calibration_reach_baseline.json", None),
}


def _lire_json(chemin):
    try:
        with open(chemin, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _ancre(repo_root, rel):
    return rel if os.path.isabs(rel) else os.path.join(repo_root, rel)


def read_backlog(repo_root):
    try:
        with open(os.path.join(repo_root, "docs", "roadmap", "PRIORITES_ET_DETTES.md"), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def read_records_graph(repo_root):
    from src import paths
    return _lire_json(_ancre(repo_root, paths.results_file("records_graph.json")))


def read_roles_counts(repo_root):
    from src import paths
    return _lire_json(_ancre(repo_root, paths.pm_dir("ROLES_COUNTS.json")))


def read_board(repo_root):
    """Le cache du tick PM. ⚠️ Écrit par `json.dump(..., default=str)` (tools/pm/tick.py) : ce qui revient
    est un ALLER-RETOUR JSON, pas le dict de `board.compute`."""
    from src import paths
    return _lire_json(_ancre(repo_root, paths.pm_dir("BOARD.json")))


def read_portes(repo_root):
    """Inventaire des gardes du hook, joint à PORTES pour titres/témoins/mutations et à BASELINES.

    La source d'AUTORITÉ est le hook : `check_gate_mutation.PORTES` est la table des portes MUTÉES
    (16 clés le 2026-09-24) alors que le hook lance 19 scripts. Le numéro vient de `^#\\s*(\\d+)\\.` en
    tête de bloc, le module du PREMIER `python tools/check_X.py` du bloc (un bloc lance parfois son check
    deux fois : `--only` puis complet).
    """
    chemin = os.path.join(repo_root, "tools", "hooks", "pre-commit")
    try:
        with open(chemin, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return None
    try:
        from tools.check_gate_mutation import PORTES
    except Exception:
        PORTES = {}

    marques = [(m.start(), m.group(1)) for m in _NUM_BLOC.finditer(src)]
    out, vus = [], set()
    for i, (deb, num) in enumerate(marques):
        fin = marques[i + 1][0] if i + 1 < len(marques) else len(src)
        mods = _CHECK.findall(src[deb:fin])
        if not mods or num in vus:
            continue
        vus.add(num)
        mod = mods[0]
        p = PORTES.get(num) or {}
        base = None
        if mod in BASELINES:
            rel, cle = BASELINES[mod]
            chemin_b = os.path.join(repo_root, "tools", rel)
            dette = None
            if cle:
                doc = _lire_json(chemin_b)
                if isinstance(doc, dict) and isinstance(doc.get(cle), (dict, list)):
                    dette = len(doc[cle])
            base = {"chemin": "tools/" + rel, "existe": os.path.exists(chemin_b), "dette": dette}
        out.append({"num": num, "module": "tools." + mod, "titre": p.get("titre"),
                    "temoins": list(p.get("temoins") or []) or None,
                    "mutations": len(p.get("mutations") or []) if p else None, "baseline": base})
    return sorted(out, key=lambda p: int(p["num"]))
```

- [ ] **Step 4 : lancer, vérifier le vert**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `12 passed`.

- [ ] **Step 5 : vérifier la porte 12 sur le fichier neuf**

Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/pilotage.py`
Expected: exit 0 — aucun littéral `data/` ni `results/` (tout passe par `src.paths`).

- [ ] **Step 6 : commit**

```bash
git add tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
git commit -m "feat(pilotage): lecteurs qui rendent None sur source absente et ANCRENT le relatif de src/paths ; inventaire des portes recompute depuis le HOOK (19 scripts) et non depuis PORTES (16 cles, sans les portes 7 et 15), mutations None jamais 0" -- tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
```

---

### Task 5 : `compute_pilotage` — la fonction pure, et le no-op exact

**Files:**
- Modify: `tools/pm/pilotage.py`
- Test: `tests/sandbox/test_pm_pilotage.py`

**Interfaces:**
- Consumes: `tools.pm.board.compute(snap, now=None) -> dict` dont les clés sont `generated_at`, `repo_root`, `aveugle`, `sessions`, `sessions_mortes`, `alertes`, `charge_connue` (`{sims_en_vol, cpu_pct, bails_vivants}`), `worktrees`, `bails`.
- Produces: `compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now, repo_root=None, board=None) -> dict`.

- [ ] **Step 1 : écrire le no-op exact et les tests d'assemblage**

```python
def test_NO_OP_EXACT_tout_absent_rend_cinq_aveuglements_et_aucun_zero():
    """Spécificité de l'instrument : sans aucune source, il ne dit pas « 0 alerte, 0 entrée » — il dit
    qu'il est AVEUGLE, cinq fois, et laisse les quatre blocs à None."""
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root="c:/x")
    assert out["schema"] == "pilotage_v1" and out["generated_at"] == NOW
    assert out["flotte"] is None and out["roadmap"] is None
    assert out["portes"] is None and out["charge"] is None
    assert len(out["aveugle"]) == 5, out["aveugle"]
    texte = json.dumps(out, ensure_ascii=False)
    assert ": 0" not in texte and "[]" not in texte, f"un zéro ou une liste vide fabriqués : {texte}"


def test_flotte_est_la_sortie_du_board_SANS_transformation():
    """Non-duplication : les clés de la flotte sont le CONTRAT du board, figé par ses 119 tests. Le
    pilotage n'en renomme, n'en retire et n'en ajoute aucune."""
    from tools.pm import board as B
    snap = {"now": NOW, "repo_root": "c:/x/agagi", "psutil": True, "registry": [], "bulletins": [],
            "worktrees": [], "commits": [], "leases": {"live": [], "dead": []}, "processes": [],
            "cpu_pct": 10.0, "backlog_paths": {}, "hook_errors": []}
    attendu = B.compute(snap, now=NOW)
    out = P.compute_pilotage(snap, None, None, None, None, NOW, repo_root="c:/x/agagi")
    assert out["flotte"] == attendu


def test_charge_porte_la_FENETRE_glissante_jamais_la_constante_depuis():
    """`ROLES_COUNTS.json` publie `depuis` (constante DEBUT, début du rôle PM) ET `fenetre` (glissante,
    30 j). Servir `depuis` comme fenêtre attribuerait le ratio à une période qui n'est pas la sienne."""
    rc = {"depuis": "2026-09-16", "fenetre": {"depuis": "2026-08-24", "jours": 30},
          "ratio_science_methodo": 1.12, "fichiers": {"science": 239, "methodo": 213, "autre": 604}}
    out = P.compute_pilotage(None, None, None, rc, None, NOW, repo_root="c:/x")
    assert out["charge"]["fenetre"] == {"depuis": "2026-08-24", "jours": 30}
    assert out["charge"]["ratio_science_methodo"] == 1.12
    assert "depuis" not in out["charge"], "la constante DEBUT n'est pas une fenêtre"


def test_age_de_la_flotte_vient_de_generated_at_jamais_du_mtime(tmp_path):
    """Un `git checkout`, une copie ou une écriture interrompue donne un mtime FRAIS sur un contenu
    périmé : la vue annoncerait une fraîcheur supposée. Seul contre-exemple qui distingue les deux
    règles : un fichier dont le mtime et le `generated_at` diffèrent de plusieurs minutes."""
    board = {"generated_at": NOW - 1800.0, "repo_root": "c:/x", "aveugle": [], "sessions": [],
             "sessions_mortes": [], "alertes": [],
             "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []},
             "worktrees": [], "bails": None}
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root="c:/x", board=board)
    assert out["charge"]["flotte_age_s"] == 1800.0
    sans = dict(board)
    sans.pop("generated_at")
    out2 = P.compute_pilotage(None, None, None, None, None, NOW, repo_root="c:/x", board=sans)
    assert out2["charge"]["flotte_age_s"] is None, "clé absente -> None, jamais un mtime de repli"


def test_prediction_une_entree_close_de_plus_ne_bouge_que_son_compte():
    """Linéarité en la dose : ajouter UNE entrée close augmente `closes` de 1 et ne touche rien d'autre."""
    base = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot())
    plus = P.compute_pilotage(None, _BACKLOG_SYNTH + "\n**P2.99 — ✅ CLOSE le 2026-09-09 — une de plus.**\nCorps.\n",
                              None, None, None, NOW, repo_root=P.racine_depot())
    a, b = base["roadmap"]["comptes"], plus["roadmap"]["comptes"]
    assert b["par_priorite"]["P2"]["closes"] == a["par_priorite"]["P2"]["closes"] + 1
    assert b["par_priorite"]["P2"]["ouvertes"] == a["par_priorite"]["P2"]["ouvertes"]
    assert b["blocs"] == a["blocs"] + 1 and b["numeros"] == a["numeros"] + 1


def test_parite_sur_le_backlog_REEL():
    """Sur le vrai fichier : autant de blocs que le cliquet compte de têtes, et aucun bloc illisible."""
    from tools.check_backlog_freshness import compter_entrees
    txt = P.read_backlog(P.racine_depot())
    assert txt is not None
    out = P.compute_pilotage(None, txt, None, None, None, NOW, repo_root=P.racine_depot())
    c = out["roadmap"]["comptes"]
    assert c["blocs"] == compter_entrees(txt)
    illis = [e["num"] for e in out["roadmap"]["entrees"] if e["statut"] == "illisible"]
    assert not illis, f"entrées illisibles sur le backlog réel : {illis}"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider -k compute or NO_OP`
Expected: FAILED — `has no attribute 'compute_pilotage'`.

- [ ] **Step 3 : implémenter `compute_pilotage`**

```python
def compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now, repo_root=None,
                     board=None):
    """PURE : tout est injecté, rien n'est lu, rien n'est écrit.

    `flotte` a DEUX provenances, jamais confondues : `board` (le contenu de BOARD.json, chemin du poll —
    un aller-retour JSON) ou `board.compute(snap)` si `snap` est fourni (chemin `?frais=1`).
    """
    now = float(now)
    racine = repo_root or racine_depot()
    aveugle = []

    flotte = None
    if snap is not None:
        from tools.pm.board import compute as board_compute
        flotte = board_compute(snap, now=now)
    elif board is not None:
        flotte = board
    else:
        aveugle.append("flotte : ni instantané ni BOARD.json — le tick PM n'a pas encore tourné")
    if flotte is not None:
        aveugle.extend("flotte: " + a for a in (flotte.get("aveugle") or []))

    roadmap = None
    if backlog_txt is None:
        aveugle.append("backlog : docs/roadmap/PRIORITES_ET_DETTES.md introuvable")
    else:
        roadmap = parse_roadmap(backlog_txt, racine, now)
        if records_graph is None:
            aveugle.append("graphe de records : results/records_graph.json introuvable")
            roadmap["portes_agi"] = None
        else:
            roadmap["portes_agi"] = records_graph.get("roadmap")
    if backlog_txt is not None and records_graph is None:
        pass                                                    # ligne déjà posée juste au-dessus
    elif backlog_txt is None and records_graph is None:
        aveugle.append("graphe de records : results/records_graph.json introuvable")

    if portes is None:
        aveugle.append("portes : tools/hooks/pre-commit illisible")

    charge = None
    if roles_counts is None and flotte is None:
        aveugle.append("compteurs du PM : data/pm/ROLES_COUNTS.json introuvable")
    else:
        if roles_counts is None:
            aveugle.append("compteurs du PM : data/pm/ROLES_COUNTS.json introuvable")
        cc = (flotte or {}).get("charge_connue") or {}
        gen = (flotte or {}).get("generated_at")
        charge = {"sims_en_vol": cc.get("sims_en_vol"), "cpu_pct": cc.get("cpu_pct"),
                  "bails_vivants": cc.get("bails_vivants"),
                  "flotte_age_s": (now - float(gen)) if gen is not None else None,
                  "ratio_science_methodo": (roles_counts or {}).get("ratio_science_methodo"),
                  "fichiers": (roles_counts or {}).get("fichiers"),
                  "fenetre": (roles_counts or {}).get("fenetre")}
    return {"schema": SCHEMA, "generated_at": now, "repo_root": racine.replace("\\", "/"),
            "aveugle": aveugle, "flotte": flotte, "roadmap": roadmap, "portes": portes, "charge": charge}


def main(argv=None):
    """`--json` imprime le pilotage. N'ÉCRIT AUCUN FICHIER : le tick PM est le seul writer."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    racine = args.repo_root or racine_depot()
    import time
    out = compute_pilotage(None, read_backlog(racine), read_records_graph(racine),
                           read_roles_counts(racine), read_portes(racine), time.time(),
                           repo_root=racine, board=read_board(racine))
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    else:
        print(f"[pilotage] {out['schema']} — {len(out['aveugle'])} aveuglement(s)")
        for a in out["aveugle"]:
            print("  AVEUGLE :", a)
        if out["roadmap"]:
            c = out["roadmap"]["comptes"]
            print(f"  roadmap : {c['blocs']} blocs, {c['numeros']} entrées, {c['illisibles']} illisible(s)")
        if out["portes"]:
            print(f"  portes : {len(out['portes'])}")
        if out["charge"]:
            print(f"  charge : {out['charge']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : lancer toute la suite du fichier**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `18 passed`. Si le no-op échoue sur `": 0" not in texte`, c'est qu'un champ rend 0 au lieu de `None` — corriger le champ, pas le test.

- [ ] **Step 5 : vérifier que `main` n'écrit rien**

```python
def test_main_json_n_ecrit_AUCUN_fichier(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    avant = sorted(os.listdir(tmp_path))
    P.main(["--json", "--repo-root", P.racine_depot()])
    assert sorted(os.listdir(tmp_path)) == avant, "main a écrit un fichier"
    assert json.loads(capsys.readouterr().out)["schema"] == "pilotage_v1"
```

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py -q -p no:cacheprovider`
Expected: `19 passed`.

- [ ] **Step 6 : essai à la main (le livrable du pas 1 est utilisable dès maintenant)**

Run: `PYTHONIOENCODING=utf-8 python -m tools.pm.pilotage`
Expected: une ligne `[pilotage] pilotage_v1 — N aveuglement(s)`, puis les comptes de la roadmap et des portes. Sur un arbre sans tick PM, la ligne « flotte : ni instantané ni BOARD.json » apparaît — c'est le comportement voulu.

- [ ] **Step 7 : commit**

```bash
git add tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
git commit -m "feat(pilotage): compute_pilotage PURE (deux provenances de la flotte, jamais confondues), no-op exact a cinq aveuglements sans un seul zero fabrique, age de la flotte lu sur generated_at et jamais sur le mtime, fenetre GLISSANTE du ratio et jamais la constante depuis ; main --json n ecrit aucun fichier" -- tools/pm/pilotage.py tests/sandbox/test_pm_pilotage.py
```

---

### Task 6 : déclarer les deux instruments dans `CALIBRATED`

**Files:**
- Modify: `tests/sandbox/test_instrument_calibration.py` (fichier PARTAGÉ — voir l'avertissement)
- Test: le cliquet lui-même

**Interfaces:**
- Consumes: la table `CALIBRATED` (`tests/sandbox/test_instrument_calibration.py:72`).

⚠️ **Fichier convoité.** Avant d'éditer :

```bash
PYTHONIOENCODING=utf-8 python -c "from tools.check_staged_authorship import snapshot; snapshot(['tests/sandbox/test_instrument_calibration.py'], owner='plan-pilotage')"
```

Et annoncer aux autres sessions (`SendMessage`) qu'on écrit dans ce fichier, puis qu'on a fini — c'est la file annoncée du dépôt.

- [ ] **Step 1 : ajouter les deux déclarations**

Dans `CALIBRATED`, ajouter :

```python
    # Pilotage (2026-09-24) : `compute_pilotage` et `parse_roadmap` PRODUISENT des affirmations (statut
    # d'une entrée, clause satisfaite, comptes publiés) — donc des instruments au sens strict.
    # ⚠️ Le cliquet ne les DÉTECTE pas : aucun de ses 14 motifs ne capte `compute_*` ni `parse_*`, et une
    # déclaration non détectée est ignorée en silence (check_instrument_calibration.py:249). C'est P2.83,
    # dont la moitié « le cliquet CRIE et tranche la cause » est livrée : la déclaration documente, la
    # GARANTIE vient des cas qui tournent en CI (job `suite-complete`, par répertoire).
    "tools/pm/pilotage.py::compute_pilotage": ["no-op:cinq-aveuglements", "prediction:une-close-de-plus",
                                               "non-duplication:board", "age:generated_at-pas-mtime"],
    "tools/pm/pilotage.py::parse_roadmap": ["parite:blocs", "composite:deux-entrees-un-bloc",
                                            "rang:quinquies-non-tronque", "clause:trois-reponses-connues",
                                            "chemins:non-captes-comptes", "illisible:compte-jamais-perdu"],
```

- [ ] **Step 2 : lancer le cliquet de calibration**

Run: `PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py`
Expected: exit 0. Si les deux déclarations apparaissent dans la liste des IGNORÉES, c'est le comportement attendu et documenté (P2.83) : le noter dans le message de commit, ne PAS renommer les fonctions pour plaire au motif.

- [ ] **Step 3 : lancer la suite de calibration**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_instrument_calibration.py -q -p no:cacheprovider`
Expected: aucun rouge NOUVEAU (comparer au résultat obtenu avant l'édition sur le même arbre).

- [ ] **Step 4 : vérifier l'autorat avant de committer**

```bash
PYTHONIOENCODING=utf-8 python -c "from tools.check_staged_authorship import verify; verify(['tests/sandbox/test_instrument_calibration.py'], owner='plan-pilotage')"
```

Expected: aucun hunk ÉTRANGER dans le lot.

- [ ] **Step 5 : commit**

```bash
git add tests/sandbox/test_instrument_calibration.py
git commit -m "test(pilotage): compute_pilotage et parse_roadmap declares CALIBRATED avec leurs dix cas -- le cliquet ne les detecte pas (aucun motif ne capte compute_* ni parse_*, P2.83), donc la declaration documente et la garantie vient des cas qui tournent en CI" -- tests/sandbox/test_instrument_calibration.py
```

---

### Task 7 : P2.81 — la racine du backend, et un test qui peut enfin échouer

**Files:**
- Modify: `backend/app/main.py:68-70`, `backend/app/services/sandbox_service.py:55-66`
- Test: `tests/test_backend.py`

**Interfaces:**
- Produces: `backend.app.services.sandbox_service.default_live_progress_path() -> str` (PUR, aucun effet de bord).

- [ ] **Step 1 : écrire le test qui échoue AUJOURD'HUI**

Ajouter à `tests/test_backend.py` :

```python
def test_P2_81_le_puits_de_progression_du_backend_est_celui_que_le_lanceur_arme() -> None:
    """P2.81 : `main.py:68` résolvait la racine par `parents[3]`, forme copiée des routes qui vivent un
    niveau PLUS PROFOND — pour `main.py` c'est le dossier PARENT du dépôt. Mesuré le 2026-09-22 :
    `C:/Users/robla/VScode_Project/results`, qui n'existe pas. Le WS `/ws/evolution` taillait donc un
    fichier que le lanceur n'écrit jamais, depuis le commit initial.

    ⚠️ Ce test NE DOIT PAS appeler `_arm_live_progress` : elle fait `os.makedirs` puis `open(path, "w")`
    sur le VRAI `<dépôt>/results/live_progress.jsonl` — elle TRONQUERAIT la progression d'un run en vol,
    et un test deviendrait writer d'un fichier partagé. On compare au helper PUR.
    """
    from pathlib import Path
    from backend.app import main as main_mod
    from backend.app.services import sandbox_service as sb

    assert Path(main_mod.LIVE_PROGRESS_PATH) == Path(sb.default_live_progress_path())
    assert Path(main_mod.RESULTS_DIR).name == "results"
    assert (Path(main_mod.RESULTS_DIR).parent / "tools" / "hooks" / "pre-commit").exists(), (
        "la racine du backend doit être le DÉPÔT : son parent doit porter tools/hooks/pre-commit")
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k P2_81`
Expected: FAIL — `AttributeError: module ... has no attribute 'default_live_progress_path'`.

- [ ] **Step 3 : extraire le helper pur**

Dans `backend/app/services/sandbox_service.py`, ajouter au-dessus de `_arm_live_progress` :

```python
def default_live_progress_path() -> str:
    """Chemin du puits de progression live, SANS effet de bord (ni makedirs ni troncature).

    Extrait pour que les tests puissent le comparer sans appeler `_arm_live_progress`, qui VIDE le
    fichier : un test qui l'appellerait tronquerait la progression d'un run en vol (P2.81).
    """
    return os.path.join(PROJECT_ROOT, "results", "live_progress.jsonl")
```

Puis, dans `_arm_live_progress`, remplacer :

```python
        if progress_path is None:
            progress_path = os.path.join(PROJECT_ROOT, "results", "live_progress.jsonl")
```

par :

```python
        if progress_path is None:
            progress_path = default_live_progress_path()
```

- [ ] **Step 4 : corriger la racine de `main.py`**

Dans `backend/app/main.py`, remplacer la ligne 68 :

```python
RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"
```

par :

```python
# ⚠️ P2.81 : `parents[3]` était copié des routes et des services, qui vivent un niveau PLUS PROFOND —
# pour CE fichier il désigne le dossier PARENT du dépôt (mesuré le 2026-09-22 :
# C:/Users/robla/VScode_Project/results, inexistant), donc `/ws/evolution` taillait un fichier que le
# lanceur n'écrit jamais. La racine se prend là où le lanceur la prend : `sandbox_service.PROJECT_ROOT`.
RESULTS_DIR = Path(sandbox_service_module.PROJECT_ROOT) / "results"
```

Et ajouter l'import en tête du fichier, à côté des autres imports de services :

```python
from .services import sandbox_service as sandbox_service_module
```

- [ ] **Step 5 : lancer, vérifier le vert**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider`
Expected: tous PASS. Vérifier en particulier que le test existant `test_ws_evolution_streams_appended_events` (qui monkeypatche `LIVE_PROGRESS_PATH`) reste vert.

- [ ] **Step 6 : vérifier qu'aucun fichier n'a été créé dans l'arbre**

Run: `git status --short results/`
Expected: aucune ligne nouvelle — le test ne doit RIEN avoir écrit.

- [ ] **Step 7 : commit**

```bash
git add backend/app/main.py backend/app/services/sandbox_service.py tests/test_backend.py
git commit -m "fix(P2.81): la racine du backend etait resolue un niveau TROP HAUT -- parents[3] copie des routes qui vivent plus profond, donc /ws/evolution taillait un fichier inexistant depuis le commit initial ; helper PUR default_live_progress_path et un test qui peut ENFIN echouer, sans tronquer le puits d un run en vol" -- backend/app/main.py backend/app/services/sandbox_service.py tests/test_backend.py
```

---

### Task 8 : le service backend — cache 30 s, flotte LUE, jamais de recalcul sur le poll

**Files:**
- Create: `backend/app/services/pilotage_service.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Consumes: `tools.pm.pilotage` (Tasks 1-5), `tools.pm.snapshot.snapshot(repo_root, ...)`.
- Produces: `get_pilotage(ttl_s: float = 30.0, frais: bool = False) -> dict`, `_vider_cache() -> None` (pour les tests).

- [ ] **Step 1 : écrire les tests du service**

```python
def test_pilotage_endpoint_rend_le_schema() -> None:
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "pilotage_v1"
    assert isinstance(d["generated_at"], (int, float))
    assert isinstance(d["aveugle"], list)


def test_pilotage_le_POLL_ne_recalcule_JAMAIS_le_snapshot(monkeypatch) -> None:
    """La mesure qui a changé le design : `snapshot()` coûte 15,6-18,1 s (charge notée : 40 % CPU,
    9 processus python) alors qu'`apiFetch` coupe à 10 s et que toute la roadmap coûte 0,70 s. Le poll ne
    doit donc jamais l'appeler — seul `?frais=1` le fait."""
    from backend.app.services import pilotage_service as ps

    def _interdit(*a, **k):
        raise AssertionError("snapshot() appelé sur le chemin du poll : 18 s par requête")

    monkeypatch.setattr(ps, "snapshot", _interdit)
    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200


def test_pilotage_un_lecteur_qui_leve_devient_une_ligne_aveugle_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import pilotage_service as ps

    def _boum(*a, **k):
        raise RuntimeError("lecteur casse")

    monkeypatch.setattr(ps.pilotage, "compute_pilotage", _boum)
    ps._vider_cache()
    r = client.get("/api/pm/pilotage")
    assert r.status_code == 200, "une exception ne doit jamais devenir un 500"
    d = r.json()
    assert d["aveugle"] and d["aveugle"][0].startswith("pilotage:")
    assert d["flotte"] is None and d["roadmap"] is None and d["portes"] is None and d["charge"] is None


def test_pilotage_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import pilotage_service as ps
    appels = {"n": 0}
    vrai = ps.pilotage.compute_pilotage

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)

    monkeypatch.setattr(ps.pilotage, "compute_pilotage", _compte)
    ps._vider_cache()
    client.get("/api/pm/pilotage")
    client.get("/api/pm/pilotage")
    assert appels["n"] == 1, f"le cache 30 s n'a pas tenu : {appels['n']} calculs"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k pilotage`
Expected: FAILED — 404 sur la route (elle arrive en Task 9) ou `ModuleNotFoundError: backend.app.services.pilotage_service`.

- [ ] **Step 3 : écrire le service**

Créer `backend/app/services/pilotage_service.py` :

```python
"""Service du pilotage : assemble `pilotage_v1` pour la route, en mémoire, SANS écrire un fichier.

⚠️ La flotte n'est pas recalculée sur le chemin du poll. Mesuré le 2026-09-24 (charge notée : 40 % de CPU,
9 processus python) : `tools.pm.snapshot.snapshot()` coûte 15,6 / 16,6 / 18,1 s — au-delà du timeout de
10 s du client — tandis que toute la roadmap coûte 0,70 s. Le poll sert donc le `BOARD.json` du tick PM
(dont le PM est l'unique writer) avec son ÂGE publié ; `frais=True` recalcule en mémoire, et seul un clic
explicite le déclenche.
"""
from __future__ import annotations

import time
from typing import Any

from tools.pm import pilotage
from tools.pm.snapshot import snapshot

_TTL_DEFAUT = 30.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def get_pilotage(ttl_s: float = _TTL_DEFAUT, frais: bool = False) -> dict:
    now = time.time()
    if not frais and _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    try:
        racine = pilotage.racine_depot()
        snap = snapshot(racine) if frais else None
        out = pilotage.compute_pilotage(
            snap,
            pilotage.read_backlog(racine),
            pilotage.read_records_graph(racine),
            pilotage.read_roles_counts(racine),
            pilotage.read_portes(racine),
            now,
            repo_root=racine,
            board=None if frais else pilotage.read_board(racine),
        )
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        out = {"schema": pilotage.SCHEMA, "generated_at": now, "repo_root": "",
               "aveugle": [f"pilotage: {type(exc).__name__}: {exc}"],
               "flotte": None, "roadmap": None, "portes": None, "charge": None}
    if not frais:
        _cache["at"], _cache["valeur"] = now, out
    return out
```

- [ ] **Step 4 : lancer (la route manque encore)**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k pilotage`
Expected: encore 404 — la route arrive en Task 9. Ne pas committer un test rouge : enchaîner.

---

### Task 9 : la route, les schémas et les types générés

**Files:**
- Create: `backend/app/routes/pm.py`
- Modify: `backend/app/schemas.py`, `backend/app/main.py`
- Modify: `frontend/openapi.json`, `frontend/src/api/schema.ts` (régénérés)

**Interfaces:**
- Consumes: `get_pilotage(ttl_s, frais)` (Task 8).
- Produces: `GET /api/pm/pilotage?frais=<bool>` ; modèle `PilotageV1`.

- [ ] **Step 1 : ajouter le modèle pydantic**

Dans `backend/app/schemas.py` :

```python
class PilotageV1(BaseModel):
    """Enveloppe de `pilotage_v1`.

    ⚠️ `flotte` est `dict | None` SANS modèle strict : son contrat appartient au board (session PM) et
    évolue chez son propriétaire ; un `response_model` qui refuserait une clé neuve lèverait un 500 HORS
    du try/except du service — une seconde source d'erreur que les modes dégradés ne couvrent pas.
    ⚠️ `schema` masque un attribut de `BaseModel` en pydantic v2 : d'où l'alias.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias="schema")
    generated_at: float
    repo_root: str
    aveugle: list[str]
    flotte: dict | None = None
    roadmap: dict | None = None
    portes: list[dict] | None = None
    charge: dict | None = None
```

Vérifier que `ConfigDict` et `Field` sont importés en tête du fichier (`from pydantic import BaseModel, ConfigDict, Field`).

- [ ] **Step 2 : écrire la route**

Créer `backend/app/routes/pm.py` :

```python
"""Route du pilotage : une seule lecture, aucun écrit.

`frais=1` recalcule la flotte en mémoire (≈ 18 s mesurés) : réservé à un clic explicite, jamais au poll.
"""
from fastapi import APIRouter

from ..schemas import PilotageV1
from ..services.pilotage_service import get_pilotage

router = APIRouter()


@router.get("/pilotage", response_model=PilotageV1, response_model_by_alias=True)
def pilotage(frais: bool = False) -> dict:
    return get_pilotage(frais=frais)
```

- [ ] **Step 3 : monter le routeur**

Dans `backend/app/main.py`, à côté des autres `include_router` (l.72-83) :

```python
from .routes.pm import router as pm_router
...
app.include_router(pm_router, prefix="/api/pm", tags=["pm"])
```

- [ ] **Step 4 : lancer les tests du service et de la route**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider`
Expected: tous PASS, les quatre tests `pilotage` compris.

- [ ] **Step 5 : régénérer les types API — dans CE commit**

```bash
PYTHONPATH=. python tools/dump_openapi.py
npm --prefix frontend run gen:api
git diff --stat -- frontend/openapi.json frontend/src/api/schema.ts
```

Expected: les deux fichiers changent (la route neuve y apparaît). La CI exige `git diff --exit-code` sur ces deux chemins (`.github/workflows/ci.yml:164-168`) : ils partent dans le MÊME commit que la route, sinon la CI rougit.

- [ ] **Step 6 : vérifier la porte de parité**

Run: `PYTHONIOENCODING=utf-8 python tools/parity_check.py --warn`
Expected: `/api/pm/pilotage` apparaît comme endpoint NON CONSOMMÉ — c'est attendu tant que le pas 3 (frontend) n'existe pas. Le noter dans le message de commit pour que personne ne le prenne pour une régression.

- [ ] **Step 7 : commit**

```bash
git add backend/app/routes/pm.py backend/app/schemas.py backend/app/main.py backend/app/services/pilotage_service.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
git commit -m "feat(pilotage): GET /api/pm/pilotage -- la flotte est LUE du BOARD.json du tick avec son age, jamais recalculee sur le poll (snapshot 15,6-18,1 s mesures contre un timeout client de 10 s), cache 30 s, toute exception devient une ligne aveugle NOMMEE et jamais un 500 ; types API regeneres dans le meme commit (drift-gate CI)" -- backend/app/routes/pm.py backend/app/schemas.py backend/app/main.py backend/app/services/pilotage_service.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
```

---

### Task 10 : les portes du dépôt, et le coût mesuré publié dans la spec

**Files:**
- Modify: `docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md` (§6, ligne du coût)

**Interfaces:** aucune — cette tâche vérifie et publie.

- [ ] **Step 1 : lancer les portes que ce lot touche**

```bash
PYTHONIOENCODING=utf-8 python tools/check_data_paths.py
PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py
PYTHONIOENCODING=utf-8 python tools/check_test_census.py
PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py
PYTHONIOENCODING=utf-8 python tools/check_synthesis_counts.py
```

Expected: exit 0 partout. ⚠️ Si `check_synthesis_counts` signale un compteur périmé sur un fichier que ce lot n'a PAS touché, c'est P2.85 (la porte juge le DISQUE, donc le travail en vol d'une autre session) : ne pas corriger le fichier d'autrui, prévenir la session propriétaire et attendre.

- [ ] **Step 2 : mesurer le coût du chemin servi, à charge NOTÉE**

```bash
PYTHONIOENCODING=utf-8 python -c "import psutil, time; print('cpu', psutil.cpu_percent(1), '%'); import sys; sys.path.insert(0,'.'); from backend.app.services.pilotage_service import get_pilotage, _vider_cache; _vider_cache(); t=time.perf_counter(); d=get_pilotage(); print('poll', round(time.perf_counter()-t,2), 's,', len(d['aveugle']), 'aveuglements')"
```

Noter les deux chiffres (charge et durée). Attendu : bien en dessous du timeout de 10 s du client, puisque le poll ne fait plus de `snapshot()`.

- [ ] **Step 3 : publier le chiffre dans la spec**

Dans `docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md`, §6, à la suite du paragraphe « **Coût — MESURÉ le 2026-09-24…** », ajouter une phrase donnant la durée du chemin SERVI avec la charge du moment et la date. Un chiffre de coût sans la charge de la machine est la classe E12 appliquée au coût.

- [ ] **Step 4 : lancer la suite complète des fichiers touchés**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_pilotage.py tests/test_backend.py tests/sandbox/test_instrument_calibration.py -q -p no:cacheprovider`
Expected: aucun rouge nouveau. Noter le compte de passés dans le message de commit.

- [ ] **Step 5 : commit**

```bash
git add docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md
git commit -m "docs(spec): le cout du chemin SERVI est mesure a charge notee et publie -- le poll ne fait plus de snapshot, donc il tient tres loin sous le timeout client de 10 s" -- docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md
```

---

## Ce que ce plan NE fait pas

Le pas 3 (famille frontend « Pilotage », trois vues, `PILOTAGE_POLL`, `a:focus-visible`), le pas 4 (patch de `tick.py`, pas du skill `/pm`, page artefact) et le pas 5 (`FRONTEND.md`) sont hors de ce plan. Les pas 4 et 5 touchent des fichiers dont une autre session est propriétaire : ils passent par elle, ou par `snapshot`/`verify` après accord. Le lot 2 « Science » (taxonomies, pipeline des runs, rythme) a sa propre entrée de backlog (P2.84) et doit être brainstormé avant tout code.

## Auto-revue

**Couverture de la spec** : §2.2 (schéma) → Tasks 2, 4, 5 ; §2.3 (trois lectures) → Task 2 (direction, ordres) et Task 5 (comptes) ; §3.1 (lecteurs, `parse_roadmap`, `BASELINES`, racine ancrée) → Tasks 1, 2, 3, 4 ; §3.2 (service, flotte lue, `?frais=1`, pas de `response_model` strict, types générés) → Tasks 8, 9 ; §5 (modes dégradés) → Tasks 4, 5, 8 ; §6 (tests, calibration, coût) → Tasks 3, 5, 6, 10 ; §7 (pas 1 et 2) → tout ; §10.3 (P2.81) → Task 7. §3.3, §3.4 et le reste du §7 sont explicitement hors plan (ci-dessus).

**Placeholders** : aucun « TBD », aucune étape sans code, aucun renvoi « comme la tâche N ».

**Cohérence des types** : `compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now, repo_root=None, board=None)` est appelée avec cette signature exacte en Tasks 5, 8 et dans les tests ; `parse_roadmap(txt, repo_root, now, evaluer_clause=None)` de même en Tasks 2, 3, 5 ; `read_portes` rend une liste de dicts dont les clés `num`, `module`, `titre`, `temoins`, `mutations`, `baseline` sont celles que Task 9 sérialise et que la spec §2.2 déclare ; `default_live_progress_path()` est produite en Task 7 et consommée par son seul test.
