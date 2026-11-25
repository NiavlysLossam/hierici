import io
import uuid
import logging
from dataclasses import dataclass
from typing import Any
from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.storage.base import StorageDriver

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Exception de base pour les erreurs de traitement d'image."""
    pass


class FileTooLargeError(ImageProcessingError):
    """Le fichier dépasse la taille maximale autorisée."""
    pass


class InvalidImageFormatError(ImageProcessingError):
    """Le format d'image est invalide, non autorisé ou corrompu."""
    pass


@dataclass
class ProcessedVariant:
    """Représente une déclinaison d'image générée."""
    variant_name: str
    content: bytes
    path: str
    content_type: str
    width: int
    height: int


@dataclass
class ImageProcessingResult:
    """Résultat complet du traitement des 3 déclinaisons d'image."""
    width: int
    height: int
    original: ProcessedVariant
    display: ProcessedVariant
    thumb: ProcessedVariant

    @property
    def variants(self) -> list[ProcessedVariant]:
        return [self.original, self.display, self.thumb]


class ImageService:
    """Service de validation, redressement EXIF, redimensionnement et compression WebP."""

    # 25 Mo strict
    MAX_FILE_SIZE = 25 * 1024 * 1024
    ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "TIFF"}
    DISPLAY_MAX_DIM = 2048
    DISPLAY_QUALITY = 85
    THUMB_MAX_DIM = 400
    THUMB_QUALITY = 80

    FORMAT_EXTENSIONS = {
        "JPEG": "jpg",
        "JPG": "jpg",
        "PNG": "png",
        "WEBP": "webp",
        "TIFF": "tif",
    }

    FORMAT_CONTENT_TYPES = {
        "JPEG": "image/jpeg",
        "JPG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "TIFF": "image/tiff",
    }

    def validate_file_size(self, content: bytes) -> None:
        """Vérifie que la taille du fichier ne dépasse pas la limite autorisée."""
        if len(content) > self.MAX_FILE_SIZE:
            raise FileTooLargeError(
                f"Le fichier dépasse la taille maximale autorisée de {self.MAX_FILE_SIZE // (1024 * 1024)} Mo."
            )

    def validate_and_open_image(self, content: bytes) -> tuple[Image.Image, str]:
        """Vérifie la taille, le format et l'intégrité de l'image via Pillow."""
        self.validate_file_size(content)

        if not content:
            raise InvalidImageFormatError("Le fichier d'image est vide.")

        try:
            img = Image.open(io.BytesIO(content))
            fmt = (img.format or "").upper()

            if fmt not in self.ALLOWED_FORMATS:
                raise InvalidImageFormatError(
                    f"Format d'image non supporté ({fmt or 'inconnu'}). Formats acceptés : JPEG, PNG, WEBP, TIFF."
                )

            # Charger les données de pixels pour détecter les fichiers corrompus ou tronqués
            img.load()
            return img, fmt
        except (UnidentifiedImageError, SyntaxError, ValueError, OSError, Image.DecompressionBombError) as e:
            logger.warning(f"Erreur d'ouverture ou d'intégrité d'image Pillow: {e}")
            raise InvalidImageFormatError("Format d'image non valide ou fichier corrompu.") from e

    def normalize_image(self, img: Image.Image) -> Image.Image:
        """Redresse automatiquement l'orientation EXIF et normalise les modes de couleur."""
        # Redressement EXIF automatique (orientation 1 à 8)
        oriented = ImageOps.exif_transpose(img)
        if oriented is None:
            oriented = img.copy()

        # Normalisation des modes de couleur pour compatibilité WebP
        if oriented.mode in ("RGB", "RGBA"):
            return oriented
        elif oriented.mode == "CMYK":
            return oriented.convert("RGB")
        elif oriented.mode == "P":
            if "transparency" in oriented.info:
                return oriented.convert("RGBA")
            return oriented.convert("RGB")
        elif oriented.mode in ("1", "L"):
            return oriented.convert("RGB")
        elif oriented.mode in ("LA", "PA"):
            return oriented.convert("RGBA")
        return oriented.convert("RGB")

    def create_variant(
        self, img: Image.Image, max_dim: int, quality: int
    ) -> tuple[bytes, int, int]:
        """Génère une déclinaison WebP compressée sans métadonnées EXIF."""
        variant_img = img.copy()
        # Ne redimensionne que si l'image dépasse la boîte max_dim x max_dim
        variant_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        width, height = variant_img.size

        out = io.BytesIO()
        # Enregistrer en WebP sans passer d'argument exif -> métadonnées purgées
        variant_img.save(out, format="WEBP", quality=quality)
        return out.getvalue(), width, height

    def process_image(
        self,
        content: bytes,
        territory_id: str | uuid.UUID,
        photo_id: str | uuid.UUID,
        filename: str | None = None,
    ) -> ImageProcessingResult:
        """Exécute l'intégralité du pipeline : validation, redressement, 3 déclinaisons."""
        img, fmt = self.validate_and_open_image(content)
        oriented_img = self.normalize_image(img)
        orig_width, orig_height = oriented_img.size

        # Détermination de l'extension de l'original
        ext = self.FORMAT_EXTENSIONS.get(fmt, "jpg")
        if filename:
            lower_name = filename.lower()
            if lower_name.endswith(".jpeg") or lower_name.endswith(".jpg"):
                ext = "jpg"
            elif lower_name.endswith(".png"):
                ext = "png"
            elif lower_name.endswith(".webp"):
                ext = "webp"
            elif lower_name.endswith(".tif") or lower_name.endswith(".tiff"):
                ext = "tif"

        str_territory_id = str(territory_id)
        str_photo_id = str(photo_id)

        original_path = f"photos/{str_territory_id}/{str_photo_id}/original.{ext}"
        display_path = f"photos/{str_territory_id}/{str_photo_id}/display.webp"
        thumb_path = f"photos/{str_territory_id}/{str_photo_id}/thumb.webp"

        # Déclinaison display (max 2048px, q85)
        display_bytes, disp_w, disp_h = self.create_variant(
            oriented_img, self.DISPLAY_MAX_DIM, self.DISPLAY_QUALITY
        )

        # Déclinaison thumb (max 400px, q80)
        thumb_bytes, thumb_w, thumb_h = self.create_variant(
            oriented_img, self.THUMB_MAX_DIM, self.THUMB_QUALITY
        )

        orig_content_type = self.FORMAT_CONTENT_TYPES.get(fmt, "application/octet-stream")

        original_variant = ProcessedVariant(
            variant_name="original",
            content=content,
            path=original_path,
            content_type=orig_content_type,
            width=orig_width,
            height=orig_height,
        )
        display_variant = ProcessedVariant(
            variant_name="display",
            content=display_bytes,
            path=display_path,
            content_type="image/webp",
            width=disp_w,
            height=disp_h,
        )
        thumb_variant = ProcessedVariant(
            variant_name="thumb",
            content=thumb_bytes,
            path=thumb_path,
            content_type="image/webp",
            width=thumb_w,
            height=thumb_h,
        )

        return ImageProcessingResult(
            width=orig_width,
            height=orig_height,
            original=original_variant,
            display=display_variant,
            thumb=thumb_variant,
        )

    async def save_variants(
        self, result: ImageProcessingResult, storage: StorageDriver
    ) -> dict[str, str]:
        """Sauvegarde les 3 déclinaisons sur le stockage et retourne les URLs d'accès."""
        urls: dict[str, str] = {}
        for variant in result.variants:
            url = await storage.save(
                content=variant.content,
                destination_path=variant.path,
                content_type=variant.content_type,
            )
            urls[f"{variant.variant_name}_url"] = url
        return urls


default_image_service = ImageService()


def get_image_service() -> ImageService:
    return default_image_service
