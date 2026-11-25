import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "HierIci" in data["message"]
    assert data["health_check"] == "/api/health"


@patch("app.main.check_db_connection", new_callable=AsyncMock)
def test_health_check_connected(mock_check_db):
    mock_check_db.return_value = True
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@patch("app.main.check_db_connection", new_callable=AsyncMock)
def test_health_check_disconnected(mock_check_db):
    mock_check_db.return_value = False
    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "disconnected"

