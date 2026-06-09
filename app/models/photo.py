import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PhotoEntityType(str, enum.Enum):
    checklist = "checklist"
    occurrence = "occurrence"
    general = "general"


class UploadedPhoto(Base):
    __tablename__ = "uploaded_photos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[PhotoEntityType] = mapped_column(
        Enum(PhotoEntityType), default=PhotoEntityType.general, nullable=False
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    uploader = relationship("Employee", back_populates="photos")
