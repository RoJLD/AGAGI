"""Service du lot 2 « Science » (P2.84) : en mémoire, SANS écrire un fichier, et sans jamais DATER par git.

L'index vient de `index_service.get_index()` — le MÊME cache que `/api/pm/index`, jamais recalculé deux fois (M6) ; la
seule commande git de la requête est donc celle de l'index (`rev-parse --git-common-dir`). Même filet que
`pilotage_service` : import gardé et NOMMÉ, chaque bloc échappé puis validé contre le modèle de la route AVANT elle
(`index_service._blocs_servables`, partagé), mode dégradé servable (`science: …`). Un index en mode dégradé n'est PAS
un mode dégradé de science : `compute_science` sert alors `trouvailles` à null avec sa ligne.
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
            _servable(_ENVELOPPE, out, "science")
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
