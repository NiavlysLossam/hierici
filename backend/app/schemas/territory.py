import uuid
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BasemapConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=150, description="Nom d'affichage du fond de carte")
    type: Literal["xyz", "wms", "wmts", "vector"] = Field(..., description="Type de service : xyz, wms, wmts ou vector")
    url: str = Field(..., min_length=1, max_length=1000, description="URL du flux ou modèle de tuiles")
    attribution: str | None = Field(default=None, max_length=500, description="Mention de copyright légale")
    max_zoom: int | None = Field(default=19, ge=1, le=24, description="Niveau de zoom maximum")
    min_zoom: int | None = Field(default=0, ge=0, le=24, description="Niveau de zoom minimum")
    is_default: bool = Field(default=False, description="Définit si ce fond est sélectionné par défaut")
    layers: str | None = Field(default=None, max_length=255, description="Nom des couches (WMS / WMTS)")
    format: str | None = Field(default="image/png", max_length=100, description="Format d'image")


class TerritoryBase(BaseModel):
    slug: str = Field(..., max_length=100, description="Identifiant unique d'URL du territoire")
    name: str = Field(..., max_length=255, description="Nom d'affichage du territoire")
    center_lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude du centre par défaut")
    center_lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude du centre par défaut")
    default_zoom: int = Field(default=13, ge=1, le=22, description="Niveau de zoom cartographique par défaut")
    basemaps: list[BasemapConfig] = Field(default_factory=list, description="Liste des fonds de carte configurés")

    @field_validator("basemaps", mode="before")
    @classmethod
    def ensure_basemaps_list(cls, v):
        if v is None:
            return []
        return v


class TerritoryCreate(TerritoryBase):
    pass


class TerritoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    center_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    center_lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    default_zoom: int | None = Field(default=None, ge=1, le=22)
    basemaps: list[BasemapConfig] | None = None

    @field_validator("basemaps")
    @classmethod
    def validate_basemaps_defaults(cls, v):
        if not v:
            return v
        # Garantit qu'un et un seul fond est marqué is_default=True
        has_default = any(b.is_default for b in v)
        if not has_default:
            v[0].is_default = True
        else:
            first_found = False
            for b in v:
                if b.is_default:
                    if not first_found:
                        first_found = True
                    else:
                        b.is_default = False
        return v


class TerritoryRead(TerritoryBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
