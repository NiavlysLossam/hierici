import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Territory(Base):
    __tablename__ = "territories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    center_lat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=43.1242,
    )
    center_lng: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.9280,
    )
    default_zoom: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=13,
    )
    basemaps: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Territory(slug='{self.slug}', name='{self.name}')>"

