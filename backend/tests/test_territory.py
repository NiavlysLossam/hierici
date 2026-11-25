import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.territory import Territory
from app.core.database import get_db
from app.core.territory import extract_territory_slug_from_request

client = TestClient(app)


def test_extract_territory_slug_header():
    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda key, default=None: "toulon" if key == "X-Territory-Slug" else ""
    slug = extract_territory_slug_from_request(mock_request)
    assert slug == "toulon"


def test_extract_territory_slug_subdomain():
    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda key, default=None: "marseille.hierici.fr:8000" if key == "host" else None
    slug = extract_territory_slug_from_request(mock_request)
    assert slug == "marseille"


def test_extract_territory_slug_localhost_subdomain():
    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda key, default=None: "toulon.localhost:5173" if key == "host" else None
    slug = extract_territory_slug_from_request(mock_request)
    assert slug == "toulon"


def test_extract_territory_slug_ip_fallback():
    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda key, default=None: "192.168.1.50:8000" if key == "host" else None
    slug = extract_territory_slug_from_request(mock_request)
    assert slug == "territoire-pilote"


def test_extract_territory_slug_fallback():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None
    slug = extract_territory_slug_from_request(mock_request)
    assert slug == "territoire-pilote"


def test_get_current_territory_endpoint():
    dummy_territory = Territory(
        id=uuid.uuid4(),
        slug="territoire-pilote",
        name="Territoire Pilote",
        center_lat=43.1242,
        center_lng=5.9280,
        default_zoom=13,
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dummy_territory
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/territory/current")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "territoire-pilote"
        assert data["name"] == "Territoire Pilote"
        assert data["center_lat"] == 43.1242
        assert data["center_lng"] == 5.9280
    finally:
        app.dependency_overrides.clear()


def test_get_current_territory_not_found_rfc7807():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/territory/current", headers={"X-Territory-Slug": "inexistant"})
        assert response.status_code == 404
        data = response.json()
        assert "type" in data
        assert "title" in data
        assert data["error"]["code"] == "TERRITORY_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
