import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.auth import get_current_active_user
from app.models.territory import Territory
from app.models.user import User, UserRole


@pytest.fixture
async def setup_admin_data():
    """Crée deux territoires avec leurs administrateurs/contributeurs et un superadmin."""
    async with AsyncSessionLocal() as session:
        t_a = Territory(
            id=uuid.uuid4(),
            slug=f"territoire-a-{uuid.uuid4().hex[:6]}",
            name="Territoire A",
            center_lat=43.12,
            center_lng=5.93,
            default_zoom=13,
            basemaps=[],
        )
        t_b = Territory(
            id=uuid.uuid4(),
            slug=f"territoire-b-{uuid.uuid4().hex[:6]}",
            name="Territoire B",
            center_lat=48.85,
            center_lng=2.35,
            default_zoom=12,
            basemaps=[],
        )
        session.add_all([t_a, t_b])
        await session.commit()
        await session.refresh(t_a)
        await session.refresh(t_b)

        u_admin_a = User(
            id=uuid.uuid4(),
            email=f"admin_a_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Admin A",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_a.id,
            is_active=True,
        )
        u_contrib_a = User(
            id=uuid.uuid4(),
            email=f"contrib_a_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Contributeur A",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_a.id,
            is_active=True,
        )
        u_admin_b = User(
            id=uuid.uuid4(),
            email=f"admin_b_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Admin B",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_b.id,
            is_active=True,
        )
        u_super = User(
            id=uuid.uuid4(),
            email=f"super_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Grand Patron",
            role=UserRole.SUPERADMIN,
            territory_id=t_a.id,
            is_active=True,
        )
        session.add_all([u_admin_a, u_contrib_a, u_admin_b, u_super])
        await session.commit()
        await session.refresh(u_admin_a)
        await session.refresh(u_contrib_a)
        await session.refresh(u_admin_b)
        await session.refresh(u_super)

    yield {
        "t_a": t_a,
        "t_b": t_b,
        "u_admin_a": u_admin_a,
        "u_contrib_a": u_contrib_a,
        "u_admin_b": u_admin_b,
        "u_super": u_super,
    }

    # Nettoyage
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.id.in_([u_admin_a.id, u_contrib_a.id, u_admin_b.id, u_super.id])))
        await session.execute(delete(Territory).where(Territory.id.in_([t_a.id, t_b.id])))
        await session.commit()


@pytest.mark.asyncio
async def test_get_and_patch_territory_config_and_bounds(setup_admin_data):
    """Vérifie la lecture, la mise à jour, les types de flux (XYZ/WMS/WMTS) et le rejet des coordonnées hors limites."""
    data = setup_admin_data
    u_admin = data["u_admin_a"]
    t_a = data["t_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_admin
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Lecture de la configuration du territoire
        res = await ac.get("/api/v1/admin/territory")
        assert res.status_code == 200
        payload = res.json()
        assert payload["id"] == str(t_a.id)
        assert payload["center_lat"] == 43.12
        assert payload["center_lng"] == 5.93
        assert payload["default_zoom"] == 13
        assert len(payload["basemaps"]) >= 1

        # 2. Mise à jour avec flux multiples (XYZ, WMS avec layers/format)
        new_basemaps = [
            {
                "id": "ign-ortho",
                "name": "IGN Ortho WMTS",
                "type": "wmts",
                "url": "https://data.geopf.fr/wmts?...",
                "attribution": "IGN",
                "is_default": True,
                "layers": "ORTHOIMAGERY.ORTHOPHOTOS",
                "format": "image/jpeg",
            },
            {
                "id": "cadastre-wms",
                "name": "Cadastre WMS",
                "type": "wms",
                "url": "https://wms.cadastre.data.gouv.fr/...",
                "attribution": "DGFIP",
                "is_default": False,
                "layers": "PARCELLES",
                "format": "image/png",
            },
        ]
        patch_res = await ac.patch(
            "/api/v1/admin/territory",
            json={
                "center_lat": 43.155,
                "center_lng": 5.942,
                "default_zoom": 15,
                "basemaps": new_basemaps,
            },
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["center_lat"] == 43.155
        assert updated["center_lng"] == 5.942
        assert updated["default_zoom"] == 15
        assert len(updated["basemaps"]) == 2
        assert updated["basemaps"][0]["type"] == "wmts"
        assert updated["basemaps"][1]["type"] == "wms"
        assert updated["basemaps"][1]["layers"] == "PARCELLES"

        # 3. Validation des bornes : Rejet HTTP 422 si latitude > 90
        err_lat = await ac.patch("/api/v1/admin/territory", json={"center_lat": 125.0})
        assert err_lat.status_code == 422

        # 4. Validation des bornes : Rejet HTTP 422 si zoom > 22
        err_zoom = await ac.patch("/api/v1/admin/territory", json={"default_zoom": 35})
        assert err_zoom.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_management_lifecycle_and_security(setup_admin_data):
    """Teste la création, liste, modification et suppression de contributeurs avec isolations et gardes de sécurité."""
    data = setup_admin_data
    u_admin = data["u_admin_a"]
    t_a = data["t_a"]
    u_admin_b = data["u_admin_b"]
    u_super = data["u_super"]

    app.dependency_overrides[get_current_active_user] = lambda: u_admin
    transport = ASGITransport(app=app)

    created_user_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Lister les contributeurs du territoire A
            res = await ac.get("/api/v1/admin/users")
            assert res.status_code == 200
            users = res.json()
            assert any(u["id"] == str(u_admin.id) for u in users)
            assert any(u["id"] == str(data["u_contrib_a"].id) for u in users)
            assert not any(u["id"] == str(u_admin_b.id) for u in users)

            # 2. Créer un nouveau contributeur
            new_email = f"nouveau_{uuid.uuid4().hex[:6]}@example.com"
            create_res = await ac.post(
                "/api/v1/admin/users",
                json={
                    "email": new_email,
                    "password": "MotDePasseSecurise123!",
                    "full_name": "Marc Nouvel Historien",
                    "role": "contributor",
                },
            )
            assert create_res.status_code == 201
            created = create_res.json()
            created_user_id = created["id"]
            assert created["email"] == new_email
            assert created["full_name"] == "Marc Nouvel Historien"
            assert created["is_active"] is True
            assert created["territory_id"] == str(t_a.id)

            # 3. Empêcher la création avec email en doublon
            dup_res = await ac.post(
                "/api/v1/admin/users",
                json={
                    "email": new_email,
                    "password": "AutrePassword!",
                    "full_name": "Doublon",
                },
            )
            assert dup_res.status_code == 400
            assert dup_res.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

            # 4. Rejeter un mot de passe composé uniquement d'espaces blancs
            blank_pass_res = await ac.post(
                "/api/v1/admin/users",
                json={
                    "email": f"blanc_{uuid.uuid4().hex[:6]}@example.com",
                    "password": "      ",
                    "full_name": "Test Blanc",
                },
            )
            assert blank_pass_res.status_code == 422

            # 5. Modifier le nom, l'état d'activation et le mot de passe
            patch_user = await ac.patch(
                f"/api/v1/admin/users/{created_user_id}",
                json={
                    "full_name": "Marc Modifié",
                    "is_active": False,
                    "password": "NouveauSuperPassword2026!",
                },
            )
            assert patch_user.status_code == 200
            patch_payload = patch_user.json()
            assert patch_payload["full_name"] == "Marc Modifié"
            assert patch_payload["is_active"] is False
            # S'assurer que le password_hash n'est pas exposé
            assert "password" not in patch_payload
            assert "password_hash" not in patch_payload

            # 6. Garde de sécurité : interdiction de désactiver son propre compte
            self_deactivate = await ac.patch(
                f"/api/v1/admin/users/{u_admin.id}",
                json={"is_active": False},
            )
            assert self_deactivate.status_code == 400
            assert self_deactivate.json()["error"]["code"] == "CANNOT_DEACTIVATE_SELF"

            # 7. Garde de sécurité : interdiction de modifier un utilisateur d'un autre territoire
            other_patch = await ac.patch(
                f"/api/v1/admin/users/{u_admin_b.id}",
                json={"full_name": "Piratage"},
            )
            assert other_patch.status_code == 403
            assert other_patch.json()["error"]["code"] == "FORBIDDEN_TERRITORY"

            # 8. Garde de sécurité : interdiction de supprimer un utilisateur d'un autre territoire
            other_del = await ac.delete(f"/api/v1/admin/users/{u_admin_b.id}")
            assert other_del.status_code == 403
            assert other_del.json()["error"]["code"] == "FORBIDDEN_TERRITORY"

            # 9. Garde de sécurité P1 (Blind Hunter) : Interdiction pour un contributeur de modifier ou supprimer un Superadmin
            super_patch = await ac.patch(
                f"/api/v1/admin/users/{u_super.id}",
                json={"full_name": "Tentative Piratage Superadmin"},
            )
            assert super_patch.status_code == 403
            assert super_patch.json()["error"]["code"] == "FORBIDDEN_SUPERADMIN_TARGET"

            super_del = await ac.delete(f"/api/v1/admin/users/{u_super.id}")
            assert super_del.status_code == 403
            assert super_del.json()["error"]["code"] == "FORBIDDEN_SUPERADMIN_TARGET"

            # 10. Erreur 404 sur utilisateur inexistant
            unknown_uuid = uuid.uuid4()
            not_found_patch = await ac.patch(f"/api/v1/admin/users/{unknown_uuid}", json={"full_name": "Inconnu"})
            assert not_found_patch.status_code == 404
            assert not_found_patch.json()["error"]["code"] == "USER_NOT_FOUND"

            # 11. Garde de sécurité : interdiction de supprimer son propre compte
            self_delete = await ac.delete(f"/api/v1/admin/users/{u_admin.id}")
            assert self_delete.status_code == 400
            assert self_delete.json()["error"]["code"] == "CANNOT_DELETE_SELF"

            # 12. Suppression légitime du compte créé
            del_res = await ac.delete(f"/api/v1/admin/users/{created_user_id}")
            assert del_res.status_code == 204

    finally:
        app.dependency_overrides.clear()
        if created_user_id:
            async with AsyncSessionLocal() as session:
                await session.execute(delete(User).where(User.id == uuid.UUID(created_user_id)))
                await session.commit()
