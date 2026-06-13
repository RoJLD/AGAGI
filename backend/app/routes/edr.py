"""Route /api/edr — sert les découvertes EDR curées (results/edr_findings.json) au dashboard.

Rend visibles les vraies expériences du journal (compétence 081, bruit de fitness 078, langage 072…),
là où le frontend ne montrait que des portes logiques + un flatland générique.
"""
import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _findings_path() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:                       # robuste à la profondeur backend/app/routes
        cand = parent / "results" / "edr_findings.json"
        if cand.exists():
            return cand
    return None


@router.get("/edr")
def get_edr_findings() -> dict:
    path = _findings_path()
    if path is None:
        return {"title": "Découvertes EDR", "findings": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - garde-fou de lecture
        return {"title": "Découvertes EDR", "findings": [], "error": str(exc)}
