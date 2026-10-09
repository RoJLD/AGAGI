"""
Tests d'intégration pour l'API FastAPI de la branche Langage Ultime (/api/lu).
Conforme au Commandement 12 (CI/CD) et Commandement 5 (Observabilité).
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_lu_metrics():
    response = client.get("/api/lu/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "global_verdict" in data
    assert data["global_verdict"] in ["VALIDE", "NEUTRE"]
    assert "global_ratio" in data


def test_api_lu_explain():
    payload = {
        "dsl": "(Alpha:AGENT)-[TARGETS]->(Resource:CONCEPT) ; (Resource)-[IS_A]->(Food:CONCEPT)"
    }
    response = client.post("/api/lu/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Alpha a pour cible prioritaire Resource" in data["human_text_fr"]
    assert "human_text_en" in data
    assert data["nodes_count"] == 3


def test_api_lu_thoughts():
    response = client.get("/api/lu/thoughts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_lu_live_sample():
    response = client.get("/api/lu/live_sample")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) >= 2
    assert "human_text_fr" in data["agents"][0]
    assert "gigatoken" in data["agents"][0]

