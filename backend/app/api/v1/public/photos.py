import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import noload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.territory import get_current_territory
from app.models.territory import Territory
from app.models.photo import Photo, PhotoStatus
from app.schemas.photo import (
    PhotoGeoJsonFeatureCollection,
    PhotoGeoJsonFeature,
    GeoJsonPointGeometry,
    PhotoGeoJsonProperties,
    PhotoPublicRead,
)
from app.services.storage import resolve_media_url

router = APIRouter(prefix="/photos", tags=["Photos Publiques"])


@router.get("", response_model=PhotoGeoJsonFeatureCollection)
async def list_public_photos_geojson(
    territory: Annotated[Territory, Depends(get_current_territory)],
    db: Annotated[AsyncSession, Depends(get_db)],
    year_min: int | None = Query(None, ge=1000, le=3000, description="Année minimale de prise de vue"),
    year_max: int | None = Query(None, ge=1000, le=3000, description="Année maximale de prise de vue"),
    search: str | None = Query(None, min_length=1, max_length=100, description="Recherche textuelle"),
    limit: int = Query(5000, ge=1, le=10000, description="Plafond de sécurité pour le volume GeoJSON"),
) -> PhotoGeoJsonFeatureCollection:
    """
    Retourne la collection GeoJSON (FeatureCollection) des photographies publiées
    et géolocalisées pour le territoire actif, prête pour le clustering cartographique.
    """
    if year_min is not None and year_max is not None and year_min > year_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "INVALID_DATE_RANGE",
                    "message": f"L'année minimale ({year_min}) ne peut être supérieure à l'année maximale ({year_max}).",
                }
            },
        )

    conditions = [
        Photo.territory_id == territory.id,
        Photo.status == PhotoStatus.PUBLISHED,
        Photo.latitude.is_not(None),
        Photo.longitude.is_not(None),
    ]

    if year_min is not None:
        conditions.append(Photo.year_taken >= year_min)
    if year_max is not None:
        conditions.append(Photo.year_taken <= year_max)

    if search and search.strip():
        # Échappement des métacaractères LIKE pour éviter les scans séquentiels non intentionnels
        clean_search = (
            search.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        search_filter = f"%{clean_search}%"
        conditions.append(
            or_(
                Photo.title.ilike(search_filter),
                Photo.description.ilike(search_filter),
                Photo.photographer.ilike(search_filter),
                Photo.archive_source.ilike(search_filter),
                Photo.period_label.ilike(search_filter),
                Photo.archive_ref.ilike(search_filter),
            )
        )

    stmt = (
        select(Photo)
        .options(noload(Photo.author), noload(Photo.territory))
        .where(and_(*conditions))
        .order_by(Photo.year_taken.asc().nulls_last(), Photo.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    photos = result.scalars().all()

    features: list[PhotoGeoJsonFeature] = []
    for p in photos:
        # Longitude en premier, Latitude en second selon le standard GeoJSON RFC 7946
        geometry = GeoJsonPointGeometry(
            type="Point",
            coordinates=(float(p.longitude), float(p.latitude)),
        )

        properties = PhotoGeoJsonProperties(
            id=p.id,
            title=p.title,
            description=p.description,
            photographer=p.photographer,
            year_taken=p.year_taken,
            is_exact_year=p.is_exact_year,
            date_exact=p.date_exact,
            period_label=p.period_label,
            archive_source=p.archive_source,
            archive_ref=p.archive_ref,
            original_source_url=p.original_source_url,
            license=p.license,
            bearing=p.bearing,
            field_of_view=p.field_of_view,
            view_distance=p.view_distance,
            image_thumb_url=resolve_media_url(p.file_thumb_path),
            image_display_url=resolve_media_url(p.file_display_path),
            image_original_url=resolve_media_url(p.file_original_path),
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

        features.append(
            PhotoGeoJsonFeature(
                type="Feature",
                id=str(p.id),
                geometry=geometry,
                properties=properties,
            )
        )

    return PhotoGeoJsonFeatureCollection(
        type="FeatureCollection",
        features=features,
    )


@router.get("/{id}", response_model=PhotoPublicRead)
async def get_public_photo_detail(
    id: uuid.UUID,
    territory: Annotated[Territory, Depends(get_current_territory)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PhotoPublicRead:
    """
    Retourne la fiche publique d'une photographie publiée du territoire actif.
    Ne divulgue aucun chemin de fichier interne ni identifiant utilisateur d'auteur.
    Renvoie 404 si la photo n'existe pas, n'appartient pas au territoire ou est en brouillon.
    """
    stmt = (
        select(Photo)
        .options(noload(Photo.author), noload(Photo.territory))
        .where(
            Photo.id == id,
            Photo.territory_id == territory.id,
            Photo.status == PhotoStatus.PUBLISHED,
        )
    )
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PHOTO_NOT_FOUND",
                    "message": "Photographie introuvable ou non publiée dans ce territoire.",
                }
            },
        )

    return PhotoPublicRead.model_validate(photo)
