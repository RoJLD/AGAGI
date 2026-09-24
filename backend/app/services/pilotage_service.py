"""Service du pilotage : assemble `pilotage_v1` pour la route, en mémoire, SANS écrire un fichier.

⚠️ La flotte n'est pas recalculée sur le chemin du poll. Mesuré le 2026-09-24 (charge notée : 40 % de CPU,
9 processus python) : `tools.pm.snapshot.snapshot()` coûte 15,6 / 16,6 / 18,1 s — au-delà du timeout de
10 s du client — tandis que toute la roadmap coûte 0,70 s. Le poll sert donc le `BOARD.json` du tick PM
(dont le PM est l'unique writer) avec son ÂGE publié ; `frais=True` recalcule en mémoire, et seul un clic
explicite le déclenche.

⚠️ `frais=True` est REFUSÉ, jamais silencieusement, si le DERNIER tableau connu (`BOARD.json`, jamais un
nouveau `snapshot()` — ce serait le coût de 18 s qu'on refuse d'engager) annonce une simulation en vol
(`charge_connue.sims_en_vol > 0`, spec §5) : recalculer la flotte pendant qu'une sim tourne, c'est la
contention kuzu / le coût contaminé que l'alerte A5 du board interdit déjà côté PM. Sans tableau lisible, il
n'y a pas de mesure sur laquelle refuser : le recalcul est lancé, et la charge INCONNUE est dite (F6).
Limite connue, non corrigée ici (elle touche `snapshot.py`, qui appartient au PM) : `snapshot(racine)` lit
bulletins et registre par `paths.*`, donc depuis un worktree, sans variable d'environnement, il lit le
`data/` du WORKTREE et non celui du dépôt commun.

⚠️ Chaque bloc est validé ICI contre le modèle nommé que la route applique (`PilotageV1`), puis passé au JSON
strict comme la route le fera : `charge`, `flotte` et `roadmap.portes_agi` recopient des sources que
`pilotage.py` ne possède pas (`BOARD.json`, `ROLES_COUNTS.json`, `records_graph.json`), et un seul champ de type
inattendu donnait un 500 à la sérialisation, APRÈS le filet d'exception, sans ligne d'aveuglement (F3). Un bloc
refusé devient `None` plus une ligne qui le NOMME ; les autres restent servis.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any

from pydantic import TypeAdapter

from tools.pm import pilotage
from tools.pm.snapshot import snapshot

from ..schemas import PilotageV1

_TTL_DEFAUT = 30.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}

# Le type de chaque bloc est LU sur le modèle de la route, jamais recopié : un bloc validé ici est validé
# exactement comme `response_model=PilotageV1` le fera.
_BLOCS = ("flotte", "roadmap", "portes", "charge")
_ADAPTATEURS = {cle: TypeAdapter(PilotageV1.model_fields[cle].annotation) for cle in _BLOCS}
_ENVELOPPE = TypeAdapter(PilotageV1)


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def _servable(adaptateur: TypeAdapter, valeur: Any) -> None:
    """Rejoue ce que fait la route (FastAPI 0.128 : `validate_python(..., from_attributes=True)`, puis
    `dump_python(mode="json", by_alias=True)`, puis `json.dumps(..., allow_nan=False)`) ; lève si elle
    refuserait. Le JSON strict compte : un `float('inf')` VALIDE pour pydantic fait encore un 500 au rendu."""
    v = adaptateur.validate_python(valeur, from_attributes=True)
    json.dumps(adaptateur.dump_python(v, mode="json", by_alias=True), ensure_ascii=False, allow_nan=False)


def _resume(exc: Exception) -> str:
    """Le refus RÉSUMÉ — jamais l'erreur pydantic vidée en entier dans une ligne `aveugle`."""
    errors = getattr(exc, "errors", None)
    if callable(errors):
        try:
            liste = errors(include_url=False)
            premiere = liste[0]
            loc = ".".join(str(x) for x in premiere.get("loc", ())) or "(racine)"
            return f"{len(liste)} erreur(s) de validation, la première sur {loc} : {premiere.get('msg')}"
        except Exception:                                  # noqa: BLE001 — le résumé ne doit jamais lever
            pass
    return f"{type(exc).__name__}: {str(exc)[:160]}"


def _blocs_servables(out: dict) -> dict:
    """Met à `None` tout bloc que la route refuserait, avec une ligne qui le NOMME ; les autres restent."""
    out = dict(out)
    aveugle = list(out.get("aveugle") or [])
    for cle in _BLOCS:
        if out.get(cle) is None:
            continue
        try:
            _servable(_ADAPTATEURS[cle], out[cle])
        except Exception as exc:                           # noqa: BLE001 — refus NOMMÉ, jamais un 500
            aveugle.append(f"{cle} : bloc refusé par le modèle de la route ({_resume(exc)}) -- servi à null, "
                           "les autres blocs restent servis")
            out[cle] = None
    out["aveugle"] = aveugle
    return out


def _sims_en_vol_dernier_tableau(racine: str) -> float | None:
    """Lit le DERNIER `BOARD.json` connu (jamais un `snapshot()` neuf) pour juger si `frais=1` doit être
    refusé. `None` si le tableau est absent, illisible, ou ne MESURE pas `sims_en_vol` (absent, `null`,
    booléen, non fini) : un refus se prononce sur une mesure, jamais sur une absence — `get_pilotage` suit
    alors son chemin normal et DIT que la charge était inconnue."""
    try:
        dernier = pilotage.read_board(racine)
    except Exception:                                      # noqa: BLE001 — un tableau illisible ne bloque rien
        return None
    if not isinstance(dernier, dict):
        return None
    cc = dernier.get("charge_connue")
    if not isinstance(cc, dict):
        return None
    sims = cc.get("sims_en_vol")
    if isinstance(sims, bool) or not isinstance(sims, (int, float)) or not math.isfinite(sims):
        return None
    return sims


def get_pilotage(ttl_s: float = _TTL_DEFAUT, frais: bool = False) -> dict:
    now = time.time()
    if not frais and _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    racine = None
    refus_frais = None
    sans_mesure = None
    effectif = frais
    try:                                                   # TOUT dans le filet, résolution de la racine comprise (F7)
        racine = pilotage.racine_depot()
        if frais:
            sims = _sims_en_vol_dernier_tableau(racine)
            if sims is None:
                sans_mesure = ("frais=1 accepté SANS mesure de charge (dernier tableau absent, illisible ou "
                               "sans sims_en_vol) -- recalcul lancé à l'aveugle")
            elif sims > 0:
                effectif = False
                refus_frais = (f"frais=1 refusé : {sims:g} simulation(s) en vol d'après le dernier tableau "
                               "connu -- recalcul de la flotte NON déclenché (charge), poll normal servi")
        snap = snapshot(racine) if effectif else None
        out = pilotage.compute_pilotage(
            snap,
            pilotage.read_backlog(racine),
            pilotage.read_records_graph(racine),
            pilotage.read_roles_counts(racine),
            pilotage.read_portes(racine),
            now,
            repo_root=racine,
            board=None if effectif else pilotage.read_board(racine),
        )
        out = _blocs_servables(out)
        _servable(_ENVELOPPE, out)                         # filet final : l'enveloppe entière passe la route
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        out = {"schema": pilotage.SCHEMA, "generated_at": now, "repo_root": racine,
               "aveugle": [f"pilotage: {type(exc).__name__}: {exc}"],
               "flotte": None, "roadmap": None, "portes": None, "charge": None}
    if not effectif:
        _cache["at"], _cache["valeur"] = now, out
    ajouts = [a for a in (refus_frais, sans_mesure) if a]
    if ajouts:
        out = dict(out)
        out["aveugle"] = list(out.get("aveugle") or []) + ajouts
    return out
