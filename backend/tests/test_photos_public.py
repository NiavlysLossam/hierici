import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.territory import Territory
from app.models.photo import Photo, PhotoStatus


@pytest.fixture
async def setup_public_test_data():
    """Prépare un territoire de test et un lot de photos (publiées et brouillons)."""
    async with AsyncSessionLocal() as session:
        t_a = Territory(
            id=uuid.uuid4(),
            slug=f"territoire-public-{uuid.uuid4().hex[:6]}",
            name="Territoire Public Test",
            center_lat=43.125,
            center_lng=5.930,
            default_zoom=14,
        )
        t_b = Territory(
            id=uuid.uuid4(),
            slug=f"autre-territoire-{uuid.uuid4().hex[:6]}",
            name="Autre Territoire Test",
            center_lat=48.856,
            center_lng=2.352,
            default_zoom=12,
        )
        session.add_all([t_a, t_b])
        await session.commit()
        await session.refresh(t_a)
        await session.refresh(t_b)

        # Photos sur Territoire A
        p1 = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            title="Place de la Liberté 1910",
            description="Vue d'ensemble animée",
            photographer="Marius Bar",
            year_taken=1910,
            archive_source="Archives Municipales",
            archive_ref="10Fi12",
            file_original_path="private/storage/original_p1.jpg",
            file_display_path="private/storage/display_p1.webp",
            file_thumb_path="private/storage/thumb_p1.webp",
            latitude=43.124500,
            longitude=5.928500,
            bearing=135,
            field_of_view=60,
            status=PhotoStatus.PUBLISHED,
        )
        p2 = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            title="Port de Commerce 1925",
            description="Bateaux à vapeur à quai",
            photographer="Inconnu",
            year_taken=1925,
            archive_source="Chambre de Commerce",
            archive_ref="CC-88",
            file_display_path="private/storage/display_p2.webp",
            latitude=43.120100,
            longitude=5.932000,
            bearing=180,
            field_of_view=75,
            status=PhotoStatus.PUBLISHED,
        )
        p3_draft = Photo(
            id=uuid.uuid4(),
            territory_id=t_a.id,
            title="Brouillon Secret Non Publié",
            latitude=43.122000,
            longitude=5.931000,
            status=PhotoStatus.DRAFT,
        )

        # Photo sur Territoire B
        p_b = Photo(
            id=uuid.uuid4(),
            territory_id=t_b.id,
            title="Notre-Dame de Paris 1900",
            latitude=48.853000,
            longitude=2.349900,
            status=PhotoStatus.PUBLISHED,
        )

        session.add_all([p1, p2, p3_draft, p_b])
        await session.commit()
        await session.refresh(p1)
        await session.refresh(p2)
        await session.refresh(p3_draft)
        await session.refresh(p_b)

        data = {
            "t_a": t_a,
            "t_b": t_b,
            "p1": p1,
            "p2": p2,
            "p3_draft": p3_draft,
            "p_b": p_b,
        }

    yield data

    # Nettoyage
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Photo).where(Photo.territory_id.in_([t_a.id, t_b.id])))
        await session.execute(delete(Territory).where(Territory.id.in_([t_a.id, t_b.id])))
        await session.commit()


@pytest.mark.asyncio
async def test_list_public_photos_geojson(setup_public_test_data):
    """Vérifie que l'endpoint public retourne une FeatureCollection GeoJSON valide avec les seules photos publiées du territoire."""
    data = setup_public_test_data
    t_a = data["t_a"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/photos",
            headers={"X-Territory-Slug": t_a.slug},
        )

    assert response.status_code == 200
    geojson = response.json()

    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) == 2

    feature_ids = [f["id"] for f in geojson["features"]]
    assert str(data["p1"].id) in feature_ids
    assert str(data["p2"].id) in feature_ids
    # Le brouillon et la photo de l'autre territoire ne doivent jamais être présents
    assert str(data["p3_draft"].id) not in feature_ids
    assert str(data["p_b"].id) not in feature_ids

    # Vérification de la géométrie Point GeoJSON (lon, lat)
    f1 = next(f for f in geojson["features"] if f["id"] == str(data["p1"].id))
    assert f1["geometry"]["type"] == "Point"
    assert f1["geometry"]["coordinates"] == [5.928500, 43.124500]
    assert f1["properties"]["title"] == "Place de la Liberté 1910"
    assert f1["properties"]["bearing"] == 135
    assert f1["properties"]["field_of_view"] == 60


@pytest.mark.asyncio
async def test_list_public_photos_filters(setup_public_test_data):
    """Vérifie les filtres par année et par mot-clé de recherche."""
    data = setup_public_test_data
    t_a = data["t_a"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Filtre par année minimale
        res_year = await client.get(
            "/api/v1/photos?year_min=1920",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_year.status_code == 200
        features = res_year.json()["features"]
        assert len(features) == 1
        assert features[0]["id"] == str(data["p2"].id)

        # Filtre par recherche textuelle (titre)
        res_search = await client.get(
            "/api/v1/photos?search=Liberté",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_search.status_code == 200
        search_features = res_search.json()["features"]
        assert len(search_features) == 1
        assert search_features[0]["id"] == str(data["p1"].id)

        # Filtre par recherche textuelle (photographe)
        res_photo = await client.get(
            "/api/v1/photos?search=Marius",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_photo.status_code == 200
        assert len(res_photo.json()["features"]) == 1


@pytest.mark.asyncio
async def test_list_public_photos_invalid_year_range(setup_public_test_data):
    """Vérifie que l'inversion d'années ou des valeurs hors limites renvoient HTTP 422."""
    data = setup_public_test_data
    t_a = data["t_a"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # year_min > year_max
        res_inv = await client.get(
            "/api/v1/photos?year_min=1950&year_max=1920",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_inv.status_code == 422

        # Valeur hors borne (>3000)
        res_overflow = await client.get(
            "/api/v1/photos?year_min=999999",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_overflow.status_code == 422


@pytest.mark.asyncio
async def test_list_public_photos_empty_and_combined_filters(setup_public_test_data):
    """Vérifie le retour d'une FeatureCollection vide conforme RFC 7946 lors d'un filtrage sans résultat."""
    data = setup_public_test_data
    t_a = data["t_a"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_empty = await client.get(
            "/api/v1/photos?year_min=1900&year_max=1905",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_empty.status_code == 200
        body = res_empty.json()
        assert body["type"] == "FeatureCollection"
        assert body["features"] == []


@pytest.mark.asyncio
async def test_get_public_photo_detail_and_privacy(setup_public_test_data):
    """Vérifie l'accès public au détail d'une photo et l'absence stricte de fuite de données internes."""
    data = setup_public_test_data
    t_a = data["t_a"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Photo publiée existante
        res_ok = await client.get(
            f"/api/v1/photos/{data['p1'].id}",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_ok.status_code == 200
        detail = res_ok.json()
        assert detail["id"] == str(data["p1"].id)
        assert detail["title"] == "Place de la Liberté 1910"

        # Vérification stricte de confidentialité (P1-1) : aucun chemin physique interne ni id d'auteur
        assert "author_user_id" not in detail
        assert "created_by_id" not in detail
        assert "file_original_path" not in detail
        assert "file_display_path" not in detail
        assert "file_thumb_path" not in detail
        assert "status" not in detail

        # Photo en brouillon -> 404
        res_draft = await client.get(
            f"/api/v1/photos/{data['p3_draft'].id}",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_draft.status_code == 404

        # Photo d'un autre territoire -> 404
        res_other = await client.get(
            f"/api/v1/photos/{data['p_b'].id}",
            headers={"X-Territory-Slug": t_a.slug},
        )
        assert res_other.status_code == 404
