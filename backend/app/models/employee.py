from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)
    position: Mapped[str] = mapped_column(String(80), nullable=False, default="Auxiliar de limpeza")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user = relationship("User", back_populates="employee", uselist=False)
    attendance_records = relationship("Attendance", back_populates="employee")
    checklists = relationship("Checklist", back_populates="employee")
    occurrences = relationship("Occurrence", back_populates="reported_by")
    photos = relationship("UploadedPhoto", back_populates="uploaded_by")

    @property
    def user_email(self) -> str | None:
        return self.user.email if self.user else None

    @property
    def user_role(self) -> str | None:
        return self.user.role.value if self.user else None
