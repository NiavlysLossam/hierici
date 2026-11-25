import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.auth import get_current_active_user
from app.models.territory import Territory
from app.models.user import User, UserRole
from app.models.photo import Photo, PhotoStatus
from app.services.storage.base import StorageDriver
from app.services.storage import get_storage_driver


@pytest.fixture
async def setup_test_data():
    """Prépare deux territoires et deux contributeurs pour tester l'API et le cloisonnement."""
    async with AsyncSessionLocal() as session:
        t_a = Territory(
            id=uuid.uuid4(),
            slug=f"toulon-{uuid.uuid4().hex[:6]}",
            name="Toulon Test",
            center_lat=43.12,
            center_lng=5.93,
            default_zoom=13,
        )
        t_b = Territory(
            id=uuid.uuid4(),
            slug=f"marseille-{uuid.uuid4().hex[:6]}",
            name="Marseille Test",
            center_lat=43.29,
            center_lng=5.37,
            default_zoom=13,
        )
        session.add_all([t_a, t_b])
        await session.commit()
        await session.refresh(t_a)
        await session.refresh(t_b)

        u_a = User(
            id=uuid.uuid4(),
            email=f"contrib_a_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Jean Toulon",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_a.id,
            is_active=True,
        )
        u_b = User(
            id=uuid.uuid4(),
            email=f"contrib_b_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Claire Marseille",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_b.id,
            is_active=True,
        )
        session.add_all([u_a, u_b])
        await session.commit()
        await session.refresh(u_a)
        await session.refresh(u_b)

    yield {
        "t_a": t_a,
        "t_b": t_b,
        "u_a": u_a,
        "u_b": u_b,
    }

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Photo).where(Photo.territory_id.in_([t_a.id, t_b.id]))
        )
        await session.execute(
            delete(User).where(User.id.in_([u_a.id, u_b.id]))
        )
        await session.execute(
            delete(Territory).where(Territory.id.in_([t_a.id, t_b.id]))
        )
        await session.commit()


async def test_unauthenticated_request_rejected():
    """Vérifie que l'accès sans authentification est rejeté avec un code 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/photos")
        assert response.status_code == 401


async def test_create_draft_photo_without_gps(setup_test_data):
    """Scénario 1: Création d'une photo 'draft' sans coordonnées GPS."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {
                "title": "Photo Port Toulon 1900",
                "description": "Vue sur la darse historique",
                "status": "draft",
                "year": 1900,
                "archive_reference": "10Fi123",
            }
            response = await ac.post("/api/v1/admin/photos", json=payload)
            assert response.status_code == 201
            data = response.json()

            assert data["title"] == "Photo Port Toulon 1900"
            assert data["status"] == "draft"
            assert data["territory_id"] == str(t_a.id)
            assert data["latitude"] is None
            assert data["longitude"] is None
            assert data["location"] is None
            assert data["year"] == 1900
            assert data["archive_reference"] == "10Fi123"
            assert data["field_of_view"] == 60
    finally:
        app.dependency_overrides.clear()


async def test_create_published_photo_with_gps(setup_test_data):
    """Scénario 2: Publication d'une photo avec coordonnées GPS valides et azimut."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {
                "title": "Fort Saint-Louis 1912",
                "status": "published",
                "latitude": 43.12,
                "longitude": 5.93,
                "bearing": 180,
                "field_of_view": 70,
            }
            response = await ac.post("/api/v1/admin/photos", json=payload)
            assert response.status_code == 201
            data = response.json()

            assert data["title"] == "Fort Saint-Louis 1912"
            assert data["status"] == "published"
            assert data["territory_id"] == str(t_a.id)
            assert data["latitude"] == 43.12
            assert data["longitude"] == 5.93
            assert data["bearing"] == 180
            assert data["field_of_view"] == 70
            assert data["location"] == {
                "type": "Point",
                "coordinates": [5.93, 43.12],
            }
    finally:
        app.dependency_overrides.clear()


async def test_create_published_photo_without_gps_rejected(setup_test_data):
    """Scénario 3: Tentative de publication sans coordonnées GPS -> HTTP 422."""
    u_a = setup_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {
                "title": "Photo sans GPS publiée",
                "status": "published",
            }
            response = await ac.post("/api/v1/admin/photos", json=payload)
            assert response.status_code == 422
            data = response.json()
            assert "error" in data or "detail" in data
    finally:
        app.dependency_overrides.clear()


async def test_bearing_bounds_validation(setup_test_data):
    """Scénario 4: Azimut hors limites (<0 ou >=360) -> HTTP 422."""
    u_a = setup_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 365°
            res1 = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test 365", "bearing": 365},
            )
            assert res1.status_code == 422

            # -5°
            res2 = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test -5", "bearing": -5},
            )
            assert res2.status_code == 422

            # 0° valide
            res3 = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test 0", "bearing": 0},
            )
            assert res3.status_code == 201
            assert res3.json()["bearing"] == 0

            # 359° valide
            res4 = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test 359", "bearing": 359},
            )
            assert res4.status_code == 201
            assert res4.json()["bearing"] == 359
    finally:
        app.dependency_overrides.clear()


async def test_list_photos_filtered_by_territory(setup_test_data):
    """Scénario 5: Un contributeur ne liste que les photos de son propre territoire."""
    u_a = setup_test_data["u_a"]
    u_b = setup_test_data["u_b"]
    t_a = setup_test_data["t_a"]
    t_b = setup_test_data["t_b"]

    async with AsyncSessionLocal() as session:
        p_a1 = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo A1 Toulon",
            status=PhotoStatus.DRAFT,
        )
        p_a2 = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo A2 Toulon",
            status=PhotoStatus.DRAFT,
        )
        p_b1 = Photo(
            territory_id=t_b.id,
            author_user_id=u_b.id,
            title="Photo B1 Marseille",
            status=PhotoStatus.DRAFT,
        )
        session.add_all([p_a1, p_a2, p_b1])
        await session.commit()

    # Appel en tant que contributeur A
    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res_a = await ac.get("/api/v1/admin/photos")
            assert res_a.status_code == 200
            data_a = res_a.json()
            titles = [p["title"] for p in data_a["items"]]
            assert "Photo A1 Toulon" in titles
            assert "Photo A2 Toulon" in titles
            assert "Photo B1 Marseille" not in titles
            assert all(p["territory_id"] == str(t_a.id) for p in data_a["items"])
    finally:
        app.dependency_overrides.clear()

    # Appel en tant que contributeur B
    app.dependency_overrides[get_current_active_user] = lambda: u_b
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res_b = await ac.get("/api/v1/admin/photos")
            assert res_b.status_code == 200
            data_b = res_b.json()
            titles_b = [p["title"] for p in data_b["items"]]
            assert "Photo B1 Marseille" in titles_b
            assert "Photo A1 Toulon" not in titles_b
            assert "Photo A2 Toulon" not in titles_b
    finally:
        app.dependency_overrides.clear()


async def test_access_photo_of_another_territory_returns_404_rfc7807(setup_test_data):
    """Scénario 6: Accès à la fiche d'un autre territoire -> 404 RFC 7807 PHOTO_NOT_FOUND."""
    u_a = setup_test_data["u_a"]
    u_b = setup_test_data["u_b"]
    t_b = setup_test_data["t_b"]

    async with AsyncSessionLocal() as session:
        photo = Photo(
            territory_id=t_b.id,
            author_user_id=u_b.id,
            title="Photo Privée Marseille",
            status=PhotoStatus.DRAFT,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        photo_b_id = photo.id

    # Utilisateur A essaie d'accéder à la photo de B
    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(f"/api/v1/admin/photos/{photo_b_id}")
            assert res.status_code == 404
            data = res.json()
            assert "error" in data
            assert data["error"]["code"] == "PHOTO_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_update_photo_and_published_validation(setup_test_data):
    """Mise à jour d'une photo et vérification de la règle de publication."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    async with AsyncSessionLocal() as session:
        photo = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Brouillon Modifiable",
            status=PhotoStatus.DRAFT,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        photo_id = photo.id

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Tentative de basculer en published sans coordonnées -> 422
            res1 = await ac.patch(
                f"/api/v1/admin/photos/{photo_id}",
                json={"status": "published"},
            )
            assert res1.status_code == 422

            # 2. Mise à jour avec coordonnées et statut published -> 200
            res2 = await ac.patch(
                f"/api/v1/admin/photos/{photo_id}",
                json={
                    "title": "Titre Modifié",
                    "status": "published",
                    "latitude": 43.1205,
                    "longitude": 5.9288,
                    "bearing": 90,
                },
            )
            assert res2.status_code == 200
            updated = res2.json()
            assert updated["title"] == "Titre Modifié"
            assert updated["status"] == "published"
            assert updated["latitude"] == 43.1205
            assert updated["longitude"] == 5.9288
            assert updated["bearing"] == 90
            assert updated["location"] == {
                "type": "Point",
                "coordinates": [5.9288, 43.1205],
            }
    finally:
        app.dependency_overrides.clear()


async def test_delete_photo_cleans_up_media_files(setup_test_data):
    """Scénario 7: Suppression d'une photo et nettoyage physique des fichiers via StorageDriver."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    async with AsyncSessionLocal() as session:
        photo = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo avec Fichiers",
            status=PhotoStatus.DRAFT,
            file_original_path="uploads/toulon/original_123.jpg",
            file_display_path="uploads/toulon/display_123.webp",
            file_thumb_path="uploads/toulon/thumb_123.webp",
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        photo_id = photo.id

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    mock_storage = AsyncMock(spec=StorageDriver)
    mock_storage.delete.return_value = True
    app.dependency_overrides[get_storage_driver] = lambda: mock_storage
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.delete(f"/api/v1/admin/photos/{photo_id}")
            assert res.status_code == 204

        # Vérification des appels à delete pour chaque fichier média
        deleted_paths = [call.args[0] for call in mock_storage.delete.call_args_list]
        assert "uploads/toulon/original_123.jpg" in deleted_paths
        assert "uploads/toulon/display_123.webp" in deleted_paths
        assert "uploads/toulon/thumb_123.webp" in deleted_paths
        assert mock_storage.delete.call_count == 3

        # Vérification en base que la photo n'existe plus
        async with AsyncSessionLocal() as session:
            check = await session.execute(select(Photo).where(Photo.id == photo_id))
            assert check.scalar_one_or_none() is None
    finally:
        app.dependency_overrides.clear()


async def test_delete_photo_from_another_territory_fails(setup_test_data):
    """Tentative de suppression d'une photo d'un autre territoire -> 404 & conservée en base."""
    u_a = setup_test_data["u_a"]
    u_b = setup_test_data["u_b"]
    t_b = setup_test_data["t_b"]

    async with AsyncSessionLocal() as session:
        photo = Photo(
            territory_id=t_b.id,
            author_user_id=u_b.id,
            title="Photo B Protégée",
            status=PhotoStatus.DRAFT,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        photo_b_id = photo.id

    # Utilisateur A essaie de supprimer la photo de B
    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.delete(f"/api/v1/admin/photos/{photo_b_id}")
            assert res.status_code == 404

        # Vérifier que la photo existe toujours en base
        async with AsyncSessionLocal() as session:
            check = await session.execute(select(Photo).where(Photo.id == photo_b_id))
            assert check.scalar_one_or_none() is not None
    finally:
        app.dependency_overrides.clear()


async def test_get_single_photo_success(setup_test_data):
    """Lecture d'une photo de son propre territoire -> 200 OK avec payload complet."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    async with AsyncSessionLocal() as session:
        photo = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo Consultable",
            status=PhotoStatus.DRAFT,
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        photo_id = photo.id

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(f"/api/v1/admin/photos/{photo_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == str(photo_id)
            assert data["title"] == "Photo Consultable"
            assert data["territory_id"] == str(t_a.id)
    finally:
        app.dependency_overrides.clear()


async def test_list_photos_search_and_status_filters(setup_test_data):
    """Vérifie le filtrage par statut et recherche plein texte."""
    u_a = setup_test_data["u_a"]
    t_a = setup_test_data["t_a"]

    async with AsyncSessionLocal() as session:
        p1 = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Pont suspendu ancien",
            description="Vue panoramique",
            status=PhotoStatus.DRAFT,
        )
        p2 = Photo(
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Cathédrale Sainte-Marie",
            description="Façade gothique",
            status=PhotoStatus.PUBLISHED,
            latitude=43.12,
            longitude=5.93,
        )
        session.add_all([p1, p2])
        await session.commit()

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Filtre par statut draft
            res_draft = await ac.get("/api/v1/admin/photos?status=draft")
            assert res_draft.status_code == 200
            items_draft = res_draft.json()["items"]
            assert any(p["title"] == "Pont suspendu ancien" for p in items_draft)
            assert not any(p["title"] == "Cathédrale Sainte-Marie" for p in items_draft)

            # Filtre par recherche textuelle
            res_search = await ac.get("/api/v1/admin/photos?search=Cathédrale")
            assert res_search.status_code == 200
            items_search = res_search.json()["items"]
            assert len(items_search) == 1
            assert items_search[0]["title"] == "Cathédrale Sainte-Marie"
    finally:
        app.dependency_overrides.clear()


async def test_superadmin_cross_territory_access(setup_test_data):
    """Le superadmin peut accéder aux photos de n'importe quel territoire."""
    t_a = setup_test_data["t_a"]
    t_b = setup_test_data["t_b"]

    superadmin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Super Administrateur",
        role=UserRole.SUPERADMIN,
        territory_id=None,
        is_active=True,
    )

    async with AsyncSessionLocal() as session:
        session.add(superadmin)
        p_b = Photo(
            territory_id=t_b.id,
            author_user_id=superadmin.id,
            title="Photo Territoire B vue par Superadmin",
            status=PhotoStatus.DRAFT,
        )
        session.add(p_b)
        await session.commit()
        await session.refresh(p_b)
        p_b_id = p_b.id

    app.dependency_overrides[get_current_active_user] = lambda: superadmin
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Lecture directe de la photo du territoire B
            res = await ac.get(f"/api/v1/admin/photos/{p_b_id}")
            assert res.status_code == 200
            assert res.json()["title"] == "Photo Territoire B vue par Superadmin"

            # Création avec territoire explicite
            create_res = await ac.post(
                "/api/v1/admin/photos",
                json={
                    "title": "Photo créée par superadmin sur A",
                    "territory_id": str(t_a.id),
                    "status": "draft",
                },
            )
            assert create_res.status_code == 201
            assert create_res.json()["territory_id"] == str(t_a.id)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_metadata_suggestions_and_view_distance(setup_test_data):
    """Vérifie la création avec is_exact_year et view_distance, et les suggestions d'archives/photographes."""
    t_a = setup_test_data["t_a"]
    u_a = setup_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Création photo avec distance personnalisée et année approximative
            create_res = await ac.post(
                "/api/v1/admin/photos",
                json={
                    "title": "Vue du pont médiéval",
                    "photographer": "Studio Nadar",
                    "archive_source": "Médiathèque Municipale",
                    "year_taken": 1898,
                    "is_exact_year": False,
                    "latitude": 43.12,
                    "longitude": 5.93,
                    "bearing": 120,
                    "field_of_view": 65,
                    "view_distance": 450,
                    "status": "draft",
                },
            )
            assert create_res.status_code == 201
            photo_data = create_res.json()
            assert photo_data["is_exact_year"] is False
            assert photo_data["view_distance"] == 450

            # 2. Récupération des suggestions pour le territoire A
            sugg_res = await ac.get("/api/v1/admin/photos/metadata-suggestions")
            assert sugg_res.status_code == 200
            sugg_json = sugg_res.json()
            assert "Studio Nadar" in sugg_json["photographers"]
            assert "Médiathèque Municipale" in sugg_json["archive_sources"]

            # 3. Validation des bornes de view_distance (< 20 et > 2000 -> 422)
            invalid_min = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test Min", "view_distance": 10},
            )
            assert invalid_min.status_code == 422

            invalid_max = await ac.post(
                "/api/v1/admin/photos",
                json={"title": "Test Max", "view_distance": 2500},
            )
            assert invalid_max.status_code == 422
    finally:
        app.dependency_overrides.clear()

    # 4. Vérification de l'étanchéité multi-territoires : l'utilisateur B ne voit pas les suggestions de A
    u_b = setup_test_data["u_b"]
    app.dependency_overrides[get_current_active_user] = lambda: u_b
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            sugg_b = await ac.get("/api/v1/admin/photos/metadata-suggestions")
            assert sugg_b.status_code == 200
            sugg_b_json = sugg_b.json()
            assert "Studio Nadar" not in sugg_b_json["photographers"]
            assert "Médiathèque Municipale" not in sugg_b_json["archive_sources"]
    finally:
        app.dependency_overrides.clear()
