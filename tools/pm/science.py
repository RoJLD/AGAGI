# -*- coding: utf-8 -*-
"""Lot 2 « Science » du dashboard (P2.84) — spec docs/superpowers/specs/2026-09-26-auto-indexation-artefacts-design.md
(§3.2, §9).

`compute_science` est PUR : il reçoit l'index (`index_v1`) et trois sources déjà LUES par les lecteurs ci-dessous, et
rend `science_v1`. Aucune vue ne recalcule un verdict (condition 4) : la pipeline recopie
`tools/check_preregistration_applied`, la taxonomie recopie les trois JSON du répertoire agi_taxonomy des données, les
trouvailles recopient les verdicts DÉCLARÉS que l'index a lus. Un bloc dont la source manque vaut `null` et une ligne
préfixée de son nom — jamais un zéro (porte 14). Une liste PARTIELLE le dit, un `null` porte sa cause. `science:` et
`index:` sont réservés aux modes dégradés des services.
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
# Les champs de `evidence` qui FONDENT une arête (demand.schema.json ; `specificity_control` en porte seul le contenu
# empirique selon tools/check_agi_taxonomy) : recopiés dans `preuves` — revue de la tâche 1, I5, décision
# d'intégrateur de Master 2 (2026-10-14).
PREUVES = ("specificity_control", "functional_aliasing", "ablation_target", "coord_intact", "emergence_bar",
           "incapable_ceiling", "ceiling_provenance")
# Pourquoi `par_semaine[famille].semaines` vaut null — vocabulaire FERMÉ (revue de la tâche 1, I2). Les trois
# dernières sont celles de l'index (`RAISONS_DATE_GIT`), selon l'historique de l'instantané des dates.
RAISONS_SEMAINES = frozenset({"famille_non_lue", "parite_rompue", "sans_date_nommee", "dates_absentes",
                              "historique_tronque", "git_indisponible"})
_RAISON_HISTORIQUE = {"tronque": "historique_tronque", "indisponible": "git_indisponible"}


def _ancre(racine, chemin):
    return chemin if os.path.isabs(chemin) else os.path.join(racine, chemin)


def _texte(v):
    return v.strip() if isinstance(v, str) and v.strip() else None


def _fini(v):
    """Un nombre FINI, jamais un booléen ; un entier trop grand pour un flottant ne l'est pas (`math.isfinite(10**400)`
    lève OverflowError — revue de la tâche 1, M3 : un seul champ faisait refuser les trois blocs)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False


def _champ(d, cle, sorte, prefixe, rejets):
    """`d[cle]` s'il est de la `sorte` attendue (`texte`, `nombre`, `entier`, `libre` = texte ou nombre) ; ABSENT (ou
    chaîne vide) → None sans un mot, c'est une recopie fidèle ; présent d'une autre sorte → None ET son nom dans
    `rejets` — jamais un retrait silencieux (revue de la tâche 1, M2)."""
    v = d.get(cle)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str) and sorte in ("texte", "libre"):
        return v.strip()
    if sorte in ("nombre", "libre") and _fini(v):
        return v
    if sorte == "entier" and isinstance(v, int) and _fini(v):
        return v
    rejets.append(f"{prefixe}.{cle}")
    return None


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
    """Le compte de verdicts (chaînes non vides) du graphe de records — SDR/ADR/EDR/REF, par
    `consolidate_records.scan_records` —, pour publier l'ÉCART avec l'index seulement (I9 : dérivé, il peut être
    périmé). Un `nodes` qui n'est pas une liste est ILLISIBLE, jamais 0 (revue de la tâche 1, I6)."""
    from src import paths
    p = _ancre(racine, paths.results_file("records_graph.json")).replace("\\", "/")
    try:
        with open(p, encoding="utf-8") as fh:
            noeuds = json.load(fh)["graph"]["nodes"]
        if not isinstance(noeuds, list):
            raise TypeError(f"nodes est un {type(noeuds).__name__}, pas une liste")
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


def semaines_denses(jours, borne=None):
    """`{"AAAA-Www": n}` DENSE de la semaine du premier jour à celle de `borne` (à défaut, du dernier jour) ; aucune
    clé hors de cet intervalle. Un zéro y dit « aucun artefact DATÉ cette semaine » : les artefacts sans date sont
    comptés à part (`sans_date`), jamais répartis (revue de la tâche 1, M8)."""
    dates = sorted(datetime.date.fromisoformat(j) for j in jours)
    compte = collections.Counter(semaine_iso(d.isoformat()) for d in dates)
    out = {}
    if dates:
        fin = datetime.date.fromisoformat(borne) if borne else dates[-1]
        lundi = dates[0] - datetime.timedelta(days=dates[0].weekday())
        while lundi <= fin:
            cle = semaine_iso(lundi.isoformat())
            out[cle] = compte[cle]
            lundi += datetime.timedelta(days=7)
    return out


def _jour_utc(ts):
    """Le jour UTC d'un horodatage, ou None hors du calendrier : l'index accepte tout `generated_at` FINI (1e300)."""
    try:
        return datetime.datetime.fromtimestamp(float(ts), tz=datetime.timezone.utc).date()
    except (OverflowError, ValueError, OSError, TypeError):
        return None


def _famille(index, nom):
    return next((f for f in index.get("familles") or [] if f.get("nom") == nom), None)


def _pipeline(index, source, aveugle):
    if source.get("raison") or source.get("couverture") is None:
        aveugle.append(f"pipeline : couverture illisible ({source.get('raison')}) -- INCONNUE, jamais (0, 0, 0, 0)")
        return None
    couverture, orphelines = dict(source["couverture"]), list(source["familles_sans_record"])
    if couverture.get("sans_record") != len(orphelines):          # deux passes de _inspection(), arbre partagé (M4)
        aveugle.append(f"pipeline : couverture() compte {couverture.get('sans_record')} famille(s) sans record, "
                       f"familles_sans_record() en nomme {len(orphelines)} -- deux lectures de l'arbre partagé, "
                       "servies telles quelles")
    fam = _famille(index, "preinscription")
    if index.get("artefacts") is None or fam is None or fam.get("fichiers") is None:
        aveugle.append("pipeline : famille preinscription non lue par l'index -- liste des pré-inscriptions INCONNUE")
        pre = None
    else:
        pre = [{"chemin": a["chemin"], "titre": a.get("titre"), "scelle": a.get("scelle"),
                "date_ajout_git": a.get("date_ajout_git")}
               for a in index["artefacts"] if a.get("famille") == "preinscription"]
    return {"couverture": couverture, "familles_sans_record": orphelines, "preinscriptions": pre}


def _taxonomie(source, aveugle):
    if source.get("raison"):
        aveugle.append(f"taxonomie : {source.get('chemin')} : {source['raison']} -- graphe INCONNU")
        return None
    sans_id, rejets = collections.defaultdict(list), []
    capacites = []
    for i, c in enumerate(source["capabilities"]):
        ident = _texte(c.get("id")) if isinstance(c, dict) else None
        if ident is None:
            sans_id["capabilities"].append(i)
            continue
        nom = f"capabilities.json[{i}]"
        capacites.append({"id": ident, "titre": _champ(c, "title", "texte", nom, rejets),
                          "record": _champ(c, "record", "texte", nom, rejets)})
    aretes = []
    for nature, cle in (("etablie", "demands"), ("refutee", "refuted")):
        for i, e in enumerate(source[cle]):
            cap = _texte(e.get("capability")) if isinstance(e, dict) else None
            pre = _texte(e.get("prerequisite")) if isinstance(e, dict) else None
            if cap is None or pre is None:
                sans_id[cle].append(i)
                continue
            nom = f"{cle}.json[{i}]"
            pe = f"{nom}.evidence"
            if e.get("evidence") is not None and not isinstance(e.get("evidence"), dict):
                rejets.append(pe)
            ev = e.get("evidence") if isinstance(e.get("evidence"), dict) else {}
            verdict = (_champ(ev, "ablation_verdict", "texte", pe, rejets) if nature == "etablie"
                       else _champ(e, "verdict", "texte", nom, rejets))
            aretes.append({"capacite": cap, "prerequis": pre, "nature": nature,
                           "force": _champ(e, "strength", "texte", nom, rejets), "verdict": verdict,
                           "ratio": _champ(ev, "ratio", "nombre", pe, rejets),
                           "n": _champ(ev, "n", "entier", pe, rejets),
                           "record": _champ(ev, "record", "texte", pe, rejets),
                           "raison": _champ(e, "reason", "texte", nom, rejets),
                           "depassee_par": _champ(e, "superseded_by", "texte", nom, rejets),
                           "preuves": {k: _champ(ev, k, "libre", pe, rejets) for k in PREUVES}})
    for cle, indices in sorted(sans_id.items()):
        aveugle.append(f"taxonomie : {len(indices)} entrée(s) de {cle}.json sans identifiant lisible "
                       f"(indice{'s' if len(indices) > 1 else ''} {', '.join(map(str, indices))}) -- non tracée(s)")
    if rejets:
        aveugle.append(f"taxonomie : {len(rejets)} valeur(s) mal typée(s) ou non finie(s) servie(s) à null -- "
                       + ", ".join(rejets[:12]) + (f" et {len(rejets) - 12} autre(s)" if len(rejets) > 12 else ""))
    hors = sorted({x for a in aretes for x in (a["capacite"], a["prerequis"])} - {c["id"] for c in capacites})
    if hors:
        aveugle.append(f"taxonomie : arête(s) vers une capacité non déclarée dans capabilities.json ({', '.join(hors)})")
    return {"capacites": capacites, "aretes": aretes}


def _par_semaine(index, aveugle, now):
    """Par famille, sur UNE date nommée ; un objet TOUJOURS servi, dont `raison` dit pourquoi `semaines` est null
    (`RAISONS_SEMAINES`). Parité vérifiée deux fois : datés + sans date = artefacts servis = `indexes` de l'index
    (M1). L'intervalle dense s'arrête au jour UTC de l'instantané des dates (git) ou de `now` (nom daté) ; sa
    dernière semaine est PARTIELLE et dite ; un artefact daté au-delà va dans `sans_date` sous `date_future`
    (revue de la tâche 1, I3 et I4)."""
    dates = index.get("dates") or {}
    aujourd_hui = datetime.datetime.fromtimestamp(float(now), tz=datetime.timezone.utc).date()
    instantane = _jour_utc(dates.get("generated_at")) if dates else None
    bornes = {"date_ajout_git": min(aujourd_hui, instantane) if instantane else aujourd_hui,
              "date_declaree": aujourd_hui}
    out = {}
    for f in index["familles"]:
        nom, champ = f["nom"], DATE_PAR_FAMILLE.get(f["nom"])
        vide = {"date": champ, "semaines": None, "sans_date": None, "semaine_partielle": None}
        if champ is None:
            aveugle.append(f"trouvailles : famille {nom} sans date nommée (DATE_PAR_FAMILLE) -- non comptée par semaine")
            out[nom] = {**vide, "raison": "sans_date_nommee"}
            continue
        if f.get("fichiers") is None or f.get("champs_introuvables") is None:
            out[nom] = {**vide, "raison": "famille_non_lue"}     # sa ligne est dans l'aveugle de l'index
            continue
        siens = [a for a in index["artefacts"] if a.get("famille") == nom]
        sans = dict(f["champs_introuvables"].get(champ) or {})
        jours = [a[champ] for a in siens if a.get(champ)]
        if len(jours) + sum(sans.values()) != len(siens) or len(siens) != f.get("indexes"):
            aveugle.append(f"trouvailles : famille {nom} : {len(jours)} daté(s) + {sum(sans.values())} sans date pour "
                           f"{len(siens)} artefact(s) servi(s), {f.get('indexes')} indexé(s) -- parité rompue, "
                           "servie à null")
            out[nom] = {**vide, "raison": "parite_rompue"}
            continue
        if champ == "date_ajout_git" and dates.get("historique") != "complet":
            raison = _RAISON_HISTORIQUE.get(dates.get("historique"), "git_indisponible") if dates else "dates_absentes"
            out[nom] = {**vide, "sans_date": sans, "raison": raison}
            continue
        borne = bornes[champ]
        futurs = sum(1 for j in jours if datetime.date.fromisoformat(j) > borne)
        if futurs:
            sans["date_future"] = sans.get("date_future", 0) + futurs
            aveugle.append(f"trouvailles : famille {nom} : {futurs} artefact(s) daté(s) après le {borne.isoformat()} "
                           f"({champ}) -- comptés dans sans_date sous date_future, jamais en semaines futures")
        semaines = semaines_denses([j for j in jours if datetime.date.fromisoformat(j) <= borne], borne.isoformat())
        out[nom] = {"date": champ, "semaines": semaines, "sans_date": sans,
                    "semaine_partielle": semaine_iso(borne.isoformat()) if semaines else None, "raison": None}
    return out


def _trouvailles(index, graphe, aveugle, now):
    rec = _famille(index, "record")
    partiels = None
    if rec is None or rec.get("fichiers") is None:
        aveugle.append("trouvailles : famille record non lue par l'index -- verdicts INCONNUS, jamais 0")
        verdicts = None
    else:
        illisibles = rec.get("illisibles") or []
        raisons = ", ".join(f"{r} : {n}" for r, n in
                            sorted(collections.Counter(str(i.get("raison")) for i in illisibles).items()))
        mal_types = ((rec.get("champs_introuvables") or {}).get("etat") or {}).get("type_inattendu", 0)
        if illisibles and not rec.get("indexes"):             # PyYAML absent : rien n'a été lu (I1-a, sonde S6)
            aveugle.append(f"trouvailles : aucun des {len(illisibles)} record(s) n'a été lu ({raisons}) -- verdicts "
                           "INCONNUS, jamais une liste vide")
            verdicts = None
        else:
            verdicts = [{"chemin": a["chemin"], "titre": a.get("titre"), "verdict": a["etat"], "gate": a.get("gate"),
                         "date_ajout_git": a.get("date_ajout_git")}
                        for a in index["artefacts"]
                        if a.get("famille") == "record" and a.get("etat_source") == "verdict"]
            partiels = bool(illisibles or mal_types)
            if illisibles:
                aveugle.append(f"trouvailles : {len(illisibles)} record(s) illisible(s) ({raisons}) -- liste des "
                               "verdicts PARTIELLE")
            if mal_types:
                aveugle.append(f"trouvailles : {mal_types} record(s) à état mal typé (verdict ou status non-chaîne, "
                               "type_inattendu) -- un verdict peut y manquer, liste PARTIELLE")
    if graphe.get("raison"):
        aveugle.append(f"trouvailles : {graphe.get('chemin')} {graphe['raison']} -- écart au graphe de records non "
                       "mesuré")
    elif verdicts is not None and graphe.get("verdicts") != len(verdicts):
        aveugle.append(f"trouvailles : {graphe.get('chemin')} compte {graphe.get('verdicts')} verdicts (records "
                       f"SDR/ADR/EDR/REF), l'index en lit {len(verdicts)} dans docs/EDR -- écart non attribué : graphe "
                       "périmé (tools/consolidate_records.py), verdict hors docs/EDR ou record illisible")
    return {"verdicts": verdicts, "verdicts_partiels": partiels, "compte_graphe": graphe.get("verdicts"),
            "par_semaine": _par_semaine(index, aveugle, now),
            "dates": dict(index["dates"]) if index.get("dates") else None}


def compute_science(index, pipeline, taxonomie, graphe, now):
    """`science_v1` — PUR ; chaque bloc null avec sa ligne quand sa source manque ; les lignes de l'index
    relayées sous « trouvailles : (index) »."""
    aveugle = []
    bloc_pipeline = _pipeline(index, pipeline, aveugle)
    bloc_taxonomie = _taxonomie(taxonomie, aveugle)
    if index.get("familles") is None or index.get("artefacts") is None:
        aveugle.append("trouvailles : index sans familles ou sans artefacts (mode dégradé de l'index) -- trouvailles "
                       "INCONNUES")
        bloc_trouvailles = None
    else:
        bloc_trouvailles = _trouvailles(index, graphe, aveugle, now)
    # Revue de la tâche 2 (mineurs 4 et 5) : la vue Science n'affiche que /science. Chaque ligne de l'index (âge
    # négatif de l'instantané, famille non lue, mode dégradé) est RELAYÉE telle quelle sous le préfixe du bloc
    # qu'elle qualifie — jamais `index:` en tête, réservé au service de l'index.
    aveugle.extend(f"trouvailles : (index) {a}" for a in index.get("aveugle") or [] if isinstance(a, str))
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
