# tests/test_security.py
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import security


def test_require_token_open_when_unset(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", None)
    assert security.require_token(x_api_token=None, authorization=None) is None


def test_require_token_enforced_when_set(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    with pytest.raises(HTTPException):
        security.require_token(x_api_token=None, authorization=None)
    with pytest.raises(HTTPException):
        security.require_token(x_api_token="wrong", authorization=None)
    assert security.require_token(x_api_token="s3cret", authorization=None) is None
    assert security.require_token(x_api_token=None, authorization="Bearer s3cret") is None


def test_mutating_endpoint_401_without_token(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    from backend.app.main import app
    client = TestClient(app)
    # /api/sandbox/stop est mutateur et idempotent (rien a nettoyer)
    assert client.post("/api/sandbox/stop").status_code == 401
    assert client.post("/api/sandbox/stop", headers={"X-API-Token": "s3cret"}).status_code == 200


def test_get_endpoints_stay_open(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    from backend.app.main import app
    client = TestClient(app)
    assert client.get("/api/sandbox/status").status_code == 200   # GET non protege
