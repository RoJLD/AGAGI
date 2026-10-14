# Lot 2 « Science » du dashboard — plan 2 (P2.84) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trois vues « Science » — Pipeline (règle scellée → record), Taxonomie (capacités et prérequis, réfutées visibles), Trouvailles (verdicts déclarés, rythme par semaine) — construites SUR l'index du plan 1 et sur des sources déjà publiées, sans jamais recalculer un verdict ni écrire une tendance.

**Architecture:** un module pur `tools/pm/science.py` : trois LECTEURS (pipeline par `tools/check_preregistration_applied`, taxonomie par `data/agi_taxonomy`, compte du graphe de records) et `compute_science(index, pipeline, taxonomie, graphe, now) -> science_v1`. Le backend sert `GET /api/pm/science` avec le filet du plan 1, en lisant l'index dans le MÊME cache que `/api/pm/index`. Le frontend ajoute une famille « Science » de trois onglets, une vue par commit.

**Tech Stack:** Python 3.13 stdlib, FastAPI + pydantic v2, pytest ; React 18 + TypeScript strict + react-query v5 + vitest ; SVG rendu par React (aucune simulation de forces).

**Spec:** `docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md` — §3.2 (les trois blocs), §3.4-3.5 (backend, frontend), §5, §7 (lignes « science »), §8 pas 4 et 5, §9 (vocabulaire des dates, qui remplace M4). Plan 1 livré : `docs/superpowers/plans/2026-09-26-auto-indexation-index.md`.

## Global Constraints

- Aucune vue ne recalcule un verdict ni n'écrit une tendance (condition 4) : la pipeline RECOPIE `couverture()` et `familles_sans_record()`, la taxonomie RECOPIE les trois JSON, les trouvailles RECOPIENT les verdicts que l'index a lus ; `par_semaine` = des comptes, aucune clé ni phrase de pente.
- Un bloc dont la source manque vaut `null` + une ligne préfixée de son nom (`pipeline : `, `taxonomie : `, `trouvailles : `) ; jamais un zéro, jamais une liste vide présentée comme une mesure (porte 14). `science:` est réservé au mode dégradé du service, `index:` à celui de l'index (I3).
- Aucun littéral `results/` ni `data/` dans les modules, docstrings comprises (porte 12) : `src/paths.py`, ancré sur la racine.
- P2.135 (dans d1 depuis `f5d16232`) : sans ses répertoires, `tools/check_preregistration_applied` LÈVE `RacineSansSource` ; le lecteur de la pipeline nomme l'exception, il ne la transforme jamais en `(0, 0, 0, 0)` (B2).
- Tout import backend vers `tools/` tourne dans l'IMAGE docker (`tools/`, `docs/` en `:ro`, `data/` et `results/` montés) ; `backend/requirements.txt` est la seule liste de dépendances.
- `make api-types` dans le MÊME commit que tout changement de `backend/app/schemas.py`, sous le bail `kuzu` (l'import de l'app peut ouvrir une base) ; `openapi.json` et `schema.ts` normalisés en LF.
- Frontend : aucun `fetch` hors `api/`, zéro `setInterval`, chemins LITTÉRAUX dans `api/pm.ts` (porte de parité), `AveugleBanner` avec `prefixeDegrade="science:"`, bloc `null` → `Empty` avec SA ligne.
- Commits par `python -m tools.check_staged_authorship commit-exact --attendu CHEMIN=FICHIER -F msg`, jamais nus, jamais `--no-verify`, messages SANS backticks ; tests Windows ET WSL (mémoire `wsl-linux-repro`) ; `python -m tools.jobs.doctor` avant toute passe longue ; un seul run lourd à la fois (un commit en est un).
- Aucun test n'écrit dans l'arbre : sources injectées, fichiers sous `tmp_path` ; `tests/test_consolidate_records.py` n'est PAS dans les passes de ce plan (P2.113 a).
- Revue adversariale opus AVANT le commit du pas 4 (Tasks 1-2 : il produit des comptes) ; relecture visuelle de chaque vue avant son commit.

## Review Focus

1. **Index en mode dégradé alors que les autres sources vont bien** → `trouvailles` null + ligne, `pipeline.preinscriptions` null + ligne, `taxonomie` servie — jamais une liste vide de verdicts. Témoins : Task 1 (`test_index_degrade_trouvailles_null_taxonomie_servie`), Task 3 (vue Pipeline, pré-inscriptions null).
2. **Famille non lue par l'index** (répertoire absent, parité rompue) → `par_semaine[famille]` null, jamais `{}` ; **famille neuve de l'index sans date nommée** → null + ligne. Témoins : Task 1 (`test_famille_non_lue_par_semaine_null`, `test_famille_inconnue_nommee_jamais_comptee`). *Amendement A1 (I2) : l'objet est toujours servi, `semaines` null et `raison` nommée (`famille_non_lue`, `parite_rompue`, `sans_date_nommee`) ; témoins renommés `test_famille_non_lue_par_semaine_CAUSE_DITE`, etc.*
3. **Arêtes parallèles** (la paire `language ← memory` porte une établie et deux réfutées) → trois traits distincts, décalés, les réfutées en pointillé — jamais superposés. Témoins : Task 4 (`decalages`, vue).
4. **Semaines ISO aux bornes d'année** (`2025-12-29` appartient à `2026-W01`, `2027-01-01` à `2026-W53`) → clés justes et densité continue à travers le changement d'année. Témoin : Task 1 (`test_semaine_iso_aux_bornes_d_annee`).
5. **JSON de taxonomie porteur d'un `NaN`** (Python l'accepte) ou d'une entrée sans identifiant → `ratio` null, entrée comptée et NOMMÉE, jamais un 500. Témoin : Task 1 (`test_taxonomie_entrees_illisibles_comptees_et_nommees`).

## Amendement A1 (2026-10-14) — revue adversariale de la tâche 1

La revue opus de la Task 1 (lecture seule) a rendu « prêt avec correctifs » : 0 critique, 6 importants, 10 mineurs. Le
livré était IDENTIQUE au texte de la Task 1 ci-dessous : les défauts étaient ceux du plan. Ils changent la forme de
`science_v1`, donc ils entrent AVANT que la Task 2 fige les schémas, dans le commit 4a (Task 1 seule — scission 4a / 4b
retenue par Master 2). Le code et les témoins de la Task 1 ci-dessous restent le texte APPROUVÉ ; le livré de 4a
diffère de lui par les points suivants, et les Tasks 2 à 5 ont été amendées pour consommer la nouvelle forme.

- **I1 — verdicts partiels dits.** Records illisibles de la famille record : une ligne `trouvailles :` (compte et
  raisons, « liste PARTIELLE ») ; tous illisibles (`indexes == 0`) → `verdicts: null`, jamais `[]`. Un état mal typé
  compté par l'index (`type_inattendu`) est relayé. Nouvelle clé `trouvailles.verdicts_partiels: bool | null`. Côté
  index (plan 1, I1-b) : un `verdict` non-chaîne n'est plus masqué par `status` (`etat` null, `type_inattendu`, comme
  le dit le §3.1 de la spec pour `verdict: {x: 1}`) — correctif et témoin dans 4a, qui touche donc un fichier livré.
- **I2 — la cause de chaque null.** `par_semaine[famille]` est TOUJOURS un objet `{date, semaines, sans_date,
  semaine_partielle, raison}` ; `raison` ∈ `RAISONS_SEMAINES` (`famille_non_lue`, `parite_rompue`, `sans_date_nommee`,
  `dates_absentes`, `historique_tronque`, `git_indisponible`). La vue écrit la cause publiée, jamais « famille non lue »
  ni « git indisponible » pour toutes.
- **I3 — le bloc `dates` de l'index** est recopié dans `trouvailles.dates` (D1 : lu avec son âge) ; l'intervalle dense
  va jusqu'à la borne (jour UTC de l'instantané des dates pour git, de `now` pour un nom daté) : les semaines vides
  jusque-là sont des zéros mesurés, et la dernière est `semaine_partielle`.
- **I4 — dates futures.** Un artefact daté après la borne va dans `sans_date` sous `date_future`, avec une ligne : plus
  de semaines futures de zéros, plus d'`OverflowError` (9999-12-31) qui refusait les trois blocs.
- **I5 — décision d'INTÉGRATEUR (Master 2, 2026-10-14 ; signalée à robla, qui peut revenir dessus).** Le plan
  approuvé ne recopiait que `ablation_verdict`, `ratio`, `n`, `record` ; la spec (§3.2) dit « établie (avec `strength`,
  `evidence`) ». Chaque arête porte désormais `preuves` : `specificity_control`, `functional_aliasing`,
  `ablation_target`, `coord_intact`, `emergence_bar`, `incapable_ceiling`, `ceiling_provenance` — une chaîne ou un
  nombre fini ; une autre valeur → null AVEC sa ligne ; un champ absent → null sans ligne (recopie fidèle). Raison :
  `check_agi_taxonomy` fait de `specificity_control` le contenu empirique de l'arête ; afficher « établie » sans lui
  servirait la forme d'une preuve sans son objet.
- **I6 — `lire_graphe` exercé** (témoins sous `tmp_path` : absent, JSON invalide, racine liste, `nodes` dict ou
  chaîne → illisible, compte connu) ; la ligne d'écart nomme les deux PÉRIMÈTRES (graphe SDR/ADR/EDR/REF, index
  docs/EDR) et n'attribue plus de cause.
- **Mineurs corrigés dans la même passe** : M1 (parité aussi contre `indexes`), M2 (valeurs mal typées ou non finies
  de la taxonomie NOMMÉES par indice et champ), M3 (`_nombre(10**400)` ne lève plus), M4 (parité compte/liste de la
  pipeline dite), M8 (docstring de `semaines_denses`), M9 (témoins : résultat porteur d'un verdict, branches
  « illisible » et « pas une liste » de `lire_taxonomie`). **Différés** (P2.170) : M5 (`lire_pipeline` lit
  `cpa._ROOT`, pas `racine`), M6 (comptes égaux, ensembles non comparés), M7 (doublons et boucles de la taxonomie non
  signalés), M10 (pré-inscriptions perdues quand la pipeline lève).
- **Interfaces changées** (Produces de la Task 1) : `semaines_denses(jours, borne=None)` ; constantes `PREUVES`
  (tuple ordonné des sept champs) et `RAISONS_SEMAINES` (frozenset) ; `trouvailles` gagne `verdicts_partiels` et
  `dates` ; chaque arête gagne `preuves`. Témoins : 34 fonctions, 42 cas (20 avant).

## Amendement A2 (2026-10-14) — revue adversariale de la tâche 2

Revue opus en lecture seule, AVANT le créneau (témoins écrits, implémentation préparée hors dépôt) : 0 critique, 5
importants, 9 mineurs. Tous traités par des témoins écrits avant le code, sauf trois mineurs différés.

- **I1 — parité des CHAMPS route ↔ module.** pydantic retire en silence une clé non déclarée ; seuls `preuves` et
  `par_semaine` étaient épinglés. Témoin : `test_science_route_sert_EXACTEMENT_la_sortie_du_module` (chaque bloc servi
  ÉGAL à la sortie de `compute_science`, chaque bloc non null).
- **I2 — le témoin de l'import refusé ne pouvait pas rougir** (« tools.pm.science » est dans le texte fixe du service) :
  cause injectée « yaml » ; et le blocage RÉEL — la sonde sans `tools.pm` du pilotage interroge aussi `/api/pm/science`
  (`test_le_backend_DEMARRE_sans_tools_pm_et_science_NOMME_l_absence`).
- **I3 — le script d'application** écrivait relativement au répertoire courant (depuis l'arbre principal, il aurait
  écrit dans l'arbre de la flotte) et n'était pas transactionnel : chemin absolu, branche vérifiée, tout calculé et
  asserté avant d'écrire, mode `--essai`.
- **I4 — le témoin du smoke manquait au plan** (fichiers, commandes, liste de commit) : ajouté ci-dessous.
- **I5 — E25** : les comptes 3 / 2 / « plus de 100 » sont RECALCULÉS depuis les JSON de la taxonomie et depuis
  `/api/pm/index`.
- **Mineurs corrigés** : contrôles positifs des témoins M6 (l'index reçu EST le cache) et de l'espion git (`all([])`) ;
  un cas du smoke où seule la clause « bloc refusé » rougit ; l'âge négatif de l'instantané et la cause du mode dégradé
  de l'index sont RELAYÉS dans l'aveugle de science sous « trouvailles : (index) » (le §9 exige « âge négatif ET une
  ligne », et la vue Science n'affiche que `/science`) — changement de `compute_science`, d'où `tools/pm/science.py` et
  ses témoins dans le commit 4b ; `compute_science` ne mute jamais l'index partagé (témoin) ; TTL testé dans les deux
  sens ; `_servable(…, "science")` ; `preuves` en `str | int | float | None` (un entier reste entier) ; la ligne
  `pipeline : famille preinscription` épinglée par la route. **Différés** (P2.170) : le même libellé « pilotage » latent
  dans `index_service` ; l'instant de l'âge recopié (celui de l'index, jusqu'à 60 s de cache) — documenté ici.

---

## Préalable

Worktree `.worktrees/front`, branche `tmp/front`. Avant la Task 1 et avant chaque commit : `git fetch`, puis fusionner la
pointe de `feat/d1-prod-pairing` DANS `tmp/front` (jamais de `MERGE_HEAD` dans l'arbre principal) et relire le compte
d'entrées du backlog. Le plan 1 doit être livré (l'index et `index_service._blocs_servables` paramétré existent).

## Structure des fichiers

| fichier | rôle | tâche |
| --- | --- | --- |
| `tools/pm/science.py` | `DATE_PAR_FAMILLE`, lecteurs `lire_pipeline` / `lire_taxonomie` / `lire_graphe`, `semaine_iso`, `semaines_denses`, `compute_science`, `main` | 1 |
| `tests/sandbox/test_pm_science.py` | témoins de `compute_science` et des lecteurs | 1 |
| `tests/sandbox/test_instrument_calibration.py`, `tools/instrument_calibration_baseline.json` | déclaration `CALIBRATED` et son gel | 1 |
| `docs/roadmap/PRIORITES_ET_DETTES.md` | clause de P2.84 repointée sur la dernière vue | 1 |
| `backend/app/services/science_service.py`, `backend/app/routes/pm.py`, `backend/app/schemas.py`, `tests/test_backend.py`, `.github/workflows/ci.yml`, `frontend/openapi.json`, `frontend/src/api/schema.ts` | route `/api/pm/science` | 2 |
| `frontend/src/api/pm.ts`, `queryKeys.ts`, `lib/polling.ts`, `tabs.ts`, `App.tsx`, `lib/science.ts`, `components/science/scienceFixture.ts`, `components/science/PipelineView.tsx` (+ tests) | famille Science, vue Pipeline | 3 |
| `frontend/src/lib/taxonomie.ts`, `components/science/TaxonomieView.tsx` (+ tests), `styles.css` | vue Taxonomie | 4 |
| `components/science/TrouvaillesView.tsx` (+ test), `lib/science.ts`, `docs/roadmap/FRONTEND.md`, backlog | vue Trouvailles ; P2.84 close | 5 |

---

### Task 1 : `tools/pm/science.py` — les trois blocs

**Files:**
- Create: `tools/pm/science.py`, `tests/sandbox/test_pm_science.py`
- Modify: `tests/sandbox/test_instrument_calibration.py` (dict `CALIBRATED`), `tools/instrument_calibration_baseline.json` (`declarations_ignorees`), `docs/roadmap/PRIORITES_ET_DETTES.md` (clause de P2.84)

**Interfaces:**
- Consumes: `index_v1` (plan 1 : `familles[].{nom, fichiers, champs_introuvables}`, `artefacts[].{famille, chemin, titre, etat, etat_source, gate, scelle, date_ajout_git, date_declaree}`, `dates.historique`) ; `tools.pm.index_artefacts.FAMILLES`, `indexer`, `read_dates` ; `tools.check_preregistration_applied.{couverture, familles_sans_record, RacineSansSource}` ; `src.paths.{data_file, results_file}`.
- Produces: `SCHEMA = "science_v1"` ; `DATE_PAR_FAMILLE: dict[str, str]` ; `lire_pipeline() -> {"couverture": dict | None, "familles_sans_record": list | None, "raison": str | None}` ; `lire_taxonomie(racine) -> {"chemin", "raison", "capabilities", "demands", "refuted"}` ; `lire_graphe(racine) -> {"verdicts": int | None, "chemin", "raison"}` ; `semaine_iso(jour: str) -> str` ; `semaines_denses(jours) -> dict[str, int]` ; `compute_science(index, pipeline, taxonomie, graphe, now) -> dict` (clés `schema, generated_at, repo_root, aveugle, pipeline, taxonomie, trouvailles`).

- [ ] **Step 1 : écrire les témoins**

`tests/sandbox/test_pm_science.py` :

```python
# -*- coding: utf-8 -*-
"""Lot 2 « Science » (P2.84). EXEMPTION DÉCLARÉE de la garde de bail : aucun monde, aucun bail.
Aucun test n'écrit dans l'arbre : sources injectées, fichiers sous tmp_path."""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import index_artefacts as IX  # noqa: E402
from tools.pm import science as S  # noqa: E402

_LEASE_GUARD_EXEMPT = True
NOW = 1_800_000_000.0
PIPE = {"couverture": {"inspectees": 20, "sans_grandeur": 13, "sans_record": 2, "total": 35},
        "familles_sans_record": ["EVO-022", "EVO-028-SMOKE"], "raison": None}
GRAPHE = {"verdicts": 2, "chemin": "C:/depot/graphe.json", "raison": None}


def _art(famille, chemin, **k):
    a = {"famille": famille, "chemin": chemin, "titre": None, "date_declaree": None, "date_source": None,
         "date_ajout_git": None, "etat": None, "etat_source": None, "regime": None, "scelle": None, "gate": None,
         "liens": []}
    a.update(k)
    return a


def _index(arts, historique="complet"):
    """index_v1 COHÉRENT : chaque famille réelle, ses comptes et ses manques de date recalculés depuis `arts` comme
    l'indexeur les compterait (sans date d'ajout : sans_ajout_trouve si l'instantané est complet, dates_absentes
    sinon ; sans date déclarée : nom_non_date)."""
    familles = []
    for f in IX.FAMILLES:
        siens = [a for a in arts if a["famille"] == f.nom]
        manques = {}
        for champ, raison in (("date_ajout_git", "sans_ajout_trouve" if historique == "complet" else "dates_absentes"),
                              ("date_declaree", "nom_non_date")):
            n = sum(1 for a in siens if not a[champ])
            manques[champ] = {raison: n} if n else {}
        familles.append({"nom": f.nom, "motif": f.motif, "repertoire": f.nom, "exclus": [], "fichiers": len(siens),
                         "indexes": len(siens), "illisibles": [], "champs_introuvables": manques,
                         "format_declare": {}})
    dates = None if historique is None else {"generated_at": NOW - 60, "age_s": 60.0, "head": "abc",
                                             "historique": historique}
    return {"schema": "index_v1", "generated_at": NOW, "repo_root": "C:/depot", "aveugle": [], "dates": dates,
            "familles": familles, "hors_familles": None, "artefacts": arts}


def _taxo():
    return {"chemin": "C:/depot/agi_taxonomy", "raison": None,
            "capabilities": [{"id": "perception", "title": "P", "record": "docs/EDR/a.md"}, {"id": "memory"}],
            "demands": [{"capability": "memory", "prerequisite": "perception", "strength": "hard",
                         "evidence": {"ablation_verdict": "X_DEMANDED", "ratio": 3.9, "n": 12,
                                      "record": "docs/EDR/b.md"}, "reason": "r"}],
            "refuted": [{"capability": "memory", "prerequisite": "perception", "verdict": "NEGATIVE_NOT_MEASURABLE",
                         "reason": "r2", "evidence": {"n": 12, "record": "docs/EDR/c.md"},
                         "superseded_by": "docs/EDR/b.md"}]}


def _science(arts, **k):
    return S.compute_science(k.get("index") or _index(arts, k.get("historique", "complet")), k.get("pipe", PIPE),
                             k.get("taxo") or _taxo(), k.get("graphe", GRAPHE), NOW)


def test_NO_OP_EXACT_toutes_sources_absentes():
    index = {"schema": "index_v1", "generated_at": NOW, "repo_root": None, "aveugle": ["index: RuntimeError: x"],
             "dates": None, "familles": None, "hors_familles": None, "artefacts": None}
    out = S.compute_science(index, {"couverture": None, "familles_sans_record": None, "raison": "RacineSansSource: x"},
                            {"chemin": "C:/x", "raison": "capabilities.json introuvable", "capabilities": None,
                             "demands": None, "refuted": None},
                            {"verdicts": None, "chemin": "C:/x/g.json", "raison": "introuvable"}, NOW)
    assert (out["pipeline"], out["taxonomie"], out["trouvailles"]) == (None, None, None)
    prefixes = {a.split(" : ")[0] for a in out["aveugle"]}
    assert prefixes == {"pipeline", "taxonomie", "trouvailles"}, out["aveugle"]
    assert not any(a.startswith(("science:", "index:")) for a in out["aveugle"])


def test_pipeline_recopiee_a_l_identique_et_preinscriptions_de_l_index():
    arts = [_art("preinscription", "docs/preregistrations/A.json", titre="A", scelle=True, date_ajout_git="2026-09-02"),
            _art("preinscription", "docs/preregistrations/B.json")]
    p = _science(arts)["pipeline"]
    assert p["couverture"] == PIPE["couverture"] and p["familles_sans_record"] == ["EVO-022", "EVO-028-SMOKE"]
    assert p["preinscriptions"] == [
        {"chemin": "docs/preregistrations/A.json", "titre": "A", "scelle": True, "date_ajout_git": "2026-09-02"},
        {"chemin": "docs/preregistrations/B.json", "titre": None, "scelle": None, "date_ajout_git": None}]


def test_pipeline_module_SANS_racine_leve_et_devient_null(tmp_path, monkeypatch):
    """Contre-exemple B2 gelé : sans ses répertoires, le module rendait (0, 0, 0, 0) ; depuis P2.135 il lève."""
    from tools import check_preregistration_applied as cpa
    monkeypatch.setattr(cpa, "_PREREG", str(tmp_path / "absent_prereg"))
    monkeypatch.setattr(cpa, "_EDR", str(tmp_path / "absent_edr"))
    lu = S.lire_pipeline()
    assert lu["couverture"] is None and lu["raison"].startswith("RacineSansSource")
    out = _science([], pipe=lu)
    assert out["pipeline"] is None
    assert any(a.startswith("pipeline : ") and "RacineSansSource" in a for a in out["aveugle"])


def test_pipeline_famille_preinscription_non_lue_liste_null_jamais_vide():
    index = _index([])
    next(f for f in index["familles"] if f["nom"] == "preinscription")["fichiers"] = None
    out = _science([], index=index)
    assert out["pipeline"]["preinscriptions"] is None
    assert any(a.startswith("pipeline : ") and "pré-inscriptions" in a for a in out["aveugle"])


def test_taxonomie_REELLE_etablies_et_refutees_depassees():
    from tools.pm.pilotage import racine_depot
    t = S.compute_science(_index([]), PIPE, S.lire_taxonomie(racine_depot()), GRAPHE, NOW)["taxonomie"]
    etablies = [a for a in t["aretes"] if a["nature"] == "etablie"]
    refutees = [a for a in t["aretes"] if a["nature"] == "refutee"]
    assert (len(t["capacites"]), len(etablies), len(refutees)) == (4, 3, 2)
    assert all(a["depassee_par"] for a in refutees) and all(a["verdict"] for a in t["aretes"])


def test_taxonomie_prediction_une_refutee_retiree_est_NOMMEE_absente():
    from tools.pm.pilotage import racine_depot
    source = S.lire_taxonomie(racine_depot())
    retiree = copy.deepcopy(source)
    perdue = retiree["refuted"].pop(0)
    t = S.compute_science(_index([]), PIPE, retiree, GRAPHE, NOW)["taxonomie"]
    refutees = [a for a in t["aretes"] if a["nature"] == "refutee"]
    assert len(refutees) == 1 and perdue["evidence"]["record"] not in {a["record"] for a in refutees}


def test_taxonomie_entrees_illisibles_comptees_et_nommees():
    taxo = _taxo()
    taxo["demands"].append({"capability": "memory"})                           # sans prérequis
    taxo["demands"][0]["evidence"]["ratio"] = float("nan")                     # json.load accepte NaN
    taxo["refuted"].append({"capability": "language", "prerequisite": "vision", "verdict": "X"})
    out = _science([], taxo=taxo)
    t = out["taxonomie"]
    assert len(t["aretes"]) == 3 and t["aretes"][0]["ratio"] is None
    assert any("1 entrée(s) de demands.json" in a for a in out["aveugle"])
    assert any("capacité non déclarée" in a and "language" in a and "vision" in a for a in out["aveugle"])


def test_taxonomie_absente_null_et_ligne(tmp_path, monkeypatch):
    monkeypatch.delenv("AGAGI_DATA_ROOT", raising=False)
    lu = S.lire_taxonomie(str(tmp_path))
    assert lu["raison"] == "capabilities.json introuvable" and lu["capabilities"] is None
    out = _science([], taxo=lu)
    assert out["taxonomie"] is None and any(a.startswith("taxonomie : ") for a in out["aveugle"])


def test_trouvailles_verdicts_de_l_index_et_ecart_au_graphe():
    arts = [_art("record", "docs/EDR/1.md", titre="A", etat="X_DEMANDED", etat_source="verdict", gate="G1",
                 date_ajout_git="2026-09-01"),
            _art("record", "docs/EDR/2.md", etat="NEG", etat_source="verdict"),
            _art("record", "docs/EDR/3.md", etat="open", etat_source="status")]
    tr = _science(arts)["trouvailles"]
    assert [v["chemin"] for v in tr["verdicts"]] == ["docs/EDR/1.md", "docs/EDR/2.md"]
    assert tr["verdicts"][0] == {"chemin": "docs/EDR/1.md", "titre": "A", "verdict": "X_DEMANDED", "gate": "G1",
                                 "date_ajout_git": "2026-09-01"}
    out = _science(arts, graphe={"verdicts": 5, "chemin": "C:/depot/graphe.json", "raison": None})
    assert any("compte 5 verdicts" in a and "en lit 2" in a for a in out["aveugle"])
    assert not any("compte" in a for a in _science(arts)["aveugle"])       # 2 contre 2 : aucune ligne d'écart


def test_graphe_absent_ecart_non_mesure_verdicts_servis():
    arts = [_art("record", "docs/EDR/1.md", etat="V", etat_source="verdict")]
    out = _science(arts, graphe={"verdicts": None, "chemin": "C:/depot/graphe.json", "raison": "introuvable"})
    assert out["trouvailles"]["compte_graphe"] is None and len(out["trouvailles"]["verdicts"]) == 1
    assert any(a.startswith("trouvailles : ") and "non mesuré" in a for a in out["aveugle"])


def test_index_degrade_trouvailles_null_taxonomie_servie():
    index = _index([])
    index.update(familles=None, artefacts=None, aveugle=["index: RuntimeError: boum"])
    out = _science([], index=index)
    assert out["trouvailles"] is None and out["taxonomie"] is not None
    assert out["pipeline"]["preinscriptions"] is None


def test_par_semaine_DENSE_semaine_intermediaire_a_zero():
    arts = [_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01"),
            _art("record", "docs/EDR/2.md", date_ajout_git="2026-09-15"),
            _art("record", "docs/EDR/3.md")]
    ps = _science(arts)["trouvailles"]["par_semaine"]
    assert ps["record"] == {"date": "date_ajout_git", "semaines": {"2026-W36": 1, "2026-W37": 0, "2026-W38": 1},
                            "sans_date": {"sans_ajout_trouve": 1}}
    assert ps["adr"] == {"date": "date_ajout_git", "semaines": {}, "sans_date": {}}   # répertoire lu, vide : mesuré


def test_par_semaine_git_indisponible_null_et_sans_date_de_l_index():
    arts = [_art("record", "docs/EDR/1.md"), _art("spec", "docs/superpowers/specs/2026-09-01-s.md",
                                                  date_declaree="2026-09-01")]
    ps = _science(arts, historique=None)["trouvailles"]["par_semaine"]
    assert ps["record"] == {"date": "date_ajout_git", "semaines": None, "sans_date": {"dates_absentes": 1}}
    assert ps["spec"]["semaines"] == {"2026-W36": 1}                          # datée par son nom : mesurable


def test_semaine_iso_aux_bornes_d_annee():
    assert S.semaine_iso("2025-12-29") == "2026-W01"
    assert S.semaine_iso("2026-12-31") == "2026-W53" and S.semaine_iso("2027-01-01") == "2026-W53"
    assert list(S.semaines_denses(["2026-12-28", "2027-01-11"])) == ["2026-W53", "2027-W01", "2027-W02"]


def test_famille_non_lue_par_semaine_null():
    index = _index([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01")])
    fam = next(f for f in index["familles"] if f["nom"] == "adr")
    fam.update(fichiers=None, indexes=None, champs_introuvables=None)
    assert _science([], index=index)["trouvailles"]["par_semaine"]["adr"] is None


def test_famille_inconnue_nommee_jamais_comptee():
    index = _index([])
    index["familles"].append({"nom": "nouvelle", "motif": "*.md", "repertoire": "x", "exclus": [], "fichiers": 0,
                              "indexes": 0, "illisibles": [], "champs_introuvables": {}, "format_declare": {}})
    out = _science([], index=index)
    assert out["trouvailles"]["par_semaine"]["nouvelle"] is None
    assert any("famille nouvelle sans date nommée" in a for a in out["aveugle"])


def test_parite_rompue_famille_null_et_ligne():
    index = _index([_art("record", "docs/EDR/1.md")])
    next(f for f in index["familles"] if f["nom"] == "record")["champs_introuvables"]["date_ajout_git"] = {}
    out = _science([], index=index)
    assert out["trouvailles"]["par_semaine"]["record"] is None
    assert any(a.startswith("trouvailles : famille record") and "servie à null" in a for a in out["aveugle"])


def test_cles_de_sortie_enumerees_aucune_tendance():
    out = _science([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01", etat="V", etat_source="verdict")])
    assert set(out) == {"schema", "generated_at", "repo_root", "aveugle", "pipeline", "taxonomie", "trouvailles"}
    assert set(out["trouvailles"]) == {"verdicts", "compte_graphe", "par_semaine"}
    for e in out["trouvailles"]["par_semaine"].values():
        assert e is None or set(e) == {"date", "semaines", "sans_date"}


def test_DATE_PAR_FAMILLE_couvre_exactement_les_familles_de_l_index():
    assert set(S.DATE_PAR_FAMILLE) == {f.nom for f in IX.FAMILLES}


def test_REEL_bout_a_bout():
    from tools.pm.pilotage import racine_depot
    r = racine_depot()
    index = IX.indexer(r, IX.read_dates(r), NOW)
    out = S.compute_science(index, S.lire_pipeline(), S.lire_taxonomie(r), S.lire_graphe(r), NOW)
    assert out["pipeline"]["couverture"]["total"] > 0
    assert len(out["trouvailles"]["verdicts"]) > 100
    assert not any(a.startswith(("science:", "index:")) for a in out["aveugle"]), out["aveugle"]
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `python -m pytest tests/sandbox/test_pm_science.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'science' from 'tools.pm'` (collecte).

- [ ] **Step 3 : écrire le module**

`tools/pm/science.py` :

```python
# -*- coding: utf-8 -*-
"""Lot 2 « Science » du dashboard (P2.84) — spec docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md
(§3.2, §9).

`compute_science` est PUR : il reçoit l'index (`index_v1`) et trois sources déjà LUES par les lecteurs ci-dessous, et
rend `science_v1`. Aucune vue ne recalcule un verdict (condition 4) : la pipeline recopie
`tools/check_preregistration_applied`, la taxonomie recopie les trois JSON du répertoire agi_taxonomy des données, les
trouvailles recopient les verdicts DÉCLARÉS que l'index a lus. Un bloc dont la source manque vaut `null` et une ligne
préfixée de son nom — jamais un zéro (porte 14). `science:` et `index:` sont réservés aux modes dégradés des services.
"""
import argparse
import collections
import datetime
import json
import math
import os
import sys
import time

SCHEMA = "science_v1"

# La date qui compte une famille par semaine (spec §3.2) : git pour les familles qui ne déclarent pas de date, le nom
# daté pour les autres. Une famille de l'index absente d'ici est NOMMÉE et jamais comptée (témoin de couverture).
DATE_PAR_FAMILLE = {
    "record": "date_ajout_git", "adr": "date_ajout_git", "ref": "date_ajout_git", "sdr": "date_ajout_git",
    "resultat": "date_ajout_git", "preinscription": "date_ajout_git",
    "spec": "date_declaree", "plan": "date_declaree", "revue": "date_declaree",
}
TAXONOMIE = ("capabilities", "demands", "refuted")


def _ancre(racine, chemin):
    return chemin if os.path.isabs(chemin) else os.path.join(racine, chemin)


def _texte(v):
    return v.strip() if isinstance(v, str) and v.strip() else None


def _nombre(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def _entier(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def lire_pipeline():
    """Recopie de `couverture()` et `familles_sans_record()`. ⚠️ P2.135 : sans ses répertoires, le module LÈVE
    `RacineSansSource` (il rendait `(0, 0, 0, 0)`, B2) ; toute exception est NOMMÉE dans `raison`, jamais des zéros."""
    try:
        from tools import check_preregistration_applied as cpa
        inspectees, sans_grandeur, sans_record, total = cpa.couverture()
        orphelines = cpa.familles_sans_record()
    except Exception as exc:                                   # noqa: BLE001 — NOMMÉ, jamais un zéro
        return {"couverture": None, "familles_sans_record": None, "raison": f"{type(exc).__name__}: {exc}"}
    return {"couverture": {"inspectees": inspectees, "sans_grandeur": sans_grandeur, "sans_record": sans_record,
                           "total": total},
            "familles_sans_record": list(orphelines), "raison": None}


def lire_taxonomie(racine):
    """Les trois fichiers de la taxonomie AGI, par `paths.data_file` ancré sur la racine (porte 12)."""
    from src import paths
    rep = _ancre(racine, paths.data_file("agi_taxonomy")).replace("\\", "/")
    vide = {n: None for n in TAXONOMIE}
    out = {"chemin": rep, "raison": None, **vide}
    for n in TAXONOMIE:
        try:
            with open(f"{rep}/{n}.json", encoding="utf-8") as fh:
                valeur = json.load(fh)
        except OSError:
            return {**out, **vide, "raison": f"{n}.json introuvable"}
        except (ValueError, RecursionError) as exc:
            return {**out, **vide, "raison": f"{n}.json illisible (JSON invalide : {exc})"}
        if not isinstance(valeur, list):
            return {**out, **vide, "raison": f"{n}.json n'est pas une liste"}
        out[n] = valeur
    return out


def lire_graphe(racine):
    """Le compte de verdicts du graphe de records, pour publier l'ÉCART avec l'index seulement (I9 : dérivé, il peut
    être périmé)."""
    from src import paths
    p = _ancre(racine, paths.results_file("records_graph.json")).replace("\\", "/")
    try:
        with open(p, encoding="utf-8") as fh:
            noeuds = json.load(fh)["graph"]["nodes"]
        n = sum(1 for x in noeuds if isinstance(x, dict) and _texte(x.get("verdict")))
    except OSError:
        return {"verdicts": None, "chemin": p, "raison": "introuvable"}
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        return {"verdicts": None, "chemin": p, "raison": f"illisible ({type(exc).__name__}: {exc})"}
    return {"verdicts": n, "chemin": p, "raison": None}


def semaine_iso(jour):
    """`"AAAA-Www"` de la semaine ISO d'un jour `AAAA-MM-JJ` (déjà en UTC dans l'index)."""
    annee, semaine, _ = datetime.date.fromisoformat(jour).isocalendar()
    return f"{annee}-W{semaine:02d}"


def semaines_denses(jours):
    """`{"AAAA-Www": n}` DENSE entre la première et la dernière semaine : la source de date est complète, un zéro y
    est une mesure (M4). Aucune clé hors de cet intervalle."""
    dates = sorted(datetime.date.fromisoformat(j) for j in jours)
    compte = collections.Counter(semaine_iso(d.isoformat()) for d in dates)
    out = {}
    if dates:
        lundi = dates[0] - datetime.timedelta(days=dates[0].weekday())
        while lundi <= dates[-1]:
            cle = semaine_iso(lundi.isoformat())
            out[cle] = compte[cle]
            lundi += datetime.timedelta(days=7)
    return out


def _famille(index, nom):
    return next((f for f in index.get("familles") or [] if f.get("nom") == nom), None)


def _pipeline(index, source, aveugle):
    if source.get("raison") or source.get("couverture") is None:
        aveugle.append(f"pipeline : couverture illisible ({source.get('raison')}) -- INCONNUE, jamais (0, 0, 0, 0)")
        return None
    fam = _famille(index, "preinscription")
    if index.get("artefacts") is None or fam is None or fam.get("fichiers") is None:
        aveugle.append("pipeline : famille preinscription non lue par l'index -- liste des pré-inscriptions INCONNUE")
        pre = None
    else:
        pre = [{"chemin": a["chemin"], "titre": a.get("titre"), "scelle": a.get("scelle"),
                "date_ajout_git": a.get("date_ajout_git")}
               for a in index["artefacts"] if a.get("famille") == "preinscription"]
    return {"couverture": dict(source["couverture"]), "familles_sans_record": list(source["familles_sans_record"]),
            "preinscriptions": pre}


def _taxonomie(source, aveugle):
    if source.get("raison"):
        aveugle.append(f"taxonomie : {source.get('chemin')} : {source['raison']} -- graphe INCONNU")
        return None
    rejets = collections.Counter()
    capacites = []
    for c in source["capabilities"]:
        ident = _texte(c.get("id")) if isinstance(c, dict) else None
        if ident is None:
            rejets["capabilities"] += 1
            continue
        capacites.append({"id": ident, "titre": _texte(c.get("title")), "record": _texte(c.get("record"))})
    aretes = []
    for nature, cle in (("etablie", "demands"), ("refutee", "refuted")):
        for e in source[cle]:
            cap = _texte(e.get("capability")) if isinstance(e, dict) else None
            pre = _texte(e.get("prerequisite")) if isinstance(e, dict) else None
            if cap is None or pre is None:
                rejets[cle] += 1
                continue
            ev = e.get("evidence") if isinstance(e.get("evidence"), dict) else {}
            aretes.append({"capacite": cap, "prerequis": pre, "nature": nature, "force": _texte(e.get("strength")),
                           "verdict": _texte(ev.get("ablation_verdict") if nature == "etablie" else e.get("verdict")),
                           "ratio": _nombre(ev.get("ratio")), "n": _entier(ev.get("n")),
                           "record": _texte(ev.get("record")), "raison": _texte(e.get("reason")),
                           "depassee_par": _texte(e.get("superseded_by"))})
    for cle, n in sorted(rejets.items()):
        aveugle.append(f"taxonomie : {n} entrée(s) de {cle}.json sans identifiant lisible -- non tracée(s)")
    hors = sorted({x for a in aretes for x in (a["capacite"], a["prerequis"])} - {c["id"] for c in capacites})
    if hors:
        aveugle.append(f"taxonomie : arête(s) vers une capacité non déclarée dans capabilities.json ({', '.join(hors)})")
    return {"capacites": capacites, "aretes": aretes}


def _par_semaine(index, aveugle):
    """Par famille, sur UNE date nommée ; parité vérifiée (datés + sans date = indexés), sinon la famille est null."""
    git_complet = (index.get("dates") or {}).get("historique") == "complet"
    out = {}
    for f in index["familles"]:
        nom, champ = f["nom"], DATE_PAR_FAMILLE.get(f["nom"])
        if champ is None:
            aveugle.append(f"trouvailles : famille {nom} sans date nommée (DATE_PAR_FAMILLE) -- non comptée par semaine")
            out[nom] = None
            continue
        if f.get("fichiers") is None or f.get("champs_introuvables") is None:
            out[nom] = None                                     # famille non lue : sa ligne est dans l'index
            continue
        siens = [a for a in index["artefacts"] if a.get("famille") == nom]
        sans = dict(f["champs_introuvables"].get(champ) or {})
        jours = [a[champ] for a in siens if a.get(champ)]
        if len(jours) + sum(sans.values()) != len(siens):
            aveugle.append(f"trouvailles : famille {nom} : {len(jours)} daté(s) + {sum(sans.values())} sans date pour "
                           f"{len(siens)} indexé(s) -- parité rompue, servie à null")
            out[nom] = None
            continue
        indispo = champ == "date_ajout_git" and not git_complet
        out[nom] = {"date": champ, "semaines": None if indispo else semaines_denses(jours), "sans_date": sans}
    return out


def _trouvailles(index, graphe, aveugle):
    rec = _famille(index, "record")
    if rec is None or rec.get("fichiers") is None:
        aveugle.append("trouvailles : famille record non lue par l'index -- verdicts INCONNUS, jamais 0")
        verdicts = None
    else:
        verdicts = [{"chemin": a["chemin"], "titre": a.get("titre"), "verdict": a["etat"], "gate": a.get("gate"),
                     "date_ajout_git": a.get("date_ajout_git")}
                    for a in index["artefacts"] if a.get("famille") == "record" and a.get("etat_source") == "verdict"]
    if graphe.get("raison"):
        aveugle.append(f"trouvailles : {graphe.get('chemin')} {graphe['raison']} -- écart au graphe de records non "
                       "mesuré")
    elif verdicts is not None and graphe.get("verdicts") != len(verdicts):
        aveugle.append(f"trouvailles : {graphe.get('chemin')} compte {graphe.get('verdicts')} verdicts, l'index en lit "
                       f"{len(verdicts)} dans les records -- graphe à regénérer (tools/consolidate_records.py)")
    return {"verdicts": verdicts, "compte_graphe": graphe.get("verdicts"), "par_semaine": _par_semaine(index, aveugle)}


def compute_science(index, pipeline, taxonomie, graphe, now):
    """`science_v1` — PUR ; chaque bloc null avec sa ligne quand sa source manque."""
    aveugle = []
    bloc_pipeline = _pipeline(index, pipeline, aveugle)
    bloc_taxonomie = _taxonomie(taxonomie, aveugle)
    if index.get("familles") is None or index.get("artefacts") is None:
        aveugle.append("trouvailles : index sans familles ou sans artefacts (mode dégradé de l'index) -- trouvailles "
                       "INCONNUES")
        bloc_trouvailles = None
    else:
        bloc_trouvailles = _trouvailles(index, graphe, aveugle)
    return {"schema": SCHEMA, "generated_at": float(now), "repo_root": index.get("repo_root"), "aveugle": aveugle,
            "pipeline": bloc_pipeline, "taxonomie": bloc_taxonomie, "trouvailles": bloc_trouvailles}


def main(argv=None):
    """`--json` imprime `science_v1` (n'écrit rien, ne lance pas git) ; sans option, un résumé par bloc."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    from tools.pm import index_artefacts
    from tools.pm.pilotage import racine_depot
    racine = args.repo_root or racine_depot()
    now = time.time()
    index = index_artefacts.indexer(racine, index_artefacts.read_dates(racine), now)
    out = compute_science(index, lire_pipeline(), lire_taxonomie(racine), lire_graphe(racine), now)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print(f"[science] {out['schema']} -- {len(out['aveugle'])} aveuglement(s)")
    for a in out["aveugle"]:
        print("  AVEUGLE :", a)
    for bloc in ("pipeline", "taxonomie", "trouvailles"):
        print(f"  {bloc:<12} {'servi' if out[bloc] is not None else 'NULL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : les témoins passent**

Run: `python -m pytest tests/sandbox/test_pm_science.py -q -p no:cacheprovider`
Expected: PASS (20 tests).

- [ ] **Step 5 : mutants (en mémoire, jamais sur disque), contrôle intact d'abord**

Un script du scratchpad remplace une fonction dans le processus et lance les témoins par `pytest.main` : (a)
`semaines_denses` qui ne remplit pas les semaines vides (`out[cle] = compte[cle]` seulement si `compte[cle]`) ; (b)
`_pipeline` qui rend `[]` au lieu de `None` pour une famille non lue ; (c) `lire_pipeline` qui rend `(0, 0, 0, 0)` sur
exception ; (d) `_par_semaine` sans contrôle de parité ; (e) `_taxonomie` qui ignore `superseded_by`.
Expected: les cinq TUÉS ; consigner au grand livre ceux qui survivent et ajouter le témoin manquant.

- [ ] **Step 6 : déclarer l'instrument, repointer la clause, portes ciblées**

Dans `CALIBRATED` (`tests/sandbox/test_instrument_calibration.py`), après les entrées de `index_artefacts` :

```python
    "tools/pm/science.py::compute_science": ["no-op:sources-absentes-blocs-null", "injection:couverture-recopiee",
                                             "prediction:une-refutee-retiree", "dense:semaine-intermediaire-zero",
                                             "parite:famille-null", "reel:bout-a-bout"],
```

Ajouter `"tools/pm/science.py::compute_science"` à `declarations_ignorees` de `tools/instrument_calibration_baseline.json`
(ordre alphabétique) — le cliquet ne détecte pas ce nom (P2.83), comme `compute_pilotage`. Dans le backlog, la clause
de P2.84 devient `<!-- closes_when:path_present=frontend/src/components/science/TrouvaillesView.tsx -->` (sinon elle
serait satisfaite dès ce commit, entrée ouverte).

Run: `python tools/check_instrument_calibration.py`, `python tools/check_data_paths.py`, `python tools/check_fabricated_defaults.py`, `python tools/check_backlog_freshness.py`
Expected: « 13 déclaration(s) ignorée(s), toutes légataires » ; « NOUVEAUX : 0 » ; « Aucun nouveau » ; exit 0.

- [ ] **Step 7 : coût mesuré**

Run: `python -m tools.jobs.doctor` puis trois fois `python -c "import time; from tools.pm import science as S, index_artefacts as IX; from tools.pm.pilotage import racine_depot; r = racine_depot(); i = IX.indexer(r, IX.read_dates(r), time.time()); t = time.perf_counter(); S.compute_science(i, S.lire_pipeline(), S.lire_taxonomie(r), S.lire_graphe(r), time.time()); print(round(time.perf_counter() - t, 2))"`
Expected: une durée par passe (attendu < 1 s : `couverture()` et `familles_sans_record()` relisent chacune les EDR) ; la
publier au §6 de la spec avec la charge notée (« `compute_science` : à mesurer au plan 2 » devient la mesure).

---

### Task 2 : `GET /api/pm/science` — service, route, schémas, smoke, image

**Files:**
- Create: `backend/app/services/science_service.py`
- Modify: `backend/app/schemas.py` (après `IndexV1`), `backend/app/routes/pm.py`, `tests/test_backend.py`, `tests/sandbox/test_ci_smoke_index.py` (A2, I4), `tools/pm/science.py` et `tests/sandbox/test_pm_science.py` (A2, relais), `.github/workflows/ci.yml`, `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `science.compute_science`, `science.lire_*` (Task 1) ; `index_service.get_index()` et `index_service._blocs_servables(out, blocs, adaptateurs)` (plan 1) ; `pilotage_service._EnveloppeRefusee, _resume, _servable, _texte_servable`.
- Produces: `get_science(ttl_s=60.0) -> dict` ; `_vider_cache()` ; route `GET /api/pm/science` (`ScienceV1`, par alias) ; modèles `ScienceCouverture`, `SciencePreinscription`, `Pipeline`, `TaxonomieCapacite`, `TaxonomiePreuves`, `TaxonomieArete`, `Taxonomie`, `TrouvailleVerdict`, `SemainesFamille`, `Trouvailles`, `ScienceV1`.

- [ ] **Step 1 : écrire les témoins backend**

Dans `tests/test_backend.py`, après les témoins de l'index :

```python
def test_science_repond_200_schema_science_v1_blocs_servis() -> None:
    from backend.app.services import index_service as ix, science_service as sc
    ix._vider_cache()
    sc._vider_cache()
    r = client.get("/api/pm/science")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "science_v1" and not any(a.startswith("science:") for a in d["aveugle"]), d["aveugle"]
    assert d["pipeline"]["couverture"]["total"] > 0
    natures = [a["nature"] for a in d["taxonomie"]["aretes"]]
    assert natures.count("etablie") == 3 and natures.count("refutee") == 2
    assert all(a["preuves"]["specificity_control"] == "pass" for a in d["taxonomie"]["aretes"]
               if a["nature"] == "etablie")                                   # A1 (I5) : servi par alias
    assert len(d["trouvailles"]["verdicts"]) > 100
    assert all(set(e) == {"date", "semaines", "sans_date", "semaine_partielle", "raison"}
               for e in d["trouvailles"]["par_semaine"].values())              # A1 (I2) : jamais null


def test_science_lit_l_index_dans_le_MEME_cache(monkeypatch) -> None:
    """M6 : /science n'appelle pas indexer quand le cache de l'index est chaud."""
    from backend.app.services import index_service as ix, science_service as sc
    ix._vider_cache()
    ix.get_index()
    appels = {"n": 0}
    vrai = ix.index_artefacts.indexer

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(ix.index_artefacts, "indexer", _compte)
    sc._vider_cache()
    assert client.get("/api/pm/science").status_code == 200
    assert appels["n"] == 0


def test_science_compute_qui_leve_devient_une_ligne_science_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import science_service as sc

    def _boum(*a, **k):
        raise RuntimeError("science cassée")
    monkeypatch.setattr(sc.science, "compute_science", _boum)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["aveugle"][0].startswith("science: RuntimeError")
    assert (d["pipeline"], d["taxonomie"], d["trouvailles"]) == (None, None, None)


def test_science_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import science_service as sc
    vrai, appels = sc.science.compute_science, {"n": 0}

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(sc.science, "compute_science", _compte)
    sc._vider_cache()
    client.get("/api/pm/science")
    client.get("/api/pm/science")
    assert appels["n"] == 1


def test_science_bloc_de_type_etranger_devient_null_sans_500(monkeypatch) -> None:
    from backend.app.services import science_service as sc
    vrai = sc.science.compute_science

    def _etranger(*a, **k):
        out = vrai(*a, **k)
        out["taxonomie"] = {"capacites": "beaucoup", "aretes": []}
        return out
    monkeypatch.setattr(sc.science, "compute_science", _etranger)
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["taxonomie"] is None and d["pipeline"] is not None
    assert any(a.startswith("taxonomie : bloc refusé") for a in d["aveugle"]), d["aveugle"]


def test_science_import_refuse_est_NOMME(monkeypatch) -> None:
    from backend.app.services import science_service as sc
    monkeypatch.setattr(sc, "_IMPORT_REFUSE", ImportError("No module named 'tools.pm.science'"))
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["aveugle"][0].startswith("science: ImportError") and "tools.pm.science" in d["aveugle"][0]


def test_science_pipeline_sans_racine_null_et_ligne(monkeypatch, tmp_path) -> None:
    """B2 par la route : le module sans ses répertoires lève (P2.135), la pipeline est null, jamais (0, 0, 0, 0)."""
    from backend.app.services import science_service as sc
    from tools import check_preregistration_applied as cpa
    monkeypatch.setattr(cpa, "_PREREG", str(tmp_path / "absent"))
    sc._vider_cache()
    d = client.get("/api/pm/science").json()
    assert d["pipeline"] is None and any(a.startswith("pipeline : ") for a in d["aveugle"]), d["aveugle"]
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py tests/sandbox/test_ci_smoke_index.py tests/sandbox/test_pm_science.py -q -p no:cacheprovider -k "science or smoke or aveugle"`
Expected: FAIL — `ImportError` sur `science_service` (ou 404 sur la route).

- [ ] **Step 3 : schémas, service, route**

`backend/app/schemas.py`, après `IndexV1` (importer `Literal` depuis `typing` s'il n'y est pas) :

```python
class ScienceCouverture(BaseModel):
    inspectees: int
    sans_grandeur: int
    sans_record: int
    total: int


class SciencePreinscription(BaseModel):
    chemin: str
    titre: str | None = None
    scelle: bool | None = None
    date_ajout_git: str | None = None


class Pipeline(BaseModel):
    couverture: ScienceCouverture
    familles_sans_record: list[str]
    preinscriptions: list[SciencePreinscription] | None = None


class TaxonomieCapacite(BaseModel):
    id: str
    titre: str | None = None
    record: str | None = None


class TaxonomiePreuves(BaseModel):
    """Amendement A1 (I5, décision d'intégrateur) : les champs de `evidence` qui fondent une arête ; chacun une
    chaîne, un nombre fini, ou null (absent de la source, ou mal typé ET nommé par une ligne `taxonomie :`)."""
    specificity_control: str | int | float | None = None
    functional_aliasing: str | int | float | None = None
    ablation_target: str | int | float | None = None
    coord_intact: str | int | float | None = None
    emergence_bar: str | int | float | None = None
    incapable_ceiling: str | int | float | None = None
    ceiling_provenance: str | int | float | None = None


class TaxonomieArete(BaseModel):
    capacite: str
    prerequis: str
    nature: Literal["etablie", "refutee"]
    force: str | None = None
    verdict: str | None = None
    ratio: float | None = None
    n: int | None = None
    record: str | None = None
    raison: str | None = None
    depassee_par: str | None = None
    preuves: TaxonomiePreuves


class Taxonomie(BaseModel):
    capacites: list[TaxonomieCapacite]
    aretes: list[TaxonomieArete]


class TrouvailleVerdict(BaseModel):
    chemin: str
    titre: str | None = None
    verdict: str
    gate: str | None = None
    date_ajout_git: str | None = None


class SemainesFamille(BaseModel):
    """Amendement A1 (I2, I3) : TOUJOURS servi ; `raison` dit pourquoi `semaines` est null, dans le vocabulaire fermé
    `science.RAISONS_SEMAINES` ; `semaine_partielle` est la semaine de la borne (instantané des dates ou `now`)."""
    date: str | None = None
    semaines: dict[str, int] | None = None
    sans_date: dict[str, int] | None = None
    semaine_partielle: str | None = None
    raison: Literal["famille_non_lue", "parite_rompue", "sans_date_nommee", "dates_absentes", "historique_tronque",
                    "git_indisponible"] | None = None


class Trouvailles(BaseModel):
    verdicts: list[TrouvailleVerdict] | None = None
    verdicts_partiels: bool | None = None       # A1 (I1) : records illisibles ou état mal typé — liste PARTIELLE
    compte_graphe: int | None = None
    par_semaine: dict[str, SemainesFamille] | None = None
    dates: IndexDates | None = None             # A1 (I3) : le bloc dates de l'index, lu avec son âge (D1)


class ScienceV1(BaseModel):
    """Enveloppe de `science_v1` (spec 2026-09-26 §3.2). Chaque bloc validé par le service DANS son filet."""
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias="schema")
    generated_at: float
    repo_root: str | None = None
    aveugle: list[str]
    pipeline: Pipeline | None = None
    taxonomie: Taxonomie | None = None
    trouvailles: Trouvailles | None = None
```

`backend/app/services/science_service.py` :

```python
"""Service du lot 2 « Science » (P2.84) : en mémoire, SANS écrire un fichier, SANS lancer git.

L'index vient de `index_service.get_index()` — le MÊME cache que `/api/pm/index`, jamais recalculé deux fois (M6).
Même filet que `pilotage_service` : import gardé et NOMMÉ, chaque bloc validé contre le modèle de la route AVANT elle,
mode dégradé servable (`science: …`).
"""
from __future__ import annotations

import time
from typing import Any

from pydantic import TypeAdapter

try:
    from tools.pm import pilotage, science
    _IMPORT_REFUSE: Exception | None = None
except Exception as _exc:                                  # noqa: BLE001 — NOMMÉ par get_science, jamais avalé
    pilotage = None
    science = None
    _IMPORT_REFUSE = _exc

from ..schemas import ScienceV1
from . import index_service
from .pilotage_service import _EnveloppeRefusee, _resume, _servable, _texte_servable

_SCHEMA = "science_v1"
_TTL_DEFAUT = 60.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}
_BLOCS = ("pipeline", "taxonomie", "trouvailles")
_ADAPTATEURS = {cle: TypeAdapter(ScienceV1.model_fields[cle].annotation) for cle in _BLOCS}
_ENVELOPPE = TypeAdapter(ScienceV1)


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def get_science(ttl_s: float = _TTL_DEFAUT) -> dict:
    now = time.time()
    if _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    racine = None
    try:
        if _IMPORT_REFUSE is not None:
            raise ImportError(f"tools.pm.science indisponible dans ce processus "
                              f"({type(_IMPORT_REFUSE).__name__}: {_IMPORT_REFUSE}) -- volume ./tools absent du "
                              "conteneur, ou dépendance absente de backend/requirements.txt")
        racine = pilotage.racine_depot()
        out = science.compute_science(index_service.get_index(), science.lire_pipeline(),
                                      science.lire_taxonomie(racine), science.lire_graphe(racine), now)
        out = index_service._blocs_servables(out, _BLOCS, _ADAPTATEURS)
        try:
            _servable(_ENVELOPPE, out)
        except Exception as exc:                           # noqa: BLE001 — NOMMÉ par le mode dégradé
            raise _EnveloppeRefusee(_resume(exc)) from exc
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        texte = (f"science: enveloppe refusée par le modèle de la route ({exc})"
                 if isinstance(exc, _EnveloppeRefusee) else f"science: {type(exc).__name__}: {exc}")
        out = {"schema": _SCHEMA, "generated_at": now,
               "repo_root": None if racine is None else _texte_servable(str(racine).replace("\\", "/")),
               "aveugle": [_texte_servable(texte)], "pipeline": None, "taxonomie": None, "trouvailles": None}
    _cache["at"], _cache["valeur"] = now, out
    return out
```

`backend/app/routes/pm.py` : importer `get_science` et `ScienceV1`, puis

```python
@router.get("/science", response_model=ScienceV1, response_model_by_alias=True)
def science() -> dict:
    """Lot 2 « Science » (P2.84) : pipeline, taxonomie, trouvailles — recopiés de sources publiées, jamais
    recalculés ; blocs null avec leur ligne quand leur source manque."""
    return get_science()
```

- [ ] **Step 4 : les témoins passent ; types régénérés**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k "science or index or pilotage"`
Expected: PASS (les 7 nouveaux et ceux de l'index et du pilotage).

Puis `make api-types` sous le bail `kuzu` (script du plan 1 : `hold("kuzu")`, `tools/dump_openapi.py`, `npm --prefix
frontend run gen:api`, normalisation LF). Expected : `schema.ts` gagne `ScienceV1` et les dix modèles ; `openapi.json`
la route `/api/pm/science`.

- [ ] **Step 5 : le smoke docker de la CI**

Dans `.github/workflows/ci.yml`, étape « Run docker compose and smoke test », après les deux appels de l'index :

```yaml
          curl --fail -s http://localhost:8000/api/pm/science -o science_smoke.json || { docker compose logs backend; exit 1; }
          python3 -c "import json, sys; d = json.load(open('science_smoke.json', encoding='utf-8')); av = d.get('aveugle') or []; bad = [a for a in av if a.startswith('science:')]; p = d.get('pipeline') or {}; tot = (p.get('couverture') or {}).get('total'); tx = d.get('taxonomie') or {}; print('science :', d.get('schema'), '| pipeline total', tot, '| aretes', len(tx.get('aretes') or [])); [print('  DEGRADE :', a) for a in bad]; sys.exit(1 if bad or d.get('schema') != 'science_v1' or not tot or not tx.get('aretes') else 0)" || { docker compose logs backend; exit 1; }
```

Rouge sur toute ligne `science:`, sur une pipeline null ou à total 0 (B2), sur une taxonomie sans arête. Valider le
YAML (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8'))"`).

- [ ] **Step 6 : reproduire l'IMAGE sans docker**

Même dossier `image/` que le plan 1 (Task 6, Step 7 : `backend/requirements.txt` + `backend/app` + `*.py` de la racine
+ volumes `results/ data/ src/ tools/ docs/` par `git archive`), venv NEUF limité à `backend/requirements.txt`, puis
depuis `image/` :

```bash
<venv>/python -c "from backend.app.services.science_service import get_science; d = get_science(); print(d['schema'], [a for a in d['aveugle'] if a.startswith('science:')], d['pipeline']['couverture']['total'], len(d['taxonomie']['aretes']), len(d['trouvailles']['verdicts']))"
```

Expected: `science_v1 [] <total > 0> 5 <plus de 100>`.

- [ ] **Step 7 : suites Windows et WSL, revue opus, commit du pas 4**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py tests/sandbox/test_ci_smoke_index.py tests/sandbox/test_pm_science.py tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider` (Windows) puis la même chose sous WSL.
Revue adversariale opus du diff des Tasks 1-2 (sources, comptes, filet, smoke, image), traitement des constats par TDD,
puis `commit-exact` sur : `tools/pm/science.py`, `tests/sandbox/test_pm_science.py`,
`tests/sandbox/test_instrument_calibration.py`, `tools/instrument_calibration_baseline.json`,
`docs/roadmap/PRIORITES_ET_DETTES.md`, la spec (§6), `backend/app/services/science_service.py`,
`backend/app/routes/pm.py`, `backend/app/schemas.py`, `tests/test_backend.py`, `tests/sandbox/test_ci_smoke_index.py` (A2),
`.github/workflows/ci.yml`,
`frontend/openapi.json`, `frontend/src/api/schema.ts`. La porte de parité signale `/api/pm/science` non consommé
jusqu'à la Task 3 : le dire dans le message.

---

### Task 3 : famille Science et vue Pipeline

**Files:**
- Create: `frontend/src/lib/science.ts`, `frontend/src/lib/science.test.ts`, `frontend/src/components/science/scienceFixture.ts`, `frontend/src/components/science/PipelineView.tsx`, `frontend/src/components/science/PipelineView.test.tsx`
- Modify: `frontend/src/api/pm.ts` (+ test), `frontend/src/api/queryKeys.ts` (+ test), `frontend/src/lib/polling.ts` (+ test), `frontend/src/tabs.ts`, `frontend/src/tabs.test.tsx`, `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `components["schemas"]["ScienceV1"]` et modèles (Task 2) ; `AveugleBanner` (`prefixeDegrade`, `titreDegrade`), `vscodeHref`, `Stat`, `Empty`, `ErrorState`, `Loading`, `Panel`.
- Produces: `fetchScience(): Promise<ScienceV1>` ; types `ScienceV1`, `Pipeline`, `Taxonomie`, `TaxonomieArete`, `Trouvailles`, `TrouvailleVerdict`, `SemainesFamille` ; `queryKeys.pm.science` ; `SCIENCE_POLL` ; `TITRE_DEGRADE_SCIENCE` ; `messageBloc(aveugle, bloc, libelle)` ; composant `PipelineView` ; onglet `pipeline` dans une famille « Science ».

- [ ] **Step 1 : écrire les témoins**

`frontend/src/lib/science.test.ts` :

```ts
import { expect, test } from "vitest";
import { messageBloc } from "./science";

test("messageBloc : les lignes du bloc et celles du mode dégradé, jamais un silence", () => {
  const av = ["pipeline : couverture illisible (RacineSansSource: x) -- INCONNUE", "taxonomie : y"];
  expect(messageBloc(av, "pipeline", "Pipeline")).toBe(
    "Pipeline indisponible — pipeline : couverture illisible (RacineSansSource: x) -- INCONNUE",
  );
  expect(messageBloc(["science: RuntimeError: z"], "taxonomie", "Taxonomie")).toBe(
    "Taxonomie indisponible — science: RuntimeError: z",
  );
  expect(messageBloc([], "trouvailles", "Trouvailles")).toMatch(/aucune ligne qui nomme ce bloc/);
});
```

Dans `api/pm.test.ts` : `test("science appelle /api/pm/science", async () => { await fetchScience(); expect(mocked).toHaveBeenCalledWith("/api/pm/science"); });` (et `fetchScience` à l'import).
Dans `queryKeys.test.ts` : `test("clé de la science", () => { expect(queryKeys.pm.science).toEqual(["pm", "science"]); });`
Dans `polling.test.ts` : `test("SCIENCE_POLL : 60 s", () => { expect(SCIENCE_POLL).toEqual({ refetchInterval: 60_000, staleTime: 10_000, refetchIntervalInBackground: false }); });` (et `SCIENCE_POLL` à l'import).
Dans `tabs.test.tsx`, un témoin de famille :

```tsx
test("famille Science : ses onglets, libellés et icônes", () => {
  const science = buildNavItems(TAB_FAMILIES).filter((i) => i.group === "Science");
  expect(science.map((i) => [i.id, i.label])).toEqual([["pipeline", "Pipeline"]]);
  for (const i of science) expect(typeof i.icon).toBe("object");
});
```

`frontend/src/components/science/scienceFixture.ts` :

```ts
import type { ScienceV1, TaxonomieArete } from "../../api/pm";

/** Les sept preuves d'une arête toutes absentes de la source (amendement A1, I5) : une réfutée n'en porte aucune. */
export const SANS_PREUVES: TaxonomieArete["preuves"] = {
  specificity_control: null, functional_aliasing: null, ablation_target: null, coord_intact: null,
  emergence_bar: null, incapable_ceiling: null, ceiling_provenance: null,
};

/** Réponse science_v1 factice, TYPÉE contre le schéma généré (tsc rougit si le contrat change sous elle). */
export function scienceFixture(over: Partial<ScienceV1> = {}): ScienceV1 {
  return {
    schema: "science_v1",
    generated_at: 1_790_430_000,
    repo_root: "C:/Users/robla/VScode_Project/AGAGI",
    aveugle: [],
    pipeline: {
      couverture: { inspectees: 20, sans_grandeur: 13, sans_record: 2, total: 35 },
      familles_sans_record: ["EVO-022", "EVO-028-SMOKE"],
      preinscriptions: [
        { chemin: "docs/preregistrations/EVO-022.json", titre: "EVO-022", scelle: true, date_ajout_git: "2026-09-02" },
        { chemin: "docs/preregistrations/X.json", titre: null, scelle: null, date_ajout_git: null },
      ],
    },
    taxonomie: {
      capacites: [
        { id: "perception", titre: "Perception", record: "docs/EDR/S2-001.md" },
        { id: "memory", titre: "Mémoire", record: null },
        { id: "language", titre: "Langage", record: null },
      ],
      aretes: [
        { capacite: "memory", prerequis: "perception", nature: "etablie", force: "hard", verdict: "X_DEMANDED",
          ratio: 3.934, n: 12, record: "docs/EDR/MEM.md", raison: "r1", depassee_par: null,
          preuves: { ...SANS_PREUVES, specificity_control: "pass", functional_aliasing: "n/a", coord_intact: 0.6547,
            emergence_bar: 0.2431, incapable_ceiling: 0.2266, ceiling_provenance: "plafond d'un agent non entraîné" } },
        { capacite: "language", prerequis: "memory", nature: "etablie", force: "hard", verdict: "X_DEMANDED",
          ratio: 4.967, n: 12, record: "docs/EDR/LM.md", raison: "r2", depassee_par: null,
          preuves: { ...SANS_PREUVES, specificity_control: "pass", functional_aliasing: "pass",
            ablation_target: "substrate", coord_intact: 0.819, emergence_bar: 0.5, incapable_ceiling: 0.1859,
            ceiling_provenance: "plafond d'un agent non entraîné" } },
        { capacite: "language", prerequis: "memory", nature: "refutee", force: null,
          verdict: "NEGATIVE_NOT_MEASURABLE", ratio: null, n: 12, record: "docs/EDR/LM-1.md",
          raison: "substrat affine", depassee_par: "docs/EDR/LM.md", preuves: SANS_PREUVES },
      ],
    },
    trouvailles: {
      verdicts: [
        { chemin: "docs/EDR/001_a.md", titre: "A", verdict: "X_DEMANDED", gate: "G1", date_ajout_git: "2026-09-01" },
        { chemin: "docs/EDR/002_b.md", titre: null, verdict: "NEGATIVE", gate: null, date_ajout_git: null },
      ],
      verdicts_partiels: false,
      compte_graphe: 2,
      par_semaine: {
        record: { date: "date_ajout_git", semaines: { "2026-W36": 1, "2026-W37": 0, "2026-W38": 2 },
          sans_date: { sans_ajout_trouve: 1 }, semaine_partielle: "2026-W38", raison: null },
        spec: { date: "date_declaree", semaines: { "2026-W38": 3 }, sans_date: {}, semaine_partielle: "2026-W38",
          raison: null },
        ref: { date: "date_ajout_git", semaines: null, sans_date: { dates_absentes: 4 }, semaine_partielle: null,
          raison: "dates_absentes" },
        adr: { date: "date_ajout_git", semaines: null, sans_date: null, semaine_partielle: null,
          raison: "famille_non_lue" },
        sdr: { date: "date_ajout_git", semaines: null, sans_date: null, semaine_partielle: null,
          raison: "parite_rompue" },
      },
      dates: { generated_at: 1_790_429_940, age_s: 60, head: "abc1234", historique: "complet" },
    },
    ...over,
  };
}
```

`frontend/src/components/science/PipelineView.test.tsx` :

```tsx
import type { ReactNode } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
}));
import { apiFetch, ApiError } from "../../api/client";
import { PipelineView } from "./PipelineView";
import { scienceFixture } from "./scienceFixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;
function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
beforeEach(() => mocked.mockResolvedValue(scienceFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("couverture recopiée : quatre comptes, en familles", async () => {
  rendre(<PipelineView />);
  expect(await screen.findByText("Familles inspectées")).toBeTruthy();
  for (const [libelle, n] of [["Familles inspectées", "20"], ["Sans grandeur nommée", "13"], ["Sans record", "2"],
    ["Total (familles)", "35"]]) {
    expect(screen.getByText(libelle).parentElement!.textContent).toContain(n);
  }
  expect(mocked).toHaveBeenCalledWith("/api/pm/science");
});

test("familles sans record NOMMÉES, avec la phrase du module", async () => {
  rendre(<PipelineView />);
  expect(await screen.findByText("EVO-022")).toBeTruthy();
  expect(screen.getByText("EVO-028-SMOKE")).toBeTruthy();
  expect(screen.getByText(/un humain tranche/)).toBeTruthy();
});

test("pré-inscriptions : absence dite, jamais inventée", async () => {
  rendre(<PipelineView />);
  const t = await screen.findByRole("table", { name: "Pré-inscriptions" });
  const x = within(t).getByText("docs/preregistrations/X.json").closest("tr")!;
  expect(within(x).getByText("sans nom")).toBeTruthy();
  expect(within(x).getByText("inconnu")).toBeTruthy();
  expect(within(x).getByText("sans date d'ajout")).toBeTruthy();
});

test("pipeline null : Empty avec SA ligne ; pré-inscriptions null : Empty sous les comptes", async () => {
  const ligne = "pipeline : couverture illisible (RacineSansSource: x) -- INCONNUE, jamais (0, 0, 0, 0)";
  mocked.mockResolvedValue(scienceFixture({ pipeline: null, aveugle: [ligne] }));
  rendre(<PipelineView />);
  expect(await screen.findByText(`Pipeline indisponible — ${ligne}`)).toBeTruthy();
  cleanup();
  const f = scienceFixture();
  mocked.mockResolvedValue({ ...f, pipeline: { ...f.pipeline!, preinscriptions: null } });
  rendre(<PipelineView />);
  expect(await screen.findByText(/Pré-inscriptions indisponible/)).toBeTruthy();
  expect(screen.getByText("Familles inspectées")).toBeTruthy();
});

test("mode dégradé : alerte ; backend injoignable : ErrorState", async () => {
  mocked.mockResolvedValue(scienceFixture({ aveugle: ["science: RuntimeError: x"], pipeline: null, taxonomie: null,
    trouvailles: null }));
  rendre(<PipelineView />);
  expect((await screen.findByRole("alert")).textContent).toContain("science: RuntimeError");
  cleanup();
  mocked.mockRejectedValue(new ApiError(0, "/api/pm/science", "Timeout après 10000 ms"));
  rendre(<PipelineView />);
  expect((await screen.findByRole("alert")).textContent).toContain("Erreur de chargement");
});
```

- [ ] **Step 2 : les lancer, ils échouent**

Run (depuis `frontend/`): `npx vitest run src/lib/science.test.ts src/api src/lib/polling.test.ts src/tabs.test.tsx src/components/science`
Expected: FAIL — modules `./science`, `./PipelineView` introuvables, `fetchScience` non exporté.

- [ ] **Step 3 : client, clé, poll, onglet, couche pure, vue**

`api/pm.ts` : types (`ScienceV1`, `Pipeline`, `Taxonomie`, `TaxonomieArete`, `Trouvailles`, `TrouvailleVerdict`,
`SemainesFamille` depuis `components["schemas"]`) et

```ts
/** Chemin LITTÉRAL (porte de parité). Aucun recalcul côté serveur au-delà de la lecture des sources publiées. */
export function fetchScience(): Promise<ScienceV1> {
  return apiFetch<ScienceV1>("/api/pm/science");
}
```

`queryKeys.ts` : `science: ["pm", "science"] as const,` dans `pm`. `polling.ts` :

```ts
/** Options react-query de la famille Science : 60 s, le cache du backend. */
export const SCIENCE_POLL = {
  refetchInterval: 60_000,
  staleTime: 10_000,
  refetchIntervalInBackground: false,
} as const;
```

`tabs.ts` : `"pipeline"` à la fin de `TAB_KEYS`, l'icône `Route` à l'import de `lucide-react`, et après la famille
Pilotage :

```ts
  {
    // Lecture seule de GET /api/pm/science (P2.84, spec 2026-09-26) : sources publiées recopiées, aucun verdict recalculé.
    family: "Science",
    tabs: [{ key: "pipeline", label: "Pipeline", icon: Route }],
  },
```

`App.tsx` : `const PipelineView = lazy(() => import("./components/science/PipelineView").then((m) => ({ default: m.PipelineView })));` et `{tab === "pipeline" && <PipelineView />}`.

`frontend/src/lib/science.ts` :

```ts
export const TITRE_DEGRADE_SCIENCE = "Science en mode dégradé : les trois blocs sont servis à null";

export type BlocScience = "pipeline" | "taxonomie" | "trouvailles";

/** Pourquoi un bloc est null : ses lignes (« bloc : … ») et celles du mode dégradé (« science: … ») ; jamais un
 *  silence — sans ligne, le message le dit. */
export function messageBloc(aveugle: readonly string[], bloc: BlocScience, libelle: string): string {
  const lignes = aveugle.filter((l) => l.startsWith(`${bloc} :`) || l.startsWith("science:"));
  if (lignes.length) return `${libelle} indisponible — ${lignes.join(" · ")}`;
  return `${libelle} indisponible — le backend n'a publié aucune ligne qui nomme ce bloc (à signaler)`;
}
```

`frontend/src/components/science/PipelineView.tsx` :

```tsx
import { useQuery } from "@tanstack/react-query";
import { fetchScience } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { vscodeHref } from "../../lib/pilotage";
import { SCIENCE_POLL } from "../../lib/polling";
import { messageBloc, TITRE_DEGRADE_SCIENCE } from "../../lib/science";
import { AveugleBanner } from "../pilotage/AveugleBanner";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { Stat } from "../ui/Stat";

const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

/** Onglet Pipeline (P2.84) : de la règle scellée au record, RECOPIÉ de tools/check_preregistration_applied.py. */
export function PipelineView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.science,
    queryFn: () => fetchScience(),
    ...SCIENCE_POLL,
  });
  if (isLoading) return <Loading label="Chargement de la science…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — science inconnue." />;
  const p = data.pipeline;
  return (
    <div className="pilotage-view">
      <h2>Pipeline : règle scellée → record</h2>
      <p className="text-dim">
        Recopié de tools/check_preregistration_applied.py (couverture, familles sans record) : rien n'est recalculé ici.
      </p>
      <AveugleBanner lignes={data.aveugle} prefixeDegrade="science:" titreDegrade={TITRE_DEGRADE_SCIENCE} />
      {!p ? (
        <Empty message={messageBloc(data.aveugle, "pipeline", "Pipeline")} />
      ) : (
        <>
          <div className="row mb-4">
            <Stat label="Familles inspectées" value={p.couverture.inspectees} />
            <Stat label="Sans grandeur nommée" value={p.couverture.sans_grandeur} />
            <Stat label="Sans record" value={p.couverture.sans_record} />
            <Stat label="Total (familles)" value={p.couverture.total} />
          </div>
          <Panel className="mb-4">
            <h3>Familles sans record</h3>
            <p className="text-dim">
              Elles nomment des grandeurs mais aucun record ne s'en réclame (ni déclaré, ni cité, ni préfixé). Ce n'est
              pas « aucun record n'existe » : un humain tranche.
            </p>
            {p.familles_sans_record.length ? (
              <ul className="pilotage-chemins">
                {p.familles_sans_record.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            ) : (
              <p>aucune</p>
            )}
          </Panel>
          {p.preinscriptions == null ? (
            <Empty message={messageBloc(data.aveugle, "pipeline", "Pré-inscriptions")} />
          ) : (
            <Panel>
              <div className="pilotage-defilement">
                <table className="runs-table" aria-label="Pré-inscriptions">
                  <thead>
                    <tr>
                      <th>Nom</th>
                      <th>Scellée</th>
                      <th>Date d'ajout</th>
                      <th>Chemin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.preinscriptions.map((r) => {
                      const href = vscodeHref(data.repo_root, r.chemin);
                      return (
                        <tr key={r.chemin}>
                          <td>{r.titre ?? <Dim>sans nom</Dim>}</td>
                          <td>{r.scelle == null ? <Dim>inconnu</Dim> : r.scelle ? "oui" : "non"}</td>
                          <td className="pilotage-nowrap">{r.date_ajout_git ?? <Dim>sans date d'ajout</Dim>}</td>
                          <td>{href ? <a href={href}>{r.chemin}</a> : r.chemin}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4 : les témoins passent ; mutants ; typage ; relecture visuelle**

Run: `npx vitest run src/lib/science.test.ts src/api src/lib/polling.test.ts src/tabs.test.tsx src/components/science` puis `npx tsc --noEmit -p tsconfig.json` (jamais `-b` : il écrit des `.tsbuildinfo` dans l'arbre).
Expected: PASS ; tsc sans erreur sur `src/`.
Mutants (script du scratchpad, fichier restauré octet pour octet, contrôle intact d'abord) : scellée null rendue « non »,
titre null remplacé par le chemin, `messageBloc` qui ignore les lignes `science:`. Expected : les trois TUÉS.
Relecture visuelle : `npm --prefix frontend run dev` contre le backend local, onglet Pipeline, largeur 390 px et 1280 px
— aucun défilement horizontal de la page (le tableau défile dans son panneau).

- [ ] **Step 5 : suite complète et commit du pas 5a**

Run: `npm --prefix frontend test` (complet) ; puis `commit-exact` sur les fichiers de la tâche. La porte de parité ne
signale plus `/api/pm/science`.

---

### Task 4 : vue Taxonomie

**Files:**
- Create: `frontend/src/lib/taxonomie.ts`, `frontend/src/lib/taxonomie.test.ts`, `frontend/src/components/science/TaxonomieView.tsx`, `frontend/src/components/science/TaxonomieView.test.tsx`
- Modify: `frontend/src/tabs.ts`, `frontend/src/tabs.test.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`

**Interfaces:**
- Consumes: `Taxonomie`, `TaxonomieArete` (Task 3) ; `scienceFixture`, `messageBloc`, `TITRE_DEGRADE_SCIENCE`.
- Produces: `noeudsDe(t): string[]` ; `dispositionCirculaire(ids, rayon, centre): Record<string, Point>` ; `decalages(aretes, pas?): number[]` ; `segment(a, b, decalage, marge)` ; composant `TaxonomieView` ; onglet `taxonomie` (icône `Waypoints`).

Décision M6 (tranchée ici, à consigner au grand livre) : un cercle DÉTERMINISTE rendu par React en SVG, pas
`ProvenanceGraph` — ce dernier est une simulation de forces d3 typée pour la provenance, non déterministe et
difficile à tester ; quatre capacités tiennent sur un cercle.

- [ ] **Step 1 : écrire les témoins**

`frontend/src/lib/taxonomie.test.ts` :

```ts
import { describe, expect, test } from "vitest";
import { autresPreuves, decalages, dispositionCirculaire, noeudsDe, segment } from "./taxonomie";
import type { TaxonomieArete } from "../api/pm";
import { SANS_PREUVES } from "../components/science/scienceFixture";

const A = (capacite: string, prerequis: string, nature: "etablie" | "refutee"): TaxonomieArete => ({
  capacite, prerequis, nature, force: null, verdict: null, ratio: null, n: null, record: null, raison: null,
  depassee_par: null, preuves: SANS_PREUVES,
});

describe("disposition", () => {
  test("cercle déterministe, premier nœud en haut", () => {
    const p = dispositionCirculaire(["a", "b", "c", "d"], 100, { x: 0, y: 0 });
    expect(p.a.x).toBeCloseTo(0);
    expect(p.a.y).toBeCloseTo(-100);
    expect(p.b.x).toBeCloseTo(100);
    expect(p.c.y).toBeCloseTo(100);
    expect(dispositionCirculaire(["seul"], 100, { x: 5, y: 7 }).seul).toEqual({ x: 5, y: 7 });
  });
  test("nœuds : capacités et extrémités d'arêtes, triés, sans doublon", () => {
    expect(noeudsDe({ capacites: [{ id: "memory" }], aretes: [A("language", "memory", "etablie")] })).toEqual([
      "language",
      "memory",
    ]);
  });
});

describe("arêtes parallèles", () => {
  test("trois arêtes sur la même paire : décalages distincts et centrés ; une seule : 0", () => {
    const d = decalages([A("language", "memory", "etablie"), A("language", "memory", "refutee"),
      A("language", "memory", "refutee"), A("memory", "perception", "etablie")]);
    expect(new Set(d.slice(0, 3)).size).toBe(3);
    expect(d[0] + d[1] + d[2]).toBeCloseTo(0);
    expect(d[3]).toBe(0);
  });
  test("le décalage suit la PAIRE, pas le sens : deux sens opposés ne se superposent pas", () => {
    const d = decalages([A("a", "b", "etablie"), A("b", "a", "refutee")]);
    const s0 = segment({ x: 0, y: 0 }, { x: 100, y: 0 }, d[0], 0);
    const s1 = segment({ x: 100, y: 0 }, { x: 0, y: 0 }, d[1], 0);
    expect(s0.y1).not.toBeCloseTo(s1.y2);
  });
  test("segment raccourci de la marge aux deux bouts", () => {
    expect(segment({ x: 0, y: 0 }, { x: 100, y: 0 }, 0, 10)).toEqual({ x1: 10, y1: 0, x2: 90, y2: 0 });
  });
});

describe("preuves (amendement A1, I5)", () => {
  test("autresPreuves : sans le contrôle de spécificité, sans les absentes, zéro gardé", () => {
    expect(autresPreuves({ ...SANS_PREUVES, specificity_control: "pass", coord_intact: 0, emergence_bar: 0.5 }))
      .toEqual([["coord_intact", 0], ["emergence_bar", 0.5]]);
    expect(autresPreuves(SANS_PREUVES)).toEqual([]);
  });
});
```

`frontend/src/components/science/TaxonomieView.test.tsx` (même en-tête de rendu que `PipelineView.test.tsx`) :

```tsx
test("graphe : une ligne par arête, réfutées en pointillé et légendées", async () => {
  const { container } = rendre(<TaxonomieView />);
  await screen.findByRole("img", { name: "Graphe des capacités et de leurs prérequis" });
  expect(container.querySelectorAll("line.taxo-arete--etablie[data-arete]")).toHaveLength(2);
  expect(container.querySelectorAll("line.taxo-arete--refutee[data-arete]")).toHaveLength(1);
  expect(screen.getByText(/réfutée \(pointillé\)/)).toBeTruthy();
});

test("tableau : la réfutée porte son verdict, sa raison et ce qui l'a dépassée", async () => {
  rendre(<TaxonomieView />);
  const t = await screen.findByRole("table", { name: "Arêtes de la taxonomie" });
  const r = within(t).getByText("NEGATIVE_NOT_MEASURABLE").closest("tr")!;
  expect(within(r).getByText("réfutée")).toBeTruthy();
  expect(within(r).getByText("substrat affine")).toBeTruthy();
  expect(within(r).getByText("docs/EDR/LM.md")).toBeTruthy();
  expect(within(r).getByText("non mesuré")).toBeTruthy();                    // ratio null : jamais 0
});

test("tableau : l'arête établie porte le contrôle qui la fonde ; la réfutée n'en invente aucun (A1, I5)", async () => {
  rendre(<TaxonomieView />);
  const t = await screen.findByRole("table", { name: "Arêtes de la taxonomie" });
  const e = within(t).getByText("docs/EDR/MEM.md").closest("tr")!;
  expect(within(e).getByText("pass")).toBeTruthy();
  expect(within(e).getByText("emergence_bar")).toBeTruthy();
  const r = within(t).getByText("NEGATIVE_NOT_MEASURABLE").closest("tr")!;
  expect(within(r).getByText("non déclaré")).toBeTruthy();
  expect(within(r).getByText("aucune déclarée")).toBeTruthy();
});

test("taxonomie null : Empty avec SA ligne", async () => {
  const ligne = "taxonomie : C:/x : capabilities.json introuvable -- graphe INCONNU";
  mocked.mockResolvedValue(scienceFixture({ taxonomie: null, aveugle: [ligne] }));
  rendre(<TaxonomieView />);
  expect(await screen.findByText(`Taxonomie indisponible — ${ligne}`)).toBeTruthy();
});
```

Et dans `tabs.test.tsx`, l'attendu de la famille Science devient `[["pipeline","Pipeline"],["taxonomie","Taxonomie"]]`.

- [ ] **Step 2 : les lancer, ils échouent**

Run: `npx vitest run src/lib/taxonomie.test.ts src/components/science src/tabs.test.tsx`
Expected: FAIL — modules introuvables.

- [ ] **Step 3 : couche pure, vue, onglet, styles**

`frontend/src/lib/taxonomie.ts` :

```ts
import type { Taxonomie, TaxonomieArete } from "../api/pm";

export interface Point {
  x: number;
  y: number;
}

/** Les nœuds du graphe : capacités déclarées ET extrémités d'arêtes (une arête vers une capacité non déclarée reste
 *  tracée, le backend l'a nommée en ligne). Triés : la disposition est déterministe. */
export function noeudsDe(t: Pick<Taxonomie, "capacites" | "aretes">): string[] {
  const s = new Set(t.capacites.map((c) => c.id));
  for (const a of t.aretes) {
    s.add(a.capacite);
    s.add(a.prerequis);
  }
  return [...s].sort();
}

/** Cercle déterministe, premier nœud en haut, sens horaire ; un nœud seul au centre. */
export function dispositionCirculaire(ids: readonly string[], rayon: number, centre: Point): Record<string, Point> {
  const out: Record<string, Point> = {};
  ids.forEach((id, i) => {
    if (ids.length === 1) {
      out[id] = { ...centre };
      return;
    }
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / ids.length;
    out[id] = { x: centre.x + rayon * Math.cos(angle), y: centre.y + rayon * Math.sin(angle) };
  });
  return out;
}

/** Décalage perpendiculaire de chaque arête parmi celles de la MÊME paire (quel que soit leur sens) : l'établie et
 *  les réfutées de `language ← memory` ne se superposent jamais (I8). Signé selon le sens, pour que deux arêtes de
 *  sens opposés tombent de part et d'autre. */
export function decalages(aretes: readonly TaxonomieArete[], pas = 10): number[] {
  const paire = (a: TaxonomieArete) => [a.capacite, a.prerequis].sort().join("|");
  const groupes = new Map<string, number[]>();
  aretes.forEach((a, i) => groupes.set(paire(a), [...(groupes.get(paire(a)) ?? []), i]));
  const out = aretes.map(() => 0);
  for (const idx of groupes.values()) {
    idx.forEach((i, k) => {
      const sens = aretes[i].capacite <= aretes[i].prerequis ? 1 : -1;
      out[i] = (k - (idx.length - 1) / 2) * pas * sens;
    });
  }
  return out;
}

/** Le trait de `a` vers `b`, raccourci de `marge` aux deux bouts et déplacé de `decalage` perpendiculairement. */
export function segment(a: Point, b: Point, decalage: number, marge: number) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const l = Math.hypot(dx, dy) || 1;
  const ux = dx / l;
  const uy = dy / l;
  const px = -uy * decalage;
  const py = ux * decalage;
  return { x1: a.x + ux * marge + px, y1: a.y + uy * marge + py, x2: b.x - ux * marge + px, y2: b.y - uy * marge + py };
}

/** Amendement A1 (I5) : les preuves d'une arête AUTRES que le contrôle de spécificité (rendu dans sa propre colonne),
 *  dans l'ordre servi, sans les absentes — une absence n'est jamais affichée comme une valeur. */
export function autresPreuves(p: TaxonomieArete["preuves"]): [string, string | number][] {
  return Object.entries(p).filter(
    (e): e is [string, string | number] => e[0] !== "specificity_control" && e[1] != null,
  );
}
```

`frontend/src/components/science/TaxonomieView.tsx` :

```tsx
import { useQuery } from "@tanstack/react-query";
import { fetchScience, type Taxonomie, type TaxonomieArete } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { mesure, vscodeHref } from "../../lib/pilotage";
import { SCIENCE_POLL } from "../../lib/polling";
import { messageBloc, TITRE_DEGRADE_SCIENCE } from "../../lib/science";
import { autresPreuves, decalages, dispositionCirculaire, noeudsDe, segment } from "../../lib/taxonomie";
import { AveugleBanner } from "../pilotage/AveugleBanner";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";

const LARGEUR = 520;
const HAUTEUR = 360;
const R_NOEUD = 28;
const NATURE = { etablie: "établie", refutee: "réfutée" } as const;
const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

function Lien({ racine, chemin }: { racine: string | null | undefined; chemin: string | null | undefined }) {
  if (!chemin) return <Dim>—</Dim>;
  const href = vscodeHref(racine, chemin);
  return href ? <a href={href}>{chemin}</a> : <>{chemin}</>;
}

function Preuves({ p }: { p: TaxonomieArete["preuves"] }) {
  const autres = autresPreuves(p);
  if (autres.length === 0) return <Dim>aucune déclarée</Dim>;
  return (
    <ul className="taxo-preuves">
      {autres.map(([k, v]) => (
        <li key={k}>
          <code>{k}</code> {String(v)}
        </li>
      ))}
    </ul>
  );
}

/** Onglet Taxonomie (P2.84) : capacités et prérequis RECOPIÉS de la taxonomie AGI ; les arêtes réfutées sont
 *  visibles, distinctes, et disent ce qui les a dépassées (I8). */
export function TaxonomieView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.science,
    queryFn: () => fetchScience(),
    ...SCIENCE_POLL,
  });
  if (isLoading) return <Loading label="Chargement de la science…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — science inconnue." />;
  const t = data.taxonomie;
  return (
    <div className="pilotage-view">
      <h2>Taxonomie : capacités et prérequis</h2>
      <AveugleBanner lignes={data.aveugle} prefixeDegrade="science:" titreDegrade={TITRE_DEGRADE_SCIENCE} />
      {!t ? (
        <Empty message={messageBloc(data.aveugle, "taxonomie", "Taxonomie")} />
      ) : (
        <Graphe t={t} racine={data.repo_root} />
      )}
    </div>
  );
}

function Graphe({ t, racine }: { t: Taxonomie; racine: string | null | undefined }) {
  const ids = noeudsDe(t);
  const pos = dispositionCirculaire(ids, 130, { x: LARGEUR / 2, y: HAUTEUR / 2 });
  const dec = decalages(t.aretes);
  return (
    <>
      <Panel className="mb-4">
        <svg viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`} role="img" aria-label="Graphe des capacités et de leurs prérequis"
          className="taxo-graphe">
          <defs>
            <marker id="taxo-fleche" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7"
              orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" />
            </marker>
          </defs>
          {t.aretes.map((a, i) => {
            const s = segment(pos[a.capacite], pos[a.prerequis], dec[i], R_NOEUD + 4);
            return (
              <line key={i} {...s} data-arete={i} className={`taxo-arete taxo-arete--${a.nature}`}
                markerEnd="url(#taxo-fleche)">
                <title>{`${a.capacite} exige ${a.prerequis} (${NATURE[a.nature]})`}</title>
              </line>
            );
          })}
          {ids.map((id) => (
            <g key={id} className="taxo-noeud">
              <circle cx={pos[id].x} cy={pos[id].y} r={R_NOEUD} />
              <text x={pos[id].x} y={pos[id].y} textAnchor="middle" dominantBaseline="middle">
                {id}
              </text>
            </g>
          ))}
        </svg>
        <p className="taxo-legende">
          <svg width="36" height="10" aria-hidden="true">
            <line x1="0" y1="5" x2="36" y2="5" className="taxo-arete taxo-arete--etablie" />
          </svg>
          établie
          <svg width="36" height="10" aria-hidden="true">
            <line x1="0" y1="5" x2="36" y2="5" className="taxo-arete taxo-arete--refutee" />
          </svg>
          réfutée (pointillé) — la flèche va de la capacité vers son prérequis ; verdict et « dépassée par » dans le
          tableau
        </p>
      </Panel>
      <Panel>
        <div className="pilotage-defilement">
          <table className="runs-table" aria-label="Arêtes de la taxonomie">
            <thead>
              <tr>
                <th>Capacité</th>
                <th>Prérequis</th>
                <th>Nature</th>
                <th>Verdict</th>
                <th>Ratio</th>
                <th>n</th>
                <th>Contrôle de spécificité</th>
                <th>Autres preuves</th>
                <th>Raison</th>
                <th>Record</th>
                <th>Dépassée par</th>
              </tr>
            </thead>
            <tbody>
              {t.aretes.map((a, i) => (
                <tr key={i}>
                  <td>{a.capacite}</td>
                  <td>{a.prerequis}</td>
                  <td>{NATURE[a.nature]}</td>
                  <td>{a.verdict ?? <Dim>non déclaré</Dim>}</td>
                  <td>{mesure(a.ratio, (n) => n.toFixed(3))}</td>
                  <td>{mesure(a.n)}</td>
                  <td>{a.preuves.specificity_control == null ? <Dim>non déclaré</Dim>
                    : String(a.preuves.specificity_control)}</td>
                  <td><Preuves p={a.preuves} /></td>
                  <td>{a.raison ?? <Dim>—</Dim>}</td>
                  <td><Lien racine={racine} chemin={a.record} /></td>
                  <td><Lien racine={racine} chemin={a.depassee_par} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
```

`styles.css` (après les styles `.pilotage-*`) :

```css
.taxo-graphe { width: 100%; max-width: 560px; height: auto; display: block; margin: 0 auto; }
.taxo-arete { stroke-width: 2; fill: none; }
.taxo-arete--etablie { stroke: var(--color-accent); }
.taxo-arete--refutee { stroke: var(--color-danger); stroke-dasharray: 6 4; }
.taxo-noeud circle { fill: var(--color-surface); stroke: var(--color-border-subtle); stroke-width: 1.5; }
.taxo-noeud text { fill: var(--color-text); font-size: 12px; }
#taxo-fleche path { fill: var(--color-text-dim); }
.taxo-legende { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; font-size: var(--font-size-xs); }
.taxo-preuves { margin: 0; padding-left: 0; list-style: none; font-size: var(--font-size-xs); }
```

`tabs.ts` : `"taxonomie"` à la fin de `TAB_KEYS`, `Waypoints` à l'import, `{ key: "taxonomie", label: "Taxonomie", icon: Waypoints }` dans la famille Science. `App.tsx` : `lazy()` de `TaxonomieView` et `{tab === "taxonomie" && <TaxonomieView />}`.

- [ ] **Step 4 : les témoins passent ; mutants ; typage ; relecture visuelle ; commit du pas 5b**

Run: `npx vitest run src/lib/taxonomie.test.ts src/components/science src/tabs.test.tsx`, puis `npx tsc --noEmit -p tsconfig.json`.
Expected: PASS.
Mutants : `decalages` qui rend 0 partout ; réfutée rendue avec la classe de l'établie ; `depassee_par` non affiché ;
contrôle de spécificité non affiché ; `autresPreuves` qui écarte un 0 (`!e[1]` au lieu de `e[1] != null`).
Expected : TUÉS. Relecture visuelle (390 px et 1280 px, thème clair ET sombre : la réfutée reste distincte). Suite
complète `npm --prefix frontend test`, puis `commit-exact`.

---

### Task 5 : vue Trouvailles ; P2.84 close

**Files:**
- Create: `frontend/src/components/science/TrouvaillesView.tsx`, `frontend/src/components/science/TrouvaillesView.test.tsx`
- Modify: `frontend/src/lib/science.ts` (+ test), `frontend/src/tabs.ts`, `frontend/src/tabs.test.tsx`, `frontend/src/App.tsx`, `docs/roadmap/FRONTEND.md`, `docs/roadmap/PRIORITES_ET_DETTES.md`

**Interfaces:**
- Consumes: `Trouvailles`, `TrouvailleVerdict`, `SemainesFamille` (Task 3) ; `totalIntrouvables`, `detailRaisons` (`lib/index.ts`, plan 1).
- Produces: `LIBELLE_DATE` ; `semainesUnion(ps): string[]` ; `filtrerVerdicts(v, f)` ; `valeursDistinctes(v, cle)` ; composant `TrouvaillesView` ; onglet `trouvailles` (icône `Lightbulb`).

- [ ] **Step 1 : écrire les témoins**

Ajouter à `frontend/src/lib/science.test.ts` :

```ts
import { filtrerVerdicts, LIBELLE_RAISON_SEMAINES, noteFamille, semainesUnion, valeursDistinctes } from "./science";
import { scienceFixture } from "../components/science/scienceFixture";

test("semainesUnion : l'union triée des semaines publiées, familles à semaines null ignorées", () => {
  expect(semainesUnion(scienceFixture().trouvailles!.par_semaine!)).toEqual(["2026-W36", "2026-W37", "2026-W38"]);
});

test("noteFamille : la date nommée, et la cause publiée quand semaines est null (A1, I2)", () => {
  const ps = scienceFixture().trouvailles!.par_semaine!;
  expect(noteFamille(ps.record)).toBe("date d'entrée dans git");
  expect(noteFamille(ps.ref)).toBe("date d'entrée dans git : non mesurable ici (instantané des dates absent)");
  expect(noteFamille(ps.adr)).toBe("famille non lue par l'index");
  expect(noteFamille({ ...ps.adr, date: null, raison: "sans_date_nommee" })).toBe("aucune date nommée pour cette famille");
  for (const r of Object.keys(LIBELLE_RAISON_SEMAINES)) expect(noteFamille({ ...ps.adr, raison: r as never })).not.toBe("");
});

test("filtres de verdicts ; valeurs distinctes sans null", () => {
  const v = scienceFixture().trouvailles!.verdicts!;
  expect(filtrerVerdicts(v, { verdict: "NEGATIVE", gate: "" })).toHaveLength(1);
  expect(filtrerVerdicts(v, { verdict: "", gate: "G1" })[0].chemin).toBe("docs/EDR/001_a.md");
  expect(valeursDistinctes(v, "gate")).toEqual(["G1"]);
});
```

`frontend/src/components/science/TrouvaillesView.test.tsx` (même en-tête de rendu) :

```tsx
test("verdicts de l'index, filtrables ; écart au graphe publié", async () => {
  rendre(<TrouvaillesView />);
  const t = await screen.findByRole("table", { name: "Verdicts déclarés" });
  expect(within(t).getByText("X_DEMANDED")).toBeTruthy();
  expect(within(t).getByText("docs/EDR/002_b.md").closest("tr")!.textContent).toContain("sans titre");
  expect(screen.getByText("2 affiché(s) sur 2")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Verdict"), { target: { value: "NEGATIVE" } });
  expect(screen.getByText("1 affiché(s) sur 2")).toBeTruthy();
  expect(screen.getByText(/Graphe de records : 2 verdicts/)).toBeTruthy();
});

test("par semaine : la DATE nommée en en-tête, zéro mesuré, la CAUSE publiée de chaque null, semaine partielle", async () => {
  rendre(<TrouvaillesView />);
  const t = await screen.findByRole("table", { name: "Artefacts par semaine" });
  expect(within(t).getByText(/record — date d'entrée dans git/)).toBeTruthy();
  expect(within(t).getByText(/spec — date déclarée/)).toBeTruthy();
  // A1 (I2) : chaque null dit SA cause, jamais « famille non lue » ni « git indisponible » pour toutes
  expect(within(t).getByText(/ref — date d'entrée dans git : non mesurable ici \(instantané des dates absent\)/))
    .toBeTruthy();
  expect(within(t).getByText(/adr — famille non lue par l'index/)).toBeTruthy();
  expect(within(t).getByText(/sdr — parité rompue/)).toBeTruthy();
  const w37 = within(t).getByText("2026-W37").closest("tr")!;
  expect(within(w37).getByText("0")).toBeTruthy();
  const w38 = within(t).getByText("2026-W38").closest("tr")!;
  expect(within(w38).getByText("2 (partielle)")).toBeTruthy();                // A1 (I3) : jamais lue pleine
  const sans = within(t).getByText("sans date").closest("tr")!;
  expect(within(sans).getByText("1 (sans_ajout_trouve 1)")).toBeTruthy();
  expect(within(sans).getByText("4 (dates_absentes 4)")).toBeTruthy();
  expect(within(sans).getAllByText("inconnu")).toHaveLength(2);              // adr et sdr : jamais 0
  expect(screen.getByText(/instantané git complet, âge 1 min/)).toBeTruthy();
});

test("verdicts PARTIELS : dit à côté du compte, jamais un compte complet", async () => {
  const f = scienceFixture();
  mocked.mockResolvedValue({ ...f, trouvailles: { ...f.trouvailles!, verdicts_partiels: true } });
  rendre(<TrouvaillesView />);
  expect(await screen.findByText(/liste PARTIELLE/)).toBeTruthy();
  expect(screen.getByText("2 affiché(s) sur 2")).toBeTruthy();
});

test("aucun texte de tendance", async () => {
  const { container } = rendre(<TrouvaillesView />);
  await screen.findByRole("table", { name: "Artefacts par semaine" });
  expect(container.textContent).not.toMatch(/accél|ralenti|hausse|baisse|tendance|progress/i);
});

test("trouvailles null : Empty avec SA ligne ; verdicts null : dit, jamais 0", async () => {
  const ligne = "trouvailles : index sans familles ou sans artefacts (mode dégradé de l'index) -- trouvailles INCONNUES";
  mocked.mockResolvedValue(scienceFixture({ trouvailles: null, aveugle: [ligne] }));
  rendre(<TrouvaillesView />);
  expect(await screen.findByText(`Trouvailles indisponible — ${ligne}`)).toBeTruthy();
  cleanup();
  const f = scienceFixture();
  mocked.mockResolvedValue({ ...f, trouvailles: { ...f.trouvailles!, verdicts: null } });
  rendre(<TrouvaillesView />);
  expect(await screen.findByText(/Verdicts inconnus/)).toBeTruthy();
});
```

Ajouter `fireEvent` à l'import de `@testing-library/react`. Dans `tabs.test.tsx`, l'attendu de la famille Science
devient `[["pipeline","Pipeline"],["taxonomie","Taxonomie"],["trouvailles","Trouvailles"]]`.

- [ ] **Step 2 : les lancer, ils échouent**

Run: `npx vitest run src/lib/science.test.ts src/components/science src/tabs.test.tsx`
Expected: FAIL — `TrouvaillesView` introuvable, `semainesUnion` non exporté.

- [ ] **Step 3 : couche pure, vue, onglet**

Ajouter à `frontend/src/lib/science.ts` :

```ts
import type { ScienceV1, SemainesFamille, TrouvailleVerdict } from "../api/pm";

type ParSemaine = NonNullable<NonNullable<ScienceV1["trouvailles"]>["par_semaine"]>;

/** Le nom lisible de la date qui compte une famille (spec §3.2) — écrit en en-tête, jamais sous-entendu. */
export const LIBELLE_DATE: Record<string, string> = {
  date_ajout_git: "date d'entrée dans git",
  date_declaree: "date déclarée",
};

/** Amendement A1 (I2) : la cause PUBLIÉE d'un `semaines` null (`science.RAISONS_SEMAINES`), jamais devinée. */
export const LIBELLE_RAISON_SEMAINES: Record<NonNullable<SemainesFamille["raison"]>, string> = {
  famille_non_lue: "famille non lue par l'index",
  parite_rompue: "parité rompue (comptes de l'index incohérents)",
  sans_date_nommee: "aucune date nommée pour cette famille",
  dates_absentes: "non mesurable ici (instantané des dates absent)",
  historique_tronque: "non mesurable ici (historique git tronqué)",
  git_indisponible: "non mesurable ici (git indisponible)",
};
const CAUSES_DE_DATE = new Set(["dates_absentes", "historique_tronque", "git_indisponible"]);

/** L'en-tête d'une famille : la date nommée ; si `semaines` est null, sa cause — précédée de la date quand c'est la
 *  SOURCE de date qui manque (la famille a été lue, ses artefacts sont comptés dans « sans date »). */
export function noteFamille(e: SemainesFamille): string {
  const date = e.date ? (LIBELLE_DATE[e.date] ?? e.date) : null;
  if (!e.raison) return date ?? "date non nommée";
  const cause = LIBELLE_RAISON_SEMAINES[e.raison] ?? e.raison;
  return CAUSES_DE_DATE.has(e.raison) && date ? `${date} : ${cause}` : cause;
}

/** L'union triée des semaines publiées (« AAAA-Www » se trie comme du texte). */
export function semainesUnion(ps: ParSemaine): string[] {
  const s = new Set<string>();
  for (const e of Object.values(ps)) if (e?.semaines) for (const k of Object.keys(e.semaines)) s.add(k);
  return [...s].sort();
}

export interface FiltreVerdicts {
  verdict: string;
  gate: string;
}

export function filtrerVerdicts(v: readonly TrouvailleVerdict[], f: FiltreVerdicts): TrouvailleVerdict[] {
  return v.filter((x) => (!f.verdict || x.verdict === f.verdict) && (!f.gate || x.gate === f.gate));
}

export function valeursDistinctes(v: readonly TrouvailleVerdict[], cle: "verdict" | "gate"): string[] {
  return [...new Set(v.map((x) => x[cle]).filter((x): x is string => typeof x === "string"))].sort();
}
```

`frontend/src/components/science/TrouvaillesView.tsx` :

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchScience } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { detailRaisons, totalIntrouvables } from "../../lib/index";
import { vscodeHref } from "../../lib/pilotage";
import { SCIENCE_POLL } from "../../lib/polling";
import { filtrerVerdicts, messageBloc, noteFamille, semainesUnion, TITRE_DEGRADE_SCIENCE,
  valeursDistinctes } from "../../lib/science";
import { AveugleBanner } from "../pilotage/AveugleBanner";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Field } from "../ui/Field";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";

const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

/** Onglet Trouvailles (P2.84) : les verdicts DÉCLARÉS dans les records (lus par l'index) et des comptes par
 *  semaine, sur une date NOMMÉE. Aucune phrase sur la pente (condition 4). */
export function TrouvaillesView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.science,
    queryFn: () => fetchScience(),
    ...SCIENCE_POLL,
  });
  const [verdict, setVerdict] = useState("");
  const [gate, setGate] = useState("");
  if (isLoading) return <Loading label="Chargement de la science…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — science inconnue." />;
  const t = data.trouvailles;
  if (!t) {
    return (
      <div className="pilotage-view">
        <h2>Trouvailles</h2>
        <AveugleBanner lignes={data.aveugle} prefixeDegrade="science:" titreDegrade={TITRE_DEGRADE_SCIENCE} />
        <Empty message={messageBloc(data.aveugle, "trouvailles", "Trouvailles")} />
      </div>
    );
  }
  const vus = t.verdicts ? filtrerVerdicts(t.verdicts, { verdict, gate }) : [];
  const ps = t.par_semaine ?? {};
  const familles = Object.keys(ps);
  const semaines = semainesUnion(ps);
  return (
    <div className="pilotage-view">
      <h2>Trouvailles</h2>
      <AveugleBanner lignes={data.aveugle} prefixeDegrade="science:" titreDegrade={TITRE_DEGRADE_SCIENCE} />
      <p className="text-dim">
        {t.compte_graphe == null
          ? "Graphe de records : compte non mesuré (voir les lignes d'aveuglement)."
          : `Graphe de records : ${t.compte_graphe} verdicts (SDR/ADR/EDR/REF) ; l'index en lit ${t.verdicts?.length ?? "un nombre inconnu"} dans docs/EDR.`}
      </p>
      <p className="text-dim">
        {t.dates == null
          ? "Dates d'entrée dans git : instantané absent (voir la ligne « trouvailles : (index) dates : … »)."
          : `Dates d'entrée dans git : instantané git ${t.dates.historique}, âge ${Math.round(t.dates.age_s / 60)} min, HEAD ${t.dates.head ?? "inconnu"}.`}
      </p>
      {!t.verdicts ? (
        <Empty message="Verdicts inconnus : la famille record n'a pas été lue par l'index (voir les lignes d'aveuglement)." />
      ) : (
        <>
          <div className="row mb-4">
            <Field label="Verdict">
              <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
                <option value="">tous</option>
                {valeursDistinctes(t.verdicts, "verdict").map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Porte">
              <select value={gate} onChange={(e) => setGate(e.target.value)}>
                <option value="">toutes</option>
                {valeursDistinctes(t.verdicts, "gate").map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </Field>
            <span className="text-dim">{`${vus.length} affiché(s) sur ${t.verdicts.length}`}</span>
            {t.verdicts_partiels && (
              <span className="text-dim">
                liste PARTIELLE : des records n'ont pas été lus ou portent un état mal typé (voir les lignes
                d'aveuglement)
              </span>
            )}
          </div>
          <Panel className="mb-4">
            <div className="pilotage-defilement">
              <table className="runs-table" aria-label="Verdicts déclarés">
                <thead>
                  <tr>
                    <th>Verdict</th>
                    <th>Titre</th>
                    <th>Porte</th>
                    <th>Date d'ajout</th>
                    <th>Chemin</th>
                  </tr>
                </thead>
                <tbody>
                  {vus.map((v) => {
                    const href = vscodeHref(data.repo_root, v.chemin);
                    return (
                      <tr key={v.chemin}>
                        <td>{v.verdict}</td>
                        <td>{v.titre ?? <Dim>sans titre</Dim>}</td>
                        <td>{v.gate ?? <Dim>—</Dim>}</td>
                        <td className="pilotage-nowrap">{v.date_ajout_git ?? <Dim>sans date d'ajout</Dim>}</td>
                        <td>{href ? <a href={href}>{v.chemin}</a> : v.chemin}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
      <Panel>
        <p className="text-dim">
          Artefacts indexés comptés par semaine ISO (UTC), chaque famille sur la date nommée dans son en-tête. Case vide :
          semaine hors de la période couverte par la famille. « (partielle) » : semaine de l'instantané, comptée
          jusqu'à lui seulement.
        </p>
        <div className="pilotage-defilement">
          <table className="runs-table" aria-label="Artefacts par semaine">
            <thead>
              <tr>
                <th>Semaine</th>
                {familles.map((f) => (
                  <th key={f}>{`${f} — ${noteFamille(ps[f])}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {semaines.map((s) => (
                <tr key={s}>
                  <td className="pilotage-nowrap">{s}</td>
                  {familles.map((f) => {
                    const n = ps[f].semaines?.[s];
                    const partielle = s === ps[f].semaine_partielle ? " (partielle)" : "";
                    return <td key={f}>{n == null ? "" : `${n}${partielle}`}</td>;
                  })}
                </tr>
              ))}
              <tr>
                <td>sans date</td>
                {familles.map((f) => {
                  const e = ps[f];
                  if (e.sans_date == null) return <td key={f}><Dim>inconnu</Dim></td>;
                  const n = totalIntrouvables(e.sans_date);
                  return <td key={f}>{n ? `${n} (${detailRaisons(e.sans_date)})` : "0"}</td>;
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
```

`tabs.ts` : `"trouvailles"` à la fin de `TAB_KEYS`, `Lightbulb` à l'import, `{ key: "trouvailles", label: "Trouvailles", icon: Lightbulb }` dans la famille Science. `App.tsx` : `lazy()` de `TrouvaillesView` et `{tab === "trouvailles" && <TrouvaillesView />}`.

- [ ] **Step 4 : les témoins passent ; mutants ; typage ; relecture visuelle**

Run: `npx vitest run src/lib/science.test.ts src/components/science src/tabs.test.tsx`, puis `npx tsc --noEmit -p tsconfig.json`.
Expected: PASS.
Mutants : semaine sans compte rendue « 0 » au lieu de vide hors période ; en-tête sans le nom de la date ; famille
à `raison` rendue comme mesurable ; une cause unique pour tous les null (le défaut I2) ; semaine partielle non
marquée ; `verdicts_partiels` ignoré. Expected : TUÉS. Relecture visuelle (390 px, 1280 px).

- [ ] **Step 5 : fermer P2.84, vague au FRONTEND.md, commit du pas 5c**

Backlog : l'en-tête de P2.84 passe au format des entrées closes du fichier (modèle : P2.114, close le 2026-09-26), avec
les shas des pas 4, 5a, 5b, 5c et ce qui reste hors périmètre (§8 de la spec : fermetures par semaine, arbres). La
clause `path_present=frontend/src/components/science/TrouvaillesView.tsx` est satisfaite par CE commit.
`docs/roadmap/FRONTEND.md` : une « Vague L — Index et Science » (état, route, onglets, coût mesuré de l'index et de
`compute_science`).
Run: suite complète `npm --prefix frontend test`, `python tools/check_backlog_freshness.py`.
Expected: verts ; la porte 4 voit la clause satisfaite ET l'entrée close.
Puis `commit-exact`, et compte rendu à Master 2 (shas des quatre commits, run CI lu par `python -m tools.ci_diff_failed`).
