from fastapi import APIRouter, Depends
from app.models.territory import Territory
from app.schemas.territory import TerritoryRead
from app.core.territory import get_current_territory
from app.api.v1.admin.territory import DEFAULT_BASEMAPS

router = APIRouter(prefix="/territory", tags=["Territoire"])


@router.get("/current", response_model=TerritoryRead)
async def get_current_active_territory(
    territory: Territory = Depends(get_current_territory),
):
    """Retourne les métadonnées et le cadrage cartographique du territoire actif."""
    if not territory.basemaps:
        territory.basemaps = DEFAULT_BASEMAPS
    return territory

