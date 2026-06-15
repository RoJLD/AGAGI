"""Routes REST du multi-run flatland (C2) : créer / lister / supprimer des runs A/B live."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..flatland_server import flatland_manager, RunCapExceeded

router = APIRouter()


class CreateRunBody(BaseModel):
    config_overrides: Optional[dict] = None
    pop_size: int = 10
    label: Optional[str] = None


@router.post("/runs")
def create_run(body: CreateRunBody) -> dict:
    try:
        run_id = flatland_manager.create_run(body.config_overrides, body.pop_size, body.label)
    except RunCapExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"run_id": run_id}


@router.get("/runs")
def list_runs() -> list:
    return flatland_manager.list_runs()


@router.delete("/runs/{run_id}")
def delete_run(run_id: str) -> dict:
    if not flatland_manager.stop_run(run_id):
        raise HTTPException(status_code=404, detail=f"run inconnu ou non supprimable: {run_id}")
    return {"stopped": True}
