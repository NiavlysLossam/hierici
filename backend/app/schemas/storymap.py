import uuid
import re
import unicodedata
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, computed_field, model_validator, field_validator
from app.models.storymap import StorymapStatus
from app.schemas.photo import PhotoRead, PhotoPublicRead
from app.services.storage import resolve_media_url


def slugify(value: str) -> str:
    """Normalise une chaîne pour créer un slug URL-friendly sans accents ni caractères spéciaux."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


# ============================================================================
# Schemas des étapes de storymap (StorymapStep)
# ============================================================================

class StorymapStepBase(BaseModel):
    photo_id: uuid.UUID | None = None
    step_order: int = 0
    title: str = Field(..., min_length=1, max_length=255, description="Titre du chapitre / étape")
    content_markdown: str | None = Field(None, description="Texte narratif en Markdown")
    audio_file_path: str | None = Field(None, description="Chemin du document sonore MP3")

    # Coordonnées caméra MapLibre
    camera_lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude cible de la caméra")
    camera_lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude cible de la caméra")
    camera_zoom: float = Field(default=12.0, ge=0.0, le=24.0, description="Niveau de zoom [0, 24]")
    camera_bearing: float = Field(default=0.0, ge=0.0, le=360.0, description="Orientation angulaire [0, 360]")
    camera_pitch: float = Field(default=0.0, ge=0.0, le=85.0, description="Inclinaison 3D [0, 85]")

    @model_validator(mode="before")
    @classmethod
    def handle_step_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Aliases courts caméra
            if "lat" in data and "camera_lat" not in data:
                data["camera_lat"] = data["lat"]
            if "lng" in data and "camera_lng" not in data:
                data["camera_lng"] = data["lng"]
            if "zoom" in data and "camera_zoom" not in data:
                data["camera_zoom"] = data["zoom"]
            if "bearing" in data and "camera_bearing" not in data:
                data["camera_bearing"] = data["bearing"]
            if "pitch" in data and "camera_pitch" not in data:
                data["camera_pitch"] = data["pitch"]

            # Aliases camelCase
            if "cameraLat" in data and "camera_lat" not in data:
                data["camera_lat"] = data["cameraLat"]
            if "cameraLng" in data and "camera_lng" not in data:
                data["camera_lng"] = data["cameraLng"]
            if "cameraZoom" in data and "camera_zoom" not in data:
                data["camera_zoom"] = data["cameraZoom"]
            if "cameraBearing" in data and "camera_bearing" not in data:
                data["camera_bearing"] = data["cameraBearing"]
            if "cameraPitch" in data and "camera_pitch" not in data:
                data["camera_pitch"] = data["cameraPitch"]
            if "stepOrder" in data and "step_order" not in data:
                data["step_order"] = data["stepOrder"]
            if "photoId" in data and "photo_id" not in data:
                data["photo_id"] = data["photoId"]
            if "contentMarkdown" in data and "content_markdown" not in data:
                data["content_markdown"] = data["contentMarkdown"]
            if "audioFilePath" in data and "audio_file_path" not in data:
                data["audio_file_path"] = data["audioFilePath"]
        return data

    @field_validator("camera_bearing")
    @classmethod
    def normalize_bearing(cls, v: float) -> float:
        if v == 360.0:
            return 0.0
        return v


class StorymapStepCreate(StorymapStepBase):
    pass


class StorymapStepUpdate(BaseModel):
    photo_id: uuid.UUID | None = None
    step_order: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    content_markdown: str | None = None
    audio_file_path: str | None = None

    camera_lat: float | None = Field(None, ge=-90.0, le=90.0)
    camera_lng: float | None = Field(None, ge=-180.0, le=180.0)
    camera_zoom: float | None = Field(None, ge=0.0, le=24.0)
    camera_bearing: float | None = Field(None, ge=0.0, le=360.0)
    camera_pitch: float | None = Field(None, ge=0.0, le=85.0)

    @model_validator(mode="before")
    @classmethod
    def handle_step_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "lat" in data and "camera_lat" not in data:
                data["camera_lat"] = data["lat"]
            if "lng" in data and "camera_lng" not in data:
                data["camera_lng"] = data["lng"]
            if "zoom" in data and "camera_zoom" not in data:
                data["camera_zoom"] = data["zoom"]
            if "bearing" in data and "camera_bearing" not in data:
                data["camera_bearing"] = data["bearing"]
            if "pitch" in data and "camera_pitch" not in data:
                data["camera_pitch"] = data["pitch"]
            if "cameraLat" in data and "camera_lat" not in data:
                data["camera_lat"] = data["cameraLat"]
            if "cameraLng" in data and "camera_lng" not in data:
                data["camera_lng"] = data["cameraLng"]
            if "cameraZoom" in data and "camera_zoom" not in data:
                data["camera_zoom"] = data["cameraZoom"]
            if "cameraBearing" in data and "camera_bearing" not in data:
                data["camera_bearing"] = data["cameraBearing"]
            if "cameraPitch" in data and "camera_pitch" not in data:
                data["camera_pitch"] = data["cameraPitch"]
            if "stepOrder" in data and "step_order" not in data:
                data["step_order"] = data["stepOrder"]
            if "photoId" in data and "photo_id" not in data:
                data["photo_id"] = data["photoId"]
            if "contentMarkdown" in data and "content_markdown" not in data:
                data["content_markdown"] = data["contentMarkdown"]
            if "audioFilePath" in data and "audio_file_path" not in data:
                data["audio_file_path"] = data["audioFilePath"]
        return data

    @field_validator("camera_bearing")
    @classmethod
    def normalize_bearing(cls, v: float | None) -> float | None:
        if v == 360.0:
            return 0.0
        return v


class StorymapStepRead(BaseModel):
    id: uuid.UUID
    storymap_id: uuid.UUID
    photo_id: uuid.UUID | None = None
    step_order: int
    title: str
    content_markdown: str | None = None
    audio_file_path: str | None = None
    camera_lat: float
    camera_lng: float
    camera_zoom: float
    camera_bearing: float
    camera_pitch: float
    created_at: datetime
    updated_at: datetime
    photo: PhotoRead | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def audio_url(self) -> str | None:
        return resolve_media_url(self.audio_file_path)

    @computed_field
    @property
    def lat(self) -> float:
        return self.camera_lat

    @computed_field
    @property
    def lng(self) -> float:
        return self.camera_lng

    @computed_field
    @property
    def zoom(self) -> float:
        return self.camera_zoom

    @computed_field
    @property
    def bearing(self) -> float:
        return self.camera_bearing

    @computed_field
    @property
    def pitch(self) -> float:
        return self.camera_pitch


class StorymapStepPublicRead(BaseModel):
    id: uuid.UUID
    step_order: int
    title: str
    content_markdown: str | None = None
    camera_lat: float
    camera_lng: float
    camera_zoom: float
    camera_bearing: float
    camera_pitch: float
    photo_id: uuid.UUID | None = None
    photo: PhotoPublicRead | None = None

    # Exclu de la sérialisation publique pour éviter la fuite de chemin de stockage interne
    audio_file_path: str | None = Field(None, exclude=True)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def audio_url(self) -> str | None:
        return resolve_media_url(self.audio_file_path)

    @computed_field
    @property
    def lat(self) -> float:
        return self.camera_lat

    @computed_field
    @property
    def lng(self) -> float:
        return self.camera_lng

    @computed_field
    @property
    def zoom(self) -> float:
        return self.camera_zoom

    @computed_field
    @property
    def bearing(self) -> float:
        return self.camera_bearing

    @computed_field
    @property
    def pitch(self) -> float:
        return self.camera_pitch


# ============================================================================
# Schemas des récits / storymaps
# ============================================================================

class StorymapBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Titre de la storymap")
    summary: str | None = Field(None, description="Résumé introductif")
    slug: str | None = Field(None, max_length=255, description="Slug URL-friendly optionnel (déduit du titre si omis)")
    cover_image_path: str | None = Field(None, description="Chemin de l'image de couverture")
    status: StorymapStatus = Field(default=StorymapStatus.DRAFT, description="Statut de publication (draft / published)")

    @model_validator(mode="before")
    @classmethod
    def handle_base_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "coverImagePath" in data and "cover_image_path" not in data:
                data["cover_image_path"] = data["coverImagePath"]
        return data


class StorymapCreate(StorymapBase):
    territory_id: uuid.UUID | None = None
    steps: list[StorymapStepCreate] = Field(default_factory=list, description="Étapes initiales optionnelles")

    @model_validator(mode="before")
    @classmethod
    def handle_create_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "territoryId" in data and "territory_id" not in data:
                data["territory_id"] = data["territoryId"]
            if "coverImagePath" in data and "cover_image_path" not in data:
                data["cover_image_path"] = data["coverImagePath"]
        return data


class StorymapUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    summary: str | None = None
    slug: str | None = Field(None, max_length=255)
    cover_image_path: str | None = None
    status: StorymapStatus | None = None
    territory_id: uuid.UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "territoryId" in data and "territory_id" not in data:
                data["territory_id"] = data["territoryId"]
            if "coverImagePath" in data and "cover_image_path" not in data:
                data["cover_image_path"] = data["coverImagePath"]
        return data


class StorymapRead(BaseModel):
    id: uuid.UUID
    territory_id: uuid.UUID
    author_user_id: uuid.UUID | None = None
    slug: str
    title: str
    summary: str | None = None
    cover_image_path: str | None = None
    status: StorymapStatus
    created_at: datetime
    updated_at: datetime
    steps: list[StorymapStepRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def cover_image_url(self) -> str | None:
        return resolve_media_url(self.cover_image_path)

    @computed_field
    @property
    def steps_count(self) -> int:
        return len(self.steps)


class StorymapPublicRead(BaseModel):
    id: uuid.UUID
    territory_id: uuid.UUID
    slug: str
    title: str
    summary: str | None = None
    status: StorymapStatus
    created_at: datetime
    updated_at: datetime
    steps: list[StorymapStepPublicRead] = Field(default_factory=list)

    # Exclu de la sérialisation publique pour éviter la fuite de métadonnées sensibles internes
    cover_image_path: str | None = Field(None, exclude=True)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def cover_image_url(self) -> str | None:
        return resolve_media_url(self.cover_image_path)

    @computed_field
    @property
    def steps_count(self) -> int:
        return len(self.steps)


class StorymapListResponse(BaseModel):
    items: list[StorymapRead]
    total: int
    page: int
    page_size: int
    pages: int


class StorymapPublicListResponse(BaseModel):
    items: list[StorymapPublicRead]
    total: int
    page: int
    page_size: int
    pages: int


class StorymapReorderPayload(BaseModel):
    step_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="Liste ordonnée exhaustive des identifiants d'étapes de la storymap",
    )
