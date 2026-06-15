# backend/app/routes/observability.py
"""Routes d'observabilité & provenance (C1) : santé KuzuDB, métriques logger, ledger des runs."""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..services.provenance_service import ProvenanceService

router = APIRouter()

_RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"
_svc = ProvenanceService(_RESULTS_DIR)


@router.get("/health/kuzu")
def health_kuzu() -> dict:
    return _svc.kuzu_health()


@router.get("/observability/logger")
def observability_logger() -> dict:
    return _svc.logger_metrics()


@router.get("/provenance")
def provenance_list() -> list:
    return _svc.list_runs()


@router.get("/provenance/{file_stem}")
def provenance_detail(file_stem: str) -> dict:
    run = _svc.get_run(file_stem)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run inconnu: {file_stem}")
    return run
