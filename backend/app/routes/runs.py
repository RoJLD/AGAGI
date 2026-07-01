from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..schemas import ABCompareResult, ConditionSummary, Decomposition, DistributionSummary, ForageFunnel, NoteCreate, NoteFeedItem, RunDetail, RunNote, RunSummary, SweepResult
from ..services.runs_service import runs_service

router = APIRouter()


@router.get("/runs", response_model=list[RunSummary])
def list_runs() -> list[dict]:
    return runs_service.list_runs()


@router.get("/runs/conditions", response_model=list[ConditionSummary])
def list_conditions() -> list[dict]:
    """Conditions = noms d'expériences (groupes de seeds), avec métriques disponibles."""
    return runs_service.list_conditions()


@router.get("/sweeps", response_model=list[SweepResult])
def list_sweeps() -> list[dict]:
    """Sweeps = runs balayant un paramètre (knob+levels+séries) ; paysage métrique-vs-paramètre."""
    return runs_service.list_sweeps()


@router.get("/runs/distributions", response_model=list[DistributionSummary])
def list_distributions(metric: str = Query(..., description="métrique numérique à distribuer")) -> list[dict]:
    """Distributions par seed des conditions portant `metric` (vue cohorte)."""
    return runs_service.list_distributions(metric)


@router.get("/runs/compare", response_model=ABCompareResult)
def compare(
    a: str = Query(..., description="condition A (name)"),
    b: str = Query(..., description="condition B (name)"),
    metric: str = Query(..., description="métrique numérique à comparer"),
) -> dict:
    result = runs_service.compare(a, b, metric)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Aucune valeur pour metric={metric} sur {a}/{b}")
    return result


class EdrLinks(BaseModel):
    edr: list[int]


@router.get("/runs/edr-links", response_model=dict[str, list[str]])
def edr_links() -> dict:
    """{edr: [run_id, ...]} — alimente les badges « runs liés » du dashboard EDR."""
    return runs_service.edr_links()


@router.get("/runs/article-links", response_model=dict[str, list[str]])
def article_links() -> dict:
    """{run_id: [article_id, ...]} — articles Sociologue liés à chaque run (via condition comparée)."""
    return runs_service.article_links()


@router.patch("/runs/{run_id}/links")
def set_run_links(run_id: str, body: EdrLinks) -> dict:
    """Associe une liste d'EDR à un run (store results/run_links.json, n'altère pas le run)."""
    return runs_service.set_run_edr_links(run_id, body.edr)


@router.get("/runs/{run_id}/notes", response_model=list[RunNote])
def list_notes(run_id: str) -> list[dict]:
    """Notes du carnet pour un run (triées par horodatage croissant)."""
    return runs_service.list_notes(run_id)


@router.post("/runs/{run_id}/notes", response_model=RunNote)
def add_note(run_id: str, body: NoteCreate) -> dict:
    """Ajoute une note horodatée au run."""
    note = runs_service.add_note(run_id, body.text)
    if note is None:
        raise HTTPException(status_code=400, detail="Le texte de la note ne peut pas être vide.")
    return note


@router.delete("/runs/{run_id}/notes/{note_id}")
def delete_note(run_id: str, note_id: str) -> dict:
    """Supprime une note du run."""
    if not runs_service.delete_note(run_id, note_id):
        raise HTTPException(status_code=404, detail="Note introuvable.")
    return {"deleted": True}


@router.get("/notes", response_model=list[NoteFeedItem])
def all_notes() -> list[dict]:
    """Flux agrégé de toutes les notes (carnet de labo), trié par horodatage décroissant."""
    return runs_service.all_notes()


@router.get("/runs/decompositions", response_model=list[Decomposition])
def list_decompositions() -> list[dict]:
    """Decompositions energetiques (budget par phase + sous-decompo biologie) pour la vue Energie."""
    return runs_service.list_decompositions()


@router.get("/runs/forage-funnels", response_model=list[ForageFunnel])
def list_forage_funnels() -> list[dict]:
    """Entonnoirs de forage (acquisition : approche/capture/revenu par niveau de métab) pour la vue Forage."""
    return runs_service.list_forage_funnels()


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str) -> dict:
    run = runs_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run introuvable: {run_id}")
    return run
