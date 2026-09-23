# Plan 3/3 — Stratège : événements détectés par le tick, lentilles figées, témoin périmé, workflow, proposition

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rejouer la procédure du 2026-09-14 (lentilles → réfuteurs → juges → synthèse → décision de robla) comme un workflow à prompts FIGÉS, déclenché par des ÉVÉNEMENTS que le tick PM détecte, avec un candidat-témoin périmé que les réfuteurs doivent tuer, et une lentille « Organisation » qui relit `ROLES.md` aux occasions prévues par la spec.

**Architecture:** `tools/pm/strategist_events.py` compare un état persisté (`data/pm/strategist_state.json`) à l'état courant (records, entrées CLOS, rétractations, `-bis`, nuls) et rend les événements + le mode (`delta` / `full`) ; le tick l'appelle et l'écrit dans le digest ; la session PM lance `.claude/workflows/strategist.js` avec les seuls arguments (`mode`, `events`, `today`, `temoin`) ; les textes des lentilles, réfuteurs et juges vivent dans `docs/REF/REF-STRATEGE.md` ; la sortie s'écrit dans `docs/roadmap/STRATEGE_PROPOSITION.md` (writer PM) ; robla tranche ; le PM écrit le bloc 🧭 en commit path-scoped.

**Tech Stack:** Python 3 stdlib, pytest, Workflow (JavaScript), `SendMessage`/`ScheduleWakeup` dans le skill `/pm`.

**Spec:** `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` (§2.2, §3.4, §6.3, §6.4, §7 étape 6). **Prérequis** : plan 1 livré (tick, `paths.pm_dir`, `ROLES.md`).

## Global Constraints

- Mêmes contraintes que le plan 1 (porte 12 via `src.paths`, porte 14 `None`, pas de `def run(` module-level, hooks sans backtick, commits path-scoped, accord de robla avant le premier commit).
- **Le PM ne rédige aucun prompt** : le JS ne porte que des identifiants (`L1`…`L8`, `R1`…`R3`, `J1`…`J3`) ; les textes sont dans le REF, versionnés. Changer un prompt = commit path-scoped décidé par robla, et le témoin doit encore être tué.
- **Le bloc 🧭 de `PRIORITES_ET_DETTES.md` ne bouge qu'après l'accord explicite de robla dans la conversation**, jamais depuis le workflow.
- Le témoin périmé est un candidat que les records ont DÉJÀ tranché ; s'il survit à la réfutation, la passe est **NULLE** et rien ne s'écrit.

---

## Structure des fichiers

| fichier | responsabilité |
| --- | --- |
| `tools/pm/strategist_events.py` | état persisté, détection d'événements, choix `delta`/`full`, plancher 30 j / 20 records |
| `tools/pm/tick.py` (modifié) | appelle la détection, l'écrit dans le digest |
| `docs/REF/REF-STRATEGE.md` | lentilles L1-L8 (L8 = Organisation), réfuteurs R1-R3, juges J1-J3, forme de la synthèse, témoin |
| `tools/strategist_temoins.json` | le candidat PÉRIMÉ et la raison connue (`attendu`) |
| `.claude/workflows/strategist.js` | phases candidats → fusion → réfutation → juges → synthèse ; contrôle du témoin ; écrit la proposition |
| `docs/roadmap/STRATEGE_PROPOSITION.md` | proposition courante (writer PM), en-tête permanent + dernière passe |
| `.claude/skills/pm/SKILL.md` (modifié) | étape 4 : quand et comment lancer le stratège, présenter à robla, écrire 🧭 |
| `docs/roadmap/ROLES.md` (modifié) | ligne Stratège : instrument livré, compteurs |
| `tests/sandbox/test_strategist_events.py`, `tests/sandbox/test_strategist_temoins.py` | témoins |

---

### Task 1 : `tools/pm/strategist_events.py` — événements et mode

**Files:**
- Create: `tools/pm/strategist_events.py`
- Modify: `tools/pm/tick.py` (après le calcul de `counts`, avant `print(digest(...))`) ; `digest` gagne un paramètre `evenements`
- Test: `tests/sandbox/test_strategist_events.py`

**Interfaces:**
- Produces:
  - `etat_courant(repo_root) -> dict` — `{"records": sorted(docs/EDR/*.md), "clos": sorted(P-items marqués clos), "retractes": sorted(records contenant "RÉTRACTÉ" ou "retracted_by:"), "bis": sorted(docs/preregistrations/*-bis*.json), "nuls": sorted(results/*.json dont "verdict" contient NUL|INDETERMINE|INCONCLUSIVE)}` ; une source illisible → `None` pour cette clé
  - `detecter(avant, apres) -> list[dict]` — `{"type": "record"|"clos"|"retractation"|"bis"|"nul", "cible": str}` ; une clé `None` d'un côté ne produit rien (aveugle, pas d'événement fabriqué)
  - `mode(evenements, dernier_full_ts, n_records_depuis_full, now, plancher_jours=30, plancher_records=20) -> "aucun"|"delta"|"full"` — `full` si rétractation, ou ≥ 20 records depuis le dernier `full`, ou > 30 j ; `delta` si ≥ 1 événement ; sinon `aucun`
  - `charger_etat(path) -> dict | None`, `ecrire_etat(path, etat) -> None`
  - `detecter_et_persister(repo_root, now, path=None) -> {"evenements", "mode", "n_records_depuis_full", "jours_depuis_full"}` — utilisé par le tick ; premier appel (pas d'état) : persiste et rend `mode: "aucun"` avec `evenements: []` (un premier tick ne déclenche rien : on ne fabrique pas 262 événements)
  - Format de l'état : `{"ts": float, "etat": {...}, "dernier_full_ts": float|None, "records_depuis_full": int}`

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_strategist_events.py` :

```python
"""Evenements du stratege : detectes par DIFF d'etats, jamais fabriques ; un premier tick ne declenche rien."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import strategist_events as SE  # noqa: E402

T0 = 1_800_000_000.0
J = 86400.0


def _etat(**kw):
    e = {"records": ["docs/EDR/A.md"], "clos": ["P2.1"], "retractes": [], "bis": [], "nuls": []}
    e.update(kw)
    return e


def test_detecter_rend_un_evenement_par_nouveaute_et_rien_sur_un_etat_identique():
    assert SE.detecter(_etat(), _etat()) == []
    ev = SE.detecter(_etat(), _etat(records=["docs/EDR/A.md", "docs/EDR/B.md"], clos=["P2.1", "P4.9"],
                                   retractes=["docs/EDR/A.md"], bis=["docs/preregistrations/X-bis.json"], nuls=["results/n.json"]))
    assert sorted((e["type"], e["cible"]) for e in ev) == [("bis", "docs/preregistrations/X-bis.json"), ("clos", "P4.9"),
                                                          ("nul", "results/n.json"), ("record", "docs/EDR/B.md"),
                                                          ("retractation", "docs/EDR/A.md")]


def test_une_source_AVEUGLE_d_un_cote_ne_fabrique_aucun_evenement():
    assert SE.detecter(_etat(records=None), _etat(records=["docs/EDR/A.md", "docs/EDR/B.md"])) == []
    assert SE.detecter(_etat(), _etat(records=None)) == []


def test_mode_delta_full_aucun():
    assert SE.mode([], T0 - J, 0, T0) == "aucun"
    assert SE.mode([{"type": "record", "cible": "x"}], T0 - J, 1, T0) == "delta"
    assert SE.mode([{"type": "retractation", "cible": "x"}], T0 - J, 1, T0) == "full"
    assert SE.mode([{"type": "record", "cible": "x"}], T0 - J, 20, T0) == "full"
    assert SE.mode([], T0 - 31 * J, 0, T0) == "full"
    assert SE.mode([], None, 0, T0) == "full"                         # jamais de full : le plancher est atteint


def test_etat_courant_lit_records_clos_retractes_bis_nuls(tmp_path):
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    (tmp_path / "docs" / "EDR" / "A.md").write_text("---\nid: EDR-A\nretracted_by: [EDR-B]\n---\n", encoding="utf-8")
    (tmp_path / "docs" / "EDR" / "B.md").write_text("verdict ⛔ RÉTRACTÉ\n", encoding="utf-8")
    (tmp_path / "docs" / "roadmap").mkdir()
    (tmp_path / "docs" / "roadmap" / "PRIORITES_ET_DETTES.md").write_text(
        "**P2.1 — ✅ CLOSE le 2026-09-16 — x.**\nQuoi.\n\n**P2.2 — OUVERTE — y.**\nQuoi.\n", encoding="utf-8")
    (tmp_path / "docs" / "preregistrations").mkdir()
    (tmp_path / "docs" / "preregistrations" / "R-bis.json").write_text("{}", encoding="utf-8")
    (tmp_path / "docs" / "preregistrations" / "R.json").write_text("{}", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "n.json").write_text(json.dumps({"verdict": "INCONCLUSIVE_REFERENCE_COLLAPSED"}), encoding="utf-8")
    (tmp_path / "results" / "ok.json").write_text(json.dumps({"verdict": "LEARNED"}), encoding="utf-8")
    e = SE.etat_courant(str(tmp_path))
    assert e["records"] == ["docs/EDR/A.md", "docs/EDR/B.md"] and e["clos"] == ["P2.1"]
    assert e["retractes"] == ["docs/EDR/A.md", "docs/EDR/B.md"] and e["bis"] == ["docs/preregistrations/R-bis.json"]
    assert e["nuls"] == ["results/n.json"]


def test_etat_courant_sans_repertoires_rend_None_par_cle(tmp_path):
    e = SE.etat_courant(str(tmp_path))
    assert e == {"records": None, "clos": None, "retractes": None, "bis": None, "nuls": None}


def test_detecter_et_persister_premier_tick_ne_declenche_rien_puis_detecte(tmp_path, monkeypatch):
    p = str(tmp_path / "state.json")
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    (tmp_path / "docs" / "EDR" / "A.md").write_text("x", encoding="utf-8")
    r = SE.detecter_et_persister(str(tmp_path), T0, path=p)
    assert r["mode"] == "aucun" and r["evenements"] == []
    (tmp_path / "docs" / "EDR" / "B.md").write_text("y", encoding="utf-8")
    r2 = SE.detecter_et_persister(str(tmp_path), T0 + 60, path=p)
    assert r2["evenements"] == [{"type": "record", "cible": "docs/EDR/B.md"}] and r2["mode"] == "delta"
    assert r2["n_records_depuis_full"] == 1
    st = json.loads(open(p, encoding="utf-8").read())
    assert st["records_depuis_full"] == 1 and st["dernier_full_ts"] == T0       # le premier tick vaut un full (point zéro)
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_strategist_events.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3 : implémenter**

`tools/pm/strategist_events.py` :

```python
"""Événements qui déclenchent le stratège (spec §2.2, §6.3) — détectés par DIFF entre un état persisté et l'état courant.
Un premier tick sans état persiste et ne déclenche RIEN (on ne fabrique pas 262 événements « nouveau record ») ; il
compte comme le point zéro d'un `full`. Une source illisible rend None et ne produit aucun événement (aveugle ≠ vide)."""
import glob
import json
import os
import re
import time

from src import paths

PLANCHER_JOURS = 30
PLANCHER_RECORDS = 20
_RETRACTE = re.compile(r"RÉTRACTÉ|RETRACTE|retracted_by:")
_NUL = re.compile(r"NUL|INDETERMIN|INCONCLUSIVE|CONTAMIN", re.I)


def _rel(root, p):
    return os.path.relpath(p, root).replace("\\", "/")


def _records(root):
    d = os.path.join(root, "docs", "EDR")
    if not os.path.isdir(d):
        return None, None
    fichiers = sorted(_rel(root, p) for p in glob.glob(os.path.join(d, "*.md")))
    retractes = []
    for f in fichiers:
        try:
            with open(os.path.join(root, f), encoding="utf-8") as fh:
                if _RETRACTE.search(fh.read()):
                    retractes.append(f)
        except (OSError, UnicodeDecodeError):
            continue
    return fichiers, retractes


def _clos(root):
    p = os.path.join(root, "docs", "roadmap", "PRIORITES_ET_DETTES.md")
    try:
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        return None
    from tools.check_backlog_freshness import _CLOSE_MARQUEURS, _TETE
    tete = re.compile(_TETE)
    out, courant, lignes_bloc = [], None, []

    def _flush():
        if courant and any(m in " ".join(lignes_bloc[:2]) for m in _CLOSE_MARQUEURS):
            out.append(courant)
    for ligne in txt.splitlines():
        m = tete.match(ligne.strip())
        if m:
            _flush()
            courant, lignes_bloc = m.group(1).split("/")[0].strip(), [ligne]
        elif courant:
            lignes_bloc.append(ligne)
    _flush()
    return sorted(set(out))


def _bis(root):
    d = os.path.join(root, "docs", "preregistrations")
    if not os.path.isdir(d):
        return None
    return sorted(_rel(root, p) for p in glob.glob(os.path.join(d, "*-bis*.json")))


def _nuls(root):
    d = os.path.join(root, "results")
    if not os.path.isdir(d):
        return None
    out = []
    for p in glob.glob(os.path.join(d, "*.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                v = json.load(fh).get("verdict")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(v, str) and _NUL.search(v):
            out.append(_rel(root, p))
    return sorted(out)


def etat_courant(repo_root):
    records, retractes = _records(repo_root)
    return {"records": records, "clos": _clos(repo_root), "retractes": retractes, "bis": _bis(repo_root), "nuls": _nuls(repo_root)}


_TYPES = (("records", "record"), ("clos", "clos"), ("retractes", "retractation"), ("bis", "bis"), ("nuls", "nul"))


def detecter(avant, apres):
    ev = []
    for cle, typ in _TYPES:
        a, b = avant.get(cle), apres.get(cle)
        if a is None or b is None:
            continue
        ev += [{"type": typ, "cible": c} for c in b if c not in set(a)]
    return ev


def mode(evenements, dernier_full_ts, n_records_depuis_full, now, plancher_jours=PLANCHER_JOURS, plancher_records=PLANCHER_RECORDS):
    if dernier_full_ts is None or (now - dernier_full_ts) > plancher_jours * 86400 or n_records_depuis_full >= plancher_records:
        return "full"
    if any(e["type"] == "retractation" for e in evenements):
        return "full"
    return "delta" if evenements else "aucun"


def charger_etat(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def ecrire_etat(path, etat):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(etat, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def detecter_et_persister(repo_root, now=None, path=None):
    now = time.time() if now is None else float(now)
    path = path or paths.pm_dir("strategist_state.json")
    courant = etat_courant(repo_root)
    st = charger_etat(path)
    if st is None:
        ecrire_etat(path, {"ts": now, "etat": courant, "dernier_full_ts": now, "records_depuis_full": 0})
        return {"evenements": [], "mode": "aucun", "n_records_depuis_full": 0, "jours_depuis_full": 0.0}
    ev = detecter(st["etat"], courant)
    n_rec = st.get("records_depuis_full", 0) + sum(1 for e in ev if e["type"] == "record")
    m = mode(ev, st.get("dernier_full_ts"), n_rec, now)
    ecrire_etat(path, {"ts": now, "etat": courant, "dernier_full_ts": st.get("dernier_full_ts"), "records_depuis_full": n_rec})
    jours = (now - st["dernier_full_ts"]) / 86400.0 if st.get("dernier_full_ts") else None
    return {"evenements": ev, "mode": m, "n_records_depuis_full": n_rec, "jours_depuis_full": jours}


def marquer_full(now=None, path=None):
    """À appeler par la session PM APRÈS une passe `full` acceptée par robla : remet les compteurs de plancher."""
    now = time.time() if now is None else float(now)
    path = path or paths.pm_dir("strategist_state.json")
    st = charger_etat(path) or {"ts": now, "etat": {}}
    st.update({"dernier_full_ts": now, "records_depuis_full": 0})
    ecrire_etat(path, st)
```

Dans `tools/pm/tick.py` : ajouter `from tools.pm.strategist_events import detecter_et_persister` ; dans `main`, après le calcul de `counts` : `ev = detecter_et_persister(args.repo_root, now)` ; changer la signature `digest(board, d, counts, evenements=None)` et ajouter, avant la ligne des compteurs :

```python
    if evenements and evenements["mode"] != "aucun":
        L_.append(f"[PM] STRATEGE mode={evenements['mode']} : {len(evenements['evenements'])} événement(s) — "
                  + "; ".join(f"{e['type']} {e['cible']}" for e in evenements["evenements"][:8])
                  + f" (records depuis full : {evenements['n_records_depuis_full']}, jours : {evenements['jours_depuis_full']})")
```

et `print(digest(board, d, counts, ev))`. Ajouter au test `test_pm_tick.py` un cas : `digest(board, d, counts, {"mode": "delta", "evenements": [{"type": "record", "cible": "docs/EDR/X.md"}], "n_records_depuis_full": 1, "jours_depuis_full": 2.0})` contient `STRATEGE mode=delta`.

- [ ] **Step 4 : lancer, vérifier le vert + portes**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_strategist_events.py tests/sandbox/test_pm_tick.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/strategist_events.py tools/pm/tick.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/pm/strategist_events.py`
Expected: PASS ; portes vertes.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/strategist_events.py tools/pm/tick.py tests/sandbox/test_strategist_events.py tests/sandbox/test_pm_tick.py
git commit -m "feat(stratege): tools/pm/strategist_events.py -- evenements par DIFF d etats persistes (record, clos, retractation, -bis, nul), mode delta/full (plancher 30 j / 20 records), premier tick = point zero ; integre au digest du tick" -- tools/pm/strategist_events.py tools/pm/tick.py tests/sandbox/test_strategist_events.py tests/sandbox/test_pm_tick.py
```

---

### Task 2 : `docs/REF/REF-STRATEGE.md` — lentilles, réfuteurs, juges, témoin figés

**Files:**
- Create: `docs/REF/REF-STRATEGE.md`, `tools/strategist_temoins.json`, `tools/strategist_temoins.py`
- Test: `tests/sandbox/test_strategist_temoins.py`

**Interfaces:**
- `strategist_temoins.charger() -> dict` — `{"candidat": str, "attendu": str (regex), "raison": str, "source": str}`
- `strategist_temoins.tue(votes) -> bool` — `votes` = liste de `{"refuted": bool, "reason": str}` ; tué ⟺ ≥ 2 réfutations ET au moins une raison matche `attendu` (le panel doit le tuer POUR LA BONNE RAISON, pas par hasard)
- Le REF porte les textes ; le JS porte les identifiants `L1`…`L8`, `R1`…`R3`, `J1`…`J3`.

- [ ] **Step 1 : écrire le test**

Créer `tests/sandbox/test_strategist_temoins.py` :

```python
"""Le temoin PERIME du stratege : un candidat que les records ont deja tranche, que les refuteurs doivent tuer pour
la bonne raison — sinon la passe est NULLE."""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import strategist_temoins as ST  # noqa: E402


def test_le_temoin_est_charge_et_sa_regex_compile():
    t = ST.charger()
    assert t["candidat"] and t["raison"] and t["source"].startswith("docs/")
    re.compile(t["attendu"])
    assert os.path.exists(os.path.join(ST._ROOT, t["source"])), "la source qui tranche le témoin doit exister"


def test_tue_exige_deux_refutations_ET_la_bonne_raison():
    t = {"attendu": "(WARM-00[13]|réactive|reactive)"}
    assert ST.tue(t, [{"refuted": True, "reason": "déjà exécuté : WARM-003 DAgger"}, {"refuted": True, "reason": "coût"},
                      {"refuted": False, "reason": "valeur"}]) is True
    assert ST.tue(t, [{"refuted": True, "reason": "coût"}, {"refuted": True, "reason": "doublon"}, {"refuted": False, "reason": ""}]) is False
    assert ST.tue(t, [{"refuted": True, "reason": "WARM-001 l'a fait"}, {"refuted": False, "reason": ""}, {"refuted": False, "reason": ""}]) is False


def test_le_REF_du_stratege_porte_les_huit_lentilles_trois_refuteurs_trois_juges():
    with open(os.path.join(ST._ROOT, "docs", "REF", "REF-STRATEGE.md"), encoding="utf-8") as fh:
        txt = fh.read()
    for ident in [f"L{i}" for i in range(1, 9)] + ["R1", "R2", "R3", "J1", "J2", "J3"]:
        assert re.search(rf"^\| \*\*{ident}\*\* \|", txt, re.M), f"{ident} absent du REF"
    assert txt.startswith("---\nid: REF-STRATEGE\n")
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_strategist_temoins.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3 : écrire le témoin, son module, le REF**

`tools/strategist_temoins.json` :

```json
{
  "_comment": "Temoin PERIME du stratege (spec PM 2026-09-16 §2.2) : un candidat deja tranche par les records, glisse parmi les candidats a chaque passe. S'il survit a la refutation, la passe est NULLE. Ne jamais le remplacer par un candidat plus facile a tuer.",
  "candidat": "Prochain run : rejouer S2-009 (recette a trois conditions) avec un warm-start apparie, comme « prochain pas jamais execute » de S2-011.",
  "attendu": "(WARM-00[13]|DAgger|déjà exécuté|deja execute|réactive|reactive|LOCK-001)",
  "raison": "Recommandation initiale de l'orchestrateur du 2026-09-08, REFUTEE par son propre panel le 2026-09-14 sur deux premisses fausses : le « jamais execute » l'avait ete (WARM-001 BPTT, WARM-003 DAgger, bassin results/warm003_dagger_genome.npz) et la tache S2-009 est REACTIVE, donc ne teste pas LOCK-001.",
  "source": "docs/roadmap/PRIORITES_ET_DETTES.md"
}
```

`tools/strategist_temoins.py` :

```python
"""Témoin périmé du stratège : chargement et règle de mise à mort (deux réfutations ET la bonne raison)."""
import json
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON = os.path.join(_ROOT, "tools", "strategist_temoins.json")


def charger():
    with open(_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def tue(temoin, votes):
    refus = [v for v in votes if v.get("refuted")]
    bonne_raison = any(re.search(temoin["attendu"], v.get("reason", ""), re.I) for v in refus)
    return len(refus) >= 2 and bonne_raison
```

`docs/REF/REF-STRATEGE.md` :

```markdown
---
id: REF-STRATEGE
type: REF
title: "Le stratège — lentilles, réfuteurs, juges et témoin figés du panel de direction"
status: active
---

# Le stratège : la procédure du 2026-09-14, figée

Précédent : audit du 2026-09-08 puis panel du 2026-09-14 (7 lentilles, 24 candidats, 72 réfutations, 3 juges) — **la
recommandation initiale de l'orchestrateur a été réfutée par son propre panel** (deux prémisses fausses). D'où la règle :
la stratégie est une PROCÉDURE, pas une voix ; les textes ci-dessous sont figés, `.claude/workflows/strategist.js` ne
porte que leurs identifiants ; les modifier est un commit décidé par robla, après lequel le témoin doit encore mourir.

**Sortie de toute passe** : `docs/roadmap/STRATEGE_PROPOSITION.md` (writer : la session PM). robla tranche dans la
conversation du PM ; le bloc 🧭 de `PRIORITES_ET_DETTES.md` ne bouge qu'après son accord. Chaque arbitrage proposé
publie la PRÉMISSE qui le porte, avec `fichier:ligne` — un arbitrage sur prémisse non mesurée est E8.

## Lentilles (phase Candidats) — chacune rend 2 à 6 candidats avec preuve `fichier:ligne`

| # | lentille | question | sources imposées |
| --- | --- | --- | --- |
| **L1** | stratège scientifique | Quel run ou quelle mesure déplace le chiffre directeur proxy 9 / in-world 0 ? Quelle prémisse porte la direction actuelle, est-elle mesurée ? | bloc 🧭 de `docs/roadmap/PRIORITES_ET_DETTES.md`, `docs/roadmap/FIL_DIRECTEUR_AGI.md`, les 5 derniers `docs/EDR/*.md` |
| **L2** | réfutateur dédié | Quelle priorité en cours repose sur une prémisse FAUSSE ou PÉRIMÉE ? Quel « jamais fait » l'a été ? (grep AVANT d'affirmer, E8) | `git log --since=30.days --name-only`, `docs/preregistrations/`, `results/` |
| **L3** | débit et coût | Qu'est-ce qui coûte des heures machine sans changer un verdict ? Quelle mesure est bornée par sa propre létalité ou sa charge ? | `data/pm/BOARD.json` (charge connue), `results/*.json` (`elapsed_s`, `cost`), CLAUDE.md §Coût des runs |
| **L4** | instruments in-world | Quel instrument n'a pas de contrôle positif, pas de plancher de bruit, pas de dose publiée ? | `tests/sandbox/test_instrument_calibration.py` (CALIBRATED), `docs/REF/REGISTRE_ERREURS.md` |
| **L5** | ingénierie du dépôt | Quelle dette rend un run non reproductible ou un résultat non rouvrable ? Quelle porte manque ? | `tools/hooks/pre-commit`, `docs/roadmap/PRIORITES_ET_DETTES.md` P0-P2 |
| **L6** | chercheur extérieur | Quel résultat publié ailleurs tranche ou déplace une question ouverte ici ? (sources nommées, pas de mémoire) | `docs/REF/RND_2018.md`, WebSearch avec citation |
| **L7** | north-star | Le travail des 30 derniers jours sert-il ADR-004 et le critère à 3 mois (record à trois conditions) ? Quoi arrêter ? | `docs/ADR/004_*.md`, `docs/superpowers/specs/2026-09-16-harness-contracts-design.md`, bloc 🧭 |
| **L8** | **Organisation** (uniquement sur événement §6.3) | Quel candidat de `ROLES.md` a atteint son critère de naissance ? Quel rôle instancié n'a plus de trouvaille confirmée ? Quelle fonction ad hoc a récidivé sans propriétaire ? Le ratio science/méthodo autorise-t-il un rôle neuf (règle 1:1) ? | `docs/roadmap/ROLES.md`, `data/pm/ROLES_COUNTS.json`, `data/pm/alerts.jsonl`, `docs/reviews/` |

## Réfuteurs (phase Réfutation) — 3 par candidat, indépendants, `refuted=true` par défaut si doute

| # | lentille | ce qui tue |
| --- | --- | --- |
| **R1** | périmé ou doublon | Un record, une entrée CLOS ou une décision 🧭 l'a déjà tranché ou exécuté (grep obligatoire : `docs/EDR`, `PRIORITES_ET_DETTES.md`, `results/`). Une preuve citée qui ne dit pas ce qu'on lui fait dire ANNULE (E8). |
| **R2** | coût et méthode | Coût > valeur chiffrée ; ajoute de la méthode là où la science n'avance plus (ratio science/méthodo dans `ROLES_COUNTS.json`) ; un run sans pré-vol possible ; une DV de survie qui confond « apprend » et « meurt en apprenant ». |
| **R3** | valeur | Ne déplace ni proxy 9 / in-world 0, ni le critère à 3 mois d'ADR-004 ; ou repose sur une prémisse non mesurée ; ou son unité de réplication n'est pas l'ère/le seed. |

## Juges (phase Juges) — 3 pondérations opposées, chacun classe les survivants

| # | pondération |
| --- | --- |
| **J1** | validité : prémisses mesurées, instrument calibré, deux issues possibles |
| **J2** | temps au premier record : ce qui grave quelque chose en moins de 15 jours machine |
| **J3** | extensibilité north-star : ce qui sert encore dans 6 mois sous ADR-004 |

## Synthèse (phase Synthèse)

Classement final = médiane des rangs des trois juges ; pour chaque candidat retenu : prémisse porteuse (`fichier:ligne`),
coût, ce que ça NE tranche pas, changement proposé au bloc 🧭 (ajout / retrait / rang). Puis : sort du témoin, candidats
réfutés et raisons, et — si L8 a tourné — naissances / mutations / dissolutions proposées dans `ROLES.md`.

## Témoin (contrôle positif de la passe)

`tools/strategist_temoins.json` : un candidat déjà tranché est glissé parmi les candidats ; il doit être réfuté par ≥ 2
réfuteurs sur 3, dont un pour la raison attendue (regex). Sinon la passe est **NULLE** : rien ne s'écrit, le compteur
`témoin manqué` du Stratège dans `ROLES.md` s'incrémente ; deux fois → les textes de ce REF sont re-scellés.

## Modes

`delta` (un événement : record, entrée close, `-bis`, nul) : L1 + L2 seulement, ≤ 5 candidats, question unique « cet
événement déplace-t-il un rang du bloc 🧭 ? ». `full` (rétractation, ≥ 20 records depuis le dernier full, > 30 jours,
ou demande de robla) : L1-L7, L8 si événement d'organisation, ≤ 12 candidats.
```

- [ ] **Step 4 : lancer, vérifier le vert + porte 1 (le REF n'est pas orphelin)**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_strategist_temoins.py tests/sandbox/test_record_graph_completeness.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_record_links.py --only docs/REF/REF-STRATEGE.md`
Expected: PASS ; `OK`.

- [ ] **Step 5 : commit**

```bash
git add docs/REF/REF-STRATEGE.md tools/strategist_temoins.json tools/strategist_temoins.py tests/sandbox/test_strategist_temoins.py
git commit -m "feat(stratege): REF-STRATEGE (L1-L8, R1-R3, J1-J3, synthese, modes) + temoin PERIME (la reco du 09-08 refutee le 09-14) et sa regle de mise a mort" -- docs/REF/REF-STRATEGE.md tools/strategist_temoins.json tools/strategist_temoins.py tests/sandbox/test_strategist_temoins.py
```

---

### Task 3 : `.claude/workflows/strategist.js` + `docs/roadmap/STRATEGE_PROPOSITION.md`

**Files:**
- Create: `.claude/workflows/strategist.js`, `docs/roadmap/STRATEGE_PROPOSITION.md`

**Interfaces:**
- `args = {mode: 'delta'|'full', events: [{type, cible}], today: 'AAAA-MM-JJ', organisation: bool, temoin: {candidat, attendu, raison}}` — tous fournis par la session PM depuis `tools/pm/strategist_events.py` et `tools/strategist_temoins.py` ; le script n'invente rien.
- Retour : `{statut: 'ECRITE'|'NUL', fichier, n_candidats, n_survivants, temoin: {tue, votes}}`.

- [ ] **Step 1 : écrire le workflow**

`.claude/workflows/strategist.js` :

```javascript
export const meta = {
  name: 'strategist',
  description: 'Stratege AGAGI : lentilles -> fusion -> refutation (3 lentilles) -> juges (3 ponderations) -> synthese, textes figes dans docs/REF/REF-STRATEGE.md ; temoin perime obligatoire ; ecrit docs/roadmap/STRATEGE_PROPOSITION.md',
  phases: [
    { title: 'Candidats', detail: 'L1-L2 (delta) ou L1-L7 (+L8 si organisation)' },
    { title: 'Fusion', detail: 'dedup, plafond, temoin glisse' },
    { title: 'Refutation', detail: 'R1 R2 R3 par candidat, refuted=true par defaut' },
    { title: 'Juges', detail: 'J1 J2 J3 classent les survivants' },
    { title: 'Synthese', detail: 'STRATEGE_PROPOSITION.md, premisse porteuse par arbitrage' },
  ],
}

const REF = 'docs/REF/REF-STRATEGE.md'
const FULL = args.mode === 'full'
const LENTILLES = FULL ? ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7'].concat(args.organisation ? ['L8'] : []) : ['L1', 'L2']
const PLAFOND = FULL ? 12 : 5
const EVENTS = (args.events || []).map(e => `${e.type} ${e.cible}`).join(' ; ') || 'aucun (demande de robla ou plancher)'

const CANDIDATS = { type: 'object', properties: { candidats: { type: 'array', items: { type: 'object', properties: {
  titre: { type: 'string' }, action: { type: 'string' }, premisse: { type: 'string' }, preuve: { type: 'string' },
  cout: { type: 'string' }, ne_tranche_pas: { type: 'string' }, control: { type: 'boolean' } },
  required: ['titre', 'action', 'premisse', 'preuve', 'cout', 'ne_tranche_pas'] } } }, required: ['candidats'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, evidence: { type: 'string' } },
  required: ['refuted', 'reason'] }
const RANG = { type: 'object', properties: { classement: { type: 'array', items: { type: 'object', properties: {
  titre: { type: 'string' }, rang: { type: 'number' }, motif: { type: 'string' } }, required: ['titre', 'rang', 'motif'] } } },
  required: ['classement'] }

const socle = `Lis ${REF} et applique EXACTEMENT le texte de l'identifiant demande. Mode ${args.mode}. Evenements declencheurs : ${EVENTS}.
Toute preuve est un fichier:ligne ou une sortie de commande que tu as LANCEE (grep, git log, python -c). Reponds en francais.`

phase('Candidats')
const lus = await parallel(LENTILLES.map(L => () =>
  agent(`${socle}\nLENTILLE ${L}. Rends 2 a 6 candidats. En mode delta, une seule question : cet evenement deplace-t-il un rang du bloc de direction ?`,
    { label: `lentille:${L}`, phase: 'Candidats', schema: CANDIDATS })))
const bruts = lus.filter(Boolean).flatMap(r => r.candidats)
log(`${bruts.length} candidats par ${lus.filter(Boolean).length}/${LENTILLES.length} lentilles`)

phase('Fusion')
const temoin = Object.assign({ control: true, action: 'lancer ce run en priorite', cout: 'non chiffre', ne_tranche_pas: 'non dit',
  preuve: 'aucune (candidat de l orchestrateur)' , premisse: 'prochain pas jamais execute' }, { titre: args.temoin.candidat })
const fusion = await agent(`Fusionne ces candidats par ACTION (pas par titre), union des preuves, au plus ${PLAFOND} distincts ; garde tel quel
le candidat marque control=true (ne le fusionne avec rien, conserve control=true). Liste les ecartes dans un candidat fictif titre '__ecartes__'.
Ne lis aucun fichier. Reponds en francais.\n${JSON.stringify(bruts.concat([temoin]), null, 1)}`,
  { label: 'fusion', phase: 'Fusion', schema: CANDIDATS, effort: 'low' })
const candidats = ((fusion && fusion.candidats) || []).filter(c => c.titre !== '__ecartes__')
if (!candidats.some(c => c.control)) { log('temoin perdu a la fusion : passe NULLE'); return { statut: 'NUL', raison: 'temoin perdu a la fusion' } }

phase('Refutation')
const juges_ = await pipeline(candidats,
  c => parallel(['R1', 'R2', 'R3'].map(R => () =>
    agent(`${socle}\nREFUTEUR ${R}. Essaie de REFUTER ce candidat ; par defaut refuted=true si tu hesites.\n${JSON.stringify(c, null, 1)}`,
      { label: `refute:${R}:${c.titre.slice(0, 24)}`, phase: 'Refutation', schema: VERDICT })))
    .then(vs => { const votes = vs.filter(Boolean); return Object.assign({}, c, { votes, survit: votes.length > 0 && votes.filter(v => v.refuted).length < 2 }) }))
const resultats = juges_.filter(Boolean)
const tem = resultats.find(c => c.control)
const raisonOk = tem && tem.votes.some(v => v.refuted && new RegExp(args.temoin.attendu, 'i').test(v.reason || ''))
const temoinTue = !!tem && !tem.survit && !!raisonOk
log(`temoin : ${temoinTue ? 'TUE pour la bonne raison' : 'NON TUE -> passe NULLE'}`)
if (!temoinTue) return { statut: 'NUL', raison: 'temoin non tue', temoin: { tue: false, votes: tem ? tem.votes : [] } }
const survivants = resultats.filter(c => c.survit && !c.control)
const refutes = resultats.filter(c => !c.survit && !c.control)
log(`${survivants.length} survivants, ${refutes.length} refutes`)

phase('Juges')
const rangs = survivants.length ? await parallel(['J1', 'J2', 'J3'].map(J => () =>
  agent(`${socle}\nJUGE ${J}. Classe TOUS ces survivants (rang 1 = le plus prioritaire) selon ta ponderation, un motif par rang.\n${JSON.stringify(survivants.map(s => ({ titre: s.titre, action: s.action, premisse: s.premisse, preuve: s.preuve, cout: s.cout })), null, 1)}`,
    { label: `juge:${J}`, phase: 'Juges', schema: RANG }))) : []
const mediane = {}
for (const s of survivants) {
  const rs = rangs.filter(Boolean).map(r => (r.classement.find(x => x.titre === s.titre) || { rang: survivants.length }).rang).sort((a, b) => a - b)
  mediane[s.titre] = rs.length ? rs[Math.floor(rs.length / 2)] : null
}

phase('Synthese')
const fichier = 'docs/roadmap/STRATEGE_PROPOSITION.md'
const synth = await agent(`${socle}\nSYNTHESE. Ecris (Write) le fichier ${fichier} : conserve son EN-TETE permanent (tout ce qui precede la ligne '## Derniere passe'),
puis remplace la section '## Derniere passe' par : date ${args.today}, mode ${args.mode}, evenements (${EVENTS}), temoin TUE (votes : ${JSON.stringify(tem.votes)}),
classement final par mediane des rangs ${JSON.stringify(mediane)} avec pour chaque survivant : action, PREMISSE PORTEUSE (fichier:ligne), cout, ce que ca ne tranche pas,
changement propose au bloc de direction (ajout / retrait / rang) ; puis les refutes et leurs raisons ${JSON.stringify(refutes.map(r => ({ titre: r.titre, raisons: r.votes.filter(v => v.refuted).map(v => v.reason) })))} ;
${args.organisation ? "puis une section Organisation : naissances / mutations / dissolutions proposees dans ROLES.md avec leur preuve ;" : ''}
et la phrase finale : 'Proposition. robla tranche ; le bloc de direction ne bouge qu apres son accord.' N'ecris dans AUCUN autre fichier.`,
  { label: 'synthese', phase: 'Synthese', effort: 'high' })
return { statut: 'ECRITE', fichier, n_candidats: candidats.length - 1, n_survivants: survivants.length,
         temoin: { tue: true, votes: tem.votes }, mediane, note: synth }
```

`docs/roadmap/STRATEGE_PROPOSITION.md` (en-tête permanent + section remplacée à chaque passe) :

```markdown
# Proposition du stratège — en attente de décision

**Writer unique : la session PM**, à partir de la sortie de `.claude/workflows/strategist.js` (textes figés :
`docs/REF/REF-STRATEGE.md`). Ce fichier est une PROPOSITION : le bloc 🧭 de `PRIORITES_ET_DETTES.md` ne bouge qu'après
la décision de robla dans la conversation du PM. Une passe dont le témoin périmé n'a pas été tué n'écrit rien ici.
Chaque arbitrage cite la prémisse qui le porte (`fichier:ligne`) : un arbitrage sur prémisse non mesurée est E8.

## Dernière passe

Aucune passe encore exécutée (fichier créé le 2026-09-16 par le plan 3).
```

- [ ] **Step 2 : essai réel en mode `delta` (contrôle du témoin), puis vérifier le fichier**

En session PM : `Workflow({scriptPath: '.claude/workflows/strategist.js', args: {mode: 'delta', events: [{type: 'record', cible: '<dernier docs/EDR ajouté>'}], today: '<date>', organisation: false, temoin: <contenu de tools/strategist_temoins.json sans _comment>}})`.
Expected: phase Refutation → `temoin : TUE pour la bonne raison` (les réfuteurs doivent trouver WARM-001/003 ou la tâche réactive) ; `STRATEGE_PROPOSITION.md` a une section « Dernière passe » datée, avec ≤ 5 candidats et une prémisse porteuse par candidat. Si le témoin n'est PAS tué : ne pas livrer — resserrer R1 dans le REF (imposer le grep de `PRIORITES_ET_DETTES.md` sur le titre du candidat) et rejouer.
Run: `PYTHONIOENCODING=utf-8 python tools/check_backlog_freshness.py` (le fichier cite des chemins) et `git status --short docs/roadmap/` (seul `STRATEGE_PROPOSITION.md` a bougé).

- [ ] **Step 3 : commit**

```bash
git add .claude/workflows/strategist.js docs/roadmap/STRATEGE_PROPOSITION.md
git commit -m "feat(stratege): workflow strategist.js (lentilles figees par identifiant, fusion, 3 refuteurs, 3 juges, synthese ; temoin perime obligatoire, passe NULLE sinon) + STRATEGE_PROPOSITION.md (writer PM, robla tranche)" -- .claude/workflows/strategist.js docs/roadmap/STRATEGE_PROPOSITION.md
```

---

### Task 4 : Intégration au `/pm`, `ROLES.md`, et le premier `full`

**Files:**
- Modify: `.claude/skills/pm/SKILL.md` (étape 4), `docs/roadmap/ROLES.md` (ligne Stratège), `tools/pm/tick.py` (rien de plus : la détection est là depuis la Task 1)

- [ ] **Step 1 : réécrire l'étape 4 du skill `/pm`**

Remplacer l'étape 4 de `.claude/skills/pm/SKILL.md` par :

```markdown
4. **Stratège** — quand le digest porte `[PM] STRATEGE mode=delta|full` :
   - lire `tools/strategist_temoins.json` (sans `_comment`) et lancer
     `Workflow({scriptPath: '.claude/workflows/strategist.js', args: {mode, events, today, organisation, temoin}})` ;
     `organisation=true` si : rétractation, alerte PM `REPETEE`, récidive E10 sur la règle d'un rôle, témoin manqué au tick
     précédent, ou ≥ 20 records / 30 jours (le `mode=full` du digest) ;
   - `statut: NUL` → incrémenter « témoin manqué » sur la ligne Stratège de `ROLES.md` (commit path-scoped après accord) ;
     deux fois de suite → proposer à robla de re-sceller `docs/REF/REF-STRATEGE.md`, ne PAS relancer ;
   - `statut: ECRITE` → présenter à robla la section « Dernière passe » de `docs/roadmap/STRATEGE_PROPOSITION.md`
     (classement, prémisse porteuse, ce que ça ne tranche pas) et ATTENDRE sa décision ;
   - décision reçue → écrire le bloc 🧭 de `docs/roadmap/PRIORITES_ET_DETTES.md` (snapshot/verify, compte d'entrées ≥ avant,
     `check_backlog_freshness`), puis `python -c "from tools.pm.strategist_events import marquer_full; marquer_full()"` si la
     passe était `full` ; compteurs du Stratège (proposées / acceptées / amendées / refusées) mis à jour dans `ROLES.md`.
```

- [ ] **Step 2 : mettre à jour la ligne Stratège de `ROLES.md`**

Remplacer la cellule Instrument par : `` `.claude/workflows/strategist.js` (identifiants) + `docs/REF/REF-STRATEGE.md` (textes figés) ; événements : `tools/pm/strategist_events.py` `` et la cellule Contrôle positif par : `` témoin périmé `tools/strategist_temoins.json` tué par ≥ 2 réfuteurs pour la raison attendue ; sinon passe NULLE ``.
Run: `PYTHONIOENCODING=utf-8 python tools/check_roles_registry.py && PYTHONIOENCODING=utf-8 python tools/check_synthesis_counts.py`
Expected: exit 0 ×2 (les comptes 3 / 7 sont inchangés).

- [ ] **Step 3 : le premier `full` — la revue des rôles à zéro**

En session PM, avec l'accord de robla (coût : ~10 lentilles + 3 × ≤ 12 réfutations + 3 juges ≈ 50 agents, ~1 h) : `mode: 'full', organisation: true`. C'est le point zéro de la règle 1:1 : la section Organisation de la proposition doit dire, chiffres à l'appui (`ROLES_COUNTS.json`), qu'aucun rôle neuf n'est recevable tant que science/méthodo < 1:1, et proposer — ou non — la dissolution d'un des trois rôles initiaux selon ses compteurs. Puis `marquer_full()`.

- [ ] **Step 4 : commit**

```bash
git add .claude/skills/pm/SKILL.md docs/roadmap/ROLES.md
git commit -m "feat(pm): etape 4 du tick -- lancer le stratege sur evenement, presenter la proposition, ecrire le bloc de direction apres decision ; ligne Stratege de ROLES.md : instrument et temoin livres" -- .claude/skills/pm/SKILL.md docs/roadmap/ROLES.md
```

---

## Auto-revue du plan

- **Couverture spec §2.2 / §3.4 / §6.3 / §6.4** : événements et modes → Task 1 (plancher 30 j / 20 records, rétractation → full) ; prompts figés, L8 Organisation, réfuteurs, juges, témoin → Task 2 ; workflow, proposition, « robla tranche », prémisse porteuse → Task 3 ; skill, compteurs, règle 1:1 au premier full → Task 4. Naissance / mutation / dissolution : portées par L8 et la section Organisation de la proposition ; l'écriture dans `ROLES.md` reste au PM après décision (writer unique).
- **Écarts déclarés** : aucun nouveau cliquet dans ce plan (le stratège n'est pas une porte) ; les compteurs du Stratège (proposées / acceptées / refusées) sont tenus À LA MAIN par le PM dans `ROLES.md` à chaque décision — un fichier `data/pm/strategist_log.jsonl` deviendra nécessaire à la 10ᵉ passe (YAGNI avant).
- **Cohérence** : `detecter_et_persister`, `marquer_full`, `charger`, `tue` nommés identiquement dans tests, code et skill ; les identifiants `L1`…`L8`, `R1`…`R3`, `J1`…`J3` existent dans le REF (test) et dans le JS.
- **Placeholders** : `<dernier docs/EDR ajouté>` et `<date>` dans l'essai réel (Task 3 Step 2) sont des valeurs de la machine au moment de l'essai ; aucun `TBD`.

