"""Service de l'index des artefacts (P2.87) : en mémoire, SANS écrire un fichier, et sans jamais DATER par git.

Les dates d'entrée dans le dépôt sont LUES dans `DATES_GIT.json` (écrit par le tick PM, là où l'historique est
complet) avec leur âge — l'image docker n'a ni git ni `.git` (spec §9, D1). La seule commande git que la requête
peut lancer est `rev-parse --git-common-dir`, qui situe le data/ du dépôt COMMUN (`snapshot.racine_commune`, P2.114) ;
sans git, elle échoue en silence et la racine du worktree sert (témoin : liste blanche sur `subprocess.Popen`).
Même filet que `pilotage_service` : import gardé et NOMMÉ, chaque bloc validé contre le modèle de la route AVANT
elle, mode dégradé servable.
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
from .pilotage_service import _EnveloppeRefusee, _ligne_de_refus, _resume, _servable, _texte_servable

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


def _echapper(valeur: Any) -> tuple[Any, int]:
    """`(valeur, n)` : toute chaîne (clé ou valeur, à toute profondeur) qui ne s'encode pas en UTF-8 devient son
    échappement VISIBLE (G2), `n` le compte. Revue du pas 2 (I2) : un seul titre porteur d'un surrogate faisait
    refuser les 780 artefacts d'un bloc."""
    if isinstance(valeur, str):
        e = _texte_servable(valeur)
        return e, int(e != valeur)
    if isinstance(valeur, dict):
        out, n = {}, 0
        for k, v in valeur.items():
            k2, nk = _echapper(k)
            v2, nv = _echapper(v)
            out[k2] = v2
            n += nk + nv
        return out, n
    if isinstance(valeur, list):
        out_l, n = [], 0
        for v in valeur:
            v2, nv = _echapper(v)
            out_l.append(v2)
            n += nv
        return out_l, n
    return valeur, 0


def _blocs_servables(out: dict, blocs: tuple = _BLOCS, adaptateurs: dict | None = None) -> dict:
    """Chaque bloc ÉCHAPPÉ puis validé contre SON modèle : un bloc refusé devient `null` + une ligne qui le nomme,
    les autres restent servis. Paramétré par les blocs d'une enveloppe : `science_service` (P2.84) s'en sert aussi.
    L'adaptateur est résolu HORS du filet : un bloc sans adaptateur est une erreur de programmation, qui lève et que
    le filet global NOMME — jamais « refusé par le modèle » (revue du pas 2, M5)."""
    adaptateurs = _ADAPTATEURS if adaptateurs is None else adaptateurs
    out = dict(out)
    aveugle = list(out.get("aveugle") or [])
    for cle in blocs:
        if out.get(cle) is None:
            continue
        adaptateur = adaptateurs[cle]
        out[cle], n = _echapper(out[cle])
        if n:
            aveugle.append(f"{cle} : {n} chaîne(s) non encodable(s) en UTF-8 (surrogate isolé, nom ou contenu de "
                           "fichier) servie(s) ÉCHAPPÉE(S), visible(s) -- le bloc reste servi")
        try:
            _servable(adaptateur, out[cle], cle)
        except Exception as exc:                           # noqa: BLE001 — refus NOMMÉ, jamais un 500
            aveugle.append(_ligne_de_refus(cle, exc, "les autres blocs restent servis"))
            out[cle] = None
    out["aveugle"] = [_texte_servable(a) if isinstance(a, str) else a for a in aveugle]
    return out


def _lire_dates(racine: str) -> dict:
    """`read_dates` en REFUS LOCAL (revue du pas 2, I3) : un DATES_GIT.json hostile rend `dates` null avec sa ligne,
    jamais les quatre blocs à null."""
    try:
        return index_artefacts.read_dates(racine)
    except Exception as exc:                               # noqa: BLE001 — NOMMÉ dans la ligne « dates : … »
        return {"doc": None, "chemin": "(non résolu)", "raison": f"illisible ({type(exc).__name__}: {exc})"}


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
        out = index_artefacts.indexer(racine, _lire_dates(racine), now)
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
