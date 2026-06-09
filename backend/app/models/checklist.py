import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class ChecklistStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    approved = "approved"
    rejected = "rejected"


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    shift: Mapped[str] = mapped_column(String(40), nullable=False)
    observations: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ChecklistStatus] = mapped_column(
        Enum(ChecklistStatus), default=ChecklistStatus.pending, nullable=False
    )
    approved_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="checklists")
    location = relationship("Location", back_populates="checklists")
    tasks = relationship(
        "ChecklistTask",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="ChecklistTask.id",
    )


class ChecklistTask(Base):
    __tablename__ = "checklist_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    checklist = relationship("Checklist", back_populates="tasks")
