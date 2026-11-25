import io
import uuid
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.auth import get_current_active_user
from app.models.territory import Territory
from app.models.user import User, UserRole
from app.models.photo import Photo, PhotoStatus
from app.services.image_service import (
    ImageService,
    get_image_service,
    FileTooLargeError,
    InvalidImageFormatError,
)
from app.services.storage import get_storage_driver


def create_test_image(
    width: int,
    height: int,
    fmt: str = "JPEG",
    orientation: int | None = None,
    color: tuple[int, int, int] | str = (100, 150, 200),
) -> bytes:
    """Génère un flux d'octets d'image valide en mémoire pour les tests."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()

    if orientation is not None and fmt.upper() in ("JPEG", "JPG"):
        exif = img.getexif()
        exif[0x0112] = orientation
        img.save(buf, format=fmt, exif=exif)
    else:
        img.save(buf, format=fmt)

    return buf.getvalue()


@pytest.fixture
async def setup_upload_test_data():
    """Prépare les territoires, contributeurs et fiches photos pour les tests d'upload."""
    async with AsyncSessionLocal() as session:
        t_a = Territory(
            id=uuid.uuid4(),
            slug=f"toulon-{uuid.uuid4().hex[:6]}",
            name="Toulon Upload Test",
            center_lat=43.12,
            center_lng=5.93,
            default_zoom=13,
        )
        t_b = Territory(
            id=uuid.uuid4(),
            slug=f"marseille-{uuid.uuid4().hex[:6]}",
            name="Marseille Upload Test",
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
            full_name="Contributeur Toulon",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_a.id,
            is_active=True,
        )
        u_b = User(
            id=uuid.uuid4(),
            email=f"contrib_b_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Contributeur Marseille",
            role=UserRole.CONTRIBUTOR,
            territory_id=t_b.id,
            is_active=True,
        )
        u_admin = User(
            id=uuid.uuid4(),
            email=f"superadmin_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            full_name="Super Administrateur",
            role=UserRole.SUPERADMIN,
            territory_id=t_a.id,
            is_active=True,
        )
        session.add_all([u_a, u_b, u_admin])
        await session.commit()
        await session.refresh(u_a)
        await session.refresh(u_b)
        await session.refresh(u_admin)

        p_a = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            author_user_id=u_a.id,
            title="Photo A Toulon",
            status=PhotoStatus.DRAFT,
        )
        p_b = Photo(
            id=uuid.uuid4(),
            territory_id=t_b.id,
            author_user_id=u_b.id,
            title="Photo B Marseille",
            status=PhotoStatus.DRAFT,
        )
        session.add_all([p_a, p_b])
        await session.commit()
        await session.refresh(p_a)
        await session.refresh(p_b)

    yield {
        "t_a": t_a,
        "t_b": t_b,
        "u_a": u_a,
        "u_b": u_b,
        "u_admin": u_admin,
        "p_a": p_a,
        "p_b": p_b,
    }

    # Nettoyage
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Photo).where(Photo.territory_id.in_([t_a.id, t_b.id]))
        )
        await session.execute(
            delete(User).where(User.id.in_([u_a.id, u_b.id, u_admin.id]))
        )
        await session.execute(
            delete(Territory).where(Territory.id.in_([t_a.id, t_b.id]))
        )
        await session.commit()


# =====================================================================
# Tests Unitaires ImageService
# =====================================================================

def test_image_service_size_validation():
    """Vérifie que la taille max de 25 Mo est strictement appliquée."""
    service = ImageService()
    # 25 Mo pile autorisés
    service.validate_file_size(b"x" * (25 * 1024 * 1024))

    # 25 Mo + 1 octet rejetés
    with pytest.raises(FileTooLargeError):
        service.validate_file_size(b"x" * (25 * 1024 * 1024 + 1))


def test_image_service_invalid_formats():
    """Vérifie le rejet des formats non autorisés ou des fichiers vides/corrompus."""
    service = ImageService()

    # Fichier vide
    with pytest.raises(InvalidImageFormatError):
        service.validate_and_open_image(b"")

    # Contenu non image (PDF, texte, executable)
    with pytest.raises(InvalidImageFormatError):
        service.validate_and_open_image(b"%PDF-1.4 header text dummy")

    with pytest.raises(InvalidImageFormatError):
        service.validate_and_open_image(b"MZ\x90\x00\x03\x00\x00\x00binary executable")


def test_image_service_supported_formats():
    """Vérifie le bon support de JPEG, PNG, WEBP, TIFF."""
    service = ImageService()
    for fmt in ("JPEG", "PNG", "WEBP", "TIFF"):
        img_bytes = create_test_image(100, 100, fmt=fmt)
        img, detected_fmt = service.validate_and_open_image(img_bytes)
        assert detected_fmt in ("JPEG", "PNG", "WEBP", "TIFF")
        assert img.size == (100, 100)


def test_image_service_exif_orientation_redressed():
    """Vérifie que l'orientation EXIF 6 (rotation 90° CCW) est redressée à la verticale."""
    service = ImageService()
    # Image paysage 400x200 avec flag EXIF 6 (doit devenir portrait 200x400)
    img_bytes = create_test_image(400, 200, fmt="JPEG", orientation=6)
    img, _ = service.validate_and_open_image(img_bytes)
    assert img.size == (400, 200)

    oriented = service.normalize_image(img)
    assert oriented.size == (200, 400)


def test_image_service_variant_generation():
    """Vérifie les contraintes dimensionnelles des variantes display et thumb."""
    service = ImageService()
    # Image HD 4000x3000
    img_bytes = create_test_image(4000, 3000, fmt="JPEG")
    res = service.process_image(
        content=img_bytes,
        territory_id=uuid.uuid4(),
        photo_id=uuid.uuid4(),
        filename="scan_archive.jpg",
    )

    # Original
    assert res.width == 4000
    assert res.height == 3000
    assert res.original.path.endswith("original.jpg")
    assert res.original.content == img_bytes

    # Display (max 2048px -> 2048x1536)
    assert res.display.path.endswith("display.webp")
    assert res.display.width == 2048
    assert res.display.height == 1536
    display_pil = Image.open(io.BytesIO(res.display.content))
    assert display_pil.format == "WEBP"
    assert display_pil.size == (2048, 1536)
    # Vérification métadonnées EXIF purgées
    assert not bool(display_pil.getexif())

    # Thumb (max 400px -> 400x300)
    assert res.thumb.path.endswith("thumb.webp")
    assert res.thumb.width == 400
    assert res.thumb.height == 300
    thumb_pil = Image.open(io.BytesIO(res.thumb.content))
    assert thumb_pil.format == "WEBP"
    assert thumb_pil.size == (400, 300)
    assert not bool(thumb_pil.getexif())


def test_image_service_smaller_image_not_upscaled():
    """Vérifie qu'une petite image (ex: 300x200) n'est pas agrandie artificiellement."""
    service = ImageService()
    img_bytes = create_test_image(300, 200, fmt="PNG")
    res = service.process_image(
        content=img_bytes,
        territory_id=uuid.uuid4(),
        photo_id=uuid.uuid4(),
        filename="small.png",
    )
    assert res.display.width == 300
    assert res.display.height == 200
    assert res.thumb.width == 300
    assert res.thumb.height == 200


# =====================================================================
# Tests d'Intégration API REST
# =====================================================================

async def test_upload_valid_hd_jpeg_existing_photo(setup_upload_test_data):
    """Scénario 1: Upload d'une image JPEG HD (4000x3000) sur une photo existante."""
    u_a = setup_upload_test_data["u_a"]
    t_a = setup_upload_test_data["t_a"]
    p_a = setup_upload_test_data["p_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            jpeg_hd = create_test_image(4000, 3000, fmt="JPEG")
            files = {"file": ("archive_hd.jpg", jpeg_hd, "image/jpeg")}

            response = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files=files,
            )

            assert response.status_code == 200
            data = response.json()

            # Vérification des propriétés retournées
            assert data["photo_id"] == str(p_a.id)
            assert data["width"] == 4000
            assert data["height"] == 3000
            assert data["file_original_path"] == f"photos/{t_a.id}/{p_a.id}/original.jpg"
            assert data["file_display_path"] == f"photos/{t_a.id}/{p_a.id}/display.webp"
            assert data["file_thumb_path"] == f"photos/{t_a.id}/{p_a.id}/thumb.webp"
            assert data["original_url"].endswith(data["file_original_path"])
            assert data["display_url"].endswith(data["file_display_path"])
            assert data["thumb_url"].endswith(data["file_thumb_path"])

            # Vérification des URLs sur le PhotoRead embarqué
            assert data["photo"]["original_url"].endswith(data["file_original_path"])
            assert data["photo"]["display_url"].endswith(data["file_display_path"])
            assert data["photo"]["thumb_url"].endswith(data["file_thumb_path"])

            # Vérification de la persistance en base de données
            async with AsyncSessionLocal() as session:
                refreshed = await session.get(Photo, p_a.id)
                assert refreshed.file_original_path == data["file_original_path"]
                assert refreshed.file_display_path == data["file_display_path"]
                assert refreshed.file_thumb_path == data["file_thumb_path"]

            # Vérification de l'existence physique dans le StorageDriver
            storage = get_storage_driver()
            assert await storage.exists(data["file_original_path"]) is True
            assert await storage.exists(data["file_display_path"]) is True
            assert await storage.exists(data["file_thumb_path"]) is True
    finally:
        app.dependency_overrides.clear()


async def test_upload_file_too_large_rejected(setup_upload_test_data):
    """Scénario 2: Fichier de 28 Mo rejeté avec HTTP 400 et RFC 7807 FILE_TOO_LARGE."""
    u_a = setup_upload_test_data["u_a"]
    p_a = setup_upload_test_data["p_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 28 Mo
            huge_content = b"0" * (28 * 1024 * 1024)
            files = {"file": ("too_large.jpg", huge_content, "image/jpeg")}

            response = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files=files,
            )

            assert response.status_code == 400
            data = response.json()
            assert data["title"] == "FILE_TOO_LARGE"
            assert data["status"] == 400
            assert "FILE_TOO_LARGE" in data["error"]["code"]
    finally:
        app.dependency_overrides.clear()


async def test_upload_invalid_format_rejected(setup_upload_test_data):
    """Scénario 3: Fichier non image rejeté avec HTTP 400 et RFC 7807 INVALID_IMAGE_FORMAT."""
    u_a = setup_upload_test_data["u_a"]
    p_a = setup_upload_test_data["p_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            files = {"file": ("malicious.exe", b"MZ\x90\x00NotAnImageFile", "application/octet-stream")}

            response = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files=files,
            )

            assert response.status_code == 400
            data = response.json()
            assert data["title"] == "INVALID_IMAGE_FORMAT"
            assert data["status"] == 400
            assert "INVALID_IMAGE_FORMAT" in data["error"]["code"]
    finally:
        app.dependency_overrides.clear()


async def test_upload_exif_orientation_via_api(setup_upload_test_data):
    """Scénario 4: Image avec flag EXIF orientation 6 redressée à la verticale dans l'API."""
    u_a = setup_upload_test_data["u_a"]
    p_a = setup_upload_test_data["p_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 600x300 paysage avec orientation 6 -> doit être redressée en 300x600 portrait
            img_bytes = create_test_image(600, 300, fmt="JPEG", orientation=6)
            files = {"file": ("portrait_sideways.jpg", img_bytes, "image/jpeg")}

            response = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files=files,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["width"] == 300
            assert data["height"] == 600

            # Vérification physique de l'image display
            storage = get_storage_driver()
            display_bytes = await storage.read(data["file_display_path"])
            disp_img = Image.open(io.BytesIO(display_bytes))
            assert disp_img.size == (300, 600)
    finally:
        app.dependency_overrides.clear()


async def test_upload_replacement_purges_old_media(setup_upload_test_data):
    """Scénario 5: Le remplacement d'image purge automatiquement les anciens fichiers via StorageDriver."""
    u_a = setup_upload_test_data["u_a"]
    p_a = setup_upload_test_data["p_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            storage = get_storage_driver()

            # 1. Premier téléversement (PNG)
            png_bytes = create_test_image(200, 200, fmt="PNG")
            resp1 = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files={"file": ("first_cliche.png", png_bytes, "image/png")},
            )
            assert resp1.status_code == 200
            data1 = resp1.json()
            old_original = data1["file_original_path"]
            old_display = data1["file_display_path"]
            old_thumb = data1["file_thumb_path"]

            assert await storage.exists(old_original) is True
            assert await storage.exists(old_display) is True
            assert await storage.exists(old_thumb) is True

            # 2. Deuxième téléversement (remplacement par JPEG)
            jpeg_bytes = create_test_image(400, 400, fmt="JPEG")
            resp2 = await ac.post(
                f"/api/v1/admin/photos/{p_a.id}/upload",
                files={"file": ("second_cliche.jpg", jpeg_bytes, "image/jpeg")},
            )
            assert resp2.status_code == 200
            data2 = resp2.json()
            new_original = data2["file_original_path"]

            # L'ancien fichier original PNG a été purgé
            assert await storage.exists(old_original) is False
            # Le nouveau original JPG existe
            assert await storage.exists(new_original) is True
            # Les déclinaisons display et thumb existent bien
            assert await storage.exists(data2["file_display_path"]) is True
            assert await storage.exists(data2["file_thumb_path"]) is True
    finally:
        app.dependency_overrides.clear()


async def test_upload_wrong_territory_returns_404(setup_upload_test_data):
    """Scénario 6: Un contributeur du Territoire A ne peut pas téléverser sur une photo du Territoire B."""
    u_a = setup_upload_test_data["u_a"]
    p_b = setup_upload_test_data["p_b"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            img_bytes = create_test_image(200, 200, fmt="JPEG")
            response = await ac.post(
                f"/api/v1/admin/photos/{p_b.id}/upload",
                files={"file": ("hack.jpg", img_bytes, "image/jpeg")},
            )

            assert response.status_code == 404
            data = response.json()
            assert data["title"] == "PHOTO_NOT_FOUND"
            assert data["error"]["code"] == "PHOTO_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_direct_upload_creates_draft_photo(setup_upload_test_data):
    """Scénario 7: Téléversement direct via POST /admin/photos/upload créant une fiche photo en brouillon."""
    u_a = setup_upload_test_data["u_a"]
    t_a = setup_upload_test_data["t_a"]

    app.dependency_overrides[get_current_active_user] = lambda: u_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            img_bytes = create_test_image(1200, 800, fmt="JPEG")
            response = await ac.post(
                "/api/v1/admin/photos/upload",
                files={"file": ("port_de_toulon_1905.jpg", img_bytes, "image/jpeg")},
                data={"title": "Port de Toulon 1905"},
            )

            assert response.status_code == 201
            data = response.json()
            created_id = uuid.UUID(data["photo_id"])

            assert data["width"] == 1200
            assert data["height"] == 800
            assert data["photo"]["title"] == "Port de Toulon 1905"
            assert data["photo"]["status"] == "draft"

            # Vérification stockage
            storage = get_storage_driver()
            assert await storage.exists(data["file_original_path"]) is True
            assert await storage.exists(data["file_display_path"]) is True
            assert await storage.exists(data["file_thumb_path"]) is True

            # Nettoyage
            async with AsyncSessionLocal() as session:
                photo_db = await session.get(Photo, created_id)
                if photo_db:
                    await session.delete(photo_db)
                    await session.commit()
    finally:
        app.dependency_overrides.clear()


async def test_superadmin_can_upload_to_any_photo(setup_upload_test_data):
    """Scénario 8: Un superadmin peut téléverser une image sur n'importe quel territoire."""
    u_admin = setup_upload_test_data["u_admin"]
    p_b = setup_upload_test_data["p_b"]

    app.dependency_overrides[get_current_active_user] = lambda: u_admin
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            img_bytes = create_test_image(300, 300, fmt="JPEG")
            response = await ac.post(
                f"/api/v1/admin/photos/{p_b.id}/upload",
                files={"file": ("admin_override.jpg", img_bytes, "image/jpeg")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["photo_id"] == str(p_b.id)
    finally:
        app.dependency_overrides.clear()
