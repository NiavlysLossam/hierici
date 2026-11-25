import logging
from sqlalchemy import text, select
from app.core.database import engine, AsyncSessionLocal, Base
from app.models.territory import Territory
from app.models.user import User, UserRole
from app.models.photo import Photo, PhotoStatus
from app.models.storymap import Storymap, StorymapStep, StorymapStatus
from app.core.security import hash_password
from app.config import settings

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialise l'extension PostGIS, crée les tables et le territoire initial + superadmin si besoin."""
    async with engine.begin() as conn:
        try:
            # Active l'extension PostGIS
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            logger.info("Extension PostGIS vérifiée / activée avec succès.")
        except Exception as e:
            logger.warning(f"Note sur l'activation PostGIS: {e}")

        # Crée toutes les tables déclarées (territories, users, etc.) si elles n'existent pas
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Schéma des tables de la base de données synchronisé.")

    # Vérification et initialisation des données de base
    async with AsyncSessionLocal() as session:
        # 1. Territoire pilote
        result_territory = await session.execute(
            select(Territory).where(Territory.slug == settings.DEFAULT_TERRITORY_SLUG)
        )
        existing_territory = result_territory.scalar_one_or_none()

        if not existing_territory:
            default_territory = Territory(
                slug=settings.DEFAULT_TERRITORY_SLUG,
                name="Territoire Pilote",
                center_lat=43.1242,
                center_lng=5.9280,
                default_zoom=13,
            )
            session.add(default_territory)
            await session.commit()
            await session.refresh(default_territory)
            existing_territory = default_territory
            logger.info(f"Territoire par défaut créé: '{settings.DEFAULT_TERRITORY_SLUG}'.")
        else:
            logger.info(f"Territoire '{settings.DEFAULT_TERRITORY_SLUG}' déjà existant.")

        # 2. Compte Superadmin initial
        result_user = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        existing_admin = result_user.scalar_one_or_none()

        if not existing_admin:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                full_name=settings.ADMIN_FULL_NAME,
                role=UserRole.SUPERADMIN,
                territory_id=existing_territory.id,
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            logger.info(f"Compte Superadmin initial créé: '{settings.ADMIN_EMAIL}'.")
        else:
            logger.info(f"Compte Superadmin '{settings.ADMIN_EMAIL}' déjà existant.")
