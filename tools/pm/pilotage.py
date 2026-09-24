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
import time

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
    from tools.pm.snapshot import ancrer_data_root
    ancrer_data_root(repo_root)   # AVANT tout paths.* : sinon un worktree lit SON propre data/ (jamais le COMMUN)
    return _lire_json(_ancre(repo_root, paths.pm_dir("ROLES_COUNTS.json")))


def read_board(repo_root):
    """Le cache du tick PM. ⚠️ Écrit par `json.dump(..., default=str)` (tools/pm/tick.py) : ce qui revient
    est un ALLER-RETOUR JSON, pas le dict de `board.compute`."""
    from src import paths
    from tools.pm.snapshot import ancrer_data_root
    ancrer_data_root(repo_root)   # AVANT tout paths.* : sinon un worktree lit SON propre data/ (jamais le COMMUN)
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


def _racine_saine(racine):
    """`False` si `racine` ne porte NI le backlog NI le hook — signe qu'elle n'est probablement pas AGAGI.

    Garde de santé (spec §3.1) : sans elle, une racine mal résolue (un `--repo-root` étranger, un cwd qui
    porte un `.git` sans être AGAGI) fait accuser CHAQUE fichier d'être absent, un par un, sans jamais
    nommer la vraie cause. Mesuré depuis un `tempfile.mkdtemp()` : cinq lignes « introuvable », zéro ligne
    nommant la racine."""
    return (os.path.isfile(os.path.join(racine, "docs", "roadmap", "PRIORITES_ET_DETTES.md"))
            and os.path.isfile(os.path.join(racine, "tools", "hooks", "pre-commit")))


def _board_valide(board):
    """`False` si `board` n'a pas la FORME d'un tableau PM : un `board` non-dict (`AttributeError` sur
    `.get`) ou dont `generated_at` n'est pas numérique (`ValueError` plus loin, sur `now - float(gen)`)
    est une source ILLISIBLE, jamais une exception qui aveugle roadmap/portes/charge avec lui (I4)."""
    if not isinstance(board, dict):
        return False
    gen = board.get("generated_at")
    if gen is not None:
        try:
            float(gen)
        except (TypeError, ValueError):
            return False
    return True


def compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now, repo_root=None,
                     board=None):
    """PURE : tout est injecté, rien n'est lu, rien n'est écrit.

    `flotte` a DEUX provenances, jamais confondues : `board` (le contenu de BOARD.json, chemin du poll —
    un aller-retour JSON) ou `board.compute(snap)` si `snap` est fourni (chemin `?frais=1`).

    ⚠️ Les deux aveuglements « backlog » et « graphe de records » sont INDÉPENDANTS : chacun se déclare
    sur l'absence de SA propre source, jamais sur une combinaison des deux — un `records_graph` fourni
    sans backlog n'a nulle part où accrocher `portes_agi`, mais son absence à lui reste rapportée (et se
    DIT : voir plus bas).
    """
    now = float(now)
    racine = repo_root or racine_depot()
    if not _racine_saine(racine):
        return {"schema": SCHEMA, "generated_at": now, "repo_root": racine.replace("\\", "/"),
                "aveugle": [f"racine résolue suspecte : {racine} ne porte ni "
                            "docs/roadmap/PRIORITES_ET_DETTES.md ni tools/hooks/pre-commit -- chemin de "
                            "dépôt probablement FAUX (jamais rapporté comme un simple fichier absent)"],
                "flotte": None, "roadmap": None, "portes": None, "charge": None}
    aveugle = []

    flotte = None
    if snap is not None:
        from tools.pm.board import compute as board_compute
        flotte = board_compute(snap, now=now)
    elif board is not None:
        if _board_valide(board):
            flotte = board
        else:
            aveugle.append(f"flotte : BOARD.json de forme inattendue ({type(board).__name__}) -- "
                            "illisible, jamais une exception qui aveugle roadmap/portes/charge avec lui")
    else:
        aveugle.append("flotte : ni instantané ni BOARD.json — le tick PM n'a pas encore tourné")
    if flotte is not None:
        aveugle.extend("flotte: " + a for a in (flotte.get("aveugle") or []))

    roadmap = None
    if backlog_txt is None:
        aveugle.append("backlog : docs/roadmap/PRIORITES_ET_DETTES.md introuvable")
    elif not backlog_txt.strip():
        aveugle.append("backlog : docs/roadmap/PRIORITES_ET_DETTES.md est VIDE -- source ILLISIBLE, "
                        "jamais un backlog de 0 entrée (cf. l'anéantissement du 2026-09-09)")
    else:
        try:
            roadmap = parse_roadmap(backlog_txt, racine, now)
        except Exception as exc:                        # parité rompue (ex. tête indentée) : NOMMÉ, pas propagé
            aveugle.append(f"backlog : docs/roadmap/PRIORITES_ET_DETTES.md illisible "
                            f"({type(exc).__name__}: {exc})")
            roadmap = None
        else:
            if roadmap["comptes"]["blocs"] == 0:
                aveugle.append("backlog : docs/roadmap/PRIORITES_ET_DETTES.md ne porte AUCUNE tête "
                                "d'entrée reconnue -- source ILLISIBLE, jamais un backlog de 0 entrée")
                roadmap = None

    if roadmap is not None:
        roadmap["portes_agi"] = records_graph.get("roadmap") if records_graph is not None else None
    elif records_graph is not None:
        aveugle.append("portes_agi : nichées dans roadmap, indisponibles -- le backlog est absent ou "
                        "illisible alors que records_graph.json, lui, est présent")
    if records_graph is None:
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
