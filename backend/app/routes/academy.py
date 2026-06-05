from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from ..services.data_service import ExperimentDataService

router = APIRouter()
results_dir = Path(__file__).resolve().parents[3] / "results"
service = ExperimentDataService(results_dir)


@router.get("/academy")
def get_academy() -> dict:
    return service.get_academy_data().model_dump()
