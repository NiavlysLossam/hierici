import uuid
from datetime import datetime, timezone
import enum
from typing import Any
from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, ForeignKey, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from geoalchemy2 import Geometry
from app.core.database import Base


class PhotoStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    territory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("territories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    photographer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    year_taken: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    is_exact_year: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    date_exact: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    period_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    archive_source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    archive_ref: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    original_source_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    license: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default="Domaine Public",
    )

    # Coordonnées géographiques WGS84 (EPSG:4326)
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    # Orientation et champ de vision
    bearing: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    field_of_view: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    view_distance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=160,
        server_default=text("160"),
    )

    # Fichiers médias gérés via StorageDriver
    file_original_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    file_display_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    file_thumb_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    status: Mapped[PhotoStatus] = mapped_column(
        Enum(PhotoStatus, name="photo_status_enum"),
        default=PhotoStatus.DRAFT,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Alias & synonymes pour compatibilité documentaire
    created_by_id = synonym("author_user_id")
    year = synonym("year_taken")
    archive_reference = synonym("archive_ref")
    source_url = synonym("original_source_url")
    location_geom = synonym("location")
    image_original_path = synonym("file_original_path")
    image_display_path = synonym("file_display_path")
    image_thumb_path = synonym("file_thumb_path")

    # Relations
    territory = relationship("Territory", backref="photos", lazy="selectin")
    author = relationship("User", backref="photos", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Photo(id='{self.id}', title='{self.title}', status='{self.status}')>"
