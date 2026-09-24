"""Service du pilotage : assemble `pilotage_v1` pour la route, en mémoire, SANS écrire un fichier.

⚠️ La flotte n'est pas recalculée sur le chemin du poll. Mesuré le 2026-09-24 (charge notée : 40 % de CPU,
9 processus python) : `tools.pm.snapshot.snapshot()` coûte 15,6 / 16,6 / 18,1 s — au-delà du timeout de
10 s du client — tandis que toute la roadmap coûte 0,70 s. Le poll sert donc le `BOARD.json` du tick PM
(dont le PM est l'unique writer) avec son ÂGE publié ; `frais=True` recalcule en mémoire, et seul un clic
explicite le déclenche.

⚠️ `frais=True` est REFUSÉ, jamais silencieusement, si le DERNIER tableau connu (`BOARD.json`, jamais un
nouveau `snapshot()` — ce serait le coût de 18 s qu'on refuse d'engager) annonce une simulation en vol
(`charge_connue.sims_en_vol > 0`, spec §5) : recalculer la flotte pendant qu'une sim tourne, c'est la
contention kuzu / le coût contaminé que l'alerte A5 du board interdit déjà côté PM.
"""
from __future__ import annotations

import time
from typing import Any

from tools.pm import pilotage
from tools.pm.snapshot import snapshot

_TTL_DEFAUT = 30.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def _sims_en_vol_dernier_tableau(racine: str) -> float | None:
    """Lit le DERNIER `BOARD.json` connu (jamais un `snapshot()` neuf) pour juger si `frais=1` doit être
    refusé. `None` si le tableau est absent ou illisible : un refus se prononce sur une mesure, jamais
    sur une absence — donc pas de refus dans ce cas, `get_pilotage` suit son chemin normal."""
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
    return sims if isinstance(sims, (int, float)) else None


def get_pilotage(ttl_s: float = _TTL_DEFAUT, frais: bool = False) -> dict:
    now = time.time()
    if not frais and _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    racine = pilotage.racine_depot()
    refus_frais = None
    effectif = frais
    if frais:
        sims = _sims_en_vol_dernier_tableau(racine)
        if sims is not None and sims > 0:
            effectif = False
            refus_frais = (f"frais=1 refusé : {sims:g} simulation(s) en vol d'après le dernier tableau "
                           "connu -- recalcul de la flotte NON déclenché (charge), poll normal servi")
    try:
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
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        out = {"schema": pilotage.SCHEMA, "generated_at": now, "repo_root": None,
               "aveugle": [f"pilotage: {type(exc).__name__}: {exc}"],
               "flotte": None, "roadmap": None, "portes": None, "charge": None}
    if not effectif:
        _cache["at"], _cache["valeur"] = now, out
    if refus_frais:
        out = dict(out)
        out["aveugle"] = list(out.get("aveugle") or []) + [refus_frais]
    return out
