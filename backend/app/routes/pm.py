"""Route du pilotage : une seule lecture, aucun écrit.

`frais=1` recalcule la flotte en mémoire (≈ 18 s mesurés) : réservé à un clic explicite, jamais au poll.
"""
from fastapi import APIRouter

from ..schemas import IndexV1, PilotageV1
from ..services.index_service import get_index
from ..services.pilotage_service import get_pilotage

router = APIRouter()


@router.get("/pilotage", response_model=PilotageV1, response_model_by_alias=True)
def pilotage(frais: bool = False) -> dict:
    return get_pilotage(frais=frais)


@router.get("/index", response_model=IndexV1, response_model_by_alias=True)
def index() -> dict:
    """Index des artefacts (P2.87) : lu des fichiers, jamais daté par git dans la requête (dates lues dans
    DATES_GIT.json, avec leur âge) ; cache 60 s."""
    return get_index()
