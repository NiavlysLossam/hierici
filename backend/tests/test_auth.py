import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User, UserRole
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_user
from app.core.security import hash_password, create_access_token

client = TestClient(app)


@pytest.fixture
def mock_users():
    superadmin = User(
        id=uuid.uuid4(),
        email="superadmin@hierici.local",
        password_hash=hash_password("SuperSecret123"),
        full_name="Super Admin",
        role=UserRole.SUPERADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    contributor = User(
        id=uuid.uuid4(),
        email="contributor@hierici.local",
        password_hash=hash_password("ContributorSecret123"),
        full_name="Jean Contributeur",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@hierici.local",
        password_hash=hash_password("InactiveSecret123"),
        full_name="Compte Inactif",
        role=UserRole.CONTRIBUTOR,
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    return {
        "superadmin": superadmin,
        "contributor": contributor,
        "inactive": inactive_user,
    }


def test_protected_route_without_token():
    response = client.get("/api/v1/admin/status")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_admin_status_with_contributor(mock_users):
    app.dependency_overrides[get_current_active_user] = lambda: mock_users["contributor"]
    try:
        response = client.get(
            "/api/v1/admin/status",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "authorized"
        assert data["role"] == "contributor"
    finally:
        app.dependency_overrides.clear()


def test_superadmin_route_forbidden_for_contributor(mock_users):
    app.dependency_overrides[get_current_active_user] = lambda: mock_users["contributor"]
    try:
        response = client.get(
            "/api/v1/admin/superadmin/overview",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_superadmin_route_allowed_for_superadmin(mock_users):
    app.dependency_overrides[get_current_active_user] = lambda: mock_users["superadmin"]
    try:
        response = client.get(
            "/api/v1/admin/superadmin/overview",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_login_successful_and_case_insensitive(mock_users):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_users["contributor"]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        # Test avec email majuscules
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "CONTRIBUTOR@hierici.local", "password": "ContributorSecret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "contributor@hierici.local"
    finally:
        app.dependency_overrides.clear()


def test_login_invalid_password(mock_users):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_users["contributor"]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "contributor@hierici.local", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_login_inactive_account(mock_users):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_users["inactive"]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@hierici.local", "password": "InactiveSecret123"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_login_oauth2_form(mock_users):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_users["superadmin"]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post(
            "/api/v1/auth/login/form",
            data={"username": "superadmin@hierici.local", "password": "SuperSecret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    finally:
        app.dependency_overrides.clear()


def test_get_my_profile(mock_users):
    app.dependency_overrides[get_current_active_user] = lambda: mock_users["contributor"]
    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "contributor@hierici.local"
        assert data["role"] == "contributor"
    finally:
        app.dependency_overrides.clear()
