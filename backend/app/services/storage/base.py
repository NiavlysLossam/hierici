from abc import ABC, abstractmethod


class StorageDriver(ABC):
    """Interface abstraite définissant le contrat pour tous les pilotes de stockage média."""

    @abstractmethod
    async def save(
        self,
        content: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Enregistre le contenu binaire à la destination spécifiée et renvoie l'URL d'accès."""
        pass

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Lit et retourne le contenu binaire du fichier situé au chemin indiqué."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Supprime le fichier du stockage. Renvoie True si supprimé, False s'il n'existait pas."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Indique si le fichier existe dans le stockage."""
        pass

    @abstractmethod
    def resolve_url(self, path: str) -> str:
        """Génère l'URL d'accès public de manière synchrone pour le fichier."""
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Génère l'URL d'accès public ou relative pour le fichier."""
        pass

