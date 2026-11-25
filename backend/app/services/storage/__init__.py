from functools import lru_cache
from app.config import settings
from app.services.storage.base import StorageDriver
from app.services.storage.local import LocalStorageDriver
from app.services.storage.s3 import S3StorageDriver


@lru_cache()
def get_storage_driver() -> StorageDriver:
    """Factory instanciant le pilote de stockage configuré par variable d'environnement."""
    driver_type = settings.STORAGE_DRIVER.lower().strip()
    if driver_type == "s3":
        return S3StorageDriver()
    return LocalStorageDriver()


def resolve_media_url(path: str | None) -> str | None:
    """Résout l'URL publique d'un chemin de fichier média via le pilote de stockage actif."""
    if not path:
        return None
    try:
        driver = get_storage_driver()
        if hasattr(driver, "resolve_url"):
            return driver.resolve_url(path)
    except Exception:
        pass
    clean_path = path.lstrip("/")
    return f"/uploads/{clean_path}"


__all__ = [
    "StorageDriver",
    "LocalStorageDriver",
    "S3StorageDriver",
    "get_storage_driver",
    "resolve_media_url",
]

