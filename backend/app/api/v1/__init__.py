from fastapi import APIRouter
from app.api.v1.public.territory import router as territory_router
from app.api.v1.public.photos import router as photos_public_router
from app.api.v1.public.storymaps import router as storymaps_public_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin.base import router as admin_router
from app.api.v1.admin.territory import router as territory_admin_router
from app.api.v1.admin.photos import router as photos_admin_router
from app.api.v1.admin.storymaps import router as storymaps_admin_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(territory_router)
api_v1_router.include_router(photos_public_router)
api_v1_router.include_router(storymaps_public_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(territory_admin_router)
api_v1_router.include_router(photos_admin_router)
api_v1_router.include_router(storymaps_admin_router)
