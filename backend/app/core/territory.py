from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.territory import Territory
from app.config import settings


def extract_territory_slug_from_request(request: Request) -> str:
    """Extrait le slug de territoire selon la priorité :
    1. En-tête HTTP 'X-Territory-Slug'
    2. Sous-domaine hôte (ex: 'toulon.hierici.fr' -> 'toulon', 'toulon.localhost' -> 'toulon')
    3. Fallback variable DEFAULT_TERRITORY_SLUG
    """
    # 1. En-tête direct
    header_slug = request.headers.get("X-Territory-Slug")
    if header_slug and header_slug.strip():
        return header_slug.strip().lower()

    # 2. Sous-domaine
    host = (request.headers.get("host") or "").split(":")[0]
    parts = host.split(".")

    # Exclure les adresses IP (ex: 127.0.0.1, 192.168.1.10)
    is_ip = len(parts) == 4 and all(p.isdigit() for p in parts)
    if not is_ip:
        # Gérer toulon.localhost (len == 2) et toulon.hierici.fr (len >= 3)
        if len(parts) >= 2 and parts[-1] == "localhost" and parts[0] not in ("www", "api", "localhost"):
            return parts[0].lower()
        if len(parts) >= 3 and parts[0] not in ("www", "api"):
            return parts[0].lower()

    # 3. Fallback variable d'environnement
    return settings.DEFAULT_TERRITORY_SLUG.lower()


class TerritoryMiddleware(BaseHTTPMiddleware):
    """Middleware extrayant et injectant le slug de territoire actif dans le contexte request.state."""

    async def dispatch(self, request: Request, call_next):
        slug = extract_territory_slug_from_request(request)
        request.state.territory_slug = slug
        response = await call_next(request)
        return response


async def get_current_territory(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Territory:
    """Dépendance FastAPI injectant et vérifiant le territoire actif pour les requêtes."""
    slug = extract_territory_slug_from_request(request)

    query = select(Territory).where(Territory.slug == slug)
    result = await db.execute(query)
    territory = result.scalar_one_or_none()

    if not territory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TERRITORY_NOT_FOUND",
                    "message": f"Le territoire '{slug}' est introuvable ou n'est pas configuré.",
                    "slug": slug,
                }
            },
        )

    # Injection dans le state de la requête pour réutilisation dans les routes suivantes
    request.state.territory = territory
    return territory

