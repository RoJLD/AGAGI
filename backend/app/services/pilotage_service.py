"""Service du pilotage : assemble `pilotage_v1` pour la route, en mémoire, SANS écrire un fichier.

⚠️ La flotte n'est pas recalculée sur le chemin du poll. Mesuré le 2026-09-24 (charge notée : 40 % de CPU,
9 processus python) : `tools.pm.snapshot.snapshot()` coûte 15,6 / 16,6 / 18,1 s — au-delà du timeout de
10 s du client — tandis que toute la roadmap coûte 0,70 s. Le poll sert donc le `BOARD.json` du tick PM
(dont le PM est l'unique writer) avec son ÂGE publié ; `frais=True` recalcule en mémoire, et seul un clic
explicite le déclenche.
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


def get_pilotage(ttl_s: float = _TTL_DEFAUT, frais: bool = False) -> dict:
    now = time.time()
    if not frais and _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    try:
        racine = pilotage.racine_depot()
        snap = snapshot(racine) if frais else None
        out = pilotage.compute_pilotage(
            snap,
            pilotage.read_backlog(racine),
            pilotage.read_records_graph(racine),
            pilotage.read_roles_counts(racine),
            pilotage.read_portes(racine),
            now,
            repo_root=racine,
            board=None if frais else pilotage.read_board(racine),
        )
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        out = {"schema": pilotage.SCHEMA, "generated_at": now, "repo_root": "",
               "aveugle": [f"pilotage: {type(exc).__name__}: {exc}"],
               "flotte": None, "roadmap": None, "portes": None, "charge": None}
    if not frais:
        _cache["at"], _cache["valeur"] = now, out
    return out
