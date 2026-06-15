from fastapi import APIRouter, HTTPException, Query

from ..services.runs_service import runs_service

router = APIRouter()


@router.get("/runs")
def list_runs() -> list[dict]:
    return runs_service.list_runs()


@router.get("/runs/conditions")
def list_conditions() -> list[dict]:
    """Conditions = noms d'expériences (groupes de seeds), avec métriques disponibles."""
    return runs_service.list_conditions()


@router.get("/runs/compare")
def compare(
    a: str = Query(..., description="condition A (name)"),
    b: str = Query(..., description="condition B (name)"),
    metric: str = Query(..., description="métrique numérique à comparer"),
) -> dict:
    result = runs_service.compare(a, b, metric)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Aucune valeur pour metric={metric} sur {a}/{b}")
    return result


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = runs_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run introuvable: {run_id}")
    return run
