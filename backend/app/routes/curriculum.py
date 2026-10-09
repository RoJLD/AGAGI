"""
backend/app/routes/curriculum.py — Router FastAPI pour le Curriculum Tri-Mondes & Phylogénèse (Arc 5).
Expose l'historique des runs persistés dans KuzuDB et permet le déclenchement de campagnes d'évolution.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime

from src.evolution.triworld_curriculum import TriWorldCurriculum, TriWorldCurriculumConfig
from src.graph_rag.experiment_tracker import ExperimentGraph
from src.graph_rag.async_logger import logger as async_logger

router = APIRouter(prefix="", tags=["Curriculum"])

# Cache d'état pour les runs asynchrones
_CURRICULUM_STATE = {
    "is_running": False,
    "last_run_id": None,
    "last_report": None,
    "error": None,
}


class RunCurriculumRequest(BaseModel):
    pop_size: int = Field(default=4, ge=2, le=50, description="Taille de la population")
    eras: int = Field(default=1, ge=1, le=10, description="Nombre d'ères par monde")
    ticks: int = Field(default=10, ge=5, le=100, description="Ticks max par ère")
    mutation_rate: float = Field(default=0.02, ge=0.001, le=0.5, description="Taux de mutation")
    isocaloric: bool = Field(default=True, description="Active le métabolisme isocalorique contrôlé")


class PhylogeneticRunSummary(BaseModel):
    id: str
    transfer_ratio: float
    stone_score: float
    agri_score: float
    indus_score: float
    status: str
    timestamp: str


def _get_graph() -> ExperimentGraph:
    shared_db = async_logger.get_db()
    if shared_db is not None:
        return ExperimentGraph(db=shared_db)
    db_path = str(Path(__file__).resolve().parents[3] / "data" / "kuzu_graph.db")
    return ExperimentGraph(db_path=db_path)


@router.get("/history", response_model=List[PhylogeneticRunSummary])
def get_curriculum_history() -> List[Dict[str, Any]]:
    """Récupère l'historique de tous les runs phylogénétiques tri-mondes enregistrés dans KuzuDB."""
    try:
        graph = _get_graph()
        return graph.get_phylogenetic_runs()
    except Exception as e:
        # Tolérance si la base n'est pas encore initialisée
        return []


@router.get("/status")
def get_curriculum_status() -> Dict[str, Any]:
    """Retourne l'état courant d'exécution du curriculum."""
    return dict(_CURRICULUM_STATE)


@router.post("/run")
def trigger_curriculum_run(req: RunCurriculumRequest) -> Dict[str, Any]:
    """Déclenche un cycle complet de curriculum tri-mondes (Monde 1 -> Monde 2 -> Monde 3) et persiste dans KuzuDB."""
    if _CURRICULUM_STATE["is_running"]:
        raise HTTPException(status_code=409, detail="Un curriculum est déjà en cours d'exécution.")

    _CURRICULUM_STATE["is_running"] = True
    _CURRICULUM_STATE["error"] = None
    try:
        cfg = TriWorldCurriculumConfig(
            pop_size=req.pop_size,
            eras_per_world=req.eras,
            max_ticks_per_era=req.ticks,
            mutation_rate=req.mutation_rate,
            isocaloric=req.isocaloric,
        )
        curriculum = TriWorldCurriculum(cfg)
        report = curriculum.run_full_curriculum()

        # Persistance dans KuzuDB
        run_id = curriculum.persist_to_kuzudb(report)
        _CURRICULUM_STATE["last_run_id"] = run_id
        _CURRICULUM_STATE["last_report"] = {
            "run_id": run_id,
            "transfer_ratio": report["transfer_ratio"],
            "scores_progression": report["scores_progression"],
            "stages": [
                {
                    "stage_name": s["stage_name"],
                    "best_final_score": s["best_final_score"],
                    "mean_final_score": s["mean_final_score"],
                }
                for s in report["stages"]
            ],
            "status": report["status"],
        }
        return _CURRICULUM_STATE["last_report"]
    except Exception as e:
        _CURRICULUM_STATE["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Erreur d'exécution du curriculum: {e}")
    finally:
        _CURRICULUM_STATE["is_running"] = False
