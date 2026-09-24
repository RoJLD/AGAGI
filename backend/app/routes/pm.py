"""Route du pilotage : une seule lecture, aucun écrit.

`frais=1` recalcule la flotte en mémoire (≈ 18 s mesurés) : réservé à un clic explicite, jamais au poll.
"""
from fastapi import APIRouter

from ..schemas import PilotageV1
from ..services.pilotage_service import get_pilotage

router = APIRouter()


@router.get("/pilotage", response_model=PilotageV1, response_model_by_alias=True)
def pilotage(frais: bool = False) -> dict:
    return get_pilotage(frais=frais)
