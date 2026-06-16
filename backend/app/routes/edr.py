"""Route /api/edr — sert les découvertes EDR curées (results/edr_findings.json) au dashboard.

Rend visibles les vraies expériences du journal (compétence 081, bruit de fitness 078, langage 072…),
là où le frontend ne montrait que des portes logiques + un flatland générique.
"""
import json
import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _findings_path() -> Path | None:
    # 1) emplacement VERSIONNÉ (backend/app/edr_findings.json) ; 2) results/ (dev local, gitignoré).
    committed = Path(__file__).resolve().parent.parent / "edr_findings.json"
    if committed.exists():
        return committed
    here = Path(__file__).resolve()
    for parent in here.parents:
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


def _edr_docs_dir() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "docs" / "EDR"
        if cand.is_dir():
            return cand
    return None


@router.get("/edr/docs")
def list_edr_docs() -> list[dict]:
    """Tous les EDR documentés (docs/EDR/NNN_*.md) — couverture 100% au frontend.
    Le frontend croise avec les findings curés pour signaler les EDR pas encore mis en carte."""
    d = _edr_docs_dir()
    out: list[dict] = []
    if d is not None:
        for p in d.glob("[0-9][0-9][0-9]_*.md"):
            m = re.match(r"^(\d{3})_(.+)\.md$", p.name)
            if m:
                out.append({"edr": int(m.group(1)), "title": m.group(2).replace("_", " "), "file": p.name})
    out.sort(key=lambda x: x["edr"], reverse=True)
    return out
