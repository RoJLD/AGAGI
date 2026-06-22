# backend/app/security.py
"""Auth opt-in par token (C4). API_TOKEN absent -> ouvert (dev local) ; defini -> exige le header."""
import os

from fastapi import Header, HTTPException

API_TOKEN = os.environ.get("AGISEED_API_TOKEN") or None   # "" ou absent -> None (ouvert)


def require_token(x_api_token: str | None = Header(default=None),
                  authorization: str | None = Header(default=None)) -> None:
    """Dependency FastAPI : laisse passer si API_TOKEN est None, sinon exige X-API-Token ou Bearer."""
    if API_TOKEN is None:
        return
    if x_api_token == API_TOKEN:
        return
    if authorization and authorization.removeprefix("Bearer ").strip() == API_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Token invalide ou manquant")
