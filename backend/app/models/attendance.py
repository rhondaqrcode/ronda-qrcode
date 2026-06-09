import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class AttendanceStatus(str, enum.Enum):
    checked_in = "checked_in"
    checked_out = "checked_out"
    absent = "absent"


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), default=AttendanceStatus.checked_in, nullable=False
    )
    check_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    check_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    check_in_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    check_in_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", back_populates="attendance_records")
    location = relationship("Location", back_populates="attendance_records")
