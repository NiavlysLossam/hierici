import os
import asyncio
from pathlib import Path
from app.services.storage.base import StorageDriver
from app.config import settings


class LocalStorageDriver(StorageDriver):
    """Pilote de stockage écrivant sur le système de fichiers local / volume persistant Docker."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_PATH).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> Path:
        # Sécurise contre les traversées de répertoire
        clean_rel = Path(relative_path.lstrip("/"))
        full_path = (self.base_dir / clean_rel).resolve()
        if not full_path.is_relative_to(self.base_dir):
            raise ValueError(f"Tentative de traversée de répertoire non autorisée : {relative_path}")
        return full_path

    async def save(
        self,
        content: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        target_path = self._resolve_path(destination_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        def _write():
            with open(target_path, "wb") as f:
                f.write(content)

        await asyncio.to_thread(_write)
        return await self.get_url(destination_path)

    async def read(self, path: str) -> bytes:
        target_path = self._resolve_path(path)
        if not target_path.is_file():
            raise FileNotFoundError(f"Fichier introuvable sur le stockage local : {path}")

        def _read():
            with open(target_path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def delete(self, path: str) -> bool:
        target_path = self._resolve_path(path)
        if not target_path.exists():
            return False

        def _delete():
            try:
                target_path.unlink()
                return True
            except OSError:
                return False

        return await asyncio.to_thread(_delete)

    async def exists(self, path: str) -> bool:
        target_path = self._resolve_path(path)
        return target_path.is_file()

    def resolve_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return f"/uploads/{clean_path}"

    async def get_url(self, path: str) -> str:
        return self.resolve_url(path)

