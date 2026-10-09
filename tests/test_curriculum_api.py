"""
tests/test_curriculum_api.py — Validation des endpoints FastAPI du Curriculum Tri-Mondes.
Vérifie :
- GET /api/curriculum/status
- GET /api/curriculum/history
- POST /api/curriculum/run
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_curriculum_status_endpoint():
    response = client.get("/api/curriculum/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert isinstance(data["is_running"], bool)


def test_curriculum_history_endpoint():
    response = client.get("/api/curriculum/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_curriculum_run_endpoint():
    payload = {
        "pop_size": 3,
        "eras": 1,
        "ticks": 5,
        "mutation_rate": 0.01
    }
    response = client.post("/api/curriculum/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "transfer_ratio" in data
    assert len(data["stages"]) == 3
    assert data["status"] == "completed"
