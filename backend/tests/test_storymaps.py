import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.auth import get_current_active_user
from app.models.territory import Territory
from app.models.user import User, UserRole
from app.models.photo import Photo, PhotoStatus
from app.models.storymap import Storymap, StorymapStep, StorymapStatus


@pytest.fixture
async def setup_storymaps_test_data():
    """Prépare deux territoires, deux contributeurs et deux photos (une publiée, une brouillon) pour les tests."""
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
        super_admin = User(
            id=uuid.uuid4(),
            email=f"superadmin_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Admin Principal",
            role=UserRole.SUPERADMIN,
            territory_id=t_a.id,
            is_active=True,
        )
        session.add_all([u_a, u_b, super_admin])
        await session.commit()
        await session.refresh(u_a)
        await session.refresh(u_b)
        await session.refresh(super_admin)

        photo_pub_a = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo d'archive port 1900",
            latitude=43.12,
            longitude=5.93,
            bearing=90,
            field_of_view=60,
            file_original_path="private/storage/original_photo.jpg",
            file_display_path="private/storage/display_photo.webp",
            file_thumb_path="private/storage/thumb_photo.webp",
            status=PhotoStatus.PUBLISHED,
        )
        photo_draft_a = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo d'archive confidentielle non publiée",
            latitude=43.12,
            longitude=5.93,
            file_display_path="private/storage/draft.webp",
            status=PhotoStatus.DRAFT,
        )
        photo_pub_b = Photo(
            id=uuid.uuid4(),
            territory_id=t_b.id,
            author_user_id=u_b.id,
            title="Photo Marseille Vieux Port",
            latitude=43.29,
            longitude=5.37,
            file_display_path="private/storage/marseille.webp",
            status=PhotoStatus.PUBLISHED,
        )
        session.add_all([photo_pub_a, photo_draft_a, photo_pub_b])
        await session.commit()
        await session.refresh(photo_pub_a)
        await session.refresh(photo_draft_a)
        await session.refresh(photo_pub_b)

    yield {
        "t_a": t_a,
        "t_b": t_b,
        "u_a": u_a,
        "u_b": u_b,
        "super_admin": super_admin,
        "photo": photo_pub_a,
        "photo_draft": photo_draft_a,
        "photo_b": photo_pub_b,
    }

    # Nettoyage en fin de test
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Storymap).where(Storymap.territory_id.in_([t_a.id, t_b.id]))
        )
        await session.execute(
            delete(Photo).where(Photo.territory_id.in_([t_a.id, t_b.id]))
        )
        await session.execute(
            delete(User).where(User.id.in_([u_a.id, u_b.id, super_admin.id]))
        )
        await session.execute(
            delete(Territory).where(Territory.id.in_([t_a.id, t_b.id]))
        )
        await session.commit()


@pytest.mark.asyncio
async def test_admin_routes_require_authentication():
    """Vérifie que les routes admin de storymaps rejettent les accès non authentifiés (401)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/admin/storymaps")
        assert res.status_code == 401

        res_post = await client.post("/api/v1/admin/storymaps", json={"title": "Test"})
        assert res_post.status_code == 401


@pytest.mark.asyncio
async def test_create_storymap_draft_and_auto_slug(setup_storymaps_test_data):
    """Vérifie la création d'une storymap en brouillon avec génération automatique de slug."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]
    t_a = data["t_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "title": "Histoire du Tramway Toulonnais (1886) !",
                "summary": "Découvrez le développement des transports urbains au 19e siècle.",
                "cover_image_path": "uploads/covers/tramway.webp",
                "status": "draft",
            }
            res = await client.post("/api/v1/admin/storymaps", json=payload)
            assert res.status_code == 201
            body = res.json()

            assert body["title"] == payload["title"]
            assert body["summary"] == payload["summary"]
            assert body["status"] == "draft"
            assert body["slug"] == "histoire-du-tramway-toulonnais-1886"
            assert body["territory_id"] == str(t_a.id)
            assert body["author_user_id"] == str(u_a.id)
            assert "cover_image_url" in body
            assert body["steps"] == []
            assert body["steps_count"] == 0
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_create_storymap_with_initial_steps_and_camera_validation(setup_storymaps_test_data):
    """Vérifie la création avec étapes initiales et la validation stricte des coordonnées cartographiques."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]
    photo = data["photo"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Étape avec coordonnées caméra invalides (latitude hors borne > 90) -> 422
            invalid_payload = {
                "title": "Storymap Hors Bornes",
                "steps": [
                    {
                        "title": "Étape Invalide",
                        "camera_lat": 150.0,
                        "camera_lng": 5.92,
                    }
                ],
            }
            res_invalid = await client.post("/api/v1/admin/storymaps", json=invalid_payload)
            assert res_invalid.status_code == 422

            # 2. Étape avec zoom hors borne (> 24) -> 422
            invalid_zoom = {
                "title": "Zoom Invalide",
                "steps": [
                    {
                        "title": "Étape Invalide",
                        "camera_lat": 43.12,
                        "camera_lng": 5.92,
                        "camera_zoom": 25.0,
                    }
                ],
            }
            res_zoom = await client.post("/api/v1/admin/storymaps", json=invalid_zoom)
            assert res_zoom.status_code == 422

            # 3. Payload valide avec 2 étapes ordonnées
            valid_payload = {
                "title": "Circuit Historique du Port",
                "summary": "Parcours maritime",
                "status": "published",
                "steps": [
                    {
                        "title": "L'Arsenal",
                        "content_markdown": "## Entrée monumentale\nConstruite en 1738.",
                        "camera_lat": 43.1242,
                        "camera_lng": 5.9280,
                        "camera_zoom": 15.5,
                        "camera_bearing": 120.0,
                        "camera_pitch": 45.0,
                        "audio_file_path": "audio/chapitre1.mp3",
                        "photo_id": str(photo.id),
                    },
                    {
                        "title": "Le Carré du Port",
                        "content_markdown": "Vue panoramique des quais.",
                        "camera_lat": 43.1210,
                        "camera_lng": 5.9320,
                        "camera_zoom": 16.0,
                        "camera_bearing": 360.0,  # 360 doit être normalisé à 0
                        "camera_pitch": 20.0,
                    },
                ],
            }
            res_valid = await client.post("/api/v1/admin/storymaps", json=valid_payload)
            assert res_valid.status_code == 201
            body = res_valid.json()

            assert body["title"] == "Circuit Historique du Port"
            assert body["steps_count"] == 2
            assert len(body["steps"]) == 2

            step1 = body["steps"][0]
            assert step1["step_order"] == 0
            assert step1["title"] == "L'Arsenal"
            assert step1["camera_bearing"] == 120.0
            assert step1["photo_id"] == str(photo.id)
            assert "audio_url" in step1

            step2 = body["steps"][1]
            assert step2["step_order"] == 1
            assert step2["title"] == "Le Carré du Port"
            assert step2["camera_bearing"] == 0.0  # Normalisé
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_add_update_delete_steps(setup_storymaps_test_data):
    """Vérifie l'ajout, la modification et la suppression unitaire d'étapes de storymap."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Créer storymap sans étape
            res_create = await client.post("/api/v1/admin/storymaps", json={"title": "Récit Étapes Test"})
            assert res_create.status_code == 201
            sm_id = res_create.json()["id"]

            # 1. Ajouter une étape
            res_step1 = await client.post(
                f"/api/v1/admin/storymaps/{sm_id}/steps",
                json={
                    "title": "Première étape",
                    "content_markdown": "Description introductive",
                    "lat": 43.12,
                    "lng": 5.92,
                    "zoom": 14.0,
                },
            )
            assert res_step1.status_code == 201
            step1 = res_step1.json()
            assert step1["title"] == "Première étape"
            assert step1["step_order"] == 0
            step1_id = step1["id"]

            # 2. Ajouter une seconde étape (ordre séquentiel incrémenté)
            res_step2 = await client.post(
                f"/api/v1/admin/storymaps/{sm_id}/steps",
                json={
                    "title": "Deuxième étape",
                    "lat": 43.13,
                    "lng": 5.94,
                },
            )
            assert res_step2.status_code == 201
            step2 = res_step2.json()
            assert step2["step_order"] == 1
            step2_id = step2["id"]

            # 3. Mettre à jour l'étape 1
            res_up = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}/steps/{step1_id}",
                json={
                    "title": "Première étape renommée",
                    "pitch": 60.0,
                },
            )
            assert res_up.status_code == 200
            assert res_up.json()["title"] == "Première étape renommée"
            assert res_up.json()["camera_pitch"] == 60.0

            # 4. Supprimer l'étape 2
            res_del = await client.delete(f"/api/v1/admin/storymaps/{sm_id}/steps/{step2_id}")
            assert res_del.status_code == 204

            # Vérifier la storymap
            res_sm = await client.get(f"/api/v1/admin/storymaps/{sm_id}")
            assert res_sm.status_code == 200
            assert res_sm.json()["steps_count"] == 1
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_reorder_steps_atomically(setup_storymaps_test_data):
    """Vérifie le réordonnancement atomique d'étapes via PUT /steps/reorder."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Storymap Réordonnancement",
                    "steps": [
                        {"title": "Étape Alpha", "lat": 43.1, "lng": 5.9},
                        {"title": "Étape Bêta", "lat": 43.2, "lng": 5.8},
                        {"title": "Étape Gamma", "lat": 43.3, "lng": 5.7},
                    ],
                },
            )
            assert res_create.status_code == 201
            sm = res_create.json()
            sm_id = sm["id"]
            id_alpha = sm["steps"][0]["id"]
            id_beta = sm["steps"][1]["id"]
            id_gamma = sm["steps"][2]["id"]

            # Inverser l'ordre : Gamma (0), Alpha (1), Bêta (2)
            res_reorder = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}/steps/reorder",
                json={"step_ids": [id_gamma, id_alpha, id_beta]},
            )
            assert res_reorder.status_code == 200
            updated_sm = res_reorder.json()

            steps_res = updated_sm["steps"]
            assert steps_res[0]["id"] == id_gamma
            assert steps_res[0]["step_order"] == 0
            assert steps_res[1]["id"] == id_alpha
            assert steps_res[1]["step_order"] == 1
            assert steps_res[2]["id"] == id_beta
            assert steps_res[2]["step_order"] == 2

            # Test d'erreur : liste incomplète -> 400
            res_incomplete = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}/steps/reorder",
                json={"step_ids": [id_gamma, id_alpha]},
            )
            assert res_incomplete.status_code == 400

            # Test d'erreur : liste avec doublon -> 400
            res_duplicate = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}/steps/reorder",
                json={"step_ids": [id_gamma, id_gamma, id_beta]},
            )
            assert res_duplicate.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_admin_list_storymaps_pagination_filters_and_isolation(setup_storymaps_test_data):
    """Vérifie la route GET /api/v1/admin/storymaps :
    - Pagination (page, page_size)
    - Filtre par statut (draft, published)
    - Filtre par recherche textuelle (titre/résumé)
    - Isolation territoriale stricte entre contributeurs.
    """
    data = setup_storymaps_test_data
    t_a = data["t_a"]
    t_b = data["t_b"]
    u_a = data["u_a"]
    u_b = data["u_b"]

    async with AsyncSessionLocal() as session:
        sm1 = Storymap(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            slug="balade-rade-1",
            title="Balade dans la Rade",
            summary="Aperçu des forts militaires",
            status=StorymapStatus.PUBLISHED,
        )
        sm2 = Storymap(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            slug="funiculaire-faron",
            title="Le Funiculaire du Mont Faron",
            summary="Histoire de la montée au sommet",
            status=StorymapStatus.DRAFT,
        )
        sm_marseille = Storymap(
            id=uuid.uuid4(),
            territory_id=t_b.id,
            author_user_id=u_b.id,
            slug="notre-dame-garde",
            title="Notre Dame de la Garde",
            summary="Vue sur la cité phocéenne",
            status=StorymapStatus.PUBLISHED,
        )
        session.add_all([sm1, sm2, sm_marseille])
        await session.commit()

    # Authentification sous Jean Toulon (u_a)
    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Liste complète pour le territoire A (2 items attendus, pas celui de Marseille)
            res = await client.get("/api/v1/admin/storymaps")
            assert res.status_code == 200
            data_res = res.json()
            assert data_res["total"] == 2
            slugs = [s["slug"] for s in data_res["items"]]
            assert "balade-rade-1" in slugs
            assert "funiculaire-faron" in slugs
            assert "notre-dame-garde" not in slugs

            # 2. Filtre par statut = published
            res_pub = await client.get("/api/v1/admin/storymaps?status=published")
            assert res_pub.status_code == 200
            assert res_pub.json()["total"] == 1
            assert res_pub.json()["items"][0]["slug"] == "balade-rade-1"

            # 3. Filtre par recherche textuelle
            res_search = await client.get("/api/v1/admin/storymaps?search=faron")
            assert res_search.status_code == 200
            assert res_search.json()["total"] == 1
            assert res_search.json()["items"][0]["slug"] == "funiculaire-faron"

            # 4. Pagination (page 1, limit 1)
            res_page = await client.get("/api/v1/admin/storymaps?page=1&page_size=1")
            assert res_page.status_code == 200
            assert len(res_page.json()["items"]) == 1
            assert res_page.json()["pages"] == 2
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_update_storymap_metadata_and_publishing(setup_storymaps_test_data):
    """Vérifie la mise à jour des métadonnées, la réinitialisation de champs optionnels et la publication d'une storymap."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Créer une storymap initiale
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Histoire du Théâtre",
                    "summary": "Résumé temporaire",
                    "cover_image_path": "uploads/covers/theatre.webp",
                    "status": "draft",
                },
            )
            assert res_create.status_code == 201
            sm_id = res_create.json()["id"]

            # 2. Mettre à jour titre, publier, et effacer volontairement le résumé et la couverture (None)
            res_update = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}",
                json={
                    "title": "L'Opéra de Toulon",
                    "summary": None,
                    "cover_image_path": None,
                    "status": "published",
                },
            )
            assert res_update.status_code == 200
            body = res_update.json()
            assert body["title"] == "L'Opéra de Toulon"
            assert body["summary"] is None
            assert body["cover_image_path"] is None
            assert body["cover_image_url"] is None
            assert body["status"] == "published"
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_public_storymaps_access_isolation_and_privacy(setup_storymaps_test_data):
    """Vérifie l'accès public aux storymaps :
    - Récit publié accessible via son slug (200)
    - Récit brouillon masqué (404)
    - Récit d'un autre territoire masqué (404)
    - Absence stricte de fuite de métadonnées sensibles (chemins internes, author_user_id)
    """
    data = setup_storymaps_test_data
    t_a = data["t_a"]
    t_b = data["t_b"]
    u_a = data["u_a"]
    u_b = data["u_b"]
    photo = data["photo"]

    # Créer 1 récit publié sur Territoire A
    # Créer 1 récit brouillon sur Territoire A
    # Créer 1 récit publié sur Territoire B
    async with AsyncSessionLocal() as session:
        sm_pub_a = Storymap(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            slug="decouverte-du-vieux-toulon",
            title="Découverte du Vieux Toulon",
            summary="Une balade à travers les ruelles médiévales.",
            cover_image_path="internal/storage/covers/vieux_toulon.webp",
            status=StorymapStatus.PUBLISHED,
        )
        step_pub = StorymapStep(
            storymap=sm_pub_a,
            photo_id=photo.id,
            step_order=0,
            title="Place Puget",
            content_markdown="La fontaine des Trois Dauphins.",
            audio_file_path="internal/storage/audio/puget.mp3",
            camera_lat=43.125,
            camera_lng=5.931,
            camera_zoom=16.0,
            camera_bearing=45.0,
            camera_pitch=30.0,
        )
        sm_pub_a.steps.append(step_pub)

        sm_draft_a = Storymap(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            slug="recit-en-preparation",
            title="Récit en Préparation",
            status=StorymapStatus.DRAFT,
        )

        sm_pub_b = Storymap(
            id=uuid.uuid4(),
            territory_id=t_b.id,
            author_user_id=u_b.id,
            slug="le-panier-marseillais",
            title="Le Panier Marseillais",
            status=StorymapStatus.PUBLISHED,
        )

        session.add_all([sm_pub_a, sm_draft_a, sm_pub_b])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Consultation publique du récit publié sur Territoire A
        res_pub = await client.get(
            "/api/v1/storymaps/decouverte-du-vieux-toulon",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_pub.status_code == 200
        item = res_pub.json()
        assert item["slug"] == "decouverte-du-vieux-toulon"
        assert item["title"] == "Découverte du Vieux Toulon"
        assert item["status"] == "published"
        assert "cover_image_url" in item
        assert len(item["steps"]) == 1

        # Vérification stricte de confidentialité (absence de chemins physiques et author_user_id)
        assert "cover_image_path" not in item
        assert "author_user_id" not in item
        step_detail = item["steps"][0]
        assert "audio_file_path" not in step_detail
        assert "audio_url" in step_detail
        assert step_detail["lat"] == 43.125
        assert step_detail["lng"] == 5.931
        assert step_detail["photo"] is not None
        assert step_detail["photo"]["title"] == "Photo d'archive port 1900"
        assert "file_original_path" not in step_detail["photo"]

        # 2. Consultation d'une storymap en brouillon -> 404 (masque le brouillon)
        res_draft = await client.get(
            "/api/v1/storymaps/recit-en-preparation",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_draft.status_code == 404
        assert res_draft.json()["error"]["code"] == "STORYMAP_NOT_FOUND"

        # 3. Consultation d'un récit d'un autre territoire -> 404 (isolation multi-territoire)
        res_other = await client.get(
            "/api/v1/storymaps/le-panier-marseillais",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_other.status_code == 404

        # 4. Catalogue public du territoire A : ne liste que le récit publié de Toulon
        res_list = await client.get(
            "/api/v1/storymaps",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_list.status_code == 200
        catalogue = res_list.json()
        assert catalogue["total"] == 1
        assert catalogue["items"][0]["slug"] == "decouverte-du-vieux-toulon"


@pytest.mark.asyncio
async def test_public_storymaps_mask_draft_photos(setup_storymaps_test_data):
    """Vérifie que les photos en statut draft liées à une étape sont totalement masquées dans les endpoints publics."""
    data = setup_storymaps_test_data
    t_a = data["t_a"]
    u_a = data["u_a"]
    photo_pub = data["photo"]
    photo_draft = data["photo_draft"]

    async with AsyncSessionLocal() as session:
        sm = Storymap(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            slug="recit-photos-mixtes",
            title="Récit avec photos mixtes",
            status=StorymapStatus.PUBLISHED,
        )
        step1 = StorymapStep(
            storymap=sm,
            photo_id=photo_pub.id,
            step_order=0,
            title="Étape photo publiée",
            camera_lat=43.12,
            camera_lng=5.93,
        )
        step2 = StorymapStep(
            storymap=sm,
            photo_id=photo_draft.id,
            step_order=1,
            title="Étape photo brouillon",
            camera_lat=43.13,
            camera_lng=5.94,
        )
        sm.steps.extend([step1, step2])
        session.add(sm)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Détail public
        res = await client.get(
            "/api/v1/storymaps/recit-photos-mixtes",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res.status_code == 200
        body = res.json()
        s1 = body["steps"][0]
        s2 = body["steps"][1]

        assert s1["photo"] is not None
        assert s1["photo_id"] == str(photo_pub.id)
        # La photo en statut draft ne doit pas être visible
        assert s2["photo"] is None
        assert s2["photo_id"] is None

        # 2. Liste publique (catalogue)
        res_list = await client.get(
            "/api/v1/storymaps",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_list.status_code == 200
        matched = next(s for s in res_list.json()["items"] if s["slug"] == "recit-photos-mixtes")
        assert matched["steps"][0]["photo"] is not None
        assert matched["steps"][1]["photo"] is None
        assert matched["steps"][1]["photo_id"] is None


@pytest.mark.asyncio
async def test_step_rejects_foreign_or_nonexistent_photo(setup_storymaps_test_data):
    """Vérifie le rejet avec code 422 (INVALID_PHOTO) si une photo appartient à un autre territoire ou est introuvable."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]
    photo_b = data["photo_b"]
    fake_photo_id = uuid.uuid4()

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Création initiale d'une storymap avec photo d'un autre territoire -> 422
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Storymap Photo Marseille dans Toulon",
                    "steps": [
                        {
                            "title": "Étape rejetée",
                            "lat": 43.12,
                            "lng": 5.93,
                            "photo_id": str(photo_b.id),
                        }
                    ],
                },
            )
            assert res_create.status_code == 422
            assert res_create.json()["error"]["code"] == "INVALID_PHOTO"

            # 2. Créer une storymap valide sans étape
            res_ok = await client.post(
                "/api/v1/admin/storymaps",
                json={"title": "Storymap Toulon Test Photo"},
            )
            assert res_ok.status_code == 201
            sm_id = res_ok.json()["id"]

            # 3. Ajout d'une étape avec une photo inexistante -> 422
            res_add_fake = await client.post(
                f"/api/v1/admin/storymaps/{sm_id}/steps",
                json={
                    "title": "Étape Photo Inexistante",
                    "lat": 43.12,
                    "lng": 5.93,
                    "photo_id": str(fake_photo_id),
                },
            )
            assert res_add_fake.status_code == 422
            assert res_add_fake.json()["error"]["code"] == "INVALID_PHOTO"

            # 4. Ajout d'une étape valide sans photo
            res_step_ok = await client.post(
                f"/api/v1/admin/storymaps/{sm_id}/steps",
                json={"title": "Étape Initiale", "lat": 43.12, "lng": 5.93},
            )
            assert res_step_ok.status_code == 201
            step_id = res_step_ok.json()["id"]

            # 5. Modification de l'étape pour lui associer la photo de Marseille -> 422
            res_up_foreign = await client.put(
                f"/api/v1/admin/storymaps/{sm_id}/steps/{step_id}",
                json={"photo_id": str(photo_b.id)},
            )
            assert res_up_foreign.status_code == 422
            assert res_up_foreign.json()["error"]["code"] == "INVALID_PHOTO"
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_delete_storymap_cascades_to_steps(setup_storymaps_test_data):
    """Vérifie que la suppression d'une storymap supprime en cascade toutes ses étapes."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Storymap à Supprimer",
                    "steps": [
                        {"title": "Étape 1", "lat": 43.1, "lng": 5.9},
                        {"title": "Étape 2", "lat": 43.2, "lng": 5.8},
                    ],
                },
            )
            assert res_create.status_code == 201
            sm_id = uuid.UUID(res_create.json()["id"])
            step_ids = [uuid.UUID(s["id"]) for s in res_create.json()["steps"]]

            # Vérifier que les étapes sont bien en base
            async with AsyncSessionLocal() as session:
                steps_db = (
                    await session.execute(
                        select(StorymapStep).where(StorymapStep.storymap_id == sm_id)
                    )
                ).scalars().all()
                assert len(steps_db) == 2

            # Supprimer la storymap
            res_del = await client.delete(f"/api/v1/admin/storymaps/{sm_id}")
            assert res_del.status_code == 204

            # Vérifier que la storymap ET toutes ses étapes ont disparu de la BDD
            async with AsyncSessionLocal() as session:
                sm_check = (
                    await session.execute(
                        select(Storymap).where(Storymap.id == sm_id)
                    )
                ).scalar_one_or_none()
                assert sm_check is None

                steps_check = (
                    await session.execute(
                        select(StorymapStep).where(StorymapStep.id.in_(step_ids))
                    )
                ).scalars().all()
                assert len(steps_check) == 0
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_delete_photo_sets_null_on_step(setup_storymaps_test_data):
    """Vérifie que la suppression d'une photo liée passe photo_id à NULL sans effacer l'étape (SET NULL)."""
    data = setup_storymaps_test_data
    u_a = data["u_a"]
    t_a = data["t_a"]

    # Créer une photo spécifique pour ce test
    async with AsyncSessionLocal() as session:
        tmp_photo = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo temporaire à supprimer",
            latitude=43.12,
            longitude=5.93,
            status=PhotoStatus.PUBLISHED,
        )
        session.add(tmp_photo)
        await session.commit()
        await session.refresh(tmp_photo)
        photo_id = tmp_photo.id

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Storymap Test Set Null",
                    "steps": [
                        {
                            "title": "Étape avec photo",
                            "lat": 43.1,
                            "lng": 5.9,
                            "photo_id": str(photo_id),
                        }
                    ],
                },
            )
            assert res_create.status_code == 201
            step_id = uuid.UUID(res_create.json()["steps"][0]["id"])

            # Supprimer la photo en BDD
            async with AsyncSessionLocal() as session:
                await session.execute(delete(Photo).where(Photo.id == photo_id))
                await session.commit()

            # Vérifier l'étape : elle doit toujours exister et son photo_id est devenu NULL
            async with AsyncSessionLocal() as session:
                step_db = (
                    await session.execute(
                        select(StorymapStep).where(StorymapStep.id == step_id)
                    )
                ).scalar_one_or_none()
                assert step_db is not None
                assert step_db.photo_id is None
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_upload_and_delete_storymap_cover(setup_storymaps_test_data):
    """Vérifie le téléversement d'une image de couverture, sa conversion WebP et sa suppression."""
    u_a = setup_storymaps_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={"title": "Récit avec couverture"},
            )
            assert res_create.status_code == 201
            storymap_id = res_create.json()["id"]

            # Création d'une image de test valide
            import io
            from PIL import Image
            buf = io.BytesIO()
            img = Image.new("RGB", (64, 64), color="red")
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            # Upload de la couverture
            res_upload = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/cover",
                files={"file": ("cover.png", img_bytes, "image/png")},
            )
            assert res_upload.status_code == 200
            data_upload = res_upload.json()
            assert data_upload["cover_image_path"] is not None
            assert data_upload["cover_image_path"].endswith(".webp")
            assert data_upload["cover_image_url"] is not None

            # Suppression de la couverture
            res_del = await client.delete(f"/api/v1/admin/storymaps/{storymap_id}/cover")
            assert res_del.status_code == 200
            data_del = res_del.json()
            assert data_del["cover_image_path"] is None
            assert data_del["cover_image_url"] is None
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_upload_and_delete_storymap_step_audio(setup_storymaps_test_data):
    """Vérifie le téléversement d'un document sonore sur une étape et sa suppression."""
    u_a = setup_storymaps_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Récit sonore",
                    "steps": [
                        {
                            "title": "Étape avec audio",
                            "lat": 43.12,
                            "lng": 5.93,
                        }
                    ],
                },
            )
            assert res_create.status_code == 201
            storymap_id = res_create.json()["id"]
            step_id = res_create.json()["steps"][0]["id"]

            fake_audio = b"ID3\x03\x00\x00\x00\x00\x00#TSSE" + b"\x00" * 50

            # Upload audio
            res_audio = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/steps/{step_id}/audio",
                files={"file": ("narration.mp3", fake_audio, "audio/mpeg")},
            )
            assert res_audio.status_code == 200
            data_audio = res_audio.json()
            assert data_audio["audio_file_path"] is not None
            assert data_audio["audio_file_path"].endswith(".mp3")
            assert data_audio["audio_url"] is not None

            # Suppression audio
            res_del = await client.delete(f"/api/v1/admin/storymaps/{storymap_id}/steps/{step_id}/audio")
            assert res_del.status_code == 200
            data_del = res_del.json()
            assert data_del["audio_file_path"] is None
            assert data_del["audio_url"] is None
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_upload_media_validation_rejections(setup_storymaps_test_data):
    """Vérifie le rejet des formats de fichiers non supportés."""
    u_a = setup_storymaps_test_data["u_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Récit validation médias",
                    "steps": [{"title": "Étape", "lat": 43.1, "lng": 5.9}],
                },
            )
            storymap_id = res_create.json()["id"]
            step_id = res_create.json()["steps"][0]["id"]

            # Rejet image invalide
            res_bad_img = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/cover",
                files={"file": ("corrupt.png", b"not-an-image", "image/png")},
            )
            assert res_bad_img.status_code == 400
            assert res_bad_img.json()["error"]["code"] == "INVALID_IMAGE_FORMAT"

            # Rejet format audio invalide (ex: exécutable ou texte)
            res_bad_audio = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/steps/{step_id}/audio",
                files={"file": ("script.sh", b"#!/bin/bash", "text/x-shellscript")},
            )
            assert res_bad_audio.status_code == 400
            assert res_bad_audio.json()["error"]["code"] == "INVALID_AUDIO_FORMAT"
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_media_cross_territory_isolation(setup_storymaps_test_data):
    """Vérifie l'étanchéité multi-territoire : u_b ne peut pas téléverser ni supprimer de médias sur un récit de u_a."""
    u_a = setup_storymaps_test_data["u_a"]
    u_b = setup_storymaps_test_data["u_b"]

    # Création du récit et de l'étape sur le territoire A par u_a
    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_create = await client.post(
                "/api/v1/admin/storymaps",
                json={
                    "title": "Récit Territoire A",
                    "steps": [{"title": "Étape A", "lat": 43.1, "lng": 5.9}],
                },
            )
            assert res_create.status_code == 201
            storymap_id = res_create.json()["id"]
            step_id = res_create.json()["steps"][0]["id"]
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)

    # Tentatives d'accès par u_b (territoire B) -> Doit retourner HTTP 404 (isolation stricte AD-2)
    app.dependency_overrides[get_current_active_user] = lambda: u_b
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            import io
            from PIL import Image
            buf = io.BytesIO()
            Image.new("RGB", (32, 32), color="green").save(buf, format="PNG")
            img_bytes = buf.getvalue()
            fake_audio = b"ID3\x03\x00\x00\x00\x00\x00#TSSE" + b"\x00" * 50

            # 1. Upload couverture interdite
            res_cover = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/cover",
                files={"file": ("cover.png", img_bytes, "image/png")},
            )
            assert res_cover.status_code == 404
            assert res_cover.json()["error"]["code"] == "STORYMAP_NOT_FOUND"

            # 2. Suppression couverture interdite
            res_del_cover = await client.delete(f"/api/v1/admin/storymaps/{storymap_id}/cover")
            assert res_del_cover.status_code == 404
            assert res_del_cover.json()["error"]["code"] == "STORYMAP_NOT_FOUND"

            # 3. Upload audio interdit
            res_audio = await client.post(
                f"/api/v1/admin/storymaps/{storymap_id}/steps/{step_id}/audio",
                files={"file": ("sound.mp3", fake_audio, "audio/mpeg")},
            )
            assert res_audio.status_code == 404
            assert res_audio.json()["error"]["code"] == "STORYMAP_NOT_FOUND"

            # 4. Suppression audio interdite
            res_del_audio = await client.delete(
                f"/api/v1/admin/storymaps/{storymap_id}/steps/{step_id}/audio"
            )
            assert res_del_audio.status_code == 404
            assert res_del_audio.json()["error"]["code"] == "STORYMAP_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


