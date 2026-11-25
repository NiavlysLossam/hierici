import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User, UserRole
from app.models.photo import Photo, PhotoStatus
from app.schemas.photo import (
    PhotoCreate,
    PhotoUpdate,
    PhotoRead,
    PhotoListResponse,
    PhotoUploadResponse,
)
from app.services.storage import get_storage_driver, StorageDriver
from app.services.image_service import (
    ImageService,
    get_image_service,
    FileTooLargeError,
    InvalidImageFormatError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/photos", tags=["Administration Photos"])


async def _purge_media_files(storage: StorageDriver, paths: list[str | None]) -> None:
    """Nettoie physiquement les fichiers médias associés via le StorageDriver."""
    for path in paths:
        if path:
            try:
                await storage.delete(path)
                logger.info(f"Fichier média purgé : {path}")
            except Exception as e:
                logger.warning(f"Erreur lors de la purge du média '{path}': {e}")


async def _read_upload_file(file: UploadFile, max_size: int = 25 * 1024 * 1024) -> bytes:
    """Lit le contenu du fichier téléversé et vérifie la taille limite de 25 Mo."""
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


@router.post(
    "",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle fiche photo historique",
)
async def create_photo(
    photo_in: PhotoCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Crée une nouvelle fiche photo rattachée au territoire du contributeur.
    En mode 'draft', les coordonnées GPS sont optionnelles.
    En mode 'published', les coordonnées GPS (latitude et longitude) sont obligatoires.
    """
    # Résolution du territoire : strict pour les contributeurs
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
        target_territory_id = photo_in.territory_id or current_user.territory_id
        if not target_territory_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "TERRITORY_REQUIRED",
                        "message": "Un territoire_id est requis pour créer une photo.",
                    }
                },
            )

    # Construction de la géométrie PostGIS si coordonnées fournies
    location_geom = None
    if photo_in.latitude is not None and photo_in.longitude is not None:
        location_geom = WKTElement(
            f"POINT({photo_in.longitude} {photo_in.latitude})",
            srid=4326,
        )

    new_photo = Photo(
        territory_id=target_territory_id,
        author_user_id=current_user.id,
        title=photo_in.title,
        description=photo_in.description,
        photographer=photo_in.photographer,
        year_taken=photo_in.year_taken,
        is_exact_year=photo_in.is_exact_year,
        date_exact=photo_in.date_exact,
        period_label=photo_in.period_label,
        archive_source=photo_in.archive_source,
        archive_ref=photo_in.archive_ref,
        original_source_url=photo_in.original_source_url,
        license=photo_in.license,
        latitude=photo_in.latitude,
        longitude=photo_in.longitude,
        location=location_geom,
        bearing=photo_in.bearing,
        field_of_view=photo_in.field_of_view,
        view_distance=photo_in.view_distance,
        file_original_path=photo_in.file_original_path,
        file_display_path=photo_in.file_display_path,
        file_thumb_path=photo_in.file_thumb_path,
        status=photo_in.status,
    )

    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)
    return new_photo


@router.get(
    "",
    response_model=PhotoListResponse,
    summary="Lister les photos historiques du territoire actif",
)
async def list_photos(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de la page"),
    status_filter: PhotoStatus | None = Query(None, alias="status", description="Filtrer par statut"),
    search: str | None = Query(None, description="Recherche textuelle sur le titre"),
    territory_id: uuid.UUID | None = Query(None, description="Filtre territoire réservé aux superadmins"),
):
    """Retourne la liste paginée des photographies historiques.
    Les contributeurs ne reçoivent strictement que les photos de leur propre territoire.
    """
    base_query = select(Photo)

    # Cloisonnement multi-territoire
    if current_user.role != UserRole.SUPERADMIN:
        base_query = base_query.where(Photo.territory_id == current_user.territory_id)
    else:
        if territory_id:
            base_query = base_query.where(Photo.territory_id == territory_id)
        elif current_user.territory_id:
            base_query = base_query.where(Photo.territory_id == current_user.territory_id)

    if status_filter:
        base_query = base_query.where(Photo.status == status_filter)

    if search and search.strip():
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            Photo.title.ilike(term)
            | Photo.description.ilike(term)
            | Photo.photographer.ilike(term)
            | Photo.archive_ref.ilike(term)
        )

    # Comptage total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Pagination & tri chronologique inversé déterministe
    paginated_query = (
        base_query.order_by(Photo.created_at.desc(), Photo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await db.execute(paginated_query)
    items = list(items_result.scalars().all())

    pages = math.ceil(total / page_size) if total > 0 else 1

    return PhotoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "/upload",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Téléverser une image et créer une nouvelle fiche photo",
)
async def upload_photo_direct(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    photo_id: uuid.UUID | None = Form(None),
    territory_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
    image_service: ImageService = Depends(get_image_service),
):
    """Téléverse un cliché photographique, génère les 3 déclinaisons WebP et initialise une photo."""
    if photo_id:
        return await upload_photo_image(
            photo_id=photo_id,
            file=file,
            current_user=current_user,
            db=db,
            storage=storage,
            image_service=image_service,
        )

    # Résolution du territoire
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
        target_territory_id = territory_id or current_user.territory_id
        if not target_territory_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "TERRITORY_REQUIRED",
                        "message": "Un territoire_id est requis pour téléverser une photo.",
                    }
                },
            )

    content = await _read_upload_file(file, max_size=image_service.MAX_FILE_SIZE)
    new_photo_id = uuid.uuid4()

    try:
        proc_result = await asyncio.to_thread(
            image_service.process_image,
            content=content,
            territory_id=target_territory_id,
            photo_id=new_photo_id,
            filename=file.filename,
        )
    except FileTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "Le fichier dépasse la taille maximale autorisée de 25 Mo.",
                }
            },
        )
    except InvalidImageFormatError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_IMAGE_FORMAT",
                    "message": "Format d'image non valide ou fichier corrompu.",
                }
            },
        )

    saved_urls = await image_service.save_variants(proc_result, storage)

    photo_title = (
        title.strip()
        if (title and title.strip())
        else (Path(file.filename).stem if file.filename else "Nouvelle photo")
    )

    new_photo = Photo(
        id=new_photo_id,
        territory_id=target_territory_id,
        author_user_id=current_user.id,
        title=photo_title,
        file_original_path=proc_result.original.path,
        file_display_path=proc_result.display.path,
        file_thumb_path=proc_result.thumb.path,
        status=PhotoStatus.DRAFT,
    )

    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)

    return PhotoUploadResponse(
        photo_id=new_photo.id,
        file_original_path=new_photo.file_original_path,
        file_display_path=new_photo.file_display_path,
        file_thumb_path=new_photo.file_thumb_path,
        original_url=saved_urls.get("original_url") or storage.resolve_url(new_photo.file_original_path),
        display_url=saved_urls.get("display_url") or storage.resolve_url(new_photo.file_display_path),
        thumb_url=saved_urls.get("thumb_url") or storage.resolve_url(new_photo.file_thumb_path),
        width=proc_result.width,
        height=proc_result.height,
        photo=PhotoRead.model_validate(new_photo),
    )


@router.post(
    "/{photo_id}/upload",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Téléverser et traiter l'image d'une photo existante",
)
async def upload_photo_image(
    photo_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
    image_service: ImageService = Depends(get_image_service),
):
    """Téléverse une image pour une fiche photo existante, produit les déclinaisons WebP et purge l'ancien média."""
    query = select(Photo).where(Photo.id == photo_id)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Photo.territory_id == current_user.territory_id)

    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PHOTO_NOT_FOUND",
                    "message": "Photo non trouvée",
                }
            },
        )

    content = await _read_upload_file(file, max_size=image_service.MAX_FILE_SIZE)

    try:
        proc_result = await asyncio.to_thread(
            image_service.process_image,
            content=content,
            territory_id=photo.territory_id,
            photo_id=photo.id,
            filename=file.filename,
        )
    except FileTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "Le fichier dépasse la taille maximale autorisée de 25 Mo.",
                }
            },
        )
    except InvalidImageFormatError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_IMAGE_FORMAT",
                    "message": "Format d'image non valide ou fichier corrompu.",
                }
            },
        )

    # Sauvegarde des nouveaux variants
    saved_urls = await image_service.save_variants(proc_result, storage)

    # Récupération des anciens chemins différents des nouveaux à purger
    old_paths = [
        p
        for p in [photo.file_original_path, photo.file_display_path, photo.file_thumb_path]
        if p and p not in (proc_result.original.path, proc_result.display.path, proc_result.thumb.path)
    ]

    photo.file_original_path = proc_result.original.path
    photo.file_display_path = proc_result.display.path
    photo.file_thumb_path = proc_result.thumb.path
    photo.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(photo)

    # Purge des anciens médias désormais orphelins
    if old_paths:
        await _purge_media_files(storage, old_paths)

    return PhotoUploadResponse(
        photo_id=photo.id,
        file_original_path=photo.file_original_path,
        file_display_path=photo.file_display_path,
        file_thumb_path=photo.file_thumb_path,
        original_url=saved_urls.get("original_url") or storage.resolve_url(photo.file_original_path),
        display_url=saved_urls.get("display_url") or storage.resolve_url(photo.file_display_path),
        thumb_url=saved_urls.get("thumb_url") or storage.resolve_url(photo.file_thumb_path),
        width=proc_result.width,
        height=proc_result.height,
        photo=PhotoRead.model_validate(photo),
    )


@router.get(
    "/metadata-suggestions",
    response_model=dict[str, list[str]],
    summary="Obtenir les suggestions de photographes et institutions d'archives",
)
async def get_metadata_suggestions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
    territory_id: uuid.UUID | None = Query(None, description="Filtre territoire réservé aux superadmins"),
    db: AsyncSession = Depends(get_db),
):
    """Retourne la liste ordonnée des photographes et institutions existants pour le territoire."""
    target_territory_id = current_user.territory_id
    if current_user.role == UserRole.SUPERADMIN:
        if territory_id:
            target_territory_id = territory_id
        elif not target_territory_id:
            from app.models.territory import Territory
            from app.core.territory import extract_territory_slug_from_request
            slug = extract_territory_slug_from_request(request)
            if slug:
                t_res = await db.execute(select(Territory.id).where(Territory.slug == slug))
                target_territory_id = t_res.scalar_one_or_none()

    query_p = (
        select(Photo.photographer)
        .where(Photo.territory_id == target_territory_id)
        .where(Photo.photographer.isnot(None))
        .distinct()
        .order_by(Photo.photographer)
        .limit(100)
    )
    res_p = await db.execute(query_p)
    photographers = list(dict.fromkeys(p.strip() for p in res_p.scalars().all() if p and p.strip()))

    query_a = (
        select(Photo.archive_source)
        .where(Photo.territory_id == target_territory_id)
        .where(Photo.archive_source.isnot(None))
        .distinct()
        .order_by(Photo.archive_source)
        .limit(100)
    )
    res_a = await db.execute(query_a)
    archive_sources = list(dict.fromkeys(a.strip() for a in res_a.scalars().all() if a and a.strip()))

    return {
        "photographers": photographers,
        "archive_sources": archive_sources,
    }


@router.get(
    "/{photo_id}",
    response_model=PhotoRead,
    summary="Consulter le détail d'une fiche photo",
)
async def get_photo(
    photo_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Récupère une photo par son identifiant unique.
    Renvoie 404 si la photo n'existe pas ou appartient à un autre territoire.
    """
    query = select(Photo).where(Photo.id == photo_id)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Photo.territory_id == current_user.territory_id)

    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PHOTO_NOT_FOUND",
                    "message": "Photo non trouvée",
                }
            },
        )

    return photo


@router.patch(
    "/{photo_id}",
    response_model=PhotoRead,
    summary="Mettre à jour partiellement une fiche photo",
)
@router.put(
    "/{photo_id}",
    response_model=PhotoRead,
    summary="Mettre à jour une fiche photo",
)
async def update_photo(
    photo_id: uuid.UUID,
    photo_in: PhotoUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Met à jour une fiche photo existante.
    Vérifie le cloisonnement territorial et impose la présence de coordonnées GPS si le statut est 'published'.
    """
    query = select(Photo).where(Photo.id == photo_id)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Photo.territory_id == current_user.territory_id)

    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PHOTO_NOT_FOUND",
                    "message": "Photo non trouvée",
                }
            },
        )

    update_data = photo_in.model_dump(exclude_unset=True)

    # Calcul des coordonnées et du statut résultants
    target_status = update_data.get("status", photo.status)
    target_lat = update_data.get("latitude", photo.latitude)
    target_lng = update_data.get("longitude", photo.longitude)

    if target_status == PhotoStatus.PUBLISHED:
        if target_lat is None or target_lng is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "COORDINATES_REQUIRED",
                        "message": "Les coordonnées géographiques (latitude et longitude) sont obligatoires pour publier une photo.",
                    }
                },
            )

    # Mise à jour des attributs du modèle
    for field, value in update_data.items():
        if field in ("latitude", "longitude"):
            continue
        elif field in ("year", "year_taken"):
            photo.year_taken = value
        elif field in ("archive_ref", "archive_reference"):
            photo.archive_ref = value
        elif field in ("source_url", "original_source_url"):
            photo.original_source_url = value
        elif field in ("image_original_path", "file_original_path"):
            photo.file_original_path = value
        elif field in ("image_display_path", "file_display_path"):
            photo.file_display_path = value
        elif field in ("image_thumb_path", "file_thumb_path"):
            photo.file_thumb_path = value
        elif field == "territory_id":
            if current_user.role == UserRole.SUPERADMIN and value is not None:
                photo.territory_id = value
        elif field in ("view_distance", "is_exact_year", "field_of_view"):
            if value is not None:
                setattr(photo, field, value)
        elif hasattr(photo, field):
            setattr(photo, field, value)

    # Mise à jour des coordonnées et de la géométrie PostGIS
    if "latitude" in update_data or "longitude" in update_data:
        if (target_lat is None) != (target_lng is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "COORDINATES_INCOMPLETE",
                        "message": "La latitude et la longitude doivent être fournies ensemble.",
                    }
                },
            )
        photo.latitude = target_lat
        photo.longitude = target_lng
        if target_lat is not None and target_lng is not None:
            photo.location = WKTElement(f"POINT({target_lng} {target_lat})", srid=4326)
        else:
            photo.location = None

    photo.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(photo)
    return photo


@router.delete(
    "/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une fiche photo et ses fichiers médias associés",
)
async def delete_photo(
    photo_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    storage: StorageDriver = Depends(get_storage_driver),
):
    """Supprime définitivement la fiche photo de la base de données
    et nettoie physiquement tous les fichiers médias associés via le StorageDriver.
    """
    query = select(Photo).where(Photo.id == photo_id)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Photo.territory_id == current_user.territory_id)

    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PHOTO_NOT_FOUND",
                    "message": "Photo non trouvée",
                }
            },
        )

    # Mémorisation des chemins de fichiers pour nettoyage post-commit
    media_paths = [
        photo.file_original_path,
        photo.file_display_path,
        photo.file_thumb_path,
    ]

    # Suppression en base de données en premier pour garantir la cohérence transactionnelle
    await db.delete(photo)
    await db.commit()

    # Nettoyage des fichiers physiques via le StorageDriver après validation en base
    await _purge_media_files(storage, media_paths)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
