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
