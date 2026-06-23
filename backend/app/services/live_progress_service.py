"""Tail incrémental du puits de progression live (results/live_progress.jsonl).

read_new() renvoie les événements ajoutés depuis le dernier appel. On ne consomme que
les lignes complètes (terminées par \\n) : une ligne partielle (write en cours) est
gardée pour le prochain appel. Reset de l'offset si le fichier a rétréci (nouveau run
qui a tronqué). Ligne JSON invalide -> ignorée. Aucune dépendance à la simulation.
"""
from __future__ import annotations

import json
from pathlib import Path


class LiveProgressTail:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._offset = 0

    def reset(self) -> None:
        self._offset = 0

    def read_new(self) -> list[dict]:
        if not self.path.exists():
            self._offset = 0
            return []
        size = self.path.stat().st_size
        if size < self._offset:  # fichier tronqué -> nouveau run
            self._offset = 0
        if size == self._offset:
            return []
        start = self._offset
        with self.path.open("rb") as f:
            f.seek(start)
            raw = f.read()
        nl = raw.rfind(b"\n")
        if nl == -1:
            return []  # pas encore de ligne complète
        consumed = raw[: nl + 1]
        self._offset = start + len(consumed)
        events: list[dict] = []
        for line in consumed.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
