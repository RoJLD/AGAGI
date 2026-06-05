from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import ExperimentDetail, ExperimentSummary
from ..services.data_service import ExperimentDataService

router = APIRouter()
results_dir = Path(__file__).resolve().parents[3] / "results"
service = ExperimentDataService(results_dir)


@router.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments() -> list[ExperimentSummary]:
    return service.list_experiments()


@router.get("/experiments/{gate}", response_model=ExperimentDetail)
def get_experiment_detail(gate: str) -> ExperimentDetail:
    try:
        return service.get_detail(gate)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Expérience introuvable: {gate}") from exc


@router.get("/experiments/{gate}/history")
def get_experiment_history(gate: str):
    try:
        return service.get_detail(gate).history
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Historique introuvable: {gate}") from exc


@router.get("/experiments/{gate}/graph")
def get_experiment_graph(gate: str) -> dict:
    try:
        return service.get_graph(gate)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Topologie introuvable: {gate}") from exc


@router.get("/experiments/{gate}/graphviz")
def get_experiment_graphviz(gate: str) -> str:
    try:
        return service.get_dot(gate)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Graphviz non trouvé pour: {gate}") from exc
