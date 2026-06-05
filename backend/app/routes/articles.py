from fastapi import APIRouter
from pathlib import Path

from ..schemas import Article
from ..services.data_service import ExperimentDataService

router = APIRouter()
results_dir = Path(__file__).resolve().parents[3] / "results"
service = ExperimentDataService(results_dir)

@router.get("/articles", response_model=list[Article])
def get_articles() -> list[Article]:
    return service.get_articles()
