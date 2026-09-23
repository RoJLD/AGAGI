# Plan 2/3 — Portes 18/19/20, `review:`, `reviewed_by`, Réfutateur, dettes consignées

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retirer au Réfutateur tout ce qui est décidable par grep en le livrant comme portes (régime cité ↔ mesuré, provenance de l'évidence, garde E19 appelée), rendre la revue OBLIGATOIRE par frontmatter, puis livrer le Réfutateur comme workflow à prompts figés avec ses témoins gelés.

**Architecture:** Trois cliquets à baseline gelée sur le modèle des portes 1 et 11 (`analyze` pur + `main` ratchet + `--only` + baseline + mutation) ; deux exigences de frontmatter/enveloppe (`review:` dans `check_record_links`, `reviewed_by` dans `preregister`) ; un workflow `.claude/workflows/refutateur.js` dont la phase 0 rejoue les prompts sur trois records-témoins gelés à leur SHA et un record sain, et sort `NUL` si un défaut connu n'est pas retrouvé.

**Tech Stack:** Python 3 stdlib (`ast`, `re`, `json`, `subprocess`), pytest, git CLI, Workflow (JavaScript, prompts figés).

**Spec:** `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` (§2.3, §3.5, §6.1, §7 étapes 4-5, §10).

## Global Constraints

- **Toute nouvelle porte** = module `tools/check_<nom>.py` (nom commençant par `check_`, donc hors du scan de calibration) + bloc dans `tools/hooks/pre-commit` appelant `python tools/check_<nom>.py` (c'est ce motif que `check_synthesis_counts._portes_hook` compte) + entrée `check_gate_mutation.PORTES["<n>"]` dont chaque `avant` apparaît EXACTEMENT une fois dans le source, indentation comprise + témoin qui ROUGIT sur la mutation + phrase et balise `<!-- count:portes_hook=N -->` de `CLAUDE.md` mises à jour ensemble (N = nombre de modules `check_*` distincts dans le hook : 18 après le plan 1, 21 après ce plan).
- **Baseline** dans la regex des fichiers déclencheurs du hook (E4 occ. 5) ; baseline stagée seule → run NON scopé (E4 occ. 6).
- **Un fichier illisible est RAPPORTÉ, jamais compté 0** ; un record sans frontmatter lisible est rapporté, pas ignoré.
- **Décimales** : les records récents écrivent `0,04`, les JSON `0.04` — normaliser `,`→`.` avant `float`.
- **Porte 12** : aucune constante `results/…` ou `data/…` dans les nouveaux `tools/check_*.py` hors regex (une regex est une chaîne : `_EST_DONNEE` est ancré `^` donc `r"results/[…]"` dans un motif SANS préfixe `^` ne matche pas — vérifier avec `python tools/check_data_paths.py --only <fichier>` à chaque tâche).
- **Fichiers partagés** (`CLAUDE.md`, `tools/hooks/pre-commit`, `tools/check_gate_mutation.py`, `tools/consolidate_records.py`, `tools/check_record_links.py`, `tools/preregister.py`, `docs/roadmap/PRIORITES_ET_DETTES.md`) : `check_staged_authorship.snapshot([...], owner='plan-refutateur')` avant d'éditer, `verify` avant de committer ; commits path-scoped ; **accord de robla avant le premier commit**.
- **Tests** : `PYTHONIOENCODING=utf-8 python -m pytest <fichier> -q -p no:cacheprovider` ; timeout 120 s ; aucun test ne lit `results/` réel autrement qu'en lecture.

---

## Structure des fichiers

| fichier | responsabilité |
| --- | --- |
| `tools/check_regime_claims.py` + `tools/regime_claims_baseline.json` | porte 18 : paramètre cité ↔ bloc `regime` d'un `results/*.json` suivi |
| `tools/check_evidence_provenance.py` + `tools/evidence_provenance_baseline.json` | porte 19 : chemin `results/` cité existe et est suivi par git |
| `tools/check_e19_optimizer_sweep.py` + `tools/e19_sweep_baseline.json` | porte 20 : runner scellé à bras sous gradient appelle `assert_verdict_invariant_to_optimizer` |
| `tools/consolidate_records.py`, `tools/check_record_links.py`, `tools/record_link_baseline.json` | `review:` lu, exigé des NOUVEAUX records à `gate:`/`tests:` |
| `tools/preregister.py` | `reviewed_by` exigé à l'enveloppe des NOUVELLES règles qui déclarent un coût |
| `docs/REF/REF-REVUE-ADVERSARIALE.md` | les 10 prompts FIGÉS du Réfutateur, numérotés |
| `.claude/workflows/refutateur.js` | phases témoins → revue → consolidation |
| `tools/refutateur_temoins.py` + `tools/refutateur_temoins.json` | extraction des témoins gelés à leur SHA, défauts connus |
| `docs/reviews/README.md` | convention des fichiers de revue référencés par `review:` |
| `tools/hooks/pre-commit`, `tools/check_gate_mutation.py`, `CLAUDE.md` | trois portes branchées, mutées, comptées |
| `docs/roadmap/PRIORITES_ET_DETTES.md` | cinq dettes consignées (P2.78-P2.82) |
| `tests/sandbox/test_regime_claims_gate.py`, `test_evidence_provenance_gate.py`, `test_e19_sweep_gate.py`, `test_record_graph_completeness.py` (ajouts), `test_preregistration_guard.py` (ajouts), `test_refutateur_temoins.py` | témoins |

---

### Task 1 : Porte 18 — `tools/check_regime_claims.py`

**Files:**
- Create: `tools/check_regime_claims.py`, `tools/regime_claims_baseline.json`
- Modify: `tools/hooks/pre-commit` (nouveau bloc `# 18.` avant `[ "$fail" -ne 0 ]`), `tools/check_gate_mutation.py` (`PORTES["18"]`), `CLAUDE.md` (balise `portes_hook`)
- Test: `tests/sandbox/test_regime_claims_gate.py`

**Interfaces:**
- Produces:
  - `PARAMS = ("forage_payoff", "flip_p", "reward_scale", "lr", "n_agents", "num_agents", "max_ticks", "ticks", "cog_gain", "base_metabolism", "torch_episode_k")` ; `ALIAS = {"n_agents": "num_agents", "ticks": "max_ticks"}`
  - `claims(texte) -> dict[str, set[float]]` — paramètre → valeurs citées (backticks retirés, `,`→`.`, `=` avec ou sans espaces)
  - `cited_results(texte) -> list[str]` — chemins `results/…json` en backtick, ensembles `{a,b}` et globs `*` développés à l'appel de `main` (pas ici)
  - `regime_values(data) -> dict[str, set[float]]` — depuis `data["regime"]` (racine) ET `data[<cellule>]["regime"]` (imbriqué : cellules = clés racine ne commençant pas par `_`) ET les clés de cellule `lr=0.001|seed=2026` (paramètre `lr`), avec alias appliqués
  - `evaluer(texte, lecteur) -> dict` — `lecteur(chemin) -> dict | None` ; rend `{"params": {...}, "cites": [...], "statut": "SANS_PARAMETRE"|"SANS_RESULTS"|"SANS_REGIME"|"DISCORDE"|"CONCORDE", "detail": [str]}`. CONCORDE ⟺ chaque paramètre cité a AU MOINS UNE valeur présente dans le régime d'AU MOINS UN results cité (une rectification cite la vraie et la fausse : c'est la vraie qui compte).
  - `analyze(root) -> {"records": {file: verdict}, "illisibles": [file]}`
  - `main(argv=None) -> int` — `--report`, `--update-baseline`, `--only` ; baseline `{"legataires": [files], "_comment"}` ; exit 1 sur tout record HORS baseline dont le statut ∉ {SANS_PARAMETRE, CONCORDE}.

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_regime_claims_gate.py` :

```python
"""Porte 18 : une valeur de parametre citee par un record est une MESURE publiee par le runner (bloc regime),
pas un decor recopie de memoire (E8 occ. 4 : forage_payoff = 3.0 alors que le run tournait a 1.0)."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_regime_claims as G  # noqa: E402

GRAB_COST_V1 = ("le régime de famine dure porte `forage_payoff = 3.0` — ramasser un fruit RAPPORTE. "
                "Résultats (`results/p41_grab_mechanism.json`).")
GRAB_COST_RECTIFIE = GRAB_COST_V1 + " Mesuré : `run_condition` construit avec `config=None`, donc `forage_payoff = 1.0`."
CALIB = ("`natural` (tel que publié : `lr = 0,04`), `lr_low` (`lr = 0,004`), `n_agents`=12 ; "
         "(`results/legacy_lr_curve_r2.json`, `cost`).")
REGIME_RACINE = {"regime": {"forage_payoff": 1.0, "num_agents": 20, "max_ticks": 400}}
REGIME_CELLULES = {"_design": {}, "lr=0.04|seed=2026": {"regime": {"num_agents": 12, "forage_payoff": 0.0}},
                   "lr=0.004|seed=2026": {"regime": {"num_agents": 12}}}


def test_claims_lit_les_trois_placements_du_backtick_et_la_virgule_francaise():
    c = G.claims("`forage_payoff = 3.0` ; `lr`=0,05 ; lr=0,002 ; `cog_gain=12.0, base_metabolism=0.75, immortal=True`")
    assert c["forage_payoff"] == {3.0} and c["lr"] == {0.05, 0.002}
    assert c["cog_gain"] == {12.0} and c["base_metabolism"] == {0.75}
    assert "immortal" not in c and "seeds" not in G.claims("3 seeds × 18 ères")


def test_cited_results_ne_retient_que_les_chemins_results_json_en_backtick():
    t = "(`results/a.json`, `results/lock_001_pred2_r{2,3,4}.json`, `docs/preregistrations/X.json`, `témoins `results/b_K{3,4}.json`)"
    assert G.cited_results(t) == ["results/a.json", "results/b_K{3,4}.json", "results/lock_001_pred2_r{2,3,4}.json"]


def test_regime_values_lit_la_racine_les_cellules_et_les_cles_de_cellule():
    r = G.regime_values(REGIME_RACINE)
    assert r["forage_payoff"] == {1.0} and r["num_agents"] == {20.0} and r["max_ticks"] == {400.0}
    c = G.regime_values(REGIME_CELLULES)
    assert c["lr"] == {0.04, 0.004} and c["num_agents"] == {12.0} and c["forage_payoff"] == {0.0}


def test_CONTRE_EXEMPLE_GELE_EDR_GRAB_COST_au_2026_09_09_est_DISCORDE():
    v = G.evaluer(GRAB_COST_V1, lambda p: REGIME_RACINE)
    assert v["statut"] == "DISCORDE" and "forage_payoff" in " ".join(v["detail"])


def test_la_rectification_qui_cite_la_vraie_ET_la_fausse_valeur_CONCORDE():
    assert G.evaluer(GRAB_COST_RECTIFIE, lambda p: REGIME_RACINE)["statut"] == "CONCORDE"


def test_alias_n_agents_num_agents_et_ticks_max_ticks():
    v = G.evaluer("`n_agents`=20 et `ticks`=400 (`results/x.json`)", lambda p: REGIME_RACINE)
    assert v["statut"] == "CONCORDE"


def test_record_sans_parametre_ou_sans_results_ou_sans_regime():
    assert G.evaluer("aucun chiffre ici", lambda p: None)["statut"] == "SANS_PARAMETRE"
    assert G.evaluer("`lr = 0,04` sans fichier", lambda p: None)["statut"] == "SANS_RESULTS"
    assert G.evaluer("`lr = 0,04` (`results/x.json`)", lambda p: {"rows": []})["statut"] == "SANS_REGIME"
    assert G.evaluer("`lr = 0,04` (`results/x.json`)", lambda p: None)["statut"] == "SANS_RESULTS"   # fichier absent -> rapporte


def test_CALIB_LEARNER_concorde_avec_les_cellules_imbriquees():
    assert G.evaluer(CALIB, lambda p: REGIME_CELLULES)["statut"] == "CONCORDE"


def test_analyze_rapporte_les_records_ILLISIBLES_au_lieu_de_les_ignorer(tmp_path):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("`lr = 0,04` (`results/x.json`)", encoding="utf-8")
    (d / "B.md").write_bytes(b"\xff\xfe\x00\x00 pas de l'utf-8 valide \x80")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text(json.dumps({"regime": {"lr": 0.04}}), encoding="utf-8")
    a = G.analyze(str(tmp_path), suivi=lambda root, rel: True)          # tmp_path n'est pas un depot git : suivi injecte
    assert a["records"]["docs/EDR/A.md"]["statut"] == "CONCORDE" and a["illisibles"] == ["docs/EDR/B.md"]


def test_le_depot_REEL_n_a_aucun_record_HORS_baseline_qui_discorde():
    a = G.analyze(G._ROOT)
    assert len(a["records"]) > 100, "le périmètre est vide, le test ne prouverait rien"
    base = set(G._load_baseline())
    hors = {f: v["statut"] for f, v in a["records"].items()
            if f not in base and v["statut"] not in ("SANS_PARAMETRE", "CONCORDE")}
    assert hors == {}, hors


def test_main_rend_1_sur_un_NOUVEAU_record_discordant_et_0_quand_il_est_gele(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text(GRAB_COST_V1, encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "p41_grab_mechanism.json").write_text(json.dumps(REGIME_RACINE), encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": []}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    assert G.main(["--root", str(tmp_path)]) == 1
    assert G.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert G.main(["--root", str(tmp_path)]) == 0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_regime_claims_gate.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: No module named 'tools.check_regime_claims'`.

- [ ] **Step 3 : implémenter**

`tools/check_regime_claims.py` :

```python
"""Porte 18 — RÉGIME CITÉ ↔ RÉGIME MESURÉ (classe E8 occ. 4, spec PM §3.5).

  python tools/check_regime_claims.py                    # cliquet : exit 1 sur tout NOUVEAU record discordant
  python tools/check_regime_claims.py --report           # état complet, exit 0
  python tools/check_regime_claims.py --update-baseline  # gèle l'état courant (dette légataire)
  python tools/check_regime_claims.py --only docs/EDR/X.md

Un record qui cite `forage_payoff = 3.0` doit citer un `results/*.json` SUIVI par git dont le bloc `regime`
porte cette valeur. Mesuré le 2026-09-16 : 47 records citent un paramètre, 4 citent un bloc regime — les 43
autres sont la dette gelée ici. Un record illisible est RAPPORTÉ, jamais compté CONCORDE.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "regime_claims_baseline.json")
PARAMS = ("forage_payoff", "flip_p", "reward_scale", "lr", "n_agents", "num_agents", "max_ticks", "ticks",
          "cog_gain", "base_metabolism", "torch_episode_k")
ALIAS = {"n_agents": "num_agents", "ticks": "max_ticks"}
_NUM = r"([0-9]+(?:[.,][0-9]+)?)"
_CLAIM = re.compile(r"(?<![\w.])(" + "|".join(PARAMS) + r")\s*=\s*" + _NUM + r"(?![\w.])")
_RESULTS = re.compile(r"`[^`]*?(results/[A-Za-z0-9_./*{},\-]+\.json)`")
_CELL_LR = re.compile(r"(?:^|\|)lr=" + _NUM + r"(?:\||$)")
OK = ("SANS_PARAMETRE", "CONCORDE")


def _f(s):
    return float(str(s).replace(",", "."))


def _canon(p):
    return ALIAS.get(p, p)


def claims(texte):
    out = {}
    for p, v in _CLAIM.findall(texte.replace("`", "")):
        out.setdefault(_canon(p), set()).add(_f(v))
    return out


def cited_results(texte):
    return sorted(set(_RESULTS.findall(texte)))


def _developper(root, motif):
    """`{2,3,4}` et `*` -> fichiers existants ; un motif sans joker rend lui-même (existant ou non)."""
    if not any(c in motif for c in "*{"):
        return [motif]
    m = re.search(r"\{([^{}]*)\}", motif)
    variantes = [motif.replace(m.group(0), x, 1) for x in m.group(1).split(",")] if m else [motif]
    out = []
    for v in variantes:
        if "{" in v:
            out += _developper(root, v)
        elif "*" in v:
            out += sorted(os.path.relpath(p, root).replace("\\", "/") for p in glob.glob(os.path.join(root, v)))
        else:
            out.append(v)
    return out


def _absorber(dst, regime):
    for k, v in (regime or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k in PARAMS:
            dst.setdefault(_canon(k), set()).add(float(v))


def regime_values(data):
    out = {}
    if not isinstance(data, dict):
        return out
    _absorber(out, data.get("regime") if isinstance(data.get("regime"), dict) else None)
    for k, v in data.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        _absorber(out, v.get("regime") if isinstance(v.get("regime"), dict) else None)
        m = _CELL_LR.search(k)
        if m:
            out.setdefault("lr", set()).add(_f(m.group(1)))
    return out


def evaluer(texte, lecteur, root=_ROOT):
    cl = claims(texte)
    cites = [c for motif in cited_results(texte) for c in _developper(root, motif)]
    if not cl:
        return {"params": {}, "cites": cites, "statut": "SANS_PARAMETRE", "detail": []}
    mesures = {}
    lus = 0
    for c in cites:
        data = lecteur(c)
        if data is None:
            continue
        lus += 1
        for p, vals in regime_values(data).items():
            mesures.setdefault(p, set()).update(vals)
    params = {p: sorted(v) for p, v in cl.items()}
    if lus == 0:
        return {"params": params, "cites": cites, "statut": "SANS_RESULTS", "detail": ["aucun results/ cité n'est lisible"]}
    if not mesures:
        return {"params": params, "cites": cites, "statut": "SANS_REGIME", "detail": ["aucun bloc regime dans les results cités"]}
    detail = []
    for p, vals in cl.items():
        if p not in mesures:
            detail.append(f"{p} cité {sorted(vals)} : absent du régime publié")
        elif not (vals & mesures[p]):
            detail.append(f"{p} cité {sorted(vals)} : régime publié {sorted(mesures[p])}")
    statut = "DISCORDE" if detail else "CONCORDE"
    return {"params": params, "cites": cites, "statut": statut, "detail": detail}


def _lecteur(root):
    def lire(rel):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None
    return lire


def _tracked(root, rel):
    p = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True)
    return p.returncode == 0


def analyze(root=_ROOT, suivi=None):
    """`suivi(root, rel) -> bool` injectable (les tests tournent hors dépôt git) ; défaut : `_tracked`, résolu à l'appel."""
    suivi = _tracked if suivi is None else suivi
    out, illisibles = {}, []
    d = os.path.join(root, "docs", "EDR")
    lecteur = _lecteur(root)

    def lecteur_suivi(rel):
        return lecteur(rel) if suivi(root, rel) else None
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".md"):
            continue
        rel = f"docs/EDR/{name}"
        try:
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                texte = fh.read()
        except (OSError, UnicodeDecodeError):
            illisibles.append(rel)
            continue
        out[rel] = evaluer(texte, lecteur_suivi, root)
    return {"records": out, "illisibles": illisibles}


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return []
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh).get("legataires", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
    a = analyze(args.root)
    fautifs = sorted(f for f, v in a["records"].items() if v["statut"] not in OK)
    for f in a["illisibles"]:
        print(f"  [ILLISIBLE, non compté] {f}")
    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Records citant un parametre SANS bloc regime concordant, geles comme dette legataire "
                                   "(E8 occ. 4). Aucun NOUVEAU (tools/check_regime_claims.py).",
                       "legataires": fautifs}, fh, ensure_ascii=False, indent=2)
        print(f"baseline gelée : {len(fautifs)} record(s) sur {len(a['records'])}")
        return 0
    n = {s: sum(1 for v in a["records"].values() if v["statut"] == s) for s in ("SANS_PARAMETRE", "CONCORDE", "SANS_RESULTS", "SANS_REGIME", "DISCORDE")}
    print(f"records : {len(a['records'])} | {n}")
    if args.report:
        for f in fautifs:
            print(f"  [{a['records'][f]['statut']}] {f} : {'; '.join(a['records'][f]['detail'])}")
        return 0
    base = set(_load_baseline())
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}
    nouveaux = [f for f in fautifs if f not in base and (only is None or f in only)]
    nouveaux += [i for i in a["illisibles"] if only is None or i in only]     # illisible BLOQUE : jamais compté OK
    if nouveaux:
        print("ÉCHEC : un record cite un paramètre que son runner n'a pas PUBLIÉ (bloc regime) — E8 occ. 4 :")
        for f in nouveaux:
            v = a["records"].get(f, {"statut": "ILLISIBLE", "detail": []})
            print(f"  [NOUVEAU {v['statut']}] {f} : {'; '.join(v['detail'])}")
        print("-> citer le results/*.json SUIVI dont le bloc regime porte la valeur, ou corriger la valeur.")
        return 1
    print(f"OK : {len(fautifs)} record(s) sans régime concordant, tous légataires (baseline). Aucun nouveau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : geler la dette, brancher, muter, compter**

Run: `PYTHONIOENCODING=utf-8 python tools/check_regime_claims.py --report`
Expected: ~43 records hors `OK` listés (les 47 − 4 mesurés le 09-16, à ±2 selon les alias), 0 illisible.
Run: `PYTHONIOENCODING=utf-8 python tools/check_regime_claims.py --update-baseline`
Expected: `baseline gelée : N record(s)`.

Bloc hook, avant `[ "$fail" -ne 0 ]` :

```sh
# 18. REGIME CITE <-> REGIME MESURE (2026-09-16) -- classe E8 occ. 4 : 47 records citent un parametre, 4 un bloc
# regime. Ne tourne que si un record EDR, un results/*.json ou la baseline est stage ; baseline seule -> non scope.
staged_rc=$(git diff --cached --name-only --diff-filter=AM | grep -E '^(docs/EDR/.*\.md|results/.*\.json|tools/regime_claims_baseline\.json)$')
if [ -n "$staged_rc" ]; then
  only_rc=$(echo "$staged_rc" | grep -E '^docs/EDR/' || true)
  if [ -n "$only_rc" ]; then
    PYTHONIOENCODING=utf-8 python tools/check_regime_claims.py --only $only_rc
  else
    PYTHONIOENCODING=utf-8 python tools/check_regime_claims.py
  fi || {
    echo ""
    echo "-> Une valeur de parametre citee n'est pas celle que le runner a PUBLIEE (bloc regime du results cite)."
    echo "   Citer le results/*.json SUIVI qui la porte, ou corriger la prose. Geler EN CONNAISSANCE :"
    echo "   python tools/check_regime_claims.py --update-baseline"
    fail=1
  }
fi

```

`check_gate_mutation.PORTES` :

```python
    "18": {
        "module": "tools.check_regime_claims",
        "titre": "régime cité ↔ régime mesuré (E8 occ. 4)",
        "temoins": ["tests/sandbox/test_regime_claims_gate.py"],
        "mutations": [{
            "nom": "une valeur citée absente du régime publié n'est plus une discordance",
            "avant": '    statut = "DISCORDE" if detail else "CONCORDE"',
            "apres": '    statut = "CONCORDE"',
            "motif": ("le verdict du cliquet — EDR-GRAB-COST tel qu'au 2026-09-09 (forage_payoff = 3.0 jamais mesuré, "
                      "défaut 1.0) passerait pour concordant"),
        }],
    },
```

`CLAUDE.md` : `**19 gardes** <!-- count:portes_hook=19 -->` (si le plan 1 est livré ; sinon 18 — recompter avec `python tools/check_synthesis_counts.py --list`).

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_regime_claims_gate.py tests/sandbox/test_gate_mutation.py tests/sandbox/test_synthesis_counts.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_gate_mutation.py --only 18 && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/check_regime_claims.py`
Expected: tous PASS ; mutation `TUEE` ; porte 12 verte.

- [ ] **Step 5 : commit**

```bash
git add tools/check_regime_claims.py tools/regime_claims_baseline.json tests/sandbox/test_regime_claims_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
git commit -m "feat(porte 18): check_regime_claims -- une valeur de parametre citee par un record doit etre PUBLIEE par le bloc regime d un results/ suivi (E8 occ. 4 ; 47 citent, 4 publient : dette gelee) ; contre-exemple GRAB-COST 09-09, mutation tuee" -- tools/check_regime_claims.py tools/regime_claims_baseline.json tests/sandbox/test_regime_claims_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
```

---

### Task 2 : Porte 19 — `tools/check_evidence_provenance.py`

**Files:**
- Create: `tools/check_evidence_provenance.py`, `tools/evidence_provenance_baseline.json`
- Modify: `tools/hooks/pre-commit` (bloc `# 19.`), `tools/check_gate_mutation.py` (`PORTES["19"]`), `CLAUDE.md` (balise)
- Test: `tests/sandbox/test_evidence_provenance_gate.py`

**Interfaces:**
- Consumes: `tools.check_regime_claims.cited_results`, `tools.check_regime_claims._developper` (Task 1).
- Produces:
  - `publie_par_hash(texte, chemin) -> bool` — `sha256` suivi de 12 à 64 hex dans les 120 caractères après la citation
  - `evaluer(texte, existe, suivi, root) -> {"cites", "absents", "non_suivis", "par_hash", "statut": "OK"|"ABSENT"|"NON_SUIVI"}` — `existe(rel)`, `suivi(rel)` injectés
  - `analyze(root) -> {"records": {file: verdict}, "illisibles": [file]}`
  - `main(argv=None) -> int` — baseline `{"legataires": {file: [chemins]}}` ; exit 1 sur toute paire (record, chemin) HORS baseline absente ou non suivie.
- Mesuré le 2026-09-16 : 69 chemins cités, 20 non suivis, 18 absents — la baseline gèle ces paires.

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_evidence_provenance_gate.py` :

```python
"""Porte 19 : une evidence citee par un record EXISTE et est SUIVIE par git (ou publiee par son hash) —
sinon la conclusion repose sur un fichier que personne ne peut rouvrir (E27, 69/20/18 mesures le 2026-09-16)."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_evidence_provenance as P  # noqa: E402

T = "Résultat (`results/a.json`) puis `results/b_r{1,2}.json` et `results/perdu.json` (sha256 0123456789abcdef)."


def test_evaluer_classe_absents_non_suivis_et_publies_par_hash():
    existe = lambda rel: rel in ("results/a.json", "results/b_r1.json")
    suivi = lambda rel: rel == "results/a.json"
    v = P.evaluer(T, existe, suivi, root=os.getcwd())
    assert v["cites"] == ["results/a.json", "results/b_r1.json", "results/b_r2.json", "results/perdu.json"]
    assert v["absents"] == ["results/b_r2.json"] and v["non_suivis"] == ["results/b_r1.json"]
    assert v["par_hash"] == ["results/perdu.json"] and v["statut"] == "ABSENT"


def test_CONTRE_EXEMPLE_GELE_un_chemin_absent_est_ABSENT_et_un_present_suivi_est_OK():
    assert P.evaluer("(`results/x.json`)", lambda r: False, lambda r: False, root=".")["statut"] == "ABSENT"
    assert P.evaluer("(`results/x.json`)", lambda r: True, lambda r: False, root=".")["statut"] == "NON_SUIVI"
    assert P.evaluer("(`results/x.json`)", lambda r: True, lambda r: True, root=".")["statut"] == "OK"
    assert P.evaluer("rien de cité", lambda r: False, lambda r: False, root=".")["statut"] == "OK"


def test_publie_par_hash_exige_sha256_dans_la_fenetre_apres_la_citation():
    assert P.publie_par_hash("`results/p.json` (sha256 0123456789abcdef)", "results/p.json") is True
    loin = "`results/p.json`" + " x" * 80 + " sha256 0123456789abcdef"          # le hash est a > 120 caracteres : hors fenetre
    assert P.publie_par_hash(loin, "results/p.json") is False
    assert P.publie_par_hash("`results/p.json` (sha256 zz)", "results/p.json") is False


def test_analyze_sur_un_arbre_factice_et_records_illisibles(tmp_path):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("(`results/a.json`)", encoding="utf-8")
    (d / "B.md").write_bytes(b"\xff\xfe\x00 invalide \x80")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "a.json").write_text("{}", encoding="utf-8")
    a = P.analyze(str(tmp_path), suivi=lambda root, rel: False)
    assert a["records"]["docs/EDR/A.md"]["statut"] == "NON_SUIVI" and a["illisibles"] == ["docs/EDR/B.md"]


def test_le_depot_REEL_n_a_aucune_paire_HORS_baseline():
    a = P.analyze(P._ROOT)
    assert sum(len(v["cites"]) for v in a["records"].values()) >= 60, "le périmètre est vide, le test ne prouverait rien"
    base = P._load_baseline()
    hors = {f: sorted(set(v["absents"] + v["non_suivis"]) - set(base.get(f, [])))
            for f, v in a["records"].items() if set(v["absents"] + v["non_suivis"]) - set(base.get(f, []))}
    assert hors == {}, hors


def test_main_ratchet_1_puis_gel_puis_0(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text("(`results/absent.json`)", encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    assert P.main(["--root", str(tmp_path)]) == 1
    assert P.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert P.main(["--root", str(tmp_path)]) == 0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_evidence_provenance_gate.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3 : implémenter**

`tools/check_evidence_provenance.py` :

```python
"""Porte 19 — PROVENANCE DE L'ÉVIDENCE : tout `results/*.json` cité par un record existe ET est suivi par git,
ou est publié par son hash (`sha256 <hex>` à côté de la citation).

  python tools/check_evidence_provenance.py [--report | --update-baseline | --only docs/EDR/X.md]

Mesuré le 2026-09-16 : 69 chemins cités par les EDR, 20 non suivis, 18 absents du disque — gelés ici comme dette.
Une conclusion dont l'évidence n'est plus rouvrable n'est pas réfutable (E27). Illisible = rapporté, jamais OK.
"""
import argparse
import json
import os
import re
import subprocess
import sys

from tools.check_regime_claims import _developper, cited_results

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "evidence_provenance_baseline.json")
_HASH = re.compile(r"sha256[:\s]+([0-9a-f]{12,64})")
FENETRE = 120


def publie_par_hash(texte, chemin):
    i = texte.find(chemin)
    while i != -1:
        if _HASH.search(texte[i + len(chemin): i + len(chemin) + FENETRE]):
            return True
        i = texte.find(chemin, i + 1)
    return False


def evaluer(texte, existe, suivi, root):
    cites = sorted({c for motif in cited_results(texte) for c in _developper(root, motif)})
    par_hash = [c for c in cites if publie_par_hash(texte, c)]
    absents = [c for c in cites if c not in par_hash and not existe(c)]
    non_suivis = [c for c in cites if c not in par_hash and existe(c) and not suivi(c)]
    statut = "ABSENT" if absents else ("NON_SUIVI" if non_suivis else "OK")
    return {"cites": cites, "absents": absents, "non_suivis": non_suivis, "par_hash": par_hash, "statut": statut}


def _tracked(root, rel):
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True).returncode == 0


def analyze(root=_ROOT, suivi=None):
    suivi = _tracked if suivi is None else suivi
    out, illisibles = {}, []
    d = os.path.join(root, "docs", "EDR")
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".md"):
            continue
        rel = f"docs/EDR/{name}"
        try:
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                texte = fh.read()
        except (OSError, UnicodeDecodeError):
            illisibles.append(rel)
            continue
        out[rel] = evaluer(texte, lambda c: os.path.exists(os.path.join(root, c)), lambda c: suivi(root, c), root)
    return {"records": out, "illisibles": illisibles}


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh).get("legataires", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
    a = analyze(args.root)
    fautes = {f: sorted(set(v["absents"] + v["non_suivis"])) for f, v in a["records"].items() if v["statut"] != "OK"}
    for f in a["illisibles"]:
        print(f"  [ILLISIBLE, non compté] {f}")
    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Paires (record, results/ cite) ABSENT ou NON SUIVI, gelees comme dette legataire (E27). "
                                   "Aucune NOUVELLE (tools/check_evidence_provenance.py).", "legataires": fautes},
                      fh, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline gelée : {sum(len(v) for v in fautes.values())} chemin(s) dans {len(fautes)} record(s)")
        return 0
    n_cites = sum(len(v["cites"]) for v in a["records"].values())
    print(f"records : {len(a['records'])} | chemins cités : {n_cites} | records fautifs : {len(fautes)}")
    if args.report:
        for f, ch in sorted(fautes.items()):
            print(f"  [{a['records'][f]['statut']}] {f} : {', '.join(ch)}")
        return 0
    base = _load_baseline()
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}
    nouveaux = {f: [c for c in ch if c not in set(base.get(f, []))] for f, ch in fautes.items() if only is None or f in only}
    nouveaux = {f: ch for f, ch in nouveaux.items() if ch}
    for i in a["illisibles"]:
        if only is None or i in only:
            nouveaux[i] = ["(record illisible)"]
    if nouveaux:
        print("ÉCHEC : un record cite une évidence absente ou non suivie par git — personne ne pourra la rouvrir (E27) :")
        for f, ch in sorted(nouveaux.items()):
            print(f"  [NOUVEAU] {f} : {', '.join(ch)}")
        print("-> git add le results/*.json, ou publier son sha256 à côté de la citation, ou corriger le chemin.")
        return 1
    print(f"OK : {sum(len(v) for v in fautes.values())} chemin(s) légataire(s) gelé(s). Aucun nouveau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : geler, brancher, muter, compter**

Run: `PYTHONIOENCODING=utf-8 python tools/check_evidence_provenance.py --report` puis `--update-baseline`
Expected: ~38 chemins (20 non suivis + 18 absents) dans la baseline.

Bloc hook :

```sh
# 19. PROVENANCE DE L'EVIDENCE (2026-09-16) -- classe E27 : 69 chemins results/ cites par les EDR, 20 non suivis,
# 18 absents. Un record EDR, un results/*.json ou la baseline stage declenche ; baseline seule -> non scope.
staged_ep=$(git diff --cached --name-only --diff-filter=AMD | grep -E '^(docs/EDR/.*\.md|results/.*\.json|tools/evidence_provenance_baseline\.json)$')
if [ -n "$staged_ep" ]; then
  only_ep=$(echo "$staged_ep" | grep -E '^docs/EDR/' || true)
  if [ -n "$only_ep" ]; then
    PYTHONIOENCODING=utf-8 python tools/check_evidence_provenance.py --only $only_ep
  else
    PYTHONIOENCODING=utf-8 python tools/check_evidence_provenance.py
  fi || {
    echo ""
    echo "-> Un record cite une evidence ABSENTE ou NON SUIVIE : git add le results/*.json, ou publier son sha256"
    echo "   a cote de la citation. Geler EN CONNAISSANCE : python tools/check_evidence_provenance.py --update-baseline"
    fail=1
  }
fi

```

`PORTES["19"]` :

```python
    "19": {
        "module": "tools.check_evidence_provenance",
        "titre": "provenance de l'évidence citée (E27)",
        "temoins": ["tests/sandbox/test_evidence_provenance_gate.py"],
        "mutations": [{
            "nom": "une évidence absente ou non suivie est toujours OK",
            "avant": '    statut = "ABSENT" if absents else ("NON_SUIVI" if non_suivis else "OK")',
            "apres": '    statut = "OK"',
            "motif": "le verdict du cliquet — les 18 chemins absents et 20 non suivis passeraient, et tout nouveau aussi",
        }],
    },
```

`CLAUDE.md` : balise `portes_hook` +1.

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_evidence_provenance_gate.py tests/sandbox/test_gate_mutation.py tests/sandbox/test_synthesis_counts.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_gate_mutation.py --only 19 && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/check_evidence_provenance.py`
Expected: PASS ; `TUEE` ; porte 12 verte.

- [ ] **Step 5 : commit**

```bash
git add tools/check_evidence_provenance.py tools/evidence_provenance_baseline.json tests/sandbox/test_evidence_provenance_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
git commit -m "feat(porte 19): check_evidence_provenance -- tout results/ cite par un record existe et est suivi par git ou publie par sha256 (E27 ; 69/20/18 mesures, dette gelee) ; mutation tuee" -- tools/check_evidence_provenance.py tools/evidence_provenance_baseline.json tests/sandbox/test_evidence_provenance_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
```

---

### Task 3 : Porte 20 — `tools/check_e19_optimizer_sweep.py`

**Files:**
- Create: `tools/check_e19_optimizer_sweep.py`, `tools/e19_sweep_baseline.json`
- Modify: `tools/hooks/pre-commit` (bloc `# 20.`), `tools/check_gate_mutation.py` (`PORTES["20"]`), `CLAUDE.md`
- Test: `tests/sandbox/test_e19_sweep_gate.py`

**Interfaces:**
- Consumes: `tools.check_control_family._sources()` (générateur `(chemin, source)`), `tools.check_control_family._HORS_PERIMETRE`.
- Produces:
  - `noms_regles(arbre) -> {"resolus": [str], "non_resolus": [str]}` — arguments des appels `verify(...)` : `Constant` → nom ; `Name` → assignation module-level à une constante ; `IfExp` → les deux branches ; sinon `non_resolus` (rapporté, jamais deviné : les runners `--regle argv`)
  - `sous_gradient(rule) -> (bool, str)` — vrai si `cellule.lr` liste ≥ 2 valeurs, ou `cellule.bras` dict ≥ 2 valeurs, ou `cellules[*].lr` ≥ 2 valeurs distinctes, ou `clause_E19` présente, ou `sender_lr` présente
  - `appelle_garde(arbre) -> bool` — un `ast.Call` nommé `assert_verdict_invariant_to_optimizer`
  - `etat(sources, regles) -> dict[path, {"regles", "non_resolus", "sous_gradient", "raison", "garde"}]` — `regles: dict[nom -> rule]` injecté
  - `runners_nus(etat) -> list[path]` — VERDICT : `sous_gradient` et pas `garde`
  - `main(argv=None) -> int` — baseline `{"runners_nus": [...]}` ; exit 1 sur tout NOUVEAU nu ; les non résolus sont IMPRIMÉS, jamais comptés nus.

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_e19_sweep_gate.py` :

```python
"""Porte 20 : un runner scelle qui compare des bras SOUS GRADIENT appelle la garde E19 — un nul a pas fixe s'est
deja retourne (RETAIN-COMPOSE 0,173 -> 0,923 au seul lr) ; la garde existe et n'a qu'UN appelant sur 11."""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_e19_optimizer_sweep as E  # noqa: E402

NU = '''
from tools.preregister import verify
RULE = "LEGACY-LR-CURVE-R2"
def main():
    regle = verify(RULE)
'''
GARDE = NU + '''
    from tools.experiment_preflight import assert_verdict_invariant_to_optimizer
    assert_verdict_invariant_to_optimizer(lambda lr: (0.1, 0.5), lrs=(0.04, 0.004))
'''
ARGV = '''
from tools.preregister import verify
def main(argv):
    nom = argv[argv.index("--regle") + 1]
    regle = verify(nom)
'''
IFEXP = '''
from tools import preregister
SMOKE = False
rule = preregister.verify("EVO-028-SMOKE" if SMOKE else "EVO-028")
'''
REGLES = {"LEGACY-LR-CURVE-R2": {"cellule": {"lr": [0.0, 0.04, 0.004]}},
          "EVO-028": {"arms": {"a": "x", "b": "y"}},
          "EVO-028-SMOKE": {"design": "smoke"},
          "LOCK": {"cellules": [{"lr": 0.0005, "episodes": 14400}, {"lr": 0.002, "episodes": 1600}]},
          "COORD": {"sender_lr": 0.05}, "CLAUSE": {"clause_E19": "..."}}


def test_noms_regles_resout_constante_nom_de_module_et_ifexp_et_RAPPORTE_argv():
    assert E.noms_regles(ast.parse(NU)) == {"resolus": ["LEGACY-LR-CURVE-R2"], "non_resolus": []}
    assert E.noms_regles(ast.parse(IFEXP))["resolus"] == ["EVO-028", "EVO-028-SMOKE"]
    r = E.noms_regles(ast.parse(ARGV))
    assert r["resolus"] == [] and len(r["non_resolus"]) == 1


def test_sous_gradient_reconnait_les_cinq_formes_et_pas_une_comparaison_evolutive():
    assert E.sous_gradient(REGLES["LEGACY-LR-CURVE-R2"])[0] is True
    assert E.sous_gradient(REGLES["LOCK"])[0] is True and E.sous_gradient(REGLES["COORD"])[0] is True
    assert E.sous_gradient(REGLES["CLAUSE"])[0] is True
    assert E.sous_gradient({"cellule": {"bras": {"lr0_reference": 0.0, "natural": None}}})[0] is True
    assert E.sous_gradient(REGLES["EVO-028"])[0] is False
    assert E.sous_gradient({"cellule": {"lr": [0.04]}})[0] is False                   # un seul pas : rien à balayer


def test_CONTRE_EXEMPLE_GELE_un_runner_sous_gradient_SANS_garde_est_NU_et_avec_garde_ne_l_est_pas():
    et = E.etat([("tools/a.py", NU), ("tools/b.py", GARDE)], REGLES)
    assert E.runners_nus(et) == ["tools/a.py"]
    assert et["tools/b.py"]["garde"] is True and et["tools/b.py"]["sous_gradient"] is True


def test_un_runner_evolutif_n_est_pas_concerne_et_un_argv_est_rapporte_non_resolu():
    et = E.etat([("tools/e.py", IFEXP), ("tools/f.py", ARGV)], REGLES)
    assert et["tools/e.py"]["sous_gradient"] is False and E.runners_nus(et) == []
    assert et["tools/f.py"]["non_resolus"] and et["tools/f.py"]["regles"] == []


def test_le_depot_REEL_n_a_aucun_runner_nu_HORS_baseline():
    et = E.etat(list(E._sources()), E.charger_regles(E._ROOT))
    assert len(et) >= 15, "le périmètre est vide, le test ne prouverait rien"
    assert sorted(set(E.runners_nus(et)) - set(E._load_baseline())) == []


def test_main_1_puis_gel_puis_0(tmp_path, monkeypatch):
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"runners_nus": []}), encoding="utf-8")
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/a.py", NU)])
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main([]) == 1
    assert E.main(["--update-baseline"]) == 0
    assert E.main([]) == 0
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_e19_sweep_gate.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3 : implémenter**

`tools/check_e19_optimizer_sweep.py` :

```python
"""Porte 20 — GARDE E19 APPELÉE : un runner SCELLÉ dont la règle compare des bras SOUS GRADIENT (grille de `lr`,
bras à pas distincts, `clause_E19`) appelle `assert_verdict_invariant_to_optimizer`, sinon son nul mesure le RÉGLAGE.

  python tools/check_e19_optimizer_sweep.py [--report | --update-baseline | --only tools/x.py]

Mesuré le 2026-09-16 : la garde a UN appelant de production pour 11 points d'entrée d'apprentissage ; aucun des
23 runners scellés ne l'appelle ; E19 vit en PROSE (`clause_E19`, 7 règles). Même forme que la porte 11 : AST, pas
regex ; un nom de règle NON RÉSOLU (argv) est rapporté, jamais deviné.
"""
import argparse
import ast
import glob
import json
import os
import sys

from tools.check_control_family import _HORS_PERIMETRE, _sources  # noqa: F401 — réutilisés tels quels

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "e19_sweep_baseline.json")
GARDE = "assert_verdict_invariant_to_optimizer"


def _constantes_module(arbre):
    out = {}
    for n in arbre.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            out[n.targets[0].id] = n.value.value
    return out


def _resoudre(node, consts):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value], []
    if isinstance(node, ast.Name) and node.id in consts:
        return [consts[node.id]], []
    if isinstance(node, ast.IfExp):
        a, na = _resoudre(node.body, consts)
        b, nb = _resoudre(node.orelse, consts)
        return a + b, na + nb
    return [], [ast.dump(node)[:80]]


def noms_regles(arbre):
    consts = _constantes_module(arbre)
    resolus, non = [], []
    for n in ast.walk(arbre):
        if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == "verify" and n.args:
            r, nr = _resoudre(n.args[0], consts)
            resolus += r
            non += nr
    return {"resolus": sorted(set(resolus)), "non_resolus": non}


def _nb_valeurs(v):
    if isinstance(v, list):
        return len({str(x) for x in v})
    if isinstance(v, dict):
        return len(v)
    return 0


def sous_gradient(rule):
    if not isinstance(rule, dict):
        return False, "règle illisible"
    if "clause_E19" in rule:
        return True, "clause_E19 déclarée"
    if "sender_lr" in rule:
        return True, "sender_lr"
    cel = rule.get("cellule") if isinstance(rule.get("cellule"), dict) else {}
    if _nb_valeurs(cel.get("lr")) >= 2:
        return True, f"cellule.lr à {_nb_valeurs(cel.get('lr'))} pas"
    if _nb_valeurs(cel.get("bras")) >= 2:
        return True, f"cellule.bras à {_nb_valeurs(cel.get('bras'))} bras"
    cells = rule.get("cellules") if isinstance(rule.get("cellules"), list) else []
    lrs = {str(c.get("lr")) for c in cells if isinstance(c, dict) and "lr" in c}
    if len(lrs) >= 2:
        return True, f"cellules à {len(lrs)} pas distincts"
    return False, "aucune grille de pas"


def appelle_garde(arbre):
    return any(isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == GARDE
               for n in ast.walk(arbre))


def charger_regles(root=_ROOT):
    out = {}
    for p in glob.glob(os.path.join(root, "docs", "preregistrations", "*.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                out[os.path.splitext(os.path.basename(p))[0]] = json.load(fh).get("rule", {})
        except (OSError, ValueError):
            out[os.path.splitext(os.path.basename(p))[0]] = None
    return out


def etat(sources, regles):
    out = {}
    for path, src in sources:
        if path in _HORS_PERIMETRE:
            continue
        try:
            arbre = ast.parse(src)
        except SyntaxError:
            continue
        noms = noms_regles(arbre)
        if not noms["resolus"] and not noms["non_resolus"]:
            continue                                            # pas un runner scellé
        sg, raisons = False, []
        for nom in noms["resolus"]:
            ok, r = sous_gradient(regles.get(nom))
            if ok:
                sg = True
                raisons.append(f"{nom} : {r}")
        out[path] = {"regles": noms["resolus"], "non_resolus": noms["non_resolus"], "sous_gradient": sg,
                     "raison": " ; ".join(raisons), "garde": appelle_garde(arbre)}
    return out


def runners_nus(etat_):
    """VERDICT du cliquet : les runners sous gradient qui n'appellent pas la garde. Jamais un booléen."""
    return sorted(p for p, v in etat_.items() if v["sous_gradient"] and not v["garde"])


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return []
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh).get("runners_nus", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args(argv)
    et = etat(list(_sources()), charger_regles(_ROOT))
    nus = runners_nus(et)
    non_res = {p: v["non_resolus"] for p, v in et.items() if v["non_resolus"]}
    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Runners scelles sous gradient SANS assert_verdict_invariant_to_optimizer (E19). "
                                   "Dette legataire GELEE : aucun NOUVEAU. tools/check_e19_optimizer_sweep.py",
                       "runners_nus": nus}, fh, indent=1, sort_keys=True)
        print(f"baseline gelée : {len(nus)} runner(s) nu(s)")
        return 0
    print(f"runners scellés : {len(et)} | sous gradient : {sum(1 for v in et.values() if v['sous_gradient'])} | "
          f"nus : {len(nus)} | règle non résolue (rapportée, jamais devinée) : {len(non_res)}")
    for p, nr in sorted(non_res.items()):
        print(f"  [NON RÉSOLU] {p} : {nr[0]}")
    if args.report:
        for p in nus:
            print(f"  [nu] {p} : {et[p]['raison']}")
        return 0
    base = set(_load_baseline())
    nouveaux = [p for p in nus if p not in base]
    if args.only is not None:
        vises = {os.path.relpath(os.path.abspath(o), _ROOT).replace("\\", "/") for o in args.only}
        nouveaux = [p for p in nouveaux if p in vises]
    if nouveaux:
        print("ÉCHEC : ce runner compare des bras SOUS GRADIENT sans appeler la garde E19 — son nul mesurera le pas :")
        for p in nouveaux:
            print(f"  [NOUVEAU] {p} : {et[p]['raison']}")
        print(f"-> appeler {GARDE}(measure, lrs=...) (tools/experiment_preflight.py:303), ou geler : --update-baseline")
        return 1
    print("OK : aucun nouveau runner sous gradient sans garde E19.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : geler, brancher, muter, compter**

Run: `PYTHONIOENCODING=utf-8 python tools/check_e19_optimizer_sweep.py --report` puis `--update-baseline`
Expected: les runners LEGACY-LR-CURVE, BILINEAR-ALIGNED, LOCK-001 et DELAYED-COORD apparaissent nus (attendu : 0/23 appelants) ; les deux `lock001_*` sont `[NON RÉSOLU]` (argv) et ne sont PAS comptés nus.

Bloc hook :

```sh
# 20. GARDE E19 APPELEE (2026-09-16) -- un runner scelle a bras sous gradient appelle
# assert_verdict_invariant_to_optimizer (RETAIN-COMPOSE : 0,173 -> 0,923 au seul lr). Meme perimetre que la porte 11.
staged_e19=$(git diff --cached --name-only --diff-filter=AM | grep -E '^((tools|src/seed_ai)/.*\.py|docs/preregistrations/.*\.json|tools/e19_sweep_baseline\.json)$')
if [ -n "$staged_e19" ]; then
  only_e19=$(echo "$staged_e19" | grep -E '\.py$' || true)
  if [ -n "$only_e19" ]; then
    PYTHONIOENCODING=utf-8 python tools/check_e19_optimizer_sweep.py --only $only_e19
  else
    PYTHONIOENCODING=utf-8 python tools/check_e19_optimizer_sweep.py
  fi || {
    echo ""
    echo "-> Ce runner compare des bras sous GRADIENT sans balayer le pas : son nul mesure le reglage (E19)."
    echo "   Appeler assert_verdict_invariant_to_optimizer(measure, lrs=...) ou geler : --update-baseline"
    fail=1
  }
fi

```

`PORTES["20"]` :

```python
    "20": {
        "module": "tools.check_e19_optimizer_sweep",
        "titre": "garde E19 appelée par tout runner scellé sous gradient",
        "temoins": ["tests/sandbox/test_e19_sweep_gate.py"],
        "mutations": [{
            "nom": "un runner sous gradient sans garde n'est plus nu",
            "avant": '    return sorted(p for p, v in etat_.items() if v["sous_gradient"] and not v["garde"])',
            "apres": "    return []",
            "motif": "le verdict du cliquet — les runners de la série LEGACY/LOCK repasseraient sans balayage du pas",
        }],
    },
```

`CLAUDE.md` : balise `portes_hook` +1 (21 si les plans 1 et 2 sont livrés).

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_e19_sweep_gate.py tests/sandbox/test_gate_mutation.py tests/sandbox/test_synthesis_counts.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_gate_mutation.py --only 20`
Expected: PASS ; `TUEE`.

- [ ] **Step 5 : commit**

```bash
git add tools/check_e19_optimizer_sweep.py tools/e19_sweep_baseline.json tests/sandbox/test_e19_sweep_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
git commit -m "feat(porte 20): check_e19_optimizer_sweep -- un runner scelle a bras sous gradient appelle assert_verdict_invariant_to_optimizer (E19 : 0/23 aujourd hui, dette gelee ; argv rapporte non resolu, jamais devine) ; mutation tuee" -- tools/check_e19_optimizer_sweep.py tools/e19_sweep_baseline.json tests/sandbox/test_e19_sweep_gate.py tools/hooks/pre-commit tools/check_gate_mutation.py CLAUDE.md
```

---

### Task 4 : `review:` — lu par le parseur, exigé des NOUVEAUX records à verdict (porte 1 étendue)

**Files:**
- Modify: `tools/consolidate_records.py` (`_empty_record`, l.37-46 : ajouter `"review": None`)
- Modify: `tools/check_record_links.py` (`analyze` l.96-129 ; payload `--update-baseline` l.153-161 ; ratchet + `--only` l.197-213 ; condition et lignes de sortie l.185-233)
- Modify: `tools/record_link_baseline.json` (re-gel), `tools/check_gate_mutation.py` (`PORTES["1"]`, 2ᵉ mutation)
- Create: `docs/reviews/README.md`
- Test: `tests/sandbox/test_record_graph_completeness.py` (ajouts)

**Interfaces:**
- Produces: `analyze(root)["review_missing"] -> [{id, file}]` — EDR portant `gate:` (G0-G4 ou foundational) OU `tests: [SDR-Gx]` et sans `review:` ; baseline `review_missing_files` ; ligne `[NOUVEAU RECORD SANS REVUE]` ; la valeur de `review:` est un CHEMIN `docs/reviews/<AAAA-MM-JJ>-<slug>.md` (jamais un id de record : `edge_key_silences` traiterait `EDR-…` comme une arête non lue).

- [ ] **Step 1 : écrire les tests (ajout à `tests/sandbox/test_record_graph_completeness.py`)**

```python
def test_a_NEW_edr_with_a_gate_but_no_review_is_review_missing(tmp_path):
    """CONTRE-EXEMPLE GELÉ de la porte 1 étendue (spec PM 2026-09-16 §3.5) : un record à verdict sans revue."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\ntests: [SDR-G0]")
    assert any(r["id"] == "EDR-999" for r in C.analyze(root)["review_missing"])


def test_an_edr_with_a_review_path_is_NOT_review_missing(tmp_path):
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: docs/reviews/2026-09-17-edr-999.md")
    assert not any(r["id"] == "EDR-999" for r in C.analyze(root)["review_missing"])


def test_an_edr_WITHOUT_verdict_anchor_is_not_asked_for_a_review(tmp_path):
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nadopts: [REF-DEMAND-MARKER]")
    assert not any(r["id"] == "EDR-999" for r in C.analyze(root)["review_missing"])


def test_the_review_key_is_READ_by_the_schema_not_silenced(tmp_path):
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: docs/reviews/2026-09-17-edr-999.md")
    sil = C.edge_key_silences(root)
    assert not any(k == "review" for _, k in sil["non_lues"])
    rec = [r for r in scan_records(root) if r["id"] == "EDR-999"][0]
    assert rec["review"] == "docs/reviews/2026-09-17-edr-999.md"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_record_graph_completeness.py -q -p no:cacheprovider -k review`
Expected: 4 FAILED (`KeyError: 'review_missing'`, `rec["review"]` absent).

- [ ] **Step 3 : implémenter**

`tools/consolidate_records.py`, dans `_empty_record`, après `"verdict": None,` :

```python
            "review": None,                 # chemin docs/reviews/<date>-<slug>.md (spec PM 2026-09-16 §3.5)
```

`tools/check_record_links.py`, dans `analyze`, remplacer `orphans, gate_unlinked, gate_tests_mismatch = [], [], []` par :

```python
    orphans, gate_unlinked, gate_tests_mismatch, review_missing = [], [], [], []
```

et ajouter dans la boucle, après le bloc `gate_tests_mismatch` :

```python
        if r["type"] == "EDR" and (has_gate or tests_sdr) and not r.get("review"):
            review_missing.append({"id": r["id"], "file": r["file"]})
```

et dans le `return` : `"review_missing": review_missing,`.

Dans `main` : payload `--update-baseline` gagne `"review_missing_files": sorted(m["file"] for m in st["review_missing"]),` ; après `new_gu = …` :

```python
    base_rv = set(base.get("review_missing_files", []))
    new_rv = [m for m in st["review_missing"] if m["file"] not in base_rv]
```

dans le filtre `--only` : `new_rv = [m for m in new_rv if m["file"] in only]` ; la condition `if not new_orph and not new_coll and not new_mism and not new_gu:` devient `… and not new_gu and not new_rv:` ; la ligne `OK :` gagne `/ {len(st['review_missing'])} sans revue` ; et après la ligne `[NOUVEL EDR NON RACCORDÉ À UNE PORTE]` :

```python
    for m in new_rv:   print(f"  [NOUVEAU RECORD SANS REVUE] {m['id']}  ({m['file']}) — ajoute review: docs/reviews/<date>-<slug>.md (revue adversariale à sondes propres, REF-REVUE-ADVERSARIALE)")
```

Le mode `--report` gagne ` sans_revue={len(st['review_missing'])}` sur sa première ligne.

`docs/reviews/README.md` :

```markdown
# Revues adversariales à sondes propres

Un fichier par revue : `docs/reviews/<AAAA-MM-JJ>-<slug-du-record>.md`, référencé par le frontmatter `review:` du record
(exigé de tout NOUVEAU record à `gate:`/`tests:` par `tools/check_record_links.py`). Writer : la session qui a lancé la
revue. Forme : en-tête (cible, SHA, date, résultat des TÉMOINS), puis une section par prompt `P1`…`P10` de
`docs/REF/REF-REVUE-ADVERSARIALE.md` avec **Sonde** (commande rejouable) / **Constat** / **Classe** (Ex) / **Verdict**
(confirmé, non confirmé, hors périmètre). Une revue dont la phase témoins a rendu NUL ne s'écrit pas.
```

`check_gate_mutation.PORTES["1"]["mutations"]` : ajouter un second dict :

```python
        }, {
            "nom": "un record à verdict SANS revue n'est plus signalé",
            "avant": '        if r["type"] == "EDR" and (has_gate or tests_sdr) and not r.get("review"):',
            "apres": "        if False:",
            "motif": "l'exigence de revue (spec PM 2026-09-16) — la règle documentée depuis le 07-21 et appliquée 1 fois sur 28 redeviendrait décorative",
        }],
```

- [ ] **Step 4 : re-geler la baseline, lancer témoins, mutation, porte 8**

Run: `PYTHONIOENCODING=utf-8 python tools/check_record_links.py --update-baseline`
Expected: `review_missing_files` gelée (≈ 262 records légataires). `git diff --stat tools/record_link_baseline.json` : uniquement des AJOUTS — si une liste existante a changé de longueur, ARRÊTER et comprendre (E22).
Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_record_graph_completeness.py tests/sandbox/test_gate_mutation.py tests/sandbox/test_synthesis_counts.py -q -p no:cacheprovider && PYTHONIOENCODING=utf-8 python tools/check_gate_mutation.py --only 1 && PYTHONIOENCODING=utf-8 python tools/check_record_links.py`
Expected: PASS ; deux mutations `TUEE` ; `OK : … Aucun nouveau.`

- [ ] **Step 5 : commit**

```bash
git add tools/consolidate_records.py tools/check_record_links.py tools/record_link_baseline.json tools/check_gate_mutation.py docs/reviews/README.md tests/sandbox/test_record_graph_completeness.py
git commit -m "feat(porte 1): review: lu par le schema et exige de tout NOUVEAU record a gate:/tests: (revue adversariale obligatoire depuis le 07-21, appliquee 1/28) ; 262 legataires geles ; 2e mutation tuee ; docs/reviews/" -- tools/consolidate_records.py tools/check_record_links.py tools/record_link_baseline.json tools/check_gate_mutation.py docs/reviews/README.md tests/sandbox/test_record_graph_completeness.py
```

---

### Task 5 : `reviewed_by` — enveloppe des NOUVELLES pré-inscriptions qui déclarent un coût

**Files:**
- Modify: `tools/preregister.py` (`preregister`, l.93-111 ; exceptions l.40-49)
- Test: `tests/sandbox/test_preregistration_guard.py` (ajouts)

**Interfaces:**
- Produces: `preregister(name, rule, *, _dir=None, reviewed_by=None) -> str` ; `ReviewRequired(RuntimeError)` ; `declare_un_cout(rule) -> bool` (clés `cout`, `budget_s`, `garde_cout`, `plafond`, `cout_scelle`). La clé `reviewed_by` est à l'ENVELOPPE (hors sceau, comme `record` P2.28) : les 58 règles existantes restent valides et re-scellables à l'identique ; `verify()` inchangé.
- Décision consignée : le « seuil de coût » de la spec est remplacé par « la règle DÉCLARE un coût » — aucun champ de coût numérique homogène n'existe (4 `budget_s` entiers, 24 `cout` en prose), donc un seuil serait deviné.

- [ ] **Step 1 : écrire les tests (ajout à `tests/sandbox/test_preregistration_guard.py`)**

```python
def test_une_NOUVELLE_regle_qui_declare_un_cout_exige_reviewed_by(tmp_path):
    from tools import preregister as PR
    rule = {"question": "q", "cout": "~40 min sous bail", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    with pytest.raises(PR.ReviewRequired, match="reviewed_by"):
        PR.preregister("T-COUT", rule, _dir=str(tmp_path))
    p = PR.preregister("T-COUT", rule, _dir=str(tmp_path), reviewed_by="docs/reviews/2026-09-17-t-cout.md")
    import json
    env = json.load(open(p, encoding="utf-8"))
    assert env["reviewed_by"] == "docs/reviews/2026-09-17-t-cout.md" and set(env) == {"name", "rule", "seal", "reviewed_by"}
    assert PR.verify("T-COUT", _dir=str(tmp_path)) == rule                      # le sceau ne porte que rule


def test_une_regle_SANS_cout_declare_ne_l_exige_pas_et_une_existante_se_rescelle_sans(tmp_path):
    from tools import preregister as PR
    rule = {"question": "q", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    PR.preregister("T-LIBRE", rule, _dir=str(tmp_path))                          # pas de coût : pas de revue exigée
    couteuse = {"question": "q", "budget_s": 3600, "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    PR.preregister("T-EXIST", couteuse, _dir=str(tmp_path), reviewed_by="x")
    PR.preregister("T-EXIST", couteuse, _dir=str(tmp_path))                     # identique : idempotent, sans reviewed_by
    assert PR.declare_un_cout(couteuse) is True and PR.declare_un_cout(rule) is False
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_preregistration_guard.py -q -p no:cacheprovider -k reviewed`
Expected: 2 FAILED (`AttributeError: ReviewRequired`).

- [ ] **Step 3 : implémenter**

Dans `tools/preregister.py`, après les exceptions existantes :

```python
class ReviewRequired(RuntimeError):
    """Une NOUVELLE règle qui déclare un coût n'est scellée qu'après la revue adversariale (spec PM 2026-09-16 §2.3)."""


_CLES_COUT = ("cout", "budget_s", "garde_cout", "plafond", "cout_scelle")


def declare_un_cout(rule: dict) -> bool:
    return isinstance(rule, dict) and any(k in rule for k in _CLES_COUT)
```

et remplacer la signature et le corps de `preregister` :

```python
def preregister(name: str, rule: dict, *, _dir=None, reviewed_by=None) -> str:
    """Scelle `rule` sous `name`. Idempotent à contenu IDENTIQUE ; lève si le contenu DIFFÈRE.
    `reviewed_by` (chemin docs/reviews/…) est écrit à l'ENVELOPPE, hors sceau : exigé d'une NOUVELLE règle qui
    déclare un coût, jamais d'une règle existante re-scellée à l'identique."""
    _assert_exhaustive(rule)
    d = _dir or _DIR
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.json")
    payload = {"name": name, "rule": rule, "seal": _seal(rule)}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("seal") != payload["seal"]:
            raise PreregistrationConflict(
                f"« {name} » est déjà scellée avec un contenu DIFFÉRENT : une règle ne se réécrit pas, on en scelle une -bis")
        return p
    if declare_un_cout(rule) and not reviewed_by:
        raise ReviewRequired(f"« {name} » déclare un coût ({', '.join(k for k in _CLES_COUT if k in rule)}) : "
                             "passer reviewed_by=<docs/reviews/…> — la revue adversariale précède le sceau (E8/E19)")
    if reviewed_by:
        payload["reviewed_by"] = reviewed_by
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
    return p
```

(Conserver le message exact de `PreregistrationConflict` tel qu'il est dans le fichier — le recopier, ne pas le réécrire.)

- [ ] **Step 4 : lancer TOUTE la garde de pré-inscription**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_preregistration_guard.py tests/sandbox/test_control_family.py -q -p no:cacheprovider`
Expected: tous PASS (dont le test qui re-vérifie les 58 règles du dépôt).

- [ ] **Step 5 : commit**

```bash
git add tools/preregister.py tests/sandbox/test_preregistration_guard.py
git commit -m "feat(preregister): reviewed_by a l enveloppe (hors sceau) exige de toute NOUVELLE regle qui declare un cout ; les 58 regles existantes inchangees" -- tools/preregister.py tests/sandbox/test_preregistration_guard.py
```

---

### Task 6 : Le Réfutateur — prompts figés, témoins gelés, workflow

**Files:**
- Create: `docs/REF/REF-REVUE-ADVERSARIALE.md`, `tools/refutateur_temoins.json`, `tools/refutateur_temoins.py`, `.claude/workflows/refutateur.js`
- Test: `tests/sandbox/test_refutateur_temoins.py`

**Interfaces:**
- `refutateur_temoins.charger() -> list[dict]` — `{nom, sha, chemin, attendu (regex), genre: "defaut"|"noop"}`
- `refutateur_temoins.extraire(temoin, dest) -> str` — `git show <sha>:<chemin>` écrit dans `dest/<nom>.md`
- `refutateur_temoins.verifier(temoin, texte_critiques) -> bool` — `genre=defaut` : `re.search(attendu)` ; `genre=noop` : au plus 1 critique
- `refutateur_temoins.main(argv)` — `--extraire <dir>` ; `--verifier <nom> <fichier>` ; exit 0/1

- [ ] **Step 1 : trouver les SHA des témoins (faits, pas devinés)**

Run, depuis la racine :

```bash
git log --format=%H --before=2026-09-10 -- "docs/EDR/EDR-GRAB-COST_*.md" | head -1
git log --format=%H --reverse -- "docs/EDR/S2-BLIND-CHAMPION*.md" | head -1
git log --format=%H --before=2026-08-15 -- "docs/EDR/*RETAIN_COMPOSE*.md" "docs/EDR/*RETAIN-COMPOSE*.md" | head -1
git log --format=%H -1 -- "docs/EDR/LOCK-002_*.md"
```

Pour chacun : `git show <sha> --stat -- docs/EDR | head` et vérifier À L'ŒIL que la version contient bien le défaut connu (GRAB-COST : `forage_payoff = 3.0` sans la rectification ; S2-BLIND v1 : la phrase de régime jamais mesurée ; RETAIN-COMPOSE : le verdict RETENTION avant `EDR-RETAIN-COMPOSE-LR`). Si un chemin ne rend rien, `git log --all --oneline --name-only | grep -i <fragment>` pour trouver le nom exact — et RAPPORTER ce qui n'a pas été trouvé plutôt que substituer un autre record.

- [ ] **Step 2 : écrire le test**

Créer `tests/sandbox/test_refutateur_temoins.py` :

```python
"""Les temoins du Refutateur existent dans l'histoire git a leur SHA, leurs regex compilent, l'extraction marche."""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import refutateur_temoins as T  # noqa: E402


def test_trois_temoins_a_defaut_et_un_noop_tous_presents_dans_git():
    tem = T.charger()
    assert sum(1 for t in tem if t["genre"] == "defaut") == 3 and sum(1 for t in tem if t["genre"] == "noop") == 1
    for t in tem:
        assert re.fullmatch(r"[0-9a-f]{40}", t["sha"]), t
        p = subprocess.run(["git", "cat-file", "-e", f"{t['sha']}:{t['chemin']}"], cwd=T._ROOT, capture_output=True)
        assert p.returncode == 0, f"{t['nom']} : {t['sha']}:{t['chemin']} absent de git"
        re.compile(t["attendu"])


def test_extraire_ecrit_la_version_GELEE_et_le_temoin_GRAB_COST_porte_encore_la_valeur_fausse(tmp_path):
    grab = [t for t in T.charger() if t["nom"] == "GRAB-COST-v09-09"][0]
    p = T.extraire(grab, str(tmp_path))
    txt = open(p, encoding="utf-8").read()
    assert "forage_payoff = 3.0" in txt and "défaut" not in txt.split("forage_payoff = 3.0")[0][-200:]


def test_verifier_accepte_le_defaut_nomme_et_refuse_son_absence():
    grab = [t for t in T.charger() if t["nom"] == "GRAB-COST-v09-09"][0]
    assert T.verifier(grab, "P3 : la valeur forage_payoff citée n'est publiée par aucun bloc regime") is True
    assert T.verifier(grab, "aucune critique") is False
    noop = [t for t in T.charger() if t["genre"] == "noop"][0]
    assert T.verifier(noop, "[]") is True and T.verifier(noop, '[{"a":1},{"b":2}]') is False
```

- [ ] **Step 3 : implémenter les témoins, le REF, le workflow**

`tools/refutateur_temoins.json` (remplacer chaque `<SHA>` par le SHA trouvé au Step 1 ; les chemins par les noms exacts) :

```json
{
  "_comment": "Temoins GELES du Refutateur (spec PM 2026-09-16 §2.3). A chaque revue, les prompts figes passent d'abord ici : un defaut connu non retrouve rend la revue NULLE. Ne jamais remplacer un temoin par un record plus commode.",
  "temoins": [
    {"nom": "GRAB-COST-v09-09", "genre": "defaut", "sha": "<SHA>", "chemin": "docs/EDR/EDR-GRAB-COST_Carry_Tax_On_Unchosen_Rocks_And_The_Feeding_Premise_Is_Refuted.md",
     "attendu": "forage_payoff", "defaut": "forage_payoff = 3.0 cite, jamais mesure ; le run tournait au defaut 1.0 (E8 occ. 4)"},
    {"nom": "S2-BLIND-v1", "genre": "defaut", "sha": "<SHA>", "chemin": "docs/EDR/<nom exact du record S2-BLIND-CHAMPION>.md",
     "attendu": "(mesur|make_blind|corps|regime)", "defaut": "phrase de regime jamais mesuree ; les controles cables sont morts de leur corps (P1.7)"},
    {"nom": "RETAIN-COMPOSE-pre-retractation", "genre": "defaut", "sha": "<SHA>", "chemin": "docs/EDR/<nom exact du record RETAIN-COMPOSE>.md",
     "attendu": "(lr|pas d'apprentissage|balayage|E19)", "defaut": "nul comparatif sans balayage du pas : 0,02 -> 0,173, 0,002 -> 0,923 (E19)"},
    {"nom": "LOCK-002-sain", "genre": "noop", "sha": "<SHA>", "chemin": "docs/EDR/<nom exact du record LOCK-002>.md",
     "attendu": "", "defaut": "aucun : record sain, au plus 1 critique non confirmee toleree (plancher publie)"}
  ]
}
```

`tools/refutateur_temoins.py` :

```python
"""Témoins gelés du Réfutateur : extraction à leur SHA, vérification qu'une revue retrouve le défaut connu."""
import argparse
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON = os.path.join(_ROOT, "tools", "refutateur_temoins.json")


def charger():
    with open(_JSON, encoding="utf-8") as fh:
        return json.load(fh)["temoins"]


def extraire(temoin, dest):
    os.makedirs(dest, exist_ok=True)
    p = subprocess.run(["git", "show", f"{temoin['sha']}:{temoin['chemin']}"], cwd=_ROOT, capture_output=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"témoin {temoin['nom']} introuvable : {temoin['sha']}:{temoin['chemin']}")
    out = os.path.join(dest, f"{temoin['nom']}.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(p.stdout)
    return out


def verifier(temoin, texte_critiques):
    if temoin["genre"] == "noop":
        try:
            return len(json.loads(texte_critiques)) <= 1
        except ValueError:
            return texte_critiques.strip() in ("", "[]")
    return re.search(temoin["attendu"], texte_critiques, re.I) is not None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extraire", metavar="DIR")
    ap.add_argument("--verifier", nargs=2, metavar=("NOM", "FICHIER"))
    args = ap.parse_args(argv)
    tem = charger()
    if args.extraire:
        for t in tem:
            print(extraire(t, args.extraire))
        return 0
    if args.verifier:
        t = [x for x in tem if x["nom"] == args.verifier[0]][0]
        with open(args.verifier[1], encoding="utf-8") as fh:
            ok = verifier(t, fh.read())
        print(f"{t['nom']} : {'RETROUVÉ' if ok else 'NON RETROUVÉ -> revue NULLE'}")
        return 0 if ok else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`docs/REF/REF-REVUE-ADVERSARIALE.md` — les prompts sont FIGÉS : toute modification est un commit path-scoped décidé par robla, et re-passe les témoins.

```markdown
---
id: REF-REVUE-ADVERSARIALE
type: REF
title: "Revue adversariale à sondes propres — les 10 prompts figés du Réfutateur"
status: active
---

# Revue adversariale à sondes propres

**Règle** (CLAUDE.md) : toute conclusion destinée au graphe passe par une revue qui LANCE ses propres sondes — pas une
relecture. Bilan mesuré : 7 revues WARM, 7 erreurs réelles ; revue obligatoire depuis le 2026-07-21, appliquée à 1 des
28 records récents (E10). Ce document fige les prompts ; `.claude/workflows/refutateur.js` les exécute, un contexte
par prompt, après avoir retrouvé le défaut connu de trois témoins gelés (`tools/refutateur_temoins.json`).

**Contrat de chaque prompt** : une SONDE obligatoire (grep, `python -c`, `git show`, lecture d'un `results/*.json`),
un CONSTAT avec `fichier:ligne` ou sortie de commande, une CLASSE du registre (Ex) ou « aucune », un VERDICT parmi
`confirmé` / `non confirmé` / `hors périmètre`. Sortie ≤ 40 lignes. Une critique sans sonde est rejetée à la consolidation.

| # | prompt | sonde imposée |
| --- | --- | --- |
| P1 | **Prémisse porteuse.** Quelle affirmation, si fausse, renverse le verdict ? Est-elle MESURÉE (bloc `regime`, `results/`) ou RECOPIÉE ? | grep de chaque valeur citée dans les `results/*.json` cités ; `python -c` qui charge le JSON et imprime `regime` |
| P2 | **Régime.** Chaque paramètre cité (`forage_payoff`, `lr`, `n_agents`, `max_ticks`, `reward_scale`…) : valeur publiée ? défaut du constructeur ? touche-t-il le chemin ablaté ? | `python tools/check_regime_claims.py --only <record>` puis lecture du constructeur (`config=None` → défaut) |
| P3 | **Balayage du pas.** Tout nul comparatif sous gradient : le pas a-t-il été balayé (nominal ET appliqué, lr/B) ? La référence lr=0 est-elle du MÊME dispositif ? | grep `lr` dans la règle scellée et le runner ; `assert_verdict_invariant_to_optimizer` appelé ? |
| P4 | **Famille de contrôles.** Combien de cellules ? `declare_design(control_family=…)` dit-il le même nombre que la prose ? Seuil hérité d'un autre dispositif ? | `python tools/check_control_family.py --report` ; lecture de la pré-inscription |
| P5 | **Les deux issues.** Le contrôle peut-il échouer ? Le bras testé peut-il réussir ? Contrôle positif dans le MÊME run ? | grep `assert_positive_control` / `assert_not_degenerate` dans le runner ; valeurs du contrôle dans le JSON |
| P6 | **Plancher de bruit.** Tout ratio a-t-il son no-op publié à côté ? Le contraste sort-il de la bande ? | grep `noop` / `no-op` dans record et JSON |
| P7 | **Dose.** Pour un apprenant : nombre de mises à jour reçues publié ? Cohorte constante (`n_agents` par bloc, `resurrections`) ? | lecture du bloc `learning` du JSON |
| P8 | **Corps et aliasing.** L'intervention touche-t-elle W[0:10] (corps), un chevauchement E/S, une vue de l'état ? | `python tools/check_io_overlap.py` ; grep `make_blind`, `W[` dans le runner |
| P9 | **Provenance.** Chaque `results/` cité existe, est suivi, porte `_provenance`/`provenance` avec un `git_sha` ; la pré-inscription est citée et son sceau intact. | `python tools/check_evidence_provenance.py --only <record>` ; `python -c "from tools.preregister import verify; verify('<nom>')"` |
| P10 | **Mécanisme.** Toute affirmation sur le CODE (« TD par tick », « curiosité active », « W figé à lr=0 ») : lire la ligne. | `Read` de la ligne citée ; `grep -n` du symbole ; E26/E29 sont nées ici |

**Phase témoins (avant toute revue réelle)** : P1-P10 sur `GRAB-COST-v09-09` doit produire une critique contenant
`forage_payoff` ; sur `S2-BLIND-v1`, `(mesur|make_blind|corps|regime)` ; sur `RETAIN-COMPOSE-pre-retractation`,
`(lr|balayage|E19)` ; sur `LOCK-002-sain`, au plus 1 critique non confirmée. Sinon la revue est **NULLE** : rien ne
s'écrit, le compteur `témoin manqué` s'incrémente dans `ROLES.md` ; deux fois → re-scellage des prompts.
```

`.claude/workflows/refutateur.js` :

```javascript
export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins geles, 10 prompts figes (REF-REVUE-ADVERSARIALE), consolidation en docs/reviews/',
  phases: [
    { title: 'Temoins', detail: '3 defauts connus + 1 no-op : un manque -> revue NULLE' },
    { title: 'Revue', detail: 'P1..P10, un contexte par prompt, sondes obligatoires' },
    { title: 'Consolidation', detail: 'docs/reviews/<date>-<slug>.md' },
  ],
}

// args = { target: 'docs/EDR/X.md' | 'docs/preregistrations/Y.json', kind: 'record'|'prereg', today: 'AAAA-MM-JJ',
//          temoins_dir: '<scratchpad>/temoins', temoins: [{nom, genre, attendu, fichier}] }
const REF = 'docs/REF/REF-REVUE-ADVERSARIALE.md'
const PROMPTS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']
const CRITIQUES = {
  type: 'object',
  properties: { critiques: { type: 'array', items: { type: 'object', properties: {
    prompt: { type: 'string' }, constat: { type: 'string' }, sonde: { type: 'string' }, preuve: { type: 'string' },
    classe: { type: 'string' }, verdict: { type: 'string' } },
    required: ['prompt', 'constat', 'sonde', 'preuve', 'classe', 'verdict'] } } },
  required: ['critiques'],
}

function consigne(cible, ids) {
  return `Tu es le REFUTATEUR. Lis ${REF} et applique EXACTEMENT les prompts ${ids.join(', ')} a la cible ${cible}.
Chaque critique porte sa SONDE (commande rejouable, que tu as LANCEE), sa PREUVE (fichier:ligne ou sortie), une classe (Ex ou aucune)
et un verdict parmi confirme / non confirme / hors perimetre. Une critique sans sonde lancee est interdite. Reponds en francais, <= 40 lignes.`
}

phase('Temoins')
const temoins = args.temoins || []
const verdictsTemoins = await parallel(temoins.map(t => () =>
  agent(consigne(t.fichier, PROMPTS), { label: `temoin:${t.nom}`, phase: 'Temoins', schema: CRITIQUES })
    .then(r => {
      const crit = (r && r.critiques) || []
      const texte = JSON.stringify(crit)
      const ok = t.genre === 'noop' ? crit.filter(c => c.verdict === 'confirme').length <= 1
                                    : new RegExp(t.attendu, 'i').test(texte)
      return { nom: t.nom, ok, n: crit.length }
    })))
const manques = verdictsTemoins.filter(Boolean).filter(v => !v.ok).map(v => v.nom)
if (manques.length || verdictsTemoins.filter(Boolean).length < temoins.length) {
  log(`revue NULLE : temoins non retrouves ${manques.join(', ')}`)
  return { statut: 'NUL', temoins: verdictsTemoins, cible: args.target }
}
log(`temoins retrouves : ${verdictsTemoins.map(v => `${v.nom}(${v.n})`).join(' ')}`)

phase('Revue')
const parPrompt = await pipeline(PROMPTS, id =>
  agent(consigne(args.target, [id]), { label: `revue:${id}`, phase: 'Revue', schema: CRITIQUES }))
const critiques = parPrompt.filter(Boolean).flatMap(r => r.critiques).filter(c => c.sonde && c.sonde.trim())

phase('Consolidation')
const slug = args.target.split('/').pop().replace(/\.(md|json)$/, '').slice(0, 60)
const sortie = `docs/reviews/${args.today}-${slug}.md`
const consolide = await agent(`Ecris le fichier ${sortie} (Write) selon docs/reviews/README.md : en-tete (cible ${args.target}, date ${args.today},
SHA courant via git rev-parse HEAD, temoins : ${JSON.stringify(verdictsTemoins)}), puis une section par prompt P1..P10 avec Sonde / Constat /
Classe / Verdict, a partir de ces critiques (JSON) : ${JSON.stringify(critiques)}. N'invente aucune critique. Ne modifie AUCUN autre fichier.
Rends le chemin ecrit et le nombre de critiques confirmees.`, { label: 'consolidation', phase: 'Consolidation', effort: 'low' })
return { statut: 'ECRITE', fichier: sortie, n_critiques: critiques.length,
         n_confirmees: critiques.filter(c => c.verdict === 'confirme').length, temoins: verdictsTemoins, note: consolide }
```

**Protocole d'invocation** (à écrire en tête de `docs/reviews/README.md`, section « Lancer une revue ») :

1. `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --extraire <scratchpad>/temoins` → 4 fichiers.
2. `Workflow({scriptPath: '.claude/workflows/refutateur.js', args: {target, kind, today, temoins: [{nom, genre, attendu, fichier: '<scratchpad>/temoins/<nom>.md'} …]}})` — les champs viennent de `tools/refutateur_temoins.json`, le script ne les invente pas.
3. `statut: NUL` → rien n'est écrit ; incrémenter `témoin manqué` dans `ROLES.md` (PM). `ECRITE` → ajouter `review: docs/reviews/<date>-<slug>.md` au frontmatter du record (la session qui grave), ou passer `reviewed_by=` à `preregister`.

- [ ] **Step 4 : lancer les tests, puis la PREMIÈRE revue réelle sur un témoin**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_refutateur_temoins.py tests/sandbox/test_record_graph_completeness.py -q -p no:cacheprovider`
Expected: PASS (le REF a un frontmatter `id:`/`type: REF` : pas d'orphelin).
Puis, en session : lancer le workflow avec `target` = le témoin GRAB-COST extrait lui-même. Attendu : phase Témoins `retrouvés 4/4`, phase Revue rend ≥ 1 critique `confirmé` contenant `forage_payoff`. Si la phase Témoins rend NUL : les prompts ne discriminent pas — corriger le REF AVANT de livrer (c'est le contrôle positif du rôle, pas un détail).

- [ ] **Step 5 : commit**

```bash
git add docs/REF/REF-REVUE-ADVERSARIALE.md tools/refutateur_temoins.json tools/refutateur_temoins.py .claude/workflows/refutateur.js docs/reviews/README.md tests/sandbox/test_refutateur_temoins.py
git commit -m "feat(refutateur): REF-REVUE-ADVERSARIALE (10 prompts figes), temoins geles a leur SHA (GRAB-COST 09-09, S2-BLIND v1, RETAIN-COMPOSE pre-retractation, LOCK-002 no-op), workflow refutateur.js (temoins -> revue -> docs/reviews)" -- docs/REF/REF-REVUE-ADVERSARIALE.md tools/refutateur_temoins.json tools/refutateur_temoins.py .claude/workflows/refutateur.js docs/reviews/README.md tests/sandbox/test_refutateur_temoins.py
```

---

### Task 7 : Consigner les cinq dettes au backlog (P2.78 → P2.82)

**Files:**
- Modify: `docs/roadmap/PRIORITES_ET_DETTES.md` — insérer dans `### Liste PRIORISÉE`, juste avant `### Décisions tranchées le 2026-09-14` (l.1053 au 2026-09-16 ; retrouver par grep)

**Interfaces:**
- Consumes: la forme canonique d'une entrée (`**P2.NN — OUVERTE — titre.**`, corps `Quoi :`, dernière ligne `<!-- closes_when:… -->`, ligne vide) ; prochains numéros libres mesurés le 2026-09-16 : P2.78 (vérifier par `grep -c "^\*\*P2\.78" docs/roadmap/PRIORITES_ET_DETTES.md` → 0 avant d'écrire, pour CHAQUE numéro).

- [ ] **Step 1 : mesurer AVANT (compte d'entité hors de l'artefact)**

Run: `git show HEAD:docs/roadmap/PRIORITES_ET_DETTES.md | grep -c -E "^\*\*P[0-9]+\." ; wc -l docs/roadmap/PRIORITES_ET_DETTES.md ; for n in 78 79 80 81 82; do grep -c "^\*\*P2\.$n" docs/roadmap/PRIORITES_ET_DETTES.md; done`
Expected: N entrées (≈115) ; 4017 lignes ; cinq `0`. Puis `python -c "from tools.check_staged_authorship import snapshot; snapshot(['docs/roadmap/PRIORITES_ET_DETTES.md'], owner='plan-refutateur')"`.

- [ ] **Step 2 : insérer les cinq entrées (Edit, jamais un découpage par index)**

```markdown
**P2.78 — ✅ CLOSE le <date de livraison de la Task 1> — Porte 18 `check_regime_claims` : une valeur de paramètre citée par un record est PUBLIÉE par le bloc `regime` d'un `results/` suivi.**
Quoi : E8 occ. 4 (EDR-GRAB-COST, `forage_payoff = 3.0` jamais mesuré, défaut 1.0). Mesuré le 2026-09-16 : **47 records citent un
paramètre, 4 citent un bloc `regime`** (`grep -l` sur `docs/EDR/*.md`). Livré : `tools/check_regime_claims.py`, baseline des 43
légataires, contre-exemple gelé GRAB-COST au 09-09, mutation tuée. Spec : `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` §3.5.
<!-- closes_when:path_present=tools/check_regime_claims.py -->

**P2.79 — ✅ CLOSE le <date> — Porte 19 `check_evidence_provenance` : tout `results/` cité existe et est suivi par git (ou publié par sha256).**
Quoi : E27. Mesuré le 2026-09-16 : **69 chemins `results/` cités par les EDR, 20 non suivis, 18 absents** (`git ls-files --error-unmatch`
/ `test -e` sur la liste extraite). Livré : `tools/check_evidence_provenance.py`, baseline des 38 paires, mutation tuée.
<!-- closes_when:path_present=tools/check_evidence_provenance.py -->

**P2.80 — ✅ CLOSE le <date> — Porte 20 `check_e19_optimizer_sweep` : un runner scellé à bras sous gradient appelle `assert_verdict_invariant_to_optimizer`.**
Quoi : E19 (RETAIN-COMPOSE 0,173 → 0,923 au seul `lr`). Mesuré le 2026-09-16 : la garde a **un appelant** (`tools/learner_calibration.py:120`)
pour 11 points d'entrée d'apprentissage, **0 des 23 runners scellés** ; E19 vit en prose (`clause_E19`, 7 règles). Livré : porte 20, baseline,
argv rapporté « non résolu » jamais deviné, mutation tuée.
<!-- closes_when:path_present=tools/check_e19_optimizer_sweep.py -->

**P2.81 — OUVERTE — `check_preregistration_applied` : l'appariement par PRÉFIXE fabrique des « familles orphelines » — à chiffrer par un cas de calibration avant tout usage de ce compte comme preuve.**
Quoi : `tools/check_preregistration_applied.py:125` apparie règle → record par `startswith(base + "_")` et se déclare lui-même faillible
(`:195` : « le distinguer sans deviner est impossible »). Le panel du 2026-09-16 a compté 8 familles rendues orphelines à tort — ce compte
a servi de preuve à un candidat-rôle avant d'être réfuté (E8). À écrire : `tests/sandbox/test_prereg_applied_pairing.py` — un record
qui cite `docs/preregistrations/<name>.json` sans préfixer le nom doit être APPARIÉ, et un nom absent doit rendre INCONNU, jamais orphelin.
<!-- closes_when:path_present=tests/sandbox/test_prereg_applied_pairing.py -->

**P2.82 — OUVERTE — Cliquet « hors motif » + test de forme du hook (E4 occ. 7) : chaque détecteur publie ce qu'il NE voit PAS.**
Quoi : 11 élargissements datés de `check_instrument_calibration` en 7 semaines, chacun révélant de la dette réelle ; **1775 `def` sur 2078
hors de tout motif**, jamais publiés. À écrire : (i) chaque `check_*.py` à motif publie « balayé / appariés / HORS MOTIF » (différentiel
AST vs regex, ~30 lignes, `ast` déjà importé à `check_instrument_calibration.py:26`), contrôle positif = l'arbre au 2026-09-15 avant
`0cdd54a` rend les 3 apprenants indentés de P2.62 ; (ii) test de forme du hook : toute `staged_X=` appelant un checker à baseline liste
sa baseline dans son regex (`tests/sandbox/test_hook_baseline_regex.py`). Sous-produit du panel du 2026-09-16 (candidat « Auditeur des
angles morts », décidable à 80 % → cliquet, pas rôle).
<!-- closes_when:path_present=tests/sandbox/test_hook_baseline_regex.py -->

```

Remplacer `<date …>` par la date réelle de livraison des Tasks 1-3 (si cette Task 7 est exécutée AVANT elles, écrire `OUVERTE` à la place de `✅ CLOSE le …` : le cliquet `clause-close` exigera de fermer l'entrée quand le fichier existera).

- [ ] **Step 3 : mesurer APRÈS, lancer le cliquet du backlog**

Run: `grep -c -E "^\*\*P[0-9]+\." docs/roadmap/PRIORITES_ET_DETTES.md ; wc -l docs/roadmap/PRIORITES_ET_DETTES.md`
Expected: N + 5 entrées ; ≈ 4017 + 40 lignes — jamais moins qu'avant.
Run: `PYTHONIOENCODING=utf-8 python tools/check_backlog_freshness.py`
Expected: `OK : 2 péremption(s) mécanique(s), toutes légataires (baseline). Aucune nouvelle.` Sinon lire la clé (`numero-double`, `chemin-mort`, `clause-refusee`) et corriger l'ENTRÉE, jamais la baseline.
Run: `python -c "from tools.check_staged_authorship import verify; verify(['docs/roadmap/PRIORITES_ET_DETTES.md'], owner='plan-refutateur')"`

- [ ] **Step 4 : commit**

```bash
git add docs/roadmap/PRIORITES_ET_DETTES.md
git commit -m "docs(backlog): P2.78-P2.82 -- portes 18/19/20 (47/4, 69/20/18, 0/23 mesures le 2026-09-16), appariement par prefixe de check_preregistration_applied a calibrer, cliquet hors motif + test de forme du hook" -- docs/roadmap/PRIORITES_ET_DETTES.md
```

---

## Auto-revue du plan

- **Couverture spec §3.5** : porte 18 → Task 1 ; porte 19 → Task 2 ; porte 20 → Task 3 ; `review:` exigé → Task 4 ; `reviewed_by` → Task 5 (écart déclaré : « déclare un coût » remplace un seuil qui n'existe pas) ; workflow, REF, témoins, no-op, `docs/reviews/` → Task 6 ; §10 → Task 7. §2.3 compteurs du Réfutateur (critiques émises / confirmées) : ils se lisent dans `docs/reviews/*.md` (verdicts par prompt) — le PM les recompute à la revue des rôles ; pas de code dédié ici (YAGNI tant qu'il n'y a pas 10 revues).
- **Cohérence** : `cited_results`/`_developper` définis Task 1, consommés Task 2 ; `_sources`/`_HORS_PERIMETRE` importés de `check_control_family` ; `review` scalaire dans `_empty_record` ; `ReviewRequired`, `declare_un_cout` nommés identiquement dans tests et code ; `charger`/`extraire`/`verifier` idem.
- **Numérotation des portes** : 18, 19, 20 ici ; 21 (registre des rôles) dans le plan 1 — l'ordre de livraison ne change pas les numéros, seul le COMPTE (`portes_hook`) est recomputé : mettre la balise de `CLAUDE.md` au nombre de modules `check_*` réellement présents dans le hook au moment du commit (`python tools/check_synthesis_counts.py --list`).
- **Placeholders** : les seuls `<…>` sont les SHA et noms exacts des témoins (Task 6, Step 1 dit COMMENT les obtenir et interdit la substitution) et la date de livraison (Task 7).

