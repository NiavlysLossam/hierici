import uuid
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.security import hash_password
from app.core.territory import get_current_territory
from app.models.user import User, UserRole
from app.models.territory import Territory
from app.schemas.territory import TerritoryRead, TerritoryUpdate, BasemapConfig
from app.schemas.user import UserRead, UserCreate, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administration Générale"])

DEFAULT_BASEMAPS = [
    {
        "id": "osm-standard",
        "name": "OpenStreetMap Standard",
        "type": "xyz",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "max_zoom": 19,
        "min_zoom": 0,
        "is_default": True,
    },
    {
        "id": "esri-world-imagery",
        "name": "Photographies Aériennes (Esri)",
        "type": "xyz",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Esri, Maxar, Earthstar Geographics",
        "max_zoom": 19,
        "min_zoom": 0,
        "is_default": False,
    },
    {
        "id": "osm-fr",
        "name": "Rendu OpenStreetMap France",
        "type": "xyz",
        "url": "https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap France",
        "max_zoom": 20,
        "min_zoom": 0,
        "is_default": False,
    },
]


async def _resolve_territory(
    current_user: User,
    request: Request,
    db: AsyncSession,
) -> Territory:
    """Résout le territoire de travail de l'administrateur selon ses privilèges."""
    if current_user.role != UserRole.SUPERADMIN:
        if not current_user.territory_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "TERRITORY_NOT_ASSIGNED", "message": "Aucun territoire assigné au contributeur."}},
            )
        result = await db.execute(select(Territory).where(Territory.id == current_user.territory_id))
        territory = result.scalar_one_or_none()
        if not territory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "TERRITORY_NOT_FOUND", "message": "Territoire introuvable."}},
            )
        return territory

    # Pour un Superadmin : utilise le territoire spécifié dans la requête ou son territoire
    return await get_current_territory(request, db)


@router.get("/territory", response_model=TerritoryRead)
async def get_admin_territory(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Retourne la configuration actuelle du territoire (cadrage, nom et fonds de carte)."""
    territory = await _resolve_territory(current_user, request, db)
    # Remplissage par défaut si aucun fond de carte n'est encore enregistré
    if not territory.basemaps:
        territory.basemaps = DEFAULT_BASEMAPS
    return territory


@router.patch("/territory", response_model=TerritoryRead)
async def update_admin_territory(
    update_in: TerritoryUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Met à jour le cadrage cartographique (centre, zoom), le nom et les fonds de carte du territoire."""
    territory = await _resolve_territory(current_user, request, db)

    if update_in.name is not None:
        territory.name = update_in.name.strip()
    if update_in.center_lat is not None:
        territory.center_lat = update_in.center_lat
    if update_in.center_lng is not None:
        territory.center_lng = update_in.center_lng
    if update_in.default_zoom is not None:
        territory.default_zoom = update_in.default_zoom
    if update_in.basemaps is not None:
        territory.basemaps = [bm.model_dump() for bm in update_in.basemaps]

    await db.commit()
    await db.refresh(territory)
    if not territory.basemaps:
        territory.basemaps = DEFAULT_BASEMAPS
    return territory


@router.get("/users", response_model=list[UserRead])
async def list_admin_users(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les contributeurs rattachés au territoire de l'administrateur."""
    territory = await _resolve_territory(current_user, request, db)

    query = (
        select(User)
        .where(User.territory_id == territory.id)
        .order_by(User.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    user_in: UserCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau compte utilisateur contributeur pour le territoire."""
    territory = await _resolve_territory(current_user, request, db)

    # Vérification d'unicité de l'email
    existing = await db.execute(select(User).where(User.email == user_in.email.strip().lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "EMAIL_ALREADY_EXISTS", "message": "Cette adresse email est déjà utilisée."}},
        )

    # Empêcher un contributeur de créer un Superadmin
    target_role = user_in.role
    if current_user.role != UserRole.SUPERADMIN and target_role == UserRole.SUPERADMIN:
        target_role = UserRole.CONTRIBUTOR

    new_user = User(
        email=user_in.email.strip().lower(),
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name.strip(),
        role=target_role,
        territory_id=territory.id,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_admin_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Modifie le nom, le rôle, l'état d'activation ou le mot de passe d'un utilisateur du territoire."""
    territory = await _resolve_territory(current_user, request, db)

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "Utilisateur introuvable."}},
        )

    # Vérification d'isolation territoriale
    if current_user.role != UserRole.SUPERADMIN and target_user.territory_id != territory.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN_TERRITORY", "message": "Action interdite sur un utilisateur externe."}},
        )

    # Garde de sécurité : un utilisateur non-Superadmin ne peut pas modifier un Superadmin
    if current_user.role != UserRole.SUPERADMIN and target_user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN_SUPERADMIN_TARGET", "message": "Impossible de modifier un compte Superadministrateur."}},
        )

    # Garde de sécurité : un utilisateur ne peut pas se désactiver lui-même
    if user_update.is_active is False and target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "CANNOT_DEACTIVATE_SELF", "message": "Vous ne pouvez pas désactiver votre propre compte."}},
        )

    if user_update.full_name is not None:
        target_user.full_name = user_update.full_name.strip()
    if user_update.role is not None and current_user.role == UserRole.SUPERADMIN:
        target_user.role = user_update.role
    if user_update.is_active is not None:
        target_user.is_active = user_update.is_active
    if user_update.password:
        target_user.password_hash = hash_password(user_update.password)

    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Supprime un compte contributeur du territoire (avec garde anti-auto-suppression)."""
    territory = await _resolve_territory(current_user, request, db)

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "Utilisateur introuvable."}},
        )

    if current_user.role != UserRole.SUPERADMIN and target_user.territory_id != territory.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN_TERRITORY", "message": "Action interdite sur un utilisateur externe."}},
        )

    # Garde de sécurité : un utilisateur non-Superadmin ne peut pas supprimer un Superadmin
    if current_user.role != UserRole.SUPERADMIN and target_user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN_SUPERADMIN_TARGET", "message": "Impossible de supprimer un compte Superadministrateur."}},
        )

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "CANNOT_DELETE_SELF", "message": "Vous ne pouvez pas supprimer votre propre compte."}},
        )

    await db.delete(target_user)
    await db.commit()
    return None

