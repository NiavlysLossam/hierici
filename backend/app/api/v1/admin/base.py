from fastapi import APIRouter, Depends
from app.core.auth import get_current_active_user, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin", tags=["Administration & Sécurité"])


@router.get("/status")
async def get_admin_status(
    current_user: User = Depends(get_current_active_user),
):
    """Route protégée vérifiant que l'utilisateur est authentifié (Contributeur ou Superadmin)."""
    return {
        "status": "authorized",
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "territory_id": str(current_user.territory_id) if current_user.territory_id else None,
    }


@router.get("/superadmin/overview")
async def get_superadmin_overview(
    current_user: User = Depends(require_role(UserRole.SUPERADMIN)),
):
    """Route strictement réservée au rôle Superadmin."""
    return {
        "status": "ok",
        "message": "Accès réservé au Superadmin validé",
        "admin_email": current_user.email,
    }

