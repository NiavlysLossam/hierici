import io
import asyncio
from pathlib import Path
import math
import uuid
import logging
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User, UserRole
from app.models.storymap import Storymap, StorymapStep, StorymapStatus
from app.models.photo import Photo
from app.services.storage import get_storage_driver, StorageDriver
from app.schemas.storymap import (
    slugify,
    StorymapCreate,
    StorymapUpdate,
    StorymapRead,
    StorymapListResponse,
    StorymapStepCreate,
    StorymapStepUpdate,
    StorymapStepRead,
    StorymapReorderPayload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/storymaps", tags=["Administration Storymaps"])

MAX_COVER_FILE_SIZE = 25 * 1024 * 1024  # 25 Mo
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo

ALLOWED_COVER_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav"}
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "application/ogg",
}


async def _read_upload_file(file: UploadFile, max_size: int) -> bytes:
    """Lit le flux du fichier téléversé et valide sa taille maximale."""
    if file.size is not None and file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Le fichier dépasse la taille maximale autorisée de {max_size // (1024 * 1024)} Mo.",
                }
            },
        )
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Le fichier dépasse la taille maximale autorisée de {max_size // (1024 * 1024)} Mo.",
                }
            },
        )
    return content


async def _generate_unique_slug(db: AsyncSession, territory_id: uuid.UUID, base_text: str, current_id: uuid.UUID | None = None) -> str:
    """Génère un slug normalisé unique pour un territoire donné."""
    clean_slug = slugify(base_text)
    if not clean_slug:
        clean_slug = f"recit-{uuid.uuid4().hex[:6]}"

    clean_slug = clean_slug[:240]

    candidate = clean_slug
    counter = 1
    while True:
        stmt = select(Storymap.id).where(
            Storymap.territory_id == territory_id,
            Storymap.slug == candidate,
        )
        if current_id:
            stmt = stmt.where(Storymap.id != current_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return candidate
        counter += 1
        candidate = f"{clean_slug}-{counter}"


async def _validate_photo_id(db: AsyncSession, territory_id: uuid.UUID, photo_id: uuid.UUID | None) -> None:
    """Vérifie qu'une photo existe et appartient bien au même territoire (AD-2)."""
    if photo_id is not None:
        stmt = select(Photo.id).where(
            Photo.id == photo_id,
            Photo.territory_id == territory_id,
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "INVALID_PHOTO",
                        "message": "Photo introuvable ou non autorisée dans ce territoire.",
                    }
                },
            )


@router.post(
    "",
    response_model=StorymapRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle storymap",
)
async def create_storymap(
    storymap_in: StorymapCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapRead:
    """Crée une nouvelle storymap rattachée au territoire actif et à l'auteur connecté.
    Permet l'ajout facultatif d'étapes initiales ordonnées.
    """
    # 1. Résolution stricte du territoire
    if current_user.role != UserRole.SUPERADMIN:
        if not current_user.territory_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "TERRITORY_NOT_ASSIGNED",
                        "message": "Le contributeur n'a aucun territoire assigné.",
                    }
                },
            )
        target_territory_id = current_user.territory_id
    else:
        target_territory_id = storymap_in.territory_id or current_user.territory_id
        if not target_territory_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "TERRITORY_REQUIRED",
                        "message": "Un territoire_id est requis pour créer une storymap.",
                    }
                },
            )

    # 2. Slug automatique unique
    slug_source = storymap_in.slug.strip() if storymap_in.slug else storymap_in.title
    unique_slug = await _generate_unique_slug(db, target_territory_id, slug_source)

    # 3. Création de l'entité Storymap
    new_storymap = Storymap(
        territory_id=target_territory_id,
        author_user_id=current_user.id,
        slug=unique_slug,
        title=storymap_in.title,
        summary=storymap_in.summary,
        cover_image_path=storymap_in.cover_image_path,
        status=storymap_in.status,
    )

    # 4. Étapes initiales optionnelles avec validation territoriale de photo_id
    for idx, step_in in enumerate(storymap_in.steps):
        await _validate_photo_id(db, target_territory_id, step_in.photo_id)
        order = step_in.step_order if step_in.step_order > 0 else idx
        step = StorymapStep(
            storymap=new_storymap,
            photo_id=step_in.photo_id,
            step_order=order,
            title=step_in.title,
            content_markdown=step_in.content_markdown,
            audio_file_path=step_in.audio_file_path,
            camera_lat=step_in.camera_lat,
            camera_lng=step_in.camera_lng,
            camera_zoom=step_in.camera_zoom,
            camera_bearing=step_in.camera_bearing,
            camera_pitch=step_in.camera_pitch,
        )
        new_storymap.steps.append(step)

    db.add(new_storymap)
    await db.commit()
    await db.refresh(new_storymap)

    # Recharger avec les étapes et photos associées
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
            selectinload(Storymap.territory),
        )
        .where(Storymap.id == new_storymap.id)
    )
    res = await db.execute(stmt)
    persisted = res.scalar_one()

    return StorymapRead.model_validate(persisted)


@router.get(
    "",
    response_model=StorymapListResponse,
    summary="Lister les storymaps du territoire actif",
)
async def list_storymaps(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de la page"),
    status_filter: StorymapStatus | None = Query(None, alias="status", description="Filtrer par statut"),
    search: str | None = Query(None, description="Recherche textuelle sur le titre ou résumé"),
    territory_id: uuid.UUID | None = Query(None, description="Filtre territoire réservé aux superadmins"),
) -> StorymapListResponse:
    """Retourne la liste paginée des storymaps du territoire du contributeur."""
    base_query = select(Storymap).options(
        selectinload(Storymap.steps),
        selectinload(Storymap.author),
    )

    # Cloisonnement multi-territoire
    if current_user.role != UserRole.SUPERADMIN:
        base_query = base_query.where(Storymap.territory_id == current_user.territory_id)
    else:
        if territory_id:
            base_query = base_query.where(Storymap.territory_id == territory_id)
        elif current_user.territory_id:
            base_query = base_query.where(Storymap.territory_id == current_user.territory_id)

    if status_filter:
        base_query = base_query.where(Storymap.status == status_filter)

    if search and search.strip():
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            Storymap.title.ilike(term) | Storymap.summary.ilike(term)
        )

    # Comptage total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Pagination & tri chronologique inversé
    paginated_query = (
        base_query.order_by(Storymap.created_at.desc(), Storymap.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await db.execute(paginated_query)
    items = list(items_result.scalars().all())

    pages = math.ceil(total / page_size) if total > 0 else 1

    return StorymapListResponse(
        items=[StorymapRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{id}",
    response_model=StorymapRead,
    summary="Consulter le détail administratif d'une storymap avec ses étapes",
)
async def get_storymap(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapRead:
    """Retourne une storymap par identifiant unique."""
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
        )
        .where(Storymap.id == id)
    )

    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    return StorymapRead.model_validate(storymap)


@router.put(
    "/{id}",
    response_model=StorymapRead,
    summary="Mettre à jour les métadonnées d'une storymap",
)
async def update_storymap(
    id: uuid.UUID,
    storymap_in: StorymapUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapRead:
    """Met à jour le titre, le résumé, le slug ou le statut de publication d'une storymap."""
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
        )
        .where(Storymap.id == id)
    )

    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    update_data = storymap_in.model_dump(exclude_unset=True)

    if "title" in update_data and update_data["title"] is not None:
        storymap.title = update_data["title"]
    if "summary" in update_data:
        storymap.summary = update_data["summary"]
    if "cover_image_path" in update_data:
        storymap.cover_image_path = update_data["cover_image_path"]
    if "status" in update_data and update_data["status"] is not None:
        storymap.status = update_data["status"]

    if "slug" in update_data and update_data["slug"] is not None and update_data["slug"].strip():
        new_slug = await _generate_unique_slug(
            db, storymap.territory_id, update_data["slug"], current_id=storymap.id
        )
        storymap.slug = new_slug

    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(storymap)

    return StorymapRead.model_validate(storymap)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une storymap et toutes ses étapes (cascade)",
)
async def delete_storymap(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
):
    """Supprime définitivement une storymap et propage la suppression en cascade à toutes ses étapes."""
    stmt = (
        select(Storymap)
        .options(selectinload(Storymap.steps))
        .where(Storymap.id == id)
    )
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    # Nettoyage des fichiers physiques orphelins (couverture et audios des étapes)
    if storymap.cover_image_path:
        try:
            await storage.delete(storymap.cover_image_path)
        except Exception as e:
            logger.warning(f"Erreur purge couverture lors suppression storymap: {e}")

    for step in storymap.steps:
        if step.audio_file_path:
            try:
                await storage.delete(step.audio_file_path)
            except Exception as e:
                logger.warning(f"Erreur purge audio step {step.id} lors suppression storymap: {e}")

    await db.delete(storymap)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Gestion des étapes (StorymapStep)
# ============================================================================

@router.post(
    "/{id}/steps",
    response_model=StorymapStepRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un chapitre / étape à une storymap",
)
async def add_storymap_step(
    id: uuid.UUID,
    step_in: StorymapStepCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapStepRead:
    """Ajoute une nouvelle étape ordonnée avec cadrage cartographique à la storymap."""
    stmt = (
        select(Storymap)
        .options(selectinload(Storymap.steps))
        .where(Storymap.id == id)
    )
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    # Validation d'isolation territoriale de la photo liée
    await _validate_photo_id(db, storymap.territory_id, step_in.photo_id)

    # Calcul de l'ordre séquentiel si non fourni
    if step_in.step_order <= 0 and storymap.steps:
        next_order = max(s.step_order for s in storymap.steps) + 1
    else:
        next_order = step_in.step_order

    new_step = StorymapStep(
        storymap_id=storymap.id,
        photo_id=step_in.photo_id,
        step_order=next_order,
        title=step_in.title,
        content_markdown=step_in.content_markdown,
        audio_file_path=step_in.audio_file_path,
        camera_lat=step_in.camera_lat,
        camera_lng=step_in.camera_lng,
        camera_zoom=step_in.camera_zoom,
        camera_bearing=step_in.camera_bearing,
        camera_pitch=step_in.camera_pitch,
    )

    db.add(new_step)
    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(new_step)

    # Charger la photo liée si présente
    if new_step.photo_id:
        step_stmt = (
            select(StorymapStep)
            .options(selectinload(StorymapStep.photo))
            .where(StorymapStep.id == new_step.id)
        )
        step_res = await db.execute(step_stmt)
        new_step = step_res.scalar_one()

    return StorymapStepRead.model_validate(new_step)


@router.put(
    "/{id}/steps/reorder",
    response_model=StorymapRead,
    summary="Réordonner atomiquement les étapes d'une storymap",
)
async def reorder_storymap_steps(
    id: uuid.UUID,
    payload: StorymapReorderPayload,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapRead:
    """Met à jour atomiquement les champs `step_order` (0, 1, 2...) de l'ensemble des étapes d'une storymap."""
    ordered_ids = payload.step_ids

    stmt = (
        select(Storymap)
        .options(selectinload(Storymap.steps).selectinload(StorymapStep.photo))
        .where(Storymap.id == id)
    )
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    step_map = {step.id: step for step in storymap.steps}

    # Vérifier que les IDs reçus correspondent exactement aux étapes existantes (ni doublons, ni manquants)
    if len(ordered_ids) != len(step_map) or set(ordered_ids) != set(step_map.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_STEP_IDS",
                    "message": "La liste des identifiants d'étapes ne correspond pas exactement aux étapes de ce récit.",
                }
            },
        )

    # Réordonnancement atomique
    for new_order, step_id in enumerate(ordered_ids):
        step_map[step_id].step_order = new_order
        step_map[step_id].updated_at = datetime.now(timezone.utc)

    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(storymap)

    # Recharger les étapes triées
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
        )
        .where(Storymap.id == storymap.id)
    )
    reloaded = (await db.execute(stmt)).scalar_one()

    return StorymapRead.model_validate(reloaded)


@router.put(
    "/{id}/steps/{step_id}",
    response_model=StorymapStepRead,
    summary="Mettre à jour un chapitre / étape",
)
async def update_storymap_step(
    id: uuid.UUID,
    step_id: uuid.UUID,
    step_in: StorymapStepUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> StorymapStepRead:
    """Met à jour le contenu, le cadrage cartographique ou la photo d'une étape."""
    stmt = select(Storymap).where(Storymap.id == id)
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    step_stmt = (
        select(StorymapStep)
        .options(selectinload(StorymapStep.photo))
        .where(StorymapStep.id == step_id, StorymapStep.storymap_id == id)
    )
    step_result = await db.execute(step_stmt)
    step = step_result.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STEP_NOT_FOUND",
                    "message": "Étape introuvable dans cette storymap.",
                }
            },
        )

    update_data = step_in.model_dump(exclude_unset=True)

    if "photo_id" in update_data:
        await _validate_photo_id(db, storymap.territory_id, update_data["photo_id"])
        step.photo_id = update_data["photo_id"]
    if "title" in update_data and update_data["title"] is not None:
        step.title = update_data["title"]
    if "content_markdown" in update_data:
        step.content_markdown = update_data["content_markdown"]
    if "audio_file_path" in update_data:
        step.audio_file_path = update_data["audio_file_path"]
    if "step_order" in update_data and update_data["step_order"] is not None:
        step.step_order = update_data["step_order"]

    if "camera_lat" in update_data and update_data["camera_lat"] is not None:
        step.camera_lat = update_data["camera_lat"]
    if "camera_lng" in update_data and update_data["camera_lng"] is not None:
        step.camera_lng = update_data["camera_lng"]
    if "camera_zoom" in update_data and update_data["camera_zoom"] is not None:
        step.camera_zoom = update_data["camera_zoom"]
    if "camera_bearing" in update_data and update_data["camera_bearing"] is not None:
        step.camera_bearing = update_data["camera_bearing"]
    if "camera_pitch" in update_data and update_data["camera_pitch"] is not None:
        step.camera_pitch = update_data["camera_pitch"]

    step.updated_at = datetime.now(timezone.utc)
    storymap.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(step)

    # Recharger avec photo si photo_id est défini
    if step.photo_id:
        step_stmt = (
            select(StorymapStep)
            .options(selectinload(StorymapStep.photo))
            .where(StorymapStep.id == step.id)
        )
        step = (await db.execute(step_stmt)).scalar_one()

    return StorymapStepRead.model_validate(step)


@router.delete(
    "/{id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une étape d'une storymap",
)
async def delete_storymap_step(
    id: uuid.UUID,
    step_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
):
    """Supprime une étape spécifique d'une storymap et purge son fichier audio."""
    stmt = select(Storymap).where(Storymap.id == id)
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    step_stmt = select(StorymapStep).where(
        StorymapStep.id == step_id,
        StorymapStep.storymap_id == id,
    )
    step_res = await db.execute(step_stmt)
    step = step_res.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STEP_NOT_FOUND",
                    "message": "Étape introuvable dans cette storymap.",
                }
            },
        )

    # Purge de l'audio orphelin
    if step.audio_file_path:
        try:
            await storage.delete(step.audio_file_path)
        except Exception as e:
            logger.warning(f"Erreur purge audio step {step.id}: {e}")

    await db.delete(step)
    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Téléversement de Médias (Couverture & Audio de chapitre)
# ============================================================================

@router.post(
    "/{id}/cover",
    response_model=StorymapRead,
    summary="Téléverser et associer une image de couverture pour la storymap",
)
async def upload_storymap_cover(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
) -> StorymapRead:
    """Téléverse une image de couverture, la redimensionne et la convertit en WebP optimisé."""
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
        )
        .where(Storymap.id == id)
    )
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    content = await _read_upload_file(file, max_size=MAX_COVER_FILE_SIZE)

    def _process_cover(raw_bytes: bytes) -> bytes:
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_COVER_FORMATS:
                raise ValueError("FORMAT_NOT_ALLOWED")
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            img.save(out_buf, format="WEBP", quality=85)
            return out_buf.getvalue()
        except UnidentifiedImageError:
            raise ValueError("INVALID_IMAGE")
        except Image.DecompressionBombError:
            raise ValueError("DECOMPRESSION_BOMB")
        except (OSError, ValueError) as e:
            if str(e) == "FORMAT_NOT_ALLOWED":
                raise
            raise ValueError("CORRUPTED_IMAGE")

    try:
        webp_bytes = await asyncio.to_thread(_process_cover, content)
    except (ValueError, OSError, Image.DecompressionBombError) as ve:
        if str(ve) == "FORMAT_NOT_ALLOWED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_IMAGE_FORMAT",
                        "message": "Format d'image non supporté. Formats acceptés : JPEG, PNG, WEBP.",
                    }
                },
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_IMAGE_FORMAT",
                    "message": "Fichier image corrompu ou illisible.",
                }
            },
        )

    # Purge ancien cover si existant
    if storymap.cover_image_path:
        try:
            await storage.delete(storymap.cover_image_path)
        except Exception as e:
            logger.warning(f"Erreur lors de la purge de l'ancien cover {storymap.cover_image_path}: {e}")

    dest_path = f"territories/{storymap.territory_id}/storymaps/{storymap.id}/cover_{uuid.uuid4().hex[:8]}.webp"
    await storage.save(webp_bytes, dest_path, content_type="image/webp")

    storymap.cover_image_path = dest_path
    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(storymap)

    return StorymapRead.model_validate(storymap)


@router.delete(
    "/{id}/cover",
    response_model=StorymapRead,
    summary="Supprimer l'image de couverture d'une storymap",
)
async def delete_storymap_cover(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
) -> StorymapRead:
    """Supprime l'image de couverture d'une storymap et purge le fichier physique."""
    stmt = (
        select(Storymap)
        .options(
            selectinload(Storymap.steps).selectinload(StorymapStep.photo),
            selectinload(Storymap.author),
        )
        .where(Storymap.id == id)
    )
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    if storymap.cover_image_path:
        try:
            await storage.delete(storymap.cover_image_path)
        except Exception as e:
            logger.warning(f"Erreur purge couverture {storymap.cover_image_path}: {e}")
        storymap.cover_image_path = None
        storymap.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(storymap)

    return StorymapRead.model_validate(storymap)


@router.post(
    "/{id}/steps/{step_id}/audio",
    response_model=StorymapStepRead,
    summary="Téléverser et associer un fichier audio pour une étape de storymap",
)
async def upload_storymap_step_audio(
    id: uuid.UUID,
    step_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
) -> StorymapStepRead:
    """Téléverse un document sonore (MP3, M4A, OGG, WAV) pour un chapitre narrative."""
    stmt = select(Storymap).where(Storymap.id == id)
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    step_stmt = (
        select(StorymapStep)
        .options(selectinload(StorymapStep.photo))
        .where(StorymapStep.id == step_id, StorymapStep.storymap_id == id)
    )
    step_res = await db.execute(step_stmt)
    step = step_res.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STEP_NOT_FOUND",
                    "message": "Étape introuvable dans cette storymap.",
                }
            },
        )

    # Validation stricte du format audio (extension ET type MIME)
    ext = Path(file.filename or "").suffix.lower()
    ct = (file.content_type or "").lower().split(";")[0].strip()

    if ext not in ALLOWED_AUDIO_EXTENSIONS or ct not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_AUDIO_FORMAT",
                    "message": "Format audio non supporté. Formats acceptés : .mp3, .m4a, .ogg, .wav avec type MIME audio valide.",
                }
            },
        )

    if not ext:
        ext = ".mp3"

    content = await _read_upload_file(file, max_size=MAX_AUDIO_FILE_SIZE)

    # Purge ancien fichier audio si présent
    if step.audio_file_path:
        try:
            await storage.delete(step.audio_file_path)
        except Exception as e:
            logger.warning(f"Erreur purge ancien audio {step.audio_file_path}: {e}")

    dest_path = f"territories/{storymap.territory_id}/storymaps/{storymap.id}/audio/{step.id}_{uuid.uuid4().hex[:8]}{ext}"
    out_mime = ct if ct in ALLOWED_AUDIO_MIMES else "audio/mpeg"
    await storage.save(content, dest_path, content_type=out_mime)

    step.audio_file_path = dest_path
    step.updated_at = datetime.now(timezone.utc)
    storymap.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(step)

    return StorymapStepRead.model_validate(step)


@router.delete(
    "/{id}/steps/{step_id}/audio",
    response_model=StorymapStepRead,
    summary="Supprimer le fichier audio d'une étape de storymap",
)
async def delete_storymap_step_audio(
    id: uuid.UUID,
    step_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
) -> StorymapStepRead:
    """Supprime le document sonore associé à une étape et purge le fichier physique."""
    stmt = select(Storymap).where(Storymap.id == id)
    if current_user.role != UserRole.SUPERADMIN:
        stmt = stmt.where(Storymap.territory_id == current_user.territory_id)

    result = await db.execute(stmt)
    storymap = result.scalar_one_or_none()

    if not storymap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STORYMAP_NOT_FOUND",
                    "message": "Storymap introuvable ou non autorisée.",
                }
            },
        )

    step_stmt = (
        select(StorymapStep)
        .options(selectinload(StorymapStep.photo))
        .where(StorymapStep.id == step_id, StorymapStep.storymap_id == id)
    )
    step_res = await db.execute(step_stmt)
    step = step_res.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "STEP_NOT_FOUND",
                    "message": "Étape introuvable dans cette storymap.",
                }
            },
        )

    if step.audio_file_path:
        try:
            await storage.delete(step.audio_file_path)
        except Exception as e:
            logger.warning(f"Erreur purge audio {step.audio_file_path}: {e}")
        step.audio_file_path = None
        step.updated_at = datetime.now(timezone.utc)
        storymap.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(step)

    return StorymapStepRead.model_validate(step)

