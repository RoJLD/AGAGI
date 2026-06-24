# backend/app/security.py
"""Auth opt-in par token (C4). API_TOKEN absent -> ouvert (dev local) ; defini -> exige le header."""
import hmac
import os

from fastapi import Header, HTTPException

API_TOKEN = os.environ.get("AGISEED_API_TOKEN") or None   # "" ou absent -> None (ouvert)


def _matches(candidate: str | None) -> bool:
    """Comparaison constant-time (hmac.compare_digest) -> pas de canal temporel sur le token.
    candidate None/non-ASCII -> False sans lever."""
    if candidate is None:
        return False
    try:
        return hmac.compare_digest(candidate.encode("utf-8"), API_TOKEN.encode("utf-8"))
    except (AttributeError, UnicodeError):
        return False


def require_token(x_api_token: str | None = Header(default=None),
                  authorization: str | None = Header(default=None)) -> None:
    """Dependency FastAPI : laisse passer si API_TOKEN est None, sinon exige X-API-Token ou Bearer."""
    if API_TOKEN is None:
        return
    if _matches(x_api_token):
        return
    if authorization and _matches(authorization.removeprefix("Bearer ").strip()):
        return
    raise HTTPException(status_code=401, detail="Token invalide ou manquant")
