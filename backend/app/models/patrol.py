from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class PatrolPoint(Base):
    __tablename__ = "patrol_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    qr_code: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    location = relationship("Location")
    scans = relationship("PatrolScan", back_populates="point")


class PatrolScan(Base):
    __tablename__ = "patrol_scans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    point_id: Mapped[int] = mapped_column(ForeignKey("patrol_points.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    qr_code: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    point = relationship("PatrolPoint", back_populates="scans")
    employee = relationship("Employee")
