"""Puits de progression live (/ws/evolution). Append-only, opt-in via env.

emit_progress n'écrit QUE si AGISEED_LIVE_PROGRESS est défini (posé par le sandbox au
lancement d'un run). Sinon : no-op total -> aucun impact sur les runs CLI / tests /
sessions parallèles. Ne propage jamais d'exception : la télémétrie ne doit pas pouvoir
faire échouer le run qu'elle observe.
"""
from __future__ import annotations

import json
import os

ENV_VAR = "AGISEED_LIVE_PROGRESS"


def emit_progress(event: dict) -> None:
    path = os.environ.get(ENV_VAR)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass
