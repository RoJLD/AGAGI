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
    except (ValueError, RecursionError):                 # imbrication profonde : RecursionError, pas ValueError
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
    if rel not in suivis:                                 # hors de l'instantané : l'histoire peut garder l'ajout d'un
        return None, "absent_des_dates"                   # chemin retiré depuis, jamais une date pour le fichier d'ici
    d = doc["dates"].get(rel)
    return (d, None) if d is not None else (None, "sans_ajout_trouve")


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
        parties = s.split("/")                            # groupé par RÉPERTOIRE (deux niveaux au plus), jamais
        compte["/".join(parties[:2]) if len(parties) > 2 else parties[0]] += 1   # par fichier : docs/X.md -> docs
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
                 "exclus": None, "fichiers": None, "indexes": None, "illisibles": None,    # null tant que NON LU
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
    `tronque` : `--depth 1` date tout du jour du clone (B3).

    Revue du pas 1 : `log.showRoot=true` figé (sinon le commit racine perd ses fichiers) ; `--is-shallow-repository`
    n'est lu que s'il rend `true` ou `false` (un git ancien renvoie le drapeau tel quel, code 0) ; un `GIT_DIR` hérité
    d'un AUTRE dépôt est refusé (`--show-toplevel` rend alors le cwd : seul `--absolute-git-dir` le voit) ; `suivis`
    = les fichiers de HEAD, jamais l'index (l'instantané publie `head`)."""
    from tools._git_env import env_isole
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
    vu, err = _git(racine, env, "rev-parse", "--absolute-git-dir")
    propre, err_propre = _git(racine, env_isole(), "rev-parse", "--absolute-git-dir")
    if vu is None or propre is None:
        doc["raison"] = f"répertoire git illisible : {err or err_propre}"
        return doc
    if os.path.normcase(os.path.realpath(vu.strip())) != os.path.normcase(os.path.realpath(propre.strip())):
        doc["raison"] = (f"dépôt git hérité {vu.strip()} différent de celui de la racine {propre.strip()} -- fuite de "
                         "GIT_DIR ou GIT_WORK_TREE dans l'environnement")
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
    if peu.strip() != "false":
        doc["raison"] = (f"état de l'historique illisible : rev-parse --is-shallow-repository a rendu {peu.strip()!r} "
                         "(git antérieur à 2.15 ?)")
        return doc
    reps = sorted({r for r in (_rel(racine, f.repertoire(racine)) for f in FAMILLES) if r})
    out, err = _git(racine, env, "-c", "diff.renames=false", "-c", "log.showRoot=true", "log", "--no-renames",
                    "--diff-filter=A", "--format=%x1e%ct", "--name-only", "--", *reps)
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
    ls, err = _git(racine, env, "ls-tree", "-r", "-z", "--name-only", "HEAD", *zones)
    if ls is None:
        doc["raison"] = f"git ls-tree HEAD : {err}"
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
        n = "aucune date publiée" if doc["dates"] is None else f"{len(doc['dates'])} date(s)"
        print(f"[index] {chemin} : historique {doc['historique']}, {n}" + (f" -- {doc['raison']}" if doc["raison"] else ""))
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
