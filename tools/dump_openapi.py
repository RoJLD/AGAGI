"""Dump le schéma OpenAPI de l'app FastAPI vers frontend/openapi.json (source du codegen TS).

Usage : PYTHONPATH=. python tools/dump_openapi.py

Sortie déterministe (indent + clés triées) pour un diff git stable en CI :
le pipeline régénère puis vérifie `git diff --exit-code` -> le drift schéma↔types
est supprimé par GÉNÉRATION (et non plus seulement détecté).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "openapi.json"


def main() -> None:
    from backend.app.main import app  # import lourd (démarre AsyncLogger/Kuzu) — d'où l'os._exit ci-dessous

    spec = app.openapi()
    OUT.write_text(json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[openapi] {len(spec.get('paths', {}))} paths -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)  # coupe court aux threads de fond démarrés à l'import (sinon le process traîne)
