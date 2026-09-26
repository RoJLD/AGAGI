# Auto-indexation des artefacts — plan 1 : l'index (P2.87) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** produire un artefact suffit à le rendre visible au dashboard : un index `index_v1` des familles d'artefacts du dépôt, servi par `GET /api/pm/index` et affiché dans un 4ᵉ onglet « Index » de la famille Pilotage, sans jamais fabriquer un titre, une date ou un état.

**Architecture:** un module pur `tools/pm/index_artefacts.py` lit les fichiers des familles déclarées (`FAMILLES`) avec trois lecteurs (frontmatter, markdown, JSON) ; les dates d'entrée dans le dépôt sont calculées par git LÀ où l'historique est complet et publiées dans `DATES_GIT.json` (writer : le tick PM ou la commande à la main), que l'index LIT avec son âge. Le backend sert l'index en mémoire (cache 60 s, filet de `pilotage_service`), le frontend l'affiche.

**Tech Stack:** Python 3.13 stdlib + PyYAML (nouvelle dépendance de l'image backend), FastAPI + pydantic v2, pytest ; React 18 + TypeScript strict + react-query v5 + vitest.

**Spec:** `docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md` (approuvée ; son §9 fait foi sur les sections précédentes là où la décision D1 les déplace). Le plan 2 (famille Science, P2.84) s'écrira quand celui-ci sera livré.

## Global Constraints

- Aucun champ fabriqué : titre, date, état introuvables = `None` ET comptés par famille et par champ avec une raison du vocabulaire FERMÉ (spec §3.1 et §9) ; jamais un titre tiré du nom, jamais `status: open` par défaut, jamais une date de repli ni une date du jour.
- L'index et le backend ne lancent JAMAIS git ; seul `ecrire_dates_git` le fait (tick PM ou `--ecrire-dates`).
- Âge d'un fichier publié = `now - generated_at`, jamais un `mtime`.
- Aucun littéral `results/` ni `data/` dans les modules (porte 12) : `src/paths.py`, ancré sur la racine.
- Préfixes `index:` réservés au mode dégradé du service ; lignes de source préfixées `dates :`, `famille <nom> :`, `frontmatter :`, `<bloc> :`.
- Tout import backend vers `tools/` doit tourner dans l'IMAGE docker ; `backend/requirements.txt` est la seule liste de dépendances.
- `make api-types` dans le MÊME commit que tout changement de `backend/app/schemas.py` ; `frontend/openapi.json` et `schema.ts` normalisés en LF.
- Commits par `python -m tools.check_staged_authorship commit-exact --attendu CHEMIN=FICHIER -F msg`, jamais nus, jamais `--no-verify`, messages SANS backticks ; tests Windows ET WSL (recette : mémoire `wsl-linux-repro`).
- Aucun test n'écrit dans l'arbre : dépôts jetables sous `tmp_path`, `AGAGI_DATA_ROOT` posé sur `tmp_path` dès qu'un code peut écrire `data/pm/`, environnement git ISOLÉ pour un dépôt jetable (`tools._git_env.env_isole`).
- Revue adversariale opus AVANT le commit des pas 1 (Tasks 1-5) et 2 (Task 6) — ils produisent des comptes.

## Review Focus

1. **Fichier globbé puis supprimé par une autre session avant sa lecture** (arbre partagé) → `illisibles` avec `lecture_impossible`, parité tenue, jamais une exception qui aveugle la famille — témoin en Task 3, Step 1 (`test_fichier_disparu_entre_glob_et_lecture`).
2. **`DATES_GIT.json` écrit sur une AUTRE branche que le checkout du backend** (worktree sur une branche en avance) → un chemin neuf absent de l'instantané rend `absent_des_dates`, jamais la date d'un autre fichier — témoin en Task 3 (`test_chemin_absent_de_l_instantane`).
3. **Nom de fichier non ASCII** (aucun aujourd'hui, mesuré) → git le citerait entre guillemets échappés sans `core.quotepath=false`, et l'index ne le daterait jamais — témoin en Task 4 (`test_nom_non_ascii_est_date`).
4. **Frontmatter en CRLF ou fichier avec BOM** (éditeurs Windows) → même lecture qu'en LF — témoin en Task 2 (`test_crlf_et_bom`).
5. **Configuration git héritée** (`diff.renames`, `core.quotepath`, `log.date`) → la commande figée donne le même résultat — témoin en Task 4 (`test_config_heritee_sans_effet`).

---

## Préalable

Travailler dans le worktree `.worktrees/front` (branche `tmp/front`). Avant la Task 1, et avant chaque commit :
`git fetch` puis fusionner la pointe de `feat/d1-prod-pairing` DANS `tmp/front` (jamais de `MERGE_HEAD` dans l'arbre
principal), en vérifiant l'union du backlog par compte d'entrées (`grep -c "^\*\*P"` avant et après). `python -m
tools.jobs.doctor` avant toute passe de tests longue ; aucune simulation, aucun bail `kuzu` dans ce plan.

## Structure des fichiers

| fichier | rôle | tâche |
| --- | --- | --- |
| `tools/frontmatter.py` | extraction du bloc frontmatter, partagée ; lecteur STRICT (lève) ; import PyYAML paresseux | 1 |
| `tools/consolidate_records.py` | `parse_record` appelle `bloc_frontmatter` — comportement inchangé | 1 |
| `tests/test_frontmatter.py` | lecteur strict + équivalence de `parse_record` sur les records réels | 1 |
| `tools/pm/index_artefacts.py` | `FAMILLES`, lecteurs par fichier, `indexer`, `read_dates`, `calculer_dates_git`, `ecrire_dates_git`, `main` | 2, 3, 4 |
| `tests/sandbox/test_pm_index_artefacts.py` | témoins de l'index et de l'écrivain | 2, 3, 4 |
| `tools/pm/tick.py`, `tests/sandbox/test_pm_tick.py` | le tick écrit `DATES_GIT.json` | 4 |
| `tests/sandbox/test_instrument_calibration.py`, `tools/instrument_calibration_baseline.json` | déclarations `CALIBRATED` et leur gel | 5 |
| `docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md`, `docs/roadmap/PRIORITES_ET_DETTES.md` | coût mesuré (§6) ; clause de P2.87 repointée sur la vue | 5 |
| `backend/app/services/index_service.py`, `backend/app/routes/pm.py`, `backend/app/schemas.py`, `backend/requirements.txt`, `tests/test_backend.py`, `.github/workflows/ci.yml`, `frontend/openapi.json`, `frontend/src/api/schema.ts` | route `/api/pm/index` | 6 |
| `frontend/src/components/pilotage/IndexView.tsx` (+ test), `frontend/src/api/pm.ts`, `queryKeys.ts`, `lib/polling.ts`, `tabs.ts`, `App.tsx`, `lib/index.ts` (+ test), fixture | onglet Index | 7 |

---

### Task 1 : `tools/frontmatter.py` — l'extraction partagée, et `parse_record` inchangé

**Files:**
- Create: `tools/frontmatter.py`
- Modify: `tools/consolidate_records.py:51-67` (`parse_record`)
- Test: `tests/test_frontmatter.py`

**Interfaces:**
- Produces: `bloc_frontmatter(texte: str) -> tuple[str, int] | None` (bloc YAML brut, position juste après la ligne fermante ; texte déjà normalisé en `\n`) ; `lire_frontmatter(texte: str) -> dict | None` (None sans bloc, `{}` pour un bloc vide ; lève `yaml.YAMLError`, `ValueError` (date impossible), `TypeError` (racine non-dict), `ImportError` avec `name == "yaml"`) ; `normaliser(texte: str) -> str`.

- [ ] **Step 1 : écrire les tests qui échouent**

`tests/test_frontmatter.py` :

```python
# -*- coding: utf-8 -*-
"""Frontmatter partagé : lecteur STRICT pour l'index (P2.87), extraction identique pour parse_record (porte 1)."""
import glob
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import frontmatter as F  # noqa: E402
from tools import consolidate_records as CR  # noqa: E402


def test_sans_bloc_rend_None():
    assert F.bloc_frontmatter("# Titre\n") is None
    assert F.lire_frontmatter("# Titre\n") is None
    assert F.lire_frontmatter("---\nid: X\nsans fermeture\n") is None     # bloc non fermé = pas de bloc


def test_bloc_vide_rend_un_dict_vide_et_la_position_de_fin():
    t = "---\n---\n# Titre\n"
    bloc, fin = F.bloc_frontmatter(t)
    assert bloc == "" and t[fin:] == "# Titre\n"
    assert F.lire_frontmatter(t) == {}


def test_bloc_lu_tel_quel():
    t = "---\nid: EDR-1\ntitle: \"Un titre : avec deux-points\"\ntests: [SDR-G1]\n---\ncorps\n"
    assert F.lire_frontmatter(t) == {"id": "EDR-1", "title": "Un titre : avec deux-points", "tests": ["SDR-G1"]}
    assert t[F.bloc_frontmatter(t)[1]:] == "corps\n"


@pytest.mark.parametrize("bloc, exc", [
    ("title: [a, b\n", yaml.YAMLError),                 # YAML cassé
    ("date: 2026-13-45\n", ValueError),                 # date impossible : PyYAML lève ValueError, pas YAMLError
    ("- a\n- b\n", TypeError),                          # racine non-dict
])
def test_le_lecteur_strict_LEVE(bloc, exc):
    with pytest.raises(exc):
        F.lire_frontmatter("---\n" + bloc + "---\n")


def test_normaliser_crlf():
    assert F.normaliser("a\r\nb\rc") == "a\nb\nc"


def _parse_record_d_origine(path):
    """Copie GELÉE de l'extraction de parse_record avant le 2026-09-26 : le témoin d'équivalence la compare au code
    courant sur les records RÉELS. Ne pas « corriger » cette copie : c'est la référence."""
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rec = CR._empty_record(os.path.relpath(path, CR._ROOT).replace(os.sep, "/"))
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(text[3:end]) or {}
            except yaml.YAMLError:
                meta = {}
            for k, v in meta.items():
                if k in CR._LIST_KEYS:
                    rec[k] = list(v) if v else []
                elif k in rec:
                    rec[k] = v
            if rec["id"]:
                rec["linked"] = True
                return rec
    m = CR._EDR_NAME.match(name)
    if m:
        rec["id"] = f"EDR-{int(m.group(1)):03d}{m.group(2)}"
        rec["type"] = "EDR"
        rec["title"] = name[m.end(2) + 1:-3].replace("_", " ")
        return rec
    return None


def test_parse_record_INCHANGE_sur_les_records_reels(capsys):
    """Porte 1 : l'extraction du bloc a changé de module, pas de comportement. Tous les records réels."""
    chemins = sorted(p for d in ("EDR", "ADR", "REF", "SDR")
                     for p in glob.glob(os.path.join(CR._ROOT, "docs", d, "*.md")))
    assert len(chemins) > 300, "contrôle : le motif doit voir les records réels"
    for p in chemins:
        assert CR.parse_record(p) == _parse_record_d_origine(p), p
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_frontmatter.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'frontmatter' from 'tools'`.

- [ ] **Step 3 : écrire `tools/frontmatter.py`**

```python
# -*- coding: utf-8 -*-
"""Frontmatter YAML en tête d'un `.md` — l'extraction partagée par `tools/consolidate_records.py` (porte 1) et
`tools/pm/index_artefacts.py` (P2.87, spec 2026-09-26).

Import de PyYAML PARESSEUX : un processus sans PyYAML sait encore dire qu'un fichier N'A PAS de frontmatter, et
seul un fichier qui EN A devient illisible (« pyyaml_absent »). `lire_frontmatter` est STRICT — il lève au lieu de
tolérer, parce que l'index doit NOMMER un frontmatter cassé ; `parse_record` garde, lui, sa propre tolérance.
"""


def normaliser(texte):
    return texte.replace("\r\n", "\n").replace("\r", "\n")


def bloc_frontmatter(texte):
    """`(bloc YAML brut, position juste après la ligne fermante)`, ou `None` sans bloc.

    Règle de `parse_record` depuis sa création : le texte COMMENCE par `---` et un `\\n---` le ferme. Le texte doit
    être normalisé en `\\n` (`normaliser`)."""
    if not texte.startswith("---"):
        return None
    fin = texte.find("\n---", 3)
    if fin == -1:
        return None
    apres = texte.find("\n", fin + 4)
    return texte[3:fin], (len(texte) if apres == -1 else apres + 1)


def lire_frontmatter(texte):
    """`dict` (vide pour un bloc vide) ou `None` sans bloc. LÈVE : `yaml.YAMLError` (YAML invalide), `ValueError`
    (date impossible, ex. `2026-13-45`), `TypeError` (racine non-dict), `ImportError` (PyYAML absent)."""
    b = bloc_frontmatter(texte)
    if b is None:
        return None
    import yaml
    meta = yaml.safe_load(b[0])
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise TypeError(f"frontmatter de type {type(meta).__name__}")
    return meta
```

- [ ] **Step 4 : faire appeler `bloc_frontmatter` par `parse_record`**

Dans `tools/consolidate_records.py`, ajouter l'import sous `import yaml` (l.14) :

```python
from tools.frontmatter import bloc_frontmatter
```

⚠️ `consolidate_records.py` ajoute `_ROOT` à `sys.path` APRÈS ses imports (l.16-18) : placer l'import APRÈS ce bloc
`if _ROOT not in sys.path: …`, avec `# noqa: E402`, sinon un appel direct `python tools/consolidate_records.py` ne
trouve pas le paquet `tools`. Puis remplacer, dans `parse_record`, tout le bloc qui commence à
`if text.startswith("---"):` et finit à `return rec` (le premier) par :

```python
    bloc = bloc_frontmatter(text)
    if bloc is not None:
        try:
            meta = yaml.safe_load(bloc[0]) or {}
        except yaml.YAMLError as e:
            # Frontmatter YAML illisible (ex. valeur non quotee avec ':') : NE PAS crasher tout
            # le graphe pour un seul record malforme (souvent une session //). On avertit et on
            # traite le fichier comme sans frontmatter -> EDR NNN_*.md tolere non-lie.
            print(f"WARN: frontmatter YAML illisible dans {name} "
                  f"({e.__class__.__name__}) -> record tolere non-lie", file=sys.stderr)
            meta = {}
        for k, v in meta.items():
            if k in _LIST_KEYS:
                rec[k] = list(v) if v else []
            elif k in rec:
                rec[k] = v
        if rec["id"]:
            rec["linked"] = True
            return rec
```

`bloc[0]` vaut exactement `text[3:end]` : seuls changent le test d'entrée et la source du bloc (un niveau
d'indentation en moins) ; le corps, le message du WARN et les défauts de `_empty_record` sont IDENTIQUES — c'est ce que
juge le témoin d'équivalence.

- [ ] **Step 5 : lancer les tests — nouveaux et existants de la porte 1**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_frontmatter.py tests/test_consolidate_records.py tests/sandbox/test_record_graph_completeness.py -q -p no:cacheprovider`
Expected: PASS, dont `test_parse_record_INCHANGE_sur_les_records_reels` (plus de 300 records).

Pas de commit ici : le pas 1 de la spec (Tasks 1-5) part en un commit après la revue opus (Task 5).

---

### Task 2 : `tools/pm/index_artefacts.py` — la table des familles et les lecteurs par fichier

**Files:**
- Create: `tools/pm/index_artefacts.py`
- Test: `tests/sandbox/test_pm_index_artefacts.py`

**Interfaces:**
- Consumes: `tools.frontmatter.bloc_frontmatter`, `lire_frontmatter`, `normaliser` (Task 1) ; `tools.consolidate_records._LIST_KEYS`.
- Produces: `FAMILLES: tuple[Famille, ...]`, `Famille(nom, repertoire, motif, forme, exclus)` (`repertoire` : `callable(racine) -> str`) ; `lire_fichier(chemin: str, rel: str, fam: Famille) -> tuple` = `("indexe", artefact: dict, manques: dict[str, str], cles_format: set[str])` ou `("illisible", raison: str, None, None)` ; `RAISONS_ILLISIBLE`, `RAISONS_CHAMP`, `RAISONS_DATE_GIT`, `CLES_FORMAT`, `SCHEMA`, `SCHEMA_DATES`, `HISTORIQUES` ; `_rel(racine, chemin) -> str | None`.

- [ ] **Step 1 : écrire les tests qui échouent**

`tests/sandbox/test_pm_index_artefacts.py` :

```python
# -*- coding: utf-8 -*-
"""Index des artefacts (P2.87). EXEMPTION DÉCLARÉE de la garde de bail : aucun monde, aucun bail.
Aucun test n'écrit dans l'arbre : fichiers sous tmp_path, AGAGI_DATA_ROOT sur tmp_path dès qu'un code peut écrire."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import index_artefacts as IX  # noqa: E402

_LEASE_GUARD_EXEMPT = True
NOW = 1_800_000_000.0
FAM = {f.nom: f for f in IX.FAMILLES}


def _ecrire(p, texte, mode="w"):
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "wb":
        p.write_bytes(texte)
    else:
        p.write_text(texte, encoding="utf-8")
    return p


def _lire(p, famille):
    return IX.lire_fichier(str(p), p.name, FAM[famille])


def test_record_a_frontmatter_complet(tmp_path):
    p = _ecrire(tmp_path / "001_x.md", "---\nid: EDR-001\ntype: EDR\ntitle: Un titre\nstatus: validated\n"
                "verdict: X_DEMANDED\ngate: G1\ndate: 2026-09-01\ntests: [SDR-G1]\ncorrected_by: EDR-002\n---\ncorps\n")
    etat, a, manques, fmt = _lire(p, "record")
    assert etat == "indexe" and manques == {}
    assert (a["titre"], a["etat"], a["etat_source"], a["gate"]) == ("Un titre", "X_DEMANDED", "verdict", "G1")
    assert (a["date_declaree"], a["date_source"]) == ("2026-09-01", "frontmatter")
    assert {"rel": "tests", "cible": "SDR-G1"} in a["liens"] and {"rel": "corrected_by", "cible": "EDR-002"} in a["liens"]
    assert fmt == {"date"}


def test_record_SANS_frontmatter_ne_FABRIQUE_ni_titre_ni_statut(tmp_path):
    """B1 de la revue : parse_record rendait title tiré du NOM et status 'open' pour 34 EDR légataires."""
    p = _ecrire(tmp_path / "011_World_Model.md", "# World Model\ncorps\n")
    etat, a, manques, _ = _lire(p, "record")
    assert etat == "indexe"
    assert a["titre"] is None and a["etat"] is None and a["etat_source"] is None
    assert manques == {"titre": "frontmatter_absent", "date_declaree": "frontmatter_absent", "etat": "frontmatter_absent"}


def test_ref_sans_status_n_est_pas_open(tmp_path):
    p = _ecrire(tmp_path / "Baldwin.md", "---\nid: REF-B\ntype: REF\ntitle: Baldwin\n---\n")
    _, a, manques, _ = _lire(p, "ref")
    assert a["etat"] is None and manques["etat"] == "cle_absente"


@pytest.mark.parametrize("bloc, raison", [
    ("title: [a, b\n", "frontmatter_yaml_invalide"),
    ("date: 2026-13-45\n", "frontmatter_yaml_invalide"),
    ("- a\n- b\n", "frontmatter_non_dict"),
])
def test_frontmatter_casse_est_ILLISIBLE_et_nomme(tmp_path, bloc, raison):
    p = _ecrire(tmp_path / "x.md", "---\n" + bloc + "---\n")
    assert _lire(p, "record") == ("illisible", raison, None, None)


def test_types_inattendus_normalises_a_None(tmp_path):
    p = _ecrire(tmp_path / "x.md", "---\nid: X\ntitle: [a, b]\nverdict: {x: 1}\nstatus: 3\ntests: 5\n---\n")
    etat, a, manques, _ = _lire(p, "record")
    assert etat == "indexe" and a["titre"] is None and a["etat"] is None
    assert manques["titre"] == "type_inattendu" and manques["etat"] == "type_inattendu"
    assert manques["liens"] == "type_inattendu" and a["liens"] == []


def test_fichier_vide_et_encodage(tmp_path):
    assert _lire(_ecrire(tmp_path / "v.md", ""), "spec") == ("illisible", "fichier_vide", None, None)
    assert _lire(_ecrire(tmp_path / "e.md", b"\xff\xfe\x00titre", "wb"), "spec")[1] == "encodage_invalide"


def test_crlf_et_bom(tmp_path):
    """Review Focus 4 : un éditeur Windows écrit CRLF et parfois un BOM — même lecture qu'en LF."""
    p = _ecrire(tmp_path / "2026-09-26-x.md", "\ufeff---\r\netat: brouillon\r\n---\r\n# Titre CRLF\r\n".encode("utf-8"),
                "wb")
    etat, a, manques, fmt = _lire(p, "spec")
    assert etat == "indexe" and a["titre"] == "Titre CRLF" and a["etat"] == "brouillon" and fmt == {"etat"}


def test_spec_titre_date_du_nom_et_etat_non_declare(tmp_path):
    p = _ecrire(tmp_path / "2026-09-26-design.md", "```\n# pas un titre\n```\n# Le vrai titre\n")
    etat, a, manques, fmt = _lire(p, "spec")
    assert (a["titre"], a["date_declaree"], a["date_source"]) == ("Le vrai titre", "2026-09-26", "nom")
    assert manques == {"etat": "frontmatter_absent"} and fmt == set()


@pytest.mark.parametrize("nom, raison", [("sans-date.md", "nom_non_date"), ("2026-13-45-x.md", "nom_date_invalide")])
def test_plan_nom_sans_date_valide_jamais_de_repli(tmp_path, nom, raison):
    p = _ecrire(tmp_path / nom, "# Titre\n")
    _, a, manques, _ = _lire(p, "plan")
    assert a["date_declaree"] is None and a["date_source"] is None and manques["date_declaree"] == raison


def test_spec_sans_titre_md(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "2026-09-26-x.md", "pas de titre\n"), "spec")
    assert a["titre"] is None and manques["titre"] == "titre_md_absent"


def test_date_frontmatter_invalide_ne_retombe_pas_sur_le_nom(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "2026-09-26-x.md", "---\ndate: bientot\n---\n# T\n"), "spec")
    assert a["date_declaree"] is None and manques["date_declaree"] == "date_invalide"


def test_json_resultat_et_preinscription(tmp_path):
    r = _ecrire(tmp_path / "r.json", json.dumps({"name": "run", "verdict": {"x": 1}, "etat": "ok", "_regime": {},
                                                 "date": "2026-09-02"}))
    etat, a, manques, fmt = _lire(r, "resultat")
    assert (a["titre"], a["etat"], a["etat_source"], a["regime"], a["scelle"]) == ("run", "ok", "etat", True, None)
    assert (a["date_declaree"], a["date_source"]) == ("2026-09-02", "cle") and fmt == {"date", "etat"}
    s = _ecrire(tmp_path / "S2-X.json", json.dumps({"name": "S2-X", "rule": {}, "seal": "abc"}))
    _, b, manques, _ = _lire(s, "preinscription")
    assert b["scelle"] is True and b["etat"] is None and manques["etat"] == "cle_absente"


def test_json_verdict_dict_n_est_pas_un_etat(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "r.json", json.dumps({"verdict": {"x": 1}})), "resultat")
    assert a["etat"] is None and manques["etat"] == "type_inattendu" and manques["titre"] == "cle_absente"


def test_json_racine_liste_et_json_invalide(tmp_path):
    etat, a, manques, _ = _lire(_ecrire(tmp_path / "l.json", "[1, 2]"), "resultat")
    assert etat == "indexe" and set(manques.values()) == {"racine_non_objet"} and a["regime"] is None
    assert _lire(_ecrire(tmp_path / "b.json", "{pas du json"), "resultat") == ("illisible", "json_invalide", None, None)


def test_pyyaml_absent_ne_rend_illisibles_que_les_fichiers_A_frontmatter(tmp_path, monkeypatch):
    import builtins
    vrai_import = builtins.__import__

    def _sans_yaml(name, *a, **k):
        if name == "yaml":
            raise ImportError("No module named 'yaml'", name="yaml")
        return vrai_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", _sans_yaml)
    avec = _ecrire(tmp_path / "2026-09-26-a.md", "---\netat: x\n---\n# A\n")
    sans = _ecrire(tmp_path / "2026-09-26-b.md", "# B\n")
    assert _lire(avec, "spec") == ("illisible", "pyyaml_absent", None, None)
    assert _lire(sans, "spec")[0] == "indexe"


def test_raisons_produites_toutes_dans_le_vocabulaire_ferme():
    assert IX.RAISONS_ILLISIBLE.isdisjoint(IX.RAISONS_CHAMP)
    for r in ("frontmatter_absent", "cle_absente", "type_inattendu", "racine_non_objet", "titre_md_absent",
              "nom_non_date", "nom_date_invalide", "date_invalide"):
        assert r in IX.RAISONS_CHAMP
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'index_artefacts' from 'tools.pm'`.

- [ ] **Step 3 : écrire le module (partie 1 : table et lecteurs)**

`tools/pm/index_artefacts.py` :

```python
# -*- coding: utf-8 -*-
"""Index des artefacts du dépôt (P2.87) — spec docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md.

`indexer` LIT les fichiers des familles déclarées dans `FAMILLES` et rend `index_v1` ; il n'écrit rien et ne lance
jamais git. Les dates d'entrée dans le dépôt viennent de `DATES_GIT.json`, écrit par `ecrire_dates_git` (writer
unique : le tick PM, ou la même commande à la main) là où l'historique git est complet, et LU avec son âge.

Aucun champ n'est FABRIQUÉ : un titre, une date ou un état introuvable vaut `None` ET il est compté, par famille et
par champ, avec une raison du vocabulaire fermé ci-dessous (condition 2 de Master 2, porte 14).
"""
import argparse
import collections
import datetime
import glob
import json
import math
import os
import re
import subprocess
import sys
import time

SCHEMA = "index_v1"
SCHEMA_DATES = "dates_git_v1"
HISTORIQUES = ("complet", "tronque", "indisponible")
CLES_FORMAT = ("date", "etat", "sujet", "liens")        # `type` exclu : la porte 1 l'impose aux records

# Vocabulaire FERMÉ (spec §3.1 et §9). `lecture_impossible` : fichier globbé puis supprimé avant sa lecture —
# l'arbre est partagé entre sessions (Review Focus 1).
RAISONS_ILLISIBLE = frozenset({"lecture_impossible", "encodage_invalide", "fichier_vide", "json_invalide",
                               "frontmatter_yaml_invalide", "frontmatter_non_dict", "pyyaml_absent"})
RAISONS_CHAMP = frozenset({"frontmatter_absent", "cle_absente", "type_inattendu", "racine_non_objet",
                           "titre_md_absent", "nom_non_date", "nom_date_invalide", "date_invalide"})
RAISONS_DATE_GIT = frozenset({"dates_absentes", "historique_tronque", "git_indisponible", "hors_depot",
                              "absent_des_dates", "sans_ajout_trouve"})

_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NOM_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def _dans(*parties):
    return lambda racine: os.path.join(racine, *parties)


def _resultats(racine):
    """Répertoire des résultats par `src/paths.py` (porte 12), ancré sur la racine s'il est relatif."""
    from src import paths
    r = paths.results_root()
    return r if os.path.isabs(r) else os.path.join(racine, r)


Famille = collections.namedtuple("Famille", "nom repertoire motif forme exclus")

# Une famille neuve = une ligne ; l'ORDRE est l'ordre de sortie. Exclus PUBLIÉS par famille, jamais retirés en silence.
FAMILLES = (
    Famille("record", _dans("docs", "EDR"), "*.md", "md_frontmatter", ("README.md",)),
    Famille("adr", _dans("docs", "ADR"), "*.md", "md_frontmatter", ()),
    Famille("ref", _dans("docs", "REF"), "*.md", "md_frontmatter", ("README.md",)),
    Famille("sdr", _dans("docs", "SDR"), "*.md", "md_frontmatter", ()),
    Famille("resultat", _resultats, "*.json", "json", ("records_graph.json",)),     # dérivé par consolidate_records
    Famille("preinscription", _dans("docs", "preregistrations"), "*.json", "json", ()),
    Famille("spec", _dans("docs", "superpowers", "specs"), "*.md", "md", ()),
    Famille("plan", _dans("docs", "superpowers", "plans"), "*.md", "md", ()),
    Famille("revue", _dans("docs", "reviews"), "*.md", "md", ("README.md",)),
)


def _rel(racine, chemin):
    """Chemin POSIX relatif à la racine, ou `None` s'il en sort (répertoire des résultats hors du dépôt)."""
    try:
        r = os.path.relpath(os.path.abspath(chemin), os.path.abspath(racine))
    except ValueError:                                   # deux lecteurs Windows différents
        return None
    if r == os.pardir or r.startswith(os.pardir + os.sep):
        return None
    return r.replace(os.sep, "/")


def _lire_texte(chemin):
    """`(texte normalisé, None)` ou `(None, raison d'illisibilité)`."""
    try:
        with open(chemin, "rb") as fh:
            brut = fh.read()
    except OSError:
        return None, "lecture_impossible"
    if not brut.strip():
        return None, "fichier_vide"
    try:
        texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "encodage_invalide"
    from tools.frontmatter import normaliser
    return normaliser(texte), None


def _frontmatter(texte):
    """`(meta | None, fin, raison | None)` — `meta` None ET raison None : pas de bloc ; raison : illisible."""
    from tools.frontmatter import bloc_frontmatter, lire_frontmatter
    bloc = bloc_frontmatter(texte)
    if bloc is None:
        return None, 0, None
    try:
        meta = lire_frontmatter(texte)
    except ImportError as exc:
        if getattr(exc, "name", None) == "yaml":
            return None, 0, "pyyaml_absent"
        raise
    except TypeError:
        return None, 0, "frontmatter_non_dict"
    except Exception:                                    # noqa: BLE001 — yaml.YAMLError, ValueError d'une date impossible
        return None, 0, "frontmatter_yaml_invalide"
    return meta, bloc[1], None


def _chaine(d, cle):
    """`(chaîne non vide, None)` ou `(None, raison)`."""
    v = d.get(cle)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, "cle_absente"
    return (v.strip(), None) if isinstance(v, str) else (None, "type_inattendu")


def _premiere_chaine(d, cles):
    """`(valeur, clé source, raison)` : la première clé qui porte une chaîne ; sinon `type_inattendu` si une des
    clés existe avec un autre type, `cle_absente` sinon."""
    raison = "cle_absente"
    for cle in cles:
        v, r = _chaine(d, cle)
        if v is not None:
            return v, cle, None
        if r == "type_inattendu":
            raison = r
    return None, None, raison


def _date(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, "cle_absente"
    if isinstance(v, datetime.datetime):
        return v.date().isoformat(), None
    if isinstance(v, datetime.date):
        return v.isoformat(), None
    if isinstance(v, str) and _DATE_ISO.match(v.strip()):
        try:
            return datetime.date.fromisoformat(v.strip()).isoformat(), None
        except ValueError:
            return None, "date_invalide"
    return None, "date_invalide"


def _date_nom(nom):
    m = _NOM_DATE.match(nom)
    if not m:
        return None, "nom_non_date"
    try:
        return datetime.date.fromisoformat(m.group(1)).isoformat(), None
    except ValueError:
        return None, "nom_date_invalide"


def _titre_md(texte, debut):
    """Premier titre `# ` hors bloc de code, après le frontmatter ; `None` s'il n'y en a pas."""
    dans_code = False
    for ligne in texte[debut:].split("\n"):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
            continue
        if not dans_code and ligne.startswith("# ") and ligne[2:].strip():
            return ligne[2:].strip()
    return None


def _liens(meta):
    """`(liens, rejets)` — toutes les clés d'arête que lit la porte 1 (`consolidate_records._LIST_KEYS`)."""
    from tools.consolidate_records import _LIST_KEYS
    out, rejets = [], 0
    for cle in _LIST_KEYS:
        v = meta.get(cle)
        if v is None:
            continue
        cibles = [v] if isinstance(v, str) else v if isinstance(v, list) else None
        if cibles is None:
            rejets += 1
            continue
        for c in cibles:
            if isinstance(c, str) and c.strip():
                out.append({"rel": cle, "cible": c.strip()})
            else:
                rejets += 1
    return out, rejets


def _artefact(famille, rel):
    return {"famille": famille, "chemin": rel, "titre": None, "date_declaree": None, "date_source": None,
            "date_ajout_git": None, "etat": None, "etat_source": None, "regime": None, "scelle": None,
            "gate": None, "liens": []}


def _poser(art, manques, champ, valeur, raison):
    art[champ] = valeur
    if raison:
        manques[champ] = raison


def _lire_record(texte, art, manques):
    meta, _, raison = _frontmatter(texte)
    if raison:
        return ("illisible", raison, None, None)
    if meta is None:
        for champ in ("titre", "date_declaree", "etat"):
            manques[champ] = "frontmatter_absent"
        return ("indexe", art, manques, set())
    art["titre"], _, r = _premiere_chaine(meta, ("title",))
    if r:
        manques["titre"] = r
    art["etat"], art["etat_source"], r = _premiere_chaine(meta, ("verdict", "status"))
    if r:
        manques["etat"] = r
    art["date_declaree"], r = _date(meta.get("date"))
    if r:
        manques["date_declaree"] = r
    else:
        art["date_source"] = "frontmatter"
    art["gate"], _, _ = _premiere_chaine(meta, ("gate",))
    art["liens"], rejets = _liens(meta)
    if rejets:
        manques["liens"] = "type_inattendu"
    return ("indexe", art, manques, {c for c in CLES_FORMAT if c in meta})


def _lire_md(texte, art, manques, nom):
    meta, fin, raison = _frontmatter(texte)
    if raison:
        return ("illisible", raison, None, None)
    titre = _titre_md(texte, fin)
    _poser(art, manques, "titre", titre, None if titre else "titre_md_absent")
    if meta is not None and meta.get("date") is not None:
        d, r, src = (*_date(meta.get("date")), "frontmatter")
    else:
        d, r, src = (*_date_nom(nom), "nom")
    _poser(art, manques, "date_declaree", d, r)
    art["date_source"] = None if r else src
    if meta is None:
        manques["etat"] = "frontmatter_absent"
    else:
        art["etat"], art["etat_source"], r = _premiere_chaine(meta, ("etat",))
        if r:
            manques["etat"] = r
    return ("indexe", art, manques, {c for c in CLES_FORMAT if meta and c in meta})


def _lire_json(texte, art, manques, fam):
    try:
        d = json.loads(texte)
    except ValueError:
        return ("illisible", "json_invalide", None, None)
    if not isinstance(d, dict):
        for champ in ("titre", "date_declaree", "etat"):
            manques[champ] = "racine_non_objet"
        return ("indexe", art, manques, set())
    art["titre"], _, r = _premiere_chaine(d, ("name", "title"))
    if r:
        manques["titre"] = r
    art["etat"], art["etat_source"], r = _premiere_chaine(d, ("etat", "verdict"))
    if r:
        manques["etat"] = r
    art["date_declaree"], r = _date(d.get("date"))
    if r:
        manques["date_declaree"] = r
    else:
        art["date_source"] = "cle"
    art["regime"] = "regime" in d or "_regime" in d
    if fam.nom == "preinscription":
        art["scelle"] = "seal" in d
    return ("indexe", art, manques, {c for c in CLES_FORMAT if c in d})


def lire_fichier(chemin, rel, fam):
    """`("indexe", artefact, manques, cles_format)` ou `("illisible", raison, None, None)`."""
    texte, raison = _lire_texte(chemin)
    if raison:
        return ("illisible", raison, None, None)
    art, manques = _artefact(fam.nom, rel), {}
    if fam.forme == "json":
        return _lire_json(texte, art, manques, fam)
    if fam.forme == "md_frontmatter":
        return _lire_record(texte, art, manques)
    return _lire_md(texte, art, manques, os.path.basename(chemin))
```

- [ ] **Step 4 : lancer les tests**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider`
Expected: PASS (18 cas).

---

### Task 3 : `read_dates` et `indexer` — familles, parité, dates lues, hors familles

**Files:**
- Modify: `tools/pm/index_artefacts.py` (ajouts en fin de module)
- Test: `tests/sandbox/test_pm_index_artefacts.py` (ajouts)

**Interfaces:**
- Consumes: `lire_fichier`, `FAMILLES`, `_rel` (Task 2) ; `tools.pm.snapshot.base_des_donnees` ; `src.paths.pm_dir`.
- Produces: `chemin_dates(racine) -> str` ; `read_dates(racine) -> {"doc": dict | None, "chemin": str, "raison": str | None}` ; `indexer(racine: str, lecture_dates: dict, now: float) -> dict` (forme `index_v1`, spec §3.1 et §9 : clés `schema, generated_at, repo_root, aveugle, dates, familles, hors_familles, artefacts`).

- [ ] **Step 1 : écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_pm_index_artefacts.py` :

```python
def _depot(tmp_path):
    """Un dépôt jetable (fichiers seulement, pas de git) portant une famille de chaque forme."""
    r = tmp_path / "depot"
    _ecrire(r / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\ntitle: A\nverdict: V\n---\n")
    _ecrire(r / "docs" / "EDR" / "002_b.md", "# B sans frontmatter\n")
    _ecrire(r / "docs" / "EDR" / "README.md", "# lisez-moi\n")
    _ecrire(r / "docs" / "EDR" / "003_c.md", "---\ntitle: [x\n---\n")
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-01-s.md", "# S\n")
    _ecrire(r / "docs" / "superpowers" / "plans" / "sans-date.md", "# P\n")
    _ecrire(r / "results" / "r.json", json.dumps({"name": "r"}))
    _ecrire(r / "results" / "records_graph.json", "{}")
    return r


def _sans_dates(r):
    return {"doc": None, "chemin": str(r / "data" / "pm" / "DATES_GIT.json"), "raison": "introuvable"}


def _dates(dates, suivis, historique="complet"):
    return {"doc": {"schema": IX.SCHEMA_DATES, "generated_at": NOW - 600, "head": "abc", "historique": historique,
                    "raison": None, "dates": dates, "suivis": suivis}, "chemin": "x", "raison": None}


@pytest.fixture
def resultats_dans_le_depot(monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", "sentinelle")
    monkeypatch.delenv("AGAGI_RESULTS_ROOT", raising=False)


def _famille(out, nom):
    return next(f for f in out["familles"] if f["nom"] == nom)


def test_NO_OP_EXACT_racine_vide(tmp_path, resultats_dans_le_depot):
    out = IX.indexer(str(tmp_path), _sans_dates(tmp_path), NOW)
    assert out["schema"] == "index_v1" and out["artefacts"] == [] and out["hors_familles"] is None
    for f in out["familles"]:
        assert f["fichiers"] is None and f["indexes"] is None and f["illisibles"] is None, f
    lignes = [a for a in out["aveugle"] if a.startswith("famille ")]
    assert len(lignes) == len(IX.FAMILLES) and all("absent" in a for a in lignes)
    assert any(a.startswith("dates : ") for a in out["aveugle"])
    assert not any(a.startswith("index:") for a in out["aveugle"])     # réservé au mode dégradé du service


def test_injection_a_dose_connue(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    rec = _famille(out, "record")
    assert (rec["fichiers"], rec["indexes"], rec["exclus"]) == (4, 2, ["README.md"])
    assert rec["illisibles"] == [{"chemin": "docs/EDR/003_c.md", "raison": "frontmatter_yaml_invalide"}]
    assert rec["champs_introuvables"]["titre"] == {"frontmatter_absent": 1}
    assert rec["champs_introuvables"]["date_ajout_git"] == {"dates_absentes": 2}
    res = _famille(out, "resultat")
    assert (res["fichiers"], res["indexes"], res["exclus"]) == (2, 1, ["records_graph.json"])
    plan = _famille(out, "plan")
    assert plan["champs_introuvables"]["date_declaree"] == {"nom_non_date": 1}
    assert _famille(out, "adr")["fichiers"] is None                     # répertoire absent : inconnu, jamais 0
    assert out["dates"] is None
    b = next(a for a in out["artefacts"] if a["chemin"] == "docs/EDR/002_b.md")
    assert b["titre"] is None and b["etat"] is None                    # contre-exemple B1 gelé


def test_prediction_un_fichier_de_plus(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    avant = IX.indexer(str(r), _sans_dates(r), NOW)
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-02-t.md", "# T\n")
    apres = IX.indexer(str(r), _sans_dates(r), NOW)
    for fa, fb in zip(avant["familles"], apres["familles"]):
        attendu = 1 if fa["nom"] == "spec" else 0
        if fa["fichiers"] is not None:
            assert (fb["fichiers"] - fa["fichiers"], fb["indexes"] - fa["indexes"]) == (attendu, attendu), fa["nom"]


def test_parite_rompue_aveugle_la_FAMILLE_seule(tmp_path, resultats_dans_le_depot, monkeypatch):
    r = _depot(tmp_path)
    vrai = IX.lire_fichier

    def _perd_un(chemin, rel, fam):
        return ("perdu", None, None, None) if rel.endswith("001_a.md") else vrai(chemin, rel, fam)
    monkeypatch.setattr(IX, "lire_fichier", _perd_un)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    assert _famille(out, "record")["fichiers"] is None
    assert any(a.startswith("famille record : parité rompue") for a in out["aveugle"])
    assert _famille(out, "spec")["indexes"] == 1                          # les autres familles restent servies
    assert not any(a["famille"] == "record" for a in out["artefacts"])


def test_fichier_disparu_entre_glob_et_lecture(tmp_path, resultats_dans_le_depot, monkeypatch):
    """Review Focus 1 : arbre partagé — une autre session supprime le fichier entre le glob et la lecture."""
    r = _depot(tmp_path)
    vrai_open = open

    def _open(chemin, *a, **k):
        if str(chemin).endswith("2026-09-01-s.md"):
            raise FileNotFoundError(chemin)
        return vrai_open(chemin, *a, **k)
    monkeypatch.setattr("builtins.open", _open)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    spec = _famille(out, "spec")
    assert spec["illisibles"] == [{"chemin": "docs/superpowers/specs/2026-09-01-s.md", "raison": "lecture_impossible"}]
    assert spec["fichiers"] == 1 and spec["indexes"] == 0


def test_dates_lues_age_sur_generated_at(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({"docs/EDR/001_a.md": "2026-09-01"},
                                    ["docs/EDR/001_a.md", "docs/EDR/002_b.md", "docs/roadmap/X.md"]), NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    b = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/002_b.md")
    assert a["date_ajout_git"] == "2026-09-01" and b["date_ajout_git"] is None
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {"sans_ajout_trouve": 1}
    assert out["dates"] == {"generated_at": NOW - 600, "age_s": 600.0, "head": "abc", "historique": "complet"}
    assert out["hors_familles"] == {"n": 1, "repertoires": {"docs/roadmap": 1}}


def test_chemin_absent_de_l_instantane(tmp_path, resultats_dans_le_depot):
    """Review Focus 2 : instantané écrit sur une autre branche — un chemin neuf n'a PAS de date, jamais une autre."""
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({}, []), NOW)
    assert all(x["date_ajout_git"] is None for x in out["artefacts"])
    assert _famille(out, "spec")["champs_introuvables"]["date_ajout_git"] == {"absent_des_dates": 1}


@pytest.mark.parametrize("historique, raison", [("tronque", "historique_tronque"), ("indisponible", "git_indisponible")])
def test_historique_non_complet(tmp_path, resultats_dans_le_depot, historique, raison):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates(None, None, historique), NOW)
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {raison: 2}
    assert out["hors_familles"] is None and any(a.startswith("dates : ") for a in out["aveugle"])


def test_read_dates_absent_illisible_et_de_forme_inattendue(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    r = str(tmp_path)
    assert IX.read_dates(r)["raison"] == "introuvable"
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "DATES_GIT.json").write_text("{casse", encoding="utf-8")
    assert IX.read_dates(r)["raison"].startswith("illisible")
    (tmp_path / "pm" / "DATES_GIT.json").write_text(json.dumps({"schema": "autre"}), encoding="utf-8")
    assert IX.read_dates(r)["raison"].startswith("de forme inattendue")
    (tmp_path / "pm" / "DATES_GIT.json").write_text(json.dumps(
        {"schema": IX.SCHEMA_DATES, "generated_at": NOW, "head": "h", "historique": "complet", "raison": None,
         "dates": {"a.md": "2026-09-01"}, "suivis": ["a.md"]}), encoding="utf-8")
    lu = IX.read_dates(r)
    assert lu["raison"] is None and lu["doc"]["dates"] == {"a.md": "2026-09-01"}
    assert "AGAGI_DATA_ROOT" in os.environ                               # posé par le test, pas écrit par le lecteur


def test_age_des_dates_jamais_le_mtime(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    (tmp_path / "pm").mkdir()
    p = tmp_path / "pm" / "DATES_GIT.json"
    p.write_text(json.dumps({"schema": IX.SCHEMA_DATES, "generated_at": NOW - 3600, "head": "h",
                             "historique": "complet", "raison": None, "dates": {}, "suivis": []}), encoding="utf-8")
    os.utime(p, (NOW, NOW))                                              # mtime FRAIS, contenu d'il y a une heure
    out = IX.indexer(str(tmp_path), IX.read_dates(str(tmp_path)), NOW)
    assert out["dates"]["age_s"] == 3600.0


def test_parite_sur_le_depot_REEL():
    """Chaque fichier globbé des familles réelles finit dans exactement un compartiment, et aucune n'est null."""
    from tools.pm.pilotage import racine_depot
    r = racine_depot()
    out = IX.indexer(r, {"doc": None, "chemin": "-", "raison": "introuvable"}, NOW)
    for f in out["familles"]:
        assert f["fichiers"] is not None, (f["nom"], out["aveugle"])
        assert f["indexes"] + len(f["illisibles"]) + len(f["exclus"]) == f["fichiers"], f["nom"]
    raisons = {r for f in out["familles"] for c in f["champs_introuvables"].values() for r in c}
    raisons |= {i["raison"] for f in out["familles"] for i in f["illisibles"]}
    assert raisons <= IX.RAISONS_CHAMP | IX.RAISONS_ILLISIBLE | IX.RAISONS_DATE_GIT, raisons
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider`
Expected: FAIL — `AttributeError: module 'tools.pm.index_artefacts' has no attribute 'indexer'`.

- [ ] **Step 3 : écrire `read_dates` et `indexer`**

Ajouter à `tools/pm/index_artefacts.py` :

```python
def chemin_dates(racine):
    """Le chemin que `read_dates` CHERCHE (et que `ecrire_dates_git` écrit) : `paths.pm_dir`, ancré sur le dépôt
    COMMUN par une résolution PURE (`snapshot.base_des_donnees`, P2.114)."""
    from src import paths
    from tools.pm.snapshot import base_des_donnees
    p = paths.pm_dir("DATES_GIT.json")
    return (p if os.path.isabs(p) else os.path.join(base_des_donnees(racine), p)).replace("\\", "/")


def _forme_dates(doc):
    """`None` si `doc` a la forme `dates_git_v1`, sinon la raison du refus."""
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_DATES:
        return "schema différent de dates_git_v1"
    g = doc.get("generated_at")
    if isinstance(g, bool) or not isinstance(g, (int, float)) or not math.isfinite(g):
        return "generated_at non numérique ou non fini"
    h = doc.get("historique")
    if h not in HISTORIQUES:
        return f"historique inconnu ({h!r})"
    dates, suivis = doc.get("dates"), doc.get("suivis")
    if h != "complet":
        return None if dates is None and suivis is None else "dates/suivis non null hors historique complet"
    if not isinstance(dates, dict) or not all(isinstance(k, str) and isinstance(v, str) and _DATE_ISO.match(v)
                                              for k, v in dates.items()):
        return "dates n'est pas un dict chemin -> AAAA-MM-JJ"
    if not isinstance(suivis, list) or not all(isinstance(s, str) for s in suivis):
        return "suivis n'est pas une liste de chemins"
    return None


def read_dates(racine):
    """`{"doc", "chemin", "raison"}` — le fichier écrit par `ecrire_dates_git`, jamais git."""
    chemin = chemin_dates(racine)
    try:
        with open(chemin, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError:
        return {"doc": None, "chemin": chemin, "raison": "introuvable"}
    except ValueError as exc:
        return {"doc": None, "chemin": chemin, "raison": f"illisible (JSON invalide : {exc})"}
    refus = _forme_dates(doc)
    if refus:
        return {"doc": None, "chemin": chemin, "raison": f"de forme inattendue ({refus})"}
    return {"doc": doc, "chemin": chemin, "raison": None}


def _lignes_dates(lecture):
    doc = lecture.get("doc")
    if doc is None:
        return [f"dates : DATES_GIT.json {lecture.get('raison')} à {lecture.get('chemin')} -- écrivain jamais passé "
                "(tick PM ou --ecrire-dates), ou racine de données mal résolue : l'absence ne tranche pas ; dates "
                "d'ajout et fichiers hors familles INCONNUS"]
    if doc["historique"] == "tronque":
        return [f"dates : historique git TRONQUÉ là où l'instantané a été écrit ({doc.get('raison')}) -- aucune date "
                "d'ajout publiée, fichiers hors familles inconnus"]
    if doc["historique"] == "indisponible":
        return [f"dates : git indisponible là où l'instantané a été écrit ({doc.get('raison')}) -- aucune date "
                "d'ajout publiée, fichiers hors familles inconnus"]
    return []


def _date_git(rel, doc, suivis):
    if doc is None:
        return None, "dates_absentes"
    if doc["historique"] == "tronque":
        return None, "historique_tronque"
    if doc["historique"] != "complet":
        return None, "git_indisponible"
    if rel is None:
        return None, "hors_depot"
    d = doc["dates"].get(rel)
    if d is not None:
        return d, None
    return None, ("sans_ajout_trouve" if rel in suivis else "absent_des_dates")


def _hors_familles(racine, suivis):
    """Fichiers SUIVIS sous `docs/` et le répertoire des résultats qui ne tombent dans aucune famille (I13)."""
    import fnmatch
    if suivis is None:
        return None
    couverts = [(_rel(racine, f.repertoire(racine)), f.motif) for f in FAMILLES]
    zones = ["docs/"] + [z + "/" for z in [_rel(racine, _resultats(racine))] if z]
    compte = collections.Counter()
    for s in suivis:
        if not any(s.startswith(z) for z in zones):
            continue
        rep, nom = os.path.dirname(s), os.path.basename(s)
        if any(rep == d and fnmatch.fnmatch(nom, m) for d, m in couverts if d):
            continue
        compte["/".join(s.split("/")[:2])] += 1
    return {"n": sum(compte.values()), "repertoires": dict(sorted(compte.items()))}


def indexer(racine, lecture_dates, now):
    """`index_v1` — lit les fichiers, n'écrit rien, ne lance jamais git (spec §3.1, §9)."""
    racine = str(racine).replace("\\", "/")
    now = float(now)
    aveugle = list(_lignes_dates(lecture_dates))
    doc = lecture_dates.get("doc")
    complet = doc is not None and doc["historique"] == "complet"
    suivis = set(doc["suivis"]) if complet else None
    familles, artefacts, sans_yaml = [], [], 0
    for fam in FAMILLES:
        rep = fam.repertoire(racine)
        ligne = {"nom": fam.nom, "motif": fam.motif, "repertoire": _rel(racine, rep) or rep.replace("\\", "/"),
                 "exclus": [], "fichiers": None, "indexes": None, "illisibles": None,
                 "champs_introuvables": None, "format_declare": None}
        if not os.path.isdir(rep):
            aveugle.append(f"famille {fam.nom} : répertoire {ligne['repertoire']} absent -- fichiers INCONNUS, jamais 0")
            familles.append(ligne)
            continue
        chemins = sorted(p for p in glob.glob(os.path.join(rep, fam.motif)) if os.path.isfile(p))
        exclus, illisibles, arts = [], [], []
        champs = {c: collections.Counter() for c in ("titre", "date_declaree", "etat", "date_ajout_git", "liens")}
        fmt = collections.Counter()
        for p in chemins:
            nom, rel = os.path.basename(p), _rel(racine, p)
            if nom in fam.exclus:
                exclus.append(nom)
                continue
            etat, a, manques, cles = lire_fichier(p, rel or p.replace("\\", "/"), fam)
            if etat == "illisible":
                illisibles.append({"chemin": rel or p.replace("\\", "/"), "raison": a})
                sans_yaml += a == "pyyaml_absent"
                continue
            if etat != "indexe":
                continue                                  # un lecteur qui perd un fichier rompt la parité ci-dessous
            a["date_ajout_git"], r = _date_git(rel, doc, suivis)
            if r:
                manques["date_ajout_git"] = r
            for champ, raison in manques.items():
                champs[champ][raison] += 1
            fmt.update(cles)
            arts.append(a)
        if len(arts) + len(illisibles) + len(exclus) != len(chemins):
            aveugle.append(f"famille {fam.nom} : parité rompue ({len(chemins)} fichiers, "
                           f"{len(arts) + len(illisibles) + len(exclus)} classés) -- famille servie à null")
            familles.append(ligne)
            continue
        ligne.update(exclus=exclus, fichiers=len(chemins), indexes=len(arts), illisibles=illisibles,
                     champs_introuvables={c: dict(v) for c, v in champs.items()},
                     format_declare={**{c: fmt[c] for c in CLES_FORMAT}, "fichiers": len(arts)})
        familles.append(ligne)
        artefacts.extend(arts)
    if sans_yaml:
        aveugle.append(f"frontmatter : PyYAML absent de ce processus -- {sans_yaml} fichier(s) à frontmatter illisible(s)")
    dates = None if doc is None else {"generated_at": doc["generated_at"], "age_s": now - float(doc["generated_at"]),
                                      "head": doc.get("head"), "historique": doc["historique"]}
    return {"schema": SCHEMA, "generated_at": now, "repo_root": racine, "aveugle": aveugle, "dates": dates,
            "familles": familles, "hors_familles": _hors_familles(racine, suivis), "artefacts": artefacts}
```

- [ ] **Step 4 : lancer les tests**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider`
Expected: PASS. Si `test_parite_sur_le_depot_REEL` échoue sur une raison hors vocabulaire, c'est un DÉFAUT du lecteur :
le corriger, jamais élargir le vocabulaire sans l'écrire dans la spec (§9) dans le même commit.

---

### Task 4 : l'écrivain `DATES_GIT.json`, la commande, et le tick PM

**Files:**
- Modify: `tools/pm/index_artefacts.py` (ajouts), `tools/pm/tick.py`
- Test: `tests/sandbox/test_pm_index_artefacts.py`, `tests/sandbox/test_pm_tick.py`

**Interfaces:**
- Consumes: `FAMILLES`, `_rel`, `_resultats`, `chemin_dates`, `read_dates`, `indexer` ; `tools.check_evidence_provenance._env_pour(root)` (rend `None` = hériter pour le dépôt courant, ou un env isolé pour un dépôt tiers) ; `tools._git_env.env_isole()` (tests).
- Produces: `calculer_dates_git(racine: str, now: float) -> dict` (forme `dates_git_v1`, ne lève jamais) ; `ecrire_dates_git(racine: str, now: float) -> tuple[dict, str]` ; `main(argv) -> int` (`--json`, `--ecrire-dates`, `--repo-root`) ; dans `tools/pm/tick.py` : `ecrire_dates(repo_root, now) -> str` (ligne de digest ou `""`).

- [ ] **Step 1 : écrire les tests qui échouent**

Ajouter à `tests/sandbox/test_pm_index_artefacts.py` :

```python
import pathlib  # noqa: E402
import subprocess  # noqa: E402

from tools._git_env import env_isole  # noqa: E402


def _git(repo, *args, date=None):
    env = env_isole()
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                          cwd=repo, env=env, capture_output=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def depot_git(tmp_path, monkeypatch):
    """Dépôt jetable RÉEL : deux commits à dates connues. AGAGI_DATA_ROOT sur tmp_path : l'écrivain n'écrit jamais
    dans le data/ réel. Environnement git isolé (règle à deux faces)."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path / "data").replace("\\", "/"))
    for v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(v, raising=False)
    r = tmp_path / "depot"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _ecrire(r / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\n---\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "a", date="2026-09-01T23:30:00+00:00")
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-02-s.md", "# S\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "s", date="2026-09-08T00:30:00+02:00")      # 2026-09-07 22:30 UTC
    return r


def test_calculer_dates_complet_en_UTC(depot_git):
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "complet" and doc["raison"] is None and len(doc["head"]) == 40
    assert doc["dates"] == {"docs/EDR/001_a.md": "2026-09-01",
                            "docs/superpowers/specs/2026-09-02-s.md": "2026-09-07"}       # jour UTC, pas local
    assert set(doc["suivis"]) == set(doc["dates"])


def test_chemin_ajoute_supprime_recree_prend_la_date_la_plus_ANCIENNE(depot_git):
    _git(depot_git, "rm", "-q", "docs/EDR/001_a.md")
    _git(depot_git, "commit", "-q", "-m", "rm", date="2026-09-10T12:00:00+00:00")
    _ecrire(depot_git / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\n---\nv2\n")
    _git(depot_git, "add", "-A")
    _git(depot_git, "commit", "-q", "-m", "re", date="2026-09-12T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"]["docs/EDR/001_a.md"] == "2026-09-01"


def test_renommage_est_une_entree_du_chemin(depot_git):
    _git(depot_git, "mv", "docs/EDR/001_a.md", "docs/EDR/001_b.md")
    _git(depot_git, "commit", "-q", "-m", "mv", date="2026-09-15T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"]["docs/EDR/001_b.md"] == "2026-09-15"


def test_config_heritee_sans_effet(depot_git):
    """Review Focus 5 : diff.renames et core.quotepath posés dans la config du dépôt ne changent rien."""
    avant = IX.calculer_dates_git(str(depot_git), NOW)["dates"]
    _git(depot_git, "config", "diff.renames", "copies")
    _git(depot_git, "config", "core.quotepath", "true")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"] == avant


def test_nom_non_ascii_est_date(depot_git):
    """Review Focus 3 : sans core.quotepath=false, git citerait "docs/EDR/002_\\303\\251t\\303\\251.md"."""
    _ecrire(depot_git / "docs" / "EDR" / "002_été.md", "# x\n")
    _git(depot_git, "add", "-A")
    _git(depot_git, "commit", "-q", "-m", "e", date="2026-09-20T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"].get("docs/EDR/002_été.md") == "2026-09-20"


def test_clone_superficiel_est_TRONQUE_jamais_date_du_jour(depot_git, tmp_path):
    """B3 de la revue : un clone --depth 1 datait tout du jour du clone."""
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", pathlib.Path(depot_git).as_uri(), str(clone))   # file:///C:/…
    doc = IX.calculer_dates_git(str(clone), NOW)
    assert doc["historique"] == "tronque" and doc["dates"] is None and doc["suivis"] is None
    assert "superficiel" in doc["raison"]


def test_hors_depot_et_racine_qui_n_est_pas_le_toplevel(tmp_path, depot_git):
    assert IX.calculer_dates_git(str(tmp_path / "nulle_part"), NOW)["historique"] == "indisponible"
    doc = IX.calculer_dates_git(str(depot_git / "docs"), NOW)             # un sous-répertoire n'est pas la racine
    assert doc["historique"] == "indisponible" and "toplevel" in doc["raison"]


def test_ecrire_puis_lire_boucle_complete(depot_git):
    doc, chemin = IX.ecrire_dates_git(str(depot_git), NOW)
    assert os.path.isfile(chemin) and chemin.endswith("pm/DATES_GIT.json")
    lu = IX.read_dates(str(depot_git))
    assert lu["raison"] is None and lu["doc"] == doc
    out = IX.indexer(str(depot_git), lu, NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    assert a["date_ajout_git"] == "2026-09-01"


def test_main_json_n_ecrit_rien_et_ecrire_dates_ecrit_UN_fichier(depot_git, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    avant = sorted(os.listdir(tmp_path))
    assert IX.main(["--json", "--repo-root", str(depot_git)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "index_v1"
    assert sorted(os.listdir(tmp_path)) == avant
    assert IX.main(["--ecrire-dates", "--repo-root", str(depot_git)]) == 0
    assert os.listdir(tmp_path / "data" / "pm") == ["DATES_GIT.json"]
```

Ajouter à `tests/sandbox/test_pm_tick.py` :

```python
def test_ecrire_dates_du_tick_ecrit_DATES_GIT_et_se_tait_si_complet(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    from tools.pm import index_artefacts as IX
    monkeypatch.setattr(IX, "calculer_dates_git", lambda racine, now: {
        "schema": IX.SCHEMA_DATES, "generated_at": now, "head": "h", "historique": "complet", "raison": None,
        "dates": {}, "suivis": []})
    assert TK.ecrire_dates(os.getcwd(), 1000.0) == ""
    assert (tmp_path / "pm" / "DATES_GIT.json").exists()


def test_ecrire_dates_du_tick_DIT_un_historique_tronque_et_une_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    from tools.pm import index_artefacts as IX
    monkeypatch.setattr(IX, "calculer_dates_git", lambda racine, now: {
        "schema": IX.SCHEMA_DATES, "generated_at": now, "head": None, "historique": "tronque",
        "raison": "clone superficiel", "dates": None, "suivis": None})
    assert TK.ecrire_dates(os.getcwd(), 1000.0).startswith("[PM] dates git : historique tronque")

    def _leve(*a, **k):
        raise OSError("disque plein")
    monkeypatch.setattr(IX, "ecrire_dates_git", _leve)
    assert TK.ecrire_dates(os.getcwd(), 1000.0).startswith("[PM] AVEUGLE SUR dates git")
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py tests/sandbox/test_pm_tick.py -q -p no:cacheprovider`
Expected: FAIL — `AttributeError: … 'calculer_dates_git'` et `… 'ecrire_dates'`.

- [ ] **Step 3 : écrire l'écrivain et la commande**

Ajouter à `tools/pm/index_artefacts.py` :

```python
def _git(racine, env, *args):
    """`(stdout, None)` ou `(None, raison)` — jamais levé."""
    try:
        p = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=racine, env=env, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if p.returncode != 0:
        return None, (p.stderr or "").strip()[:200] or f"code {p.returncode}"
    return p.stdout, None


def calculer_dates_git(racine, now):
    """`dates_git_v1` — dates d'entrée du CHEMIN actuel dans le dépôt (spec §3.1 et §9, D1). Ne lève jamais.

    Commande FIGÉE, jamais la config héritée : `--no-renames` et `diff.renames=false` (un renommage est une
    entrée), `core.quotepath=false` (noms non ASCII), `%ct` en UTC, et pour un chemin ajouté plusieurs fois la
    date la PLUS ANCIENNE (sortie antichronologique : la dernière écriture l'emporte). Un clone superficiel est
    `tronque` : `--depth 1` date tout du jour du clone (B3)."""
    from tools.check_evidence_provenance import _env_pour
    racine = str(racine)
    doc = {"schema": SCHEMA_DATES, "generated_at": float(now), "head": None, "historique": "indisponible",
           "raison": None, "dates": None, "suivis": None}
    env = _env_pour(racine)
    top, err = _git(racine, env, "rev-parse", "--show-toplevel")
    if top is None:
        doc["raison"] = f"git muet : {err}"
        return doc
    if os.path.normcase(os.path.realpath(top.strip())) != os.path.normcase(os.path.realpath(racine)):
        doc["raison"] = f"toplevel {top.strip()} différent de la racine {racine}"
        return doc
    head, _ = _git(racine, env, "rev-parse", "HEAD")
    doc["head"] = head.strip() if head else None
    peu, err = _git(racine, env, "rev-parse", "--is-shallow-repository")
    if peu is None:
        doc["raison"] = f"état de l'historique illisible : {err}"
        return doc
    if peu.strip() == "true":
        doc.update(historique="tronque", raison="clone superficiel (git rev-parse --is-shallow-repository = true)")
        return doc
    reps = sorted({r for r in (_rel(racine, f.repertoire(racine)) for f in FAMILLES) if r})
    out, err = _git(racine, env, "-c", "diff.renames=false", "log", "--no-renames", "--diff-filter=A",
                    "--format=%x1e%ct", "--name-only", "--", *reps)
    if out is None:
        doc["raison"] = f"git log : {err}"
        return doc
    dates = {}
    for bloc in out.split("\x1e"):
        lignes = [l for l in bloc.split("\n") if l.strip()]
        if not lignes or not lignes[0].strip().isdigit():
            continue
        jour = datetime.datetime.fromtimestamp(int(lignes[0]), tz=datetime.timezone.utc).date().isoformat()
        for chemin in lignes[1:]:
            dates[chemin.strip()] = jour
    zones = ["docs"] + [z for z in [_rel(racine, _resultats(racine))] if z]
    ls, err = _git(racine, env, "ls-files", "-z", "--", *zones)
    if ls is None:
        doc["raison"] = f"git ls-files : {err}"
        return doc
    doc.update(historique="complet", dates=dates, suivis=sorted(s for s in ls.split("\0") if s))
    return doc


def ecrire_dates_git(racine, now):
    """Writer UNIQUE de `DATES_GIT.json` (tick PM ou `--ecrire-dates`, même programme). Rend `(doc, chemin)`."""
    doc = calculer_dates_git(racine, now)
    chemin = chemin_dates(racine)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    return doc, chemin


def main(argv=None):
    """`--json` imprime l'index (n'écrit rien, ne lance pas git) ; `--ecrire-dates` écrit DATES_GIT.json."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=None)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--ecrire-dates", action="store_true")
    args = ap.parse_args(argv)
    from tools.pm.pilotage import racine_depot
    racine = args.repo_root or racine_depot()
    if args.ecrire_dates:
        doc, chemin = ecrire_dates_git(racine, time.time())
        print(f"[index] {chemin} : historique {doc['historique']}, {len(doc['dates'] or {})} date(s)"
              + (f" -- {doc['raison']}" if doc["raison"] else ""))
        return 0 if doc["historique"] == "complet" else 1
    out = indexer(racine, read_dates(racine), time.time())
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"[index] {out['schema']} — {len(out['artefacts'])} artefact(s), {len(out['aveugle'])} aveuglement(s)")
        for a in out["aveugle"]:
            print("  AVEUGLE :", a)
        for f in out["familles"]:
            print(f"  {f['nom']:<15} fichiers={f['fichiers']} indexés={f['indexes']} "
                  f"illisibles={None if f['illisibles'] is None else len(f['illisibles'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : brancher le tick PM**

Dans `tools/pm/tick.py`, remplacer

```python
    pilotage = ecrire_pilotage(args.repo_root, board, counts, now)
    print(digest(board, d, counts, illisibles=illisibles) + ("\n" + pilotage if pilotage else ""))
    return 0
```

par

```python
    lignes = [l for l in (ecrire_pilotage(args.repo_root, board, counts, now), ecrire_dates(args.repo_root, now)) if l]
    print(digest(board, d, counts, illisibles=illisibles) + ("\n" + "\n".join(lignes) if lignes else ""))
    return 0


def ecrire_dates(repo_root, now):
    """Spec P2.87 §9 (D1) : le tick, qui tourne là où l'historique git est complet, écrit `DATES_GIT.json`, que le
    backend LIT avec son âge. Une ligne de digest si l'historique n'est pas complet ou si l'écriture lève — jamais
    un tick qui échoue (BOARD.json, journal, compteurs et pilotage sont déjà écrits)."""
    try:
        from tools.pm import index_artefacts as IX
        doc, _ = IX.ecrire_dates_git(str(repo_root).replace("\\", "/"), now)
    except Exception as exc:                            # noqa: BLE001 — NOMMÉ dans le digest, jamais avalé
        return f"[PM] AVEUGLE SUR dates git (DATES_GIT.json non écrit : {type(exc).__name__}: {exc})"
    if doc["historique"] != "complet":
        return f"[PM] dates git : historique {doc['historique']} ({doc['raison']}) -- aucune date d'ajout publiée"
    return ""
```

et ajouter, dans `test_main_ecrit_tableau_journal_compteurs_et_sort_0` (même test, nom conservé : la porte 10 compte
un renommage comme une disparition), après les assertions du pilotage :

```python
    assert (tmp_path / "pm" / "DATES_GIT.json").exists()
```

- [ ] **Step 5 : lancer les tests (index, tick, pilotage)**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_index_artefacts.py tests/sandbox/test_pm_tick.py tests/sandbox/test_pm_pilotage.py tests/test_frontmatter.py -q -p no:cacheprovider`
Expected: PASS.

---

### Task 5 : calibration, coût mesuré, revue opus, commit du pas 1

**Files:**
- Modify: `tests/sandbox/test_instrument_calibration.py` (bloc `CALIBRATED`, après les deux entrées du pilotage), `tools/instrument_calibration_baseline.json` (`declarations_ignorees`), `docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md` (§6), `docs/roadmap/PRIORITES_ET_DETTES.md` (clause de P2.87)

- [ ] **Step 1 : déclarer les deux instruments**

Dans `CALIBRATED`, après l'entrée `"tools/pm/pilotage.py::parse_roadmap": [...]` :

```python
    # Index des artefacts (P2.87, 2026-09-26) : `indexer` publie des comptes (fichiers, indexés, champs
    # introuvables, format déclaré) et `calculer_dates_git` des dates — des instruments. Le cliquet ne capte pas
    # ces noms (P2.83) : déclarations GELÉES dans `declarations_ignorees`, garantie par les cas qui tournent en CI.
    "tools/pm/index_artefacts.py::indexer": ["no-op:racine-vide-fichiers-null", "injection:dose-connue",
                                             "prediction:un-fichier-de-plus", "parite:famille-null-seule",
                                             "reel:parite-et-vocabulaire-ferme"],
    "tools/pm/index_artefacts.py::calculer_dates_git": ["reel:depot-jetable-dates-utc", "tronque:clone-depth-1",
                                                        "config-heritee:sans-effet", "plus-ancienne:ajout-recree"],
```

- [ ] **Step 2 : geler les deux déclarations et vérifier la porte 2**

Ajouter `"tools/pm/index_artefacts.py::calculer_dates_git"` et `"tools/pm/index_artefacts.py::indexer"` à la liste
`declarations_ignorees` de `tools/instrument_calibration_baseline.json`, dans l'ordre alphabétique de la liste.

Run: `PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py 2>&1 | tail -3`
Expected: `OK : aucun nouvel instrument non calibré ; 12 déclaration(s) ignorée(s), toutes légataires (baseline).`
Si la porte DÉTECTE l'un des deux noms (motif élargi depuis), le retirer du gel : une déclaration détectée et
calibrée n'a rien à geler.

- [ ] **Step 3 : mesurer le coût, machine au repos, charge notée — et le publier au §6 de la spec**

```bash
python -m tools.jobs.doctor
PYTHONIOENCODING=utf-8 python - <<'EOF'
import time, json, psutil
from tools.pm import index_artefacts as IX
from tools.pm.pilotage import racine_depot
print("charge :", psutil.cpu_percent(interval=1.0), "%")
r = racine_depot()
for i in range(3):
    t0 = time.perf_counter(); d = IX.calculer_dates_git(r, time.time()); t1 = time.perf_counter()
    out = IX.indexer(r, {"doc": d, "chemin": "-", "raison": None}, time.time()); t2 = time.perf_counter()
    print(f"passe {i+1} : dates {t1-t0:.2f} s ({d['historique']}, {len(d['dates'] or {})}), indexer {t2-t1:.2f} s, "
          f"{len(out['artefacts'])} artefacts, {len(json.dumps(out, ensure_ascii=False).encode())} octets")
EOF
```

Remplacer au §6 la phrase « À mesurer au pas 1 … » par les trois passes mesurées, la charge et la date. Si
`indexer` dépasse 2 s, noter que le cache du service passera à 300 s (Task 6, Step 3).

- [ ] **Step 4 : repointer la clause de P2.87 sur la VUE**

La clause actuelle (`path_present=tools/pm/index_artefacts.py`) serait satisfaite par CE commit alors que P2.87 n'est
pas livré (le dashboard ne s'indexe qu'au pas 3) — la porte 4 signalerait une entrée ouverte à clause satisfaite.
Remplacer, dans l'entrée P2.87 de `docs/roadmap/PRIORITES_ET_DETTES.md` :

```text
<!-- closes_when:path_present=tools/pm/index_artefacts.py -->
```

par

```text
<!-- closes_when:path_present=frontend/src/components/pilotage/IndexView.tsx -->
```

Run: `PYTHONIOENCODING=utf-8 python tools/check_backlog_freshness.py 2>&1 | head -3`
Expected: `OK : …` sans nouvelle péremption.

- [ ] **Step 5 : suites Windows puis WSL**

Run (Windows) : `PYTHONIOENCODING=utf-8 python -m pytest tests/test_frontmatter.py tests/test_consolidate_records.py tests/sandbox/test_pm_index_artefacts.py tests/sandbox/test_pm_tick.py tests/sandbox/test_pm_pilotage.py tests/sandbox/test_pm_snapshot.py tests/sandbox/test_instrument_calibration.py -q -p no:cacheprovider`
Run (WSL) : recette de la mémoire `wsl-linux-repro` (copie par `git archive` du worktree + fichiers modifiés par `tar --force-local -rf`, copie devenue dépôt git, venv `~/agagi-venv`, `python` dans le PATH), mêmes fichiers.
Expected: PASS des deux côtés ; noter les comptes.

- [ ] **Step 6 : revue adversariale opus AVANT le commit**

Lancer un sous-agent opus (lecture + sondes, n'écrit rien dans le dépôt) sur le diff des Tasks 1-5 : fabrication d'un
état, parité, vocabulaire, écrivain git (règle à deux faces, clone superficiel, worktree), équivalence de
`parse_record`, porte 12, porte 2. Traiter chaque constat Bloquant/Important, rejouer les tests, puis committer.

- [ ] **Step 7 : commit du pas 1**

Copier chaque fichier produit dans le scratchpad (`--attendu`), écrire le message dans un fichier (sans backticks) et :

```bash
python -m tools.check_staged_authorship commit-exact \
  --attendu tools/frontmatter.py=<copie> --attendu tools/consolidate_records.py=<copie> \
  --attendu tools/pm/index_artefacts.py=<copie> --attendu tools/pm/tick.py=<copie> \
  --attendu tests/test_frontmatter.py=<copie> --attendu tests/sandbox/test_pm_index_artefacts.py=<copie> \
  --attendu tests/sandbox/test_pm_tick.py=<copie> --attendu tests/sandbox/test_instrument_calibration.py=<copie> \
  --attendu tools/instrument_calibration_baseline.json=<copie> \
  --attendu docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md=<copie> \
  --attendu docs/roadmap/PRIORITES_ET_DETTES.md=<copie> -F <message>
```

Expected: `exit=0`, chaque fichier « porte EXACTEMENT l'attendu ». Lire le compte de suppressions de la sortie.

---

### Task 6 : `GET /api/pm/index` — service, route, schémas, PyYAML, smoke CI

**Files:**
- Create: `backend/app/services/index_service.py`
- Modify: `backend/app/routes/pm.py`, `backend/app/schemas.py` (après `PilotageV1`), `backend/requirements.txt`, `.github/workflows/ci.yml` (étape « Run docker compose and smoke test »), `tests/test_backend.py`, `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `index_artefacts.indexer`, `read_dates` ; `pilotage.racine_depot` ; `pilotage_service._servable`, `_resume`, `_texte_servable`, `_EnveloppeRefusee`.
- Produces: `index_service.get_index(ttl_s: float = 60.0) -> dict`, `index_service._vider_cache()` ; modèles `IndexV1`, `IndexFamille`, `IndexIllisible`, `IndexArtefact`, `IndexLien`, `IndexDates`, `IndexHorsFamilles` ; route `GET /api/pm/index` (`response_model=IndexV1`, `response_model_by_alias=True`) ; type TS `components["schemas"]["IndexV1"]`.

- [ ] **Step 1 : écrire les tests backend qui échouent**

Ajouter à `tests/test_backend.py` :

```python
def test_index_repond_200_schema_index_v1_et_familles_servies() -> None:
    from backend.app.services import index_service as ix
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "index_v1" and isinstance(d["generated_at"], (int, float))
    assert d["familles"] is not None and d["artefacts"] is not None, d["aveugle"]
    assert not any(a.startswith("index:") for a in d["aveugle"]), d["aveugle"]
    rec = next(f for f in d["familles"] if f["nom"] == "record")
    assert rec["indexes"] > 300


def test_index_ne_lance_JAMAIS_git_dans_la_requete(monkeypatch) -> None:
    """D1 : git vit dans l'écrivain de DATES_GIT.json, jamais sur le chemin de la requête. Compteur (le filet du
    service avalerait une AssertionError — leçon du lot 1)."""
    from backend.app.services import index_service as ix
    from tools.pm import index_artefacts as IX
    appels = {"n": 0}

    def _interdit(*a, **k):
        appels["n"] += 1
        raise AssertionError("git appelé dans la requête")
    monkeypatch.setattr(IX, "calculer_dates_git", _interdit)
    monkeypatch.setattr(IX, "_git", _interdit)
    ix._vider_cache()
    assert client.get("/api/pm/index").status_code == 200
    assert appels["n"] == 0


def test_index_indexer_qui_leve_devient_une_ligne_index_jamais_un_500(monkeypatch) -> None:
    from backend.app.services import index_service as ix

    def _boum(*a, **k):
        raise RuntimeError("indexeur cassé")
    monkeypatch.setattr(ix.index_artefacts, "indexer", _boum)
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["aveugle"][0].startswith("index: RuntimeError") and d["familles"] is None and d["artefacts"] is None


def test_index_cache_sous_le_TTL(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    vrai, appels = ix.index_artefacts.indexer, {"n": 0}

    def _compte(*a, **k):
        appels["n"] += 1
        return vrai(*a, **k)
    monkeypatch.setattr(ix.index_artefacts, "indexer", _compte)
    ix._vider_cache()
    client.get("/api/pm/index")
    client.get("/api/pm/index")
    assert appels["n"] == 1


def test_index_bloc_de_type_etranger_devient_null_sans_500(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    vrai = ix.index_artefacts.indexer

    def _etranger(*a, **k):
        out = vrai(*a, **k)
        out["hors_familles"] = {"n": "beaucoup", "repertoires": {}}
        return out
    monkeypatch.setattr(ix.index_artefacts, "indexer", _etranger)
    ix._vider_cache()
    r = client.get("/api/pm/index")
    assert r.status_code == 200
    d = r.json()
    assert d["hors_familles"] is None and d["familles"] is not None
    assert any(a.startswith("hors_familles : bloc refusé") for a in d["aveugle"]), d["aveugle"]


def test_index_import_refuse_est_NOMME(monkeypatch) -> None:
    from backend.app.services import index_service as ix
    monkeypatch.setattr(ix, "_IMPORT_REFUSE", ImportError("No module named 'yaml'"))
    ix._vider_cache()
    d = client.get("/api/pm/index").json()
    assert d["aveugle"][0].startswith("index: ImportError") and "yaml" in d["aveugle"][0]
```

- [ ] **Step 2 : les lancer, ils échouent**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k index`
Expected: FAIL — 404 sur `/api/pm/index` ou `ModuleNotFoundError: backend.app.services.index_service`.

- [ ] **Step 3 : écrire les modèles, le service et la route**

Dans `backend/app/schemas.py`, après `PilotageV1` :

```python
class IndexIllisible(BaseModel):
    chemin: str
    raison: str


class IndexFamille(BaseModel):
    nom: str
    motif: str
    repertoire: str | None = None
    exclus: list[str]
    fichiers: int | None = None
    indexes: int | None = None
    illisibles: list[IndexIllisible] | None = None
    champs_introuvables: dict[str, dict[str, int]] | None = None
    format_declare: dict[str, int] | None = None


class IndexLien(BaseModel):
    rel: str
    cible: str


class IndexArtefact(BaseModel):
    famille: str
    chemin: str
    titre: str | None = None
    date_declaree: str | None = None
    date_source: str | None = None
    date_ajout_git: str | None = None
    etat: str | None = None
    etat_source: str | None = None
    regime: bool | None = None
    scelle: bool | None = None
    gate: str | None = None
    liens: list[IndexLien] = []


class IndexDates(BaseModel):
    generated_at: float
    age_s: float
    head: str | None = None
    historique: str


class IndexHorsFamilles(BaseModel):
    n: int
    repertoires: dict[str, int]


class IndexV1(BaseModel):
    """Enveloppe de `index_v1` (spec 2026-09-26 §3.1, §9). Chaque bloc est validé par le service DANS son filet :
    un bloc refusé devient `null` plus une ligne `aveugle` qui le nomme, jamais un 500."""
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias="schema")
    generated_at: float
    repo_root: str | None = None
    aveugle: list[str]
    dates: IndexDates | None = None
    familles: list[IndexFamille] | None = None
    hors_familles: IndexHorsFamilles | None = None
    artefacts: list[IndexArtefact] | None = None
```

`backend/app/services/index_service.py` :

```python
"""Service de l'index des artefacts (P2.87) : en mémoire, SANS écrire un fichier, SANS lancer git.

Les dates d'entrée dans le dépôt sont LUES dans `DATES_GIT.json` (écrit par le tick PM, là où l'historique est
complet) avec leur âge — l'image docker n'a ni git ni `.git` (spec §9, D1). Même filet que `pilotage_service` :
import gardé et NOMMÉ, chaque bloc validé contre le modèle de la route AVANT elle, mode dégradé servable.
"""
from __future__ import annotations

import time
from typing import Any

from pydantic import TypeAdapter

try:
    from tools.pm import index_artefacts, pilotage
    _IMPORT_REFUSE: Exception | None = None
except Exception as _exc:                                  # noqa: BLE001 — NOMMÉ par get_index, jamais avalé
    index_artefacts = None
    pilotage = None
    _IMPORT_REFUSE = _exc

from ..schemas import IndexV1
from .pilotage_service import _EnveloppeRefusee, _resume, _servable, _texte_servable

_SCHEMA = "index_v1"
_TTL_DEFAUT = 60.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}
_BLOCS = ("dates", "familles", "hors_familles", "artefacts")
_ADAPTATEURS = {cle: TypeAdapter(IndexV1.model_fields[cle].annotation) for cle in _BLOCS}
_ENVELOPPE = TypeAdapter(IndexV1)


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def _blocs_servables(out: dict) -> dict:
    out = dict(out)
    aveugle = list(out.get("aveugle") or [])
    for cle in _BLOCS:
        if out.get(cle) is None:
            continue
        try:
            _servable(_ADAPTATEURS[cle], out[cle], cle)
        except Exception as exc:                           # noqa: BLE001 — refus NOMMÉ, jamais un 500
            aveugle.append(f"{cle} : bloc refusé par le modèle de la route ({_resume(exc)}) -- servi à null, les "
                           "autres blocs restent servis")
            out[cle] = None
    out["aveugle"] = [_texte_servable(a) if isinstance(a, str) else a for a in aveugle]
    return out


def get_index(ttl_s: float = _TTL_DEFAUT) -> dict:
    now = time.time()
    if _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    racine = None
    try:
        if _IMPORT_REFUSE is not None:
            raise ImportError(f"tools.pm.index_artefacts indisponible dans ce processus "
                              f"({type(_IMPORT_REFUSE).__name__}: {_IMPORT_REFUSE}) -- volume ./tools absent du "
                              "conteneur, ou dépendance absente de backend/requirements.txt")
        racine = pilotage.racine_depot()
        out = index_artefacts.indexer(racine, index_artefacts.read_dates(racine), now)
        out = _blocs_servables(out)
        try:
            _servable(_ENVELOPPE, out)
        except Exception as exc:                           # noqa: BLE001 — NOMMÉ par le mode dégradé
            raise _EnveloppeRefusee(_resume(exc)) from exc
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        texte = (f"index: enveloppe refusée par le modèle de la route ({exc})" if isinstance(exc, _EnveloppeRefusee)
                 else f"index: {type(exc).__name__}: {exc}")
        out = {"schema": _SCHEMA, "generated_at": now,
               "repo_root": None if racine is None else _texte_servable(str(racine).replace("\\", "/")),
               "aveugle": [_texte_servable(texte)],
               "dates": None, "familles": None, "hors_familles": None, "artefacts": None}
    _cache["at"], _cache["valeur"] = now, out
    return out
```

Dans `backend/app/routes/pm.py` :

```python
from ..schemas import IndexV1, PilotageV1
from ..services.index_service import get_index
...


@router.get("/index", response_model=IndexV1, response_model_by_alias=True)
def index() -> dict:
    return get_index()
```

Dans `backend/requirements.txt`, ajouter une ligne `pyyaml`.

- [ ] **Step 4 : lancer les tests backend**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py -q -p no:cacheprovider -k "index or pilotage"`
Expected: PASS (6 cas `index` + ceux du pilotage).

- [ ] **Step 5 : régénérer les types API — dans CE commit, en LF**

```bash
python -m tools.jobs.doctor
PYTHONPATH=. python tools/dump_openapi.py
npm --prefix frontend run gen:api
python -c "import pathlib; [p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n')) for p in map(pathlib.Path, ['frontend/openapi.json', 'frontend/src/api/schema.ts'])]"
git diff --stat -- frontend/openapi.json frontend/src/api/schema.ts
```

Expected: les deux fichiers changent (`IndexV1` et la route y apparaissent), sans fin de ligne CRLF.

- [ ] **Step 6 : le smoke docker de la CI**

Dans `.github/workflows/ci.yml`, étape « Run docker compose and smoke test », après la ligne `python3 -c "…pilotage…"`,
ajouter :

```yaml
          # Index des artefacts (P2.87) : même marqueur de mode dégradé, et les familles doivent être SERVIES (une
          # image sans pyyaml rendrait tous les frontmatters illisibles). La ligne « dates : … » est ATTENDUE : ni git
          # ni DATES_GIT.json dans l'image.
          curl --fail -s http://localhost:8000/api/pm/index -o index_smoke.json || { docker compose logs backend; exit 1; }
          python3 -c "import json, sys; d = json.load(open('index_smoke.json', encoding='utf-8')); av = d.get('aveugle') or []; bad = [a for a in av if a.startswith('index:')]; fam = d.get('familles') or []; rec = [f for f in fam if f.get('nom') == 'record']; ill = [i for f in fam for i in (f.get('illisibles') or []) if i.get('raison') == 'pyyaml_absent']; print('index :', d.get('schema'), '|', len(av), 'ligne(s) aveugle |', rec[0].get('indexes') if rec else None, 'records'); [print('  DEGRADE :', a) for a in bad]; sys.exit(1 if bad or d.get('schema') != 'index_v1' or not rec or not rec[0].get('indexes') or ill else 0)" || { docker compose logs backend; exit 1; }
```

- [ ] **Step 7 : reproduire l'IMAGE sans docker (leçon `b7a06d87`, D2)**

Dans le scratchpad : un dossier `image/` = `backend/requirements.txt` + `backend/app` + `*.py` de la racine (ce que
copie `Dockerfile.backend`) + les volumes du compose (`results/`, `data/`, `src/`, `tools/`, `docs/`) copiés par
`git archive` ; un venv NEUF avec `pip install -r requirements.txt` SEULEMENT ; puis, depuis `image/` :

```bash
<venv>/python -c "from backend.app.services.index_service import get_index; d = get_index(); print(d['schema'], [a for a in d['aveugle'] if a.startswith('index:')], sum(len([i for i in (f['illisibles'] or []) if i['raison'] == 'pyyaml_absent']) for f in d['familles']), next(f['indexes'] for f in d['familles'] if f['nom'] == 'record'))"
```

Expected: `index_v1 [] 0 <plus de 300>` — aucun mode dégradé, aucun `pyyaml_absent`, les records indexés. Refaire
l'exercice SANS `pyyaml` dans le venv : attendu `index_v1 [] <n > 300> …` avec la ligne `frontmatter : PyYAML absent`
— c'est le contrôle positif de la garde.

- [ ] **Step 8 : suites Windows et WSL, revue opus, commit du pas 2**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_backend.py tests/sandbox/test_pm_index_artefacts.py -q -p no:cacheprovider` (Windows) puis la même chose sous WSL (recette `wsl-linux-repro`).
Puis revue adversariale opus du diff (filet, validation par bloc, image, smoke), traitement des constats, et
`commit-exact` sur : `backend/app/services/index_service.py`, `backend/app/routes/pm.py`, `backend/app/schemas.py`,
`backend/requirements.txt`, `.github/workflows/ci.yml`, `tests/test_backend.py`, `frontend/openapi.json`,
`frontend/src/api/schema.ts`. La porte de parité signalera `/api/pm/index` comme NON consommé jusqu'à la Task 7 :
le dire dans le message.

---

### Task 7 : l'onglet « Index » de la famille Pilotage

**Files:**
- Create: `frontend/src/lib/index.ts`, `frontend/src/lib/index.test.ts`, `frontend/src/components/pilotage/IndexView.tsx`, `frontend/src/components/pilotage/IndexView.test.tsx`, `frontend/src/components/pilotage/indexFixture.ts`
- Modify: `frontend/src/api/pm.ts`, `frontend/src/api/pm.test.ts`, `frontend/src/api/queryKeys.ts`, `frontend/src/api/queryKeys.test.ts`, `frontend/src/lib/polling.ts`, `frontend/src/lib/polling.test.ts`, `frontend/src/tabs.ts`, `frontend/src/tabs.test.tsx`, `frontend/src/App.tsx`, `frontend/src/components/pilotage/AveugleBanner.tsx` (+ son test)

**Interfaces:**
- Consumes: `components["schemas"]["IndexV1"]` (Task 6) ; `AveugleBanner`, `vscodeHref`, `formatAge`, `NON_MESURE` (lot 1).
- Produces: `fetchIndex(): Promise<IndexV1>` ; `queryKeys.pm.index` ; `INDEX_POLL` ; `totalIntrouvables(c: Record<string, number> | undefined): number` ; `detailRaisons(c): string` ; `filtrerArtefacts(arts, filtre): IndexArtefact[]` ; `LIMITE_AFFICHAGE = 300` ; composant `IndexView`.

- [ ] **Step 1 : écrire les tests de la couche pure et du client**

`frontend/src/lib/index.test.ts` :

```ts
import { describe, expect, test } from "vitest";
import { detailRaisons, filtrerArtefacts, LIMITE_AFFICHAGE, totalIntrouvables } from "./index";
import type { IndexArtefact } from "../api/pm";

const A = (o: Partial<IndexArtefact>): IndexArtefact => ({
  famille: "spec", chemin: "docs/x.md", titre: null, date_declaree: null, date_source: null, date_ajout_git: null,
  etat: null, etat_source: null, regime: null, scelle: null, gate: null, liens: [], ...o,
});

describe("comptes de champs introuvables", () => {
  test("total et détail par raison, dans l'ordre décroissant", () => {
    const c = { frontmatter_absent: 34, cle_absente: 2 };
    expect(totalIntrouvables(c)).toBe(36);
    expect(detailRaisons(c)).toBe("frontmatter_absent 34 · cle_absente 2");
  });
  test("aucun champ introuvable : 0 MESURÉ, détail vide", () => {
    expect(totalIntrouvables({})).toBe(0);
    expect(detailRaisons({})).toBe("");
  });
});

describe("filtrerArtefacts", () => {
  const arts = [A({ famille: "record", titre: "Perception", chemin: "docs/EDR/1.md", date_ajout_git: "2026-09-01" }),
    A({ famille: "spec", titre: null, chemin: "docs/superpowers/specs/2026-09-26-p.md" })];
  test("famille, texte (titre OU chemin), sans date d'ajout", () => {
    expect(filtrerArtefacts(arts, { famille: "record", texte: "", sansDate: false })).toHaveLength(1);
    expect(filtrerArtefacts(arts, { famille: "", texte: "2026-09-26", sansDate: false })[0].famille).toBe("spec");
    expect(filtrerArtefacts(arts, { famille: "", texte: "percep", sansDate: false })[0].famille).toBe("record");
    expect(filtrerArtefacts(arts, { famille: "", texte: "", sansDate: true })[0].famille).toBe("spec");
  });
  test("la limite d'affichage est un nombre déclaré", () => {
    expect(LIMITE_AFFICHAGE).toBe(300);
  });
});
```

Dans `frontend/src/api/pm.test.ts`, ajouter :

```ts
import { fetchIndex } from "./pm";

test("l'index appelle /api/pm/index", async () => {
  await fetchIndex();
  expect(mocked).toHaveBeenCalledWith("/api/pm/index");
});
```

Dans `queryKeys.test.ts` : `test("clé de l'index", () => { expect(queryKeys.pm.index).toEqual(["pm", "index"]); });`
Dans `polling.test.ts` : `test("INDEX_POLL : 60 s", () => { expect(INDEX_POLL).toEqual({ refetchInterval: 60_000, staleTime: 10_000, refetchIntervalInBackground: false }); });` (et ajouter `INDEX_POLL` à l'import).
Dans `tabs.test.tsx`, remplacer l'attendu de la famille Pilotage par `[["flotte","Flotte"],["roadmap","Roadmap"],["portes","Portes"],["index","Index"]]`.

- [ ] **Step 2 : les lancer, ils échouent**

Run: `npx --prefix frontend vitest run src/lib/index.test.ts src/api src/lib/polling.test.ts src/tabs.test.tsx` (depuis `frontend/` : `npx vitest run …`)
Expected: FAIL — module `./index` introuvable, `fetchIndex` non exporté.

- [ ] **Step 3 : écrire la couche pure, le client, la clé, le poll, l'onglet**

`frontend/src/lib/index.ts` :

```ts
import type { IndexArtefact } from "../api/pm";

/** Affichage borné et DIT : au-delà, la table écrit « n affichés sur m — affinez le filtre », jamais une coupe muette. */
export const LIMITE_AFFICHAGE = 300;

export function totalIntrouvables(c: Record<string, number> | null | undefined): number {
  return Object.values(c ?? {}).reduce((s, n) => s + n, 0);
}

export function detailRaisons(c: Record<string, number> | null | undefined): string {
  return Object.entries(c ?? {})
    .sort((a, b) => b[1] - a[1])
    .map(([r, n]) => `${r} ${n}`)
    .join(" · ");
}

export interface FiltreIndex {
  famille: string;
  texte: string;
  sansDate: boolean;
}

export function filtrerArtefacts(arts: IndexArtefact[], f: FiltreIndex): IndexArtefact[] {
  const t = f.texte.trim().toLowerCase();
  return arts.filter(
    (a) =>
      (!f.famille || a.famille === f.famille) &&
      (!t || a.chemin.toLowerCase().includes(t) || (a.titre ?? "").toLowerCase().includes(t)) &&
      (!f.sansDate || a.date_ajout_git === null),
  );
}
```

Dans `frontend/src/api/pm.ts`, ajouter :

```ts
export type IndexV1 = components["schemas"]["IndexV1"];
export type IndexFamille = components["schemas"]["IndexFamille"];
export type IndexArtefact = components["schemas"]["IndexArtefact"];

/** Chemin LITTÉRAL, premier argument direct d'`apiFetch` (porte de parité). Aucun recalcul côté serveur au-delà de
 *  la lecture des fichiers : git n'est jamais lancé dans la requête (spec P2.87 §9, D1). */
export function fetchIndex(): Promise<IndexV1> {
  return apiFetch<IndexV1>("/api/pm/index");
}
```

`queryKeys.ts` : dans `pm`, ajouter `index: ["pm", "index"] as const,`.
`polling.ts` : ajouter

```ts
/** Options react-query de l'index des artefacts : 60 s, le cache du backend (l'index relit ~770 fichiers). */
export const INDEX_POLL = {
  refetchInterval: 60_000,
  staleTime: 10_000,
  refetchIntervalInBackground: false,
} as const;
```

`tabs.ts` : ajouter `"index"` à la fin de `TAB_KEYS`, l'icône `Library` à l'import de `lucide-react`, et dans la
famille Pilotage, après Portes : `{ key: "index", label: "Index", icon: Library },`.
`App.tsx` : après le `lazy()` de `PilotagePortesView`,

```tsx
const IndexView = lazy(() => import("./components/pilotage/IndexView").then((m) => ({ default: m.IndexView })));
```

et, après `{tab === "portes" && <PilotagePortesView />}` : `{tab === "index" && <IndexView />}`.

`AveugleBanner.tsx` : le préfixe du mode dégradé devient un paramètre (le lot 1 ne connaissait que `pilotage:`) —
signature `AveugleBanner({ lignes, prefixeDegrade = "pilotage:", titreDegrade = "Pilotage en mode dégradé : les quatre
blocs sont servis à null" })`, et les deux `startsWith("pilotage:")` deviennent `startsWith(prefixeDegrade)`, le
`<strong>` du bloc d'alerte rend `{titreDegrade}`. Les trois vues du lot 1 ne passent rien (défauts inchangés). Ajouter
à `AveugleBanner.test.tsx` :

```tsx
test("préfixe de mode dégradé paramétré : une ligne « index: » est une ALERTE pour l'index", () => {
  render(<AveugleBanner lignes={["index: ImportError: yaml"]} prefixeDegrade="index:" titreDegrade="Index dégradé" />);
  expect(screen.getByRole("alert").textContent).toContain("Index dégradé");
  expect(screen.getByRole("alert").textContent).toContain("index: ImportError: yaml");
});
```

- [ ] **Step 4 : écrire les tests de la vue**

`frontend/src/components/pilotage/indexFixture.ts` :

```ts
import type { IndexV1 } from "../../api/pm";

/** Réponse index_v1 factice, TYPÉE contre le schéma généré (tsc rougit si le contrat change sous elle). */
export function indexFixture(over: Partial<IndexV1> = {}): IndexV1 {
  return {
    schema: "index_v1",
    generated_at: 1_790_430_000,
    repo_root: "C:/Users/robla/VScode_Project/AGAGI",
    aveugle: [],
    dates: { generated_at: 1_790_429_400, age_s: 600, head: "abc", historique: "complet" },
    familles: [
      {
        nom: "record", motif: "*.md", repertoire: "docs/EDR", exclus: ["README.md"], fichiers: 4, indexes: 2,
        illisibles: [{ chemin: "docs/EDR/003_c.md", raison: "frontmatter_yaml_invalide" }],
        champs_introuvables: { titre: { frontmatter_absent: 1 }, date_declaree: { frontmatter_absent: 2 },
          etat: { frontmatter_absent: 1 }, date_ajout_git: {}, liens: {} },
        format_declare: { date: 0, etat: 0, sujet: 0, liens: 0, fichiers: 2 },
      },
      {
        nom: "adr", motif: "*.md", repertoire: "docs/ADR", exclus: [], fichiers: null, indexes: null,
        illisibles: null, champs_introuvables: null, format_declare: null,
      },
    ],
    hors_familles: { n: 12, repertoires: { "docs/roadmap": 10, "docs/specs": 2 } },
    artefacts: [
      { famille: "record", chemin: "docs/EDR/001_a.md", titre: "Perception demandée", date_declaree: null,
        date_source: null, date_ajout_git: "2026-09-01", etat: "X_DEMANDED", etat_source: "verdict", regime: null,
        scelle: null, gate: "G1", liens: [{ rel: "tests", cible: "SDR-G1" }] },
      { famille: "record", chemin: "docs/EDR/002_b.md", titre: null, date_declaree: null, date_source: null,
        date_ajout_git: null, etat: null, etat_source: null, regime: null, scelle: null, gate: null, liens: [] },
    ],
    ...over,
  };
}
```

`frontend/src/components/pilotage/IndexView.test.tsx` :

```tsx
import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
}));
import { apiFetch, ApiError } from "../../api/client";
import { IndexView } from "./IndexView";
import { indexFixture } from "./indexFixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;
function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
beforeEach(() => mocked.mockResolvedValue(indexFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("table des familles : comptes, exclus, illisibles avec raison, champs introuvables par raison", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("4")).toBeTruthy();
  expect(within(rec).getByText("README.md")).toBeTruthy();
  expect(within(rec).getByText(/frontmatter_yaml_invalide/)).toBeTruthy();
  expect(within(rec).getAllByText("1 (frontmatter_absent 1)")).toHaveLength(2);   // titre ET état
  expect(within(rec).getByText("2 (frontmatter_absent 2)")).toBeTruthy();           // date déclarée
  expect(mocked).toHaveBeenCalledWith("/api/pm/index");
});

test("famille à répertoire absent : « inconnu », jamais 0", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const adr = within(t).getByText("adr").closest("tr")!;
  expect(within(adr).getAllByText("inconnu").length).toBeGreaterThan(0);
  expect(within(adr).queryByText("0")).toBeNull();
});

test("format déclaré : un compte par clé, sans seuil ni couleur", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("date 0 · etat 0 · sujet 0 · liens 0 sur 2")).toBeTruthy();
  expect(rec.querySelector(".badge")).toBeNull();
});

test("artefact sans titre : « sans titre », jamais le nom du fichier ; sans date d'ajout : dit", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Artefacts indexés" });
  const b = within(t).getByText("docs/EDR/002_b.md").closest("tr")!;
  expect(within(b).getByText("sans titre")).toBeTruthy();
  expect(within(b).getByText("sans date d'ajout")).toBeTruthy();
});

test("dates : âge et état de l'historique publiés ; instantané absent → dit, pas de date inventée", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText(/historique complet, instantané de 10 min/)).toBeTruthy();
  cleanup();
  const ligne = "dates : DATES_GIT.json introuvable à C:/x/data/pm/DATES_GIT.json -- écrivain jamais passé";
  mocked.mockResolvedValue(indexFixture({ dates: null, hors_familles: null, aveugle: [ligne] }));
  rendre(<IndexView />);
  expect(await screen.findByText(/Dates d'ajout indisponibles/)).toBeTruthy();
  expect(screen.getByText(/Fichiers hors familles : inconnus/)).toBeTruthy();
  expect(screen.getByRole("status").textContent).toContain(ligne);
});

test("hors familles : le compte et ses répertoires", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText("12 fichier(s) suivi(s) hors familles : docs/roadmap 10 · docs/specs 2")).toBeTruthy();
});

test("filtre de famille et de texte ; au-delà de la limite, la coupe est DITE", async () => {
  const beaucoup = Array.from({ length: 305 }, (_, i) => ({ ...indexFixture().artefacts![0], chemin: `docs/EDR/${i}.md` }));
  mocked.mockResolvedValue(indexFixture({ artefacts: beaucoup }));
  rendre(<IndexView />);
  expect(await screen.findByText("300 affiché(s) sur 305 — affinez le filtre")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Texte"), { target: { value: "docs/EDR/12" } });
  expect(screen.getByText(/affiché\(s\) sur 305$/)).toBeTruthy();
});

test("mode dégradé : alerte + Empty ; backend injoignable : ErrorState", async () => {
  mocked.mockResolvedValue(indexFixture({ aveugle: ["index: ImportError: No module named 'yaml'"], dates: null,
    familles: null, hors_familles: null, artefacts: null }));
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("index: ImportError");
  expect(screen.getByText(/^Familles indisponible — index: ImportError/)).toBeTruthy();
  cleanup();
  mocked.mockRejectedValue(new ApiError(0, "/api/pm/index", "Timeout après 10000 ms"));
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("Erreur de chargement");
});
```

- [ ] **Step 5 : écrire la vue**

`frontend/src/components/pilotage/IndexView.tsx` :

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchIndex, type IndexFamille } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { detailRaisons, filtrerArtefacts, LIMITE_AFFICHAGE, totalIntrouvables } from "../../lib/index";
import { formatAge, vscodeHref } from "../../lib/pilotage";
import { INDEX_POLL } from "../../lib/polling";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Field } from "../ui/Field";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { AveugleBanner } from "./AveugleBanner";

const CHAMPS = ["titre", "date_declaree", "etat", "date_ajout_git"] as const;
const LIBELLE: Record<(typeof CHAMPS)[number], string> = {
  titre: "Titre introuvable",
  date_declaree: "Date déclarée introuvable",
  etat: "État introuvable",
  date_ajout_git: "Date d'ajout introuvable",
};
const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

function Introuvable({ c }: { c: Record<string, number> | undefined }) {
  const n = totalIntrouvables(c);
  return <>{n ? `${n} (${detailRaisons(c)})` : "0"}</>;
}

function LigneFamille({ f }: { f: IndexFamille }) {
  const inconnu = f.fichiers == null;
  return (
    <tr>
      <td>{f.nom}</td>
      <td>
        <code>
          {f.repertoire}/{f.motif}
        </code>
      </td>
      <td>{inconnu ? <Dim>inconnu</Dim> : f.fichiers}</td>
      <td>{inconnu ? <Dim>inconnu</Dim> : f.indexes}</td>
      <td>{f.exclus.length ? f.exclus.join(", ") : <Dim>aucun</Dim>}</td>
      <td>
        {f.illisibles == null ? (
          <Dim>inconnu</Dim>
        ) : f.illisibles.length ? (
          <ul className="pilotage-chemins">
            {f.illisibles.map((i) => (
              <li key={i.chemin}>
                {i.chemin} <span className="text-dim">({i.raison})</span>
              </li>
            ))}
          </ul>
        ) : (
          "0"
        )}
      </td>
      {CHAMPS.map((c) => (
        <td key={c}>{f.champs_introuvables == null ? <Dim>inconnu</Dim> : <Introuvable c={f.champs_introuvables[c]} />}</td>
      ))}
      <td>
        {f.format_declare == null ? (
          <Dim>inconnu</Dim>
        ) : (
          `date ${f.format_declare.date} · etat ${f.format_declare.etat} · sujet ${f.format_declare.sujet} · liens ${f.format_declare.liens} sur ${f.format_declare.fichiers}`
        )}
      </td>
    </tr>
  );
}

/** Onglet Index (P2.87) : les familles d'artefacts du dépôt et ce que l'index n'a PAS su lire, LUS de
 *  `GET /api/pm/index`. Aucun champ inventé : « sans titre », « sans date d'ajout », « inconnu » disent l'absence. */
export function IndexView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.index,
    queryFn: () => fetchIndex(),
    ...INDEX_POLL,
  });
  const [famille, setFamille] = useState("");
  const [texte, setTexte] = useState("");
  const [sansDate, setSansDate] = useState(false);

  if (isLoading) return <Loading label="Chargement de l'index…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — index inconnu." />;

  const degrade = data.aveugle.filter((a) => a.startsWith("index:"));
  const raisonDegrade = degrade.length ? ` — ${degrade.join(" · ")}` : "";
  const vus = data.artefacts ? filtrerArtefacts(data.artefacts, { famille, texte, sansDate }) : [];
  const affiches = vus.slice(0, LIMITE_AFFICHAGE);
  return (
    <div className="pilotage-view">
      <h2>Index des artefacts</h2>
      <p className="text-dim">
        Relu depuis les fichiers du dépôt à chaque sondage (60 s) ; les dates d'ajout viennent de DATES_GIT.json, écrit
        par le tick PM là où l'historique git est complet.{" "}
        {data.dates
          ? `Dates : historique ${data.dates.historique}, instantané de ${formatAge(data.dates.age_s)}.`
          : "Dates d'ajout indisponibles (voir les lignes d'aveuglement)."}
      </p>
      <AveugleBanner
        lignes={data.aveugle}
        prefixeDegrade="index:"
        titreDegrade="Index en mode dégradé : familles et artefacts servis à null"
      />
      {!data.familles ? (
        <Empty message={`Familles indisponible${raisonDegrade}`} />
      ) : (
        <Panel className="mb-4">
          <div className="pilotage-defilement">
            <table className="runs-table" aria-label="Familles d'artefacts">
              <thead>
                <tr>
                  <th>Famille</th>
                  <th>Motif</th>
                  <th>Fichiers</th>
                  <th>Indexés</th>
                  <th>Exclus</th>
                  <th>Illisibles</th>
                  {CHAMPS.map((c) => (
                    <th key={c}>{LIBELLE[c]}</th>
                  ))}
                  <th>Format déclaré (par clé)</th>
                </tr>
              </thead>
              <tbody>
                {data.familles.map((f) => (
                  <LigneFamille key={f.nom} f={f} />
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      <p>
        {data.hors_familles
          ? `${data.hors_familles.n} fichier(s) suivi(s) hors familles : ${detailRaisons(data.hors_familles.repertoires)}`
          : "Fichiers hors familles : inconnus (pas d'instantané git complet)."}
      </p>
      {!data.artefacts ? (
        <Empty message={`Artefacts indisponible${raisonDegrade}`} />
      ) : (
        <>
          <div className="row mb-4">
            <Field label="Famille">
              <select value={famille} onChange={(e) => setFamille(e.target.value)}>
                <option value="">toutes</option>
                {(data.familles ?? []).map((f) => (
                  <option key={f.nom} value={f.nom}>
                    {f.nom}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Texte">
              <input value={texte} onChange={(e) => setTexte(e.target.value)} placeholder="titre ou chemin" />
            </Field>
            <label className="checkbox-inline">
              <input type="checkbox" checked={sansDate} onChange={(e) => setSansDate(e.target.checked)} /> sans date
              d'ajout
            </label>
            <span className="text-dim">
              {affiches.length < vus.length
                ? `${affiches.length} affiché(s) sur ${vus.length} — affinez le filtre`
                : `${vus.length} affiché(s) sur ${data.artefacts.length}`}
            </span>
          </div>
          <Panel>
            <div className="pilotage-defilement">
              <table className="runs-table" aria-label="Artefacts indexés">
                <thead>
                  <tr>
                    <th>Famille</th>
                    <th>Titre</th>
                    <th>Chemin</th>
                    <th>Date déclarée</th>
                    <th>Date d'ajout</th>
                    <th>État</th>
                  </tr>
                </thead>
                <tbody>
                  {affiches.map((a) => {
                    const href = vscodeHref(data.repo_root, a.chemin);
                    return (
                      <tr key={a.chemin}>
                        <td>{a.famille}</td>
                        <td>{a.titre ?? <Dim>sans titre</Dim>}</td>
                        <td>
                          {href ? (
                            <a href={href} aria-label={`ouvrir ${a.chemin} dans VS Code`}>
                              {a.chemin}
                            </a>
                          ) : (
                            a.chemin
                          )}
                        </td>
                        <td className="pilotage-nowrap">
                          {a.date_declaree ? `${a.date_declaree} (${a.date_source})` : <Dim>non déclarée</Dim>}
                        </td>
                        <td className="pilotage-nowrap">{a.date_ajout_git ?? <Dim>sans date d'ajout</Dim>}</td>
                        <td>{a.etat ? `${a.etat} (${a.etat_source})` : <Dim>non déclaré</Dim>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 6 : lancer vitest, build, prettier, parité**

Run (depuis `frontend/`) : `npx vitest run` puis `npm run build` puis `npx prettier --print-width 120 --check src/components/pilotage src/lib/index.ts src/lib/index.test.ts`
Run (racine) : `PYTHONIOENCODING=utf-8 python -c "from pathlib import Path; import tools.parity_check as pc; print('/api/pm/index' in pc.scan_frontend_consumers(Path('.').resolve()))"`
Expected: tous verts ; `True` pour la parité.

- [ ] **Step 7 : mutants des règles de la vue (témoins discriminants)**

Sur le modèle du lot 1 (script du scratchpad : mutation en place, restauration octet pour octet vérifiée) :
« inconnu » rendu `0` pour une famille à `fichiers null` ; `sans titre` remplacé par le nom du fichier ; coupe à 300
sans le texte « affinez le filtre » ; `format_declare` rendu en badge ; `data.dates` ignoré (âge non publié) ;
`hors_familles null` rendu « 0 fichier(s) ». Chaque mutant doit faire rougir au moins un témoin.

- [ ] **Step 8 : contrôle visuel unique, puis commit du pas 3 et fermeture de P2.87**

Un seul contrôle visuel sur la sortie RÉELLE de `python -m tools.pm.index_artefacts --json` servie par un faux
backend statique (le vrai lance une simulation au démarrage), clair et sombre, page confinée (aucun défilement
horizontal de la page). Puis marquer P2.87 CLOSE dans le backlog (« ✅ CLOSE le <date> », avec ce qui est livré et
le commit), vérifier la porte 4, et `commit-exact` sur les fichiers de la Task 7 + le backlog.

---

## Ce que ce plan NE fait pas

La famille Science (P2.84 : Pipeline, Taxonomie, Trouvailles) — plan 2, écrit après la livraison de celui-ci ; la
publication de l'index dans la page artefact claude.ai ; une porte sur le format déclaré ; P2.135 (la porte 3 qui rend
un vert sur une racine vide), attribuée par Master 2.

## Auto-revue

- **Couverture de la spec** : §3.1 lecteurs, vocabulaire, parité, types → Tasks 2-3 ; §9 D1 (écrivain, lecture avec
  âge, raisons) → Tasks 3-4 ; D2 (PyYAML, image) → Task 6 Steps 3, 6, 7 ; D3 (onglet Index dans Pilotage) → Task 7 ;
  §3.4 backend (filet, préfixes, cache, smoke) → Task 6 ; §7 cas de calibration → Tasks 1-4, 6, 7 ; porte 2 (gel) →
  Task 5 ; porte 12 → Task 2 (`_resultats` par `src/paths.py`) ; §6 coût → Task 5 Step 3 ; §11 clause → Task 5 Step 4
  et Task 7 Step 8.
- **Précisions ajoutées à la spec par le plan** (à reporter au §9 dans le commit du pas 1) : la raison
  `lecture_impossible` (fichier supprimé entre le glob et la lecture) ; le bloc `dates` de `index_v1`
  (`generated_at`, `age_s`, `head`, `historique`) qui porte l'âge de l'instantané ; `tools/frontmatter.py` comme
  lieu de l'extraction partagée (import PyYAML paresseux), au lieu d'une fonction de `consolidate_records`.
- **Types** : `lire_fichier` rend un 4-uplet partout ; `read_dates` rend `{"doc", "chemin", "raison"}` consommé tel
  quel par `indexer` et `_lignes_dates` ; `IndexArtefact` (Python) et `IndexArtefact` (TS généré) ont les mêmes 12
  champs.
- **Composant du lot 1 modifié** : `AveugleBanner` gagne deux paramètres optionnels (préfixe et titre du mode
  dégradé), défauts identiques au comportement du lot 1 ; ses trois témoins existants doivent rester verts.
