import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class StorymapStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Storymap(Base):
    __tablename__ = "storymaps"
    __table_args__ = (
        UniqueConstraint("territory_id", "slug", name="uq_storymaps_territory_slug"),
    )

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

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    cover_image_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    status: Mapped[StorymapStatus] = mapped_column(
        Enum(StorymapStatus, name="storymap_status_enum"),
        default=StorymapStatus.DRAFT,
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

    # Relations
    territory = relationship("Territory", backref="storymaps", lazy="selectin")
    author = relationship("User", backref="storymaps", lazy="selectin")
    steps = relationship(
        "StorymapStep",
        back_populates="storymap",
        cascade="all, delete-orphan",
        order_by="StorymapStep.step_order",
        lazy="selectin",
    )


class StorymapStep(Base):
    __tablename__ = "storymap_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    storymap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storymaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("photos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    step_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content_markdown: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    audio_file_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    # Coordonnées cartographiques caméra MapLibre
    camera_lat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    camera_lng: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    camera_zoom: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=12.0,
    )
    camera_bearing: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    camera_pitch: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
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

    # Relations
    storymap = relationship("Storymap", back_populates="steps")
    photo = relationship("Photo", lazy="selectin")
