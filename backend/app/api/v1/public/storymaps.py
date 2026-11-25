import math
import uuid
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.territory import get_current_territory
from app.models.territory import Territory
from app.models.storymap import Storymap, StorymapStep, StorymapStatus
from app.models.photo import Photo, PhotoStatus
from app.schemas.storymap import (
    StorymapPublicRead,
    StorymapPublicListResponse,
    StorymapStepPublicRead,
)
from app.schemas.photo import PhotoPublicRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storymaps", tags=["Storymaps Publiques"])


def _format_public_storymap(storymap: Storymap) -> StorymapPublicRead:
    """Formate une storymap pour l'exposition publique en masquant les photos non publiées
    et en évitant toute fuite de métadonnées sensibles (chemins de fichiers internes, author_user_id).
    """
    public_steps: list[StorymapStepPublicRead] = []
    for step in storymap.steps:
        photo_public = None
        if step.photo and step.photo.status == PhotoStatus.PUBLISHED:
            photo_public = PhotoPublicRead.model_validate(step.photo)

        public_step = StorymapStepPublicRead(
            id=step.id,
            step_order=step.step_order,
            title=step.title,
            content_markdown=step.content_markdown,
            audio_file_path=step.audio_file_path,
            camera_lat=step.camera_lat,
            camera_lng=step.camera_lng,
            camera_zoom=step.camera_zoom,
            camera_bearing=step.camera_bearing,
            camera_pitch=step.camera_pitch,
            photo_id=step.photo_id if photo_public else None,
            photo=photo_public,
        )
        public_steps.append(public_step)

    return StorymapPublicRead(
        id=storymap.id,
        territory_id=storymap.territory_id,
        slug=storymap.slug,
        title=storymap.title,
        summary=storymap.summary,
        status=storymap.status,
        created_at=storymap.created_at,
        updated_at=storymap.updated_at,
        cover_image_path=storymap.cover_image_path,
        steps=public_steps,
    )


@router.get(
    "",
    response_model=StorymapPublicListResponse,
    summary="Catalogue des récits publiés du territoire actif",
)
async def list_public_storymaps(
    territory: Annotated[Territory, Depends(get_current_territory)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de la page"),
    search: str | None = Query(None, min_length=1, max_length=100, description="Recherche textuelle"),
) -> StorymapPublicListResponse:
    """Retourne la liste paginée des storymaps publiées du territoire actif.
    Ne divulgue aucun brouillon ni chemin interne.
    """
    base_query = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
        )
        .where(
            Storymap.territory_id == territory.id,
            Storymap.status == StorymapStatus.PUBLISHED,
        )
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            Storymap.title.ilike(term) | Storymap.summary.ilike(term)
        )

    # Comptage total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Pagination & tri
    paginated_query = (
        base_query.order_by(Storymap.created_at.desc(), Storymap.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await db.execute(paginated_query)
    items = list(items_result.scalars().all())

    pages = math.ceil(total / page_size) if total > 0 else 1

    return StorymapPublicListResponse(
        items=[_format_public_storymap(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{slug}",
    response_model=StorymapPublicRead,
    summary="Consulter un récit publié par son slug",
)
async def get_public_storymap_detail(
    slug: str,
    territory: Annotated[Territory, Depends(get_current_territory)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StorymapPublicRead:
    """Retourne les détails et l'ensemble des étapes ordonnées d'une storymap publiée.
    Renvoie 404 (STORYMAP_NOT_FOUND) si le récit est introuvable, en statut draft ou rattaché à un autre territoire.
    """
    clean_slug = slug.strip().lower()

    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
        )
        .where(
            Storymap.slug == clean_slug,
            Storymap.territory_id == territory.id,
            Storymap.status == StorymapStatus.PUBLISHED,
        )
    )

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non publiée dans ce territoire.",
                }
            },
        )

    return _format_public_storymap(storymap)
