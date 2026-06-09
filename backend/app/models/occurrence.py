import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class OccurrenceSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class OccurrenceStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Occurrence(Base):
    __tablename__ = "occurrences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    reported_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    severity: Mapped[OccurrenceSeverity] = mapped_column(
        Enum(OccurrenceSeverity), default=OccurrenceSeverity.medium, nullable=False
    )
    status: Mapped[OccurrenceStatus] = mapped_column(
        Enum(OccurrenceStatus), default=OccurrenceStatus.open, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    location = relationship("Location", back_populates="occurrences")
    reported_by = relationship("Employee", back_populates="occurrences")
