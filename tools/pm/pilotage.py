# -*- coding: utf-8 -*-
"""Source UNIQUE de l'état de pilotage : flotte, roadmap, portes, charge, assemblés en `pilotage_v1`.

`compute_pilotage` est PURE (toutes les sources sont injectées ; seul le chemin cherché d'une source PM
absente est recalculé, pour la nommer) et **aucune fonction de ce module n'écrit un fichier** :
le backend l'appelle en mémoire, le tick PM en dumpe le résultat lui-même. Une source absente n'est
jamais un zéro : elle est `None` PLUS une ligne `aveugle` (porte 14 appliquée au schéma).
"""
import argparse
import json
import math
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
    tête composite `P2.0 / P2.1` vaut UN. Les entrées sont dupliquées par numéro APRÈS la vérification.
    Parité rompue -> `ValueError` EXPLICITE, jamais un `assert` : sous `python -O` un `assert` disparaît,
    et un backlog à une tête indentée sortait alors TRONQUÉ sans un mot (F11).

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

    tetes = compter_entrees(txt)
    if len(blocs) != tetes:
        raise ValueError(f"parité rompue : {len(blocs)} blocs contre {tetes} têtes comptées par le cliquet")

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


# Ponctuation ORPHELINE laissée par le retrait du marqueur, du rang et de la date. Mesuré le 2026-09-26 : 68 titres
# sur 172 commençaient par « ( , [[EDR-…]]) — — » ou « ( ) — — » quand le statut était daté entre parenthèses
# (« ✅ CLOSE (2026-09-14) — rang 2 — … »). Une parenthèse n'est un débris qu'en début de mot : `f()` ou `llm_fn()`
# collés à leur nom restent intacts — le markdown du titre est laissé TEL QUEL.
_PARENS_VIDES = re.compile(r"(?:(?<=\s)|^)\(\s*[,;:]?\s*\)")
_PARENS_A_SEPARATEUR = re.compile(r"(?:(?<=\s)|^)\(\s*[,;:]\s*")
_TIRETS_REPETES = re.compile(r"—(?:\s*—)+")


def _sans_debris(titre):
    t = _PARENS_A_SEPARATEUR.sub("(", _PARENS_VIDES.sub(" ", titre))
    t = re.sub(r"\s{2,}", " ", t).strip(" -—")
    return _TIRETS_REPETES.sub("—", t).strip(" -—")


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
    titre = _sans_debris(titre)

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


# Tête de bloc du hook : « # 24. TITRE », tirets de décoration tolérés (« # --- 24. TITRE »). Mesuré le 2026-09-26 :
# la porte 24 est entrée sous la forme décorée, et le motif strict l'effaçait de l'inventaire en silence (23 servies
# pour 24 branchées). Un commentaire daté (« # 2026-09-26 : ») n'est pas une tête : le chiffre y est suivi d'un tiret.
_NUM_BLOC = re.compile(r"^#\s*(?:-+\s*)?(\d+)\.", re.M)
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
    # Clés de dette déclarées le 2026-09-26 après CONFRONTATION du compte à la sortie de la porte : 89 légataires
    # (check_fabricated_defaults), 64 (check_regime_claims), 19 gelés (check_e19_optimizer_sweep), 54 sites gelés
    # (check_grid_threshold). Les quatre dernières lignes manquaient : la vue Portes affichait « aucune baseline »
    # pour des portes qui en ont une (revue adversariale du pas 3).
    "check_fabricated_defaults": ("fabricated_defaults_baseline.json", "legataires"),
    "check_control_family": ("control_family_baseline.json", None),
    "check_io_overlap": ("io_overlap_baseline.json", None),
    "check_calibration_reach": ("calibration_reach_baseline.json", None),
    "check_regime_claims": ("regime_claims_baseline.json", "legataires"),
    # 17 records dans `legataires` pour 18 chemins publiés par la porte : unité ambiguë, dette NON déclarée
    "check_evidence_provenance": ("evidence_provenance_baseline.json", None),
    "check_hook_deployment": ("hook_deployment_baseline.json", None),
    "check_e19_optimizer_sweep": ("e19_sweep_baseline.json", "legataires"),
    "check_grid_threshold": ("grid_threshold_baseline.json", "sites"),
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


def _racine_des_donnees_pm(repo_root):
    """Base où ancrer un chemin RELATIF de `paths.pm_dir` — résolution PURE, aucune écriture d'environnement.

    Même sémantique que `snapshot.ancrer_data_root` (qui pose `AGAGI_DATA_ROOT = <racine commune>/data`,
    c.-à-d. le défaut relatif joint à la racine COMMUNE), sans son effet de bord : si `AGAGI_DATA_ROOT` est
    posée, `paths.pm_dir` en tient compte et un chemin encore relatif s'ancre sur `repo_root` comme avant ;
    sinon il s'ancre sur la racine COMMUNE à tous les worktrees (`git rev-parse --git-common-dir`), et sur
    `repo_root` si git est muet. ⚠️ F1 : l'appel à `ancrer_data_root` vivait ici, donc dans le processus
    uvicorn — mesuré, UN poll faisait basculer `paths.data_root()` / `paths.db_root()` (KuzuDB, génomes,
    HoF) vers le `data/` COMMUN pour tout le processus et ses enfants. La règle vit dans
    `snapshot.base_des_donnees` (P2.114 : `snapshot` en a besoin pour le chemin `?frais=1`) — une seule copie."""
    from tools.pm.snapshot import base_des_donnees
    return base_des_donnees(repo_root)


def chemin_roles_counts(repo_root):
    """Le chemin que `read_roles_counts` CHERCHE — un seul calcul, pour qu'une absence se nomme à l'endroit
    exact où elle a été constatée (G9)."""
    from src import paths
    return _ancre(_racine_des_donnees_pm(repo_root), paths.pm_dir("ROLES_COUNTS.json"))


def chemin_board(repo_root):
    """Le chemin que `read_board` CHERCHE (même rôle que `chemin_roles_counts`)."""
    from src import paths
    return _ancre(_racine_des_donnees_pm(repo_root), paths.pm_dir("BOARD.json"))


def read_roles_counts(repo_root):
    return _lire_json(chemin_roles_counts(repo_root))


def read_board(repo_root):
    """Le cache du tick PM. ⚠️ Écrit par `json.dump(..., default=str)` (tools/pm/tick.py) : ce qui revient
    est un ALLER-RETOUR JSON, pas le dict de `board.compute`."""
    return _lire_json(chemin_board(repo_root))


def _chemin_cherche(resolveur, racine):
    """Le chemin cherché, en POSIX, pour une ligne `aveugle` — jamais une exception : un chemin non résolu
    se DIT à la place du chemin."""
    try:
        return str(resolveur(racine)).replace("\\", "/")
    except Exception as exc:                                       # noqa: BLE001 — la ligne ne doit jamais lever
        return f"<chemin non résolu : {type(exc).__name__}>"


def read_portes(repo_root):
    """Inventaire des gardes du hook, joint à PORTES pour titres/témoins/mutations et à BASELINES.

    La source d'AUTORITÉ est le hook : `check_gate_mutation.PORTES` est la table des portes MUTÉES
    (16 clés le 2026-09-24) alors que le hook lance 19 scripts. Le numéro vient de `_NUM_BLOC` (tirets de
    décoration tolérés) en tête de bloc, le module du PREMIER `python tools/check_X.py` du bloc (un bloc lance parfois son check
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
    nommant la racine.

    ⚠️ Les DEUX témoins doivent manquer (F5, ruling du contrôleur). Une racine qui porte l'un des deux est
    AGAGI avec un fichier absent — l'accident E22 que ce dépôt a déjà subi — et ce sont les lignes PAR
    SOURCE qui le nomment ; `not (A and B)` y disait « racine suspecte » et mettait flotte, portes et
    charge à `None`, sources saines comprises."""
    return (os.path.isfile(os.path.join(racine, "docs", "roadmap", "PRIORITES_ET_DETTES.md"))
            or os.path.isfile(os.path.join(racine, "tools", "hooks", "pre-commit")))


def _board_refus(board):
    """`None` si `board` a la FORME d'un tableau PM, sinon la RAISON (une chaîne) de le déclarer illisible.

    I4 puis F8 : chaque forme refusée a été MESURÉE comme un défaut — `board` non-dict ou `charge_connue`
    non-dict (`AttributeError` sur `.get`, tout aveuglé ; `charge_connue = []` rendait la charge tout à
    `None` SANS ligne), `aveugle` non-liste (`aveugle = 5` : `TypeError` ; `"abc"` : trois lignes
    « flotte: a/b/c » fabriquées), `generated_at` non numérique, booléen (âge absurde) ou non fini (âge
    `nan`, puis un 500 à la sérialisation JSON). Une clé ABSENTE (ou `null`) n'est pas un refus : elle est
    dite plus loin, dans le bloc qu'elle prive."""
    if not isinstance(board, dict):
        return f"racine de type {type(board).__name__}"
    gen = board.get("generated_at")
    if gen is not None:
        if isinstance(gen, bool):
            return "generated_at booléen"
        try:
            valeur = float(gen)
        except OverflowError:
            # G8 : un entier JSON de plus de 309 chiffres — non attrapée, l'exception sortait de
            # `compute_pilotage` et aveuglait TOUT le pilotage.
            return "generated_at hors bornes (entier trop grand pour un float)"
        except (TypeError, ValueError):
            return f"generated_at non numérique ({type(gen).__name__})"
        if not math.isfinite(valeur):
            return f"generated_at non fini ({valeur})"
    cc = board.get("charge_connue")
    if cc is not None and not isinstance(cc, dict):
        return f"charge_connue de type {type(cc).__name__}"
    av = board.get("aveugle")
    if av is not None and not (isinstance(av, list) and all(isinstance(a, str) for a in av)):
        return f"aveugle n'est pas une liste de chaînes ({type(av).__name__})"
    return None


def compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now, repo_root=None,
                     board=None):
    """PURE : toutes les SOURCES sont injectées, rien n'est écrit. Une seule résolution hors injection : quand
    `BOARD.json` ou `ROLES_COUNTS.json` manque, le chemin que son lecteur CHERCHE est recalculé (git
    `rev-parse` compris, via `chemin_board` / `chemin_roles_counts`) pour que la ligne le NOMME (G9).

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
        refus = _board_refus(board)
        if refus is None:
            flotte = board
        else:
            aveugle.append(f"flotte : BOARD.json de forme inattendue ({refus}) -- illisible, jamais une "
                            "exception qui aveugle roadmap/portes/charge avec lui")
    else:
        # G9 : l'ancienne ligne affirmait une CAUSE (« le tick PM n'a pas encore tourné ») tirée d'une
        # absence ; mesuré, git absent du PATH, un backend lancé depuis un worktree le disait pendant que le
        # tick tournait. La ligne nomme le chemin CHERCHÉ et les deux causes, sans en choisir une.
        aveugle.append(f"flotte : BOARD.json introuvable (ou JSON illisible) à {_chemin_cherche(chemin_board, racine)}"
                        " -- tick PM jamais passé, ou racine de données mal résolue : l'absence ne tranche pas")
    if flotte is not None:
        aveugle.extend("flotte: " + a for a in (flotte.get("aveugle") or []))
        if flotte.get("generated_at") is None:
            aveugle.append("flotte : BOARD.json sans generated_at -- âge inconnu (jamais un mtime de repli)")
        cc_flotte = flotte.get("charge_connue")
        if cc_flotte is None:
            aveugle.append("charge : BOARD.json ne porte pas charge_connue -- sims_en_vol, cpu_pct et "
                            "bails_vivants inconnus, servis à null")
        elif isinstance(cc_flotte, dict):
            # G7 (classe F8) : `charge_connue = {}` passait la garde (c'est un dict) et les champs tombaient
            # à `None` sans un mot. Chaque champ attendu ABSENT est nommé, sur une seule ligne.
            absents = [c for c in ("sims_en_vol", "cpu_pct", "bails_vivants") if c not in cc_flotte]
            if absents:
                aveugle.append(f"charge : charge_connue de la flotte ne porte pas {', '.join(absents)} -- "
                                "inconnu(s), servi(s) à null")

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

    # `records_graph.json` est une source ÉTRANGÈRE (writer : check_record_links) : sa forme se vérifie ICI,
    # sinon un `roadmap` non-dict passait dans `Roadmap.portes_agi` et la route levait HORS du filet du
    # service (500), et un graphe non-dict faisait lever `.get` et aveuglait TOUT le pilotage (F3).
    graphe = records_graph
    if graphe is not None and not isinstance(graphe, dict):
        aveugle.append(f"graphe de records : results/records_graph.json de forme inattendue "
                        f"({type(graphe).__name__}) -- illisible, portes_agi servies à null")
        graphe = None
    if roadmap is not None:
        portes_agi = None
        if graphe is not None:
            if "roadmap" not in graphe:
                aveugle.append("portes_agi : results/records_graph.json ne porte pas de clé roadmap -- "
                                "portes G0-G4 inconnues, servies à null")
            elif not isinstance(graphe["roadmap"], dict):
                aveugle.append(f"portes_agi : la clé roadmap de records_graph.json est de forme inattendue "
                                f"({type(graphe['roadmap']).__name__}) -- servie à null, le reste de la "
                                "roadmap reste servi")
            else:
                portes_agi = graphe["roadmap"]
        roadmap["portes_agi"] = portes_agi
    elif graphe is not None:
        aveugle.append("portes_agi : nichées dans roadmap, indisponibles -- le backlog est absent ou "
                        "illisible alors que records_graph.json, lui, est présent")
    if records_graph is None:
        aveugle.append("graphe de records : results/records_graph.json introuvable")

    if portes is None:
        aveugle.append("portes : tools/hooks/pre-commit illisible")

    compteurs = roles_counts
    if compteurs is None:
        aveugle.append(f"compteurs du PM : ROLES_COUNTS.json introuvable (ou JSON illisible) à "
                        f"{_chemin_cherche(chemin_roles_counts, racine)} -- tick PM jamais passé, ou racine de "
                        "données mal résolue : l'absence ne tranche pas")
    elif not isinstance(compteurs, dict):
        aveugle.append(f"compteurs du PM : ROLES_COUNTS.json de forme inattendue ({type(compteurs).__name__}) "
                        "-- illisible, jamais une exception qui aveugle le reste du pilotage")
        compteurs = None
    charge = None
    if compteurs is not None or flotte is not None:
        cc = (flotte or {}).get("charge_connue") or {}
        gen = (flotte or {}).get("generated_at")
        fichiers = None
        if compteurs is not None:
            # roles_counts.compute_counts rend {science: 0, methodo: 0, autre: 0} quand git est muet, et le
            # DIT dans ce drapeau voisin : recopier `fichiers` publierait un zéro FABRIQUÉ (F10). G7 : `fichiers`
            # n'est publié que si le drapeau vaut EXACTEMENT `True` — il est né avec `roles_counts.py`
            # (ff99e849, `git log -S fichiers_disponibles`), donc son absence n'est pas un « ancien format ».
            dispo = compteurs.get("fichiers_disponibles")
            if dispo is True:
                fichiers = compteurs.get("fichiers")
            elif dispo is False:
                aveugle.append("charge : ROLES_COUNTS.json déclare fichiers_disponibles = false (git muet) -- "
                                "comptes de fichiers INDISPONIBLES, leur zéro est FABRIQUÉ, servis à null")
            else:
                etat = ("absent" if "fichiers_disponibles" not in compteurs else
                        "null" if dispo is None else f"de type {type(dispo).__name__}")
                aveugle.append(f"charge : ROLES_COUNTS.json ne dit pas si ses comptes de fichiers sont fiables "
                                f"(fichiers_disponibles {etat}) -- disponibilité inconnue, servis à null")
        charge = {"sims_en_vol": cc.get("sims_en_vol"), "cpu_pct": cc.get("cpu_pct"),
                  "bails_vivants": cc.get("bails_vivants"),
                  "flotte_age_s": (now - float(gen)) if gen is not None else None,
                  "ratio_science_methodo": (compteurs or {}).get("ratio_science_methodo"),
                  "fichiers": fichiers,
                  "fenetre": (compteurs or {}).get("fenetre")}
    return {"schema": SCHEMA, "generated_at": now, "repo_root": racine.replace("\\", "/"),
            "aveugle": aveugle, "flotte": flotte, "roadmap": roadmap, "portes": portes, "charge": charge}


ARTEFACT_SCHEMA = "pilotage_artefact_v1"
# Limite du store de la page artefact : 256 KiB par document sérialisé (db.d.ts du contrat 0.2.60). Mesuré le
# 2026-09-26 : `pilotage_v1` complet = 150 KiB compacts (172 blocs, +45 en deux jours), dont 95 KiB d'entrées —
# publié tel quel, il aurait dépassé la limite sous deux semaines environ. Marge de 16 KiB sous la limite.
ARTEFACT_OCTETS_MAX = 240 * 1024


def _octets(d):
    return len(json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def _chaines(v):
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def _flotte_artefact(f, aveugle):
    if not isinstance(f, dict):
        return None
    sessions = alertes = None
    illisibles = {"session": 0, "alerte": 0}
    if isinstance(f.get("sessions"), list):
        sessions = []
        for s in f["sessions"]:
            if not isinstance(s, dict):
                illisibles["session"] += 1
                continue
            bulletin = s["bulletin"] if isinstance(s.get("bulletin"), bool) else None
            ft = s.get("files_touched")
            sessions.append({"nom": s.get("name") or s.get("session_id") or "?", "branche": s.get("branch"),
                             "bulletin": bulletin, "claims": _chaines(s.get("claims")),
                             "claims_inferes": _chaines(s.get("claims_inferes")),
                             # sans bulletin, les fichiers en vol sont INCONNUS : jamais le 0 d'une liste vide
                             "fichiers_en_vol": None if bulletin is False or not isinstance(ft, list) else len(ft),
                             # P2.118 : écritures Bash possibles, COMPTÉES jamais nommées (None = jamais compté)
                             "bash_ecritures_possibles": s.get("bash_ecritures_possibles"),
                             "heartbeat_at": s.get("heartbeat_at")})
    if isinstance(f.get("alertes"), list):
        alertes = []
        for a in f["alertes"]:
            if not isinstance(a, dict):
                illisibles["alerte"] += 1
                continue
            alertes.append({"id": a.get("id"), "gravite": a.get("gravite"), "message": a.get("message")})
    for quoi, n in illisibles.items():
        if n:
            aveugle.append(f"flotte : {n} entrée(s) de {quoi} illisible(s), non projetée(s)")
    return {"generated_at": f.get("generated_at"), "sessions": sessions,
            "sessions_mortes": _chaines(f["sessions_mortes"]) if isinstance(f.get("sessions_mortes"), list) else None,
            "alertes": alertes}


def _roadmap_artefact(rm):
    if not isinstance(rm, dict):
        return None
    pa = rm.get("portes_agi")
    portes_agi = None
    if isinstance(pa, dict):
        portes_agi = {}
        for k, v in pa.items():
            v = v if isinstance(v, dict) else {}
            tb = v.get("tested_by")
            portes_agi[str(k)] = {"sdr": v.get("sdr"), "status": v.get("status"),
                                  "records": len(tb) if isinstance(tb, list) else None}
    entrees = []
    for e in rm.get("entrees") or []:
        ch = [c for c in (e.get("chemins") or []) if isinstance(c, dict)]
        c = e.get("clause")
        d = {"num": e.get("num"), "priorite": e.get("priorite"), "rang": e.get("rang"), "statut": e.get("statut"),
             "date": e.get("date"), "titre": e.get("titre"),
             "clause": {"pred": c.get("pred"), "satisfaite": c.get("satisfaite")} if isinstance(c, dict) else None,
             "chemins": len(ch), "chemins_absents": sum(1 for x in ch if x.get("existe") is False),
             "chemins_non_captes": e.get("chemins_non_captes")}
        if e.get("raison_illisible"):
            d["raison_illisible"] = e["raison_illisible"]
        entrees.append(d)
    return {"direction": rm.get("direction"), "comptes": rm.get("comptes"), "portes_agi": portes_agi,
            "entrees": entrees}


def _portes_artefact(portes):
    if not isinstance(portes, list):
        return None
    return [{"num": p.get("num"), "module": p.get("module"), "titre": p.get("titre"), "mutations": p.get("mutations"),
             "baseline": bool(p["baseline"].get("existe")) if isinstance(p.get("baseline"), dict) else None,
             "dette": p["baseline"].get("dette") if isinstance(p.get("baseline"), dict) else None}
            for p in portes if isinstance(p, dict)]


def projection_artefact(p):
    """Projection PURE de `pilotage_v1` pour la page artefact (spec §3.4), publiée par le skill /pm.

    La page est lue HORS de la machine : un chemin de fichier y serait un lien mort, et une preuve d'alerte y
    exposerait des chemins locaux. Elle garde donc les COMPTES (chemins cités, absents, non captés ; records d'une
    porte G) et retire les listes, les preuves et les arguments de clause. Un bloc `None` reste `None`, une entrée
    illisible de la flotte est DITE (ligne `aveugle`), et si le document dépasse `ARTEFACT_OCTETS_MAX` les entrées
    du backlog sont retirées et c'est écrit dans `omis` — jamais un document tronqué qui se présenterait comme
    complet, jamais un `write_db` refusé en silence."""
    aveugle = list(p.get("aveugle") or [])
    out = {"schema": ARTEFACT_SCHEMA, "source_schema": p.get("schema"), "generated_at": p.get("generated_at"),
           "aveugle": aveugle, "omis": [],
           "flotte": _flotte_artefact(p.get("flotte"), aveugle), "roadmap": _roadmap_artefact(p.get("roadmap")),
           "portes": _portes_artefact(p.get("portes")), "charge": p.get("charge")}
    n = _octets(out)
    if n > ARTEFACT_OCTETS_MAX and out["roadmap"] is not None:
        k = len(out["roadmap"]["entrees"])
        out["roadmap"]["entrees"] = None
        out["omis"].append(f"entrées du backlog retirées ({k}) : document de {n} octets > {ARTEFACT_OCTETS_MAX} "
                           "octets (limite du store : 256 KiB par document) -- comptes, direction et portes G0-G4 "
                           "restent publiés")
        n = _octets(out)
    if n > ARTEFACT_OCTETS_MAX:
        out["omis"].append(f"document de {n} octets > {ARTEFACT_OCTETS_MAX} octets même sans les entrées -- le "
                           "store le refusera")
    return out


def main(argv=None):
    """`--json` imprime le pilotage, `--artefact` sa projection pour la page artefact. N'ÉCRIT AUCUN FICHIER : le
    tick PM est le seul writer."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--artefact", action="store_true")
    args = ap.parse_args(argv)
    racine = args.repo_root or racine_depot()
    out = compute_pilotage(None, read_backlog(racine), read_records_graph(racine),
                           read_roles_counts(racine), read_portes(racine), time.time(),
                           repo_root=racine, board=read_board(racine))
    if args.artefact:
        print(json.dumps(projection_artefact(out), ensure_ascii=False, indent=1, default=str))
    elif args.json:
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
