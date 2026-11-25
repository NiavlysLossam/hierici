import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, computed_field, model_validator, field_validator
from app.models.photo import PhotoStatus
from app.services.storage import resolve_media_url


class PhotoBase(BaseModel):
    title: str = Field(..., min_length=1, description="Titre de la photographie")
    description: str | None = None
    photographer: str | None = None
    year_taken: int | None = None
    year: int | None = None
    is_exact_year: bool = True
    date_exact: str | None = None
    period_label: str | None = None
    archive_source: str | None = None
    archive_ref: str | None = None
    archive_reference: str | None = None
    original_source_url: str | None = None
    source_url: str | None = None
    license: str | None = "Domaine Public"
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    bearing: int | None = Field(None, ge=0, le=360, description="Azimut en degrés (0-359, 360 normalisé à 0)")

    @field_validator("bearing")
    @classmethod
    def normalize_bearing_val(cls, v: int | None) -> int | None:
        if v == 360:
            return 0
        return v
    field_of_view: int = Field(60, ge=1, le=180, description="Champ de vision en degrés")
    view_distance: int = Field(160, ge=20, le=2000, description="Longueur du cône de vision en mètres")
    file_original_path: str | None = None
    image_original_path: str | None = None
    file_display_path: str | None = None
    image_display_path: str | None = None
    file_thumb_path: str | None = None
    image_thumb_path: str | None = None
    status: PhotoStatus = PhotoStatus.DRAFT
    territory_id: uuid.UUID | None = None


class PhotoCreate(PhotoBase):
    @model_validator(mode="after")
    def validate_rules(self) -> "PhotoCreate":
        # Synchronisation des alias
        if self.year is not None and self.year_taken is None:
            self.year_taken = self.year
        if self.archive_reference is not None and self.archive_ref is None:
            self.archive_ref = self.archive_reference
        if self.source_url is not None and self.original_source_url is None:
            self.original_source_url = self.source_url
        if self.image_original_path is not None and self.file_original_path is None:
            self.file_original_path = self.image_original_path
        if self.image_display_path is not None and self.file_display_path is None:
            self.file_display_path = self.image_display_path
        if self.image_thumb_path is not None and self.file_thumb_path is None:
            self.file_thumb_path = self.image_thumb_path

        # Si l'une des coordonnées est fournie, l'autre doit l'être
        if (self.latitude is not None and self.longitude is None) or (
            self.latitude is None and self.longitude is not None
        ):
            raise ValueError("Latitude et longitude doivent être renseignées ensemble.")

        # Si publié, les coordonnées géographiques sont obligatoires
        if self.status == PhotoStatus.PUBLISHED:
            if self.latitude is None or self.longitude is None:
                raise ValueError(
                    "Les coordonnées géographiques (latitude et longitude) sont obligatoires pour la publication d'une photo."
                )

        return self


class PhotoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    description: str | None = None
    photographer: str | None = None
    year_taken: int | None = None
    year: int | None = None
    is_exact_year: bool | None = None
    date_exact: str | None = None
    period_label: str | None = None
    archive_source: str | None = None
    archive_ref: str | None = None
    archive_reference: str | None = None
    original_source_url: str | None = None
    source_url: str | None = None
    license: str | None = None
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    bearing: int | None = Field(None, ge=0, le=360, description="Azimut en degrés (0-359, 360 normalisé à 0)")

    @field_validator("bearing")
    @classmethod
    def normalize_bearing_val(cls, v: int | None) -> int | None:
        if v == 360:
            return 0
        return v
    field_of_view: int | None = Field(None, ge=1, le=180)
    view_distance: int | None = Field(None, ge=20, le=2000)
    file_original_path: str | None = None
    image_original_path: str | None = None
    file_display_path: str | None = None
    image_display_path: str | None = None
    file_thumb_path: str | None = None
    image_thumb_path: str | None = None
    status: PhotoStatus | None = None
    territory_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_rules(self) -> "PhotoUpdate":
        if self.year is not None and self.year_taken is None:
            self.year_taken = self.year
        if self.archive_reference is not None and self.archive_ref is None:
            self.archive_ref = self.archive_reference
        if self.source_url is not None and self.original_source_url is None:
            self.original_source_url = self.source_url
        if self.image_original_path is not None and self.file_original_path is None:
            self.file_original_path = self.image_original_path
        if self.image_display_path is not None and self.file_display_path is None:
            self.file_display_path = self.image_display_path
        if self.image_thumb_path is not None and self.file_thumb_path is None:
            self.file_thumb_path = self.image_thumb_path
        return self


class PhotoRead(BaseModel):
    id: uuid.UUID
    territory_id: uuid.UUID
    author_user_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    photographer: str | None = None
    year_taken: int | None = None
    is_exact_year: bool = True
    date_exact: str | None = None
    period_label: str | None = None
    archive_source: str | None = None
    archive_ref: str | None = None
    original_source_url: str | None = None
    license: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    bearing: int | None = None
    field_of_view: int = 60
    view_distance: int = 160
    file_original_path: str | None = None
    file_display_path: str | None = None
    file_thumb_path: str | None = None
    status: PhotoStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def year(self) -> int | None:
        return self.year_taken

    @computed_field
    @property
    def archive_reference(self) -> str | None:
        return self.archive_ref

    @computed_field
    @property
    def source_url(self) -> str | None:
        return self.original_source_url

    @computed_field
    @property
    def created_by_id(self) -> uuid.UUID | None:
        return self.author_user_id

    @computed_field
    @property
    def image_original_path(self) -> str | None:
        return self.file_original_path

    @computed_field
    @property
    def image_display_path(self) -> str | None:
        return self.file_display_path

    @computed_field
    @property
    def image_thumb_path(self) -> str | None:
        return self.file_thumb_path

    @computed_field
    @property
    def original_url(self) -> str | None:
        return resolve_media_url(self.file_original_path)

    @computed_field
    @property
    def display_url(self) -> str | None:
        return resolve_media_url(self.file_display_path)

    @computed_field
    @property
    def thumb_url(self) -> str | None:
        return resolve_media_url(self.file_thumb_path)

    @computed_field
    @property
    def image_original_url(self) -> str | None:
        return self.original_url

    @computed_field
    @property
    def image_display_url(self) -> str | None:
        return self.display_url

    @computed_field
    @property
    def image_thumb_url(self) -> str | None:
        return self.thumb_url

    @computed_field
    @property
    def location(self) -> dict | None:
        if self.longitude is not None and self.latitude is not None:
            return {"type": "Point", "coordinates": [self.longitude, self.latitude]}
        return None


class PhotoUploadResponse(BaseModel):
    photo_id: uuid.UUID
    file_original_path: str
    file_display_path: str
    file_thumb_path: str
    original_url: str
    display_url: str
    thumb_url: str
    width: int
    height: int
    photo: PhotoRead | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image_original_path(self) -> str:
        return self.file_original_path

    @computed_field
    @property
    def image_display_path(self) -> str:
        return self.file_display_path

    @computed_field
    @property
    def image_thumb_path(self) -> str:
        return self.file_thumb_path

    @computed_field
    @property
    def image_original_url(self) -> str:
        return self.original_url

    @computed_field
    @property
    def image_display_url(self) -> str:
        return self.display_url

    @computed_field
    @property
    def image_thumb_url(self) -> str:
        return self.thumb_url


class PhotoListResponse(BaseModel):
    items: list[PhotoRead]
    total: int
    page: int
    page_size: int
    pages: int


class GeoJsonPointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]  # (longitude, latitude)


class PhotoGeoJsonProperties(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    photographer: str | None = None
    year_taken: int | None = None
    is_exact_year: bool = True
    date_exact: str | None = None
    period_label: str | None = None
    archive_source: str | None = None
    archive_ref: str | None = None
    original_source_url: str | None = None
    license: str | None = None
    bearing: int | None = None
    field_of_view: int = 60
    view_distance: int = 160
    image_thumb_url: str | None = None
    image_display_url: str | None = None
    image_original_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhotoGeoJsonFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: GeoJsonPointGeometry
    properties: PhotoGeoJsonProperties


class PhotoGeoJsonFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PhotoGeoJsonFeature]


class PhotoPublicRead(BaseModel):
    id: uuid.UUID
    territory_id: uuid.UUID
    title: str
    description: str | None = None
    photographer: str | None = None
    year_taken: int | None = None
    is_exact_year: bool = True
    date_exact: str | None = None
    period_label: str | None = None
    archive_source: str | None = None
    archive_ref: str | None = None
    original_source_url: str | None = None
    license: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    bearing: int | None = None
    field_of_view: int = 60
    view_distance: int = 160
    original_url: str | None = None
    display_url: str | None = None
    thumb_url: str | None = None
    image_original_url: str | None = None
    image_display_url: str | None = None
    image_thumb_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
